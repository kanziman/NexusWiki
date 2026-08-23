"""Ask 스레드 이력 — 오프라인 라우트·영속 순서 회귀.

관련: openspec/changes/ask-thread-history/tasks.md 슬라이스 1–3
"""

from __future__ import annotations

import json
from uuid import uuid4

import httpx
import pytest

from api.main import create_app
from api.services.ask import NO_EVIDENCE_MESSAGE, AskService
from tests.test_ask_router import (
    _ASK_PATH,
    _PERSISTED_THREAD_ID,
    _ask_body,
    _EmptyRetrievalService,
    _FakeLlmStream,
    _parse_sse,
    _persist_ok,
    _settings,
    _UpstreamResponse,
)


def _auth() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


@pytest.mark.asyncio
async def test_ask_without_client_turn_id_is_422() -> None:
    app = create_app(_settings(), git_sha="test-sha")
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                _ASK_PATH.format(workspace_id=uuid4()),
                json={"query": "질문"},
                headers=_auth(),
            )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_persist_rpc_runs_before_done_and_done_carries_thread_id() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path == "/rest/v1/rpc/persist_ask_turn":
            body = json.loads(request.content.decode())
            assert body["p_status"] == "no-evidence"
            assert body["p_client_turn_id"]
            return _persist_ok()
        return httpx.Response(200, json=[])

    app = create_app(_settings(), git_sha="test-sha")
    fake_llm = _FakeLlmStream(_UpstreamResponse([]))
    async with app.router.lifespan_context(app):
        app.state.http_client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), timeout=httpx.Timeout(2.0)
        )
        app.state.ask_service = AskService(_EmptyRetrievalService(), fake_llm)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                _ASK_PATH.format(workspace_id=uuid4()),
                json=_ask_body(),
                headers=_auth(),
            )
        await app.state.http_client.aclose()

    events = _parse_sse(response.text)
    names = [name for name, _ in events]
    assert names == ["meta", "citations", "done"]
    assert "/rest/v1/rpc/persist_ask_turn" in seen
    assert seen.index("/rest/v1/rpc/persist_ask_turn") >= 0
    assert events[-1][1]["thread_id"] == _PERSISTED_THREAD_ID
    assert events[1][1]["text"] == NO_EVIDENCE_MESSAGE


@pytest.mark.asyncio
async def test_persist_failure_omits_done() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/rpc/persist_ask_turn":
            return httpx.Response(
                401,
                json={"code": "42501", "message": "permission denied"},
            )
        return httpx.Response(200, json=[])

    app = create_app(_settings(), git_sha="test-sha")
    fake_llm = _FakeLlmStream(_UpstreamResponse([]))
    async with app.router.lifespan_context(app):
        app.state.http_client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), timeout=httpx.Timeout(2.0)
        )
        app.state.ask_service = AskService(_EmptyRetrievalService(), fake_llm)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                _ASK_PATH.format(workspace_id=uuid4()),
                json=_ask_body(),
                headers=_auth(),
            )
        await app.state.http_client.aclose()

    names = [name for name, _ in _parse_sse(response.text)]
    assert names == ["meta", "citations"]
    assert "done" not in names


@pytest.mark.asyncio
async def test_thread_crud_uses_user_db_and_maps_empty_get_to_forbidden() -> None:
    thread_id = str(uuid4())
    workspace_id = str(uuid4())
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path))
        if request.url.path == "/rest/v1/ask_threads" and request.method == "GET":
            if request.url.params.get("id"):
                return httpx.Response(200, json=[])
            return httpx.Response(
                200,
                json=[
                    {
                        "id": thread_id,
                        "title": "첫 질문",
                        "created_at": "2026-08-23T00:00:00Z",
                        "updated_at": "2026-08-23T00:00:00Z",
                    }
                ],
            )
        if request.url.path == "/rest/v1/ask_threads" and request.method == "PATCH":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": thread_id,
                        "title": "새 제목",
                        "created_at": "2026-08-23T00:00:00Z",
                        "updated_at": "2026-08-23T00:01:00Z",
                    }
                ],
            )
        if request.url.path == "/rest/v1/ask_threads" and request.method == "DELETE":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": thread_id,
                        "title": "첫 질문",
                        "created_at": "2026-08-23T00:00:00Z",
                        "updated_at": "2026-08-23T00:00:00Z",
                    }
                ],
            )
        if request.url.path == "/rest/v1/ask_messages":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": str(uuid4()),
                        "client_turn_id": str(uuid4()),
                        "question": "질문",
                        "answer_text": "답 [[wiki:w1]]",
                        "citations": {
                            "text": "답 [[wiki:w1]]",
                            "resolved": [{"alias": "w1", "kind": "wiki", "id": "wiki-1"}],
                        },
                        "status": "resolved",
                        "created_at": "2026-08-23T00:00:00Z",
                    }
                ],
            )
        raise AssertionError(request.url)

    app = create_app(_settings(), git_sha="test-sha")
    async with app.router.lifespan_context(app):
        app.state.http_client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), timeout=httpx.Timeout(2.0)
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            listed = await client.get(f"/workspaces/{workspace_id}/ask/threads", headers=_auth())
            missing = await client.get(
                f"/workspaces/{workspace_id}/ask/threads/{uuid4()}", headers=_auth()
            )
            renamed = await client.patch(
                f"/workspaces/{workspace_id}/ask/threads/{thread_id}",
                json={"title": "새 제목"},
                headers=_auth(),
            )
            deleted = await client.delete(
                f"/workspaces/{workspace_id}/ask/threads/{thread_id}",
                headers=_auth(),
            )
            empty_title = await client.patch(
                f"/workspaces/{workspace_id}/ask/threads/{thread_id}",
                json={"title": ""},
                headers=_auth(),
            )
        await app.state.http_client.aclose()

    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "첫 질문"
    assert missing.status_code == 403
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "새 제목"
    assert deleted.status_code == 200
    assert empty_title.status_code == 422


@pytest.mark.asyncio
async def test_retry_or_switch_sends_distinct_client_turn_id() -> None:
    ids: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/rpc/persist_ask_turn":
            body = json.loads(request.content.decode())
            ids.append(body["p_client_turn_id"])
            return _persist_ok()
        return httpx.Response(200, json=[])

    app = create_app(_settings(), git_sha="test-sha")
    fake_llm = _FakeLlmStream(_UpstreamResponse([]))
    async with app.router.lifespan_context(app):
        app.state.http_client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), timeout=httpx.Timeout(2.0)
        )
        app.state.ask_service = AskService(_EmptyRetrievalService(), fake_llm)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = str(uuid4())
            second = str(uuid4())
            workspace_id = uuid4()
            await client.post(
                _ASK_PATH.format(workspace_id=workspace_id),
                json=_ask_body(client_turn_id=first),
                headers=_auth(),
            )
            await client.post(
                _ASK_PATH.format(workspace_id=workspace_id),
                json=_ask_body(client_turn_id=second),
                headers=_auth(),
            )
        await app.state.http_client.aclose()

    assert ids == [first, second]
    assert first != second
