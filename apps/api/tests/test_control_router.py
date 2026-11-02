"""Control Room 접근 경계와 응답 계약 (#165, #166). 로컬 스택에서 RLS까지 증명한다."""

# ruff: noqa: ASYNC212

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import httpx
import pytest

from api.routers.control import _SPAN_LABELS
from nexuswiki_core.observability import _SPAN_NAMES
from tests.conftest import LOCAL_STACK

_SECRET_QUESTION = "고유한-질문-문자열"  # noqa: S105 - 테스트 픽스처
_SECRET_ANSWER = "고유한-답변-문자열"  # noqa: S105 - 테스트 픽스처
_RAW_ERROR = "RuntimeError: 고유한-원시-오류 sk-or-v1-abc"


def _user_headers(token: str) -> dict[str, str]:
    return {
        "apikey": LOCAL_STACK["publishable_key"],
        "Authorization": f"Bearer {token}",
        "Prefer": "return=representation",
    }


def _admin_headers() -> dict[str, str]:
    return {
        "apikey": LOCAL_STACK["admin_key"],
        "Authorization": f"Bearer {LOCAL_STACK['admin_key']}",
        "Prefer": "return=representation",
    }


def _rpc(stack: httpx.Client, token: str, name: str, params: dict[str, Any]) -> Any:
    response = stack.post(f"/rest/v1/rpc/{name}", headers=_user_headers(token), json=params)
    assert response.status_code < 400, response.text
    return response.json()


def _seed_ask_turn(stack: httpx.Client, actor: Any, *, cost: int = 2300) -> str:
    """작성자의 JWT로 턴을 만들고, 워커처럼 service key로 사용량을 남긴다."""
    trace_id = str(uuid4())
    turn_id = str(uuid4())
    started = _rpc(
        stack,
        actor.access_token,
        "start_ask_turn",
        {
            "p_workspace_id": actor.workspace_id,
            "p_thread_id": None,
            "p_client_turn_id": turn_id,
            "p_question": _SECRET_QUESTION,
            "p_trace_id": trace_id,
        },
    )
    assert started[0]["trace_id"] == trace_id
    _rpc(
        stack,
        actor.access_token,
        "finalize_ask_turn",
        {
            "p_workspace_id": actor.workspace_id,
            "p_thread_id": started[0]["thread_id"],
            "p_client_turn_id": turn_id,
            "p_answer_text": _SECRET_ANSWER,
            "p_citations": {"text": _SECRET_ANSWER, "resolved": []},
            "p_status": "resolved",
            "p_control_report": {
                "version": 1,
                "outcome": "resolved",
                "route": {"decision": "STANDARD", "reason": "default"},
                "total_ms": 1200,
                "spans": [
                    {"name": "retrieval", "start_ms": 0, "duration_ms": 200},
                    {"name": "llm_stream", "start_ms": 200, "duration_ms": 1000},
                    {"name": "조작된-구간", "start_ms": 0, "duration_ms": 1},
                ],
                "evidence": {"wiki": 4, "source": 4},
                "retrieval": {"policy_version": "v", "missing_channels": ["wiki_vector"]},
                "citation": {"cited_anchor_count": 3, "dual_citation_rate": 0.5},
            },
        },
    )
    inserted = stack.post(
        "/rest/v1/usage_events",
        headers=_admin_headers(),
        json={
            "workspace_id": actor.workspace_id,
            "trace_id": trace_id,
            "kind": "llm",
            "provider": "p",
            "model": "test-model",
            "prompt_tokens": 90,
            "completion_tokens": 10,
            "total_tokens": 100,
            "cost_micros": cost,
            "duration_ms": 1000,
            "metadata": {"call": "ask"},
        },
    )
    assert inserted.status_code < 400, inserted.text
    return trace_id


def _seed_ingest_chain(stack: httpx.Client, actor: Any) -> str:
    trace_id = str(uuid4())

    def job(job_type: str, status: str, **values: Any) -> None:
        lock = (
            {"locked_at": "2026-11-02T00:00:00+00:00", "locked_by": "w"}
            if status == "running"
            else {}
        )
        response = stack.post(
            "/rest/v1/jobs",
            headers=_admin_headers(),
            json={
                "workspace_id": actor.workspace_id,
                "type": job_type,
                "payload": {"target_id": str(uuid4()), "secret": "고유한-payload"},
                "trace_id": trace_id,
                "status": status,
                **lock,
                **values,
            },
        )
        assert response.status_code < 400, response.text

    job("parse", "succeeded", last_claimed_at="2026-11-02T00:00:00+00:00")
    job("compile", "dead", last_error=_RAW_ERROR, attempts=3)
    return trace_id


@pytest.mark.asyncio
async def test_author_sees_own_ask_trace_with_totals_matching_usage(
    two_workspaces_two_users: tuple[Any, Any],
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
) -> None:
    owner, _ = two_workspaces_two_users
    trace_id = _seed_ask_turn(local_stack, owner)

    async with authed_client(owner) as client:
        listed = await client.get(f"/workspaces/{owner.workspace_id}/control/traces")
        detail = await client.get(f"/workspaces/{owner.workspace_id}/control/traces/{trace_id}")

    assert listed.status_code == 200, listed.text
    assert trace_id in {item["trace_id"] for item in listed.json()["items"]}
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["kind"] == "ask"
    assert payload["route"] == {"decision": "STANDARD", "reason": "default"}
    assert payload["totals"] == {
        "call_count": 1,
        "total_tokens": 100,
        "cost_micros": 2300,
        "incomplete_call_count": 0,
        "pending_micros": 0,
        "budget_micros": 2300,
        "unresolved_count": 0,
        "manual_review_count": 0,
        "over_reserve_count": 0,
    }
    assert [span["name"] for span in payload["spans"]] == ["retrieval", "llm_stream"]
    assert payload["missing_channels"] == ["wiki_vector"]


@pytest.mark.asyncio
async def test_responses_never_carry_bodies_payloads_or_raw_errors(
    two_workspaces_two_users: tuple[Any, Any],
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
) -> None:
    owner, _ = two_workspaces_two_users
    ask_trace = _seed_ask_turn(local_stack, owner)
    ingest_trace = _seed_ingest_chain(local_stack, owner)
    path = f"/workspaces/{owner.workspace_id}/control"

    async with authed_client(owner) as client:
        responses = [
            await client.get(f"{path}/traces"),
            await client.get(f"{path}/traces/{ask_trace}"),
            await client.get(f"{path}/traces/{ingest_trace}"),
            await client.get(f"{path}/ask-aggregate"),
        ]

    for response in responses:
        assert response.status_code == 200, response.text
        text = response.text
        for forbidden in (
            _SECRET_QUESTION,
            _SECRET_ANSWER,
            "고유한-payload",
            "고유한-원시-오류",
            "sk-or-v1",
            "조작된-구간",
        ):
            assert forbidden not in text


@pytest.mark.asyncio
async def test_editor_gets_403_for_another_members_ask_trace(
    two_workspaces_two_users: tuple[Any, Any],
    workspace_member_with_role: Any,
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
) -> None:
    owner, _ = two_workspaces_two_users
    editor = workspace_member_with_role(owner, "editor")
    trace_id = _seed_ask_turn(local_stack, editor)

    async with authed_client(owner) as client:
        detail = await client.get(f"/workspaces/{owner.workspace_id}/control/traces/{trace_id}")
        absent = await client.get(f"/workspaces/{owner.workspace_id}/control/traces/{uuid4()}")
        listed = await client.get(f"/workspaces/{owner.workspace_id}/control/traces")

    # owner도 다른 멤버의 Ask는 볼 수 없고, 존재 여부도 구분되지 않는다.
    assert detail.status_code == 403
    assert absent.status_code == 403
    assert detail.json() == absent.json()
    assert trace_id not in {item["trace_id"] for item in listed.json()["items"]}


@pytest.mark.asyncio
async def test_viewer_sees_only_own_ask_traces(
    two_workspaces_two_users: tuple[Any, Any],
    workspace_member_with_role: Any,
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
) -> None:
    owner, _ = two_workspaces_two_users
    viewer = workspace_member_with_role(owner, "viewer")
    own_trace = _seed_ask_turn(local_stack, viewer)
    ingest_trace = _seed_ingest_chain(local_stack, owner)
    path = f"/workspaces/{owner.workspace_id}/control"

    async with authed_client(viewer) as client:
        listed = await client.get(f"{path}/traces")
        own = await client.get(f"{path}/traces/{own_trace}")
        ingest = await client.get(f"{path}/traces/{ingest_trace}")
        aggregate = await client.get(f"{path}/ask-aggregate")

    assert listed.status_code == 200
    assert listed.json()["can_view_workspace"] is False
    assert {item["trace_id"] for item in listed.json()["items"]} == {own_trace}
    assert own.status_code == 200
    assert ingest.status_code == 403
    assert aggregate.status_code == 403


@pytest.mark.asyncio
async def test_non_member_is_denied_everywhere(
    two_workspaces_two_users: tuple[Any, Any],
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
) -> None:
    owner, outsider = two_workspaces_two_users
    ask_trace = _seed_ask_turn(local_stack, owner)
    ingest_trace = _seed_ingest_chain(local_stack, owner)
    path = f"/workspaces/{owner.workspace_id}/control"

    async with authed_client(outsider) as client:
        responses = [
            await client.get(f"{path}/traces"),
            await client.get(f"{path}/traces/{ask_trace}"),
            await client.get(f"{path}/traces/{ingest_trace}"),
            await client.get(f"{path}/ask-aggregate"),
        ]

    assert [response.status_code for response in responses] == [403, 403, 403, 403]


@pytest.mark.asyncio
async def test_member_removed_from_workspace_loses_own_trace(
    two_workspaces_two_users: tuple[Any, Any],
    workspace_member_with_role: Any,
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
) -> None:
    owner, _ = two_workspaces_two_users
    author = workspace_member_with_role(owner, "editor")
    trace_id = _seed_ask_turn(local_stack, author)
    removed = local_stack.delete(
        "/rest/v1/workspace_members",
        params={"workspace_id": f"eq.{owner.workspace_id}", "user_id": f"eq.{author.user_id}"},
        headers=_user_headers(owner.access_token),
    )
    assert removed.status_code < 400, removed.text

    async with authed_client(author) as client:
        response = await client.get(f"/workspaces/{owner.workspace_id}/control/traces/{trace_id}")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_editor_sees_ingest_stages_with_sanitized_error_category(
    two_workspaces_two_users: tuple[Any, Any],
    workspace_member_with_role: Any,
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
) -> None:
    owner, _ = two_workspaces_two_users
    editor = workspace_member_with_role(owner, "editor")
    trace_id = _seed_ingest_chain(local_stack, owner)

    async with authed_client(editor) as client:
        response = await client.get(f"/workspaces/{owner.workspace_id}/control/traces/{trace_id}")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["kind"] == "ingest"
    assert payload["status"] == "failed"
    stages = {stage["type"]: stage for stage in payload["stages"]}
    assert stages["parse"]["state"] == "completed"
    assert stages["compile"]["state"] == "failed"
    assert stages["compile"]["error_category"] == "internal_error"
    assert stages["compile"]["attempts"] == 3
    # 중단된 체인에는 대기 단계를 그리지 않는다.
    assert "embed" not in stages


@pytest.mark.asyncio
async def test_running_ingest_reports_completed_active_and_pending_stages(
    two_workspaces_two_users: tuple[Any, Any],
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
) -> None:
    owner, _ = two_workspaces_two_users
    trace_id = str(uuid4())
    for job_type, status, extra in (
        ("parse", "succeeded", {}),
        ("compile", "running", {"locked_at": "2026-11-02T00:00:00+00:00", "locked_by": "w"}),
    ):
        response = local_stack.post(
            "/rest/v1/jobs",
            headers=_admin_headers(),
            json={
                "workspace_id": owner.workspace_id,
                "type": job_type,
                "payload": {"target_id": str(uuid4())},
                "trace_id": trace_id,
                "status": status,
                **extra,
            },
        )
        assert response.status_code < 400, response.text

    async with authed_client(owner) as client:
        response = await client.get(f"/workspaces/{owner.workspace_id}/control/traces/{trace_id}")

    states = [(stage["type"], stage["state"]) for stage in response.json()["stages"]]
    assert states == [
        ("parse", "completed"),
        ("compile", "active"),
        ("link_sync", "pending"),
        ("embed", "pending"),
        ("conflict_check", "pending"),
    ]


@pytest.mark.asyncio
async def test_ask_aggregate_counts_without_identifying_anyone(
    two_workspaces_two_users: tuple[Any, Any],
    workspace_member_with_role: Any,
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
) -> None:
    owner, _ = two_workspaces_two_users
    teammate = workspace_member_with_role(owner, "viewer")
    trace_a = _seed_ask_turn(local_stack, owner, cost=1000)
    trace_b = _seed_ask_turn(local_stack, teammate, cost=3000)

    async with authed_client(owner) as client:
        response = await client.get(f"/workspaces/{owner.workspace_id}/control/ask-aggregate")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["turn_count"] == 2
    assert payload["resolved_count"] == 2
    assert payload["decision_counts"] == {"STANDARD": 2}
    assert payload["total_cost_micros"] == 4000
    assert payload["p50_total_ms"] == 1200
    serialized = json.dumps(payload)
    for identifier in (owner.user_id, teammate.user_id, trace_a, trace_b):
        assert identifier not in serialized


@pytest.mark.asyncio
async def test_forged_report_values_do_not_break_the_aggregate(
    two_workspaces_two_users: tuple[Any, Any],
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
) -> None:
    owner, _ = two_workspaces_two_users
    trace_id = _seed_ask_turn(local_stack, owner)
    forged = local_stack.patch(
        "/rest/v1/ask_messages",
        params={"trace_id": f"eq.{trace_id}"},
        headers=_user_headers(owner.access_token),
        json={"control_report": {"total_ms": "문자열", "route": {"decision": "<script>"}}},
    )
    assert forged.status_code < 400, forged.text

    async with authed_client(owner) as client:
        response = await client.get(f"/workspaces/{owner.workspace_id}/control/ask-aggregate")

    assert response.status_code == 200, response.text
    assert response.json()["decision_counts"] == {}
    assert response.json()["p50_total_ms"] is None


@pytest.mark.parametrize("total_ms", [1e20, -5, 86400001])
@pytest.mark.asyncio
async def test_out_of_range_durations_do_not_break_the_aggregate(
    two_workspaces_two_users: tuple[Any, Any],
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
    total_ms: float,
) -> None:
    # ⚠️ 문자열만 막으면 큰 수가 `::int`에서 22003을 내어 전 editor의 집계가 500이 된다.
    owner, _ = two_workspaces_two_users
    trace_id = _seed_ask_turn(local_stack, owner)
    forged = local_stack.patch(
        "/rest/v1/ask_messages",
        params={"trace_id": f"eq.{trace_id}"},
        headers=_user_headers(owner.access_token),
        json={"control_report": {"total_ms": total_ms}},
    )
    assert forged.status_code < 400, forged.text

    async with authed_client(owner) as client:
        response = await client.get(f"/workspaces/{owner.workspace_id}/control/ask-aggregate")

    assert response.status_code == 200, response.text
    assert response.json()["p95_total_ms"] is None


def test_author_cannot_rewrite_the_trace_id_of_a_turn(
    two_workspaces_two_users: tuple[Any, Any], local_stack: httpx.Client
) -> None:
    # ⚠️ 바꿀 수 있으면 다른 멤버의 trace로 Control Room 게이트를 통과하고 합계를 부풀린다.
    owner, _ = two_workspaces_two_users
    trace_id = _seed_ask_turn(local_stack, owner)

    rewritten = local_stack.patch(
        "/rest/v1/ask_messages",
        params={"trace_id": f"eq.{trace_id}"},
        headers=_user_headers(owner.access_token),
        json={"trace_id": str(uuid4())},
    )

    assert rewritten.status_code == 403
    assert rewritten.json()["code"] == "42501"


@pytest.mark.parametrize("source", ["usage_events", "jobs"])
@pytest.mark.asyncio
async def test_member_cannot_adopt_an_existing_trace_for_a_new_turn(
    two_workspaces_two_users: tuple[Any, Any],
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
    workspace_member_with_role: Callable[[Any, str], Any],
    source: str,
) -> None:
    # ⚠️ viewer는 usage_events에서 다른 멤버의 trace를 읽을 수 있다. 그 값으로 자기 턴을 만들 수
    #    있으면 "다른 멤버의 trace는 403"이 이 경로로 무너지고 재전달로 합계가 오염된다.
    owner, _ = two_workspaces_two_users
    viewer = workspace_member_with_role(owner, "viewer")
    if source == "usage_events":
        trace_id = _seed_ask_turn(local_stack, owner)
    else:
        trace_id = str(uuid4())
        seeded = local_stack.post(
            "/rest/v1/jobs",
            headers=_admin_headers(),
            json={
                "workspace_id": owner.workspace_id,
                "type": "parse",
                "payload": {"target_id": str(uuid4())},
                "trace_id": trace_id,
            },
        )
        assert seeded.status_code < 400, seeded.text

    adopted = local_stack.post(
        "/rest/v1/rpc/start_ask_turn",
        headers=_user_headers(viewer.access_token),
        json={
            "p_workspace_id": owner.workspace_id,
            "p_thread_id": None,
            "p_client_turn_id": str(uuid4()),
            "p_question": "남의 trace로 만든 턴",
            "p_trace_id": trace_id,
        },
    )

    assert adopted.status_code == 403, adopted.text
    assert adopted.json()["code"] == "42501"
    async with authed_client(viewer) as client:
        detail = await client.get(f"/workspaces/{owner.workspace_id}/control/traces/{trace_id}")
    assert detail.status_code == 403


@pytest.mark.parametrize("source", ["usage_events", "jobs"])
@pytest.mark.asyncio
async def test_direct_insert_cannot_adopt_an_existing_trace_either(
    two_workspaces_two_users: tuple[Any, Any],
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
    workspace_member_with_role: Callable[[Any, str], Any],
    source: str,
) -> None:
    # ⚠️ 작성자는 RPC 없이 ask_messages에 INSERT할 수 있다. 함수 안의 검사는 이 경로로 우회됐다.
    owner, _ = two_workspaces_two_users
    viewer = workspace_member_with_role(owner, "viewer")
    if source == "usage_events":
        trace_id = _seed_ask_turn(local_stack, owner)
    else:
        trace_id = str(uuid4())
        seeded = local_stack.post(
            "/rest/v1/jobs",
            headers=_admin_headers(),
            json={
                "workspace_id": owner.workspace_id,
                "type": "parse",
                "payload": {"target_id": str(uuid4())},
                "trace_id": trace_id,
            },
        )
        assert seeded.status_code < 400, seeded.text
    own_turn = _rpc(
        local_stack,
        viewer.access_token,
        "start_ask_turn",
        {
            "p_workspace_id": owner.workspace_id,
            "p_thread_id": None,
            "p_client_turn_id": str(uuid4()),
            "p_question": "내 스레드",
            "p_trace_id": str(uuid4()),
        },
    )

    inserted = local_stack.post(
        "/rest/v1/ask_messages",
        headers=_user_headers(viewer.access_token),
        json={
            "thread_id": own_turn[0]["thread_id"],
            "workspace_id": owner.workspace_id,
            "client_turn_id": str(uuid4()),
            "question": "남의 trace로 직접 넣은 턴",
            "status": "resolved",
            "trace_id": trace_id,
        },
    )

    assert inserted.status_code == 403, inserted.text
    assert inserted.json()["code"] == "42501"
    async with authed_client(viewer) as client:
        detail = await client.get(f"/workspaces/{owner.workspace_id}/control/traces/{trace_id}")
    assert detail.status_code == 403


def _seed_raw_source(stack: httpx.Client, actor: Any) -> str:
    raw_source_id = str(uuid4())
    response = stack.post(
        "/rest/v1/raw_sources",
        headers=_admin_headers(),
        json={
            "id": raw_source_id,
            "workspace_id": actor.workspace_id,
            "title": "원문",
            "source_type": "text",
            "content": "본문",
            "content_hash": uuid4().hex,
        },
    )
    assert response.status_code < 400, response.text
    return raw_source_id


def test_editor_cannot_enqueue_a_job_under_an_ask_trace(
    two_workspaces_two_users: tuple[Any, Any], local_stack: httpx.Client
) -> None:
    # ⚠️ 막지 않으면 Control Room의 수집 분기를 지나 "다른 멤버의 Ask trace는 403"이 무너진다.
    owner, _ = two_workspaces_two_users
    trace_id = _seed_ask_turn(local_stack, owner)
    raw_source_id = _seed_raw_source(local_stack, owner)

    response = local_stack.post(
        "/rest/v1/rpc/enqueue_source_job",
        headers=_user_headers(owner.access_token),
        json={
            "p_workspace_id": owner.workspace_id,
            "p_raw_source_id": raw_source_id,
            "p_trace_id": trace_id,
        },
    )

    assert response.status_code == 403, response.text
    assert response.json()["code"] == "42501"
    jobs = local_stack.get(
        "/rest/v1/jobs",
        params={"workspace_id": f"eq.{owner.workspace_id}", "trace_id": f"eq.{trace_id}"},
        headers=_admin_headers(),
    )
    assert jobs.json() == []


def test_one_request_may_enqueue_several_jobs_under_its_trace(
    two_workspaces_two_users: tuple[Any, Any], local_stack: httpx.Client
) -> None:
    # 영상 배치 등록은 한 요청의 잡들이 같은 trace를 공유한다. 위 거부가 이 경로를 막으면 안 된다.
    owner, _ = two_workspaces_two_users
    trace_id = str(uuid4())

    created = [
        _rpc(
            local_stack,
            owner.access_token,
            "enqueue_source_job",
            {
                "p_workspace_id": owner.workspace_id,
                "p_raw_source_id": _seed_raw_source(local_stack, owner),
                "p_trace_id": trace_id,
            },
        )
        for _ in range(2)
    ]

    assert [rows[0]["trace_id"] for rows in created] == [trace_id, trace_id]


def test_retransmitting_a_turn_keeps_its_trace_even_after_usage_exists(
    two_workspaces_two_users: tuple[Any, Any], local_stack: httpx.Client
) -> None:
    # 재전달은 원래 턴을 돌려주는 정상 경로이므로 위 거부에 걸리면 안 된다.
    owner, _ = two_workspaces_two_users
    turn_id = str(uuid4())
    trace_id = str(uuid4())
    params = {
        "p_workspace_id": owner.workspace_id,
        "p_thread_id": None,
        "p_client_turn_id": turn_id,
        "p_question": "재전달",
        "p_trace_id": trace_id,
    }
    _rpc(local_stack, owner.access_token, "start_ask_turn", params)
    seeded = local_stack.post(
        "/rest/v1/usage_events",
        headers=_admin_headers(),
        json={
            "workspace_id": owner.workspace_id,
            "trace_id": trace_id,
            "kind": "llm",
            "provider": "test",
            "model": "test",
            "cost_micros": 1,
        },
    )
    assert seeded.status_code < 400, seeded.text

    again = _rpc(
        local_stack, owner.access_token, "start_ask_turn", {**params, "p_trace_id": str(uuid4())}
    )

    assert again[0]["trace_id"] == trace_id


def test_aggregate_boundary_is_rounded_down_to_the_utc_day(
    two_workspaces_two_users: tuple[Any, Any], local_stack: httpx.Client
) -> None:
    # 경계를 조금씩 옮겨 개별 턴의 값을 분리하지 못해야 한다. 방금 만든 턴의 시각보다 뒤를 지정해도
    # 같은 날이면 그 턴이 집계에 포함된다.
    owner, _ = two_workspaces_two_users
    _seed_ask_turn(local_stack, owner)
    just_ahead = (datetime.now(UTC) + timedelta(seconds=1)).isoformat()

    rows = _rpc(
        local_stack,
        owner.access_token,
        "ask_trace_aggregate",
        {"p_workspace_id": owner.workspace_id, "p_since": just_ahead},
    )

    assert rows[0]["turn_count"] == 1


def test_control_report_size_is_limited(
    two_workspaces_two_users: tuple[Any, Any], local_stack: httpx.Client
) -> None:
    owner, _ = two_workspaces_two_users
    trace_id = _seed_ask_turn(local_stack, owner)

    oversized = local_stack.patch(
        "/rest/v1/ask_messages",
        params={"trace_id": f"eq.{trace_id}"},
        headers=_user_headers(owner.access_token),
        json={"control_report": {"blob": [str(uuid4()) for _ in range(3000)]}},
    )

    assert oversized.status_code >= 400


@pytest.mark.asyncio
async def test_control_budget_separates_editor_and_viewer_scopes_and_denies_outsider(
    two_workspaces_two_users: tuple[Any, Any],
    workspace_member_with_role: Any,
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
) -> None:
    owner, outsider = two_workspaces_two_users
    viewer = workspace_member_with_role(owner, "viewer")
    _seed_ask_turn(local_stack, owner, cost=2300)
    raw_source_id = _seed_raw_source(local_stack, owner)
    seeded_compile = local_stack.post(
        "/rest/v1/usage_events",
        headers=_admin_headers(),
        json={
            "workspace_id": owner.workspace_id,
            "kind": "llm",
            "provider": "openrouter",
            "model": "test-model",
            "prompt_tokens": 500,
            "completion_tokens": 100,
            "total_tokens": 600,
            "cost_micros": 1700,
            "metadata": {"call": "compile", "route": "TRUNCATED", "max_tokens": 4096},
        },
    )
    assert seeded_compile.status_code < 400, seeded_compile.text
    seeded_skip = local_stack.post(
        "/rest/v1/jobs",
        headers=_admin_headers(),
        json={
            "workspace_id": owner.workspace_id,
            "type": "link_sync",
            "status": "succeeded",
            "payload": {
                "target_id": raw_source_id,
                "raw_source_id": raw_source_id,
                "compile_route": "SKIP_UNCHANGED",
                "secret": "고유한-payload",
            },
        },
    )
    assert seeded_skip.status_code < 400, seeded_skip.text

    path = f"/workspaces/{owner.workspace_id}/control/budget"
    async with authed_client(owner) as owner_client:
        owner_resp = await owner_client.get(path)
    async with authed_client(viewer) as viewer_client:
        viewer_resp = await viewer_client.get(path)
    async with authed_client(outsider) as outsider_client:
        outsider_resp = await outsider_client.get(path)

    assert outsider_resp.status_code == 403
    assert owner_resp.status_code == 200, owner_resp.text
    owner_body = owner_resp.json()
    assert owner_body["can_view_workspace"] is True
    assert owner_body["reported_micros"] == 4000
    assert owner_body["budget_micros"] == 4000
    assert owner_body["savings"]["compile_truncated_count"] == 1
    assert owner_body["savings"]["compile_skipped_count"] == 1
    assert {item["call"] for item in owner_body["by_call_path"]} == {"ask", "compile"}
    assert "고유한-payload" not in owner_resp.text

    assert viewer_resp.status_code == 200, viewer_resp.text
    viewer_body = viewer_resp.json()
    assert viewer_body["can_view_workspace"] is False
    assert viewer_body["budget_micros"] == 4000
    assert viewer_body["savings"]["compile_truncated_count"] == 0
    assert viewer_body["savings"]["compile_skipped_count"] == 0
    assert viewer_body["by_call_path"] == []


def _seed_quality_turn(stack: httpx.Client, actor: Any, *, status: str, quality: Any) -> None:
    turn_id = str(uuid4())
    started = _rpc(
        stack,
        actor.access_token,
        "start_ask_turn",
        {
            "p_workspace_id": actor.workspace_id,
            "p_thread_id": None,
            "p_client_turn_id": turn_id,
            "p_question": _SECRET_QUESTION,
            "p_trace_id": str(uuid4()),
        },
    )
    _rpc(
        stack,
        actor.access_token,
        "finalize_ask_turn",
        {
            "p_workspace_id": actor.workspace_id,
            "p_thread_id": started[0]["thread_id"],
            "p_client_turn_id": turn_id,
            "p_answer_text": _SECRET_ANSWER,
            "p_citations": {"text": _SECRET_ANSWER, "resolved": []},
            "p_status": status,
            "p_control_report": {"version": 1, "outcome": status, "quality": quality},
        },
    )


@pytest.mark.asyncio
async def test_control_quality_separates_scopes_and_survives_forged_reports(
    two_workspaces_two_users: tuple[Any, Any],
    workspace_member_with_role: Any,
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
) -> None:
    owner, outsider = two_workspaces_two_users
    viewer = workspace_member_with_role(owner, "viewer")
    _seed_quality_turn(
        local_stack,
        owner,
        status="fallback",
        quality={
            "mode": "enforce",
            "violations": ["no_citation"],
            "repair_attempted": True,
            "repaired": False,
            "fallback": True,
        },
    )
    _seed_quality_turn(
        local_stack,
        owner,
        status="resolved",
        quality={
            "mode": "enforce",
            "violations": ["fabricated_anchor"],
            "repair_attempted": True,
            "repaired": True,
            "fallback": False,
        },
    )
    # 작성자가 control_report를 조작해도 집계가 깨지면 안 된다.
    _seed_quality_turn(
        local_stack,
        owner,
        status="resolved",
        quality={"violations": "조작", "repair_attempted": "yes", "repaired": 1},
    )
    _seed_quality_turn(local_stack, viewer, status="resolved", quality=None)
    seeded = local_stack.post(
        "/rest/v1/usage_events",
        headers=_admin_headers(),
        json={
            "workspace_id": owner.workspace_id,
            "kind": "llm",
            "provider": "openrouter",
            "model": "test-model",
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
            "cost_micros": 1,
            "metadata": {
                "call": "compile",
                "fence_stripped": True,
                "violation": "semantic_invalid",
                "exhausted": True,
            },
        },
    )
    assert seeded.status_code < 400, seeded.text
    seeded_empty = local_stack.post(
        "/rest/v1/usage_events",
        headers=_admin_headers(),
        json={
            "workspace_id": owner.workspace_id,
            "kind": "llm",
            "provider": "openrouter",
            "model": "test-model",
            "prompt_tokens": 1,
            "completion_tokens": 0,
            "total_tokens": 1,
            "cost_micros": 1,
            "metadata": {"call": "conflict_check", "violation": "missing_content"},
        },
    )
    assert seeded_empty.status_code < 400, seeded_empty.text

    path = f"/workspaces/{owner.workspace_id}/control/quality"
    async with authed_client(owner) as owner_client:
        owner_resp = await owner_client.get(path)
    async with authed_client(viewer) as viewer_client:
        viewer_resp = await viewer_client.get(path)
    async with authed_client(outsider) as outsider_client:
        outsider_resp = await outsider_client.get(path)
    async with authed_client(None) as anonymous_client:
        anonymous_resp = await anonymous_client.get(path)

    assert outsider_resp.status_code == 403
    assert anonymous_resp.status_code == 401
    assert owner_resp.status_code == 200, owner_resp.text
    body = owner_resp.json()
    assert body["can_view_workspace"] is True
    assert body["ask"] == {
        "turns": 4,
        "violation_turns": 2,
        "no_citation_turns": 1,
        "fabricated_turns": 1,
        "repair_attempted": 2,
        "repaired": 1,
        "fallback": 1,
    }
    assert body["structured"]["calls"] == 2
    assert body["structured"]["fence_stripped"] == 1
    assert body["structured"]["semantic_invalid"] == 1
    assert body["structured"]["missing_content"] == 1
    assert body["structured"]["exhausted"] == 1
    assert _SECRET_ANSWER not in owner_resp.text
    assert _SECRET_QUESTION not in owner_resp.text

    assert viewer_resp.status_code == 200, viewer_resp.text
    viewer_body = viewer_resp.json()
    assert viewer_body["can_view_workspace"] is False
    assert viewer_body["ask"]["turns"] == 1
    assert viewer_body["ask"]["violation_turns"] == 0
    assert viewer_body["structured"] is None
    assert viewer_body["evidence"] is None


def test_repair_span_passes_both_display_allowlists() -> None:
    assert _SPAN_LABELS["repair"] == "인용 수리"
    assert "repair" in _SPAN_NAMES
