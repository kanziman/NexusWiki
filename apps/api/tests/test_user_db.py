"""쓰기 경로의 0행·다중행 차단과 단일 403 핸들러 회귀 테스트."""

from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from api.db.user import UserDb
from api.errors import DatabaseError, WorkspaceForbidden, register_error_handlers

SUPABASE_URL = "https://example.invalid"
PUBLISHABLE_KEY = "sb_publishable_test"
REQUESTER_JWT = "requester-jwt"

WORKSPACE_ID = "11111111-1111-4111-8111-111111111111"
ROW_ID = "33333333-3333-4333-8333-333333333333"

ONE_ROW = [{"id": ROW_ID, "workspace_id": WORKSPACE_ID, "name": "after"}]
TWO_ROWS = [
    {"id": ROW_ID, "workspace_id": WORKSPACE_ID},
    {"id": ROW_ID, "workspace_id": "other"},
]

# PostgREST가 WITH CHECK 위반을 돌려주는 형태. 상태 코드와 code가 함께 온다.
WITH_CHECK_VIOLATION = {
    "code": "42501",
    "details": None,
    "hint": None,
    "message": 'new row violates row-level security policy for table "workspaces"',
}


def db_returning(
    payload: Any,
    *,
    status: int = 200,
    seen: list[httpx.Request] | None = None,
) -> tuple[UserDb, httpx.AsyncClient]:
    async def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=payload)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    db = UserDb(
        client,
        supabase_url=SUPABASE_URL,
        publishable_key=PUBLISHABLE_KEY,
        access_token=REQUESTER_JWT,
    )
    return db, client


# -----------------------------------------------------------------------------
# 1. 쓰기 경로 — 정확히 1행이 아니면 진행하지 않는다 (02-CONTEXT.md > D-11)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_one_raises_when_no_row_was_affected() -> None:
    # RLS의 USING이 막으면 예외가 아니라 0행이 돌아온다. 그것을 성공으로 넘기면
    # 격리 실패가 조용히 지나간다.
    db, client = db_returning([])
    async with client:
        with pytest.raises(WorkspaceForbidden):
            await db.update_one("workspaces", match={"id": ROW_ID}, values={"name": "x"})


@pytest.mark.asyncio
async def test_delete_one_raises_when_no_row_was_affected() -> None:
    db, client = db_returning([])
    async with client:
        with pytest.raises(WorkspaceForbidden):
            await db.delete_one("workspaces", match={"id": ROW_ID})


@pytest.mark.asyncio
async def test_update_one_raises_when_more_than_one_row_matched() -> None:
    # 2행 이상은 스코프가 의도보다 넓게 잡혔다는 뜻이다 (SPEC Edge Coverage R4).
    db, client = db_returning(TWO_ROWS)
    async with client:
        with pytest.raises(WorkspaceForbidden):
            await db.update_one("workspaces", match={"id": ROW_ID}, values={"name": "x"})


@pytest.mark.asyncio
async def test_delete_one_raises_when_more_than_one_row_matched() -> None:
    db, client = db_returning(TWO_ROWS)
    async with client:
        with pytest.raises(WorkspaceForbidden):
            await db.delete_one("workspaces", match={"id": ROW_ID})


@pytest.mark.asyncio
async def test_update_one_returns_the_single_affected_row() -> None:
    seen: list[httpx.Request] = []
    db, client = db_returning(ONE_ROW, seen=seen)
    async with client:
        row = await db.update_one(
            "workspaces",
            match={"id": ROW_ID},
            values={"name": "after"},
        )

    assert row == ONE_ROW[0]
    assert seen[0].method == "PATCH"
    assert seen[0].url.params["id"] == f"eq.{ROW_ID}"
    assert "return=representation" in seen[0].headers["prefer"]


@pytest.mark.asyncio
async def test_delete_one_returns_the_single_affected_row() -> None:
    db, client = db_returning(ONE_ROW)
    async with client:
        row = await db.delete_one("workspaces", match={"id": ROW_ID})

    assert row == ONE_ROW[0]


@pytest.mark.asyncio
async def test_write_without_a_match_is_refused_before_any_request() -> None:
    seen: list[httpx.Request] = []
    db, client = db_returning(ONE_ROW, seen=seen)
    async with client:
        with pytest.raises(ValueError):
            await db.update_one("workspaces", match={}, values={"name": "x"})

    assert seen == []


@pytest.mark.asyncio
async def test_every_request_carries_the_requester_jwt() -> None:
    # ⚠️ 이 경로가 service key를 쓰면 RLS가 통째로 우회된다.
    seen: list[httpx.Request] = []
    db, client = db_returning(ONE_ROW, seen=seen)
    async with client:
        await db.select("workspaces")
        await db.update_one("workspaces", match={"id": ROW_ID}, values={"name": "x"})

    for request in seen:
        assert request.headers["authorization"] == f"Bearer {REQUESTER_JWT}"
        assert request.headers["apikey"] == PUBLISHABLE_KEY


# -----------------------------------------------------------------------------
# 2. 읽기 경로 — 0행 규칙 밖에 있다 (02-CONTEXT.md > D-11)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_select_returns_an_empty_list_without_raising() -> None:
    db, client = db_returning([])
    async with client:
        rows = await db.select("workspaces", match={"workspace_id": WORKSPACE_ID})

    assert rows == []


# -----------------------------------------------------------------------------
# 3. SQLSTATE 전파 — 렌더링은 핸들러의 몫이다 (02-CONTEXT.md > D-13)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_with_check_violation_propagates_with_its_sqlstate() -> None:
    db, client = db_returning(WITH_CHECK_VIOLATION, status=403)
    async with client:
        with pytest.raises(DatabaseError) as excinfo:
            await db.update_one("workspaces", match={"id": ROW_ID}, values={"name": "x"})

    assert excinfo.value.sqlstate == WITH_CHECK_VIOLATION["code"]
    assert not isinstance(excinfo.value, WorkspaceForbidden)


# -----------------------------------------------------------------------------
# 4. 단일 예외 핸들러 (02-CONTEXT.md > D-12, D-13)
# -----------------------------------------------------------------------------


def build_error_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/raises-forbidden")
    async def raises_forbidden() -> None:
        raise WorkspaceForbidden(table="workspaces", affected=0)

    @app.get("/raises-with-check")
    async def raises_with_check() -> None:
        raise DatabaseError(sqlstate="42501", status_code=403, message="denied")

    @app.get("/raises-other-sqlstate")
    async def raises_other_sqlstate() -> None:
        raise DatabaseError(sqlstate="08006", status_code=500, message="connection failure")

    return app


async def call(path: str) -> httpx.Response:
    app = build_error_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


@pytest.mark.asyncio
async def test_both_paths_are_rendered_by_the_same_handler_object() -> None:
    app = build_error_app()

    assert app.exception_handlers[WorkspaceForbidden] is app.exception_handlers[DatabaseError]


@pytest.mark.asyncio
async def test_workspace_forbidden_renders_as_forbidden() -> None:
    response = await call("/raises-forbidden")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_with_check_violation_renders_as_forbidden() -> None:
    response = await call("/raises-with-check")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_forbidden_body_leaks_nothing_about_the_resource() -> None:
    # 존재 여부가 응답으로 새면 열거 공격이 성립한다 (02-CONTEXT.md > D-12).
    missing = await call("/raises-forbidden")
    violated = await call("/raises-with-check")

    assert missing.json() == violated.json()
    body = missing.text
    for leak in (ROW_ID, "workspaces", "42501", "row-level"):
        assert leak not in body


@pytest.mark.asyncio
async def test_other_sqlstates_are_not_rendered_as_forbidden() -> None:
    # ⚠️ 핸들러가 모든 DB 오류를 403으로 뭉개면 진짜 장애가 격리 위반으로 위장된다.
    response = await call("/raises-other-sqlstate")

    assert response.status_code != 403
