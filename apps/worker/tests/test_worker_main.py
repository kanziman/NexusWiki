import asyncio
from typing import Any

import pytest
import structlog

from nexuswiki_core.trace import TraceMiddleware
from worker import __main__ as worker_main
from worker import embedding as embedding_provider
from worker.embedding import EmbeddingResult
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
        def __init__(self, config: Any) -> None:
            constructed["middleware"] = [m.cls for m in config.app.user_middleware]
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
    assert constructed["middleware"] == [TraceMiddleware]


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
        _settings(),
        "ws-1",
        {"cost": 0.0000011, "prompt_tokens": 2, "model": "m"},
        incomplete=False,
        duration_ms=15,
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
        "metadata": {"call": "ask"},
        "trace_id": None,
        "duration_ms": 15,
    }


class _FakeHttpClient:
    async def __aenter__(self) -> object:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


def _patch_query_embedding(
    monkeypatch: pytest.MonkeyPatch, rows: list[tuple[str, dict[str, Any]]], *, fail: bool = False
) -> None:
    class FakeDb:
        def __init__(self, client: object) -> None:
            pass

        async def insert_usage_event(self, *, workspace_id: str, row: dict[str, Any]) -> None:
            if fail:
                raise RuntimeError("db unavailable")
            rows.append((workspace_id, row))

    async def fake_embed(*_: Any, **__: Any) -> EmbeddingResult:
        return EmbeddingResult([[0.0] * 1024], 7, 0, 7, 11, "DeepInfra", "baai/bge-m3")

    monkeypatch.setattr(worker_main, "openrouter_client", lambda settings: _FakeHttpClient())
    monkeypatch.setattr(worker_main, "service_client", lambda settings: _FakeHttpClient())
    monkeypatch.setattr(worker_main, "ServiceDb", FakeDb)
    monkeypatch.setattr(embedding_provider, "embed_texts", fake_embed)


@pytest.mark.asyncio
async def test_query_embedding_records_usage_under_the_request_workspace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows: list[tuple[str, dict[str, Any]]] = []
    _patch_query_embedding(monkeypatch, rows)
    trace_id = "7f3a19c2-1111-4222-8333-444455556666"

    with structlog.contextvars.bound_contextvars(workspace_id="ws-1", trace_id=trace_id):
        vector = await worker_main._embed_query(_settings(), "질문")
    await asyncio.gather(*worker_main._pending_usage_writes)

    assert len(vector) == 1024
    workspace_id, row = rows[0]
    assert workspace_id == "ws-1"
    assert row["kind"] == "embedding"
    assert row["cost_micros"] == 11
    assert row["trace_id"] == trace_id
    assert row["job_id"] is None
    assert row["metadata"] == {"call": "query_embedding"}
    assert "질문" not in str(row)


@pytest.mark.asyncio
async def test_query_embedding_survives_a_usage_record_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_query_embedding(monkeypatch, [], fail=True)

    with structlog.contextvars.bound_contextvars(workspace_id="ws-1"):
        vector = await worker_main._embed_query(_settings(), "질문")
    await asyncio.gather(*worker_main._pending_usage_writes)

    assert len(vector) == 1024


@pytest.mark.asyncio
async def test_query_embedding_without_workspace_serves_and_records_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows: list[tuple[str, dict[str, Any]]] = []
    _patch_query_embedding(monkeypatch, rows)

    vector = await worker_main._embed_query(_settings(), "질문")
    await asyncio.gather(*worker_main._pending_usage_writes)

    assert len(vector) == 1024
    assert rows == []


@pytest.mark.asyncio
@pytest.mark.parametrize("queue_fails", [False, True])
async def test_shutdown_flushes_only_after_the_queue_loop_finished(
    monkeypatch: pytest.MonkeyPatch, queue_fails: bool
) -> None:
    # ⚠️ flush가 큐 루프보다 먼저 돌면 잡 반납에 쓸 `WORKER_GRACE_SECONDS`를 소모한다.
    order: list[str] = []

    class FakeClient:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *args: object) -> None:
            return None

    async def noop(*args: object, **kwargs: object) -> None:
        return None

    async def run_queue_loop(*args: object, **kwargs: object) -> int:
        order.append("queue_finished")
        if queue_fails:
            raise RuntimeError("queue loop failed")
        return 0

    def configure(**kwargs: Any) -> bool:
        order.append("configured")
        assert kwargs["secret_key"] is None
        return False

    def flush() -> bool:
        order.append("flushed")
        return True

    settings = _settings().model_copy(update={"RTT_PROBE_ENABLED": False})
    monkeypatch.setattr(worker_main, "WorkerSettings", lambda: settings)
    monkeypatch.setattr(worker_main, "configure_logging", lambda **kwargs: None)
    # Windows의 이벤트 루프는 신호 처리기를 지원하지 않는다. 이 테스트의 관심사도 아니다.
    monkeypatch.setattr(asyncio.get_running_loop(), "add_signal_handler", lambda *args: None)
    monkeypatch.setattr(worker_main, "resolve_git_sha", lambda: "test-sha")
    monkeypatch.setattr(worker_main, "resolve_worker_id", lambda: "worker-test")
    monkeypatch.setattr(worker_main, "service_client", lambda settings: FakeClient())
    monkeypatch.setattr(worker_main, "ServiceDb", lambda client: object())
    monkeypatch.setattr(worker_main, "assert_enums_match_db", noop)
    monkeypatch.setattr(worker_main, "_run_queue_baseline_probe", noop)
    monkeypatch.setattr(worker_main, "_serve_internal_listeners", noop)
    monkeypatch.setattr(worker_main, "run_queue_loop", run_queue_loop)
    monkeypatch.setattr(worker_main, "configure_observability", configure)
    monkeypatch.setattr(worker_main, "flush_observability", flush)

    if queue_fails:
        with pytest.raises(ExceptionGroup):
            await worker_main.main()
    else:
        await worker_main.main()

    assert order == ["configured", "queue_finished", "flushed"]
