"""배포된 worker에서 Supabase PostgREST RTT를 측정한다.

관련 태스크: P0-INIT-04
설계 근거: 01-CONTEXT.md > D-14 (SPEC 경계가 새 라우터를 금지하므로 측정을 worker 기동에 붙인다)
"""

import math
import time
from dataclasses import dataclass

import httpx

_perf_counter = time.perf_counter

RTT_WARMUP_COUNT: int = 5
RTT_SAMPLE_COUNT: int = 50
RTT_REQUEST_TIMEOUT_SECONDS: float = 5.0


@dataclass(frozen=True)
class RttResult:
    cold_first_ms: float | None
    p50_ms: float | None
    p95_ms: float | None
    sample_count: int
    warmup_count: int
    failures: int


async def measure_rtt(
    client: httpx.AsyncClient,
    *,
    supabase_url: str,
    publishable_key: str,
    sample_count: int = RTT_SAMPLE_COUNT,
    warmup_count: int = RTT_WARMUP_COUNT,
) -> RttResult:
    """콜드 요청, 워밍업, 표본 순서로 readiness와 같은 왕복을 측정한다."""
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/workspaces?select=id&limit=1"
    headers = {"apikey": publishable_key, "Accept": "application/json"}
    failures = 0

    async def request_once() -> float | None:
        nonlocal failures
        started = _perf_counter()
        try:
            response = await client.get(
                endpoint,
                headers=headers,
                timeout=httpx.Timeout(RTT_REQUEST_TIMEOUT_SECONDS),
            )
            elapsed_ms = (_perf_counter() - started) * 1000
            response.raise_for_status()
        except httpx.HTTPError:
            failures += 1
            return None
        return elapsed_ms

    cold_first_ms = await request_once()
    for _ in range(warmup_count):
        await request_once()

    samples: list[float] = []
    for _ in range(sample_count):
        if (elapsed := await request_once()) is not None:
            samples.append(elapsed)
    samples.sort()

    # Nearest-rank percentile: rank=ceil(p*N), converted to a zero-based index.
    def percentile(percent: float) -> float | None:
        if not samples:
            return None
        return samples[max(0, math.ceil(percent * len(samples)) - 1)]

    return RttResult(
        cold_first_ms=cold_first_ms,
        p50_ms=percentile(0.50),
        p95_ms=percentile(0.95),
        sample_count=len(samples),
        warmup_count=warmup_count,
        failures=failures,
    )
