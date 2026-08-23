"""Ask 스레드 RLS·교차 멤버 403을 로컬 스택에서 증명한다.

관련: openspec/changes/ask-thread-history/tasks.md 슬라이스 1·3
스택이 없으면 skip — conftest.local_stack 과 같은 관례.
"""

# ruff: noqa: ASYNC212

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.conftest import LOCAL_STACK


def _user_headers(access_token: str) -> dict[str, str]:
    return {
        "apikey": LOCAL_STACK["publishable_key"],
        "Authorization": f"Bearer {access_token}",
        "Prefer": "return=representation",
    }


@pytest.mark.asyncio
async def test_same_workspace_member_cannot_read_or_mutate_others_thread(
    two_workspaces_two_users: tuple[Any, Any],
    workspace_member_with_role: Any,
    local_stack: httpx.Client,
) -> None:
    owner, _other_ws = two_workspaces_two_users
    teammate = workspace_member_with_role(owner, "editor")
    probe = local_stack.get("/rest/v1/ask_threads", headers=_user_headers(owner.access_token))
    if probe.status_code >= 400 and "ask_threads" in probe.text:
        pytest.skip("0018_ask_history 가 로컬 스택에 아직 없다")

    created = local_stack.post(
        "/rest/v1/ask_threads",
        headers=_user_headers(owner.access_token),
        json={"workspace_id": owner.workspace_id, "title": "소유자 대화"},
    )
    assert created.status_code < 400, created.text
    thread = created.json()[0] if isinstance(created.json(), list) else created.json()
    thread_id = thread["id"]

    listed_own = local_stack.get(
        "/rest/v1/ask_threads",
        params={"workspace_id": f"eq.{owner.workspace_id}"},
        headers=_user_headers(owner.access_token),
    )
    assert listed_own.status_code == 200
    assert any(row["id"] == thread_id for row in listed_own.json())

    listed_teammate = local_stack.get(
        "/rest/v1/ask_threads",
        params={"workspace_id": f"eq.{owner.workspace_id}"},
        headers=_user_headers(teammate.access_token),
    )
    assert listed_teammate.status_code == 200
    assert listed_teammate.json() == []

    patched = local_stack.patch(
        "/rest/v1/ask_threads",
        params={"id": f"eq.{thread_id}"},
        headers=_user_headers(teammate.access_token),
        json={"title": "가로채기"},
    )
    assert patched.status_code < 500
    body = patched.json()
    assert body == [] or patched.status_code in {401, 403}

    deleted = local_stack.delete(
        "/rest/v1/ask_threads",
        params={"id": f"eq.{thread_id}"},
        headers=_user_headers(teammate.access_token),
    )
    assert deleted.status_code < 500
    content_type = deleted.headers.get("content-type", "")
    deleted_body = deleted.json() if content_type.startswith("application/json") else []
    if isinstance(deleted_body, list):
        assert deleted_body == []


@pytest.mark.asyncio
async def test_api_zero_row_rename_and_delete_are_403(
    two_workspaces_two_users: tuple[Any, Any],
    workspace_member_with_role: Any,
    authed_client: Any,
    local_stack: httpx.Client,
) -> None:
    owner, _other = two_workspaces_two_users
    teammate = workspace_member_with_role(owner, "editor")
    probe = local_stack.get("/rest/v1/ask_threads", headers=_user_headers(owner.access_token))
    if probe.status_code >= 400 and "ask_threads" in probe.text:
        pytest.skip("0018_ask_history 가 로컬 스택에 아직 없다")

    created = local_stack.post(
        "/rest/v1/ask_threads",
        headers=_user_headers(owner.access_token),
        json={"workspace_id": owner.workspace_id, "title": "소유자 대화"},
    )
    assert created.status_code < 400, created.text
    thread = created.json()[0] if isinstance(created.json(), list) else created.json()

    async with authed_client(teammate) as client:
        renamed = await client.patch(
            f"/workspaces/{owner.workspace_id}/ask/threads/{thread['id']}",
            json={"title": "가로채기"},
        )
        deleted = await client.delete(
            f"/workspaces/{owner.workspace_id}/ask/threads/{thread['id']}",
        )
    assert renamed.status_code == 403
    assert deleted.status_code == 403


@pytest.mark.asyncio
async def test_anon_has_no_ask_thread_policy(
    local_stack: httpx.Client,
) -> None:
    response = local_stack.get(
        "/rest/v1/ask_threads",
        headers={"apikey": LOCAL_STACK["publishable_key"]},
    )
    if response.status_code == 404 or "does not exist" in response.text:
        pytest.skip("0018_ask_history 가 로컬 스택에 아직 없다")
    assert response.status_code in {401, 403}
