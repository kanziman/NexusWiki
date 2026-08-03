"""Supabase REST를 통한 얇은 DB readiness 어댑터.

관련 태스크: P0-INIT-02
설계 근거: 01-CONTEXT.md > D-11
(Phase 1은 DB 트랜스포트를 결정하지 않는다 — 교체 지점은 이 파일 한 곳)
"""

from dataclasses import dataclass
from time import monotonic

import httpx

READINESS_TIMEOUT_SECONDS: float = 2.0


@dataclass(frozen=True)
class ReadinessResult:
    ok: bool
    reason: str | None
    elapsed_ms: float


async def check_db_roundtrip(
    client: httpx.AsyncClient,
    *,
    supabase_url: str,
    publishable_key: str,
    timeout_seconds: float = READINESS_TIMEOUT_SECONDS,
) -> ReadinessResult:
    """PostgREST 요청 한 번으로 DB 왕복 가능 여부를 확인한다."""
    started = monotonic()
    try:
        # ⚠️ 호출별 타임아웃이 없으면 readiness가 매달려 Railway가 프로세스를
        # 교체하지 못한 채 무한 대기한다. 근거: 01-CONTEXT.md > D-11.
        response = await client.get(
            f"{supabase_url.rstrip('/')}/rest/v1/workspaces?select=id&limit=1",
            headers={"apikey": publishable_key, "Accept": "application/json"},
            timeout=httpx.Timeout(timeout_seconds),
        )
    except httpx.TimeoutException:
        return _result(started, ok=False, reason="db_roundtrip_timeout")
    except httpx.HTTPError:
        return _result(started, ok=False, reason="db_unreachable")

    if not response.is_success:
        return _result(started, ok=False, reason=f"db_status_{response.status_code}")
    return _result(started, ok=True, reason=None)


def _result(started: float, *, ok: bool, reason: str | None) -> ReadinessResult:
    return ReadinessResult(
        ok=ok,
        reason=reason,
        elapsed_ms=(monotonic() - started) * 1000,
    )
