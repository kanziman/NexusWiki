"""배포된 worker에서 noop 잡의 claim→complete 왕복을 반복 측정한다.

관련 태스크: P2-JOB-01
설계 근거: 02-CONTEXT.md > D-17 (Phase 2가 실측할 수 있는 것은 noop 잡의 큐
           오버헤드뿐이며, 최종 reap 타임아웃은 Phase 3에서 확정한다)
설계 근거: checklists.json > decisions.job_queue

구조는 `worker/rtt.py`와 같다 — 콜드 1회 → 워밍업 N회 → 표본 M회, 최근접 순위
백분위. 다른 것은 재는 대상이 HTTP 왕복이 아니라 **claim→complete 왕복**이라는
점 하나다. 두 기준선을 나란히 놓고 읽으려면 산출 방식이 같아야 한다.

측정 구간의 경계 (이 선택이 유도되는 타임아웃의 의미를 정한다)

    enqueue ──┐                    ┌── 측정 구간 ──┐
              └─ insert into jobs ─┤ claim_job ... complete_job ├─
                                   └ locked_at 이 찍힘 ─────────┘

  인큐는 측정 구간 **밖**이다. `reap_stale_jobs`가 보는 나이는 `locked_at`
  기준이고(0003:185-196), `locked_at`은 claim 시점에 찍힌다. 인큐부터 claim까지의
  대기 시간은 큐에 잡이 쌓인 정도이지 워커가 잡을 붙들고 있는 시간이 아니므로,
  타임아웃이 덮어야 하는 구간에 포함되지 않는다.

소비자: `worker.__main__.main` (`QUEUE_BASELINE_ENABLED`가 참일 때 기동 시 1회)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Final, Protocol
from uuid import uuid4

import httpx

_perf_counter = perf_counter

__all__ = [
    "QUEUE_BASELINE_JOB_TYPE",
    "QUEUE_BASELINE_P99_MIN_SAMPLES",
    "QUEUE_BASELINE_SAMPLE_COUNT",
    "QUEUE_BASELINE_WARMUP_COUNT",
    "BaselineQueueDb",
    "QueueBaselineResult",
    "measure_queue_roundtrip",
]

# 워밍업은 rtt.py와 같은 5회. 커넥션과 PostgREST 준비 비용을 표본에서 뺀다.
QUEUE_BASELINE_WARMUP_COUNT: Final[int] = 5

# ⚠️ p99를 주장하려면 워밍업 제외 성공 표본이 200회 이상이어야 한다 (SPEC R11).
#    실패가 섞여도 200을 넘기도록 여유를 둔 값이다 — 220회를 시도해 20회까지의
#    실패를 흡수한다. 이 값을 200으로 낮추면 실패 한 번에 p99를 잃는다.
QUEUE_BASELINE_SAMPLE_COUNT: Final[int] = 220

# ⚠️ 이 문턱 아래에서는 p99를 계산하지 않고 None으로 둔다. 표본 200개 미만에서
#    최근접 순위 p99는 사실상 최댓값이며, "p99"라는 이름이 그 한 표본에 근거 없는
#    신뢰를 준다. 값을 지어내지 않는 것이 여기서 유일하게 옳은 동작이다.
#    근거: 02-CONTEXT.md > D-17, SPEC Edge Coverage R11.
QUEUE_BASELINE_P99_MIN_SAMPLES: Final[int] = 200

# 프로브가 만들고 처리하는 잡 종류. LLM 비용이 0인 유일한 핸들러다.
QUEUE_BASELINE_JOB_TYPE: Final[str] = "noop"


@dataclass(frozen=True)
class QueueBaselineResult:
    cold_first_ms: float | None
    p50_ms: float | None
    p95_ms: float | None
    p99_ms: float | None
    sample_count: int
    warmup_count: int
    failures: int


class BaselineQueueDb(Protocol):
    """이 프로브가 쓰는 `ServiceDb`의 부분집합."""

    async def enqueue_job(
        self,
        *,
        workspace_id: str,
        job_type: str,
        payload: dict[str, Any],
        max_attempts: int = ...,
    ) -> dict[str, Any] | None: ...

    async def claim_job(
        self, *, worker_id: str, types: list[str] | None = ...
    ) -> dict[str, Any] | None: ...

    async def complete_job(self, job_id: str) -> dict[str, Any] | None: ...

    async def release_job(self, job_id: str, *, worker_id: str) -> dict[str, Any] | None: ...


async def measure_queue_roundtrip(
    db: BaselineQueueDb,
    *,
    workspace_id: str,
    worker_id: str,
    sample_count: int = QUEUE_BASELINE_SAMPLE_COUNT,
    warmup_count: int = QUEUE_BASELINE_WARMUP_COUNT,
) -> QueueBaselineResult:
    """콜드 왕복, 워밍업, 표본 순서로 claim→complete 왕복을 측정한다."""
    failures = 0

    async def roundtrip_once() -> float | None:
        nonlocal failures

        # 각 회차가 자기 잡을 만든다. target_id를 매번 새로 만드는 이유는 0007의
        # jobs_dedup_idx가 (workspace_id, type, payload ->> 'target_id') 위의 부분
        # 유니크 인덱스라, 같은 키로 두 번째를 넣으면 23505로 막히기 때문이다.
        try:
            job = await db.enqueue_job(
                workspace_id=workspace_id,
                job_type=QUEUE_BASELINE_JOB_TYPE,
                payload={"target_id": str(uuid4())},
                max_attempts=1,
            )
        except httpx.HTTPError:
            job = None
        if job is None:
            failures += 1
            return None
        job_id = str(job["id"])

        started = _perf_counter()
        succeeded = False
        try:
            # ⚠️ `types` 필터를 반드시 건다. `claim_job`은 id로 지정할 수 없는 전역
            #    폴링이므로, 필터 없이 부르면 프로브가 운영 잡을 집어가 그 잡을
            #    핸들러 없이 complete 처리한다 — 실제 일이 조용히 사라진다.
            claimed = await db.claim_job(worker_id=worker_id, types=[QUEUE_BASELINE_JOB_TYPE])
            if claimed is None:
                pass
            elif str(claimed["id"]) != job_id:
                # 같은 type의 남의 잡을 집었다. 즉시 반납하고 이 회차를 버린다 —
                # complete를 부르면 그 잡의 실제 처리가 없었던 일이 된다.
                await db.release_job(str(claimed["id"]), worker_id=worker_id)
            else:
                succeeded = await db.complete_job(job_id) is not None
        except httpx.HTTPError:
            succeeded = False
        elapsed_ms = (_perf_counter() - started) * 1000

        if not succeeded:
            failures += 1
            return None
        return elapsed_ms

    cold_first_ms = await roundtrip_once()
    for _ in range(warmup_count):
        await roundtrip_once()

    samples: list[float] = []
    for _ in range(sample_count):
        if (elapsed := await roundtrip_once()) is not None:
            samples.append(elapsed)
    samples.sort()

    # 최근접 순위 백분위: rank = ceil(p × N)을 0-기반 인덱스로. rtt.py:69-73과
    # 같은 식이어야 두 기준선을 같은 표에 놓고 읽을 수 있다.
    def percentile(percent: float) -> float | None:
        if not samples:
            return None
        return samples[max(0, math.ceil(percent * len(samples)) - 1)]

    return QueueBaselineResult(
        cold_first_ms=cold_first_ms,
        p50_ms=percentile(0.50),
        p95_ms=percentile(0.95),
        p99_ms=percentile(0.99) if len(samples) >= QUEUE_BASELINE_P99_MIN_SAMPLES else None,
        sample_count=len(samples),
        warmup_count=warmup_count,
        failures=failures,
    )
