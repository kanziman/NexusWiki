"""Private, worker-owned LLM-chat-streaming HTTP boundary.

관련 태스크: 05-01-PLAN.md Task 1
설계 근거: 05-CONTEXT.md > D-01 (LLM 호출 전송 경계, query-embedding 경계를 그대로 미러링)
설계 근거: docs/architecture/query-embedding-boundary.md (필수 불변식 + 레이트리밋 결정)

`worker.query_embedding`의 형태를 그대로 따른다 — `Service` 클래스 + `add_*_route` +
토큰 버킷 + bearer 인증. 두 리스너는 같은 `FastAPI` 앱/같은 `uvicorn.Server`에 함께
올라간다(`railway.json`의 private-networking 토글은 서비스 단위이지 포트 단위가 아니다).

⚠️ 이 서비스의 토큰 버킷은 `_reserve_token()` — 프로세스 수명 카운터가 **아니다**.
docs/architecture/query-embedding-boundary.md가 문서화한 커밋 `6a14144`의 버그를
다시 들여오지 않는다.

예산 상한 확인과 `usage_events` 기록은 이 태스크의 범위 밖이다(05-04-PLAN.md가
`stream()` 위에 얹는다) — 여기서 `ServiceDb`/`service_client`를 끌어오지 않는다.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

__all__ = [
    "ChatStreamFunction",
    "LlmChatRequest",
    "LlmStreamService",
    "add_llm_stream_route",
]

ChatStreamFunction = Callable[["LlmChatRequest"], AsyncIterator[bytes]]
MonotonicClock = Callable[[], float]


class LlmChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    workspace_id: str
    messages: list[dict[str, str]]


class LlmStreamService:
    """인증된, 대역폭이 제한된 요청을 주입된 스트리밍 채팅 함수에 묶는다."""

    def __init__(
        self,
        chat_stream: ChatStreamFunction,
        *,
        internal_token: str,
        max_concurrency: int = 2,
        rate_capacity: int = 20,
        refill_tokens_per_second: float = 0.2,
        monotonic: MonotonicClock = time.monotonic,
    ) -> None:
        if not internal_token:
            raise ValueError("internal token is required")
        if min(max_concurrency, rate_capacity, refill_tokens_per_second) <= 0:
            raise ValueError("llm stream bounds must be positive")
        self._chat_stream = chat_stream
        self._internal_token = internal_token
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._rate_capacity = rate_capacity
        self._refill_tokens_per_second = refill_tokens_per_second
        self._monotonic = monotonic
        self._tokens = float(rate_capacity)
        self._last_refill = monotonic()
        self._request_lock = asyncio.Lock()

    async def _reserve_token(self) -> None:
        """토큰 하나를 예약한다 — 단조 시계 기반 리필. 프로세스 수명 카운터가 아니다."""
        async with self._request_lock:
            now = self._monotonic()
            elapsed = max(0.0, now - self._last_refill)
            self._tokens = min(
                float(self._rate_capacity),
                self._tokens + elapsed * self._refill_tokens_per_second,
            )
            self._last_refill = max(self._last_refill, now)
            if self._tokens < 1:
                raise HTTPException(status_code=429, detail="rate_limited")
            self._tokens -= 1

    async def stream(
        self, request: LlmChatRequest, authorization: str | None
    ) -> AsyncIterator[bytes]:
        """인증 + quota 예약을 마친 뒤 청크 제너레이터를 돌려준다.

        ⚠️ 이 메서드 자체는 `yield`가 없는 평범한 코루틴이다 — 의도적이다. Starlette의
        `StreamingResponse`는 본문 이터레이터를 돌리기 **전에** 이미 `http.response.start`를
        전송하므로, 인증 실패를 제너레이터 안에서 `raise`하면 헤더가 이미 나간 뒤라
        401/429가 아니라 "response already started" `RuntimeError`로 깨진다(실측 확인).
        그래서 인증·quota 예약은 라우터가 `await`하는 이 코루틴 몸통에서 끝내고,
        실제 스트리밍은 별도의 `_stream_chunks`(순수 제너레이터)가 맡는다.
        """
        # 인증이 quota/provider 작업보다 먼저다 — query_embedding.py와 같은 계약.
        if authorization != f"Bearer {self._internal_token}":
            raise HTTPException(status_code=401, detail="internal_unauthorized")
        await self._reserve_token()
        return self._stream_chunks(request)

    async def _stream_chunks(self, request: LlmChatRequest) -> AsyncIterator[bytes]:
        async with self._semaphore:
            async for chunk in self._chat_stream(request):
                yield chunk


def add_llm_stream_route(app: FastAPI, service: LlmStreamService) -> None:
    """`POST /internal/llm-chat`를 기존 앱에 등록한다 (query-embedding과 같은 process/port)."""

    @app.post("/internal/llm-chat")
    async def llm_chat(
        request: LlmChatRequest,
        authorization: Annotated[str | None, Header()] = None,
    ) -> StreamingResponse:
        chunks = await service.stream(request, authorization)
        return StreamingResponse(chunks, media_type="text/event-stream")
