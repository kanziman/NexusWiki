import asyncio

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
