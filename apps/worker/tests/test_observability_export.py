"""게이트웨이가 사용량 기록 뒤에 내보내고 그 실패에 영향받지 않는지 고정한다 (#167)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest
import structlog

from nexuswiki_core import observability
from nexuswiki_core.trace import bind_trace
from worker.llm_gateway import LlmCallContext, record_stream_usage

_TRACE_ID = "7f3a19c2-1111-4222-8333-444455556666"
# ASCII만 쓴다. 한글은 JSON 직렬화에서 XXXX로 바뀌어 유출되어도 부재 단언을 통과한다.
_BODY = "unique-body-zq81x"


class _FakeLangfuse:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create_trace_id(self, *, seed: str) -> str:
        return f"lf-{seed}"

    def start_observation(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(end=lambda: None)


class _BrokenLangfuse:
    def create_trace_id(self, *, seed: str) -> str:
        return seed

    def start_observation(self, **_: Any) -> None:
        raise ConnectionError("관측 서비스 장애")


class _Sink:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    async def insert_usage_event(self, *, workspace_id: str, row: dict[str, Any]) -> None:
        self.rows.append({"workspace_id": workspace_id, **row})


@pytest.fixture(autouse=True)
def _clean_context() -> Any:
    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()


@pytest.fixture
def langfuse(monkeypatch: pytest.MonkeyPatch) -> _FakeLangfuse:
    fake = _FakeLangfuse()
    monkeypatch.setattr(observability, "_client", fake)
    return fake


async def _stream_usage(sink: _Sink, *, metadata: dict[str, Any] | None = None) -> None:
    await record_stream_usage(
        sink,
        LlmCallContext(workspace_id="ws-1", call="ask_answer", metadata=metadata or {}),
        usage={
            "provider": "p",
            "model": "m",
            "prompt_tokens": 3,
            "completion_tokens": 2,
            "total_tokens": 5,
            "cost": 0.001,
        },
        duration_ms=7,
        incomplete=False,
    )


@pytest.mark.asyncio
async def test_gateway_exports_each_usage_row_without_input_or_output(
    langfuse: _FakeLangfuse,
) -> None:
    bind_trace(_TRACE_ID)
    sink = _Sink()

    await _stream_usage(sink, metadata={"raw_source_id": _BODY, "route": "STANDARD"})

    [call] = langfuse.calls
    assert call["as_type"] == "generation"
    assert call["model"] == "m"
    assert call["usage_details"] == {"input": 3, "output": 2, "total": 5}
    # 비용의 원천은 `usage_events`다. 내보낸 값은 같은 행에서 나온 사본이어야 한다.
    assert call["cost_details"]["total"] == sink.rows[0]["cost_micros"] / 1_000_000
    assert call["metadata"]["duration_ms"] == 7
    assert call["metadata"]["route"] == "STANDARD"
    assert "input" not in call
    assert "output" not in call
    assert _BODY not in json.dumps(call, ensure_ascii=False)


@pytest.mark.asyncio
async def test_export_outage_leaves_usage_rows_intact(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(observability, "_client", _BrokenLangfuse())
    bind_trace(_TRACE_ID)
    sink = _Sink()

    await _stream_usage(sink)

    assert len(sink.rows) == 1
    assert sink.rows[0]["trace_id"] == _TRACE_ID


@pytest.mark.asyncio
async def test_failed_usage_insert_still_propagates_and_exports_nothing(
    langfuse: _FakeLangfuse,
) -> None:
    # 내보내기가 기록 실패를 가리면 안 된다. Postgres에 없는 비용을 외부에만 남기지도 않는다.
    class FailingSink:
        async def insert_usage_event(self, *, workspace_id: str, row: dict[str, Any]) -> None:
            raise RuntimeError("usage insert failed")

    bind_trace(_TRACE_ID)

    with pytest.raises(RuntimeError, match="usage insert failed"):
        await _stream_usage(FailingSink())  # type: ignore[arg-type]

    assert langfuse.calls == []
