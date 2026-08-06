"""service key로 PostgREST에 붙는 worker 전용 DB 경로.

관련 태스크: P2-JOB-01
설계 근거: 02-CONTEXT.md > D-06, D-08
설계 근거: checklists.json > decisions.db_access, decisions.db_transport

소비자: 02-07의 큐 루프(`claim_job` → 핸들러 → `complete_job`/`fail_job`/`release_job`)
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Final

import httpx

from worker.settings import WorkerSettings

__all__ = [
    "QUEUE_RPC_FUNCTIONS",
    "RPC_HELPERS",
    "SERVICE_REQUEST_TIMEOUT_SECONDS",
    "TABLE_HELPERS",
    "ServiceDb",
    "service_client",
]

SERVICE_REQUEST_TIMEOUT_SECONDS: Final[float] = 10.0

# `ServiceDb`가 직접 테이블을 읽는 헬퍼. 전부 workspace_id를 필수로 요구한다.
TABLE_HELPERS: Final[frozenset[str]] = frozenset({"get_job", "list_jobs"})

# 0003이 정의한 큐 함수(0007의 release_job 포함)만을 호출하는 헬퍼.
QUEUE_RPC_FUNCTIONS: Final[frozenset[str]] = frozenset(
    {"claim_job", "complete_job", "fail_job", "release_job"}
)
RPC_HELPERS: Final[frozenset[str]] = QUEUE_RPC_FUNCTIONS


def service_client(
    settings: WorkerSettings,
    *,
    timeout_seconds: float = SERVICE_REQUEST_TIMEOUT_SECONDS,
) -> httpx.AsyncClient:
    """`WorkerSettings`를 인자로 받아야만 service key 클라이언트를 만든다.

    모듈 전역 싱글턴을 두지 않는다 — 두는 순간 import 부작용으로 키를 읽으려 시도하게
    되어 D-06의 인과("막히는 것은 import가 아니라 키다")가 흐려진다.
    근거: 02-CONTEXT.md > D-08.

    ⚠️ 아래 `TypeError`는 방어선이 아니다. 실제로 막는 것은 `ApiSettings`에 이 필드가
    없다는 사실과 Railway가 api 서비스 env에 값을 주입하지 않는다는 사실이며, 이 검사는
    그 사실이 코드에 드러나는 표면일 뿐이다. 근거: 02-CONTEXT.md > D-06.
    """
    secret_key = getattr(settings, "SUPABASE_SECRET_KEY", None)
    if not isinstance(secret_key, str) or not secret_key:
        raise TypeError(
            "service_client는 SUPABASE_SECRET_KEY를 가진 WorkerSettings를 요구한다 — "
            f"{type(settings).__name__}에는 그 필드가 없다 (02-CONTEXT.md > D-06)"
        )

    return httpx.AsyncClient(
        base_url=f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1",
        headers={
            "apikey": secret_key,
            "Authorization": f"Bearer {secret_key}",
            "Accept": "application/json",
        },
        timeout=httpx.Timeout(timeout_seconds),
    )


# ⚠️ `service_role`은 BYPASSRLS다. 아래 테이블 헬퍼에서 workspace_id 조건이 빠지면
#    0004의 격리 정책 전부가 무효가 되고, 오류 없이 다른 테넌트의 행이 돌아온다.
#    그래서 workspace_id는 keyword-only이며 **기본값을 갖지 않는다** — 기본값이 있으면
#    잊고 호출해도 통과한다. 근거: checklists.json > decisions.db_access.
class ServiceDb:
    """주입된 service key 클라이언트 위에서만 동작하는 worker용 헬퍼 묶음.

    공개 헬퍼는 둘 중 하나여야 한다. 테이블 헬퍼(`TABLE_HELPERS`)는 workspace_id를 필수로
    받고, 큐 RPC 헬퍼(`RPC_HELPERS`)는 `QUEUE_RPC_FUNCTIONS`에 있는 함수만 호출한다.
    `apps/worker/tests/test_service_client.py`가 이 분류를 단언하므로, 분류를 빠져나가는
    헬퍼를 추가하면 red가 된다. Phase 2가 실제로 쓰는 범위는 `jobs` 하나이며 도메인
    테이블 헬퍼는 Phase 3의 일이다.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    # -- 테이블 헬퍼 ---------------------------------------------------------

    async def get_job(self, job_id: str, *, workspace_id: str) -> dict[str, Any] | None:
        rows = await self._select(
            "jobs",
            params={"id": f"eq.{job_id}", "workspace_id": f"eq.{workspace_id}", "limit": "1"},
        )
        return rows[0] if rows else None

    async def list_jobs(
        self,
        *,
        workspace_id: str,
        statuses: Sequence[str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {
            "workspace_id": f"eq.{workspace_id}",
            "order": "created_at.desc",
            "limit": str(limit),
        }
        if statuses:
            params["status"] = f"in.({','.join(statuses)})"
        return await self._select("jobs", params=params)

    # -- 큐 RPC 헬퍼 ---------------------------------------------------------
    #
    # 큐 함수는 테이블이 아니라 0003이 정의한 계약을 호출한다. claim은 설계상 전역
    # 폴링이고(어느 워크스페이스의 잡이든 집어간다), 나머지 셋은 이미 점유한 잡의
    # id로만 동작한다. 그래서 여기에 workspace_id를 요구하면 쓰이지 않는 인자가 되어
    # 격리를 강제하는 척만 하게 된다. 이 셋이 도메인 행을 읽는 통로가 아니라는 사실이
    # 분류를 정당화하며, 그 사실은 `QUEUE_RPC_FUNCTIONS` 허용 목록이 고정한다.

    async def claim_job(
        self,
        *,
        worker_id: str,
        types: Sequence[str] | None = None,
    ) -> dict[str, Any] | None:
        return await self._rpc(
            "claim_job",
            {"p_worker_id": worker_id, "p_types": list(types) if types is not None else None},
        )

    async def complete_job(self, job_id: str) -> dict[str, Any] | None:
        return await self._rpc("complete_job", {"p_job_id": job_id})

    async def fail_job(
        self,
        job_id: str,
        *,
        error: str,
        backoff: str | None = None,
        max_backoff: str | None = None,
    ) -> dict[str, Any] | None:
        payload: dict[str, Any] = {"p_job_id": job_id, "p_error": error}
        if backoff is not None:
            payload["p_backoff"] = backoff
        if max_backoff is not None:
            payload["p_max_backoff"] = max_backoff
        return await self._rpc("fail_job", payload)

    async def release_job(self, job_id: str, *, worker_id: str) -> dict[str, Any] | None:
        """SIGTERM 시 잡을 큐로 반납한다 (attempts를 되돌린다).

        ⚠️ `worker_id`는 선택 인자가 아니다. `public.release_job`은
        `locked_by = p_worker_id` 술어로 락 소유자를 검사하며, 그 술어가 종료 중인
        워커가 살아 있는 다른 워커의 잡을 큐로 되돌리는 것을 막는 유일한 장치다.
        기본값을 주면 그 검사를 우회할 길이 생긴다.
        근거: 02-CONTEXT.md > D-18, `supabase/migrations/0007_*.sql` 섹션 4.
        """
        return await self._rpc("release_job", {"p_job_id": job_id, "p_worker_id": worker_id})

    # -- 내부 ----------------------------------------------------------------

    async def _select(self, table: str, *, params: dict[str, str]) -> list[dict[str, Any]]:
        response = await self._client.get(f"/{table}", params=params)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else [payload]

    async def _rpc(self, function: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        response = await self._client.post(f"/rpc/{function}", json=payload)
        response.raise_for_status()
        result = response.json()
        if isinstance(result, list):
            result = result[0] if result else None
        if not isinstance(result, dict):
            return None
        # ⚠️ `returns public.jobs` 함수(complete_job · fail_job)가 0행을 돌려주면
        #    PostgREST는 null이 아니라 **모든 필드가 null인 레코드**를 만들어 준다.
        #    0003의 큐 함수들은 `where ... and status = 'running'` 절 덕분에 재호출이
        #    정상적으로 0행이고(at-least-once라 재호출이 정상 경로다), 그것을 그대로
        #    돌려주면 호출부의 `if row:` 가 no-op을 성공으로 읽는다. 그 오독은 오류 없이
        #    "두 번 처리해서 두 번 다 성공했다"는 기록을 남긴다.
        #    `setof` 함수(claim_job · release_job)는 빈 배열로 오므로 위에서 이미 걸러진다.
        if all(value is None for value in result.values()):
            return None
        return result
