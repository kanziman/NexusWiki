"""테넌트 격리를 실제 HTTP 왕복으로 증명하기 위한 최소 workspaces 라우터.

관련 태스크: P2-BE-01
설계 근거: 02-CONTEXT.md > D-11, D-12, D-13

⚠️ 이 라우터는 제품 기능이 아니라 **격리 증명 표면**이다. 도메인 라우터가 하나도 없으면
"애플리케이션 경로에서의 교차 테넌트 시도가 Forbidden으로 돌아온다"를 확인할 표면 자체가
없다. 실제 도메인 라우터는 Phase 3~5가 세운다 (02-SPEC.md Boundaries).

소비자: apps/api/tests/test_workspaces_isolation.py (SEC-06)
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from api.db.user import UserDb
from api.settings import ApiSettings

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

# ⚠️ 이 모듈에는 상태 코드 리터럴도 인라인 상태 코드 응답도 두지 않는다. `health.py`는
#    JSONResponse에 상태 코드를 직접 실어 보내지만 여기서는 의도적으로 그 습관을 깬다 —
#    라우터마다 상태 코드가 흩어지면 "부재와 격리 위반을 구분하지 않는다"가 라우터마다
#    다시 결정되고 SEC-04의 "한 곳" 조건이 깨진다. 근거: 02-CONTEXT.md > D-12, D-13.
#
#    책임 분배: 격리 실패 렌더링은 `api.errors`의 단일 핸들러가, 자격증명 없는 요청은
#    아래 HTTPBearer가 맡는다. 라우터는 어느 쪽도 스스로 판정하지 않는다.
_bearer = HTTPBearer()

_WORKSPACES_TABLE = "workspaces"


class WorkspaceUpdateRequest(BaseModel):
    """갱신 가능한 필드만 노출하는 요청 모델.

    ⚠️ `extra="forbid"`가 이 모델의 핵심이다. 모르는 필드를 조용히 버리면 소유권 이전
    필드를 실은 요청이 "성공했는데 아무 일도 일어나지 않았다"로 보이고, 반대로 통과시키면
    이 라우터가 곧 소유권 이전 경로가 된다 (T-02-21). 둘 다 아니고 거절한다.
    """

    model_config = ConfigDict(extra="forbid")

    # 상한 100은 `0001_core_schema.sql`의 workspaces.name CHECK와 같은 값이다.
    name: str = Field(min_length=1, max_length=100)


def _user_db(request: Request, credentials: HTTPAuthorizationCredentials) -> UserDb:
    """요청자 JWT를 실은 어댑터를 만든다.

    ⚠️ 여기에 실리는 것은 요청자 JWT이며 service key가 아니다. service key를 실으면
    BYPASSRLS라 `0004`의 격리 정책이 통째로 우회된다.
    근거: checklists.json > decisions.db_access.
    """
    settings: ApiSettings = request.app.state.settings
    return UserDb(
        request.app.state.http_client,
        supabase_url=settings.SUPABASE_URL,
        publishable_key=settings.SUPABASE_PUBLISHABLE_KEY,
        access_token=credentials.credentials,
    )


@router.patch("/{workspace_id}")
async def update_workspace(
    workspace_id: UUID,
    payload: WorkspaceUpdateRequest,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    """워크스페이스 한 행을 갱신한다. 격리 판정은 RLS와 `UserDb`의 몫이다."""
    db = _user_db(request, credentials)
    return await db.update_one(
        _WORKSPACES_TABLE,
        match={"id": str(workspace_id)},
        values=payload.model_dump(),
    )


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    """워크스페이스 한 행을 삭제한다. 대상이 없든 남의 것이든 응답은 같다 (D-12)."""
    db = _user_db(request, credentials)
    return await db.delete_one(_WORKSPACES_TABLE, match={"id": str(workspace_id)})
