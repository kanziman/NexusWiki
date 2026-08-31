"""위키 검증 상태 전이와 공개 발행 표면.

관련 태스크: QC-02, GitHub #82
설계 근거: 05-CONTEXT.md > D-06
설계 근거: openspec/changes/add-wiki-page-publish-controls/design.md
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from typing import Annotated, Any, Final
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

from api.db.user import UserDb
from api.errors import DUPLICATE_SQLSTATE, DatabaseError, WorkspaceForbidden
from api.settings import ApiSettings
from nexuswiki_core.domain import VerificationStatus

router = APIRouter(prefix="/workspaces", tags=["wiki"])
_bearer = HTTPBearer()
_CITATION_SNIPPET_CHARS: Final[int] = 240
_PUBLICATIONS_TABLE: Final[str] = "wiki_page_publications"


class VerifyRequest(BaseModel):
    """클라이언트는 상태와 만료 시점만 고른다. 감사자는 DB가 찍는다."""

    model_config = ConfigDict(extra="forbid")

    verification_status: VerificationStatus
    expires_at: datetime | None = None


class BulkVerifyRequest(BaseModel):
    """선택한 위키 문서들의 검증 상태를 일괄 갱신한다."""

    model_config = ConfigDict(extra="forbid")

    page_ids: list[UUID]
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    expires_at: datetime | None = None


class BulkPublishRequest(BaseModel):
    """선택한 위키 문서들 중 검증된 문서를 일괄 공개 발행한다."""

    model_config = ConfigDict(extra="forbid")

    page_ids: list[UUID]


def _user_db(request: Request, credentials: HTTPAuthorizationCredentials) -> UserDb:
    settings: ApiSettings = request.app.state.settings
    return UserDb(
        request.app.state.http_client,
        supabase_url=settings.SUPABASE_URL,
        publishable_key=settings.SUPABASE_PUBLISHABLE_KEY,
        access_token=credentials.credentials,
    )


@router.patch("/{workspace_id}/wiki/{wiki_id}/verify")
async def verify_wiki_page(
    workspace_id: UUID,
    wiki_id: UUID,
    body: VerifyRequest,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    """RLS가 editor 이상을 판정하고 트리거가 검증 감사 필드를 강제한다."""
    values: dict[str, Any] = {"verification_status": body.verification_status.value}
    if body.expires_at is not None:
        values["expires_at"] = body.expires_at.isoformat()
    row = await _user_db(request, credentials).update_one(
        "wiki_pages",
        match={"id": str(wiki_id), "workspace_id": str(workspace_id)},
        values=values,
    )
    return {
        key: row[key]
        for key in (
            "id",
            "slug",
            "verification_status",
            "verified_by",
            "verified_at",
            "expires_at",
            "disputed",
        )
    }


@router.post("/{workspace_id}/wiki/bulk-verify")
async def bulk_verify_wiki_pages(
    workspace_id: UUID,
    body: BulkVerifyRequest,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    """선택한 위키 문서들을 일괄 검증 처리한다.

    RLS가 editor 이상 권한을 강제하며, 트리거가 검증 감사 필드를 기록한다.
    """
    db = _user_db(request, credentials)
    ws_id = str(workspace_id)
    values: dict[str, Any] = {"verification_status": body.verification_status.value}
    if body.expires_at is not None:
        values["expires_at"] = body.expires_at.isoformat()

    verified_pages: list[dict[str, Any]] = []
    for wiki_id in body.page_ids:
        row = await db.update_one(
            "wiki_pages",
            match={"id": str(wiki_id), "workspace_id": ws_id},
            values=values,
        )
        verified_pages.append(
            {
                key: row[key]
                for key in (
                    "id",
                    "slug",
                    "verification_status",
                    "verified_by",
                    "verified_at",
                    "expires_at",
                    "disputed",
                )
            }
        )

    return {
        "verified_count": len(verified_pages),
        "verified_pages": verified_pages,
    }


@router.post("/{workspace_id}/wiki/bulk-publish")
async def bulk_publish_wiki_pages(
    workspace_id: UUID,
    body: BulkPublishRequest,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    """선택한 위키 문서 중 검증 완료된 문서들을 일괄 공개 발행한다.

    미검증, 분쟁, 만료 상태 문서는 제외하고 유효한 문서만 스냅샷을 생성/갱신한다.
    """
    db = _user_db(request, credentials)
    ws_id = str(workspace_id)

    workspaces = await db.select("workspaces", match={"id": ws_id}, columns="slug", limit=1)
    if len(workspaces) != 1:
        raise WorkspaceForbidden(table="workspaces", affected=len(workspaces))
    workspace_slug = str(workspaces[0]["slug"])
    user_id = _requester_user_id(credentials.credentials)
    now_iso = datetime.now(UTC).isoformat()

    published_pages: list[dict[str, Any]] = []

    for wiki_id in body.page_ids:
        page_id = str(wiki_id)
        pages = await db.select(
            "wiki_pages",
            match={"id": page_id, "workspace_id": ws_id},
            columns="id,slug,title,content,sources,verification_status,expires_at,disputed",
            limit=1,
        )
        if not pages:
            continue
        page = pages[0]
        if (
            page.get("verification_status") != VerificationStatus.VERIFIED.value
            or page.get("disputed") is True
            or _is_expired(page.get("expires_at"))
        ):
            continue

        citations = await _citation_snapshot(
            db, workspace_id=ws_id, source_ids=_source_ids(page.get("sources"))
        )

        values: dict[str, Any] = {
            "wiki_page_id": page_id,
            "workspace_id": ws_id,
            "published_slug": page["slug"],
            "published_title": page["title"],
            "published_content": page["content"],
            "published_citations": citations,
            "published_by": user_id,
            "published_at": now_iso,
        }

        existing = await db.select(
            _PUBLICATIONS_TABLE,
            match={"wiki_page_id": page_id, "workspace_id": ws_id},
            columns="wiki_page_id",
            limit=1,
        )
        if existing:
            row = await db.update_one(
                _PUBLICATIONS_TABLE,
                match={"wiki_page_id": page_id, "workspace_id": ws_id},
                values=values,
            )
        else:
            try:
                row = await db.insert_one(_PUBLICATIONS_TABLE, values=values)
            except DatabaseError as exc:
                if exc.sqlstate != DUPLICATE_SQLSTATE:
                    raise
                row = await db.update_one(
                    _PUBLICATIONS_TABLE,
                    match={"wiki_page_id": page_id, "workspace_id": ws_id},
                    values=values,
                )

        published_pages.append(_publication_response(row, workspace_slug=workspace_slug))

    return {
        "published_count": len(published_pages),
        "published_pages": published_pages,
    }


@router.delete("/{workspace_id}/wiki/{wiki_id}")
async def delete_wiki_page(
    workspace_id: UUID,
    wiki_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    """위키 문서를 영구 삭제한다.

    소유자만 삭제할 수 있으며(RLS wiki_pages_delete_owner),
    DB 외래키 on delete cascade에 의해 연관 청크, 그래프 엣지, 발행 스냅샷, 북마크가 함께 삭제된다.
    """
    db = _user_db(request, credentials)
    ws_id = str(workspace_id)
    page_id = str(wiki_id)

    deleted_row = await db.delete_one(
        "wiki_pages",
        match={"id": page_id, "workspace_id": ws_id},
    )
    return {
        "id": deleted_row["id"],
        "workspace_id": deleted_row["workspace_id"],
        "slug": deleted_row.get("slug", ""),
        "title": deleted_row.get("title", ""),
    }


@router.put("/{workspace_id}/wiki/{wiki_id}/publication")
async def put_wiki_publication(
    workspace_id: UUID,
    wiki_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    """검증된 위키의 현재 본문·인용 스냅샷을 사이드카에 저장한다.

    바디를 받지 않는다. `published_by`는 요청 JWT `sub`이고, 미검증·분쟁·만료
    문서는 리더와 같은 이유로 거부한다.
    """
    db = _user_db(request, credentials)
    ws_id = str(workspace_id)
    page_id = str(wiki_id)
    pages = await db.select(
        "wiki_pages",
        match={"id": page_id, "workspace_id": ws_id},
        columns="id,slug,title,content,sources,verification_status,expires_at,disputed",
        limit=1,
    )
    if len(pages) != 1:
        raise WorkspaceForbidden(table="wiki_pages", affected=len(pages))
    page = pages[0]
    if page.get("disputed") is True or _is_expired(page.get("expires_at")):
        raise WorkspaceForbidden(table=_PUBLICATIONS_TABLE, affected=0)

    workspaces = await db.select("workspaces", match={"id": ws_id}, columns="slug", limit=1)
    if len(workspaces) != 1:
        raise WorkspaceForbidden(table="workspaces", affected=len(workspaces))
    workspace_slug = str(workspaces[0]["slug"])

    values: dict[str, Any] = {
        "wiki_page_id": page_id,
        "workspace_id": ws_id,
        "published_slug": page["slug"],
        "published_title": page["title"],
        "published_content": page["content"],
        "published_citations": await _citation_snapshot(
            db, workspace_id=ws_id, source_ids=_source_ids(page.get("sources"))
        ),
        "published_by": _requester_user_id(credentials.credentials),
        "published_at": datetime.now(UTC).isoformat(),
    }
    existing = await db.select(
        _PUBLICATIONS_TABLE,
        match={"wiki_page_id": page_id, "workspace_id": ws_id},
        columns="wiki_page_id",
        limit=1,
    )
    if existing:
        row = await db.update_one(
            _PUBLICATIONS_TABLE,
            match={"wiki_page_id": page_id, "workspace_id": ws_id},
            values=values,
        )
    else:
        try:
            row = await db.insert_one(_PUBLICATIONS_TABLE, values=values)
        except DatabaseError as exc:
            if exc.sqlstate != DUPLICATE_SQLSTATE:
                raise
            row = await db.update_one(
                _PUBLICATIONS_TABLE,
                match={"wiki_page_id": page_id, "workspace_id": ws_id},
                values=values,
            )
    return _publication_response(row, workspace_slug=workspace_slug)


@router.delete("/{workspace_id}/wiki/{wiki_id}/publication")
async def delete_wiki_publication(
    workspace_id: UUID,
    wiki_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    """해당 위키의 공개 발행본을 한 행만 지운다. 0행은 403이다."""
    row = await _user_db(request, credentials).delete_one(
        _PUBLICATIONS_TABLE,
        match={"wiki_page_id": str(wiki_id), "workspace_id": str(workspace_id)},
    )
    return {"wiki_page_id": row["wiki_page_id"], "workspace_id": row["workspace_id"]}


def _publication_response(row: dict[str, Any], *, workspace_slug: str) -> dict[str, Any]:
    published_slug = str(row["published_slug"])
    return {
        "wiki_page_id": row["wiki_page_id"],
        "workspace_id": row["workspace_id"],
        "published_slug": published_slug,
        "workspace_slug": workspace_slug,
        "published_at": row["published_at"],
        "public_path": f"/p/{workspace_slug}/{published_slug}",
    }


def _requester_user_id(token: str) -> str:
    """액세스 토큰 payload의 `sub`를 읽는다. 서명 검증은 PostgREST가 같은 토큰으로 한다."""
    parts = token.split(".")
    if len(parts) < 2:
        raise WorkspaceForbidden(table=_PUBLICATIONS_TABLE, affected=0)
    padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, json.JSONDecodeError):
        raise WorkspaceForbidden(table=_PUBLICATIONS_TABLE, affected=0) from None
    sub = payload.get("sub") if isinstance(payload, dict) else None
    if not isinstance(sub, str) or not sub:
        raise WorkspaceForbidden(table=_PUBLICATIONS_TABLE, affected=0)
    return sub


def _is_expired(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed < datetime.now(UTC)


def _source_ids(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


async def _citation_snapshot(
    db: UserDb, *, workspace_id: str, source_ids: list[str]
) -> list[dict[str, str]]:
    citations: list[dict[str, str]] = []
    for source_id in source_ids:
        sources = await db.select(
            "raw_sources",
            match={"id": source_id, "workspace_id": workspace_id},
            columns="id,title",
            limit=1,
        )
        if not sources:
            continue
        title = sources[0].get("title")
        chunks = await db.select(
            "source_chunks",
            match={"raw_source_id": source_id, "workspace_id": workspace_id},
            columns="content,chunk_index",
            limit=1,
            order="chunk_index.asc",
        )
        snippet = ""
        if chunks:
            content = chunks[0].get("content")
            if isinstance(content, str):
                snippet = content[:_CITATION_SNIPPET_CHARS]
        citations.append(
            {
                "anchor": source_id,
                "source_title": title if isinstance(title, str) and title else "원문",
                "snippet": snippet,
            }
        )
    return citations
