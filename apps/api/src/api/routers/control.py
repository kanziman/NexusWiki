"""Control Room 추적 조회.

관련 이슈: #165, #166
설계 근거: openspec/changes/ai-control-flow-accounting/design.md > D9
계약: openspec/changes/ai-control-flow-accounting/specs/ai-control-room/spec.md

접근 판정 순서

  요청자 JWT로 ask_messages 조회 ──행 있음──> Ask 상세 (RLS가 작성자만 통과시킨다)
          │ 0행
          v
  editor 역할 확인 ──아니면──> 403
          │
          v
  jobs 조회 ──행 있음──> 수집 상세
          │ 0행
          v
         403 (부재와 격리 위반을 구분하지 않는다)

⚠️ `usage_events`는 trace 게이트를 통과한 **뒤에만** 읽는다. 다만 이 순서는 이 화면의 동작을 정할
뿐 경계가 아니다. 멤버는 RLS로 `usage_events`를 직접 읽을 수 있고, design Risks가 이를 수용했다.

⚠️ 응답은 허용 필드로만 조립한다. 질문, 프롬프트, 답변, 잡 payload를 읽지도 돌려주지도 않는다.
`last_error`는 분류를 계산하려고 읽지만 원문을 응답에 싣지 않는다.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Final
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.db.user import UserDb
from api.errors import WorkspaceForbidden
from api.routers.jobs import CHAIN_ORDER, STEP_LABELS

router = APIRouter(prefix="/workspaces", tags=["control"])
_bearer = HTTPBearer()

_TRACE_LIST_LIMIT: Final[int] = 100
_JOB_ROW_LIMIT: Final[int] = 500
_ASK_COLUMNS: Final[str] = "trace_id,status,created_at,control_report"
_JOB_COLUMNS: Final[str] = (
    "trace_id,type,status,attempts,created_at,updated_at,last_claimed_at,last_error"
)
_USAGE_COLUMNS: Final[str] = (
    "kind,model,prompt_tokens,completion_tokens,total_tokens,"
    "cost_micros,duration_ms,occurred_at,metadata"
)

# 원시 오류 문자열을 내보내지 않고 알려진 분류만 통과시킨다. `last_error`는 정제되어 있지만 일반
# 예외의 메시지를 담을 수 있다.
_ERROR_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "provider_credit_exhausted",
        "provider_error",
        "upstream_error",
        "no_transcript",
        "video_unavailable",
        "provider_unavailable",
        "needs_ocr",
        "empty_extraction",
        "unsupported_source_type",
        "unsupported_mime",
        "unreadable_document",
        "storage_object_missing",
    }
)
_SPAN_LABELS: Final[dict[str, str]] = {
    "retrieval": "4채널 검색",
    "context": "근거 조립",
    "llm_stream": "답변 생성",
    "citation": "인용 검증",
}
_STAGE_STATES: Final[dict[str, str]] = {
    "queued": "pending",
    "running": "active",
    "succeeded": "completed",
    "failed": "retrying",
    "dead": "failed",
    "canceled": "canceled",
}


def _user_db(request: Request, credentials: HTTPAuthorizationCredentials) -> UserDb:
    settings = request.app.state.settings
    return UserDb(
        request.app.state.http_client,
        supabase_url=settings.SUPABASE_URL,
        publishable_key=settings.SUPABASE_PUBLISHABLE_KEY,
        access_token=credentials.credentials,
    )


async def _has_role(db: UserDb, *, workspace_id: UUID, min_role: str) -> bool:
    result = await db.rpc(
        "has_workspace_role", params={"ws_id": str(workspace_id), "min_role": min_role}
    )
    return bool(result) and result[0] is True


def _error_category(last_error: object) -> str | None:
    if not isinstance(last_error, str) or not last_error:
        return None
    token = last_error.split(maxsplit=1)[0].rstrip(":")
    if token in _ERROR_CATEGORIES:
        return token
    return "llm_schema" if "구조화 출력" in last_error else "internal_error"


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _stage_duration_ms(row: Mapping[str, Any]) -> int | None:
    if row.get("status") in {"queued", "running"}:
        return None
    started, ended = _parse_time(row.get("last_claimed_at")), _parse_time(row.get("updated_at"))
    if started is None or ended is None:
        return None
    return max(0, round((ended - started).total_seconds() * 1000))


def _number(value: object) -> int | float:
    return value if isinstance(value, int | float) and not isinstance(value, bool) else 0


def _short_text(value: object) -> str | None:
    return value[:60] if isinstance(value, str) else None


def _route(report: Mapping[str, Any]) -> dict[str, str | None] | None:
    """보고서는 작성자가 수정할 수 있으므로 형태와 길이를 다시 확인한다."""
    route = report.get("route")
    if not isinstance(route, Mapping):
        return None
    return {
        "decision": _short_text(route.get("decision")),
        "reason": _short_text(route.get("reason")),
    }


def _spans(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    spans = report.get("spans")
    if not isinstance(spans, list):
        return []
    safe = []
    for span in spans[:32]:
        if isinstance(span, Mapping) and span.get("name") in _SPAN_LABELS:
            safe.append(
                {
                    "name": span["name"],
                    "label": _SPAN_LABELS[span["name"]],
                    "start_ms": _number(span.get("start_ms")),
                    "duration_ms": _number(span.get("duration_ms")),
                }
            )
    return safe


def _ask_summary(row: Mapping[str, Any]) -> dict[str, Any]:
    report = row.get("control_report")
    report = report if isinstance(report, Mapping) else {}
    return {
        "trace_id": row["trace_id"],
        "kind": "ask",
        "status": row["status"],
        "started_at": row["created_at"],
        "route": _route(report),
        "total_ms": _number(report.get("total_ms")) or None,
    }


def _ingest_status(rows: list[dict[str, Any]]) -> str:
    statuses = {row.get("status") for row in rows}
    if "dead" in statuses:
        return "failed"
    if statuses & {"queued", "running", "failed"}:
        return "running"
    return "canceled" if "canceled" in statuses else "succeeded"


def _ingest_summary(trace_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "kind": "ingest",
        "status": _ingest_status(rows),
        "started_at": min(str(row["created_at"]) for row in rows),
        "route": None,
        "total_ms": None,
    }


def _stages(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """완료·진행·대기 단계를 체인 순서로 돌려준다.

    후속 잡은 앞 단계가 끝나야 생기므로, 아직 행이 없는 단계는 체인이 중단되지 않았을 때만 대기로
    표시한다. 중단된 체인에 대기를 그리면 다시 진행될 것처럼 보인다.
    """
    position = {job_type: index for index, job_type in enumerate(CHAIN_ORDER)}
    ordered = sorted(
        rows, key=lambda row: (position.get(row["type"], len(CHAIN_ORDER)), str(row["created_at"]))
    )
    stages = [
        {
            "type": row["type"],
            "label": STEP_LABELS.get(row["type"], "알 수 없는 단계"),
            "state": _STAGE_STATES.get(str(row.get("status")), "failed"),
            "attempts": _number(row.get("attempts")),
            "duration_ms": _stage_duration_ms(row),
            "error_category": _error_category(row.get("last_error")),
        }
        for row in ordered
    ]
    if _ingest_status(rows) == "running":
        seen = {row["type"] for row in rows}
        stages.extend(
            {
                "type": job_type,
                "label": STEP_LABELS[job_type],
                "state": "pending",
                "attempts": 0,
                "duration_ms": None,
                "error_category": None,
            }
            for job_type in CHAIN_ORDER
            if job_type not in seen
        )
    return stages


def _call(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadata")
    metadata = metadata if isinstance(metadata, Mapping) else {}
    return {
        "call": _short_text(metadata.get("call")),
        "kind": row.get("kind"),
        "model": row.get("model"),
        "attempt": metadata.get("attempt") if isinstance(metadata.get("attempt"), int) else None,
        "incomplete": metadata.get("incomplete") is True,
        "route": _short_text(metadata.get("route")),
        "prompt_tokens": _number(row.get("prompt_tokens")),
        "completion_tokens": _number(row.get("completion_tokens")),
        "total_tokens": _number(row.get("total_tokens")),
        "cost_micros": _number(row.get("cost_micros")),
        "duration_ms": row.get("duration_ms"),
        "occurred_at": row.get("occurred_at"),
    }


def _totals(calls: list[dict[str, Any]]) -> dict[str, int | float]:
    return {
        "call_count": len(calls),
        "total_tokens": sum(call["total_tokens"] for call in calls),
        "cost_micros": sum(call["cost_micros"] for call in calls),
        "incomplete_call_count": sum(1 for call in calls if call["incomplete"]),
    }


async def _calls(db: UserDb, *, workspace_id: UUID, trace_id: UUID) -> list[dict[str, Any]]:
    rows = await db.select(
        "usage_events",
        match={"workspace_id": str(workspace_id), "trace_id": str(trace_id)},
        columns=_USAGE_COLUMNS,
        order="occurred_at.asc",
    )
    return [_call(row) for row in rows]


@router.get("/{workspace_id}/control/traces")
async def list_traces(
    workspace_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    """볼 수 있는 trace 목록. 자신의 Ask와, editor 이상이면 수집 trace를 돌려준다."""
    db = _user_db(request, credentials)
    if not await _has_role(db, workspace_id=workspace_id, min_role="viewer"):
        raise WorkspaceForbidden(table="workspace_members", affected=0)
    can_view_workspace = await _has_role(db, workspace_id=workspace_id, min_role="editor")

    ask_rows = await db.select(
        "ask_messages",
        match={"workspace_id": str(workspace_id)},
        columns=_ASK_COLUMNS,
        order="created_at.desc",
        limit=_TRACE_LIST_LIMIT,
    )
    items = [_ask_summary(row) for row in ask_rows if row.get("trace_id")]

    if can_view_workspace:
        job_rows = await db.select(
            "jobs",
            match={"workspace_id": str(workspace_id)},
            columns=_JOB_COLUMNS,
            order="created_at.desc",
            limit=_JOB_ROW_LIMIT,
        )
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in job_rows:
            if row.get("trace_id"):
                grouped.setdefault(str(row["trace_id"]), []).append(row)
        items.extend(_ingest_summary(trace_id, rows) for trace_id, rows in grouped.items())

    items.sort(key=lambda item: str(item["started_at"]), reverse=True)
    return {"items": items[:_TRACE_LIST_LIMIT], "can_view_workspace": can_view_workspace}


@router.get("/{workspace_id}/control/traces/{trace_id}")
async def get_trace(
    workspace_id: UUID,
    trace_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    db = _user_db(request, credentials)
    ask_rows = await db.select(
        "ask_messages",
        match={"workspace_id": str(workspace_id), "trace_id": str(trace_id)},
        columns=_ASK_COLUMNS,
        limit=1,
    )
    if ask_rows:
        calls = await _calls(db, workspace_id=workspace_id, trace_id=trace_id)
        report = ask_rows[0].get("control_report")
        report = report if isinstance(report, Mapping) else {}
        citation = report.get("citation")
        citation = citation if isinstance(citation, Mapping) else {}
        evidence = report.get("evidence")
        evidence = evidence if isinstance(evidence, Mapping) else {}
        retrieval = report.get("retrieval")
        retrieval = retrieval if isinstance(retrieval, Mapping) else {}
        missing = retrieval.get("missing_channels")
        return {
            **_ask_summary(ask_rows[0]),
            "spans": _spans(report),
            "evidence": {
                "wiki": _number(evidence.get("wiki")),
                "source": _number(evidence.get("source")),
            },
            "missing_channels": (
                [name[:40] for name in missing if isinstance(name, str)][:8]
                if isinstance(missing, list)
                else []
            ),
            "citation": {
                key: _number(citation.get(key))
                for key in (
                    "cited_anchor_count",
                    "fabricated_anchor_count",
                    "dual_citation_rate",
                    "unsourced_sentence_ratio",
                )
            },
            "stages": [],
            "calls": calls,
            "totals": _totals(calls),
        }

    if await _has_role(db, workspace_id=workspace_id, min_role="editor"):
        job_rows = await db.select(
            "jobs",
            match={"workspace_id": str(workspace_id), "trace_id": str(trace_id)},
            columns=_JOB_COLUMNS,
        )
        if job_rows:
            calls = await _calls(db, workspace_id=workspace_id, trace_id=trace_id)
            return {
                **_ingest_summary(str(trace_id), job_rows),
                "spans": [],
                "stages": _stages(job_rows),
                "calls": calls,
                "totals": _totals(calls),
            }

    # 부재와 권한 없음을 구분하지 않는다. 구분하면 trace 식별자로 존재를 탐지할 수 있다.
    raise WorkspaceForbidden(table="ask_messages", affected=0)


@router.get("/{workspace_id}/control/ask-aggregate")
async def ask_aggregate(
    workspace_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    days: Annotated[int, Query(ge=1, le=90)] = 30,
) -> dict[str, Any]:
    """Ask 집계. 역할 검사는 함수 본문이 하며 위반은 42501을 거쳐 403이 된다."""
    since = datetime.now(UTC) - timedelta(days=days)
    rows = await _user_db(request, credentials).rpc(
        "ask_trace_aggregate",
        params={"p_workspace_id": str(workspace_id), "p_since": since.isoformat()},
    )
    row = rows[0] if rows else {}
    return {
        "days": days,
        "turn_count": row.get("turn_count", 0),
        "resolved_count": row.get("resolved_count", 0),
        "no_evidence_count": row.get("no_evidence_count", 0),
        "error_count": row.get("error_count", 0),
        "decision_counts": row.get("decision_counts") or {},
        "p50_total_ms": row.get("p50_total_ms"),
        "p95_total_ms": row.get("p95_total_ms"),
        "total_cost_micros": row.get("total_cost_micros", 0),
        "incomplete_call_count": row.get("incomplete_call_count", 0),
    }
