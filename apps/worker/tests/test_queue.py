"""claim→complete 루프와 SIGTERM 반납 계약 회귀 테스트.

`FakeQueue`는 0003/0007의 큐 함수 계약(claim이 attempts를 올린다 · complete/fail은
`status = 'running'` 행에만 걸린다 · release는 `locked_by` 소유자만 통과시키고
attempts를 되돌린다)을 최소한으로 흉내 낸다. 워커 코드가 그 계약을 어떻게 쓰는지가
이 파일의 관심사이고, 함수 자신의 계약은 supabase/tests/0007_queue_functions.sql이
SQL 수준에서 이미 고정했다.

파일 후반부(`4. 실제 DB를 상대로 한 통합 검증`)는 대역 없이 로컬 Supabase 스택을
직접 상대한다. 멱등성과 반납 후 경합은 실제 함수 호출 없이는 증명되지 않기 때문이다
(02-SPEC.md Edge Coverage R10 두 행).
"""

import asyncio
import os
import secrets
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlsplit

import httpx
import pytest

from worker import __main__ as worker_main
from worker import handlers, queue
from worker.db.service import ServiceDb, service_client
from worker.errors import ProviderError, UnsafeFetchTarget
from worker.handlers import conflict
from worker.handlers.noop import handle_noop
from worker.settings import WorkerSettings

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
            "cancel_requested_at": None,
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

    async def dead_letter_job(
        self, job_id: str, *, worker_id: str, error: str
    ) -> dict[str, Any] | None:
        self.calls.append(("dead_letter_job", job_id))
        row = self.rows[job_id]
        if row["status"] != "running" or row["locked_by"] != worker_id:
            return None
        row.update(status="dead", last_error=error, locked_by=None)
        return dict(row)

    async def cancel_job(self, job_id: str, *, worker_id: str) -> dict[str, Any] | None:
        self.calls.append(("cancel_job", job_id))
        row = self.rows[job_id]
        if row["status"] != "running" or row["locked_by"] != worker_id:
            return None
        row.update(status="canceled", locked_by=None)
        return dict(row)

    async def reap_stale_jobs(self, *, timeout: str) -> list[dict[str, Any]]:  # noqa: ASYNC109
        self.calls.append(("reap_stale_jobs", timeout))
        return []


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


@pytest.mark.asyncio
async def test_idle_queue_periodically_reaps_stale_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeQueue()
    stop = asyncio.Event()
    waits = 0

    async def stop_after_interval(event: asyncio.Event, seconds: float) -> bool:
        del seconds
        nonlocal waits
        waits += 1
        if waits == queue.REAP_INTERVAL_CYCLES:
            event.set()
        return True

    monkeypatch.setattr(queue, "_wait_for_stop", stop_after_interval)
    await queue.run_queue_loop(db, worker_id=WORKER_ID, stop=stop, reap_timeout_seconds=900)
    assert db.called("reap_stale_jobs") == ["900 seconds"]


# -----------------------------------------------------------------------------
# 2. 데드레터 — 레지스트리에 없는 type (0003_jobs.sql:31-36의 계약)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_type_is_dead_lettered_with_the_type_in_last_error() -> None:
    db = FakeQueue()
    db.enqueue(job_type="complie", max_attempts=3)

    claimed = await queue.process_next_job(db, worker_id=WORKER_ID, stop=asyncio.Event())

    assert claimed is True
    row = db.rows[JOB_ID]
    assert row["status"] == "dead"
    assert "complie" in row["last_error"]
    # 재시도 대기 없이 즉시 판정한다 — 백오프를 0으로 보낸다.
    assert db.called("dead_letter_job") == [JOB_ID]
    assert db.called("fail_job") == []
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


@pytest.mark.asyncio
async def test_cancelled_claim_skips_handler_and_closes_the_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeQueue()
    row = db.enqueue()
    row["cancel_requested_at"] = "2026-08-10T00:00:00Z"
    invoked: list[str] = []

    async def recording(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
        del workspace_id, payload
        invoked.append(job_id)

    install_handler(monkeypatch, recording)
    assert await queue.process_next_job(db, worker_id=WORKER_ID, stop=asyncio.Event()) is True
    assert invoked == []
    assert db.called("cancel_job") == [JOB_ID]
    assert db.rows[JOB_ID]["status"] == "canceled"


def test_sanitize_error_hides_provider_response_and_credentials() -> None:
    provider = ProviderError(provider="openrouter", status_code=502, kind="upstream")
    leaked = "Bearer secret-token sk-or-v1-abcdefghijklmnopqrstuvwxyz"
    assert "openrouter" in queue.sanitize_error(provider)
    assert "502" in queue.sanitize_error(provider)
    result = queue.sanitize_error(RuntimeError(leaked))
    assert leaked not in result
    assert "[REDACTED]" in result


def test_sanitize_error_keeps_our_reason_token() -> None:
    result = queue.sanitize_error(UnsafeFetchTarget(reason="private_address"))
    assert "private_address" in result


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
    worker_id = queue.resolve_worker_id()

    assert worker_id == queue.resolve_worker_id()
    assert str(os.getpid()) in worker_id


# =============================================================================
# 4. 실제 DB를 상대로 한 통합 검증 — 멱등성과 반납 후 경합
#
# 위 단위 테스트는 큐 함수를 `FakeQueue`로 대체한다. 대역은 우리가 이해한 계약을
# 반영할 뿐이므로, 이해가 틀렸다면 대역도 같이 틀린다. SPEC Edge Coverage가 R10에
# idempotency와 concurrency 두 엣지를 covered로 표시했고 그 둘은 실제 함수 호출
# 없이 증명되지 않는다. 아래 셋은 로컬 스택을 직접 상대한다.
#
# ⚠️ 이 테스트들은 **로컬 전용**이다. 아래 loopback 가드가 없으면 환경에 남아 있는
#    클라우드 자격증명으로 프로덕션 큐에 잡을 만들고 지우게 된다. `.env.local`에는
#    실제 클라우드 키가 들어 있으므로 그 이름들(`SUPABASE_URL` 등)을 쓰지 않고
#    `NEXUSWIKI_LOCAL_*` 접두 변수만 읽는다.
# =============================================================================

LOCAL_SUPABASE_URL = os.environ.get("NEXUSWIKI_LOCAL_SUPABASE_URL", "http://127.0.0.1:54421")
# supabase CLI 로컬 스택의 기본 JWT 시크릿에서 파생되는 고정 service_role 키.
# 머신이 다르면 NEXUSWIKI_LOCAL_SERVICE_KEY로 덮어쓴다.
LOCAL_SERVICE_KEY = os.environ.get(
    "NEXUSWIKI_LOCAL_SERVICE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0."
    "EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU",
)
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "[::1]"})


@dataclass
class LocalQueueStack:
    """로컬 스택 위에 만든 1회용 워크스페이스와 그 위의 `ServiceDb`."""

    db: ServiceDb
    client: httpx.AsyncClient
    workspace_id: str
    user_id: str
    access_token: str

    async def enqueue(
        self,
        *,
        job_type: str = "noop",
        payload: dict[str, Any] | None = None,
        max_attempts: int = 3,
    ) -> dict[str, Any]:
        body = {
            "workspace_id": self.workspace_id,
            "type": job_type,
            "payload": payload if payload is not None else {"target_id": str(uuid.uuid4())},
            "max_attempts": max_attempts,
        }
        response = await self.client.post(
            "/jobs", json=body, headers={"Prefer": "return=representation"}
        )
        response.raise_for_status()
        return response.json()[0]

    async def fetch(self, job_id: str) -> dict[str, Any]:
        row = await self.db.get_job(job_id, workspace_id=self.workspace_id)
        assert row is not None, f"잡 {job_id} 가 사라졌다"
        return row


async def _local_stack_is_up() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as probe:
            response = await probe.get(
                f"{LOCAL_SUPABASE_URL}/rest/v1/",
                headers={"apikey": LOCAL_SERVICE_KEY},
            )
    except httpx.HTTPError:
        return False
    return response.status_code < 500


@pytest.fixture
async def local_queue() -> AsyncIterator[LocalQueueStack]:
    host = urlsplit(LOCAL_SUPABASE_URL).hostname
    assert host in LOOPBACK_HOSTS, (
        f"통합 테스트는 로컬 스택 전용이다 — {LOCAL_SUPABASE_URL} 은 loopback이 아니다"
    )
    if not await _local_stack_is_up():
        pytest.skip(f"로컬 Supabase 스택이 응답하지 않는다: {LOCAL_SUPABASE_URL}")

    settings = WorkerSettings(
        SUPABASE_URL=LOCAL_SUPABASE_URL,
        SUPABASE_PUBLISHABLE_KEY="local-publishable-unused-on-service-path",
        SUPABASE_SECRET_KEY=LOCAL_SERVICE_KEY,
        DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54422/postgres",
        OPENROUTER_API_KEY="unused-in-phase-2",
        OPENAI_API_KEY="unused-in-phase-2",
        LLM_MODEL="unused-in-phase-2",
    )

    async with service_client(settings) as client:
        # ⚠️ 워크스페이스는 service key로 만들 수 없다. 0007 섹션 8의 최소권한
        #    매트릭스가 `service_role`에 workspaces SELECT만 주었고, 생성은
        #    요청자 JWT의 경로이기 때문이다(0004의 workspaces_insert_self_owned).
        #    그래서 픽스처는 실제 배치와 같은 순서를 밟는다: 사용자를 만들고,
        #    그 사용자의 토큰으로 워크스페이스를 만들고, 잡만 service key로 다룬다.
        email = f"queue-{uuid.uuid4().hex[:12]}@example.invalid"
        password = secrets.token_urlsafe(24)
        created = await client.post(
            f"{LOCAL_SUPABASE_URL}/auth/v1/admin/users",
            json={"email": email, "password": password, "email_confirm": True},
        )
        created.raise_for_status()
        user_id = created.json()["id"]

        granted = await client.post(
            f"{LOCAL_SUPABASE_URL}/auth/v1/token?grant_type=password",
            json={"email": email, "password": password},
        )
        granted.raise_for_status()
        access_token = granted.json()["access_token"]

        # ⚠️ 사용자 삭제는 워크스페이스 생성이 실패해도 반드시 돌아야 한다. 안쪽에만
        #    두면 생성이 터진 실행마다 auth.users에 고아 계정이 쌓이고, 그 계정들은
        #    다음 실행에서 아무도 지우지 않는다.
        try:
            async with httpx.AsyncClient(
                base_url=f"{LOCAL_SUPABASE_URL}/rest/v1",
                headers={
                    "apikey": LOCAL_SERVICE_KEY,
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
                timeout=httpx.Timeout(10.0),
            ) as user_client:
                workspace_name = f"queue-it-{uuid.uuid4().hex[:8]}"
                workspace = await user_client.post(
                    "/workspaces",
                    json={"name": workspace_name, "slug": workspace_name, "owner_id": user_id},
                    headers={"Prefer": "return=representation"},
                )
                workspace.raise_for_status()
                workspace_id = workspace.json()[0]["id"]

                try:
                    yield LocalQueueStack(
                        db=ServiceDb(client),
                        client=client,
                        workspace_id=workspace_id,
                        user_id=user_id,
                        access_token=access_token,
                    )
                finally:
                    # 워크스페이스 삭제가 jobs를 cascade로 지운다(0003:29). `jobs`에는
                    # 어느 롤도 DELETE 권한이 없으므로 잔여 행을 지우는 유일한
                    # 경로가 이 cascade다.
                    await user_client.delete(f"/workspaces?id=eq.{workspace_id}")
                    leftovers = await client.get(
                        "/jobs", params={"workspace_id": f"eq.{workspace_id}", "select": "id"}
                    )
                    assert leftovers.json() == [], leftovers.text
        finally:
            # workspaces.owner_id 는 on delete restrict 이므로 사용자는 언제나 그 다음이다.
            await client.delete(f"{LOCAL_SUPABASE_URL}/auth/v1/admin/users/{user_id}")


def _local_worker_settings() -> WorkerSettings:
    return WorkerSettings(
        SUPABASE_URL=LOCAL_SUPABASE_URL,
        SUPABASE_PUBLISHABLE_KEY="local-publishable-unused-on-service-path",
        SUPABASE_SECRET_KEY=LOCAL_SERVICE_KEY,
        DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54422/postgres",
        OPENROUTER_API_KEY="unused-in-phase-5",
        OPENAI_API_KEY="unused-in-phase-5",
        LLM_MODEL="unused-in-phase-5",
    )


@pytest.mark.asyncio
async def test_local_budget_aggregate_is_complete_and_private(local_queue: LocalQueueStack) -> None:
    """The real RPC sees all rows and rejects Ask at the inclusive cap boundary."""
    now = datetime.now(UTC)
    since = datetime(now.year, now.month, 1, tzinfo=UTC).isoformat()
    total = 1001
    rows = [
        {
            "workspace_id": local_queue.workspace_id,
            "kind": "llm",
            "provider": "test",
            "model": "test",
            "cost_micros": 1,
            "occurred_at": since,
        }
        for _ in range(total)
    ]
    inserted = await local_queue.client.post(
        "/usage_events", json=rows, headers={"Prefer": "return=representation"}
    )
    inserted.raise_for_status()

    assert (
        await local_queue.db.sum_usage_events_since(
            workspace_id=local_queue.workspace_id, since=since
        )
        == total
    )

    async with httpx.AsyncClient(
        base_url=f"{LOCAL_SUPABASE_URL}/rest/v1",
        headers={
            "apikey": LOCAL_SERVICE_KEY,
            "Authorization": f"Bearer {local_queue.access_token}",
        },
    ) as requester:
        denied = await requester.post(
            "/rpc/sum_usage_events_since",
            json={"p_workspace_id": local_queue.workspace_id, "p_since": since},
        )
        assert denied.status_code in (401, 403), denied.text
        updated = await requester.patch(
            f"/workspaces?id=eq.{local_queue.workspace_id}",
            json={"monthly_budget_micros": total},
            headers={"Prefer": "return=representation"},
        )
        updated.raise_for_status()

    assert (
        await worker_main._check_ask_budget(_local_worker_settings(), local_queue.workspace_id)
        is False
    )


@pytest.mark.asyncio
async def test_local_automated_dispute_retains_human_verification_audit(
    local_queue: LocalQueueStack, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real service-role dispute must not overwrite an earlier requester audit stamp."""
    pages = []
    page_specs = (
        ("verified", "The policy permits this."),
        ("conflict", "The policy forbids this."),
    )
    for slug, content in page_specs:
        response = await local_queue.client.post(
            "/wiki_pages",
            json={
                "workspace_id": local_queue.workspace_id,
                "slug": f"{slug}-{uuid.uuid4().hex}",
                "title": slug,
                "category": "concepts",
                "content": content,
                "sources": ["source-under-test"],
            },
            headers={"Prefer": "return=representation"},
        )
        response.raise_for_status()
        pages.append(response.json()[0])
    first, second = pages

    async with httpx.AsyncClient(
        base_url=f"{LOCAL_SUPABASE_URL}/rest/v1",
        headers={
            "apikey": LOCAL_SERVICE_KEY,
            "Authorization": f"Bearer {local_queue.access_token}",
        },
    ) as requester:
        verified = await requester.patch(
            f"/wiki_pages?id=eq.{first['id']}&workspace_id=eq.{local_queue.workspace_id}",
            json={"verification_status": "verified"},
            headers={"Prefer": "return=representation"},
        )
        verified.raise_for_status()
        audited = verified.json()[0]
    assert audited["verified_by"] == local_queue.user_id
    assert audited["verified_at"] is not None
    audit_pair = (audited["verified_by"], audited["verified_at"])

    class CandidateAdapter:
        def __init__(self, real: ServiceDb) -> None:
            self.real = real

        async def list_wiki_pages_for_source(self, **_values: Any) -> list[dict[str, Any]]:
            return [first]

        async def find_similar_wiki_pages(self, **_values: Any) -> list[dict[str, Any]]:
            return [{"candidate_wiki_id": second["id"], "similarity": 0.99}]

        async def _select(self, table: str, *, params: dict[str, str]) -> list[dict[str, Any]]:
            return await self.real._select(table, params=params)  # noqa: SLF001

        async def set_wiki_page_disputed(self, wiki_id: str, *, workspace_id: str) -> None:
            await self.real.set_wiki_page_disputed(wiki_id, workspace_id=workspace_id)

        async def complete_job_and_chain(self, _job_id: str) -> None:
            return None

    async def contradiction(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(
            payload=conflict.ConflictJudgement(is_contradiction=True, rationale="facts clash")
        )

    monkeypatch.setattr(conflict, "complete_structured", contradiction)
    await conflict.run_conflict_check(
        CandidateAdapter(local_queue.db),  # type: ignore[arg-type]
        object(),
        settings=_local_worker_settings(),
        job_id=str(uuid.uuid4()),
        workspace_id=local_queue.workspace_id,
        payload={"raw_source_id": "source-under-test"},
    )

    current = await local_queue.db._select(  # noqa: SLF001
        "wiki_pages",
        params={
            "workspace_id": f"eq.{local_queue.workspace_id}",
            "id": f"in.({first['id']},{second['id']})",
        },
    )
    by_id = {row["id"]: row for row in current}
    assert by_id[first["id"]]["verification_status"] == "disputed"
    assert by_id[first["id"]]["disputed"] is True
    assert (by_id[first["id"]]["verified_by"], by_id[first["id"]]["verified_at"]) == audit_pair
    assert by_id[second["id"]]["verification_status"] == "disputed"
    assert by_id[second["id"]]["disputed"] is True


@pytest.mark.asyncio
async def test_reprocessing_a_finished_job_converges_to_succeeded(
    local_queue: LocalQueueStack,
) -> None:
    """at-least-once 재처리 — 같은 잡을 두 번 처리해도 상태가 수렴한다."""
    job = await local_queue.enqueue()
    job_id = job["id"]

    assert await queue.process_next_job(local_queue.db, worker_id="idem-A", stop=asyncio.Event())
    after_first = await local_queue.fetch(job_id)
    assert after_first["status"] == "succeeded", after_first

    # 두 번째 처리: 핸들러를 다시 돌리고 complete_job을 다시 부른다.
    await handle_noop(job_id=job_id, workspace_id=local_queue.workspace_id, payload=job["payload"])
    repeated = await local_queue.db.complete_job(job_id)

    # 이것이 참인 이유는 complete_job의 `where ... and status = 'running'`
    # 절(0003_jobs.sql:146)이 재호출을 예외가 아니라 0행 no-op으로 만들기
    # 때문이다. 이 테스트는 그 절에 의존하고 있다 — 절이 사라지면 여기서 깨진다.
    assert repeated is None
    after_second = await local_queue.fetch(job_id)
    assert after_second["status"] == "succeeded", after_second
    assert after_second["attempts"] == after_first["attempts"]


@pytest.mark.asyncio
async def test_late_completion_after_release_does_not_overwrite_another_worker(
    local_queue: LocalQueueStack, monkeypatch: pytest.MonkeyPatch
) -> None:
    """워커 A 반납 → 워커 B claim → A의 지연 완료 순서를 실제로 재현한다."""
    job = await local_queue.enqueue()
    job_id = job["id"]
    stop = asyncio.Event()
    started = asyncio.Event()

    async def never_finishing(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
        del job_id, workspace_id, payload
        started.set()
        await asyncio.Event().wait()

    install_handler(monkeypatch, never_finishing)

    task = asyncio.create_task(
        queue.process_next_job(local_queue.db, worker_id="A", stop=stop, grace_seconds=0.05)
    )
    await started.wait()
    stop.set()
    await task

    released = await local_queue.fetch(job_id)
    assert released["status"] == "queued", released
    assert released["attempts"] == 0, released
    assert released["locked_by"] is None, released

    claimed_by_b = await local_queue.db.claim_job(worker_id="B")
    assert claimed_by_b is not None and claimed_by_b["id"] == job_id

    held_by_b = await local_queue.fetch(job_id)
    # 워커 A의 루프는 반납 이후 그 잡 참조를 버렸다 — B의 진행이 그대로 살아 있다.
    assert held_by_b["status"] == "running", held_by_b
    assert held_by_b["locked_by"] == "B", held_by_b
    assert held_by_b["attempts"] == 1, held_by_b

    # ⚠️ 이 계약의 주체가 워커 코드라는 사실을 여기서 못 박는다. complete_job은
    #    locked_by를 보지 않으므로, A가 뒤늦게 부르면 실제로 B의 진행을 덮어쓴다.
    #    SQL이 막아주지 않는다 — 루프가 부르지 않는 것이 유일한 방어다.
    overwritten = await local_queue.db.complete_job(job_id)
    assert overwritten is not None and overwritten["status"] == "succeeded", overwritten


@pytest.mark.asyncio
async def test_real_job_delivers_its_workspace_scope_to_the_handler(
    local_queue: LocalQueueStack, monkeypatch: pytest.MonkeyPatch
) -> None:
    """service_role은 BYPASSRLS다 — 이 값이 닿지 않으면 Phase 3가 교차 테넌트를 읽는다."""
    payload = {"target_id": str(uuid.uuid4())}
    job = await local_queue.enqueue(payload=payload)
    seen: list[dict[str, Any]] = []

    async def recording(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
        seen.append({"job_id": job_id, "workspace_id": workspace_id, "payload": payload})

    install_handler(monkeypatch, recording)

    await queue.process_next_job(local_queue.db, worker_id="scope-A", stop=asyncio.Event())

    assert seen == [
        {"job_id": job["id"], "workspace_id": local_queue.workspace_id, "payload": payload}
    ], seen
    assert (await local_queue.fetch(job["id"]))["status"] == "succeeded"
