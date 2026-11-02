"""#179 조회 불가와 중복 정산의 대조 경계 검증.

설계: openspec/changes/reconcile-interrupted-ask-cost/design.md D5.
"""

# ruff: noqa: S106
# 비밀이 아닌 테스트 전용 인증 문자열이다.
import asyncio

import httpx
import pytest

from worker.ask_cost import AskCostAccounting
from worker.settings import WorkerSettings


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "status", "settles"),
    [
        ({"id": "gen-a", "model": "m", "total_cost": 0, "cancelled": True}, 200, True),
        ({"id": "gen-a", "model": "m", "total_cost": 0.01, "finish_reason": "stop"}, 200, True),
        ({"id": "gen-b", "model": "m", "total_cost": 0, "finish_reason": "stop"}, 200, False),
        ({"id": "gen-a", "model": "other", "total_cost": 0, "finish_reason": "stop"}, 200, False),
        ({"id": "gen-a", "model": "m", "total_cost": None, "finish_reason": "stop"}, 200, False),
        ({"id": "gen-a", "model": "m", "total_cost": 0}, 200, False),
        ({}, 404, False),
        ({}, 429, False),
        ({}, 500, False),
    ],
)
async def test_lookup_needs_conclusive_matching_cost(payload, status, settles):
    settings = WorkerSettings(
        SUPABASE_URL="http://db.invalid",
        SUPABASE_PUBLISHABLE_KEY="test",
        SUPABASE_SECRET_KEY="test",
        DATABASE_URL="postgresql://unused",
        OPENROUTER_API_KEY="test",
        LLM_MODEL="m",
    )
    accounting = AskCostAccounting(settings)
    actions = []

    async def update(call, action, **params):
        actions.append((action, params))
        return True

    accounting.update = update

    def transport(request):
        assert request.url.path == "/generation"
        assert request.url.params["id"] == "gen-a"
        return httpx.Response(status, json={"data": payload})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(transport), base_url="http://p.invalid"
    ) as client:
        await accounting.reconcile(
            client,
            {
                "id": "call",
                "workspace_id": "ws",
                "model": "m",
                "generation_id": "gen-a",
                "lease_id": "lease",
            },
        )
    assert any(a == "settle" for a, _ in actions) is settles
    assert actions[-1] == ("retry", {"p_lease_id": "lease"})
    assert all(a != "release" for a, _ in actions)


@pytest.mark.asyncio
async def test_restarted_loop_uses_durable_claim_and_stops(monkeypatch):
    from worker import ask_cost

    settings = WorkerSettings(
        SUPABASE_URL="http://db.invalid",
        SUPABASE_PUBLISHABLE_KEY="test",
        SUPABASE_SECRET_KEY="test",
        DATABASE_URL="postgresql://unused",
        OPENROUTER_API_KEY="test",
        LLM_MODEL="m",
    )
    accounting = AskCostAccounting(settings)
    stop = asyncio.Event()
    actions = []
    call = {
        "id": "call",
        "workspace_id": "ws",
        "model": "m",
        "lease_id": "lease",
        "generation_id": "gen-recovered",
    }

    async def rpc(function, **params):
        actions.append((function, params))
        if function == "claim_ask_costs":
            assert params == {"p_limit": 5}
            return [call]
        assert params["p_workspace_id"] == "ws"
        assert params["p_call_id"] == "call"
        if params["p_action"] == "settle":
            stop.set()
        return True

    accounting.rpc = rpc
    monkeypatch.setattr(
        ask_cost,
        "openrouter_client",
        lambda _: httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(
                    200,
                    json={
                        "data": {
                            "id": "gen-recovered",
                            "model": "m",
                            "total_cost": 0.000007,
                            "finish_reason": "stop",
                            "prompt": "DO_NOT_PERSIST_THIS_BODY",
                            "secret": "DO_NOT_PERSIST_THIS_KEY",
                        }
                    },
                )
            ),
            base_url="http://p.invalid",
        ),
    )
    await asyncio.wait_for(accounting.run(stop), timeout=1)
    settlement = next(p for f, p in actions if p.get("p_action") == "settle")
    assert settlement["p_cost_micros"] == 7
    assert "DO_NOT_PERSIST" not in str(actions)
