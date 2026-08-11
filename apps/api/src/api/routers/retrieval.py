"""Authenticated, evidence-only retrieval route."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from api.db.user import UserDb
from api.services.retrieval import HttpQueryEmbeddingClient, RetrievalService

router = APIRouter(prefix="/workspaces", tags=["retrieval"])
_bearer = HTTPBearer()


class RetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=1)
    requested_k: int = Field(default=8, ge=1, le=8)


def _user_db(request: Request, credentials: HTTPAuthorizationCredentials) -> UserDb:
    settings = request.app.state.settings
    return UserDb(
        request.app.state.http_client,
        supabase_url=settings.SUPABASE_URL,
        publishable_key=settings.SUPABASE_PUBLISHABLE_KEY,
        access_token=credentials.credentials,
    )


@router.post("/{workspace_id}/retrieval")
async def retrieve(
    workspace_id: UUID,
    body: RetrievalRequest,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    settings = request.app.state.settings
    if len(body.query) > settings.RETRIEVAL_MAX_QUERY_CHARS:
        raise HTTPException(status_code=422, detail="invalid_query")
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
        result = await service.retrieve(
            workspace_id, body.query, body.requested_k, _user_db(request, credentials)
        )
    except ValueError:
        raise HTTPException(status_code=422, detail="invalid_query") from None
    return {
        "evidence": [
            {
                "id": hit.evidence_id,
                "kind": hit.kind,
                "document_id": hit.document_id,
                "channels": list(hit.channels),
                "contributions": dict(hit.contributions),
                "metadata": dict(hit.metadata),
            }
            for hit in result.evidence
        ],
        "meta": result.meta,
    }
