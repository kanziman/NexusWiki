"""위키 공개 발행 경로의 스냅샷 저장·격리·역할 거부를 증명한다.

GitHub: #82 · #83 · #84
설계 근거: openspec/changes/add-wiki-page-publish-controls/design.md
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import status

from api.errors import FORBIDDEN_BODY

TenantPair = tuple[Any, Any]


def _page_values(
    workspace_id: str, *, slug: str | None = None, sources: list[str] | None = None
) -> dict[str, Any]:
    return {
        "workspace_id": workspace_id,
        "slug": slug or f"pub-{uuid4().hex}",
        "title": "Background Job Lifecycle",
        "category": "concepts",
        "content": "발행 본문",
        "sources": sources or [],
    }


async def _insert_verified_page(
    user_db: Any,
    authed_client: Any,
    actor: Any,
    *,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    async with user_db(actor) as db:
        page = await db.insert_one(
            "wiki_pages",
            values=_page_values(actor.workspace_id, sources=sources),
        )
    verify_path = f"/workspaces/{actor.workspace_id}/wiki/{page['id']}/verify"
    async with authed_client(actor) as client:
        verified = await client.patch(verify_path, json={"verification_status": "verified"})
    assert verified.status_code == status.HTTP_200_OK
    return page


def _publication_path(workspace_id: str, wiki_id: str) -> str:
    return f"/workspaces/{workspace_id}/wiki/{wiki_id}/publication"


async def test_owner_publishes_verified_page_with_citation_snapshot(
    two_workspaces_two_users: TenantPair,
    authed_client: Any,
    user_db: Any,
) -> None:
    owner, _ = two_workspaces_two_users
    async with user_db(owner) as db:
        source = await db.insert_one(
            "raw_sources",
            values={
                "workspace_id": owner.workspace_id,
                "title": "원문 가이드",
                "source_type": "text",
                "content": "원문 앞부분 스니펫",
                "content_hash": uuid4().hex,
            },
        )
    page = await _insert_verified_page(user_db, authed_client, owner, sources=[source["id"]])

    async with authed_client(owner) as client:
        published = await client.put(_publication_path(owner.workspace_id, page["id"]))
    assert published.status_code == status.HTTP_200_OK
    body = published.json()
    assert body["published_slug"] == page["slug"]
    assert body["workspace_slug"] == owner.workspace_name
    assert body["public_path"] == f"/p/{owner.workspace_name}/{page['slug']}"
    assert body["wiki_page_id"] == page["id"]

    async with user_db(owner) as db:
        rows = await db.select(
            "wiki_page_publications",
            match={"wiki_page_id": page["id"], "workspace_id": owner.workspace_id},
            limit=1,
        )
    assert len(rows) == 1
    assert rows[0]["published_title"] == "Background Job Lifecycle"
    assert rows[0]["published_content"] == "발행 본문"
    assert rows[0]["published_by"] == owner.user_id
    citations = rows[0]["published_citations"]
    assert citations == [
        {
            "anchor": source["id"],
            "source_title": "원문 가이드",
            "snippet": "",
        }
    ]


async def test_publish_is_upsert_and_foreign_workspace_is_forbidden(
    two_workspaces_two_users: TenantPair,
    authed_client: Any,
    user_db: Any,
) -> None:
    alice, bob = two_workspaces_two_users
    assert alice.workspace_id != bob.workspace_id
    page = await _insert_verified_page(user_db, authed_client, bob)

    async with authed_client(alice) as client:
        blocked = await client.put(_publication_path(bob.workspace_id, page["id"]))
    assert blocked.status_code == status.HTTP_403_FORBIDDEN
    assert blocked.json() == FORBIDDEN_BODY

    async with authed_client(bob) as client:
        first = await client.put(_publication_path(bob.workspace_id, page["id"]))
        second = await client.put(_publication_path(bob.workspace_id, page["id"]))
    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK

    async with user_db(bob) as db:
        rows = await db.select(
            "wiki_page_publications",
            match={"wiki_page_id": page["id"], "workspace_id": bob.workspace_id},
        )
    assert len(rows) == 1


async def test_unverified_page_and_viewer_cannot_publish_or_unpublish(
    two_workspaces_two_users: TenantPair,
    authed_client: Any,
    user_db: Any,
    workspace_member_with_role: Any,
) -> None:
    owner, _ = two_workspaces_two_users
    editor = workspace_member_with_role(owner, "editor")
    viewer = workspace_member_with_role(owner, "viewer")
    async with user_db(owner) as db:
        unverified = await db.insert_one(
            "wiki_pages",
            values=_page_values(owner.workspace_id, slug=f"unverified-{uuid4().hex}"),
        )
    verified = await _insert_verified_page(user_db, authed_client, owner)

    async with authed_client(owner) as client:
        rejected = await client.put(_publication_path(owner.workspace_id, unverified["id"]))
        published = await client.put(_publication_path(owner.workspace_id, verified["id"]))
    assert rejected.status_code == status.HTTP_403_FORBIDDEN
    assert rejected.json() == FORBIDDEN_BODY
    assert published.status_code == status.HTTP_200_OK

    async with authed_client(editor) as client:
        editor_put = await client.put(_publication_path(owner.workspace_id, verified["id"]))
    assert editor_put.status_code == status.HTTP_200_OK

    async with authed_client(viewer) as client:
        viewer_put = await client.put(_publication_path(owner.workspace_id, verified["id"]))
        viewer_delete = await client.delete(_publication_path(owner.workspace_id, verified["id"]))
    assert viewer_put.status_code == status.HTTP_403_FORBIDDEN
    assert viewer_put.json() == FORBIDDEN_BODY
    assert viewer_delete.status_code == status.HTTP_403_FORBIDDEN
    assert viewer_delete.json() == FORBIDDEN_BODY

    async with authed_client(owner) as client:
        deleted = await client.delete(_publication_path(owner.workspace_id, verified["id"]))
    assert deleted.status_code == status.HTTP_200_OK
    assert deleted.json() == {
        "wiki_page_id": verified["id"],
        "workspace_id": owner.workspace_id,
    }

    async with user_db(owner) as db:
        remaining = await db.select(
            "wiki_page_publications",
            match={"wiki_page_id": verified["id"], "workspace_id": owner.workspace_id},
        )
    assert remaining == []


async def test_delete_missing_publication_is_forbidden(
    two_workspaces_two_users: TenantPair,
    authed_client: Any,
    user_db: Any,
) -> None:
    owner, _ = two_workspaces_two_users
    page = await _insert_verified_page(user_db, authed_client, owner)
    async with authed_client(owner) as client:
        missing = await client.delete(_publication_path(owner.workspace_id, page["id"]))
    assert missing.status_code == status.HTTP_403_FORBIDDEN
    assert missing.json() == FORBIDDEN_BODY
