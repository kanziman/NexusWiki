"""RLS 범위 안에서 제한된 위키 링크 이웃을 읽는 라우터.

관련 태스크: API-04
설계 근거: 05-CONTEXT.md > D-07.1, D-07.2

D-07.2 감사 결론: `api.routers.jobs.list_source_jobs`가 raw source별 모든 잡에
`chain_position`/`chain_total`을 이미 돌려주므로 parse→compile→link_sync→embed의
집계 진행률 표면은 충족된다. 따라서 이 라우터는 별도 job-status 엔드포인트를 만들지 않는다.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from api.db.user import UserDb
from api.settings import ApiSettings

router = APIRouter(prefix="/workspaces", tags=["graph"])
_bearer = HTTPBearer()


class GraphEdge(BaseModel):
    from_wiki_id: str
    to_wiki_id: str
    depth: int


class GraphResponse(BaseModel):
    edges: list[GraphEdge]


def _user_db(request: Request, credentials: HTTPAuthorizationCredentials) -> UserDb:
    settings: ApiSettings = request.app.state.settings
    return UserDb(
        request.app.state.http_client,
        supabase_url=settings.SUPABASE_URL,
        publishable_key=settings.SUPABASE_PUBLISHABLE_KEY,
        access_token=credentials.credentials,
    )


@router.get("/{workspace_id}/graph")
async def graph_neighborhood(
    workspace_id: UUID,
    seed_wiki_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    fanout: Annotated[int, Query(ge=1, le=20)] = 10,
    total_limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> GraphResponse:
    rows = await _user_db(request, credentials).rpc(
        "wiki_graph_neighborhood",
        params={
            "p_workspace_id": str(workspace_id),
            "p_seed_wiki_id": str(seed_wiki_id),
            "p_fanout": fanout,
            "p_total_limit": total_limit,
        },
    )
    if not isinstance(rows, list):
        raise HTTPException(status_code=502, detail="graph_unavailable")
    return GraphResponse(edges=[GraphEdge(**row) for row in rows])
