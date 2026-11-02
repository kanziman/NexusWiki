"""위키 변경 제안의 승인 경계와 적용 (ai-control-risk-policy, #198, #200).

로컬 스택에서 요청자 JWT로 호출한다. 권한이 틀리면 조용히 위키가 바뀌는 경로라 실제 RLS로 본다.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import uuid4

import httpx
import pytest

from tests.conftest import LOCAL_STACK
from worker.db.service import ServiceDb  # noqa: TID251 - 워커 적용 경로를 실제 DB로 검증한다
from worker.handlers.wiki_proposal_apply import run_wiki_proposal_apply  # noqa: TID251

_PROPOSED_BODY = "고유한-제안-본문"


def _admin() -> dict[str, str]:
    return {
        "apikey": LOCAL_STACK["admin_key"],
        "Authorization": f"Bearer {LOCAL_STACK['admin_key']}",
        "Prefer": "return=representation",
    }


def _seed(stack: httpx.Client, owner: Any) -> tuple[str, str, str]:
    tag = uuid4().hex[:10]
    source = stack.post(
        "/rest/v1/raw_sources",
        headers=_admin(),
        json={
            "workspace_id": owner.workspace_id,
            "title": "원문",
            "source_type": "text",
            "content": "본문",
            "content_hash": f"h-{tag}",
        },
    )
    assert source.status_code < 400, source.text
    raw_source_id = source.json()[0]["id"]
    page = stack.post(
        "/rest/v1/wiki_pages",
        headers=_admin(),
        json={
            "workspace_id": owner.workspace_id,
            "slug": f"page-{tag}",
            "title": "현재 제목",
            "category": "concepts",
            "content": "사람이 검증한 본문",
            "sources": [raw_source_id],
        },
    )
    assert page.status_code < 400, page.text
    wiki_id = page.json()[0]["id"]
    proposal = stack.post(
        "/rest/v1/rpc/upsert_wiki_write_proposal",
        headers=_admin(),
        json={
            "p_workspace_id": owner.workspace_id,
            "p_wiki_id": wiki_id,
            "p_raw_source_id": raw_source_id,
            "p_risk_reason": "verified_page",
            "p_title": "제안 제목",
            "p_category": "concepts",
            "p_aliases": ["별칭"],
            "p_confidence": "high",
            "p_content": _PROPOSED_BODY,
            "p_evidence_chunk_ids": [],
        },
    )
    assert proposal.status_code < 400, proposal.text
    return wiki_id, raw_source_id, proposal.json()


def _page(stack: httpx.Client, wiki_id: str) -> dict[str, Any]:
    rows = stack.get("/rest/v1/wiki_pages", headers=_admin(), params={"id": f"eq.{wiki_id}"}).json()
    return rows[0]


def _upsert(stack: httpx.Client, body: dict[str, Any]) -> Any:
    return stack.post("/rest/v1/rpc/upsert_wiki_write_proposal", headers=_admin(), json=body)


def _get(stack: httpx.Client, path: str, *, headers: dict[str, str], params: dict[str, str]) -> Any:
    return stack.get(path, headers=headers, params=params)


def _proposal(stack: httpx.Client, proposal_id: str) -> dict[str, Any]:
    rows = stack.get(
        "/rest/v1/wiki_write_proposals", headers=_admin(), params={"id": f"eq.{proposal_id}"}
    ).json()
    return rows[0]


@pytest.mark.asyncio
async def test_only_editors_can_decide_and_foreign_workspaces_cannot_reach_it(
    two_workspaces_two_users: tuple[Any, Any],
    workspace_member_with_role: Any,
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
) -> None:
    owner, outsider = two_workspaces_two_users
    viewer = workspace_member_with_role(owner, "viewer")
    wiki_id, _, proposal_id = _seed(local_stack, owner)
    path = f"/workspaces/{owner.workspace_id}/wiki-proposals/{proposal_id}/approve"

    async with authed_client(viewer) as client:
        assert (await client.post(path)).status_code == 403
    async with authed_client(outsider) as client:
        assert (await client.post(path)).status_code == 403
        # 자기 워크스페이스 경로로 다른 테넌트의 제안을 지목해도 처리되지 않는다.
        foreign = await client.post(
            f"/workspaces/{outsider.workspace_id}/wiki-proposals/{proposal_id}/approve"
        )
        assert foreign.status_code == 409
    async with authed_client(None) as client:
        assert (await client.post(path)).status_code == 401

    assert _proposal(local_stack, proposal_id)["status"] == "pending"
    assert _page(local_stack, wiki_id)["content"] == "사람이 검증한 본문"


@pytest.mark.asyncio
async def test_viewer_cannot_read_proposal_bodies(
    two_workspaces_two_users: tuple[Any, Any],
    workspace_member_with_role: Any,
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
) -> None:
    owner, outsider = two_workspaces_two_users
    viewer = workspace_member_with_role(owner, "viewer")
    _seed(local_stack, owner)
    path = f"/workspaces/{owner.workspace_id}/control/risk"

    async with authed_client(owner) as client:
        owner_resp = await client.get(path)
    async with authed_client(viewer) as client:
        viewer_resp = await client.get(path)
    async with authed_client(outsider) as client:
        outsider_resp = await client.get(path)

    assert outsider_resp.status_code == 403
    assert owner_resp.status_code == 200, owner_resp.text
    body = owner_resp.json()
    assert body["proposals"]["pending"] == 1
    assert body["pending_proposals"][0]["proposed_content"] == _PROPOSED_BODY
    assert body["pending_proposals"][0]["current_content"] == "사람이 검증한 본문"

    assert viewer_resp.status_code == 200, viewer_resp.text
    assert viewer_resp.json()["proposals"]["pending"] == 1
    assert viewer_resp.json()["pending_proposals"] == []
    assert _PROPOSED_BODY not in viewer_resp.text

    direct = _get(
        local_stack,
        "/rest/v1/wiki_write_proposals",
        headers={
            "apikey": LOCAL_STACK["publishable_key"],
            "Authorization": f"Bearer {viewer.access_token}",
        },
        params={},
    )
    assert direct.status_code == 200
    assert direct.json() == []


@pytest.mark.asyncio
async def test_recompile_keeps_a_single_pending_proposal_with_latest_content(
    two_workspaces_two_users: tuple[Any, Any], local_stack: httpx.Client
) -> None:
    owner, _ = two_workspaces_two_users
    wiki_id, raw_source_id, proposal_id = _seed(local_stack, owner)
    second = _upsert(
        local_stack,
        {
            "p_workspace_id": owner.workspace_id,
            "p_wiki_id": wiki_id,
            "p_raw_source_id": raw_source_id,
            "p_risk_reason": "verified_page",
            "p_title": "제안 제목",
            "p_category": "concepts",
            "p_aliases": [],
            "p_confidence": "high",
            "p_content": "최신 제안",
            "p_evidence_chunk_ids": [],
        },
    )
    assert second.json() == proposal_id
    assert _proposal(local_stack, proposal_id)["proposed_content"] == "최신 제안"


@pytest.mark.asyncio
async def test_reject_leaves_the_page_and_a_second_decision_conflicts(
    two_workspaces_two_users: tuple[Any, Any],
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
) -> None:
    owner, _ = two_workspaces_two_users
    wiki_id, _, proposal_id = _seed(local_stack, owner)
    base = f"/workspaces/{owner.workspace_id}/wiki-proposals/{proposal_id}"

    async with authed_client(owner) as client:
        rejected = await client.post(f"{base}/reject")
        again = await client.post(f"{base}/approve")

    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    assert again.status_code == 409
    assert _page(local_stack, wiki_id)["content"] == "사람이 검증한 본문"


@pytest.mark.asyncio
async def test_approval_enqueues_apply_and_applies_exactly_once(
    two_workspaces_two_users: tuple[Any, Any],
    authed_client: Callable[..., Any],
    local_stack: httpx.Client,
) -> None:
    owner, _ = two_workspaces_two_users
    wiki_id, raw_source_id, proposal_id = _seed(local_stack, owner)

    async with authed_client(owner) as client:
        approved = await client.post(
            f"/workspaces/{owner.workspace_id}/wiki-proposals/{proposal_id}/approve"
        )
    assert approved.status_code == 200, approved.text
    jobs = _get(
        local_stack,
        "/rest/v1/jobs",
        headers=_admin(),
        params={"workspace_id": f"eq.{owner.workspace_id}", "type": "eq.wiki_proposal_apply"},
    ).json()
    assert len(jobs) == 1
    assert jobs[0]["payload"]["proposal_id"] == proposal_id
    assert _page(local_stack, wiki_id)["content"] == "사람이 검증한 본문"

    job_id = jobs[0]["id"]
    async with httpx.AsyncClient(
        base_url=f"{LOCAL_STACK['url']}/rest/v1", headers=_admin()
    ) as service:
        db = ServiceDb(service)
        for _ in range(2):
            await run_wiki_proposal_apply(
                db,
                job_id=job_id,
                workspace_id=owner.workspace_id,
                payload=jobs[0]["payload"],
            )

    page = _page(local_stack, wiki_id)
    assert page["content"] == _PROPOSED_BODY
    assert page["title"] == "제안 제목"
    assert page["search_tsv"]
    assert raw_source_id in page["sources"]
    assert _proposal(local_stack, proposal_id)["status"] == "applied"
    revisions = _get(
        local_stack,
        "/rest/v1/wiki_page_revisions",
        headers=_admin(),
        params={"wiki_id": f"eq.{wiki_id}"},
    ).json()
    assert [row["previous_content"] for row in revisions] == ["사람이 검증한 본문"]
