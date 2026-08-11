"""05-01-PLAN.md Task 2 — Ask 라우트 회귀 (fully offline: ASGITransport + injected fakes).

`test_query_embedding.py`의 완전 오프라인 관례를 따른다 — 로컬 스택도 워커 프로세스도
필요하지 않는다. `RetrievalService`와 워커 스트림 클라이언트는 둘 다 페이크로 주입하고,
`prompt_templates`/`wiki_pages`/`source_chunks` 조회는 `httpx.MockTransport`로 가로챈다
(`AskService`가 실제로 쓰는 `UserDb._client`/`_base_url`/`_headers` seam이 그대로 돈다).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import httpx
import pytest

from api.main import create_app
from api.services.ask import NO_EVIDENCE_MESSAGE, AskService
from api.services.retrieval import RetrievalResult
from api.settings import ApiSettings
from nexuswiki_core.rrf import EvidenceHit

_WIKI_ID = str(uuid4())
_SOURCE_CHUNK_ID = str(uuid4())
_RAW_SOURCE_ID = str(uuid4())
_TEMPLATE_ID = str(uuid4())
_ASK_PATH = "/workspaces/{workspace_id}/ask"


def _settings() -> ApiSettings:
    return ApiSettings(
        SUPABASE_URL="https://example.invalid",
        SUPABASE_PUBLISHABLE_KEY="sb_publishable_test",
    )


class _EmptyRetrievalService:
    async def retrieve(
        self, workspace_id: object, query: str, requested_k: int, user_db: object
    ) -> RetrievalResult:
        return RetrievalResult(evidence=[], meta={"policy_version": "test-v1"})


class _NonEmptyRetrievalService:
    async def retrieve(
        self, workspace_id: object, query: str, requested_k: int, user_db: object
    ) -> RetrievalResult:
        evidence = [
            EvidenceHit.wiki(wiki_id=_WIKI_ID, rank=1, metadata={"title": "테스트 위키"}),
            EvidenceHit.source(
                chunk_id=_SOURCE_CHUNK_ID,
                rank=1,
                metadata={"raw_source_id": _RAW_SOURCE_ID, "chunk_index": 0},
            ),
        ]
        return RetrievalResult(evidence=evidence, meta={"policy_version": "test-v1"})


class _UpstreamResponse:
    def __init__(self, lines: list[str], *, status_code: int = 200) -> None:
        self.status_code = status_code
        self._lines = lines

    async def aiter_lines(self) -> AsyncIterator[str]:
        for line in self._lines:
            yield line


class _FakeLlmStream:
    """`AskService`가 기대하는 `LlmStreamClient` Protocol을 만족하는 페이크."""

    def __init__(self, upstream: _UpstreamResponse) -> None:
        self._upstream = upstream
        self.calls = 0

    def stream(self, *, workspace_id: str, messages: list[dict[str, str]]) -> _FakeLlmStream:
        self.calls += 1
        assert workspace_id
        assert messages
        return self

    async def __aenter__(self) -> _UpstreamResponse:
        return self._upstream

    async def __aexit__(self, *exc: object) -> None:
        return None


def _mock_prompt_and_content_transport() -> httpx.MockTransport:
    def _handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/rest/v1/wiki_pages":
            return httpx.Response(200, json=[{"id": _WIKI_ID, "content": "위키 본문"}])
        if path == "/rest/v1/source_chunks":
            return httpx.Response(200, json=[{"id": _SOURCE_CHUNK_ID, "content": "원문 본문"}])
        if path == "/rest/v1/prompt_templates":
            if "workspace_id" in request.url.params:
                # 1차: 워크스페이스 기본 조회 — 없음
                return httpx.Response(200, json=[])
            # 2차: 전역 기본 조회
            return httpx.Response(
                200,
                json=[
                    {
                        "id": _TEMPLATE_ID,
                        "name": "기술 심층 분석",
                        "workspace_id": None,
                        "system_prompt": "당신은 분석가입니다.",
                        "template": (
                            "## 질문\n\n{{question}}\n\n"
                            "## 위키\n\n{{wiki_context}}\n\n"
                            "## 원문\n\n{{source_context}}"
                        ),
                    }
                ],
            )
        raise AssertionError(f"unexpected request: {request.url}")

    return httpx.MockTransport(_handler)


def _parse_sse(text: str) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    for block in text.strip("\n").split("\n\n"):
        if not block:
            continue
        name: str | None = None
        data: str | None = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line[len("event: ") :]
            elif line.startswith("data: "):
                data = line[len("data: ") :]
        if name is not None and data is not None:
            events.append((name, json.loads(data)))
    return events


@pytest.mark.asyncio
async def test_no_evidence_short_circuits_before_any_llm_call() -> None:
    app = create_app(_settings(), git_sha="test-sha")
    fake_llm = _FakeLlmStream(_UpstreamResponse([]))
    async with app.router.lifespan_context(app):
        app.state.ask_service = AskService(_EmptyRetrievalService(), fake_llm)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                _ASK_PATH.format(workspace_id=uuid4()),
                json={"query": "질문", "requested_k": 8},
                headers={"Authorization": "Bearer test-token"},
            )

    assert response.status_code == 200
    events = _parse_sse(response.text)
    names = [name for name, _ in events]
    assert names == ["meta", "citations", "done"]
    citations_payload = events[1][1]
    assert citations_payload["text"] == NO_EVIDENCE_MESSAGE
    assert citations_payload["cited_anchor_count"] == 0
    assert fake_llm.calls == 0


@pytest.mark.asyncio
async def test_grounded_answer_streams_meta_delta_citations_done_with_fabrication_stripped() -> (
    None
):
    app = create_app(_settings(), git_sha="test-sha")
    upstream = _UpstreamResponse(
        [
            'data: {"choices":[{"delta":{"content":"결론입니다 [[wiki:w1]] 그리고 "}}]}',
            'data: {"choices":[{"delta":{"content":"[[wiki:w99]] 입니다."}}]}',
            "data: [DONE]",
        ]
    )
    fake_llm = _FakeLlmStream(upstream)
    async with app.router.lifespan_context(app):
        app.state.http_client = httpx.AsyncClient(
            transport=_mock_prompt_and_content_transport(), timeout=httpx.Timeout(2.0)
        )
        app.state.ask_service = AskService(_NonEmptyRetrievalService(), fake_llm)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                _ASK_PATH.format(workspace_id=uuid4()),
                json={"query": "질문", "requested_k": 8},
                headers={"Authorization": "Bearer test-token"},
            )
        await app.state.http_client.aclose()

    assert response.status_code == 200
    events = _parse_sse(response.text)
    names = [name for name, _ in events]
    assert names[0] == "meta"
    assert names[-2:] == ["citations", "done"]
    assert names.count("delta") == 2

    citations_payload = dict(events)["citations"]
    assert citations_payload["resolved"] == [{"alias": "w1", "kind": "wiki", "id": _WIKI_ID}]
    assert citations_payload["fabricated_anchor_count"] == 1
    assert citations_payload["cited_anchor_count"] == 1
    assert "[[wiki:w99]]" not in citations_payload["text"]
    assert "[[wiki:w1]]" in citations_payload["text"]
    assert fake_llm.calls == 1
