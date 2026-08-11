import asyncio

import httpx
import pytest
from fastapi import HTTPException

from worker.query_embedding import (
    QueryEmbeddingRequest,
    QueryEmbeddingService,
    create_query_embedding_app,
)

_INTERNAL_TOKEN = "test-internal-token"  # noqa: S105 - non-secret test fixture


class MonotonicClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


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


@pytest.mark.asyncio
async def test_token_bucket_refills_after_exhaustion_without_restart() -> None:
    clock = MonotonicClock()
    calls = 0

    async def embed(text: str) -> list[float]:
        nonlocal calls
        calls += 1
        return [0.0] * 1024

    service = QueryEmbeddingService(
        embed,
        internal_token=_INTERNAL_TOKEN,
        rate_capacity=2,
        refill_tokens_per_second=0.5,
        monotonic=clock,
    )
    request = QueryEmbeddingRequest(text="hello")
    authorization = f"Bearer {_INTERNAL_TOKEN}"

    await service.embed(request, authorization)
    await service.embed(request, authorization)
    with pytest.raises(Exception) as exhausted:
        await service.embed(request, authorization)
    assert "429" in str(exhausted.value)

    clock.advance(1.9)
    with pytest.raises(HTTPException) as partial:
        await service.embed(request, authorization)
    assert partial.value.status_code == 429
    clock.advance(0.1)
    await service.embed(request, authorization)

    clock.advance(100)
    await service.embed(request, authorization)
    await service.embed(request, authorization)
    with pytest.raises(Exception) as capped:
        await service.embed(request, authorization)
    assert "429" in str(capped.value)

    assert calls == 5


@pytest.mark.asyncio
async def test_invalid_requests_do_not_consume_quota_but_provider_attempts_do() -> None:
    clock = MonotonicClock()

    async def failing_embed(text: str) -> list[float]:
        raise RuntimeError("provider unavailable")

    service = QueryEmbeddingService(
        failing_embed,
        internal_token=_INTERNAL_TOKEN,
        rate_capacity=1,
        refill_tokens_per_second=1,
        monotonic=clock,
    )
    request = QueryEmbeddingRequest(text="hello")

    with pytest.raises(Exception) as unauthorized:
        await service.embed(request, None)
    assert "401" in str(unauthorized.value)
    with pytest.raises(Exception) as invalid:
        await service.embed(QueryEmbeddingRequest(text=""), f"Bearer {_INTERNAL_TOKEN}")
    assert "422" in str(invalid.value)

    with pytest.raises(Exception) as provider_failure:
        await service.embed(request, f"Bearer {_INTERNAL_TOKEN}")
    assert "502" in str(provider_failure.value)
    with pytest.raises(Exception) as exhausted:
        await service.embed(request, f"Bearer {_INTERNAL_TOKEN}")
    assert "429" in str(exhausted.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["timeout", "malformed", "cancelled"])
async def test_every_begun_provider_attempt_consumes_a_token(
    outcome: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = MonotonicClock()

    async def embed(text: str) -> list[float]:
        if outcome == "cancelled":
            raise asyncio.CancelledError
        if outcome == "malformed":
            return [0.0]
        return [0.0] * 1024

    service = QueryEmbeddingService(
        embed,
        internal_token=_INTERNAL_TOKEN,
        rate_capacity=1,
        refill_tokens_per_second=1,
        monotonic=clock,
    )
    request = QueryEmbeddingRequest(text="hello")
    authorization = f"Bearer {_INTERNAL_TOKEN}"
    if outcome == "timeout":

        async def timeout(*args: object, **kwargs: object) -> list[float]:
            args[0].close()  # type: ignore[union-attr]
            raise TimeoutError

        monkeypatch.setattr("worker.query_embedding.asyncio.wait_for", timeout)

    if outcome == "cancelled":
        with pytest.raises(asyncio.CancelledError):
            await service.embed(request, authorization)
    else:
        with pytest.raises(HTTPException):
            await service.embed(request, authorization)
    with pytest.raises(Exception) as exhausted:
        await service.embed(request, authorization)
    assert "429" in str(exhausted.value)


@pytest.mark.asyncio
async def test_exhausted_bucket_admits_only_one_parallel_contender_after_refill() -> None:
    clock = MonotonicClock()

    async def embed(text: str) -> list[float]:
        return [0.0] * 1024

    service = QueryEmbeddingService(
        embed,
        internal_token=_INTERNAL_TOKEN,
        rate_capacity=1,
        refill_tokens_per_second=1,
        monotonic=clock,
    )
    request = QueryEmbeddingRequest(text="hello")
    authorization = f"Bearer {_INTERNAL_TOKEN}"
    await service.embed(request, authorization)
    clock.advance(1)

    results = await asyncio.gather(
        service.embed(request, authorization),
        service.embed(request, authorization),
        return_exceptions=True,
    )

    assert sum(isinstance(result, Exception) for result in results) == 1
