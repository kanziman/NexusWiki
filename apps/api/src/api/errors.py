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
    "BUDGET_SQLSTATE",
    "DUPLICATE_SQLSTATE",
    "FORBIDDEN_BODY",
    "FORBIDDEN_SQLSTATE",
    "BudgetExceeded",
    "DatabaseError",
    "SourceAlreadyIngested",
    "TextTooLarge",
    "WorkspaceForbidden",
    "register_error_handlers",
]

# `WITH CHECK` 위반이 올라오는 SQLSTATE. 이 문자열은 이 파일에만 있어야 한다 —
# 매핑이 흩어지면 SEC-04의 "한 곳" 조건이 깨진다 (02-CONTEXT.md > D-13).
FORBIDDEN_SQLSTATE: Final[str] = "42501"

# `(workspace_id, content_hash)` 유니크 위반 — 같은 내용의 재수집 (ING-02).
DUPLICATE_SQLSTATE: Final[str] = "23505"

# `enqueue_source_job`이 월 비용 상한 초과에 쓰는 코드 (`0009_pipeline_ops.sql:297`).
BUDGET_SQLSTATE: Final[str] = "53400"

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


class SourceAlreadyIngested(Exception):
    """같은 워크스페이스에 같은 내용의 원문이 이미 있다 (ING-02).

    조용한 성공이 아니라 **눈에 보이는 거부**여야 한다. 200으로 넘기면 사용자는 두 번째
    투입이 새 컴파일을 일으켰다고 믿고, 실제로는 아무 일도 일어나지 않는다.
    """

    def __init__(self, *, raw_source_id: str | None) -> None:
        super().__init__("이미 수집된 원문이다")
        self.raw_source_id = raw_source_id


class BudgetExceeded(Exception):
    """이번 달 LLM 지출이 워크스페이스 상한에 닿았다 (OPS-01, SQLSTATE 53400)."""


class TextTooLarge(Exception):
    """요청 본문 텍스트가 `ApiSettings.MAX_TEXT_CHARS`를 넘었다 (T-03-24).

    ⚠️ 이 판정은 라우터가 아니라 여기서 렌더된다. 라우터가 상태 코드를 정하기 시작하면
    D-13의 "등록 지점이 하나" 조건이 라우터마다 다시 결정된다.
    """

    def __init__(self, *, limit: int) -> None:
        super().__init__(f"본문 길이가 상한 {limit}자를 넘었다")
        self.limit = limit


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


# ⚠️ 아래 세 렌더 함수를 `_render_isolation_failure`에 합치지 않는다. 42501 매핑을
#    흐리면 격리 위반과 다른 실패가 같은 응답으로 뭉개져 SEC-04가 지키던 것이 사라진다.
#    D-13이 요구하는 것은 "렌더 함수가 하나"가 아니라 **"등록 지점이 하나"**이며,
#    그 조건은 아래 `register_error_handlers` 한 곳이 유지한다.
async def _render_duplicate_source(request: Request, exc: Exception) -> JSONResponse:
    """이미 수집된 원문 — 409와 기존 `raw_source_id`.

    ⚠️ 본문에 id를 싣는 것이 D-12("존재 여부를 상태로 구분하지 않는다")와 충돌하지 않는
    이유: 이 id는 `(workspace_id, content_hash)` 유니크가 잡은 **요청자 자신의 워크스페이스**
    안의 행이고, 그 INSERT가 RLS의 `with check`를 이미 통과한 뒤에만 여기 도달한다.
    남의 테넌트의 존재 여부는 이 경로로 새어 나갈 수 없다 (T-03-26).
    """
    raw_source_id = getattr(exc, "raw_source_id", None)
    _logger.info("sources.already_ingested", path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "already_ingested", "raw_source_id": raw_source_id},
    )


async def _render_budget_exceeded(request: Request, exc: Exception) -> JSONResponse:
    """월 비용 상한 초과 — 402.

    ⚠️ 본문에 지출액도 상한도 싣지 않는다. 금액 노출은 03-07의 잡·예산 라우터가 소유하며,
    거기서는 조회 권한이 함께 판정된다. 거부 응답에 금액을 끼워 넣으면 그 판정 없이
    새어 나간다.
    """
    del exc
    _logger.warning("sources.budget_exceeded", path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        content={"detail": "budget_exceeded"},
    )


async def _render_text_too_large(request: Request, exc: Exception) -> JSONResponse:
    """본문 길이 상한 초과 — 413. 상한값은 밝힌다 (비밀이 아니라 계약이다)."""
    limit = getattr(exc, "limit", None)
    _logger.info("sources.text_too_large", path=request.url.path, limit=limit)
    return JSONResponse(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        content={"detail": "text_too_large", "limit": limit},
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
    app.add_exception_handler(SourceAlreadyIngested, _render_duplicate_source)  # type: ignore[arg-type]
    app.add_exception_handler(BudgetExceeded, _render_budget_exceeded)  # type: ignore[arg-type]
    app.add_exception_handler(TextTooLarge, _render_text_too_large)  # type: ignore[arg-type]
