"""#177~#178 실제 스트림 서비스와 회계 경계의 실패·취소·금액 검증.

설계: openspec/changes/reconcile-interrupted-ask-cost/design.md D1~D4.
"""

# ruff: noqa: S106
# 비밀이 아닌 테스트 전용 인증 문자열이다.
import asyncio
import json
from typing import Any

import httpx
import pytest
from fastapi import HTTPException

from worker.ask_cost import AskCostAccounting, confirmed_cost
from worker.llm_stream import LlmChatRequest, LlmStreamService
from worker.settings import WorkerSettings


def settings(**kwargs: Any) -> WorkerSettings:
    return WorkerSettings(
        SUPABASE_URL="http://example.invalid",
        SUPABASE_PUBLISHABLE_KEY="test",
        SUPABASE_SECRET_KEY="test",
        DATABASE_URL="postgresql://unused",
        OPENROUTER_API_KEY="test",
        LLM_MODEL="m",
        **kwargs,
    )


def policy_settings() -> WorkerSettings:
    return settings(
        ASK_COST_POLICIES={
            "m": {
                "reserve_micros": 100,
                "max_input_bytes": 100,
                "max_tokens": 10,
                "version": "v1",
            }
        }
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (True, None),
        (-1, None),
        ("NaN", None),
        (float("inf"), None),
        ("0", 0),
        (0, 0),
        ("0.0000001", 1),
        ("0.000002", 2),
        ({}, None),
    ],
)
def test_cost_is_not_silently_zero(value, expected):
    assert confirmed_cost(value) == expected


class FakeAccounting(AskCostAccounting):
    def __init__(self):
        super().__init__(policy_settings())
        self.actions = []
        self.finishes = []
        self.start_allowed = True

    async def rpc(self, function, **params):
        self.actions.append((function, params))
        if function == "reserve_ask_cost":
            return {
                "id": params["p_call_id"],
                "workspace_id": params["p_workspace_id"],
                "model": "m",
            }
        return self.start_allowed if params.get("p_action") == "start" else True

    async def finish(self, call, usage, **kwargs):
        self.finishes.append((call, usage, kwargs))


@pytest.mark.asyncio
async def test_no_policy_or_oversize_never_reserves():
    accounting = FakeAccounting()
    accounting.settings = settings()
    with pytest.raises(HTTPException) as exc:
        await accounting.reserve("ws", [])
    assert exc.value.status_code == 503
    accounting.settings = policy_settings()
    with pytest.raises(HTTPException) as exc:
        await accounting.reserve("ws", [{"content": "가" * 100}])
    assert exc.value.status_code == 422
    assert accounting.actions == []


@pytest.mark.asyncio
@pytest.mark.parametrize(("fail", "status"), [("NW402", 402), ("42501", 503)])
async def test_failed_reservation_never_calls_provider(fail, status):
    accounting = FakeAccounting()

    async def rpc(*args, **kwargs):
        request = httpx.Request("POST", "https://db.invalid")
        response = httpx.Response(400, json={"code": fail}, request=request)
        raise httpx.HTTPStatusError("failure", request=request, response=response)

    accounting.rpc = rpc

    async def provider(request):
        pytest.fail("공급자가 호출됨")
        yield b""

    service = LlmStreamService(
        provider, internal_token="test", check_budget=None, record_usage=None, accounting=accounting
    )
    with pytest.raises(HTTPException) as exc:
        await service.stream(LlmChatRequest(workspace_id="ws", messages=[]), "Bearer test")
    assert exc.value.status_code == status


@pytest.mark.asyncio
async def test_generation_before_first_chunk_and_cancel_retains_reservation():
    accounting = FakeAccounting()

    async def provider(request):
        assert request._cost_call["max_tokens"] == 10
        assert accounting.actions[-1][1]["p_action"] == "start"
        await request._on_generation("gen-test")
        yield b'data: {"id":"gen-test","choices":[{"delta":{"content":"answer"}}]}\n'

    service = LlmStreamService(
        provider, internal_token="test", check_budget=None, record_usage=None, accounting=accounting
    )
    stream = await service.stream(LlmChatRequest(workspace_id="ws", messages=[]), "Bearer test")
    await anext(stream)
    await stream.aclose()
    assert accounting.finishes[0][2]["sent"] is True
    assert accounting.finishes[0][2]["complete"] is False
    assert [a[1].get("p_action") for a in accounting.actions].count("generation") == 1


@pytest.mark.asyncio
async def test_cancel_while_waiting_for_slot_is_proven_not_sent():
    accounting = FakeAccounting()

    async def provider(request):
        pytest.fail("전송 전 취소")
        yield b""

    service = LlmStreamService(
        provider, internal_token="test", check_budget=None, record_usage=None, accounting=accounting
    )
    await service._semaphore.acquire()
    await service._semaphore.acquire()
    stream = await service.stream(LlmChatRequest(workspace_id="ws", messages=[]), "Bearer test")
    task = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert accounting.finishes[0][2]["sent"] is False


@pytest.mark.asyncio
async def test_finish_preserves_observation_and_explicit_zero(monkeypatch):
    from worker import ask_cost

    writes = []
    actions = []

    def transport(request):
        writes.append(json.loads(request.content))
        return httpx.Response(201, json=[{}])

    monkeypatch.setattr(
        ask_cost,
        "service_client",
        lambda _: httpx.AsyncClient(
            transport=httpx.MockTransport(transport), base_url="http://db.invalid"
        ),
    )
    accounting = AskCostAccounting(policy_settings())

    async def update(call, action, **params):
        actions.append((action, params))
        return True

    accounting.update = update
    call = {"id": "call", "workspace_id": "ws", "model": "m"}
    await accounting.finish(call, {"cost": 0}, complete=True, duration_ms=1, sent=True)
    assert writes[0][0]["ask_call_id"] == "call"
    assert actions[-1] == ("settle", {"p_cost_micros": 0, "p_source": "final_usage"})
    await accounting.finish(call, {}, complete=True, duration_ms=1, sent=True)
    assert actions[-1][0] == "unresolved"


@pytest.mark.asyncio
async def test_provider_max_tokens_and_header_are_forwarded_before_body():
    from worker.llm import stream_chat

    seen = []

    def transport(request):
        assert json.loads(request.content)["max_tokens"] == 10
        return httpx.Response(
            200, headers={"X-Generation-Id": "gen-header"}, content=b"data: [DONE]\n"
        )

    async def on_generation(value):
        seen.append(value)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(transport), base_url="http://p.invalid"
    ) as client:
        async for _ in stream_chat(
            client,
            settings=policy_settings(),
            messages=[],
            max_tokens=10,
            on_generation=on_generation,
        ):
            assert seen == ["gen-header"]


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [False, True])
async def test_stream_completion_requires_clean_terminal_frame(bad):
    accounting = FakeAccounting()

    async def provider(request):
        if bad:
            yield b'data: {"error":{"message":"synthetic"}}\n'
        yield b'data: {"id":"gen-a","model":"m","usage":{"cost":0},"choices":[]}\n'
        yield b"data: [DONE]\n"

    service = LlmStreamService(
        provider, internal_token="test", check_budget=None, record_usage=None, accounting=accounting
    )
    stream = await service.stream(LlmChatRequest(workspace_id="ws", messages=[]), "Bearer test")
    assert len([part async for part in stream]) == (3 if bad else 2)
    assert accounting.finishes[0][2]["complete"] is not bad
