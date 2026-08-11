"""위키 검증 상태 전이 표면.

관련 태스크: QC-02
설계 근거: 05-CONTEXT.md > D-06
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

from api.db.user import UserDb
from api.settings import ApiSettings
from nexuswiki_core.domain import VerificationStatus

router = APIRouter(prefix="/workspaces", tags=["wiki"])
_bearer = HTTPBearer()


class VerifyRequest(BaseModel):
    """클라이언트는 상태와 만료 시점만 고른다. 감사자는 DB가 찍는다."""

    model_config = ConfigDict(extra="forbid")

    verification_status: VerificationStatus
    expires_at: datetime | None = None


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
