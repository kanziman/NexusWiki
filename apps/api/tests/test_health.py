"""liveness와 readiness 라우터의 회귀 테스트."""

import time
from contextlib import asynccontextmanager

import httpx
import pytest
from api.health_check import ReadinessResult, check_db_roundtrip
from api.main import app


@asynccontextmanager
async def app_client():
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            yield client


@pytest.mark.asyncio
async def test_health_does_not_require_supabase_env(monkeypatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)

    async with app_client() as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ready_returns_503_for_unreachable_database(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "test-publishable-key")

    started = time.monotonic()
    async with app_client() as client:
        response = await client.get("/health/ready")
    elapsed = time.monotonic() - started

    assert elapsed < 3.0
    assert response.status_code == 503
    assert response.json()["reason"] in {
        "db_roundtrip_timeout",
        "db_unreachable",
    }


@pytest.mark.asyncio
async def test_db_roundtrip_result_has_stable_fields() -> None:
    async with httpx.AsyncClient() as client:
        result = await check_db_roundtrip(
            client,
            supabase_url="http://127.0.0.1:9",
            publishable_key="test-publishable-key",
            timeout_seconds=0.1,
        )

    assert isinstance(result, ReadinessResult)
    assert set(vars(result)) == {"ok", "reason", "elapsed_ms"}
