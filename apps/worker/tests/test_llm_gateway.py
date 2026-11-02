"""모든 공급자 호출의 사용량이 빠짐없이 기록되는지 고정한다 (#161, #162)."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import structlog
from pydantic import BaseModel

from nexuswiki_core.trace import bind_trace
from worker import llm
from worker.errors import LlmSchemaError
from worker.llm_gateway import LlmCallContext, LlmGateway, record_stream_usage
from worker.settings import WorkerSettings

_TRACE_ID = "7f3a19c2-1111-4222-8333-444455556666"
_CONTEXT = LlmCallContext(workspace_id="ws-1", job_id="job-1", call="compile")


class _Payload(BaseModel):
    value: str


class _Sink:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    async def insert_usage_event(self, *, workspace_id: str, row: dict[str, Any]) -> None:
        self.rows.append({"workspace_id": workspace_id, **row})


def _settings() -> WorkerSettings:
    return WorkerSettings(
        _env_file=None,
        SUPABASE_URL="https://example.invalid",
        SUPABASE_PUBLISHABLE_KEY="sb_publishable_test",
        SUPABASE_SECRET_KEY="sb_secret_test",  # noqa: S106 - 테스트 픽스처
        DATABASE_URL="postgresql://postgres:pw@127.0.0.1:54422/postgres",
        OPENROUTER_API_KEY="sk-or-v1-test",
        LLM_MODEL="test-model",
        EMBEDDING_MODEL="baai/bge-m3",
        EMBEDDING_PROVIDER="deepinfra/fp32",
    )


def _completion(content: str, *, cost: float) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": content}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 10,
                "total_tokens": 110,
                "cost": cost,
            },
            "provider": "Anthropic",
            "model": "test-model",
        },
    )


def _client(contents: list[str], *, cost: float = 0.01) -> httpx.AsyncClient:
    index = {"n": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        content = contents[min(index["n"], len(contents) - 1)]
        index["n"] += 1
        return _completion(content, cost=cost)

    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url=llm.OPENROUTER_BASE_URL
    )


@pytest.mark.asyncio
async def test_retry_records_one_usage_event_per_provider_call() -> None:
    sink = _Sink()
    async with _client(["```json 깨짐", json.dumps({"value": "ok"})]) as client:
        result = await LlmGateway(sink, client, _settings()).complete_structured(
            _CONTEXT, system_prompt="s", user_prompt="u", schema_model=_Payload
        )

    assert result.payload == _Payload(value="ok")
    assert [row["metadata"]["attempt"] for row in sink.rows] == [1, 2]
    assert sum(row["cost_micros"] for row in sink.rows) == 20_000


@pytest.mark.asyncio
async def test_every_attempt_failing_still_records_all_spending() -> None:
    sink = _Sink()
    async with _client(["JSON이 아님"]) as client:
        with pytest.raises(LlmSchemaError):
            await LlmGateway(sink, client, _settings()).complete_structured(
                _CONTEXT, system_prompt="s", user_prompt="u", schema_model=_Payload
            )

    assert sum(row["cost_micros"] for row in sink.rows) == 30_000
    assert len(sink.rows) == llm.STRUCTURED_OUTPUT_MAX_ATTEMPTS


@pytest.mark.asyncio
async def test_usage_row_carries_attribution_and_no_body() -> None:
    sink = _Sink()
    bind_trace(_TRACE_ID)
    try:
        async with _client([json.dumps({"value": "고유한-응답-문자열"})]) as client:
            await LlmGateway(sink, client, _settings()).complete_structured(
                LlmCallContext(
                    workspace_id="ws-1",
                    job_id="job-1",
                    call="compile",
                    metadata={"raw_source_id": "r"},
                ),
                system_prompt="s",
                user_prompt="고유한-프롬프트-문자열",
                schema_model=_Payload,
            )
    finally:
        structlog.contextvars.clear_contextvars()

    row = sink.rows[0]
    assert row["workspace_id"] == "ws-1"
    assert row["job_id"] == "job-1"
    assert row["trace_id"] == _TRACE_ID
    assert row["kind"] == "llm"
    assert row["duration_ms"] >= 0
    assert row["metadata"] == {"call": "compile", "raw_source_id": "r", "attempt": 1}
    serialized = json.dumps(row, ensure_ascii=False)
    assert "고유한-프롬프트-문자열" not in serialized
    assert "고유한-응답-문자열" not in serialized


@pytest.mark.asyncio
async def test_request_body_is_unchanged_by_the_gateway() -> None:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return _completion(json.dumps({"value": "ok"}), cost=0.01)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url=llm.OPENROUTER_BASE_URL
    ) as client:
        await LlmGateway(_Sink(), client, _settings()).complete_structured(
            _CONTEXT, system_prompt="s", user_prompt="u", schema_model=_Payload
        )

    assert bodies[0]["messages"] == [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u"},
    ]
    assert set(bodies[0]) == {"model", "messages", "usage", "response_format", "provider"}


@pytest.mark.asyncio
async def test_embedding_call_records_usage_and_empty_input_records_nothing() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "provider": "DeepInfra",
                "model": "baai/bge-m3",
                "data": [{"embedding": [0.0] * 1024}],
                "usage": {"prompt_tokens": 7, "total_tokens": 7, "cost": 0.000001},
            },
        )

    sink = _Sink()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url=llm.OPENROUTER_BASE_URL
    ) as client:
        gateway = LlmGateway(sink, client, _settings())
        await gateway.embed_texts(
            LlmCallContext(workspace_id="ws-1", job_id="job-1", call="embed_source"),
            texts=["본문"],
        )
        await gateway.embed_texts(
            LlmCallContext(workspace_id="ws-1", job_id="job-1", call="embed_source"), texts=[]
        )

    assert len(sink.rows) == 1
    assert sink.rows[0]["kind"] == "embedding"
    assert sink.rows[0]["cost_micros"] == 1
    assert sink.rows[0]["metadata"] == {"call": "embed_source"}


@pytest.mark.parametrize(
    "usage,incomplete,expected_metadata",
    [
        ({"prompt_tokens": 5, "total_tokens": 6, "cost": 0.5}, False, {"call": "ask"}),
        ({}, True, {"call": "ask", "incomplete": True}),
    ],
)
@pytest.mark.asyncio
async def test_stream_usage_marks_incomplete_calls(
    usage: dict[str, Any], incomplete: bool, expected_metadata: dict[str, Any]
) -> None:
    sink = _Sink()
    await record_stream_usage(
        sink,
        LlmCallContext(workspace_id="ws-1", call="ask"),
        usage=usage,
        duration_ms=12,
        incomplete=incomplete,
    )

    assert sink.rows[0]["job_id"] is None
    assert sink.rows[0]["duration_ms"] == 12
    assert sink.rows[0]["metadata"] == expected_metadata


_PROVIDER_FUNCTIONS = {"complete_structured", "stream_chat", "embed_texts"}
_GUARDED_DIR = Path(__file__).parents[1] / "src" / "worker" / "handlers"
_GUARDED_FILES = [*_GUARDED_DIR.glob("*.py"), _GUARDED_DIR.parent / "__main__.py"]


@pytest.mark.parametrize("path", _GUARDED_FILES, ids=lambda path: path.name)
def test_callers_cannot_import_provider_functions_directly(path: Path) -> None:
    """핸들러가 공급자 함수를 직접 쓰면 사용량 기록이 다시 누락된다 (design D4)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("worker.")
        for alias in node.names
    }

    assert not imported & _PROVIDER_FUNCTIONS
