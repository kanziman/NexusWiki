"""격리 위반을 렌더하는 단일 지점.

관련 태스크: P2-BE-01
설계 근거: 02-CONTEXT.md > D-12, D-13

소비자: `api.main.create_app` (등록은 여기 한 곳), 02-04의 라우터(상태 코드를 직접 다루지 않음)
"""

from __future__ import annotations

from typing import Any, Final

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from nexuswiki_core.logging import get_logger

__all__ = [
    "FORBIDDEN_BODY",
    "FORBIDDEN_SQLSTATE",
    "DatabaseError",
    "WorkspaceForbidden",
    "register_error_handlers",
]

# `WITH CHECK` 위반이 올라오는 SQLSTATE. 이 문자열은 이 파일에만 있어야 한다 —
# 매핑이 흩어지면 SEC-04의 "한 곳" 조건이 깨진다 (02-CONTEXT.md > D-13).
FORBIDDEN_SQLSTATE: Final[str] = "42501"

# ⚠️ 본문은 고정 문자열이다. 테이블명·리소스 id·SQLSTATE 중 무엇이라도 실으면 다른
#    테넌트의 리소스 존재 여부가 응답으로 새어나가 열거 공격이 성립한다.
FORBIDDEN_BODY: Final[dict[str, str]] = {"detail": "forbidden"}
_DATABASE_ERROR_BODY: Final[dict[str, str]] = {"detail": "database_error"}

_logger = get_logger(__name__)


class WorkspaceForbidden(Exception):
    """쓰기 경로에서 영향 행 수가 정확히 1이 아닐 때 발생한다.

    0은 RLS의 `USING`이 막았거나 리소스가 없다는 뜻이고, 2 이상은 스코프가 의도보다
    넓게 잡혔다는 뜻이다. 둘 다 계속 진행하면 안 된다.
    """

    def __init__(self, *, table: str, affected: int) -> None:
        super().__init__(f"{table}: 영향 행 수가 {affected}이다 (1이어야 한다)")
        self.table = table
        self.affected = affected


class DatabaseError(Exception):
    """PostgREST가 돌려준 오류를 SQLSTATE와 함께 그대로 실어 올린다.

    `UserDb`는 이 예외를 만들기만 하고 어떤 SQLSTATE가 Forbidden인지 판정하지 않는다.
    판정과 렌더링은 아래 단일 핸들러의 몫이다.
    """

    def __init__(self, *, sqlstate: str | None, status_code: int, message: str) -> None:
        super().__init__(f"[{sqlstate or 'unknown'}] {message}")
        self.sqlstate = sqlstate
        self.status_code = status_code
        self.message = message


# ⚠️ 존재하지 않는 리소스와 격리 위반을 구분하지 않는다 — 둘 다 같은 응답이다.
#    Not Found를 주면 다른 테넌트의 리소스 존재 여부가 상태 코드로 새어나가 열거
#    공격이 성립한다. UX상 404가 낫다는 이유로 뒤집지 말 것 (02-CONTEXT.md > D-12).
async def _render_isolation_failure(request: Request, exc: Exception) -> JSONResponse:
    """`WorkspaceForbidden`과 SQLSTATE 42501을 같은 응답으로 렌더한다.

    두 경로가 서로 다른 곳에서 처리되면 SEC-04의 "한 곳" 조건이 깨지므로, 등록 대상이
    둘이어도 렌더 함수는 이 하나다 (02-CONTEXT.md > D-13).

    ⚠️ 42501이 아닌 SQLSTATE까지 Forbidden으로 뭉개지 않는다. 커넥션 실패 같은 진짜
    장애가 격리 위반으로 위장되면 원인을 찾을 수 없게 된다.
    """
    if isinstance(exc, WorkspaceForbidden):
        _logger.warning(
            "db.workspace_forbidden",
            path=request.url.path,
            table=exc.table,
            affected=exc.affected,
        )
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=FORBIDDEN_BODY)

    sqlstate = getattr(exc, "sqlstate", None)
    if sqlstate == FORBIDDEN_SQLSTATE:
        _logger.warning("db.with_check_violation", path=request.url.path, sqlstate=sqlstate)
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=FORBIDDEN_BODY)

    _logger.error("db.error", path=request.url.path, sqlstate=sqlstate)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_DATABASE_ERROR_BODY,
    )


def register_error_handlers(app: FastAPI) -> None:
    """격리 관련 예외를 앱에 붙인다.

    ⚠️ 호출 지점은 `api.main.create_app` 한 곳뿐이다. 라우터가 스스로 상태 코드를 정하기
    시작하면 D-12의 "존재 여부를 구분하지 않는다"가 라우터마다 다시 결정된다.
    광범위한 `Exception` 핸들러는 두지 않는다 — 정상 오류 경로(`/health/ready`의 503 등)를
    삼키게 된다.
    """
    handler: Any = _render_isolation_failure
    app.add_exception_handler(WorkspaceForbidden, handler)
    app.add_exception_handler(DatabaseError, handler)
