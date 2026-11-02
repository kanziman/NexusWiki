"""Private, worker-owned query-embedding HTTP boundary."""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Annotated

import structlog
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict

from nexuswiki_core.trace import TraceMiddleware, parse_trace_id
from worker.embedding import EMBEDDING_DIMENSIONS

EmbeddingFunction = Callable[[str], Awaitable[list[float]]]
MonotonicClock = Callable[[], float]

# ⚠️ 비용 귀속 값을 structlog 컨텍스트에서 읽지 않는다. 리스너는 `main`이 묶은
#    `workspace_id="bootstrap"`을 물려받으므로, 헤더가 없는 호출이 건너뛰지 않고 그 값으로 기록을
#    시도한다. 지금은 UUID가 아니라 실패할 뿐이지만, 진짜 ID가 묶이면 다른 테넌트로 조용히 귀속된다.
_request_workspace_id: ContextVar[str | None] = ContextVar(
    "query_embedding_workspace_id", default=None
)


def request_workspace_id() -> str | None:
    """이 요청의 헤더에서 검증한 워크스페이스. 없거나 형식이 틀리면 `None`이다."""
    return _request_workspace_id.get()


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
        x_workspace_id: Annotated[str | None, Header()] = None,
    ) -> QueryEmbeddingResponse:
        # 본문이 아니라 헤더로 받는다. 요청 모델이 `extra="forbid"`라 필드를 더하면 이전 버전 워커가
        # 새 API의 호출을 422로 거부한다 (ai-control-flow-accounting design D2, D5).
        workspace_id = parse_trace_id(x_workspace_id)
        token = _request_workspace_id.set(workspace_id)
        try:
            if workspace_id is None:
                return await service.embed(request, authorization)
            with structlog.contextvars.bound_contextvars(workspace_id=workspace_id):
                return await service.embed(request, authorization)
        finally:
            _request_workspace_id.reset(token)


def create_query_embedding_app(service: QueryEmbeddingService) -> FastAPI:
    """Small ASGI app intended for the Railway private network only.

    Kept as a thin wrapper so every existing call site (including
    `test_query_embedding.py`) keeps working unchanged.
    """
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    app.add_middleware(
        TraceMiddleware, log_event="worker.internal_request_completed", trust_inbound=True
    )
    add_query_embedding_route(app, service)
    return app
