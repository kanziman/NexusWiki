"""claim→complete 루프와 SIGTERM 반납 계약 회귀 테스트.

`FakeQueue`는 0003/0007의 큐 함수 계약(claim이 attempts를 올린다 · complete/fail은
`status = 'running'` 행에만 걸린다 · release는 `locked_by` 소유자만 통과시키고
attempts를 되돌린다)을 최소한으로 흉내 낸다. 워커 코드가 그 계약을 어떻게 쓰는지가
이 파일의 관심사이고, 함수 자신의 계약은 supabase/tests/0007_queue_functions.sql이
SQL 수준에서 이미 고정했다.
"""

import asyncio
from typing import Any

import pytest

from worker import handlers, queue

WORKER_ID = "worker-under-test"
WORKSPACE_ID = "11111111-1111-4111-8111-111111111111"
JOB_ID = "22222222-2222-4222-8222-222222222222"


class FakeQueue:
    """`ServiceDb`의 큐 RPC 4종만 흉내 내는 인메모리 대역."""

    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}
        self.calls: list[tuple[str, str]] = []
        self.fail_backoffs: list[str | None] = []

    def enqueue(
        self,
        *,
        job_id: str = JOB_ID,
        workspace_id: str = WORKSPACE_ID,
        job_type: str = "noop",
        payload: dict[str, Any] | None = None,
        max_attempts: int = 3,
        attempts: int = 0,
    ) -> dict[str, Any]:
        row = {
            "id": job_id,
            "workspace_id": workspace_id,
            "type": job_type,
            "status": "queued",
            "payload": payload if payload is not None else {},
            "attempts": attempts,
            "max_attempts": max_attempts,
            "last_error": None,
            "locked_by": None,
        }
        self.rows[job_id] = row
        return row

    def called(self, function: str) -> list[str]:
        return [job_id for name, job_id in self.calls if name == function]

    async def claim_job(
        self, *, worker_id: str, types: list[str] | None = None
    ) -> dict[str, Any] | None:
        self.calls.append(("claim_job", worker_id))
        for row in self.rows.values():
            if row["status"] not in ("queued", "failed"):
                continue
            if types is not None and row["type"] not in types:
                continue
            row["status"] = "running"
            row["attempts"] += 1
            row["locked_by"] = worker_id
            return dict(row)
        return None

    async def complete_job(self, job_id: str) -> dict[str, Any] | None:
        self.calls.append(("complete_job", job_id))
        row = self.rows[job_id]
        if row["status"] != "running":  # 0003:146 의 where ... and status = 'running'
            return None
        row.update(status="succeeded", last_error=None, locked_by=None)
        return dict(row)

    async def fail_job(
        self,
        job_id: str,
        *,
        error: str,
        backoff: str | None = None,
        max_backoff: str | None = None,
    ) -> dict[str, Any] | None:
        del max_backoff
        self.calls.append(("fail_job", job_id))
        self.fail_backoffs.append(backoff)
        row = self.rows[job_id]
        if row["status"] != "running":
            return None
        row["status"] = "dead" if row["attempts"] >= row["max_attempts"] else "failed"
        row.update(last_error=error, locked_by=None)
        return dict(row)

    async def release_job(self, job_id: str, *, worker_id: str) -> dict[str, Any] | None:
        self.calls.append(("release_job", job_id))
        row = self.rows[job_id]
        # 0007 섹션 4의 locked_by 술어 — 소유자가 아니면 0행 no-op이다.
        if row["status"] != "running" or row["locked_by"] != worker_id:
            return None
        row.update(status="queued", locked_by=None)
        row["attempts"] -= 1
        return dict(row)


def install_handler(
    monkeypatch: pytest.MonkeyPatch, handler: Any, *, job_type: str = "noop"
) -> None:
    monkeypatch.setitem(handlers.HANDLERS, job_type, handler)


# -----------------------------------------------------------------------------
# 1. claim → 핸들러 → complete
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_noop_job_claim_to_complete() -> None:
    db = FakeQueue()
    db.enqueue()

    claimed = await queue.process_next_job(db, worker_id=WORKER_ID, stop=asyncio.Event())

    assert claimed is True
    assert db.called("complete_job") == [JOB_ID]
    assert db.rows[JOB_ID]["status"] == "succeeded"
    assert db.rows[JOB_ID]["locked_by"] is None


@pytest.mark.asyncio
async def test_empty_queue_waits_for_the_poll_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeQueue()
    stop = asyncio.Event()
    waits: list[float] = []

    async def record_wait(event: asyncio.Event, seconds: float) -> bool:
        waits.append(seconds)
        event.set()  # 두 번째 바퀴를 돌지 않도록 종료 신호로 대신한다
        return True

    monkeypatch.setattr(queue, "_wait_for_stop", record_wait)

    processed = await queue.run_queue_loop(db, worker_id=WORKER_ID, stop=stop)

    assert processed == 0
    assert waits == [queue.QUEUE_POLL_INTERVAL_SECONDS]
    # 빈 큐에서 바쁜 대기(claim 연타)를 하지 않는다.
    assert len(db.called("claim_job")) == 1


# -----------------------------------------------------------------------------
# 2. 데드레터 — 레지스트리에 없는 type (0003_jobs.sql:31-36의 계약)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_type_is_dead_lettered_with_the_type_in_last_error() -> None:
    db = FakeQueue()
    # max_attempts=1 이면 첫 claim에서 attempts=1 이 되어 곧바로 dead가 된다.
    db.enqueue(job_type="complie", max_attempts=1)

    claimed = await queue.process_next_job(db, worker_id=WORKER_ID, stop=asyncio.Event())

    assert claimed is True
    row = db.rows[JOB_ID]
    assert row["status"] == "dead"
    assert "complie" in row["last_error"]
    # 재시도 대기 없이 즉시 판정한다 — 백오프를 0으로 보낸다.
    assert db.fail_backoffs == [queue.DEAD_LETTER_BACKOFF]
    assert db.called("complete_job") == []


@pytest.mark.asyncio
async def test_unknown_type_never_reaches_a_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeQueue()
    db.enqueue(job_type="complie", max_attempts=1)
    invoked: list[str] = []

    async def recording(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
        del workspace_id, payload
        invoked.append(job_id)

    install_handler(monkeypatch, recording)

    await queue.process_next_job(db, worker_id=WORKER_ID, stop=asyncio.Event())

    assert invoked == []


# -----------------------------------------------------------------------------
# 3. 핸들러 실패 — fail_job이 재시도/데드레터를 판정한다
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handler_exception_is_reported_through_fail_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeQueue()
    db.enqueue(max_attempts=3)

    async def exploding(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
        del job_id, workspace_id, payload
        raise RuntimeError("handler boom")

    install_handler(monkeypatch, exploding)

    claimed = await queue.process_next_job(db, worker_id=WORKER_ID, stop=asyncio.Event())

    assert claimed is True
    row = db.rows[JOB_ID]
    assert row["status"] == "failed"  # 남은 시도가 있으므로 dead가 아니다
    assert "RuntimeError" in row["last_error"]
    assert len(row["last_error"]) <= queue.LAST_ERROR_MAX_CHARS
    assert db.called("complete_job") == []


@pytest.mark.asyncio
async def test_handler_exception_becomes_dead_when_attempts_are_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeQueue()
    db.enqueue(max_attempts=1)

    async def exploding(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
        del job_id, workspace_id, payload
        raise RuntimeError("handler boom")

    install_handler(monkeypatch, exploding)

    await queue.process_next_job(db, worker_id=WORKER_ID, stop=asyncio.Event())

    assert db.rows[JOB_ID]["status"] == "dead"


# -----------------------------------------------------------------------------
# 4. SIGTERM — 새 claim 금지, grace 상한, attempts 소모 없는 반납 (D-18)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_prevents_a_new_claim() -> None:
    db = FakeQueue()
    db.enqueue()
    stop = asyncio.Event()
    stop.set()

    claimed = await queue.process_next_job(db, worker_id=WORKER_ID, stop=stop)

    assert claimed is False
    assert db.called("claim_job") == []
    assert db.rows[JOB_ID]["status"] == "queued"
    assert db.rows[JOB_ID]["attempts"] == 0


@pytest.mark.asyncio
async def test_job_finishing_within_grace_completes_normally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeQueue()
    db.enqueue()
    stop = asyncio.Event()
    started = asyncio.Event()
    finish = asyncio.Event()

    async def slow(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
        del job_id, workspace_id, payload
        started.set()
        await finish.wait()

    install_handler(monkeypatch, slow)

    task = asyncio.create_task(
        queue.process_next_job(db, worker_id=WORKER_ID, stop=stop, grace_seconds=5.0)
    )
    await started.wait()
    stop.set()
    finish.set()

    assert await task is True
    assert db.rows[JOB_ID]["status"] == "succeeded"
    assert db.called("release_job") == []


@pytest.mark.asyncio
async def test_job_exceeding_grace_is_released_without_consuming_an_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeQueue()
    db.enqueue()
    attempts_before_claim = db.rows[JOB_ID]["attempts"]
    stop = asyncio.Event()
    started = asyncio.Event()

    async def never_finishing(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
        del job_id, workspace_id, payload
        started.set()
        await asyncio.Event().wait()

    install_handler(monkeypatch, never_finishing)

    task = asyncio.create_task(
        queue.process_next_job(db, worker_id=WORKER_ID, stop=stop, grace_seconds=0.01)
    )
    await started.wait()
    stop.set()
    await task

    row = db.rows[JOB_ID]
    assert db.called("release_job") == [JOB_ID], db.calls
    assert row["status"] == "queued"
    # ⚠️ 여기가 D-18의 전부다. fail_job을 재사용했다면 attempts가 1로 남아
    #    재배포 세 번에 정상 잡이 dead로 떨어진다.
    assert row["attempts"] == attempts_before_claim
    # 반납한 잡에 대해 완료/실패 처리를 시도하지 않는다 (T-02-40).
    assert db.called("complete_job") == []
    assert db.called("fail_job") == []


# -----------------------------------------------------------------------------
# 5. 워크스페이스 스코프와 로그 컨텍스트
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handler_receives_workspace_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeQueue()
    db.enqueue(payload={"target_id": "t-1"})
    seen: list[dict[str, Any]] = []

    async def recording(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
        seen.append({"job_id": job_id, "workspace_id": workspace_id, "payload": payload})

    install_handler(monkeypatch, recording)

    await queue.process_next_job(db, worker_id=WORKER_ID, stop=asyncio.Event())

    assert seen == [
        {"job_id": JOB_ID, "workspace_id": WORKSPACE_ID, "payload": {"target_id": "t-1"}}
    ]


@pytest.mark.asyncio
async def test_job_context_is_bound_and_always_cleared(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeQueue()
    db.enqueue()
    bound: list[dict[str, str | None]] = []
    cleared: list[int] = []

    def record_bind(*, job_id: str | None = None, workspace_id: str | None = None) -> None:
        bound.append({"job_id": job_id, "workspace_id": workspace_id})

    monkeypatch.setattr(queue, "bind_job_context", record_bind)
    monkeypatch.setattr(queue, "clear_job_context", lambda: cleared.append(1))

    async def exploding(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
        del job_id, workspace_id, payload
        raise RuntimeError("handler boom")

    install_handler(monkeypatch, exploding)

    await queue.process_next_job(db, worker_id=WORKER_ID, stop=asyncio.Event())

    assert bound == [{"job_id": JOB_ID, "workspace_id": WORKSPACE_ID}]
    # 핸들러가 터져도 finally가 컨텍스트를 지운다 — 잡 간 컨텍스트 누수 방지 (T-02-45).
    assert cleared == [1]


# -----------------------------------------------------------------------------
# 6. 상수와 워커 식별자
# -----------------------------------------------------------------------------


def test_grace_is_shorter_than_the_platform_grace_period() -> None:
    # ⚠️ 같거나 길면 반납이 시작되기 전에 프로세스가 죽어 잡이 running으로 남고
    #    reap_stale_jobs 기본 15분을 기다려야 한다 (02-CONTEXT.md > D-18).
    assert queue.WORKER_GRACE_SECONDS < queue.PLATFORM_GRACE_SECONDS


def test_worker_id_is_stable_within_a_process_and_names_the_pid() -> None:
    import os

    worker_id = queue.resolve_worker_id()

    assert worker_id == queue.resolve_worker_id()
    assert str(os.getpid()) in worker_id
