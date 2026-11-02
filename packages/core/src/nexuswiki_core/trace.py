"""요청 하나에서 시작된 처리를 잇는 trace 컨텍스트와 ASGI 미들웨어.

관련 이슈: #159
설계 근거: openspec/changes/ai-control-flow-accounting/design.md > D2
계약: openspec/changes/ai-control-flow-accounting/specs/ai-request-tracing/spec.md

값의 단일 원천은 structlog contextvars다. 별도 `ContextVar`를 두면 `clear_job_context`가
로그 컨텍스트만 지우고 trace는 남겨 다음 잡으로 새어 나간다.

소비자: `api.main`, `api.services.*`(내부 호출 헤더), `worker.__main__`(내부 리스너)
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any, Final
from uuid import UUID, uuid4

import structlog

from nexuswiki_core.logging import get_logger

__all__ = [
    "TRACE_HEADER",
    "TraceMiddleware",
    "TraceRecorder",
    "bind_trace",
    "current_trace_id",
    "new_trace_id",
    "parse_trace_id",
    "trace_headers",
]

TRACE_HEADER: Final[str] = "X-Trace-Id"

_TRACE_KEY: Final[str] = "trace_id"
_TRACE_HEADER_BYTES: Final[bytes] = TRACE_HEADER.lower().encode("ascii")

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
AsgiApp = Callable[[Scope, Receive, Send], Awaitable[None]]


def new_trace_id() -> str:
    return str(uuid4())


def parse_trace_id(value: str | None) -> str | None:
    """UUID 형식이면 정규형을, 아니면 `None`을 돌려준다."""
    if not value:
        return None
    try:
        return str(UUID(value))
    except ValueError:
        return None


def bind_trace(trace_id: str) -> None:
    structlog.contextvars.bind_contextvars(**{_TRACE_KEY: trace_id})


def current_trace_id() -> str | None:
    value = structlog.contextvars.get_contextvars().get(_TRACE_KEY)
    return value if isinstance(value, str) else None


def trace_headers() -> dict[str, str]:
    """내부 호출에 실을 헤더. 컨텍스트에 값이 없으면 비어 있다."""
    trace_id = current_trace_id()
    return {TRACE_HEADER: trace_id} if trace_id else {}


class TraceMiddleware:
    """요청마다 trace를 묶고 응답 헤더와 완료 로그에 남기는 순수 ASGI 미들웨어.

    ⚠️ `BaseHTTPMiddleware`로 바꾸지 않는다. 스트리밍 응답에서 컨텍스트 전파와 취소 동작이
    불안정해질 수 있다.

    ⚠️ `trust_inbound`는 내부 토큰으로 인증되는 워커 리스너에서만 켠다. API에서 켜면 클라이언트가
    고른 값으로 다른 요청의 기록에 섞여 들어갈 수 있다.

    처리되지 않은 예외는 응답이 시작되기 전이면 여기서 500을 보내고 다시 던진다.
    `ServerErrorMiddleware`는 사용자 미들웨어 바깥이라 그쪽에 맡기면 trace 헤더가 빠지는데,
    넓은 `Exception` 핸들러는 `api.errors`가 금지한다.
    """

    def __init__(
        self,
        app: AsgiApp,
        *,
        log_event: str,
        trust_inbound: bool = False,
    ) -> None:
        self._app = app
        self._log_event = log_event
        self._trust_inbound = trust_inbound

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        bind_trace(self._resolve_trace_id(scope))
        started = time.perf_counter()
        status_code: int | None = None

        async def send_with_trace(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                # 요청 처리 중 trace가 다시 묶일 수 있으므로 헤더를 보내는 시점의 값을 쓴다.
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() != _TRACE_HEADER_BYTES
                ]
                trace_id = current_trace_id() or new_trace_id()
                headers.append((_TRACE_HEADER_BYTES, trace_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        try:
            await self._app(scope, receive, send_with_trace)
        except Exception:
            if status_code is None:
                await send_with_trace(
                    {
                        "type": "http.response.start",
                        "status": 500,
                        "headers": [(b"content-type", b"text/plain; charset=utf-8")],
                    }
                )
                await send_with_trace(
                    {"type": "http.response.body", "body": b"Internal Server Error"}
                )
            raise
        finally:
            # 경로는 식별자만 담는다. 쿼리 문자열은 사용자 입력일 수 있어 남기지 않는다.
            get_logger(__name__).info(
                self._log_event,
                method=scope.get("method"),
                path=scope.get("path"),
                status_code=status_code,
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
            )
            structlog.contextvars.unbind_contextvars(_TRACE_KEY)

    def _resolve_trace_id(self, scope: Scope) -> str:
        if self._trust_inbound:
            for name, value in scope.get("headers", []):
                if name.lower() == _TRACE_HEADER_BYTES:
                    inbound = parse_trace_id(value.decode("latin-1"))
                    if inbound:
                        return inbound
        return new_trace_id()


class TraceRecorder:
    """한 요청의 구간 시간을 모은다.

    ⚠️ 이름과 시간만 받는다. 본문을 담을 필드가 없는 것이 이 클래스의 설계다. 끝나지 않은 구간은
    보고 시점에 닫으므로, 어느 분기로 끝나든 호출자가 일일이 닫지 않아도 된다.
    """

    def __init__(self, *, clock: Callable[[], float] = time.perf_counter) -> None:
        self._clock = clock
        self._started = clock()
        self._spans: list[dict[str, Any]] = []

    def start(self, name: str) -> None:
        """이전 구간을 닫고 새 구간을 연다. 구간은 겹치지 않고 순서대로 이어진다."""
        self._close_open_span()
        self._spans.append({"name": name, "start": self._clock() - self._started, "end": None})

    def spans(self) -> list[dict[str, Any]]:
        self._close_open_span()
        return [
            {
                "name": span["name"],
                "start_ms": round(span["start"] * 1000),
                "duration_ms": round((span["end"] - span["start"]) * 1000),
            }
            for span in self._spans
        ]

    def total_ms(self) -> int:
        return round((self._clock() - self._started) * 1000)

    def _close_open_span(self) -> None:
        if self._spans and self._spans[-1]["end"] is None:
            self._spans[-1]["end"] = self._clock() - self._started
