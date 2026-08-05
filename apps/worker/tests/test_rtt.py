from collections.abc import Iterator
from dataclasses import fields

import httpx
import pytest

from worker import rtt


def clock_for(delays_ms: list[float]) -> Iterator[float]:
    now = 0.0
    for delay in delays_ms:
        yield now
        now += delay / 1000
        yield now


def client_with_statuses(statuses: list[int]) -> httpx.AsyncClient:
    remaining = iter(statuses)

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/v1/workspaces"
        assert dict(request.url.params) == {"select": "id", "limit": "1"}
        assert request.headers["apikey"] == "test-key"
        return httpx.Response(next(remaining), json=[])

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_result_populates_all_six_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = iter(clock_for([2.0] * 4))
    monkeypatch.setattr(rtt, "_perf_counter", lambda: next(clock))
    async with client_with_statuses([200] * 4) as client:
        result = await rtt.measure_rtt(
            client,
            supabase_url="https://example.invalid",
            publishable_key="test-key",
            sample_count=2,
            warmup_count=1,
        )
    assert {field.name for field in fields(result)} == {
        "cold_first_ms",
        "p50_ms",
        "p95_ms",
        "sample_count",
        "warmup_count",
        "failures",
    }
    assert result == rtt.RttResult(2.0, 2.0, 2.0, 2, 1, 0)


@pytest.mark.asyncio
async def test_nearest_rank_percentiles(monkeypatch: pytest.MonkeyPatch) -> None:
    delays = [1.0, *range(1, 101)]
    clock = iter(clock_for([float(value) for value in delays]))
    monkeypatch.setattr(rtt, "_perf_counter", lambda: next(clock))
    async with client_with_statuses([200] * 101) as client:
        result = await rtt.measure_rtt(
            client,
            supabase_url="https://example.invalid",
            publishable_key="test-key",
            sample_count=100,
            warmup_count=0,
        )
    assert result.p50_ms == pytest.approx(50.0)
    assert result.p95_ms == pytest.approx(95.0)


@pytest.mark.asyncio
async def test_warmups_are_excluded_from_fifty_samples(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = iter(clock_for([99.0] * 6 + [3.0] * 50))
    monkeypatch.setattr(rtt, "_perf_counter", lambda: next(clock))
    async with client_with_statuses([200] * 56) as client:
        result = await rtt.measure_rtt(
            client,
            supabase_url="https://example.invalid",
            publishable_key="test-key",
            sample_count=50,
        )
    assert result.sample_count == 50
    assert result.warmup_count == 5
    assert result.p50_ms == pytest.approx(3.0)


@pytest.mark.asyncio
async def test_partial_failures_are_counted(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = iter(clock_for([1.0, 1.0, 1.0]))
    monkeypatch.setattr(rtt, "_perf_counter", lambda: next(clock))
    async with client_with_statuses([500, 200, 500]) as client:
        result = await rtt.measure_rtt(
            client,
            supabase_url="https://example.invalid",
            publishable_key="test-key",
            sample_count=2,
            warmup_count=0,
        )
    assert result.failures == 2
    assert result.sample_count == 1
    assert result.p50_ms is not None


@pytest.mark.asyncio
async def test_all_failures_return_empty_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rtt, "_perf_counter", lambda: 0.0)
    async with client_with_statuses([500] * 4) as client:
        result = await rtt.measure_rtt(
            client,
            supabase_url="https://example.invalid",
            publishable_key="test-key",
            sample_count=3,
            warmup_count=0,
        )
    assert result.sample_count == 0
    assert result.p50_ms is None
    assert result.p95_ms is None
    assert result.failures == 4
