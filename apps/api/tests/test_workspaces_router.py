"""workspaces 라우터가 상태 코드도 예외 처리도 직접 다루지 않음을 고정하는 회귀 테스트.

여기서는 PostgREST 응답을 MockTransport로 주입한다 — 실제 왕복은
`test_workspaces_isolation.py`가 로컬 스택을 상대로 확인한다.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import httpx
from fastapi import status

from api.errors import FORBIDDEN_BODY
from api.main import create_app
from api.routers.workspaces import WorkspaceUpdateRequest
from api.settings import ApiSettings

REQUESTER_JWT = "requester-jwt"
WORKSPACE_ID = "11111111-1111-4111-8111-111111111111"

UPDATED_ROW = {
    "id": WORKSPACE_ID,
    "name": "renamed",
    "kind": "team",
}


def build_settings() -> ApiSettings:
    return ApiSettings(
        SUPABASE_URL="https://example.invalid",
        SUPABASE_PUBLISHABLE_KEY="sb_publishable_test",
    )


@asynccontextmanager
async def router_client(
    payload: Any,
    *,
    upstream_status: int = 200,
    seen: list[httpx.Request] | None = None,
    authenticated: bool = True,
) -> AsyncIterator[httpx.AsyncClient]:
    """MockTransport를 `app.state.http_client`에 꽂은 ASGI 클라이언트."""

    async def upstream(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(upstream_status, json=payload)

    app = create_app(build_settings(), git_sha="test-sha")
    app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    headers = {"Authorization": f"Bearer {REQUESTER_JWT}"} if authenticated else {}
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            headers=headers,
        ) as client:
            yield client
    finally:
        await app.state.http_client.aclose()


# -----------------------------------------------------------------------------
# 1. 성공 경로 — 라우터가 UserDb의 반환을 그대로 흘려보낸다
# -----------------------------------------------------------------------------


async def test_patch_own_workspace_returns_the_updated_representation() -> None:
    seen: list[httpx.Request] = []
    async with router_client([UPDATED_ROW], seen=seen) as client:
        response = await client.patch(f"/workspaces/{WORKSPACE_ID}", json={"name": "renamed"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == UPDATED_ROW
    assert seen[0].method == "PATCH"
    # 요청자 JWT가 그대로 PostgREST로 전달되어야 RLS가 걸린다.
    assert seen[0].headers["Authorization"] == f"Bearer {REQUESTER_JWT}"


async def test_delete_own_workspace_succeeds() -> None:
    seen: list[httpx.Request] = []
    async with router_client([UPDATED_ROW], seen=seen) as client:
        response = await client.delete(f"/workspaces/{WORKSPACE_ID}")

    assert response.status_code == status.HTTP_200_OK
    assert seen[0].method == "DELETE"


# -----------------------------------------------------------------------------
# 2. 실패 경로 — 렌더링은 단일 핸들러의 몫이다 (02-CONTEXT.md > D-13)
# -----------------------------------------------------------------------------


async def test_zero_affected_rows_are_rendered_by_the_single_handler() -> None:
    # 라우터가 예외를 잡았다면 이 응답은 500이거나 라우터가 만든 본문이 된다.
    async with router_client([]) as client:
        response = await client.patch(f"/workspaces/{WORKSPACE_ID}", json={"name": "renamed"})

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == FORBIDDEN_BODY


async def test_with_check_violation_reaches_the_same_handler() -> None:
    violation = {"code": "42501", "details": None, "hint": None, "message": "denied"}
    async with router_client(violation, upstream_status=403) as client:
        response = await client.delete(f"/workspaces/{WORKSPACE_ID}")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == FORBIDDEN_BODY


# -----------------------------------------------------------------------------
# 3. 본문 검증 실패는 격리 실패와 다른 양식이다
# -----------------------------------------------------------------------------


async def test_empty_name_is_a_validation_failure_not_an_isolation_failure() -> None:
    async with router_client([UPDATED_ROW]) as client:
        response = await client.patch(f"/workspaces/{WORKSPACE_ID}", json={"name": ""})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json() != FORBIDDEN_BODY


async def test_ownership_transfer_field_is_rejected_before_any_upstream_call() -> None:
    # T-02-21: 갱신 요청 모델이 소유권 이전 필드를 받으면 이 라우터가 소유권 이전 경로가 된다.
    seen: list[httpx.Request] = []
    async with router_client([UPDATED_ROW], seen=seen) as client:
        response = await client.patch(
            f"/workspaces/{WORKSPACE_ID}",
            json={"name": "renamed", "owner_id": str(uuid4())},
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert seen == []


def test_update_model_exposes_only_the_name_field() -> None:
    assert set(WorkspaceUpdateRequest.model_fields) == {"name"}


# -----------------------------------------------------------------------------
# 4. 인증 없는 요청은 Forbidden이 아니다
# -----------------------------------------------------------------------------


async def test_request_without_a_bearer_token_is_unauthorized() -> None:
    async with router_client([UPDATED_ROW], authenticated=False) as client:
        response = await client.delete(f"/workspaces/{WORKSPACE_ID}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.status_code != status.HTTP_403_FORBIDDEN


# -----------------------------------------------------------------------------
# 5. 경로와 메서드가 실제로 앱에 붙어 있다
# -----------------------------------------------------------------------------


def test_both_methods_are_exposed_on_the_workspace_path() -> None:
    # ⚠️ FastAPI 0.141의 include_router는 `app.routes`에 개별 APIRoute 대신 불투명한
    #    _IncludedRouter 하나를 남긴다 — `{r.path for r in app.routes}`로는 라우터 안의
    #    경로가 보이지 않는다. 실제로 노출된 표면을 묻는 유일하게 안정적인 창구는
    #    OpenAPI 문서이므로 그쪽을 본다.
    app = create_app(build_settings(), git_sha="test-sha")

    paths = app.openapi()["paths"]

    assert "/workspaces/{workspace_id}" in paths
    assert {"patch", "delete"} <= set(paths["/workspaces/{workspace_id}"])
