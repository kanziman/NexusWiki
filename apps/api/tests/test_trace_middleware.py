"""요청 trace 계약 (#159). 로컬 스택 없이 ASGITransport로 돈다."""

from __future__ import annotations

from uuid import UUID, uuid4

import httpx
import pytest
import structlog
from structlog.testing import capture_logs

from api.errors import WorkspaceForbidden
from api.main import create_app
from api.services.ask import HttpLlmStreamClient
from api.services.retrieval import HttpQueryEmbeddingClient
from api.settings import ApiSettings
from nexuswiki_core.trace import TRACE_HEADER, bind_trace, current_trace_id

_FORGED = str(uuid4())


def _app():  # noqa: ANN202 - 테스트 헬퍼
    app = create_app(
        ApiSettings(
            SUPABASE_URL="https://example.invalid",
            SUPABASE_PUBLISHABLE_KEY="sb_publishable_test",
        ),
        git_sha="test-sha",
    )

    async def ok() -> dict[str, str | None]:
        return {"trace_id": current_trace_id()}

    async def forbidden() -> None:
        raise WorkspaceForbidden(table="t", affected=0)

    async def boom() -> None:
        raise RuntimeError("처리되지 않은 예외")

    app.add_api_route("/_test/ok", ok)
    app.add_api_route("/_test/forbidden", forbidden)
    app.add_api_route("/_test/boom", boom)
    return app


def _client(app) -> httpx.AsyncClient:  # noqa: ANN001 - 테스트 헬퍼
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    )


@pytest.mark.asyncio
async def test_response_carries_server_issued_trace_visible_to_the_handler() -> None:
    async with _client(_app()) as client:
        response = await client.get("/_test/ok")

    trace_id = response.headers[TRACE_HEADER]
    assert str(UUID(trace_id)) == trace_id
    assert response.json()["trace_id"] == trace_id


@pytest.mark.asyncio
async def test_each_request_gets_its_own_trace() -> None:
    async with _client(_app()) as client:
        first = await client.get("/_test/ok")
        second = await client.get("/_test/ok")

    assert first.headers[TRACE_HEADER] != second.headers[TRACE_HEADER]


@pytest.mark.asyncio
async def test_client_supplied_trace_is_ignored() -> None:
    async with _client(_app()) as client:
        response = await client.get("/_test/ok", headers={TRACE_HEADER: _FORGED})

    assert response.headers[TRACE_HEADER] != _FORGED
    assert response.json()["trace_id"] != _FORGED


@pytest.mark.asyncio
async def test_handled_error_response_carries_trace() -> None:
    async with _client(_app()) as client:
        response = await client.get("/_test/forbidden")

    assert response.status_code == 403
    assert UUID(response.headers[TRACE_HEADER])


@pytest.mark.asyncio
async def test_validation_error_response_carries_trace() -> None:
    async with _client(_app()) as client:
        response = await client.post(
            f"/workspaces/{uuid4()}/ask",
            json={},
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 422
    assert UUID(response.headers[TRACE_HEADER])


@pytest.mark.asyncio
async def test_unhandled_exception_response_carries_trace_without_leaking_detail() -> None:
    async with _client(_app()) as client:
        response = await client.get("/_test/boom")

    assert response.status_code == 500
    assert UUID(response.headers[TRACE_HEADER])
    assert "처리되지 않은" not in response.text


@pytest.mark.asyncio
async def test_browser_can_read_the_trace_header_through_cors() -> None:
    async with _client(_app()) as client:
        response = await client.get("/_test/ok", headers={"Origin": "http://localhost:3000"})

    exposed = response.headers.get("access-control-expose-headers", "")
    assert TRACE_HEADER.lower() in exposed.lower()


@pytest.mark.asyncio
async def test_request_log_carries_the_same_trace_and_no_query_string() -> None:
    with capture_logs(processors=[structlog.contextvars.merge_contextvars]) as logs:
        async with _client(_app()) as client:
            response = await client.get("/_test/ok", params={"q": "비밀 질문"})

    entry = next(log for log in logs if log["event"] == "api.request_completed")
    assert entry["trace_id"] == response.headers[TRACE_HEADER]
    assert entry["status_code"] == 200
    assert "비밀" not in str(entry)


@pytest.mark.asyncio
async def test_trace_does_not_leak_after_the_request() -> None:
    async with _client(_app()) as client:
        await client.get("/_test/ok")

    assert current_trace_id() is None


@pytest.mark.asyncio
async def test_query_embedding_call_forwards_current_trace() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        return httpx.Response(200, json={"vector": [0.0] * 1024})

    trace_id = str(uuid4())
    bind_trace(trace_id)
    try:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            await HttpQueryEmbeddingClient(
                http,
                url="http://worker",
                token="t",  # noqa: S106
                timeout_seconds=1.0,
            ).embed("질문", workspace_id="ws-1")
    finally:
        structlog.contextvars.clear_contextvars()

    assert seen[TRACE_HEADER.lower()] == trace_id
    assert seen["x-workspace-id"] == "ws-1"


@pytest.mark.asyncio
async def test_llm_stream_call_forwards_current_trace() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        return httpx.Response(200, text="data: [DONE]\n")

    trace_id = str(uuid4())
    bind_trace(trace_id)
    try:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            stream = HttpLlmStreamClient(
                http,
                url="http://worker",
                token="t",  # noqa: S106
                timeout_seconds=1.0,
            ).stream(workspace_id="w", messages=[])
            async with stream as response:
                assert response.status_code == 200
    finally:
        structlog.contextvars.clear_contextvars()

    assert seen[TRACE_HEADER.lower()] == trace_id
