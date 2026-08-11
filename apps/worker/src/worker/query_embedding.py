"""Private, worker-owned query-embedding HTTP boundary."""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict

from worker.embedding import EMBEDDING_DIMENSIONS

EmbeddingFunction = Callable[[str], Awaitable[list[float]]]
MonotonicClock = Callable[[], float]


class QueryEmbeddingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str


class QueryEmbeddingResponse(BaseModel):
    vector: list[float]


class QueryEmbeddingService:
    """Binds authenticated, bounded requests to an injected worker embedder."""

    def __init__(
        self,
        embed: EmbeddingFunction,
        *,
        internal_token: str,
        max_text_chars: int = 10_000,
        timeout_seconds: float = 5.0,
        max_concurrency: int = 4,
        rate_capacity: int = 100,
        refill_tokens_per_second: float = 1.0,
        monotonic: MonotonicClock = time.monotonic,
    ) -> None:
        if not internal_token:
            raise ValueError("internal token is required")
        if (
            min(
                max_text_chars,
                timeout_seconds,
                max_concurrency,
                rate_capacity,
                refill_tokens_per_second,
            )
            <= 0
        ):
            raise ValueError("query embedding bounds must be positive")
        self._embed = embed
        self._internal_token = internal_token
        self._max_text_chars = max_text_chars
        self._timeout_seconds = timeout_seconds
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._rate_capacity = rate_capacity
        self._refill_tokens_per_second = refill_tokens_per_second
        self._monotonic = monotonic
        self._tokens = float(rate_capacity)
        self._last_refill = monotonic()
        self._request_lock = asyncio.Lock()

    async def _reserve_token(self) -> None:
        """Reserve one provider-attempt token, refilling from a monotonic clock."""
        async with self._request_lock:
            now = self._monotonic()
            elapsed = max(0.0, now - self._last_refill)
            self._tokens = min(
                float(self._rate_capacity),
                self._tokens + elapsed * self._refill_tokens_per_second,
            )
            # A clock cannot normally go backwards, but retaining the later value
            # makes a faulty injected clock unable to mint quota by oscillating.
            self._last_refill = max(self._last_refill, now)
            if self._tokens < 1:
                raise HTTPException(status_code=429, detail="rate_limited")
            self._tokens -= 1

    async def embed(
        self, request: QueryEmbeddingRequest, authorization: str | None
    ) -> QueryEmbeddingResponse:
        # Authenticate before quota/provider work, so unauthenticated calls cannot
        # consume capacity.
        if authorization != f"Bearer {self._internal_token}":
            raise HTTPException(status_code=401, detail="internal_unauthorized")
        if not request.text or len(request.text) > self._max_text_chars:
            raise HTTPException(status_code=422, detail="invalid_query")
        # A reservation covers every valid provider attempt, including failures,
        # timeouts, malformed output, and cancellation after work has begun.
        await self._reserve_token()
        try:
            async with self._semaphore:
                vector = await asyncio.wait_for(
                    self._embed(request.text), timeout=self._timeout_seconds
                )
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            raise HTTPException(status_code=504, detail="embedding_unavailable") from None
        except Exception:
            # Provider bodies and exception strings are not caller-visible.
            raise HTTPException(status_code=502, detail="embedding_unavailable") from None
        if len(vector) != EMBEDDING_DIMENSIONS or not all(
            math.isfinite(float(value)) for value in vector
        ):
            raise HTTPException(status_code=502, detail="embedding_unavailable")
        return QueryEmbeddingResponse(vector=[float(value) for value in vector])


def add_query_embedding_route(app: FastAPI, service: QueryEmbeddingService) -> None:
    """Register `POST /internal/query-embedding` on an existing app.

    Extracted from `create_query_embedding_app` (05-01-PLAN.md Task 1) so the worker's
    private listener can host this route alongside `/internal/llm-chat` on one
    `FastAPI` app / one `uvicorn.Server`, instead of a second app on a second port.
    """

    @app.post("/internal/query-embedding", response_model=QueryEmbeddingResponse)
    async def query_embedding(
        request: QueryEmbeddingRequest,
        authorization: Annotated[str | None, Header()] = None,
    ) -> QueryEmbeddingResponse:
        return await service.embed(request, authorization)


def create_query_embedding_app(service: QueryEmbeddingService) -> FastAPI:
    """Small ASGI app intended for the Railway private network only.

    Kept as a thin wrapper so every existing call site (including
    `test_query_embedding.py`) keeps working unchanged.
    """
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    add_query_embedding_route(app, service)
    return app
