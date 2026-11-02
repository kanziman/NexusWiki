"""Authenticated, evidence-only retrieval route."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from api.db.user import UserDb
from api.errors import WorkspaceForbidden
from api.services.retrieval import HttpQueryEmbeddingClient, RetrievalService

router = APIRouter(prefix="/workspaces", tags=["retrieval"])
_bearer = HTTPBearer()


class RetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=1)
    requested_k: int = Field(default=8, ge=1, le=8)


class RetrievalEvidence(BaseModel):
    """A retrieval record, deliberately not an answer or citation payload."""

    id: str
    kind: str
    document_id: str
    channels: list[str]
    contributions: dict[str, float]
    metadata: dict[str, Any]


class RetrievalResponse(BaseModel):
    """The Phase 4 boundary: evidence plus safe retrieval observability only."""

    evidence: list[RetrievalEvidence]
    meta: dict[str, Any]


def _user_db(request: Request, credentials: HTTPAuthorizationCredentials) -> UserDb:
    settings = request.app.state.settings
    return UserDb(
        request.app.state.http_client,
        supabase_url=settings.SUPABASE_URL,
        publishable_key=settings.SUPABASE_PUBLISHABLE_KEY,
        access_token=credentials.credentials,
    )


async def _require_member(db: UserDb, *, workspace_id: UUID) -> None:
    """임베딩 호출 전에 요청자의 JWT와 멤버십을 확인한다.

    ⚠️ 서비스는 RLS가 평가되는 첫 RPC보다 먼저 임베딩을 호출하고, 워커는 경로의 워크스페이스로
    `service_role` 비용 행을 쓴다. 이 게이트가 없으면 로그인 없이 다른 테넌트의 월 상한을 소진해
    수집과 Ask를 멈출 수 있다. Ask 경로는 `start_ask_turn`이 같은 역할을 한다.
    """
    result = await db.rpc(
        "has_workspace_role",
        params={"ws_id": str(workspace_id), "min_role": "viewer"},
    )
    if not result or result[0] is not True:
        raise WorkspaceForbidden(table="workspace_members", affected=0)


@router.post("/{workspace_id}/retrieval")
async def retrieve(
    workspace_id: UUID,
    body: RetrievalRequest,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> RetrievalResponse:
    settings = request.app.state.settings
    if len(body.query) > settings.RETRIEVAL_MAX_QUERY_CHARS:
        raise HTTPException(status_code=422, detail="invalid_query")
    db = _user_db(request, credentials)
    await _require_member(db, workspace_id=workspace_id)
    service = getattr(request.app.state, "retrieval_service", None)
    if service is None:
        service = RetrievalService(
            HttpQueryEmbeddingClient(
                request.app.state.http_client,
                url=settings.QUERY_EMBEDDING_INTERNAL_URL,
                token=settings.QUERY_EMBEDDING_INTERNAL_TOKEN,
                timeout_seconds=settings.QUERY_EMBEDDING_TIMEOUT_SECONDS,
            )
        )
    try:
        result = await service.retrieve(workspace_id, body.query, body.requested_k, db)
    except ValueError:
        raise HTTPException(status_code=422, detail="invalid_query") from None
    return RetrievalResponse(
        evidence=[
            RetrievalEvidence(
                id=hit.evidence_id,
                kind=hit.kind,
                document_id=hit.document_id,
                channels=list(hit.channels),
                contributions=dict(hit.contributions),
                metadata=dict(hit.metadata),
            )
            for hit in result.evidence
        ],
        meta=result.meta,
    )
