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
_PERSISTED_THREAD_ID = str(uuid4())
_ASK_PATH = "/workspaces/{workspace_id}/ask"


def _ask_body(**extra: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"query": "질문", "client_turn_id": str(uuid4())}
    body.update(extra)
    return body


def _persist_ok() -> httpx.Response:
    return httpx.Response(
        200,
        json=[{"thread_id": _PERSISTED_THREAD_ID, "message_id": str(uuid4())}],
    )


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
        self.messages: list[dict[str, str]] = []

    def stream(self, *, workspace_id: str, messages: list[dict[str, str]]) -> _FakeLlmStream:
        self.calls += 1
        assert workspace_id
        assert messages
        self.messages = messages
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
        if path in {
            "/rest/v1/rpc/start_ask_turn",
            "/rest/v1/rpc/finalize_ask_turn",
        }:
            return _persist_ok()
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
        app.state.http_client = httpx.AsyncClient(
            transport=_mock_prompt_and_content_transport(), timeout=httpx.Timeout(2.0)
        )
        app.state.ask_service = AskService(_EmptyRetrievalService(), fake_llm)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                _ASK_PATH.format(workspace_id=uuid4()),
                json=_ask_body(requested_k=8),
                headers={"Authorization": "Bearer test-token"},
            )
        await app.state.http_client.aclose()

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
                json=_ask_body(requested_k=8),
                headers={"Authorization": "Bearer test-token"},
            )
        await app.state.http_client.aclose()

    assert response.status_code == 200
    events = _parse_sse(response.text)
    names = [name for name, _ in events]
    assert names[0] == "meta"
    assert names[-2:] == ["citations", "done"]
    assert events[-1][1]["thread_id"] == _PERSISTED_THREAD_ID
    assert names.count("delta") == 2

    citations_payload = dict(events)["citations"]
    assert citations_payload["resolved"] == [{"alias": "w1", "kind": "wiki", "id": _WIKI_ID}]
    assert citations_payload["fabricated_anchor_count"] == 1
    assert citations_payload["cited_anchor_count"] == 1
    assert "[[wiki:w99]]" not in citations_payload["text"]
    assert "[[wiki:w1]]" in citations_payload["text"]
    assert fake_llm.calls == 1


async def _post_ask_capturing_finalize(
    upstream: _UpstreamResponse, retrieval_service: Any = None
) -> tuple[list[tuple[str, dict[str, Any]]], dict[str, Any]]:
    """Ask를 끝까지 돌리고 SSE 이벤트와 `finalize_ask_turn`에 실린 값을 돌려준다."""
    finalized: dict[str, Any] = {}
    base = _mock_prompt_and_content_transport()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/rpc/finalize_ask_turn":
            finalized.update(json.loads(request.content))
        return base.handler(request)

    app = create_app(_settings(), git_sha="test-sha")
    async with app.router.lifespan_context(app):
        app.state.http_client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), timeout=httpx.Timeout(2.0)
        )
        app.state.ask_service = AskService(
            retrieval_service or _NonEmptyRetrievalService(), _FakeLlmStream(upstream)
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                _ASK_PATH.format(workspace_id=uuid4()),
                json=_ask_body(requested_k=8),
                headers={"Authorization": "Bearer test-token"},
            )
        await app.state.http_client.aclose()
    assert response.status_code == 200
    return _parse_sse(response.text), finalized


@pytest.mark.asyncio
async def test_control_report_is_saved_without_any_body() -> None:
    _, finalized = await _post_ask_capturing_finalize(
        _UpstreamResponse(
            [
                'data: {"choices":[{"delta":{"content":"고유한-답변-문자열 [[wiki:w1]] '
                '[[src:s1]]."}}]}',
                "data: [DONE]",
            ]
        )
    )

    report = finalized["p_control_report"]
    assert report["outcome"] == "resolved"
    assert report["route"] == {"decision": "STANDARD", "reason": "default"}
    assert report["evidence"] == {"wiki": 1, "source": 1}
    assert report["citation"]["dual_citation_rate"] == 1.0
    assert [span["name"] for span in report["spans"]] == [
        "retrieval",
        "context",
        "llm_stream",
        "citation",
    ]
    assert all(span["duration_ms"] >= 0 for span in report["spans"])
    serialized = json.dumps(report, ensure_ascii=False)
    for forbidden in ("고유한-답변-문자열", "위키 본문", "원문 본문", "질문", _WIKI_ID):
        assert forbidden not in serialized


@pytest.mark.asyncio
async def test_lookup_decision_is_recorded_but_the_llm_still_runs() -> None:
    class ExactTitleRetrieval:
        async def retrieve(self, *_: object) -> RetrievalResult:
            return RetrievalResult(
                evidence=[
                    EvidenceHit.wiki(wiki_id=_WIKI_ID, rank=1, metadata={"title": "질문"}),
                    EvidenceHit.source(chunk_id=_SOURCE_CHUNK_ID, rank=1),
                ],
                meta={"policy_version": "test-v1"},
            )

    upstream = _UpstreamResponse(
        ['data: {"choices":[{"delta":{"content":"답변"}}]}', "data: [DONE]"]
    )
    events, finalized = await _post_ask_capturing_finalize(upstream, ExactTitleRetrieval())

    assert finalized["p_control_report"]["route"]["decision"] == "LOOKUP"
    assert "delta" in [name for name, _ in events]
    assert finalized["p_status"] == "resolved"


@pytest.mark.asyncio
async def test_no_evidence_report_and_error_report_are_saved() -> None:
    _, no_evidence = await _post_ask_capturing_finalize(
        _UpstreamResponse([]), _EmptyRetrievalService()
    )
    _, failed = await _post_ask_capturing_finalize(_UpstreamResponse(["data: {broken"]))

    assert no_evidence["p_control_report"]["route"]["decision"] == "NO_EVIDENCE"
    assert no_evidence["p_control_report"]["outcome"] == "no-evidence"
    assert failed["p_control_report"]["outcome"] == "error"


@pytest.mark.asyncio
async def test_replayed_turn_keeps_the_original_trace_in_the_response() -> None:
    original_trace = str(uuid4())
    base = _mock_prompt_and_content_transport()
    started: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/rpc/start_ask_turn":
            started.update(json.loads(request.content))
            return httpx.Response(
                200,
                json=[
                    {
                        "thread_id": _PERSISTED_THREAD_ID,
                        "message_id": str(uuid4()),
                        "trace_id": original_trace,
                    }
                ],
            )
        return base.handler(request)

    app = create_app(_settings(), git_sha="test-sha")
    async with app.router.lifespan_context(app):
        app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        app.state.ask_service = AskService(
            _EmptyRetrievalService(), _FakeLlmStream(_UpstreamResponse([]))
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                _ASK_PATH.format(workspace_id=uuid4()),
                json=_ask_body(),
                headers={"Authorization": "Bearer test-token"},
            )
        await app.state.http_client.aclose()

    assert started["p_trace_id"] != original_trace
    assert response.headers["x-trace-id"] == original_trace


@pytest.mark.asyncio
async def test_malformed_stream_frame_ends_turn_with_error() -> None:
    events, finalized = await _post_ask_capturing_finalize(
        _UpstreamResponse(
            [
                'data: {"choices":[{"delta":{"content":"앞부분"}}]}',
                "data: {broken",
            ]
        )
    )

    names = [name for name, _ in events]
    assert names == ["meta", "delta", "citations", "done"]
    assert dict(events)["citations"]["error"] == "llm_unavailable"
    assert finalized["p_status"] == "error"
    assert finalized["p_answer_text"] == ""


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_frame",
    [
        'data: {"error":{"code":502,"message":"공급자 오류"},'
        '"choices":[{"delta":{"content":""},"finish_reason":"error"}]}',
        'data: {"choices":[{"delta":{"content":""},"finish_reason":"error"}]}',
        'data: {"error":{"code":429,"message":"한도 초과"}}',
    ],
)
async def test_provider_error_frame_does_not_store_partial_answer(error_frame: str) -> None:
    events, finalized = await _post_ask_capturing_finalize(
        _UpstreamResponse(['data: {"choices":[{"delta":{"content":"앞부분"}}]}', error_frame])
    )

    assert [name for name, _ in events] == ["meta", "delta", "citations", "done"]
    citations = dict(events)["citations"]
    assert citations["error"] == "llm_unavailable"
    assert "공급자 오류" not in json.dumps(citations, ensure_ascii=False)
    assert finalized["p_status"] == "error"
    assert finalized["p_answer_text"] == ""


class _RetrievalWithChannelMeta:
    def __init__(self, evidence: list[EvidenceHit]) -> None:
        self._evidence = evidence

    async def retrieve(
        self, workspace_id: object, query: str, requested_k: int, user_db: object
    ) -> RetrievalResult:
        return RetrievalResult(
            evidence=self._evidence,
            meta={
                "policy_version": "test-v1",
                "returned": len(self._evidence),
                "wiki_vector": {"status": "failed", "error_code": "embedding_unavailable"},
                "source_vector": {"status": "ok"},
                "wiki_lexical": {"status": "ok"},
                "source_lexical": {"status": "failed", "error_code": "rpc_unavailable"},
                "graph": {"status": "disabled"},
            },
        )


@pytest.mark.asyncio
async def test_meta_reports_only_failed_channels_and_not_disabled_graph() -> None:
    evidence = [EvidenceHit.source(chunk_id=_SOURCE_CHUNK_ID, rank=1)]
    events, _ = await _post_ask_capturing_finalize(
        _UpstreamResponse(["data: [DONE]"]), _RetrievalWithChannelMeta(evidence)
    )

    assert dict(events)["meta"]["missing_channels"] == ["source_lexical", "wiki_vector"]


@pytest.mark.asyncio
async def test_no_evidence_meta_also_reports_failed_channels() -> None:
    events, _ = await _post_ask_capturing_finalize(
        _UpstreamResponse([]), _RetrievalWithChannelMeta([])
    )

    meta = dict(events)["meta"]
    assert meta["no_evidence"] is True
    assert meta["missing_channels"] == ["source_lexical", "wiki_vector"]


@pytest.mark.asyncio
async def test_healthy_channels_report_no_missing_channels() -> None:
    events, _ = await _post_ask_capturing_finalize(_UpstreamResponse(["data: [DONE]"]))

    assert dict(events)["meta"]["missing_channels"] == []


@pytest.mark.asyncio
async def test_visible_requested_template_is_used_for_ask() -> None:
    selected_template_id = str(uuid4())
    app = create_app(_settings(), git_sha="test-sha")
    fake_llm = _FakeLlmStream(_UpstreamResponse(["data: [DONE]"]))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/wiki_pages":
            return httpx.Response(200, json=[{"id": _WIKI_ID, "content": "위키 본문"}])
        if request.url.path == "/rest/v1/source_chunks":
            return httpx.Response(200, json=[{"id": _SOURCE_CHUNK_ID, "content": "원문 본문"}])
        if request.url.path == "/rest/v1/prompt_templates":
            assert request.url.params["id"] == f"eq.{selected_template_id}"
            assert request.url.params["target_type"] == "eq.ask"
            return httpx.Response(
                200,
                json=[
                    {
                        "id": selected_template_id,
                        "name": "경영진 요약",
                        "workspace_id": None,
                        "system_prompt": "선택된 시스템 프롬프트",
                        "template": "{{question}} {{wiki_context}} {{source_context}}",
                    }
                ],
            )
        if request.url.path in {
            "/rest/v1/rpc/start_ask_turn",
            "/rest/v1/rpc/finalize_ask_turn",
        }:
            return _persist_ok()
        raise AssertionError(f"unexpected request: {request.url}")

    async with app.router.lifespan_context(app):
        app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        app.state.ask_service = AskService(_NonEmptyRetrievalService(), fake_llm)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                _ASK_PATH.format(workspace_id=uuid4()),
                json=_ask_body(template_id=selected_template_id),
                headers={"Authorization": "Bearer test-token"},
            )
        await app.state.http_client.aclose()

    assert response.status_code == 200
    assert dict(_parse_sse(response.text))["meta"]["template_id"] == selected_template_id
    assert fake_llm.messages[0]["content"] == "선택된 시스템 프롬프트"


@pytest.mark.asyncio
async def test_invisible_requested_template_falls_back_to_default() -> None:
    selected_template_id = str(uuid4())
    app = create_app(_settings(), git_sha="test-sha")
    fake_llm = _FakeLlmStream(_UpstreamResponse(["data: [DONE]"]))

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
                json=_ask_body(template_id=selected_template_id),
                headers={"Authorization": "Bearer test-token"},
            )
        await app.state.http_client.aclose()

    assert response.status_code == 200
    assert dict(_parse_sse(response.text))["meta"]["template_id"] == _TEMPLATE_ID
