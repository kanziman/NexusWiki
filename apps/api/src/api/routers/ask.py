"""D-01/D-02/D-03을 구현하는 SSE Ask 라우트.

관련 태스크: 05-01-PLAN.md Task 2
설계 근거: 05-CONTEXT.md > D-01, D-02, D-03

`retrieval.py`의 인증/설정 배선을 그대로 복사한다(의도적 소규모 중복 — 이 프로젝트의
라우터별 관례). `AskService.ask()`가 내보내는 `(event_name, payload)` 튜플을 실제
SSE 프레임으로 렌더링하는 `_format_sse()`는 여기 둔다 — 서비스 모듈을
프레이밍-비관여로 유지해야 Test 5/6이 이벤트 이름/순서만 독립적으로 단언할 수 있다.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from api.db.user import UserDb
from api.services.ask import AskService, HttpLlmStreamClient
from api.services.retrieval import HttpQueryEmbeddingClient, RetrievalService

router = APIRouter(prefix="/workspaces", tags=["ask"])
_bearer = HTTPBearer()


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=1)
    # retrieval.py의 RetrievalRequest와 동일한 상한 — RetrievalService의
    # DEFAULT_RETRIEVAL_POLICY.requested_k(=8)와 정확히 일치해야 하위 retrieve() 호출이
    # ValueError를 던지지 않는다.
    requested_k: int = Field(default=8, ge=1, le=8)
    template_id: str | None = Field(default=None)


def _user_db(request: Request, credentials: HTTPAuthorizationCredentials) -> UserDb:
    settings = request.app.state.settings
    return UserDb(
        request.app.state.http_client,
        supabase_url=settings.SUPABASE_URL,
        publishable_key=settings.SUPABASE_PUBLISHABLE_KEY,
        access_token=credentials.credentials,
    )


def _ask_service(request: Request) -> AskService:
    service = getattr(request.app.state, "ask_service", None)
    if service is not None:
        return service
    settings = request.app.state.settings
    return AskService(
        RetrievalService(
            HttpQueryEmbeddingClient(
                request.app.state.http_client,
                url=settings.QUERY_EMBEDDING_INTERNAL_URL,
                token=settings.QUERY_EMBEDDING_INTERNAL_TOKEN,
                timeout_seconds=settings.QUERY_EMBEDDING_TIMEOUT_SECONDS,
            )
        ),
        HttpLlmStreamClient(
            request.app.state.http_client,
            url=settings.LLM_STREAM_INTERNAL_URL,
            token=settings.LLM_STREAM_INTERNAL_TOKEN,
            timeout_seconds=settings.LLM_STREAM_TIMEOUT_SECONDS,
        ),
    )


async def _format_sse(events: AsyncIterator[tuple[str, dict[str, Any]]]) -> AsyncIterator[str]:
    async for name, payload in events:
        yield f"event: {name}\ndata: {json.dumps(payload)}\n\n"


@router.post("/{workspace_id}/ask")
async def ask(
    workspace_id: UUID,
    body: AskRequest,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> StreamingResponse:
    settings = request.app.state.settings
    if len(body.query) > settings.RETRIEVAL_MAX_QUERY_CHARS:
        raise HTTPException(status_code=422, detail="invalid_query")
    service = _ask_service(request)
    events = service.ask(
        workspace_id=workspace_id,
        query=body.query,
        requested_k=body.requested_k,
        template_id=body.template_id,
        user_db=_user_db(request, credentials),
    )
    return StreamingResponse(_format_sse(events), media_type="text/event-stream")
