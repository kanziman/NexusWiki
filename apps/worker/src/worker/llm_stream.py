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
import json
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated, Any, Protocol

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, PrivateAttr

from nexuswiki_core.logging import get_logger
from worker.ask_cost import AskCostAccounting

__all__ = [
    "ChatStreamFunction",
    "LlmChatRequest",
    "LlmStreamService",
    "add_llm_stream_route",
]

_logger = get_logger(__name__)

ChatStreamFunction = Callable[["LlmChatRequest"], AsyncIterator[bytes]]
BudgetCheck = Callable[[str], Awaitable[bool]]


class UsageRecorder(Protocol):
    """스트림 한 건의 사용량 기록. `incomplete`면 최종 사용량을 받지 못한 호출이다."""

    def __call__(
        self, workspace_id: str, usage: dict[str, Any], *, incomplete: bool, duration_ms: int
    ) -> Awaitable[None]: ...


MonotonicClock = Callable[[], float]


class LlmChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    workspace_id: str
    messages: list[dict[str, str]]
    evidence_research: bool = False
    _cost_call: dict[str, Any] | None = PrivateAttr(default=None)
    _on_generation: Callable[[str], Awaitable[None]] | None = PrivateAttr(default=None)


class LlmStreamService:
    """인증된, 대역폭이 제한된 요청을 주입된 스트리밍 채팅 함수에 묶는다."""

    def __init__(
        self,
        chat_stream: ChatStreamFunction,
        *,
        internal_token: str,
        check_budget: BudgetCheck,
        record_usage: UsageRecorder,
        max_concurrency: int = 2,
        rate_capacity: int = 20,
        refill_tokens_per_second: float = 0.2,
        monotonic: MonotonicClock = time.monotonic,
        accounting: AskCostAccounting | None = None,
    ) -> None:
        if not internal_token:
            raise ValueError("internal token is required")
        if min(max_concurrency, rate_capacity, refill_tokens_per_second) <= 0:
            raise ValueError("llm stream bounds must be positive")
        self._chat_stream = chat_stream
        self._accounting = accounting
        self._check_budget = check_budget
        self._record_usage = record_usage
        self._internal_token = internal_token
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._rate_capacity = rate_capacity
        self._refill_tokens_per_second = refill_tokens_per_second
        self._monotonic = monotonic
        self._tokens = float(rate_capacity)
        self._last_refill = monotonic()
        self._request_lock = asyncio.Lock()
        # 취소된 스트림의 기록 태스크가 GC로 사라지지 않게 강한 참조를 유지한다.
        self._pending_records: set[asyncio.Task[None]] = set()

    def pending_records(self) -> set[asyncio.Task[None]]:
        """아직 끝나지 않은 사용량 기록. 종료 경로가 프로세스를 내리기 전에 기다린다."""
        return set(self._pending_records)

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
        if self._accounting is None and not await self._check_budget(request.workspace_id):
            raise HTTPException(status_code=402, detail="budget_exceeded")
        await self._reserve_token()
        if self._accounting is not None:
            request._cost_call = await self._accounting.reserve(
                request.workspace_id, request.messages
            )
        return self._stream_chunks(request)

    async def _stream_chunks(self, request: LlmChatRequest) -> AsyncIterator[bytes]:
        latest_usage: dict[str, Any] = {}
        started = self._monotonic()
        finished = False
        sent = False
        done = False
        bad_frame = False
        call = request._cost_call
        generation_ids: set[str] = set()

        async def generation(value: str) -> None:
            if value in generation_ids:
                return
            generation_ids.add(value)
            if self._accounting and call:
                await self._accounting.update(call, "generation", p_generation_id=value)

        request._on_generation = generation if call else None
        try:
            async with self._semaphore:
                if self._accounting and call:
                    # DB의 일회성 전송 전이를 얻은 실행만 공급자를 호출한다.
                    if not await self._accounting.update(call, "start"):
                        raise RuntimeError("call already started")
                    sent = True
                async for chunk in self._chat_stream(request):
                    if chunk.decode("utf-8", errors="replace").strip() == "data: [DONE]":
                        done = True
                    try:
                        payload = json.loads(chunk.decode("utf-8").removeprefix("data: ").strip())
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        if chunk.startswith(b"data:") and not done:
                            bad_frame = True
                    else:
                        latest_usage = _merge_usage(latest_usage, payload)
                        if isinstance(payload, dict):
                            if payload.get("id") and isinstance(payload["id"], str):
                                await generation(payload["id"])
                            if payload.get("error") is not None:
                                bad_frame = True
                            choices = payload.get("choices")
                            if choices is not None and not isinstance(choices, list):
                                bad_frame = True
                            for choice in choices if isinstance(choices, list) else []:
                                if (
                                    isinstance(choice, dict)
                                    and choice.get("finish_reason") == "error"
                                ):
                                    bad_frame = True
                    yield chunk
            finished = True
        finally:
            # ⚠️ 정상 종료 뒤에만 기록하면 클라이언트가 끊은 호출의 지출이 월 상한에서 빠진다.
            if self._accounting and call:

                async def finish() -> None:
                    try:
                        await self._accounting.finish(
                            call,
                            latest_usage,
                            complete=finished and done and not bad_frame,
                            duration_ms=round((self._monotonic() - started) * 1000),
                            sent=sent,
                        )
                    except Exception:  # noqa: BLE001 - 예약은 DB에 남아 재대조된다.
                        _logger.warning("worker.ask_cost_finish_failed")

                task = asyncio.create_task(finish())
                self._pending_records.add(task)
                task.add_done_callback(self._pending_records.discard)
                await asyncio.shield(task)
            else:
                await self._record_detached(
                    request.workspace_id,
                    latest_usage,
                    incomplete=not finished or not latest_usage,
                    duration_ms=round((self._monotonic() - started) * 1000),
                )

    async def _record_detached(
        self, workspace_id: str, usage: dict[str, Any], *, incomplete: bool, duration_ms: int
    ) -> None:
        """취소되어도 끝까지 기록한다. 기록 실패가 이미 끝난 응답을 깨뜨리지 않게 한다."""

        async def record() -> None:
            try:
                await self._record_usage(
                    workspace_id, usage, incomplete=incomplete, duration_ms=duration_ms
                )
            except Exception:  # noqa: BLE001 - 응답은 이미 나갔다. 원인은 로그로 남긴다.
                _logger.exception("worker.ask_usage_record_failed", incomplete=incomplete)

        task = asyncio.create_task(record())
        self._pending_records.add(task)
        task.add_done_callback(self._pending_records.discard)
        await asyncio.shield(task)


def _merge_usage(latest: dict[str, Any], payload: object) -> dict[str, Any]:
    """최종 사용량에 응답 최상위의 모델과 공급자를 합친다. 사용량은 청크 안에 모델을 담지 않는다."""
    if not isinstance(payload, dict):
        return latest
    usage = payload.get("usage")
    if not isinstance(usage, dict) or not usage:
        return latest
    routing = {key: payload[key] for key in ("model", "provider") if payload.get(key)}
    return {**usage, **routing}


def add_llm_stream_route(app: FastAPI, service: LlmStreamService) -> None:
    """`POST /internal/llm-chat`를 기존 앱에 등록한다 (query-embedding과 같은 process/port)."""

    @app.post("/internal/llm-chat")
    async def llm_chat(
        request: LlmChatRequest,
        authorization: Annotated[str | None, Header()] = None,
    ) -> StreamingResponse:
        chunks = await service.stream(request, authorization)
        return StreamingResponse(chunks, media_type="text/event-stream")
