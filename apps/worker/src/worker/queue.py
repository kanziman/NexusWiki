"""claim→핸들러→complete 루프와 SIGTERM 반납.

관련 태스크: P2-JOB-01
설계 근거: 02-CONTEXT.md > D-16, D-17, D-18
설계 근거: checklists.json > decisions.job_queue, decisions.db_access

상태 전이 중 이 모듈이 일으키는 것 (0003/0007의 함수를 통해서만 일어난다 —
`jobs`를 직접 UPDATE하지 않는다)

  queued ──claim_job──> running ──complete_job──> succeeded
                          │
                          ├──fail_job(핸들러 예외 / 미등록 type)──> failed | dead
                          └──release_job(SIGTERM + grace 초과)──> queued (attempts −1)

소비자: `worker.__main__.main`
"""

from __future__ import annotations

import asyncio
import os
import socket
from typing import Any, Final, Protocol

from nexuswiki_core.logging import bind_job_context, clear_job_context, get_logger
from worker.handlers import UnknownJobTypeError, resolve_handler

__all__ = [
    "DEAD_LETTER_BACKOFF",
    "LAST_ERROR_MAX_CHARS",
    "PLATFORM_GRACE_SECONDS",
    "QUEUE_POLL_INTERVAL_SECONDS",
    "WORKER_GRACE_SECONDS",
    "process_next_job",
    "resolve_worker_id",
    "run_queue_loop",
    "sanitize_error",
]

# Railway가 SIGTERM 후 SIGKILL까지 주는 시간. 상한을 비교하기 위한 기준값일 뿐
# 이 모듈이 이 값을 기다리지는 않는다.
PLATFORM_GRACE_SECONDS: Final[float] = 30.0

# ⚠️ WORKER_GRACE_SECONDS는 PLATFORM_GRACE_SECONDS보다 **짧아야** 한다. 같거나
#    길면 반납이 시작되기도 전에 프로세스가 SIGKILL로 죽고, 잡은 `running`인 채
#    남아 `reap_stale_jobs` 기본 15분이 지나야 큐로 돌아온다. 배포 한 번이 잡
#    하나를 15분 묶어 두는 셈이다. 근거: 02-CONTEXT.md > D-18.
WORKER_GRACE_SECONDS: Final[float] = 20.0

# 빈 큐에서의 폴링 간격. 종료 신호를 함께 기다리므로 이 값만큼 종료가 늦어지지 않는다.
QUEUE_POLL_INTERVAL_SECONDS: Final[float] = 2.0

# 미등록 type은 재시도해도 결과가 같으므로 백오프 없이 즉시 판정한다.
DEAD_LETTER_BACKOFF: Final[str] = "0 seconds"

# `jobs.last_error`는 멤버가 SELECT할 수 있고 프론트가 그대로 보여준다.
LAST_ERROR_MAX_CHARS: Final[int] = 500

_logger = get_logger(__name__)


class QueueDb(Protocol):
    """이 루프가 쓰는 `ServiceDb`의 부분집합."""

    async def claim_job(
        self, *, worker_id: str, types: list[str] | None = ...
    ) -> dict[str, Any] | None: ...

    async def complete_job(self, job_id: str) -> dict[str, Any] | None: ...

    async def fail_job(
        self,
        job_id: str,
        *,
        error: str,
        backoff: str | None = ...,
        max_backoff: str | None = ...,
    ) -> dict[str, Any] | None: ...

    async def release_job(self, job_id: str, *, worker_id: str) -> dict[str, Any] | None: ...


def resolve_worker_id() -> str:
    """`jobs.locked_by`에 실릴 워커 인스턴스 식별자 (0003:56 — 호스트+PID)."""
    return f"{socket.gethostname()}-{os.getpid()}"


def sanitize_error(error: BaseException) -> str:
    """예외를 `last_error`에 실을 문자열로 정제한다.

    ⚠️ 여기가 provider 원문 예외를 거르는 자리다. `last_error`는 워크스페이스
    멤버가 SELECT할 수 있고(0004) 프론트가 그대로 보여주므로, OpenRouter/OpenAI
    응답 본문이 그대로 실리면 내부 구조와 프롬프트가 새어 나간다. Phase 2에는
    provider 호출이 없어 지금은 타입+메시지 절단만 한다 — Phase 3(OPS)이 이
    함수 안에서 provider별 마스킹을 채운다.
    """
    text = f"{type(error).__name__}: {error}"
    if len(text) <= LAST_ERROR_MAX_CHARS:
        return text
    return text[: LAST_ERROR_MAX_CHARS - 1] + "…"


async def _wait_for_stop(stop: asyncio.Event, seconds: float) -> bool:
    """`seconds`만큼 대기하되 종료 신호가 오면 즉시 깨어난다."""
    try:
        await asyncio.wait_for(stop.wait(), seconds)
    except TimeoutError:
        return False
    return True


async def _dead_letter(
    db: QueueDb, *, job_id: str, job_type: str, reason: str
) -> dict[str, Any] | None:
    """미등록 type을 백오프 없이 데드레터 판정으로 보낸다.

    ⚠️ 0003/0007의 함수 중 특정 잡을 한 번에 `dead`로 만드는 것은 없다. `dead`는
    `fail_job`/`reap_stale_jobs` 양쪽에서 `attempts >= max_attempts`로만 도달하며,
    그 게이트를 건너뛰려면 `jobs`를 직접 UPDATE해야 한다 — 그것은 이 프로젝트가
    금지한 경로다(0003:92-98). 그래서 백오프를 0으로 보내 **대기 없이** 판정을
    반복하게 만든다: `run_after = now()`이므로 잡은 곧바로 다시 claim 대상이 되고,
    핸들러는 한 번도 돌지 않은 채 max_attempts 안에 `dead`로 수렴한다.
    한 번에 보내려면 `0008`에 `dead_letter_job()`이 필요하다.
    """
    row = await db.fail_job(job_id, error=reason, backoff=DEAD_LETTER_BACKOFF)
    status = (row or {}).get("status")
    if status == "dead":
        _logger.error("worker.job_dead_lettered", job_type=job_type, reason=reason)
    else:
        _logger.warning(
            "worker.job_dead_letter_pending",
            job_type=job_type,
            status=status,
            reason=reason,
        )
    return row


async def _run_within_grace(
    handler_task: asyncio.Task[None], *, stop: asyncio.Event, grace_seconds: float
) -> bool:
    """핸들러가 끝났으면 True, grace 상한을 넘겨 반납해야 하면 False.

    ⚠️ 상한은 `stop`이 세워진 **뒤에만** 적용한다. 정상 운영 중에 상한으로 긴 잡을
    죽이면 하트비트 대신 잡 분할을 택한 D-16의 전제가 무너진다 — 분할 이전의 긴
    잡이 상한에 걸려 실패로 기록되기 때문이다.
    """
    stop_waiter = asyncio.create_task(stop.wait())
    try:
        done, _ = await asyncio.wait(
            {handler_task, stop_waiter}, return_when=asyncio.FIRST_COMPLETED
        )
        if handler_task in done:
            return True
        try:
            await asyncio.wait_for(handler_task, grace_seconds)
        except TimeoutError:
            return False
        return True
    finally:
        stop_waiter.cancel()


async def process_next_job(
    db: QueueDb,
    *,
    worker_id: str,
    stop: asyncio.Event,
    grace_seconds: float = WORKER_GRACE_SECONDS,
) -> bool:
    """잡 하나를 집어 처리한다. 집을 잡이 없거나 종료 중이면 False."""
    if stop.is_set():
        # 종료 신호 이후에는 새 잡을 집지 않는다 — 집는 순간 attempts가 소모된다.
        return False

    # ⚠️ 처리할 수 있는 type만 필터로 넘기면(`types=list(HANDLERS)`) 레지스트리 밖
    #    type이 큐에 남아 영원히 아무도 집지 않는 상태가 된다. 그래서 필터 없이
    #    전부 집어와 미등록 type을 명시적으로 데드레터로 보낸다 — 이것이
    #    0003_jobs.sql:31-36이 `jobs.type`에 CHECK를 걸지 않는 대가로 워커에게
    #    지운 책임이다. `HANDLERS`가 사실상의 잡 종류 열거이므로 그 검증 지점도
    #    여기 하나뿐이다.
    job = await db.claim_job(worker_id=worker_id)
    if job is None:
        return False

    job_id = str(job["id"])
    workspace_id = str(job["workspace_id"])
    job_type = str(job["type"])
    payload = job.get("payload") or {}

    bind_job_context(job_id=job_id, workspace_id=workspace_id)
    try:
        _logger.info(
            "worker.job_claimed",
            job_type=job_type,
            attempts=job.get("attempts"),
            max_attempts=job.get("max_attempts"),
        )
        try:
            handler = resolve_handler(job_type)
        except UnknownJobTypeError as error:
            await _dead_letter(db, job_id=job_id, job_type=job_type, reason=str(error))
            return True

        handler_task = asyncio.create_task(
            handler(job_id=job_id, workspace_id=workspace_id, payload=payload)
        )
        finished = await _run_within_grace(handler_task, stop=stop, grace_seconds=grace_seconds)
        if not finished:
            # ⚠️ 여기서 fail_job을 재사용하면 자발적 종료가 독약 잡 카운트를
            #    소모해 재배포 세 번에 정상 잡이 dead로 떨어진다. release_job이
            #    따로 존재하는 유일한 이유다 (02-CONTEXT.md > D-18).
            await db.release_job(job_id, worker_id=worker_id)
            _logger.info("worker.job_released", job_type=job_type, grace_seconds=grace_seconds)
            # 반납한 잡은 여기서 참조를 버린다. complete_job은 locked_by를 보지
            # 않으므로, 뒤늦게 완료 처리하면 이미 그 잡을 집어간 다른 워커의
            # 진행을 덮어쓴다 (T-02-40).
            return True

        try:
            await handler_task
        except Exception as error:  # noqa: BLE001 - 재시도/데드레터 판정은 fail_job의 몫
            _logger.exception("worker.job_failed", job_type=job_type)
            await db.fail_job(job_id, error=sanitize_error(error))
            return True

        await db.complete_job(job_id)
        _logger.info("worker.job_completed", job_type=job_type)
        return True
    finally:
        clear_job_context()


async def run_queue_loop(
    db: QueueDb,
    *,
    worker_id: str,
    stop: asyncio.Event,
    poll_interval: float = QUEUE_POLL_INTERVAL_SECONDS,
    grace_seconds: float = WORKER_GRACE_SECONDS,
) -> int:
    """종료 신호가 올 때까지 잡을 집어 처리하고, 처리한 잡 수를 돌려준다."""
    processed = 0
    while not stop.is_set():
        claimed = await process_next_job(
            db, worker_id=worker_id, stop=stop, grace_seconds=grace_seconds
        )
        if claimed:
            processed += 1
            continue
        await _wait_for_stop(stop, poll_interval)
    return processed
