"""#172 로컬 DB의 병렬 승인·정산·JWT 비용 표시를 함께 검증한다.

설계: openspec/changes/reconcile-interrupted-ask-cost/design.md D1~D6.
"""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException

from tests.conftest import LOCAL_STACK
from worker.ask_cost import AskCostAccounting
from worker.llm_stream import LlmChatRequest, LlmStreamService
from worker.settings import WorkerSettings


@pytest.mark.asyncio
async def test_concurrent_reservations_and_settlement_reach_budget_api(
    two_workspaces_two_users,
    set_workspace_budget,
    authed_client,
):
    owner, outsider = two_workspaces_two_users
    set_workspace_budget(owner, 100)
    headers = {
        "apikey": LOCAL_STACK["admin_key"],
        "Authorization": f"Bearer {LOCAL_STACK['admin_key']}",
    }
    ws = owner.workspace_id
    async with httpx.AsyncClient(base_url=LOCAL_STACK["url"] + "/rest/v1", headers=headers) as db:
        params = [
            {
                "p_workspace_id": ws,
                "p_call_id": str(uuid4()),
                "p_trace_id": str(uuid4()),
                "p_model": "m",
                "p_policy_version": "v1",
                "p_reserve_micros": 70,
            }
            for _ in range(2)
        ]
        results = await asyncio.gather(*[db.post("/rpc/reserve_ask_cost", json=p) for p in params])
        assert sorted(r.status_code for r in results) == [200, 400]
        winner = next(r.json()[0] for r in results if r.status_code == 200)
        path = f"/workspaces/{ws}/budget"
        async with authed_client(owner) as api:
            before = (await api.get(path)).json()
            assert before["spent_micros"] == 70
            assert before["pending_micros"] == 70
            assert before["reported_micros"] == 0
        action = {"p_workspace_id": ws, "p_call_id": winner["id"]}
        assert (await db.post("/rpc/update_ask_cost", json={**action, "p_action": "start"})).json()
        settled = await asyncio.gather(
            *[
                db.post(
                    "/rpc/update_ask_cost",
                    json={**action, "p_action": "settle", "p_cost_micros": 20},
                )
                for _ in range(2)
            ]
        )
        assert sorted(r.json() for r in settled) == [False, True]
        async with authed_client(owner) as api:
            after = (await api.get(path)).json()
            assert after["spent_micros"] == 20
            assert after["pending_micros"] == 0
            assert after["reported_micros"] == 20
        async with httpx.AsyncClient(
            base_url=LOCAL_STACK["url"] + "/rest/v1",
            headers={
                "apikey": LOCAL_STACK["publishable_key"],
                "Authorization": f"Bearer {outsider.access_token}",
            },
        ) as user:
            denied = await user.post(
                "/rpc/ask_cost_snapshot",
                json={"p_workspace_id": ws, "p_since": datetime.now(UTC).isoformat()},
            )
            assert denied.status_code == 403
            assert (await user.post("/rpc/reserve_ask_cost", json=params[0])).status_code >= 400
            assert (await user.get("/ask_cost_calls")).status_code >= 400


@pytest.mark.asyncio
async def test_reservation_survives_client_restart_and_reconciliation_lease(
    two_workspaces_two_users,
):
    owner, _ = two_workspaces_two_users
    headers = {
        "apikey": LOCAL_STACK["admin_key"],
        "Authorization": f"Bearer {LOCAL_STACK['admin_key']}",
    }
    ws = owner.workspace_id
    call_id = str(uuid4())
    async with httpx.AsyncClient(base_url=LOCAL_STACK["url"] + "/rest/v1", headers=headers) as db:
        response = await db.post(
            "/rpc/reserve_ask_cost",
            json={
                "p_workspace_id": ws,
                "p_call_id": call_id,
                "p_trace_id": str(uuid4()),
                "p_model": "m",
                "p_policy_version": "v1",
                "p_reserve_micros": 70,
            },
        )
        assert response.status_code == 200
        assert (
            await db.post(
                "/rpc/update_ask_cost",
                json={"p_workspace_id": ws, "p_call_id": call_id, "p_action": "start"},
            )
        ).json()
    # 새 연결에서도 예약을 읽는다. 프로세스 메모리가 예산의 원천이면 이 값이 사라진다.
    async with httpx.AsyncClient(base_url=LOCAL_STACK["url"] + "/rest/v1", headers=headers) as db:
        result = await db.post(
            "/rpc/sum_usage_events_since",
            json={"p_workspace_id": ws, "p_since": "1970-01-01T00:00:00Z"},
        )
        assert result.json() == 70


@pytest.mark.asyncio
async def test_interruption_rejects_repeat_until_actual_settlement(
    two_workspaces_two_users,
    set_workspace_budget,
    authed_client,
):
    owner, _ = two_workspaces_two_users
    set_workspace_budget(owner, 100)
    settings = WorkerSettings(
        SUPABASE_URL=LOCAL_STACK["url"],
        SUPABASE_PUBLISHABLE_KEY=LOCAL_STACK["publishable_key"],
        SUPABASE_SECRET_KEY=LOCAL_STACK["admin_key"],
        DATABASE_URL="postgresql://unused",
        OPENROUTER_API_KEY="fixture",
        LLM_MODEL="m",
        ASK_COST_POLICIES={
            "m": {"reserve_micros": 70, "max_input_bytes": 1000, "max_tokens": 10, "version": "v1"}
        },
    )
    accounting = AskCostAccounting(settings)
    calls = []

    async def provider(request):
        calls.append(request._cost_call)
        await request._on_generation(f"gen-{uuid4()}")
        yield b'data: {"choices":[{"delta":{"content":"synthetic"}}]}\n'

    service = LlmStreamService(
        provider,
        internal_token="fixture",  # noqa: S106 - 합성 인증
        check_budget=None,
        record_usage=None,
        accounting=accounting,
    )
    request = LlmChatRequest(workspace_id=owner.workspace_id, messages=[])
    stream = await service.stream(request, "Bearer fixture")
    await anext(stream)
    await stream.aclose()
    with pytest.raises(HTTPException) as error:
        await service.stream(request, "Bearer fixture")
    assert error.value.status_code == 402
    assert len(calls) == 1
    async with authed_client(owner) as api:
        costs = (await api.get(f"/workspaces/{owner.workspace_id}/budget")).json()
        assert costs["spent_micros"] == 70
        assert costs["pending_micros"] == 70
    # 같은 원자적 정산 경계로 확정 비용을 반영하면 미확정 점유만 해제된다.
    assert await accounting.update(calls[0], "settle", p_cost_micros=20)
    async with authed_client(owner) as api:
        costs = (await api.get(f"/workspaces/{owner.workspace_id}/budget")).json()
        assert costs["spent_micros"] == 20
        assert costs["pending_micros"] == 0
    next_stream = await service.stream(
        LlmChatRequest(workspace_id=owner.workspace_id, messages=[]), "Bearer fixture"
    )
    await anext(next_stream)
    await next_stream.aclose()
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_cost_trace_rpc_keeps_author_and_membership_gate(
    two_workspaces_two_users,
    workspace_member_with_role,
    authed_client,
):
    owner, _ = two_workspaces_two_users
    author = workspace_member_with_role(owner, "editor")
    viewer = workspace_member_with_role(owner, "viewer")

    def user_headers(actor):
        return {
            "apikey": LOCAL_STACK["publishable_key"],
            "Authorization": f"Bearer {actor.access_token}",
        }

    admin = {
        "apikey": LOCAL_STACK["admin_key"],
        "Authorization": f"Bearer {LOCAL_STACK['admin_key']}",
    }
    trace = str(uuid4())
    params = {
        "p_workspace_id": owner.workspace_id,
        "p_trace_id": trace,
        "p_since": "1970-01-01T00:00:00Z",
    }
    async with httpx.AsyncClient(base_url=LOCAL_STACK["url"] + "/rest/v1") as db:
        turn = await db.post(
            "/rpc/start_ask_turn",
            headers=user_headers(author),
            json={
                "p_workspace_id": owner.workspace_id,
                "p_thread_id": None,
                "p_client_turn_id": str(uuid4()),
                "p_question": "synthetic",
                "p_trace_id": trace,
            },
        )
        assert turn.status_code == 200
        reservation = await db.post(
            "/rpc/reserve_ask_cost",
            headers=admin,
            json={
                "p_workspace_id": owner.workspace_id,
                "p_call_id": str(uuid4()),
                "p_trace_id": trace,
                "p_model": "m",
                "p_policy_version": "v1",
                "p_reserve_micros": 70,
            },
        )
        assert reservation.status_code == 200
        call = reservation.json()[0]
        stamp = datetime.fromisoformat(call["created_at"])
        # API가 아닌 공개 RPC에 같은 초의 두 경계를 직접 전달한다.
        for only_ask in (True, False):
            snapshots = []
            for microsecond in (0, 999999):
                reply = await db.post(
                    "/rpc/ask_cost_snapshot",
                    headers=user_headers(owner),
                    json={
                        "p_workspace_id": owner.workspace_id,
                        "p_since": stamp.replace(microsecond=microsecond).isoformat(),
                        "p_ask_only": only_ask,
                    },
                )
                assert reply.status_code == 200
                snapshots.append(reply.json())
            assert snapshots[0] == snapshots[1]
            assert snapshots[0][0]["pending_micros"] == 70
        own = await db.post("/rpc/ask_cost_snapshot", headers=user_headers(author), json=params)
        assert own.status_code == 200
        assert own.json()[0]["pending_micros"] == 70
        for actor in (owner, viewer):
            denied = await db.post(
                "/rpc/ask_cost_snapshot", headers=user_headers(actor), json=params
            )
            assert denied.status_code == 403
            denied_calls = await db.post(
                "/rpc/ask_cost_trace_calls",
                headers=user_headers(actor),
                json={"p_workspace_id": owner.workspace_id, "p_trace_id": trace},
            )
            assert denied_calls.status_code == 403
        async with authed_client(author) as api:
            detail = await api.get(f"/workspaces/{owner.workspace_id}/control/traces/{trace}")
            assert detail.status_code == 200
            assert detail.json()["totals"]["unresolved_count"] == 1
            assert detail.json()["totals"]["pending_micros"] == 70
        action = {"p_workspace_id": owner.workspace_id, "p_call_id": call["id"]}
        assert (
            await db.post(
                "/rpc/update_ask_cost", headers=admin, json={**action, "p_action": "start"}
            )
        ).json()
        observed = await db.post(
            "/usage_events",
            headers=admin,
            json={
                "workspace_id": owner.workspace_id,
                "ask_call_id": call["id"],
                "trace_id": trace,
                "kind": "llm",
                "provider": "fixture",
                "model": "m",
                "cost_micros": 90,
                "total_tokens": 10,
            },
        )
        assert observed.status_code < 400
        assert (
            await db.post(
                "/rpc/update_ask_cost",
                headers=admin,
                json={**action, "p_action": "settle", "p_cost_micros": 20},
            )
        ).json()
        async with authed_client(author) as api:
            detail = (
                await api.get(f"/workspaces/{owner.workspace_id}/control/traces/{trace}")
            ).json()
            assert detail["totals"]["call_count"] == 1
            assert detail["calls"][0]["observed_cost_micros"] == 90
            assert detail["calls"][0]["cost_micros"] == 20
            assert sum(c["cost_micros"] for c in detail["calls"]) == detail["totals"]["cost_micros"]
        aggregate = {
            "p_workspace_id": owner.workspace_id,
            "p_since": params["p_since"],
            "p_ask_only": True,
        }
        assert (
            await db.post("/rpc/ask_cost_snapshot", headers=user_headers(viewer), json=aggregate)
        ).status_code == 403
        visible_budget = await db.post(
            "/rpc/ask_cost_snapshot",
            headers=user_headers(viewer),
            json={"p_workspace_id": owner.workspace_id, "p_since": params["p_since"]},
        )
        assert visible_budget.json()[0]["unresolved_count"] == 0
        removed = await db.delete(
            "/workspace_members",
            headers=user_headers(owner),
            params={"workspace_id": f"eq.{owner.workspace_id}", "user_id": f"eq.{author.user_id}"},
        )
        assert removed.status_code < 400
        assert (
            await db.post("/rpc/ask_cost_snapshot", headers=user_headers(author), json=params)
        ).status_code == 403
