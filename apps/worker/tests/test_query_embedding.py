import httpx
import pytest

from worker.query_embedding import (
    QueryEmbeddingRequest,
    QueryEmbeddingService,
    create_query_embedding_app,
)

_INTERNAL_TOKEN = "test-internal-token"  # noqa: S105 - non-secret test fixture


@pytest.mark.asyncio
async def test_private_endpoint_rejects_missing_token_before_embedding() -> None:
    calls = 0

    async def embed(text: str) -> list[float]:
        nonlocal calls
        calls += 1
        return [0.0] * 1024

    app = create_query_embedding_app(QueryEmbeddingService(embed, internal_token=_INTERNAL_TOKEN))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/internal/query-embedding", json={"text": "hello"})

    assert response.status_code == 401
    assert calls == 0


@pytest.mark.asyncio
async def test_authenticated_endpoint_returns_only_valid_vector() -> None:
    async def embed(text: str) -> list[float]:
        return [0.0] * 1024

    app = create_query_embedding_app(QueryEmbeddingService(embed, internal_token=_INTERNAL_TOKEN))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/internal/query-embedding",
            json={"text": "hello"},
            headers={"Authorization": f"Bearer {_INTERNAL_TOKEN}"},
        )

    assert response.status_code == 200
    assert list(response.json()) == ["vector"]
    assert len(response.json()["vector"]) == 1024


@pytest.mark.asyncio
async def test_provider_error_is_redacted() -> None:
    async def embed(text: str) -> list[float]:
        raise RuntimeError("provider token: secret")

    service = QueryEmbeddingService(embed, internal_token=_INTERNAL_TOKEN)
    with pytest.raises(Exception) as error:
        await service.embed(QueryEmbeddingRequest(text="hello"), f"Bearer {_INTERNAL_TOKEN}")

    assert "secret" not in str(error.value)
