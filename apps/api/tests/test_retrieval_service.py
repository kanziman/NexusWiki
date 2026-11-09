import asyncio
from dataclasses import replace
from uuid import uuid4

import httpx
import pytest

from api.db.user import UserDb
from api.errors import DatabaseError
from api.main import create_app
from api.services.retrieval import RetrievalResult, RetrievalService, strict_research_access
from api.settings import ApiSettings
from nexuswiki_core.retrieval_policy import DEFAULT_RETRIEVAL_POLICY
from nexuswiki_core.rrf import EvidenceHit


class FakeEmbeddingClient:
    async def embed(self, text: str, *, workspace_id: str) -> list[float]:
        assert text == "hello world"
        return [0.0] * 1024


def _rows(function: str) -> list[dict[str, object]]:
    if function == "search_chunks":
        return [{"id": "source-vector", "raw_source_id": "source-a", "chunk_index": 0}]
    if function == "search_wiki_embeddings":
        return [{"id": "wiki-chunk", "wiki_id": "wiki-a", "chunk_index": 0}]
    if function == "search_source_lexical":
        return [{"id": "source-lexical", "raw_source_id": "source-b", "chunk_index": 0}]
    if function == "search_wiki_lexical":
        return [{"id": "wiki-b", "slug": "wiki-b", "title": "Wiki B"}]
    raise AssertionError(function)


class FourChannelDb:
    async def rpc(self, function: str, *, params: dict[str, object]) -> list[dict[str, object]]:
        if function in {"search_chunks", "search_wiki_embeddings"}:
            assert len(params["p_query"]) == 1024  # type: ignore[arg-type]
        else:
            assert params["p_bigrams"] == "he el ll lo wo or rl ld"
        return _rows(function)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 402, 403])
async def test_research_scope_propagates_denied_channel_instead_of_partial_success(status):
    class DeniedDb(FourChannelDb):
        async def rpc(self, function, *, params):
            if function == "search_chunks":
                raise DatabaseError(status_code=status, sqlstate=None, message="거부")
            return await super().rpc(function, params=params)

    context = strict_research_access.set(True)
    try:
        with pytest.raises(DatabaseError):
            await RetrievalService(FakeEmbeddingClient()).retrieve(
                uuid4(), "hello world", 8, DeniedDb()
            )
    finally:
        strict_research_access.reset(context)


@pytest.mark.asyncio
async def test_four_first_wave_channels_begin_before_any_channel_is_released() -> None:
    started: set[str] = set()
    all_started = asyncio.Event()
    release = asyncio.Event()

    class BarrierDb:
        async def rpc(self, function: str, *, params: dict[str, object]) -> list[dict[str, object]]:
            started.add(function)
            if len(started) == 4:
                all_started.set()
            await release.wait()
            return _rows(function)

    task = asyncio.create_task(
        RetrievalService(FakeEmbeddingClient()).retrieve(uuid4(), "Hello WORLD", 4, BarrierDb())
    )
    await asyncio.wait_for(all_started.wait(), timeout=0.5)
    assert started == {
        "search_chunks",
        "search_wiki_embeddings",
        "search_source_lexical",
        "search_wiki_lexical",
    }
    release.set()
    result = await task
    assert len(result.evidence) == 4


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "policy",
    [
        DEFAULT_RETRIEVAL_POLICY,
        replace(
            DEFAULT_RETRIEVAL_POLICY,
            version="hybrid-rrf-v1",
            same_channel_aggregation="sum",
        ),
    ],
    ids=["best_rank", "sum"],
)
async def test_one_vector_serves_both_dense_channels_and_meta_is_safe(policy) -> None:
    result = await RetrievalService(FakeEmbeddingClient(), policy=policy).retrieve(
        uuid4(), "Hello WORLD", requested_k=4, user_db=FourChannelDb()
    )

    assert {hit.canonical_id for hit in result.evidence} == {
        "source:source-vector",
        "source:source-lexical",
        "wiki:wiki-a",
        "wiki:wiki-b",
    }
    assert result.meta["policy_version"] == policy.version
    assert result.meta["same_channel_aggregation"] == policy.same_channel_aggregation
    for name in ("wiki_vector", "source_vector", "wiki_lexical", "source_lexical"):
        channel = result.meta[name]
        assert channel["status"] == "ok"
        assert channel["requested"] == 20
        assert channel["returned"] == 1
        assert channel["underfill"] is True
        assert channel["raw_hit_ids"]
        assert channel["contribution"] == 1


@pytest.mark.asyncio
async def test_embedding_failure_marks_exactly_dense_channels_failed_and_leaves_lexical_live() -> (
    None
):
    class FailingEmbeddingClient:
        async def embed(self, text: str, *, workspace_id: str) -> list[float]:
            raise RuntimeError("provider secret must not leak")

    result = await RetrievalService(FailingEmbeddingClient()).retrieve(
        uuid4(), "Hello WORLD", requested_k=2, user_db=FourChannelDb()
    )

    assert {hit.kind for hit in result.evidence} == {"source", "wiki"}
    assert result.meta["wiki_vector"]["error_code"] == "embedding_unavailable"
    assert result.meta["source_vector"]["error_code"] == "embedding_unavailable"
    assert result.meta["wiki_lexical"]["status"] == "ok"
    assert result.meta["source_lexical"]["status"] == "ok"


class RecordingDb(FourChannelDb):
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def rpc(self, function: str, *, params: dict[str, object]) -> list[dict[str, object]]:
        self.calls.append(function)
        return await super().rpc(function, params=params)


@pytest.mark.asyncio
async def test_wiki_only_scope_calls_only_wiki_channels_and_marks_source_disabled() -> None:
    db = RecordingDb()
    policy = replace(DEFAULT_RETRIEVAL_POLICY, enabled_channels={"wiki_vector", "wiki_lexical"})

    result = await RetrievalService(FakeEmbeddingClient(), policy=policy).retrieve(
        uuid4(), "Hello WORLD", requested_k=4, user_db=db
    )

    assert sorted(db.calls) == ["search_wiki_embeddings", "search_wiki_lexical"]
    assert {hit.kind for hit in result.evidence} == {"wiki"}
    for name in ("source_vector", "source_lexical"):
        assert result.meta[name]["status"] == "disabled"
        assert result.meta[name]["error_code"] is None
    assert result.meta["wiki_vector"]["status"] == "ok"


@pytest.mark.asyncio
async def test_disabled_channel_stays_disabled_when_embedding_fails() -> None:
    class FailingEmbeddingClient:
        async def embed(self, text: str, *, workspace_id: str) -> list[float]:
            raise RuntimeError("down")

    policy = replace(DEFAULT_RETRIEVAL_POLICY, enabled_channels={"source_vector", "source_lexical"})
    result = await RetrievalService(FailingEmbeddingClient(), policy=policy).retrieve(
        uuid4(), "Hello WORLD", requested_k=2, user_db=FourChannelDb()
    )

    assert result.meta["source_vector"]["status"] == "failed"
    assert result.meta["wiki_vector"]["status"] == "disabled"
    assert result.meta["wiki_lexical"]["status"] == "disabled"
    assert {hit.kind for hit in result.evidence} == {"source"}


@pytest.mark.asyncio
async def test_lexical_only_policy_never_embeds_the_query() -> None:
    class ExplodingEmbeddingClient:
        async def embed(self, text: str, *, workspace_id: str) -> list[float]:
            raise AssertionError("embedding must not be called")

    policy = replace(DEFAULT_RETRIEVAL_POLICY, enabled_channels={"wiki_lexical", "source_lexical"})
    result = await RetrievalService(ExplodingEmbeddingClient(), policy=policy).retrieve(
        uuid4(), "Hello WORLD", requested_k=2, user_db=FourChannelDb()
    )

    assert result.meta["wiki_vector"]["status"] == "disabled"
    assert result.meta["source_vector"]["status"] == "disabled"


@pytest.mark.asyncio
async def test_failed_or_malformed_channel_cannot_cancel_siblings_or_leak_error() -> None:
    class PartialDb:
        async def rpc(self, function: str, *, params: dict[str, object]) -> list[dict[str, object]]:
            if function == "search_wiki_embeddings":
                raise RuntimeError("database internals must not leak")
            if function == "search_wiki_lexical":
                return [{"wrong": "shape"}]
            return _rows(function)

    result = await RetrievalService(FakeEmbeddingClient()).retrieve(
        uuid4(), "Hello WORLD", requested_k=2, user_db=PartialDb()
    )

    assert {hit.kind for hit in result.evidence} == {"source"}
    assert result.meta["wiki_vector"] == {
        **result.meta["wiki_vector"],
        "status": "failed",
        "error_code": "rpc_unavailable",
    }
    assert result.meta["wiki_lexical"]["status"] == "failed"
    assert "database internals" not in str(result.meta)


@pytest.mark.asyncio
async def test_cancellation_propagates() -> None:
    class CancelledEmbeddingClient:
        async def embed(self, text: str, *, workspace_id: str) -> list[float]:
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await RetrievalService(CancelledEmbeddingClient()).retrieve(
            uuid4(), "hello", requested_k=1, user_db=FourChannelDb()
        )


@pytest.mark.asyncio
async def test_graph_is_disabled_by_default_and_never_calls_its_rpc() -> None:
    calls: list[str] = []

    class NoGraphDb(FourChannelDb):
        async def rpc(self, function: str, *, params: dict[str, object]) -> list[dict[str, object]]:
            calls.append(function)
            return await super().rpc(function, params=params)

    result = await RetrievalService(FakeEmbeddingClient()).retrieve(
        uuid4(), "Hello WORLD", requested_k=4, user_db=NoGraphDb()
    )

    assert "expand_wiki_graph" not in calls
    assert result.meta["graph"]["status"] == "disabled"


@pytest.mark.asyncio
async def test_graph_uses_ordered_fused_wiki_seeds_and_refuses_first_wave_results() -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class GraphDb(FourChannelDb):
        async def rpc(self, function: str, *, params: dict[str, object]) -> list[dict[str, object]]:
            calls.append((function, params))
            if function == "expand_wiki_graph":
                return [
                    {"wiki_id": "wiki-c", "depth": 1},
                    {"wiki_id": "wiki-a", "depth": 0},
                ]
            return await super().rpc(function, params=params)

    policy = replace(DEFAULT_RETRIEVAL_POLICY, graph_enabled=True)
    result = await RetrievalService(FakeEmbeddingClient(), policy=policy).retrieve(
        uuid4(), "Hello WORLD", requested_k=4, user_db=GraphDb()
    )

    graph_call = next(params for function, params in calls if function == "expand_wiki_graph")
    assert graph_call["p_seed_wiki_ids"] == ["wiki-a", "wiki-b"]
    assert graph_call["p_fanout"] == 5
    assert graph_call["p_total_limit"] == 50
    wiki_a = next(hit for hit in result.evidence if hit.canonical_id == "wiki:wiki-a")
    assert {"wiki_vector", "graph"} <= set(wiki_a.contributions)
    assert result.meta["graph"]["status"] == "ok"


@pytest.mark.asyncio
async def test_graph_ranks_deterministically_by_seed_rank_then_hop_then_id() -> None:
    class GraphDb(FourChannelDb):
        async def rpc(self, function: str, *, params: dict[str, object]) -> list[dict[str, object]]:
            if function == "expand_wiki_graph":
                return [
                    {"wiki_id": "wiki-z", "depth": 2},
                    {"wiki_id": "wiki-c", "depth": 1},
                    {"wiki_id": "wiki-a", "depth": 0},
                    {"wiki_id": "wiki-b", "depth": 0},
                ]
            return await super().rpc(function, params=params)

    policy = replace(DEFAULT_RETRIEVAL_POLICY, graph_enabled=True, requested_k=8)
    result = await RetrievalService(FakeEmbeddingClient(), policy=policy).retrieve(
        uuid4(), "Hello WORLD", requested_k=8, user_db=GraphDb()
    )

    graph_hits = [hit for hit in result.evidence if "graph" in hit.contributions]
    assert [hit.canonical_id for hit in graph_hits] == [
        "wiki:wiki-a",
        "wiki:wiki-b",
        "wiki:wiki-c",
        "wiki:wiki-z",
    ]


@pytest.mark.asyncio
async def test_retrieval_route_declares_evidence_only_json_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(
        ApiSettings(SUPABASE_URL="http://supabase.test", SUPABASE_PUBLISHABLE_KEY="test-key"),
        git_sha="test",
    )

    class FakeService:
        async def retrieve(self, *args: object, **kwargs: object) -> RetrievalResult:
            return RetrievalResult(
                evidence=[EvidenceHit.source(chunk_id="chunk-a", rank=1)],
                meta={"policy_version": "test"},
            )

    app.state.retrieval_service = FakeService()
    workspace_id = uuid4()

    async def member(self: object, function: str, *, params: object) -> list[bool]:
        assert function == "has_workspace_role"
        return [True]

    monkeypatch.setattr(UserDb, "rpc", member)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": "Bearer requester-jwt"},
        ) as client:
            response = await client.post(
                f"/workspaces/{workspace_id}/retrieval", json={"query": "hello"}
            )

    assert response.headers["content-type"].startswith("application/json")
    assert set(response.json()) == {"evidence", "meta"}
    response_schema = app.openapi()["paths"]["/workspaces/{workspace_id}/retrieval"]["post"][
        "responses"
    ]
    assert "200" in response_schema
    assert "RetrievalResponse" in str(response_schema)
    assert all(field not in str(response_schema) for field in ("answer", "citations", "delta"))


@pytest.mark.asyncio
async def test_candidates_keep_hits_beyond_requested_k_for_dual_evidence_selection() -> None:
    """Ask의 이중 근거 선택이 이 값에 기댄다. 비면 조용히 상위 k개로 돌아가 위키 독점이 재발한다."""
    result = await RetrievalService(FakeEmbeddingClient()).retrieve(
        uuid4(), "Hello WORLD", requested_k=1, user_db=FourChannelDb()
    )

    assert len(result.evidence) == 1
    assert result.candidates[0] == result.evidence[0]
    assert {hit.kind for hit in result.candidates} == {"wiki", "source"}
