"""로컬 Supabase 스택을 상대로 실제 왕복 격리 테스트를 돌리기 위한 공유 픽스처.

관련 태스크: P2-BE-01
설계 근거: 02-CONTEXT.md > D-12, D-14
설계 근거: checklists.json > decisions.db_access

저장소 최초의 `conftest.py`다. 여기 있는 픽스처들은 실제 사용자와 워크스페이스를
**만들고 지운다** — 아래 두 개의 ⚠️ 가 그래서 붙어 있다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
import pytest

from api.db.user import UserDb
from api.main import create_app
from api.settings import ApiSettings

# ⚠️ 로컬 스택 접속 정보를 환경변수에서 읽지 않는다. 저장소 루트의 `.env.local`은
#    **클라우드** 프로젝트의 URL과 secret key를 담고 있어서, 환경을 읽는 픽스처는 그 값이
#    export 된 셸에서 실제 운영 프로젝트에 사용자와 워크스페이스를 만들고 지운다.
#    아래 값은 Supabase CLI가 모든 로컬 스택에 동일하게 발급하는 공개 데모 키이며,
#    포트 54421은 `supabase/config.toml`의 [api] port다 (같은 머신의 다른 프로젝트가
#    543xx를 점유하므로 튜토리얼 기본값 54321이 아니다).
LOCAL_STACK: dict[str, str] = {
    "url": "http://127.0.0.1:54421",
    "publishable_key": (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ".eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9"
        ".CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
    ),
    "admin_key": (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ".eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0"
        ".EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"
    ),
}

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

# 이미 발급한 식별자. 픽스처가 같은 행을 두 번 내주면 그 순간 실패한다.
_ISSUED: set[str] = set()


@dataclass(frozen=True)
class TenantActor:
    """한 테넌트를 대표하는 사용자와 그 사용자가 소유한 워크스페이스."""

    user_id: str
    email: str
    access_token: str
    workspace_id: str
    workspace_name: str


def _assert_loopback() -> None:
    host = urlsplit(LOCAL_STACK["url"]).hostname
    if host not in _LOOPBACK_HOSTS:
        raise RuntimeError(
            f"격리 픽스처는 루프백 주소에서만 돈다 (지정된 host: {host}). "
            "이 픽스처는 사용자와 워크스페이스를 생성·삭제하므로 원격 프로젝트를 가리키면 안 된다."
        )


def _admin_headers() -> dict[str, str]:
    key = LOCAL_STACK["admin_key"]
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def _user_headers(access_token: str, *, representation: bool = False) -> dict[str, str]:
    headers = {
        "apikey": LOCAL_STACK["publishable_key"],
        "Authorization": f"Bearer {access_token}",
    }
    if representation:
        headers["Prefer"] = "return=representation"
    return headers


def _expect(response: httpx.Response, *, what: str) -> Any:
    if response.status_code >= 400:
        raise RuntimeError(
            f"{what} 실패 ({response.status_code}): {response.text[:300]}\n"
            "로컬 스택이 떠 있고 0001~0007이 적용되어 있는지 확인하라 — `supabase status`."
        )
    return response.json()


def _create_actor(client: httpx.Client) -> TenantActor:
    tag = uuid4().hex[:12]
    email = f"test-{tag}@example.test"
    # 리터럴이 아니므로 테스트마다 값이 다르고, 저장소에 남는 상수도 없다.
    credential = f"pw-{uuid4().hex}"

    user = _expect(
        client.post(
            "/auth/v1/admin/users",
            headers=_admin_headers(),
            json={"email": email, "password": credential, "email_confirm": True},
        ),
        what="테스트 사용자 생성",
    )
    session = _expect(
        client.post(
            "/auth/v1/token",
            params={"grant_type": "password"},
            headers={"apikey": LOCAL_STACK["publishable_key"]},
            json={"email": email, "password": credential},
        ),
        what="테스트 사용자 로그인",
    )
    access_token = session["access_token"]

    # ⚠️ 워크스페이스는 요청자 JWT로 만든다. `0007` 섹션 8의 최소권한 매트릭스는
    #    service_role에 workspaces SELECT만 주므로 admin 경로로는 애초에 만들 수 없다 —
    #    워커가 워크스페이스를 만드는 경로가 설계에 없기 때문이며, 이것이 정상이다.
    #    `workspaces_add_owner_member` 트리거가 소유자를 멤버로 자동 등록하므로
    #    멤버십 행을 따로 넣지 않는다 (0001_core_schema.sql:32-84).
    name = f"test-{tag}"
    rows = _expect(
        client.post(
            "/rest/v1/workspaces",
            headers=_user_headers(access_token, representation=True),
            json={"name": name, "slug": name, "owner_id": user["id"]},
        ),
        what="테스트 워크스페이스 생성",
    )

    actor = TenantActor(
        user_id=user["id"],
        email=email,
        access_token=access_token,
        workspace_id=rows[0]["id"],
        workspace_name=name,
    )
    _register(actor)
    return actor


def _register(actor: TenantActor, *, include_workspace: bool = True) -> None:
    fresh = {actor.user_id, actor.email}
    if include_workspace:
        fresh.add(actor.workspace_id)
    collision = fresh & _ISSUED
    if collision:
        raise AssertionError(
            f"픽스처가 이미 발급한 식별자를 다시 내줬다: {sorted(collision)}. "
            "테스트가 서로의 상태에 의존하게 되므로 실행 순서에 따라 결과가 달라진다."
        )
    _ISSUED.update(fresh)


def _destroy_actor(client: httpx.Client, actor: TenantActor) -> None:
    # ⚠️ 순서가 중요하다. `workspaces.owner_id`는 `on delete restrict`라 워크스페이스가
    #    남아 있으면 사용자 삭제가 실패하고, 실패를 삼키면 다음 실행에 잔여 행이 쌓인다.
    #    워크스페이스 삭제는 소유자 JWT로만 가능하다 (service_role에 DELETE 권한이 없다).
    client.request(
        "DELETE",
        "/rest/v1/workspaces",
        params={"id": f"eq.{actor.workspace_id}"},
        headers=_user_headers(actor.access_token),
    )
    _expect(
        client.delete(f"/auth/v1/admin/users/{actor.user_id}", headers=_admin_headers()),
        what="테스트 사용자 삭제",
    )


def _local_stack_is_up() -> bool:
    """스택이 응답하는지만 확인한다 — 어떤 행도 만들거나 지우지 않는다."""
    try:
        response = httpx.get(
            f"{LOCAL_STACK['url']}/rest/v1/",
            headers={"apikey": LOCAL_STACK["publishable_key"]},
            timeout=2.0,
        )
    except httpx.HTTPError:
        return False
    return response.status_code < 500


@pytest.fixture
def local_stack() -> Iterator[httpx.Client]:
    """로컬 스택을 직접 때리는 동기 클라이언트 (픽스처 준비·정리 전용).

    ⚠️ 스택이 없으면 setup 에러가 아니라 **skip**이다. 이 픽스처를 쓰는 테스트는 실제
    사용자와 워크스페이스를 만들어야 해서 스택 없이는 성립하지 않는데, 에러로 두면
    스택이 없는 환경(= GitHub Actions 러너)에서 pytest 잡 전체가 red가 되어 CI 게이트가
    켜지자마자 꺼진다. 02-07이 `apps/worker/tests/test_queue.py`의 통합 픽스처에 세운
    것과 같은 관례다.
    ⚠️ 그러나 skip은 "검증했다"가 아니다. CI는 `-rs`로 건너뛴 테스트를 사유와 함께
    출력해 건너뛴 것이 건너뛴 것으로 보이게 하고, 이 테스트들의 실제 검증 장소는 로컬
    `supabase start` 뒤의 전체 스위트다 (docs/ops/ci-security-gate.md § DB 의존 테스트).
    """
    _assert_loopback()
    if not _local_stack_is_up():
        pytest.skip(f"로컬 Supabase 스택이 응답하지 않는다: {LOCAL_STACK['url']}")
    with httpx.Client(base_url=LOCAL_STACK["url"], timeout=10.0) as client:
        yield client


@pytest.fixture
def two_workspaces_two_users(local_stack: httpx.Client) -> Iterator[tuple[TenantActor, ...]]:
    """테스트마다 고유한 사용자 2명과 그들이 각각 소유한 워크스페이스 2개.

    ⚠️ 이 픽스처를 세션·모듈 스코프로 공유하면 실행 순서와 병렬성에 따라 결과가 달라져
    위양성과 위음성이 함께 생긴다 — 앞선 테스트가 지운 워크스페이스를 뒤 테스트가 때리면
    "격리되어서 Forbidden"과 "이미 없어서 Forbidden"이 구별되지 않는다.
    함수 스코프로 두고 teardown을 보장한다 (02-CONTEXT.md > D-14).
    """
    actors = tuple(_create_actor(local_stack) for _ in range(2))
    try:
        yield actors
    finally:
        for actor in actors:
            _destroy_actor(local_stack, actor)


@pytest.fixture
def workspace_member_with_role(
    local_stack: httpx.Client,
) -> Iterator[Callable[[TenantActor, str], TenantActor]]:
    """소유자 워크스페이스에 별도 인증 사용자를 editor/viewer로 초대한다."""
    members: list[tuple[TenantActor, TenantActor]] = []

    def _create(owner: TenantActor, role: str) -> TenantActor:
        tag = uuid4().hex[:12]
        email = f"test-member-{tag}@example.test"
        credential = f"pw-{uuid4().hex}"
        user = _expect(
            local_stack.post(
                "/auth/v1/admin/users",
                headers=_admin_headers(),
                json={"email": email, "password": credential, "email_confirm": True},
            ),
            what="테스트 멤버 사용자 생성",
        )
        session = _expect(
            local_stack.post(
                "/auth/v1/token",
                params={"grant_type": "password"},
                headers={"apikey": LOCAL_STACK["publishable_key"]},
                json={"email": email, "password": credential},
            ),
            what="테스트 멤버 사용자 로그인",
        )
        _expect(
            local_stack.post(
                "/rest/v1/workspace_members",
                headers=_user_headers(owner.access_token, representation=True),
                json={"workspace_id": owner.workspace_id, "user_id": user["id"], "role": role},
            ),
            what="테스트 워크스페이스 멤버 추가",
        )
        member = TenantActor(
            user_id=user["id"],
            email=email,
            access_token=session["access_token"],
            workspace_id=owner.workspace_id,
            workspace_name=owner.workspace_name,
        )
        _register(member, include_workspace=False)
        members.append((member, owner))
        return member

    try:
        yield _create
    finally:
        for member, owner in members:
            # 발행본은 published_by를 on delete restrict로 보존한다. 워크스페이스
            # fixture보다 멤버 fixture가 먼저 정리되므로, 이 테스트 멤버가 만든 발행본을
            # 소유자 권한으로 먼저 지우지 않으면 auth.users 정리가 23503으로 실패한다.
            _expect(
                local_stack.delete(
                    "/rest/v1/wiki_page_publications",
                    params={"published_by": f"eq.{member.user_id}"},
                    headers=_user_headers(owner.access_token, representation=True),
                ),
                what="테스트 멤버 발행본 삭제",
            )
            _expect(
                local_stack.delete(
                    f"/auth/v1/admin/users/{member.user_id}", headers=_admin_headers()
                ),
                what="테스트 멤버 사용자 삭제",
            )


@pytest.fixture
def isolation_principals(
    local_stack: httpx.Client,
    two_workspaces_two_users: tuple[TenantActor, TenantActor],
    workspace_member_with_role: Callable[[TenantActor, str], TenantActor],
) -> Iterator[tuple[TenantActor, TenantActor, TenantActor, TenantActor, TenantActor]]:
    """D-09's function-scoped requester set, with service role used only by setup fixtures.

    The returned tuple is A owner/editor/viewer, B owner, and an authenticated
    non-member.  Assertion requests must always use one of these requester JWTs
    (or no JWT for anonymous cases); the admin key never leaves fixture setup.
    """

    owner_a, owner_b = two_workspaces_two_users
    editor_a = workspace_member_with_role(owner_a, "editor")
    viewer_a = workspace_member_with_role(owner_a, "viewer")
    non_member = _create_actor(local_stack)
    try:
        yield owner_a, editor_a, viewer_a, owner_b, non_member
    finally:
        _destroy_actor(local_stack, non_member)


@pytest.fixture
def seed_wiki_link(local_stack: httpx.Client) -> Callable[[str, str, str, str], None]:
    """사용자 경로가 쓰기 금지인 그래프 간선을 로컬 테스트 데이터로만 심는다."""

    def _seed(workspace_id: str, from_wiki_id: str, to_wiki_id: str, target_slug: str) -> None:
        _expect(
            local_stack.post(
                "/rest/v1/wiki_links",
                headers={**_admin_headers(), "Prefer": "return=representation"},
                json={
                    "workspace_id": workspace_id,
                    "from_wiki_id": from_wiki_id,
                    "to_wiki_id": to_wiki_id,
                    "target_slug": target_slug,
                },
            ),
            what="테스트 그래프 간선 생성",
        )

    return _seed


@pytest.fixture
def seed_source_chunk(local_stack: httpx.Client) -> Callable[[str, str, str], str]:
    """사용자 쓰기가 금지된 파생 원문 청크를 테스트 준비 단계에서만 심는다."""

    def _seed(workspace_id: str, raw_source_id: str, content: str) -> str:
        rows = _expect(
            local_stack.post(
                "/rest/v1/source_chunks",
                headers={**_admin_headers(), "Prefer": "return=representation"},
                json={
                    "workspace_id": workspace_id,
                    "raw_source_id": raw_source_id,
                    "chunk_index": 0,
                    "content": content,
                    "char_start": 0,
                    "char_end": len(content),
                },
            ),
            what="테스트 원문 청크 생성",
        )
        return str(rows[0]["id"])

    return _seed


@pytest.fixture
def set_workspace_budget(local_stack: httpx.Client) -> Callable[[TenantActor, int], None]:
    """워크스페이스 월 비용 상한을 소유자 JWT로 직접 바꾼다 (OPS-01 경계 테스트용).

    ⚠️ 라우터가 아니라 **PostgREST 직접 호출**이다. `WorkspaceUpdateRequest`가 `name`만
    허용하므로 라우터로는 이 컬럼에 닿을 수 없고, 닿게 만들려고 라우터를 넓히면 상한이
    사용자 편집 표면이 된다. `workspaces` UPDATE는 owner에게 열려 있으므로(0004:171-174)
    소유자 JWT로 가능하다.

    ⚠️ `usage_events`에 가짜 지출을 넣는 대신 **상한을 낮춘다.** `authenticated`에는 그
    테이블 INSERT 권한이 아예 없고(`0009` 섹션 8), admin 키로 우회해 넣으면 테스트가
    감사 기록을 위조하는 셈이 된다. 상한만 조정하면 검증하려는 비교(`spent >= cap`,
    경계 포함)를 정확히 겨냥한다.
    """

    def _set(actor: TenantActor, micros: int) -> None:
        _expect(
            local_stack.patch(
                "/rest/v1/workspaces",
                params={"id": f"eq.{actor.workspace_id}"},
                headers=_user_headers(actor.access_token, representation=True),
                json={"monthly_budget_micros": micros},
            ),
            what="워크스페이스 월 상한 조정",
        )

    return _set


def _local_settings(**overrides: Any) -> ApiSettings:
    # ⚠️ `overrides`로 넘길 수 있는 것은 secret이 아닌 운영 토글뿐이다 — `ApiSettings`에
    #    secret 필드가 애초에 존재하지 않으므로(02-CONTEXT.md > D-06) 이 seam이 그 경계를
    #    넓히지 않는다. 상한값 같은 것을 테스트마다 작은 값으로 바꿔 경계를 정확히
    #    때리기 위해 있다 (500,000자 본문을 실제로 왕복시키지 않는다).
    return ApiSettings(
        SUPABASE_URL=LOCAL_STACK["url"],
        SUPABASE_PUBLISHABLE_KEY=LOCAL_STACK["publishable_key"],
        **overrides,
    )


@pytest.fixture
def authed_client() -> Callable[..., Any]:
    """사용자를 받아 그 사용자의 JWT를 실은 ASGI 클라이언트를 여는 팩토리.

    한 테스트 안에서 두 테넌트의 클라이언트가 동시에 필요하므로 픽스처 자체가 아니라
    팩토리를 돌려준다. `actor=None`이면 자격증명 없는 요청을 만든다.
    `settings_overrides`로 비-secret 설정을 바꿔 경계 테스트를 만들 수 있다.
    """

    @asynccontextmanager
    async def _open(
        actor: TenantActor | None, **settings_overrides: Any
    ) -> AsyncIterator[httpx.AsyncClient]:
        _assert_loopback()
        app = create_app(_local_settings(**settings_overrides), git_sha="test-sha")
        headers = {"Authorization": f"Bearer {actor.access_token}"} if actor else {}
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
                headers=headers,
                timeout=10.0,
            ) as client:
                yield client

    return _open


@pytest.fixture
def user_db() -> Callable[..., Any]:
    """요청자 JWT를 실은 `UserDb`를 직접 여는 팩토리 (읽기 경로 확인용)."""

    @asynccontextmanager
    async def _open(actor: TenantActor) -> AsyncIterator[UserDb]:
        _assert_loopback()
        async with httpx.AsyncClient(timeout=10.0) as client:
            yield UserDb(
                client,
                supabase_url=LOCAL_STACK["url"],
                publishable_key=LOCAL_STACK["publishable_key"],
                access_token=actor.access_token,
            )

    return _open
