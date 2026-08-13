"""사용자에게 잡 진행·제어·표시용 비용 정보를 돌려주는 라우터.

관련 태스크: P2-API-01, P3-UI-01
설계 근거: 03-CONTEXT.md > D-03
설계 근거: 03-07-PLAN.md > D-P18, D-P19
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Final
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.db.user import UserDb
from api.errors import JobNotCancellable, JobNotRetryable, WorkspaceForbidden
from api.settings import ApiSettings

router = APIRouter(prefix="/workspaces", tags=["jobs"])

# ⚠️ 이 모듈에는 거부 상태 코드 리터럴이나 인라인 오류 응답을 두지 않는다. 403·409는
# `api.errors`의 단일 등록 지점이 소유한다 (02-CONTEXT.md > D-12, D-13).
_bearer = HTTPBearer()

# `worker.handlers.HANDLERS`에서 noop을 뺀 사실상의 파이프라인 순서다. api는 worker를
# import하지 않으므로 수기로 유지한다. 어긋나면 사용자는 새 단계를 알 수 없는 단계로 본다.
CHAIN_ORDER: Final[tuple[str, ...]] = ("parse", "compile", "link_sync", "embed", "conflict_check")

# 라벨은 서버가 소유한다. 클라이언트가 type 문자열을 매칭하면 새 type 추가 때 조용히 빈
# 라벨이 된다. 그래서 응답은 type과 step_label을 함께 돌려준다.
STEP_LABELS: Final[dict[str, str]] = {
    "parse": "원문 파싱",
    "compile": "위키 컴파일",
    "link_sync": "링크 동기화",
    "embed": "임베딩",
    "conflict_check": "지식 충돌 검사",
    "noop": "무동작",
}

_JOBS_TABLE = "jobs"
_USAGE_EVENTS_TABLE = "usage_events"
_BUDGET_USAGE_LIMIT: Final[int] = 1000


def _user_db(request: Request, credentials: HTTPAuthorizationCredentials) -> UserDb:
    """요청자 JWT를 실은 RLS 어댑터를 만든다."""
    settings: ApiSettings = request.app.state.settings
    return UserDb(
        request.app.state.http_client,
        supabase_url=settings.SUPABASE_URL,
        publishable_key=settings.SUPABASE_PUBLISHABLE_KEY,
        access_token=credentials.credentials,
    )


def _job_response(row: dict[str, Any]) -> dict[str, Any]:
    """잡 내부 payload를 노출하지 않는 UI 계약으로 좁힌다."""
    job_type = str(row["type"])
    try:
        position: int | None = CHAIN_ORDER.index(job_type) + 1
    except ValueError:
        position = None
    return {
        "id": row["id"],
        "type": job_type,
        "step_label": STEP_LABELS.get(job_type, "알 수 없는 단계"),
        "chain_position": position,
        "chain_total": len(CHAIN_ORDER),
        "status": row["status"],
        "attempts": row["attempts"],
        "max_attempts": row["max_attempts"],
        "run_after": row["run_after"],
        "last_error": row["last_error"],
        "cancel_requested_at": row["cancel_requested_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _job_sort_key(job: dict[str, Any]) -> tuple[int, str]:
    position = job["chain_position"]
    return (position if position is not None else len(CHAIN_ORDER) + 1, str(job["created_at"]))


async def _usage_rows_since(
    db: UserDb, *, workspace_id: UUID, month_start: datetime, job_id: UUID | None = None
) -> list[dict[str, Any]]:
    """`UserDb.select`의 eq 전용 필터를 넓히지 않고 gte 필터만 이 표면에 둔다."""
    params = {
        "select": "cost_micros,occurred_at",
        "workspace_id": f"eq.{workspace_id}",
        "occurred_at": f"gte.{month_start.isoformat()}",
        "limit": str(_BUDGET_USAGE_LIMIT),
    }
    if job_id is not None:
        params["job_id"] = f"eq.{job_id}"
    # UserDb의 공용 select는 비교 연산자를 eq로 고정한다. month 경계만 필요한 이 읽기는
    # 그 소유권을 바꾸지 않고 같은 요청자 JWT·RLS 헤더로 PostgREST를 호출한다.
    response = await db._client.get(  # noqa: SLF001 - 위의 제한적 연산자 seam
        f"{db._base_url}/{_USAGE_EVENTS_TABLE}", params=params, headers=db._headers
    )
    payload = db._payload(response)  # noqa: SLF001 - UserDb와 동일한 오류 정규화
    return payload if isinstance(payload, list) else [payload]


def _month_start() -> datetime:
    now = datetime.now(UTC)
    return datetime(now.year, now.month, 1, tzinfo=UTC)


async def _require_operations_role(db: UserDb, *, workspace_id: UUID) -> None:
    """운영 스냅샷은 editor 이상에게만 보여준다.

    기존 RLS 헬퍼를 요청자 JWT로 호출한다. 이 검사를 대시보드 역할 판정에 맡기면
    직접 API 호출로 비용/잡 집계가 새는 경로가 생긴다.
    """
    result = await db.rpc(
        "has_workspace_role",
        params={"ws_id": str(workspace_id), "min_role": "editor"},
    )
    if not result or result[0] is not True:
        raise WorkspaceForbidden(table="workspace_members", affected=0)


def _pipeline_snapshot(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """허용된 상태만 고정 순서의 안전한 표시 DTO로 축소한다."""
    counts = {step: {"queued": 0, "running": 0, "dead": 0} for step in CHAIN_ORDER}
    for row in rows:
        job_type = str(row.get("type", ""))
        job_status = str(row.get("status", ""))
        if job_type in counts and job_status in counts[job_type]:
            counts[job_type][job_status] += 1
    return [{"type": step, "step_label": STEP_LABELS[step], **counts[step]} for step in CHAIN_ORDER]


@router.get("/{workspace_id}/sources/{raw_source_id}/jobs")
async def list_source_jobs(
    workspace_id: UUID,
    raw_source_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, list[dict[str, Any]]]:
    db = _user_db(request, credentials)
    # `_as_filters`는 키를 손대지 않으므로 jsonb 경로가 PostgREST 파라미터로 그대로 간다.
    # RLS 위에 workspace 필터를 한 겹 더 둬 요청한 경계 밖의 가시 행을 섞지 않는다.
    rows = await db.select(
        _JOBS_TABLE,
        match={"workspace_id": str(workspace_id), "payload->>raw_source_id": str(raw_source_id)},
        limit=len(CHAIN_ORDER) * 3,
    )
    # 인큐 직후 폴링 창의 0행은 404가 아니라 정상 빈 목록이다. 다른 테넌트도 RLS가 0행으로
    # 만들어 같은 응답이 된다. 이는 존재 여부를 구분하지 않는 의도된 계약이다.
    jobs = sorted((_job_response(row) for row in rows), key=_job_sort_key)
    return {"jobs": jobs}


@router.post("/{workspace_id}/jobs/{job_id}/retry")
async def retry_job(
    workspace_id: UUID,
    job_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    db = _user_db(request, credentials)
    rows = await db.rpc("retry_dead_job", params={"p_job_id": str(job_id)})
    if not rows:
        raise JobNotRetryable
    row = rows[0]
    assert str(row["workspace_id"]) == str(workspace_id)  # noqa: S101 - RPC 계약 단언
    return _job_response(row)


@router.post("/{workspace_id}/jobs/{job_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_job(
    workspace_id: UUID,
    job_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    db = _user_db(request, credentials)
    rows = await db.rpc("request_job_cancel", params={"p_job_id": str(job_id)})
    if not rows:
        raise JobNotCancellable
    row = rows[0]
    assert str(row["workspace_id"]) == str(workspace_id)  # noqa: S101 - RPC 계약 단언
    usage = await _usage_rows_since(
        db, workspace_id=workspace_id, month_start=_month_start(), job_id=job_id
    )
    response = _job_response(row)
    response["canceled_immediately"] = row["status"] == "canceled"
    # 이미 기록된 비용은 취소해도 사라지지 않는다. 문구 대신 기계 판독 가능한 수치만 준다.
    response["billing"] = {
        "usage_event_count": len(usage),
        "spent_micros": sum(int(item["cost_micros"]) for item in usage),
    }
    # running 잡은 이 시점에 끝나지 않았으므로 202가 요청 접수임을 나타낸다.
    return response


@router.get("/{workspace_id}/budget")
async def workspace_budget(
    workspace_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    db = _user_db(request, credentials)
    cap_rows = await db.select(
        "workspaces", match={"id": str(workspace_id)}, columns="monthly_budget_micros", limit=1
    )
    # 읽기 0행은 RLS가 막은 경우에도 빈 목록이다. 예산값으로 다른 워크스페이스 존재를 알리지 않는다.
    cap_micros = int(cap_rows[0]["monthly_budget_micros"]) if cap_rows else 0
    month_start = _month_start()
    usage = await _usage_rows_since(db, workspace_id=workspace_id, month_start=month_start)
    spent_micros = sum(int(item["cost_micros"]) for item in usage)
    return {
        "cap_micros": cap_micros,
        "spent_micros": spent_micros,
        "remaining_micros": cap_micros - spent_micros,
        "month_start": month_start.isoformat(),
        "truncated": len(usage) == _BUDGET_USAGE_LIMIT,
        # 이 값은 표시용이다. 권위 있는 상한 판정은 enqueue_source_job SQL이 한다 (D-P18).
        "authoritative": False,
    }


@router.get("/{workspace_id}/operations")
async def workspace_operations(
    workspace_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    """owner/editor 전용 비용·파이프라인 표시 스냅샷 (OPS-06).

    이 엔드포인트는 원문, 공급자 정보, usage metadata와 잡 오류를 읽거나 반환하지
    않는다. 반환 스키마는 아래 allowlist로만 조립한다.
    """
    db = _user_db(request, credentials)
    await _require_operations_role(db, workspace_id=workspace_id)

    month_start = _month_start()
    cap_rows = await db.select(
        "workspaces", match={"id": str(workspace_id)}, columns="monthly_budget_micros", limit=1
    )
    usage = await _usage_rows_since(db, workspace_id=workspace_id, month_start=month_start)
    # RLS를 태운 요청자 JWT 직접 읽기다. 집계는 서버에서만 수행하며 원 행은 응답에 없다.
    job_rows = await db.select(
        _JOBS_TABLE,
        match={"workspace_id": str(workspace_id)},
        columns="type,status",
    )
    cap_micros = int(cap_rows[0]["monthly_budget_micros"]) if cap_rows else 0
    spent_micros = sum(int(item["cost_micros"]) for item in usage)
    return {
        "budget": {
            "cap_micros": cap_micros,
            "spent_micros": spent_micros,
            "remaining_micros": cap_micros - spent_micros,
            "month_start": month_start.isoformat(),
            "truncated": len(usage) == _BUDGET_USAGE_LIMIT,
            "authoritative": False,
        },
        "pipeline": _pipeline_snapshot(job_rows),
        "observed_at": datetime.now(UTC).isoformat(),
    }
