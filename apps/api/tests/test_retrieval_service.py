import asyncio
from uuid import uuid4

import pytest

from api.services.retrieval import RetrievalService
from nexuswiki_core.retrieval_policy import DEFAULT_RETRIEVAL_POLICY


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        assert text == "hello world"
        return [0.0] * 1024


class FakeUserDb:
    async def rpc(self, function: str, *, params: dict[str, object]) -> list[dict[str, object]]:
        if function == "search_chunks":
            assert len(params["p_query"]) == 1024  # type: ignore[arg-type]
            return [
                {"id": "chunk-a", "raw_source_id": "source-a", "chunk_index": 0, "content": "hello"}
            ]
        if function == "search_source_lexical":
            assert params["p_bigrams"] == "he el ll lo wo or rl ld"
            return [
                {"id": "chunk-b", "raw_source_id": "source-b", "chunk_index": 0, "content": "world"}
            ]
        raise AssertionError(function)


@pytest.mark.asyncio
async def test_tracer_returns_evidence_and_safe_channel_meta() -> None:
    result = await RetrievalService(FakeEmbeddingClient()).retrieve(
        uuid4(), "Hello WORLD", requested_k=2, user_db=FakeUserDb()
    )

    assert [hit.canonical_id for hit in result.evidence] == ["source:chunk-a", "source:chunk-b"]
    assert result.meta["policy_version"] == DEFAULT_RETRIEVAL_POLICY.version
    assert result.meta["source_vector"]["status"] == "ok"
    assert result.meta["source_lexical"]["status"] == "ok"


@pytest.mark.asyncio
async def test_dense_failure_leaves_lexical_retrieval_successful() -> None:
    class FailingEmbeddingClient:
        async def embed(self, text: str) -> list[float]:
            raise RuntimeError("provider secret must not leak")

    class LexicalOnlyDb:
        async def rpc(self, function: str, *, params: dict[str, object]) -> list[dict[str, object]]:
            assert function == "search_source_lexical"
            return [
                {"id": "chunk-b", "raw_source_id": "source-b", "chunk_index": 0, "content": "world"}
            ]

    result = await RetrievalService(FailingEmbeddingClient()).retrieve(
        uuid4(), "Hello WORLD", requested_k=2, user_db=LexicalOnlyDb()
    )

    assert [hit.canonical_id for hit in result.evidence] == ["source:chunk-b"]
    assert result.meta["source_vector"]["status"] == "failed"
    assert result.meta["source_vector"]["error_code"] == "embedding_unavailable"
    assert result.meta["source_lexical"]["status"] == "ok"


@pytest.mark.asyncio
async def test_cancellation_propagates() -> None:
    class CancelledEmbeddingClient:
        async def embed(self, text: str) -> list[float]:
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await RetrievalService(CancelledEmbeddingClient()).retrieve(
            uuid4(), "hello", requested_k=1, user_db=FakeUserDb()
        )
