"""03-07 잡 진행·재시도·취소·예산 표면의 로컬 스택 회귀."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi import status

from api.errors import FORBIDDEN_BODY
from api.routers.jobs import _job_response

TEXT_PATH = "/workspaces/{workspace_id}/sources/text"
JOBS_PATH = "/workspaces/{workspace_id}/sources/{raw_source_id}/jobs"
RETRY_PATH = "/workspaces/{workspace_id}/jobs/{job_id}/retry"
CANCEL_PATH = "/workspaces/{workspace_id}/jobs/{job_id}/cancel"
BUDGET_PATH = "/workspaces/{workspace_id}/budget"


def _body() -> dict[str, str]:
    return {"title": "잡 테스트", "text": f"본문-{uuid4()}"}


async def _enqueue(client: httpx.AsyncClient, workspace_id: str) -> dict[str, str]:
    response = await client.post(TEXT_PATH.format(workspace_id=workspace_id), json=_body())
    assert response.status_code == status.HTTP_202_ACCEPTED, response.text
    return response.json()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", JOBS_PATH),
        ("POST", RETRY_PATH),
        ("POST", CANCEL_PATH),
        ("GET", BUDGET_PATH),
    ],
)
async def test_all_job_routes_require_credentials(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
    method: str,
    path: str,
) -> None:
    owner, _ = two_workspaces_two_users
    rendered = path.format(workspace_id=owner.workspace_id, raw_source_id=uuid4(), job_id=uuid4())
    async with authed_client(None) as client:
        response = await client.request(method, rendered)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_empty_source_job_list_is_200(
    two_workspaces_two_users: tuple[Any, ...], authed_client: Callable[..., Any]
) -> None:
    owner, _ = two_workspaces_two_users
    async with authed_client(owner) as client:
        response = await client.get(
            JOBS_PATH.format(workspace_id=owner.workspace_id, raw_source_id=uuid4())
        )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"jobs": []}


@pytest.mark.asyncio
async def test_enqueued_parse_job_has_ui_progress_without_payload(
    two_workspaces_two_users: tuple[Any, ...], authed_client: Callable[..., Any]
) -> None:
    owner, _ = two_workspaces_two_users
    async with authed_client(owner) as client:
        enqueue = await _enqueue(client, owner.workspace_id)
        response = await client.get(
            JOBS_PATH.format(
                workspace_id=owner.workspace_id, raw_source_id=enqueue["raw_source_id"]
            )
        )
    assert response.status_code == status.HTTP_200_OK
    job = response.json()["jobs"][0]
    assert job["type"] == "parse"
    assert job["step_label"]
    assert job["chain_position"] == 1
    assert "payload" not in job


def test_conflict_check_has_a_named_final_job_progress_step() -> None:
    job = _job_response(
        {
            "id": str(uuid4()),
            "type": "conflict_check",
            "status": "queued",
            "attempts": 0,
            "max_attempts": 3,
            "run_after": None,
            "last_error": None,
            "cancel_requested_at": None,
            "created_at": "2026-08-12T00:00:00Z",
            "updated_at": "2026-08-12T00:00:00Z",
        }
    )

    assert job["step_label"] == "지식 충돌 검사"
    assert job["chain_position"] == 5
    assert job["chain_total"] == 5


@pytest.mark.asyncio
async def test_other_tenant_source_list_is_indistinguishable_from_empty(
    two_workspaces_two_users: tuple[Any, ...], authed_client: Callable[..., Any]
) -> None:
    owner, other = two_workspaces_two_users
    async with authed_client(other) as other_client:
        source = await _enqueue(other_client, other.workspace_id)
    async with authed_client(owner) as client:
        blocked = await client.get(
            JOBS_PATH.format(workspace_id=other.workspace_id, raw_source_id=source["raw_source_id"])
        )
        empty = await client.get(
            JOBS_PATH.format(workspace_id=owner.workspace_id, raw_source_id=uuid4())
        )
    assert blocked.status_code == empty.status_code == status.HTTP_200_OK
    assert blocked.json() == empty.json() == {"jobs": []}


@pytest.mark.asyncio
async def test_non_dead_retry_is_conflict(
    two_workspaces_two_users: tuple[Any, ...], authed_client: Callable[..., Any]
) -> None:
    owner, _ = two_workspaces_two_users
    async with authed_client(owner) as client:
        enqueue = await _enqueue(client, owner.workspace_id)
        response = await client.post(
            RETRY_PATH.format(workspace_id=owner.workspace_id, job_id=enqueue["job_id"])
        )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "not_retryable"}


@pytest.mark.asyncio
async def test_missing_and_other_tenant_retry_are_the_same_forbidden_response(
    two_workspaces_two_users: tuple[Any, ...], authed_client: Callable[..., Any]
) -> None:
    owner, other = two_workspaces_two_users
    async with authed_client(other) as other_client:
        enqueue = await _enqueue(other_client, other.workspace_id)
    async with authed_client(owner) as client:
        blocked = await client.post(
            RETRY_PATH.format(workspace_id=other.workspace_id, job_id=enqueue["job_id"])
        )
        absent = await client.post(
            RETRY_PATH.format(workspace_id=owner.workspace_id, job_id=uuid4())
        )
    assert blocked.status_code == absent.status_code == status.HTTP_403_FORBIDDEN
    assert blocked.json() == absent.json() == FORBIDDEN_BODY


@pytest.mark.asyncio
async def test_queued_cancel_is_immediate_and_second_cancel_is_conflict(
    two_workspaces_two_users: tuple[Any, ...], authed_client: Callable[..., Any]
) -> None:
    owner, _ = two_workspaces_two_users
    async with authed_client(owner) as client:
        enqueue = await _enqueue(client, owner.workspace_id)
        path = CANCEL_PATH.format(workspace_id=owner.workspace_id, job_id=enqueue["job_id"])
        first = await client.post(path)
        second = await client.post(path)
        listed = await client.get(
            JOBS_PATH.format(
                workspace_id=owner.workspace_id, raw_source_id=enqueue["raw_source_id"]
            )
        )
    assert first.status_code == status.HTTP_202_ACCEPTED
    assert first.json()["canceled_immediately"] is True
    assert first.json()["billing"] == {"usage_event_count": 0, "spent_micros": 0}
    assert second.status_code == status.HTTP_409_CONFLICT
    assert second.json() == {"detail": "not_cancellable"}
    assert listed.json()["jobs"][0]["status"] == "canceled"


@pytest.mark.asyncio
async def test_budget_is_display_only_and_empty_usage_costs_zero(
    two_workspaces_two_users: tuple[Any, ...], authed_client: Callable[..., Any]
) -> None:
    owner, _ = two_workspaces_two_users
    async with authed_client(owner) as client:
        response = await client.get(BUDGET_PATH.format(workspace_id=owner.workspace_id))
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert all(
        isinstance(body[key], int) for key in ("cap_micros", "spent_micros", "remaining_micros")
    )
    assert body["spent_micros"] == 0
    assert body["authoritative"] is False
