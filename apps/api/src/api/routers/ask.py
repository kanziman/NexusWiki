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
from api.errors import WorkspaceForbidden
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
    thread_id: UUID | None = Field(default=None)
    client_turn_id: UUID


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


async def _start_ask_turn(
    *,
    db: UserDb,
    workspace_id: UUID,
    thread_id: UUID | None,
    client_turn_id: UUID,
    query: str,
) -> UUID:
    """SSE를 열기 전에 진행 중 턴을 만들고, 실패를 일반 API 오류로 돌려준다."""
    rows = await db.rpc(
        "start_ask_turn",
        params={
            "p_workspace_id": str(workspace_id),
            "p_thread_id": str(thread_id) if thread_id is not None else None,
            "p_client_turn_id": str(client_turn_id),
            "p_question": query,
        },
    )
    if len(rows) != 1 or not rows[0].get("thread_id"):
        raise WorkspaceForbidden(table="ask_messages", affected=len(rows))
    return UUID(str(rows[0]["thread_id"]))


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
    db = _user_db(request, credentials)
    started_thread_id = await _start_ask_turn(
        db=db,
        workspace_id=workspace_id,
        thread_id=body.thread_id,
        client_turn_id=body.client_turn_id,
        query=body.query,
    )
    service = _ask_service(request)
    events = service.ask(
        workspace_id=workspace_id,
        query=body.query,
        requested_k=body.requested_k,
        template_id=body.template_id,
        user_db=db,
        thread_id=started_thread_id,
        client_turn_id=body.client_turn_id,
    )
    return StreamingResponse(
        _format_sse(events),
        media_type="text/event-stream",
        headers={"X-Ask-Thread-Id": str(started_thread_id)},
    )


class ThreadRenameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=100)


def _thread_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.get("/{workspace_id}/ask/threads")
async def list_ask_threads(
    workspace_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> list[dict[str, Any]]:
    rows = await _user_db(request, credentials).select(
        "ask_threads",
        match={"workspace_id": str(workspace_id)},
        columns="id,title,created_at,updated_at",
        order="updated_at.desc",
    )
    return [_thread_summary(row) for row in rows]


@router.get("/{workspace_id}/ask/threads/{thread_id}")
async def get_ask_thread(
    workspace_id: UUID,
    thread_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    db = _user_db(request, credentials)
    threads = await db.select(
        "ask_threads",
        match={"id": str(thread_id), "workspace_id": str(workspace_id)},
        columns="id,title,created_at,updated_at",
        limit=1,
    )
    if not threads:
        # 부재와 격리 위반을 구분하지 않는다.
        raise WorkspaceForbidden(table="ask_threads", affected=0)
    messages = await db.select(
        "ask_messages",
        match={"thread_id": str(thread_id), "workspace_id": str(workspace_id)},
        columns="id,client_turn_id,question,answer_text,citations,status,created_at",
        order="created_at.asc",
    )
    return {**_thread_summary(threads[0]), "messages": messages}


@router.patch("/{workspace_id}/ask/threads/{thread_id}")
async def rename_ask_thread(
    workspace_id: UUID,
    thread_id: UUID,
    body: ThreadRenameRequest,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    row = await _user_db(request, credentials).update_one(
        "ask_threads",
        match={"id": str(thread_id), "workspace_id": str(workspace_id)},
        values={"title": body.title},
    )
    return _thread_summary(row)


@router.delete("/{workspace_id}/ask/threads/{thread_id}")
async def delete_ask_thread(
    workspace_id: UUID,
    thread_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    row = await _user_db(request, credentials).delete_one(
        "ask_threads",
        match={"id": str(thread_id), "workspace_id": str(workspace_id)},
    )
    return _thread_summary(row)
