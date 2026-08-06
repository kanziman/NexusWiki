"""SEC-06: 교차 테넌트 접근이 애플리케이션 경로에서 전부 Forbidden으로 돌아옴을 증명한다.

관련 태스크: P2-BE-01
설계 근거: 02-CONTEXT.md > D-11, D-12, D-14

이 파일은 02-03이 `MockTransport`로 가정했던 두 가지 — "RLS가 막은 쓰기는 대표 표현에서
0행으로 돌아온다"와 "부재와 격리 위반이 구별되지 않는다" — 를 로컬 스택을 상대로 하는
실제 왕복으로 처음 확인한다.

⚠️ 이 테스트가 공허해지는 두 경로를 구조적으로 막는다.
   (1) 같은 워크스페이스를 두 번 쓰는 것 — 모든 교차 케이스가 두 id의 상이함을 먼저 단언한다.
   (2) 인증 없는 요청 — 자격증명이 없으면 Unauthorized라 Forbidden 단언이 우연히 통과해버린다.
       그래서 인증 없는 경우를 별도 케이스로 분리해 Forbidden이 **아님**을 단언한다.
   그리고 정상 소유자 경로가 성공함을 함께 고정한다 — 전부 거절하는 서버도 교차 케이스만
   보면 통과하기 때문이다.
"""

from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi import status

from api.errors import FORBIDDEN_BODY

# 픽스처가 돌려주는 `TenantActor`는 conftest가 소유한다. `--import-mode=importlib`에서
# 테스트 디렉터리는 패키지가 아니므로 그 이름을 import 하지 않고 구조적으로만 쓴다.
TenantPair = tuple[Any, Any]

# 새 라우터가 늘면 이 표에 **행만 추가**한다 (02-CONTEXT.md > D-14).
# (HTTP 메서드, 경로 템플릿, 요청 본문, 설명)
CROSS_TENANT_CASES: list[tuple[str, str, dict[str, Any] | None, str]] = [
    ("PATCH", "/workspaces/{workspace_id}", {"name": "hijacked"}, "남의 워크스페이스 이름 변경"),
    ("DELETE", "/workspaces/{workspace_id}", None, "남의 워크스페이스 삭제"),
]

CASE_IDS = [f"{method}-{description}" for method, _, _, description in CROSS_TENANT_CASES]

# 데코레이터를 한 번만 정의해 모든 교차 케이스가 정확히 같은 표를 돌게 한다.
CASE = pytest.mark.parametrize(
    ("method", "path", "body", "description"), CROSS_TENANT_CASES, ids=CASE_IDS
)


def _request_kwargs(body: dict[str, Any] | None) -> dict[str, Any]:
    return {"json": body} if body is not None else {}


def _assert_carries_a_bearer_token(client: httpx.AsyncClient) -> None:
    # 자격증명 없는 요청은 Unauthorized를 받으므로, 헤더를 확인하지 않으면 "인증되지
    # 않아서 실패한 것"을 "격리되어서 실패한 것"으로 착각할 수 있다.
    assert client.headers["Authorization"].startswith("Bearer ")


# -----------------------------------------------------------------------------
# 1. 교차 테넌트 쓰기 — 양방향 모두 Forbidden
# -----------------------------------------------------------------------------


@CASE
async def test_cross_tenant_write_is_forbidden(
    two_workspaces_two_users: TenantPair,
    authed_client: Any,
    method: str,
    path: str,
    body: dict[str, Any] | None,
    description: str,
) -> None:
    alice, bob = two_workspaces_two_users
    assert alice.workspace_id != bob.workspace_id, description

    async with authed_client(alice) as client:
        _assert_carries_a_bearer_token(client)
        response = await client.request(
            method,
            path.format(workspace_id=bob.workspace_id),
            **_request_kwargs(body),
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == FORBIDDEN_BODY


@CASE
async def test_cross_tenant_write_is_forbidden_in_the_other_direction(
    two_workspaces_two_users: TenantPair,
    authed_client: Any,
    method: str,
    path: str,
    body: dict[str, Any] | None,
    description: str,
) -> None:
    # 방향을 뒤집어도 같아야 한다 — 한쪽만 검사하면 "첫 번째 사용자가 특별한" 구현이 통과한다.
    alice, bob = two_workspaces_two_users
    assert bob.workspace_id != alice.workspace_id, description

    async with authed_client(bob) as client:
        _assert_carries_a_bearer_token(client)
        response = await client.request(
            method,
            path.format(workspace_id=alice.workspace_id),
            **_request_kwargs(body),
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


# -----------------------------------------------------------------------------
# 2. 존재하지 않는 리소스도 Not Found가 아니라 Forbidden이다 (02-CONTEXT.md > D-12)
# -----------------------------------------------------------------------------


@CASE
async def test_absent_resource_is_forbidden_not_not_found(
    two_workspaces_two_users: TenantPair,
    authed_client: Any,
    method: str,
    path: str,
    body: dict[str, Any] | None,
    description: str,
) -> None:
    alice, _ = two_workspaces_two_users
    ghost_id = uuid4()

    async with authed_client(alice) as client:
        response = await client.request(
            method,
            path.format(workspace_id=ghost_id),
            **_request_kwargs(body),
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.status_code != status.HTTP_404_NOT_FOUND
    assert response.json() == FORBIDDEN_BODY


async def test_second_delete_of_own_workspace_is_forbidden(
    two_workspaces_two_users: TenantPair,
    authed_client: Any,
) -> None:
    """자기 워크스페이스 재삭제도 Forbidden이다 — 02-CONTEXT.md > D-12의 직접 귀결이다.

    두 번째 호출을 다르게 응답하려면 "그 id의 리소스가 존재하는가"를 응답에 실어야 하고,
    그 순간 남의 워크스페이스에 대해서도 같은 정보가 새어나간다. 버그가 아니다.
    """
    alice, _ = two_workspaces_two_users

    async with authed_client(alice) as client:
        first = await client.delete(f"/workspaces/{alice.workspace_id}")
        second = await client.delete(f"/workspaces/{alice.workspace_id}")

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_403_FORBIDDEN
    assert second.json() == FORBIDDEN_BODY


# -----------------------------------------------------------------------------
# 3. 정상 경로가 살아 있다 — 전부 거절하는 서버는 위 케이스를 그냥 통과한다
# -----------------------------------------------------------------------------


@CASE
async def test_owner_can_write_to_their_own_workspace(
    two_workspaces_two_users: TenantPair,
    authed_client: Any,
    method: str,
    path: str,
    body: dict[str, Any] | None,
    description: str,
) -> None:
    alice, _ = two_workspaces_two_users

    async with authed_client(alice) as client:
        response = await client.request(
            method,
            path.format(workspace_id=alice.workspace_id),
            **_request_kwargs(body),
        )

    assert response.status_code == status.HTTP_200_OK, description
    assert response.json()["id"] == alice.workspace_id


# -----------------------------------------------------------------------------
# 4. 인증 없는 요청은 Forbidden이 아니다 (위양성 차단)
# -----------------------------------------------------------------------------


@CASE
async def test_unauthenticated_write_is_unauthorized_not_forbidden(
    two_workspaces_two_users: TenantPair,
    authed_client: Any,
    method: str,
    path: str,
    body: dict[str, Any] | None,
    description: str,
) -> None:
    _, bob = two_workspaces_two_users

    async with authed_client(None) as client:
        assert "Authorization" not in client.headers
        response = await client.request(
            method,
            path.format(workspace_id=bob.workspace_id),
            **_request_kwargs(body),
        )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED, description
    assert response.status_code != status.HTTP_403_FORBIDDEN


# -----------------------------------------------------------------------------
# 5. 읽기 경로에는 0행 규칙이 없다 (02-CONTEXT.md > D-11)
# -----------------------------------------------------------------------------


async def test_read_that_rls_blocks_returns_empty_instead_of_forbidden(
    two_workspaces_two_users: TenantPair,
    user_db: Any,
) -> None:
    """RLS가 막은 조회는 빈 결과이며 예외가 아니다.

    쓰기 전용 메서드를 따로 두지 않았다면 이 빈 결과가 Forbidden이 되었을 것이고,
    "정상적으로 비어 있는 조회"를 표현할 방법이 사라졌을 것이다.
    """
    alice, bob = two_workspaces_two_users
    assert alice.workspace_id != bob.workspace_id

    async with user_db(alice) as db:
        blocked = await db.select("workspaces", match={"id": bob.workspace_id})
        own = await db.select("workspaces", match={"id": alice.workspace_id})

    assert blocked == []
    assert [row["id"] for row in own] == [alice.workspace_id]


# -----------------------------------------------------------------------------
# 6. 픽스처가 테스트마다 새 행을 준다 (실행 순서·병렬성 무관)
# -----------------------------------------------------------------------------


async def test_each_test_receives_freshly_created_rows(
    two_workspaces_two_users: TenantPair,
) -> None:
    # conftest의 픽스처는 세션 안에서 이미 발급한 식별자를 다시 내주면 스스로 실패한다.
    # 이 테스트는 그 계약이 실제로 살아 있는지를 확인할 뿐이다.
    alice, bob = two_workspaces_two_users

    assert alice.workspace_id != bob.workspace_id
    assert alice.user_id != bob.user_id
    assert alice.email != bob.email
    assert alice.workspace_name.startswith("test-")
    assert bob.workspace_name.startswith("test-")
