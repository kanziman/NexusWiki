"""noop claim→complete 왕복 기준선의 백분위 산술과 표본 부족 분기 회귀 테스트.

시계는 주입하고 DB는 대역으로 바꾼다 — 여기서 고정하는 것은 산술과 분기이지
네트워크가 아니다. 실제 왕복은 배포된 Railway worker가 잰다 (02-CONTEXT.md > D-17).
"""

from collections.abc import Iterator
from dataclasses import fields
from typing import Any

import httpx
import pytest

from worker import queue_baseline

WORKSPACE_ID = "11111111-1111-4111-8111-111111111111"
WORKER_ID = "probe-worker-1"


def clock_for(delays_ms: list[float]) -> Iterator[float]:
    """왕복 하나가 시계를 정확히 두 번 읽는다는 전제로 시각열을 만든다."""
    now = 0.0
    for delay in delays_ms:
        yield now
        now += delay / 1000
        yield now


class FakeQueue:
    """0003/0007 큐 함수의 계약을 흉내 내는 대역.

    ⚠️ 대역이 흉내 내는 것은 "insert한 잡을 claim이 그대로 돌려준다"와 "0행이면
    None"뿐이다. 이 이해가 맞는지는 02-07의 실제 DB 통합 테스트가 이미 증명했다.
    """

    def __init__(self, *, failing_rounds: set[int] | None = None) -> None:
        self.failing_rounds = failing_rounds or set()
        self.round = 0
        self.enqueued: list[dict[str, Any]] = []
        self.completed: list[str] = []
        self.released: list[str] = []

    async def enqueue_job(
        self,
        *,
        workspace_id: str,
        job_type: str,
        payload: dict[str, Any],
        max_attempts: int = 1,
    ) -> dict[str, Any] | None:
        self.round += 1
        job = {
            "id": f"job-{self.round}",
            "workspace_id": workspace_id,
            "type": job_type,
            "payload": payload,
            "max_attempts": max_attempts,
        }
        self.enqueued.append(job)
        return job

    async def claim_job(
        self, *, worker_id: str, types: list[str] | None = None
    ) -> dict[str, Any] | None:
        return self.enqueued[-1] if self.enqueued else None

    async def complete_job(self, job_id: str) -> dict[str, Any] | None:
        if self.round in self.failing_rounds:
            return None
        self.completed.append(job_id)
        return {"id": job_id, "status": "succeeded"}

    async def release_job(self, job_id: str, *, worker_id: str) -> dict[str, Any] | None:
        self.released.append(job_id)
        return {"id": job_id, "status": "queued"}


class ForeignClaimQueue(FakeQueue):
    """claim이 자기 잡이 아닌 다른 잡을 돌려주는 경합 상황."""

    async def claim_job(
        self, *, worker_id: str, types: list[str] | None = None
    ) -> dict[str, Any] | None:
        return {"id": "someone-elses-job", "type": "noop"}


async def measure(
    db: FakeQueue,
    *,
    sample_count: int,
    warmup_count: int = 0,
) -> queue_baseline.QueueBaselineResult:
    return await queue_baseline.measure_queue_roundtrip(
        db,
        workspace_id=WORKSPACE_ID,
        worker_id=WORKER_ID,
        sample_count=sample_count,
        warmup_count=warmup_count,
    )


# -----------------------------------------------------------------------------
# 1. 결과 형태
# -----------------------------------------------------------------------------


async def test_result_populates_all_seven_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = iter(clock_for([2.0] * 4))
    monkeypatch.setattr(queue_baseline, "_perf_counter", lambda: next(clock))

    result = await measure(FakeQueue(), sample_count=2, warmup_count=1)

    assert {field.name for field in fields(result)} == {
        "cold_first_ms",
        "p50_ms",
        "p95_ms",
        "p99_ms",
        "sample_count",
        "warmup_count",
        "failures",
    }
    assert result.sample_count == 2
    assert result.warmup_count == 1
    assert result.failures == 0


async def test_sample_constant_supports_the_p99_claim() -> None:
    # SPEC R11: 워밍업 제외 성공 표본이 200회 이상이어야 p99를 주장할 수 있다.
    assert (
        queue_baseline.QUEUE_BASELINE_SAMPLE_COUNT >= queue_baseline.QUEUE_BASELINE_P99_MIN_SAMPLES
    )
    assert queue_baseline.QUEUE_BASELINE_P99_MIN_SAMPLES == 200
    # 테스트가 시계를 주입할 수 있어야 백분위 산술을 결정적으로 검증할 수 있다.
    assert hasattr(queue_baseline, "_perf_counter")


# -----------------------------------------------------------------------------
# 2. 백분위 산술 — 최근접 순위 (rtt.py와 같은 방식)
# -----------------------------------------------------------------------------


async def test_nearest_rank_percentiles(monkeypatch: pytest.MonkeyPatch) -> None:
    delays = [1.0, *(float(value) for value in range(1, 201))]
    clock = iter(clock_for(delays))
    monkeypatch.setattr(queue_baseline, "_perf_counter", lambda: next(clock))

    result = await measure(FakeQueue(), sample_count=200)

    assert result.p50_ms == pytest.approx(100.0)
    assert result.p95_ms == pytest.approx(190.0)
    assert result.p99_ms == pytest.approx(198.0)


async def test_cold_first_roundtrip_is_separated_from_warmups_and_samples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = iter(clock_for([500.0, 400.0, 3.0, 3.0]))
    monkeypatch.setattr(queue_baseline, "_perf_counter", lambda: next(clock))

    result = await measure(FakeQueue(), sample_count=2, warmup_count=1)

    assert result.cold_first_ms == pytest.approx(500.0)
    assert result.warmup_count == 1
    assert result.sample_count == 2
    assert result.p50_ms == pytest.approx(3.0)


# -----------------------------------------------------------------------------
# 3. 표본 부족이면 p99를 주장하지 않는다 (SPEC Edge Coverage R11)
# -----------------------------------------------------------------------------


async def test_two_hundred_samples_yield_a_p99(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = iter(clock_for([7.0] * 201))
    monkeypatch.setattr(queue_baseline, "_perf_counter", lambda: next(clock))

    result = await measure(FakeQueue(), sample_count=200)

    assert result.sample_count == 200
    assert result.p99_ms == pytest.approx(7.0)


async def test_one_hundred_ninety_nine_samples_refuse_to_claim_a_p99(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = iter(clock_for([7.0] * 200))
    monkeypatch.setattr(queue_baseline, "_perf_counter", lambda: next(clock))

    result = await measure(FakeQueue(), sample_count=199)

    assert result.sample_count == 199
    assert result.p99_ms is None
    # 표본이 부족해도 p50/p95는 그대로 남는다 — 주장을 줄이는 것이지 버리는 것이 아니다.
    assert result.p50_ms is not None
    assert result.p95_ms is not None


# -----------------------------------------------------------------------------
# 4. 실패 회차
# -----------------------------------------------------------------------------


async def test_failed_roundtrips_are_counted_and_excluded_from_samples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = iter(clock_for([5.0] * 4))
    monkeypatch.setattr(queue_baseline, "_perf_counter", lambda: next(clock))

    # 1회차는 콜드, 2·4회차가 complete_job에서 0행으로 돌아온다.
    result = await measure(FakeQueue(failing_rounds={2, 4}), sample_count=3)

    assert result.failures == 2
    assert result.sample_count == 1
    assert result.cold_first_ms == pytest.approx(5.0)


async def test_no_successful_samples_yields_no_percentiles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = iter(clock_for([5.0] * 4))
    monkeypatch.setattr(queue_baseline, "_perf_counter", lambda: next(clock))

    result = await measure(FakeQueue(failing_rounds={1, 2, 3, 4}), sample_count=3)

    assert result.sample_count == 0
    assert result.cold_first_ms is None
    assert result.p50_ms is None
    assert result.p95_ms is None
    assert result.p99_ms is None
    assert result.failures == 4


async def test_transport_errors_are_counted_not_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = iter(clock_for([5.0] * 2))
    monkeypatch.setattr(queue_baseline, "_perf_counter", lambda: next(clock))

    class ExplodingQueue(FakeQueue):
        async def claim_job(
            self, *, worker_id: str, types: list[str] | None = None
        ) -> dict[str, Any] | None:
            raise httpx.ConnectError("boom")

    result = await measure(ExplodingQueue(), sample_count=1)

    assert result.failures == 2
    assert result.sample_count == 0


# -----------------------------------------------------------------------------
# 5. 남의 잡을 집으면 반납하고 그 회차를 버린다
# -----------------------------------------------------------------------------


async def test_a_foreign_claim_is_released_and_discarded(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = iter(clock_for([5.0] * 2))
    monkeypatch.setattr(queue_baseline, "_perf_counter", lambda: next(clock))

    db = ForeignClaimQueue()
    result = await measure(db, sample_count=1)

    assert db.released == ["someone-elses-job", "someone-elses-job"]
    assert db.completed == []
    assert result.sample_count == 0
    assert result.failures == 2
