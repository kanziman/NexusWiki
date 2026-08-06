"""liveness와 readiness 라우터의 회귀 테스트."""

import time
from contextlib import asynccontextmanager
from typing import Any

import httpx
import pytest

from api.health_check import ReadinessResult, check_db_roundtrip
from api.main import create_app
from api.settings import ApiSettings
from nexuswiki_core.settings import MissingSettingError

# 닿을 수 없는 주소 — readiness가 반드시 실패 경로를 타게 한다.
UNREACHABLE_SUPABASE_URL = "http://127.0.0.1:9"


def build_settings(**overrides: str) -> ApiSettings:
    values: dict[str, str] = {
        "SUPABASE_URL": UNREACHABLE_SUPABASE_URL,
        "SUPABASE_PUBLISHABLE_KEY": "test-publishable-key",
    }
    values.update(overrides)
    return ApiSettings(**values)


@asynccontextmanager
async def app_client(settings: ApiSettings | None = None, *, git_sha: str = "test-sha") -> Any:
    app = create_app(settings if settings is not None else build_settings(), git_sha=git_sha)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


def test_create_app_stores_the_injected_settings_on_app_state() -> None:
    settings = build_settings()

    app = create_app(settings=settings, git_sha="sha-1")

    assert app.state.settings is settings
    assert app.state.git_sha == "sha-1"


@pytest.mark.asyncio
async def test_health_does_not_require_supabase_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)

    async with app_client() as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_reports_the_git_sha_handed_to_the_factory() -> None:
    async with app_client(git_sha="deadbeef") as client:
        response = await client.get("/health")

    assert response.json()["git_sha"] == "deadbeef"


@pytest.mark.asyncio
async def test_ready_returns_503_for_unreachable_database() -> None:
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
async def test_ready_never_invents_a_missing_env_reason_at_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 환경을 비워도 readiness는 주입된 설정만 보므로 부팅 시점 검증을 흉내내지 않는다.
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)

    async with app_client() as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert not response.json()["reason"].startswith("missing_env")


def test_incomplete_settings_fail_before_the_app_is_ever_built(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "test-publishable-key")

    with pytest.raises(MissingSettingError) as excinfo:
        create_app(ApiSettings())

    assert "SUPABASE_URL" in str(excinfo.value)


@pytest.mark.asyncio
async def test_db_roundtrip_result_has_stable_fields() -> None:
    async with httpx.AsyncClient() as client:
        result = await check_db_roundtrip(
            client,
            supabase_url=UNREACHABLE_SUPABASE_URL,
            publishable_key="test-publishable-key",
            timeout_seconds=0.1,
        )

    assert isinstance(result, ReadinessResult)
    assert set(vars(result)) == {"ok", "reason", "elapsed_ms"}
