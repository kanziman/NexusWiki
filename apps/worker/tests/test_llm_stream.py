"""05-01-PLAN.md Task 1 — private /internal/llm-chat listener 회귀 테스트.

`test_query_embedding.py`의 ASGITransport 패턴을 미러링한다. 스트리밍 응답을
`asyncio.wait_for`로 감싸는 이유는 05-RESEARCH.md Pitfall 5 — ASGITransport 위의
`AsyncClient.stream()`이 무한 대기할 수 있다는 문서화된 위험 때문이다.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from worker.llm_stream import (
    LlmChatRequest,
    LlmStreamService,
    add_llm_stream_route,
)

_INTERNAL_TOKEN = "test-llm-stream-token"  # noqa: S105 - non-secret test fixture


async def _allowed(_: str) -> bool:
    return True


async def _ignore_usage(_: str, __: dict[str, Any]) -> None:
    return None


class MonotonicClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _app(service: LlmStreamService) -> FastAPI:
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    add_llm_stream_route(app, service)
    return app


@pytest.mark.asyncio
async def test_unauthenticated_request_is_rejected_before_any_provider_call() -> None:
    calls = 0

    async def chat_stream(request: LlmChatRequest) -> AsyncIterator[bytes]:
        nonlocal calls
        calls += 1
        yield b"data: should-not-happen\n"

    service = LlmStreamService(
        chat_stream,
        internal_token=_INTERNAL_TOKEN,
        check_budget=_allowed,
        record_usage=_ignore_usage,
    )
    app = _app(service)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await asyncio.wait_for(
            client.post(
                "/internal/llm-chat",
                json={"workspace_id": "ws-1", "messages": [{"role": "user", "content": "hi"}]},
            ),
            timeout=5,
        )

    assert response.status_code == 401
    assert calls == 0


@pytest.mark.asyncio
async def test_authenticated_request_relays_injected_bytes_unchanged() -> None:
    async def chat_stream(request: LlmChatRequest) -> AsyncIterator[bytes]:
        assert request.workspace_id == "ws-1"
        yield b'data: {"choices":[{"delta":{"content":"hello"}}]}\n'
        yield b"data: [DONE]\n"

    service = LlmStreamService(
        chat_stream,
        internal_token=_INTERNAL_TOKEN,
        check_budget=_allowed,
        record_usage=_ignore_usage,
    )
    app = _app(service)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await asyncio.wait_for(
            client.post(
                "/internal/llm-chat",
                json={"workspace_id": "ws-1", "messages": [{"role": "user", "content": "hi"}]},
                headers={"Authorization": f"Bearer {_INTERNAL_TOKEN}"},
            ),
            timeout=5,
        )

    assert response.status_code == 200
    assert response.text == ('data: {"choices":[{"delta":{"content":"hello"}}]}\ndata: [DONE]\n')


@pytest.mark.asyncio
async def test_exhausted_token_bucket_returns_429_without_calling_chat_stream() -> None:
    clock = MonotonicClock()
    calls = 0

    async def chat_stream(request: LlmChatRequest) -> AsyncIterator[bytes]:
        nonlocal calls
        calls += 1
        yield b"data: should-not-happen\n"

    service = LlmStreamService(
        chat_stream,
        internal_token=_INTERNAL_TOKEN,
        check_budget=_allowed,
        record_usage=_ignore_usage,
        rate_capacity=1,
        refill_tokens_per_second=1,
        monotonic=clock,
    )
    app = _app(service)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        headers = {"Authorization": f"Bearer {_INTERNAL_TOKEN}"}
        body = {"workspace_id": "ws-1", "messages": [{"role": "user", "content": "hi"}]}

        first = await asyncio.wait_for(
            client.post("/internal/llm-chat", json=body, headers=headers), timeout=5
        )
        assert first.status_code == 200

        second = await asyncio.wait_for(
            client.post("/internal/llm-chat", json=body, headers=headers), timeout=5
        )

    assert second.status_code == 429
    assert calls == 1


@pytest.mark.asyncio
async def test_over_budget_request_is_rejected_before_any_provider_call() -> None:
    calls = 0

    async def chat_stream(request: LlmChatRequest) -> AsyncIterator[bytes]:
        nonlocal calls
        calls += 1
        yield b"data: should-not-happen\n"

    async def over_budget(_: str) -> bool:
        return False

    service = LlmStreamService(
        chat_stream,
        internal_token=_INTERNAL_TOKEN,
        check_budget=over_budget,
        record_usage=_ignore_usage,
    )
    app = _app(service)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/internal/llm-chat",
            json={"workspace_id": "ws-1", "messages": [{"role": "user", "content": "hi"}]},
            headers={"Authorization": f"Bearer {_INTERNAL_TOKEN}"},
        )

    assert response.status_code == 402
    assert response.json()["detail"] == "budget_exceeded"
    assert calls == 0


@pytest.mark.asyncio
async def test_completed_stream_records_latest_provider_usage_once() -> None:
    recorded: list[tuple[str, dict[str, Any]]] = []

    async def chat_stream(request: LlmChatRequest) -> AsyncIterator[bytes]:
        yield b'data: {"usage":{"cost":0.000001,"prompt_tokens":2}}\n'
        yield b'data: {"usage":{"cost":0.000003,"completion_tokens":4}}\n'
        yield b"data: [DONE]\n"

    async def record_usage(workspace_id: str, usage: dict[str, Any]) -> None:
        recorded.append((workspace_id, usage))

    service = LlmStreamService(
        chat_stream,
        internal_token=_INTERNAL_TOKEN,
        check_budget=_allowed,
        record_usage=record_usage,
    )
    app = _app(service)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/internal/llm-chat",
            json={"workspace_id": "ws-1", "messages": [{"role": "user", "content": "hi"}]},
            headers={"Authorization": f"Bearer {_INTERNAL_TOKEN}"},
        )

    assert response.status_code == 200
    assert recorded == [("ws-1", {"cost": 0.000003, "completion_tokens": 4})]


@pytest.mark.asyncio
async def test_completed_stream_without_usage_records_an_empty_usage_event() -> None:
    recorded: list[tuple[str, dict[str, Any]]] = []

    async def chat_stream(request: LlmChatRequest) -> AsyncIterator[bytes]:
        yield b'data: {"choices":[{"delta":{"content":"hello"}}]}\n'
        yield b"data: [DONE]\n"

    async def record_usage(workspace_id: str, usage: dict[str, Any]) -> None:
        recorded.append((workspace_id, usage))

    service = LlmStreamService(
        chat_stream,
        internal_token=_INTERNAL_TOKEN,
        check_budget=_allowed,
        record_usage=record_usage,
    )
    app = _app(service)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/internal/llm-chat",
            json={"workspace_id": "ws-1", "messages": [{"role": "user", "content": "hi"}]},
            headers={"Authorization": f"Bearer {_INTERNAL_TOKEN}"},
        )

    assert response.status_code == 200
    assert recorded == [("ws-1", {})]
