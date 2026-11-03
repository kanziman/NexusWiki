"""공통 LLM 정책과 위험한 위키 쓰기 통제 (ai-control-risk-policy, #197, #198)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from pydantic import BaseModel

from nexuswiki_core.llm_policy import (
    ASK_POLICY,
    LLM_POLICY_VERSION,
    STRUCTURED_POLICY,
    with_policy,
)
from nexuswiki_core.wiki_write_policy import WikiWriteRisk, classify_wiki_write
from worker import llm
from worker.handlers import resolve_handler
from worker.handlers.compile import run_compile
from worker.handlers.embed import run_embed
from worker.handlers.wiki_proposal_apply import (
    WIKI_PROPOSAL_APPLY_JOB_TYPE,
    handle_wiki_proposal_apply,
    run_wiki_proposal_apply,
)
from worker.llm_gateway import LlmCallContext, LlmGateway, record_stream_usage
from worker.settings import WorkerSettings


class _Payload(BaseModel):
    value: str


def _settings() -> WorkerSettings:
    return WorkerSettings(
        _env_file=None,
        SUPABASE_URL="https://example.invalid",
        SUPABASE_PUBLISHABLE_KEY="sb_publishable_test",
        SUPABASE_SECRET_KEY="sb_secret_test",  # noqa: S106 - 테스트 픽스처
        DATABASE_URL="postgresql://postgres:pw@127.0.0.1:54422/postgres",
        OPENROUTER_API_KEY="sk-or-v1-test",
        LLM_MODEL="test-model",
        EMBEDDING_MODEL="baai/bge-m3",
        EMBEDDING_PROVIDER="deepinfra/fp32",
    )


def _client(handler: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url="https://x.invalid", transport=httpx.MockTransport(handler))


def _ok(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2, "cost": 0.001},
            "provider": "Anthropic",
            "model": "m",
        },
    )


def test_with_policy_prepends_without_mutating_input() -> None:
    messages = [{"role": "system", "content": "템플릿"}, {"role": "user", "content": "질문"}]
    result = with_policy(messages, "정책")
    assert result[0]["content"] == "정책\n\n템플릿"
    assert messages[0]["content"] == "템플릿"


def test_with_policy_creates_a_system_turn_when_the_template_has_none() -> None:
    result = with_policy([{"role": "user", "content": "질문"}], "정책")
    assert result[0] == {"role": "system", "content": "정책"}


@pytest.mark.asyncio
async def test_structured_call_carries_policy_and_data_collection_deny() -> None:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return _ok('{"value": "가"}')

    async with _client(handler) as client:
        await llm.complete_structured(
            client,
            settings=_settings(),
            system_prompt="템플릿",
            user_prompt="u",
            schema_model=_Payload,
        )
    assert bodies[0]["messages"][0]["content"].startswith(STRUCTURED_POLICY)
    assert bodies[0]["provider"] == {"data_collection": "deny", "require_parameters": True}


@pytest.mark.asyncio
async def test_prompt_only_fallback_keeps_data_collection_deny() -> None:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        if len(bodies) == 1:
            return httpx.Response(400, json={})
        return _ok('{"value": "가"}')

    async with _client(handler) as client:
        await llm.complete_structured(
            client,
            settings=_settings(),
            system_prompt="템플릿",
            user_prompt="u",
            schema_model=_Payload,
        )
    assert "response_format" not in bodies[1]
    assert bodies[1]["provider"] == {"data_collection": "deny"}


def test_stream_body_carries_ask_policy_even_for_a_template_without_citation_rules() -> None:
    body = llm._chat_stream_body(
        settings=_settings(),
        messages=[{"role": "system", "content": "인용 규칙 없는 템플릿"}],
    )
    assert body["messages"][0]["content"].startswith(ASK_POLICY)
    assert "[[wiki:w1]]" in body["messages"][0]["content"]
    assert "자료" in body["messages"][0]["content"]
    assert body["provider"] == {"data_collection": "deny"}


class _Sink:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    async def insert_usage_event(self, *, workspace_id: str, row: dict[str, Any]) -> None:
        self.rows.append(row)


@pytest.mark.asyncio
async def test_policy_version_is_recorded_on_every_call_path() -> None:
    sink = _Sink()
    async with _client(lambda _: _ok('{"value": "가"}')) as client:
        await LlmGateway(sink, client, _settings()).complete_structured(
            LlmCallContext(workspace_id="ws", call="compile"),
            system_prompt="s",
            user_prompt="u",
            schema_model=_Payload,
        )
    await record_stream_usage(
        sink,
        LlmCallContext(workspace_id="ws", call="ask"),
        usage={"prompt_tokens": 1},
        duration_ms=1,
        incomplete=False,
    )
    assert [row["metadata"]["policy_version"] for row in sink.rows] == [LLM_POLICY_VERSION] * 2


@pytest.mark.parametrize(
    ("existing", "new_content", "published", "risk", "reason", "changed"),
    [
        (None, "새 본문", False, WikiWriteRisk.LOW, "new_page", False),
        ({"content": "같음"}, "같음", False, WikiWriteRisk.LOW, "unchanged", False),
        (
            {"content": "같음", "verification_status": "verified"},
            "같음",
            True,
            WikiWriteRisk.LOW,
            "unchanged",
            False,
        ),
        (
            {"content": "이전", "verification_status": "verified"},
            "새 본문",
            False,
            WikiWriteRisk.HIGH,
            "verified_page",
            True,
        ),
        ({"content": "이전"}, "새 본문", True, WikiWriteRisk.HIGH, "published_page", True),
        (
            {"content": "이전", "sources": ["other", "rs"]},
            "새 본문",
            False,
            WikiWriteRisk.MEDIUM,
            "other_source_page",
            True,
        ),
        (
            {"content": "가" * 100, "sources": ["rs"]},
            "가" * 50,
            False,
            WikiWriteRisk.MEDIUM,
            "large_shrink",
            True,
        ),
        (
            {"content": "이전 본문", "sources": ["rs"]},
            "바뀐 본문입니다",
            False,
            WikiWriteRisk.LOW,
            "same_source_update",
            True,
        ),
    ],
)
def test_write_classification(
    existing: dict[str, Any] | None,
    new_content: str,
    published: bool,
    risk: WikiWriteRisk,
    reason: str,
    changed: bool,
) -> None:
    decision = classify_wiki_write(
        existing, new_content=new_content, raw_source_id="rs", published=published
    )
    assert (decision.risk, decision.reason, decision.changed) == (risk, reason, changed)


class _WikiDb(_Sink):
    def __init__(self, page: dict[str, Any] | None, *, published: bool = False) -> None:
        super().__init__()
        self.page = page
        self.published = published
        self.upserts: list[dict[str, Any]] = []
        self.revisions: list[dict[str, Any]] = []
        self.proposals: list[dict[str, Any]] = []
        self.evidence: list[dict[str, Any]] = []
        self.chained: list[dict[str, Any]] = []

    async def get_raw_source(self, _id: str, *, workspace_id: str) -> dict[str, str]:
        return {"title": "원문", "source_type": "text"}

    async def get_default_prompt_template(self, **_: str) -> dict[str, str]:
        return {"id": "t", "system_prompt": "s", "template": "{{source_content}}"}

    async def list_wiki_slugs(self, **_: str) -> list[str]:
        return []

    async def list_source_chunks(self, **_: str) -> list[dict[str, str]]:
        return [{"id": "chunk-1", "content": "청크"}]

    async def latest_compile_fingerprint(self, **_: str) -> None:
        return None

    async def get_wiki_page_by_slug(self, **_: str) -> dict[str, Any] | None:
        return self.page

    async def is_wiki_page_published(self, **_: str) -> bool:
        return self.published

    async def upsert_wiki_page(self, *, workspace_id: str, row: dict[str, Any]) -> dict[str, str]:
        self.upserts.append(row)
        return {"id": "wiki-1"}

    async def index_wiki_page_lexical(self, **_: Any) -> None:
        return None

    async def insert_wiki_page_revision(self, *, workspace_id: str, row: dict[str, Any]) -> None:
        self.revisions.append(row)

    async def upsert_wiki_write_proposal(self, **values: Any) -> None:
        self.proposals.append(values)

    async def replace_wiki_page_evidence(self, **values: Any) -> None:
        self.evidence.append(values)

    async def complete_job_and_chain(self, _job_id: str, **values: Any) -> None:
        self.chained.append(values)


async def _compile(db: _WikiDb, *, mode: str) -> None:
    page = {
        "title": "제목",
        "category": "concepts",
        "confidence": "high",
        "content": "새 본문입니다",
        "evidence": ["s1"],
    }
    answer = json.dumps({"pages": [page]}, ensure_ascii=False)
    async with _client(lambda _: _ok(answer)) as client:
        await run_compile(
            db,
            client,
            settings=SimpleNamespace(
                LLM_MODEL="m",
                COMPILE_MAX_INPUT_TOKENS=24000,
                COMPILE_MAX_PAGES=8,
                AI_CONTROL_RISK_MODE=mode,
            ),
            job_id="job-1",
            workspace_id="ws",
            payload={"raw_source_id": "rs"},
        )


def _verified_page(**overrides: Any) -> dict[str, Any]:
    return {
        "id": "wiki-1",
        "slug": "slug",
        "title": "이전 제목",
        "content": "사람이 검증한 본문",
        "verification_status": "verified",
        "sources": ["rs"],
        **overrides,
    }


@pytest.mark.asyncio
async def test_enforce_holds_verified_page_and_job_succeeds() -> None:
    db = _WikiDb(_verified_page())
    await _compile(db, mode="enforce")
    assert db.upserts == []
    assert db.revisions == []
    assert db.evidence == []
    assert db.proposals[0]["risk_reason"] == "verified_page"
    assert db.proposals[0]["evidence_chunk_ids"] == ["chunk-1"]
    assert db.chained[0]["next_type"] == "link_sync"


@pytest.mark.asyncio
async def test_shadow_writes_but_records_high_risk_revision_before_overwriting() -> None:
    db = _WikiDb(_verified_page())
    await _compile(db, mode="shadow")
    assert db.proposals == []
    assert db.upserts[0]["content"] == "새 본문입니다"
    assert db.revisions[0]["risk_level"] == "high"
    assert db.revisions[0]["previous_content"] == "사람이 검증한 본문"
    assert db.revisions[0]["job_id"] == "job-1"


@pytest.mark.asyncio
async def test_off_skips_classification() -> None:
    db = _WikiDb(_verified_page())
    await _compile(db, mode="off")
    assert db.revisions == []
    assert db.proposals == []
    assert len(db.upserts) == 1


@pytest.mark.asyncio
async def test_unchanged_body_leaves_no_revision_or_proposal() -> None:
    db = _WikiDb(
        _verified_page(
            content="새 본문입니다",
            title="제목",
            category="concepts",
            aliases=[],
            confidence="high",
        )
    )
    await _compile(db, mode="enforce")
    assert db.revisions == []
    assert db.proposals == []
    assert len(db.upserts) == 1


@pytest.mark.asyncio
async def test_new_page_has_no_revision() -> None:
    db = _WikiDb(None)
    await _compile(db, mode="enforce")
    assert db.revisions == []
    assert db.proposals == []
    assert len(db.upserts) == 1


class _ApplyDb(_WikiDb):
    def __init__(self, status: str) -> None:
        super().__init__(_verified_page(sources=["other"]))
        self.indexed: list[dict[str, Any]] = []
        self.marked: list[str] = []
        self.proposal: dict[str, Any] = {
            "id": "p-1",
            "wiki_id": "wiki-1",
            "raw_source_id": "rs",
            "status": status,
            "proposed_title": "제안 제목",
            "proposed_category": "concepts",
            "proposed_aliases": ["별칭"],
            "proposed_confidence": "high",
            "proposed_content": "제안 본문",
            "evidence_chunk_ids": ["chunk-1"],
        }

    async def get_wiki_write_proposal(self, *_: str, **__: str) -> dict[str, Any]:
        return self.proposal

    async def get_wiki_page(self, *_: str, **__: str) -> dict[str, Any] | None:
        return self.page

    async def index_wiki_page_lexical(self, **values: Any) -> None:
        self.indexed.append(values)

    async def mark_wiki_write_proposal_applied(self, proposal_id: str, **_: str) -> None:
        self.marked.append(proposal_id)


@pytest.mark.asyncio
async def test_approved_proposal_applies_with_revision_index_and_chain() -> None:
    db = _ApplyDb("approved")
    await run_wiki_proposal_apply(
        db, job_id="job-2", workspace_id="ws", payload={"proposal_id": "p-1"}
    )
    assert db.revisions[0]["previous_content"] == "사람이 검증한 본문"
    assert db.revisions[0]["reason"] == "approved_proposal"
    row = db.upserts[0]
    assert row["slug"] == "slug"
    assert row["content"] == "제안 본문"
    assert row["sources"] == ["other", "rs"]
    assert "verification_status" not in row
    assert db.indexed[0]["wiki_id"] == "wiki-1"
    assert db.evidence[0]["chunk_ids"] == ["chunk-1"]
    assert db.marked == ["p-1"]
    assert db.chained[0]["next_type"] == "link_sync"


@pytest.mark.parametrize("status", ["rejected", "pending"])
@pytest.mark.asyncio
async def test_undecided_or_rejected_proposal_is_a_no_op(status: str) -> None:
    db = _ApplyDb(status)
    await run_wiki_proposal_apply(
        db, job_id="job-2", workspace_id="ws", payload={"proposal_id": "p-1"}
    )
    assert db.upserts == []
    assert db.revisions == []
    assert db.chained == [{}]


@pytest.mark.asyncio
async def test_rerun_after_applied_restores_the_chain_without_rewriting() -> None:
    """적용 표시 뒤 체인 등록 전에 죽으면 재실행이 체인을 이어야 색인이 이전 본문에 남지 않는다."""
    db = _ApplyDb("applied")
    await run_wiki_proposal_apply(
        db, job_id="job-2", workspace_id="ws", payload={"proposal_id": "p-1"}
    )
    assert db.upserts == []
    assert db.revisions == []
    assert db.chained[0]["next_type"] == "link_sync"
    assert db.chained[0]["next_payload"]["raw_source_id"] == "rs"


@pytest.mark.parametrize(
    "existing",
    [{"verification_status": "verified"}, {"verification_status": "unverified"}],
    ids=["verified", "published"],
)
def test_metadata_change_on_protected_pages_is_high_risk(existing: dict[str, Any]) -> None:
    decision = classify_wiki_write(
        {"content": "같음", **existing},
        new_content="같음",
        raw_source_id="rs",
        published=existing["verification_status"] != "verified",
        metadata_changed=True,
    )
    assert decision.risk == WikiWriteRisk.HIGH
    assert decision.changed is True


def test_metadata_change_on_plain_pages_is_not_a_revision() -> None:
    decision = classify_wiki_write(
        {"content": "같음"},
        new_content="같음",
        raw_source_id="rs",
        published=False,
        metadata_changed=True,
    )
    assert decision.changed is False


@pytest.mark.asyncio
async def test_enforce_holds_metadata_only_change_on_verified_page() -> None:
    db = _WikiDb(
        _verified_page(
            content="새 본문입니다",
            title="제목",
            category="entities",
            aliases=[],
            confidence="high",
        )
    )
    await _compile(db, mode="enforce")
    assert db.upserts == []
    assert db.proposals[0]["category"] == "concepts"


@pytest.mark.asyncio
async def test_shadow_metadata_only_change_does_not_create_revision() -> None:
    db = _WikiDb(_verified_page(content="새 본문입니다"))
    await _compile(db, mode="shadow")
    assert db.revisions == []
    assert db.proposals == []
    assert db.upserts[0]["title"] == "제목"
    assert db.upserts[0]["content"] == "새 본문입니다"


@pytest.mark.asyncio
async def test_approved_metadata_only_change_applies_without_revision() -> None:
    db = _ApplyDb("approved")
    db.proposal["proposed_content"] = "사람이 검증한 본문"
    await run_wiki_proposal_apply(
        db, job_id="job-2", workspace_id="ws", payload={"proposal_id": "p-1"}
    )
    assert db.revisions == []
    assert db.upserts[0]["title"] == "제안 제목"
    assert db.upserts[0]["content"] == "사람이 검증한 본문"
    assert db.marked == ["p-1"]
    assert db.indexed[0]["wiki_id"] == "wiki-1"
    assert db.chained[0]["next_type"] == "link_sync"


@pytest.mark.asyncio
async def test_other_source_update_records_a_medium_revision() -> None:
    db = _WikiDb(_verified_page(verification_status="unverified", sources=["other"]))
    await _compile(db, mode="enforce")
    assert db.proposals == []
    assert db.revisions[0]["risk_level"] == "medium"
    assert db.revisions[0]["reason"] == "other_source_page"
    assert len(db.upserts) == 1


def test_apply_job_type_is_registered() -> None:
    assert resolve_handler(WIKI_PROPOSAL_APPLY_JOB_TYPE) is handle_wiki_proposal_apply


class _EmbedDb:
    def __init__(self, stored: list[dict[str, Any]]) -> None:
        self.stored = stored
        self.upserted: list[dict[str, Any]] = []

    async def list_wiki_pages_for_source(self, **_: Any) -> list[dict[str, str]]:
        return [{"id": "wiki-1", "content": "바뀐 본문입니다"}]

    async def list_wiki_embeddings(self, **_: Any) -> list[dict[str, Any]]:
        return self.stored

    async def upsert_wiki_embeddings(self, *, rows: Any, **_: Any) -> None:
        self.upserted.extend(rows)

    async def delete_wiki_embeddings_from(self, **_: Any) -> None:
        return None

    async def insert_usage_event(self, **_: Any) -> None:
        return None

    async def complete_job_and_chain(self, *_: Any, **__: Any) -> None:
        return None


async def _embed(db: _EmbedDb) -> int:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        texts = json.loads(request.content)["input"]
        return httpx.Response(
            200,
            json={
                "data": [{"embedding": [0.0] * 1024} for _ in texts],
                "usage": {"prompt_tokens": 1, "total_tokens": 1},
                "model": "baai/bge-m3",
                "provider": "DeepInfra",
            },
        )

    async with _client(handler) as client:
        await run_embed(
            db,
            client,
            settings=_settings(),
            job_id="job-1",
            workspace_id="ws",
            payload={"raw_source_id": "rs", "scope": "wiki"},
        )
    return calls


@pytest.mark.asyncio
async def test_changed_wiki_body_is_reembedded_even_when_the_index_exists() -> None:
    """번호만 비교하면 벡터 채널이 승인이나 재컴파일 전 본문으로 계속 검색된다."""
    db = _EmbedDb([{"chunk_index": 0, "chunk_content": "이전 본문"}])
    assert await _embed(db) == 1
    assert db.upserted[0]["chunk_content"] == "바뀐 본문입니다"


@pytest.mark.asyncio
async def test_unchanged_wiki_body_is_not_reembedded() -> None:
    db = _EmbedDb([{"chunk_index": 0, "chunk_content": "바뀐 본문입니다"}])
    assert await _embed(db) == 0
