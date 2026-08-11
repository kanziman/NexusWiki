import asyncio
from typing import Any

import pytest

from worker import __main__ as worker_main
from worker.settings import WorkerSettings


def _settings() -> WorkerSettings:
    return WorkerSettings(
        SUPABASE_URL="https://example.invalid",
        SUPABASE_PUBLISHABLE_KEY="sb_publishable_test",
        SUPABASE_SECRET_KEY="sb_secret_test",  # noqa: S106 - test fixture
        DATABASE_URL="postgresql://postgres:pw@127.0.0.1:54422/postgres",
        OPENROUTER_API_KEY="sk-or-v1-test",
        LLM_MODEL="test-model",
        QUERY_EMBEDDING_INTERNAL_TOKEN="test-internal-token",  # noqa: S105, S106
        QUERY_EMBEDDING_RATE_CAPACITY=7,
        QUERY_EMBEDDING_RATE_REFILL_TOKENS_PER_SECOND=2.5,
    )


@pytest.mark.asyncio
async def test_query_embedding_listener_receives_explicit_rate_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructed: dict[str, object] = {}

    class FakeService:
        def __init__(self, embed: object, **kwargs: object) -> None:
            constructed.update(kwargs)

    class FakeServer:
        def __init__(self, config: object) -> None:
            self.should_exit = False

        async def serve(self) -> None:
            await asyncio.sleep(0)

    monkeypatch.setattr(worker_main, "QueryEmbeddingService", FakeService)
    monkeypatch.setattr(worker_main, "add_query_embedding_route", lambda app, service: None)
    monkeypatch.setattr(worker_main, "add_llm_stream_route", lambda app, service: None)
    monkeypatch.setattr(worker_main.uvicorn, "Server", FakeServer)

    stop = asyncio.Event()
    stop.set()
    await worker_main._serve_internal_listeners(_settings(), stop)

    assert constructed["rate_capacity"] == 7
    assert constructed["refill_tokens_per_second"] == 2.5


@pytest.mark.asyncio
async def test_ask_budget_uses_monthly_spend_and_rejects_equal_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    class FakeClient:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *args: object) -> None:
            return None

    class FakeDb:
        def __init__(self, client: object) -> None:
            pass

        async def get_workspace_budget_cap(self, *, workspace_id: str) -> int | None:
            seen["workspace_id"] = workspace_id
            return 100

        async def sum_usage_events_since(self, *, workspace_id: str, since: str) -> int:
            seen["since"] = since
            return 100

    monkeypatch.setattr(worker_main, "service_client", lambda settings: FakeClient())
    monkeypatch.setattr(worker_main, "ServiceDb", FakeDb)

    assert await worker_main._check_ask_budget(_settings(), "ws-1") is False
    assert seen["workspace_id"] == "ws-1"
    assert str(seen["since"]).endswith("+00:00")


@pytest.mark.asyncio
async def test_record_ask_usage_converts_provider_cost_to_microdollars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: dict[str, Any] = {}

    class FakeClient:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *args: object) -> None:
            return None

    class FakeDb:
        def __init__(self, client: object) -> None:
            pass

        async def insert_usage_event(self, *, workspace_id: str, row: dict[str, Any]) -> None:
            recorded["workspace_id"] = workspace_id
            recorded["row"] = row

    monkeypatch.setattr(worker_main, "service_client", lambda settings: FakeClient())
    monkeypatch.setattr(worker_main, "ServiceDb", FakeDb)

    await worker_main._record_ask_usage(
        _settings(), "ws-1", {"cost": 0.0000011, "prompt_tokens": 2, "model": "m"}
    )

    assert recorded["workspace_id"] == "ws-1"
    assert recorded["row"] == {
        "job_id": None,
        "kind": "llm",
        "provider": "openrouter",
        "model": "m",
        "prompt_tokens": 2,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cost_micros": 2,
        "metadata": {},
    }
