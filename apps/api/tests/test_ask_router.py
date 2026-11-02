"""05-01-PLAN.md Task 2 — Ask 라우트 회귀 (fully offline: ASGITransport + injected fakes).

`test_query_embedding.py`의 완전 오프라인 관례를 따른다 — 로컬 스택도 워커 프로세스도
필요하지 않는다. `RetrievalService`와 워커 스트림 클라이언트는 둘 다 페이크로 주입하고,
`prompt_templates`/`wiki_pages`/`source_chunks` 조회는 `httpx.MockTransport`로 가로챈다
(`AskService`가 실제로 쓰는 `UserDb._client`/`_base_url`/`_headers` seam이 그대로 돈다).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import httpx
import pytest
import structlog

from api.main import create_app
from api.routers.ask import _ask_service
from api.services import ask as ask_service_module
from api.services.ask import NO_EVIDENCE_MESSAGE, AskService, HttpAskTurnExporter
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
    upstream: _UpstreamResponse, retrieval_service: Any = None, fake_llm: Any = None
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
            retrieval_service or _NonEmptyRetrievalService(),
            fake_llm or _FakeLlmStream(upstream),
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "frame",
    [
        'data: {"choices":"문자열"}',
        'data: {"choices":["문자열"]}',
        'data: {"choices":[{"delta":"문자열"}]}',
        'data: {"choices":[{"delta":{"content":123}}]}',
        'data: {"choices":[{"delta":{"content":["목록"]}}]}',
        'data: {"choices":[{"delta":{"content":0}}]}',
        # 값이 falsy여도 틀린 형태다. 빈 값으로 취급하면 잘린 답변이 해결된 답변으로 저장된다.
        'data: {"choices":0}',
        'data: {"choices":""}',
        'data: {"choices":false}',
        'data: {"choices":{}}',
        'data: {"choices":[0]}',
        'data: {"choices":[{"delta":0}]}',
        'data: {"choices":[{"delta":""}]}',
        'data: {"choices":[{"delta":false}]}',
        'data: {"choices":[{"delta":[]}]}',
    ],
)
async def test_wrongly_shaped_frame_ends_turn_with_error(frame: str) -> None:
    # ⚠️ 파싱은 되지만 형태가 틀리면 예전에는 `join`의 TypeError로 턴이 `streaming`에 남았다.
    events, finalized = await _post_ask_capturing_finalize(
        _UpstreamResponse(['data: {"choices":[{"delta":{"content":"앞부분"}}]}', frame])
    )

    assert dict(events)["citations"]["error"] == "llm_unavailable"
    assert events[-1][0] == "done"
    assert finalized["p_status"] == "error"
    assert finalized["p_answer_text"] == ""


@pytest.mark.asyncio
async def test_null_delta_content_is_not_a_failure() -> None:
    # 공급자는 역할만 담은 첫 프레임이나 사용량 프레임에서 `content: null`을 보낸다.
    events, finalized = await _post_ask_capturing_finalize(
        _UpstreamResponse(
            [
                'data: {"choices":[{"delta":{"content":null}}]}',
                'data: {"choices":[{"delta":{"content":"답변 [[wiki:w1]] [[src:s1]]."}}]}',
                "data: [DONE]",
            ]
        )
    )

    assert "error" not in dict(events)["citations"]
    assert finalized["p_status"] == "resolved"


class _FailingRetrieval:
    async def retrieve(self, *args: object, **kwargs: object) -> RetrievalResult:
        raise RuntimeError("고유한-내부-오류-문자열")


@pytest.mark.asyncio
async def test_retrieval_failure_after_start_finalizes_as_error_without_a_route(
    caplog: pytest.LogCaptureFixture, capfd: pytest.CaptureFixture[str]
) -> None:
    fake_llm = _FakeLlmStream(_UpstreamResponse(["data: [DONE]"]))
    events, finalized = await _post_ask_capturing_finalize(
        _UpstreamResponse(["data: [DONE]"]), _FailingRetrieval(), fake_llm
    )

    assert [name for name, _ in events] == ["meta", "citations", "done"]
    assert dict(events)["citations"]["error"] == "retrieval_unavailable"
    assert finalized["p_status"] == "error"
    report = finalized["p_control_report"]
    # 검색 전에 실패했으므로 결정이 없다. 집계 RPC는 이런 행을 결정 분포에서 거른다.
    assert report["route"] is None
    assert report["outcome"] == "error"
    assert report["evidence"] == {"wiki": 0, "source": 0}
    assert fake_llm.calls == 0
    captured = capfd.readouterr()
    assert "고유한-내부-오류-문자열" not in captured.out + captured.err + caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failing_path",
    [
        "/rest/v1/wiki_pages",
        "/rest/v1/source_chunks",
        "/rest/v1/prompt_templates",
        "render",
    ],
)
async def test_context_failure_after_start_finalizes_as_error(failing_path: str) -> None:
    finalized: dict[str, Any] = {}
    base = _mock_prompt_and_content_transport()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == failing_path:
            return httpx.Response(500, json={"code": "XX000", "message": "boom"})
        if failing_path == "render" and request.url.path == "/rest/v1/prompt_templates":
            # 닫히지 않은 자리표시자라 `_render`가 `ValueError`를 던진다.
            return httpx.Response(
                200,
                json=[
                    {
                        "id": _TEMPLATE_ID,
                        "name": "깨진 템플릿",
                        "workspace_id": None,
                        "system_prompt": "s",
                        "template": "{{question",
                    }
                ],
            )
        if request.url.path == "/rest/v1/rpc/finalize_ask_turn":
            finalized.update(json.loads(request.content))
        return base.handler(request)

    fake_llm = _FakeLlmStream(_UpstreamResponse(["data: [DONE]"]))
    app = create_app(_settings(), git_sha="test-sha")
    async with app.router.lifespan_context(app):
        app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
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

    events = _parse_sse(response.text)
    assert dict(events)["citations"]["error"] == "context_unavailable"
    assert events[-1][0] == "done"
    assert finalized["p_status"] == "error"
    # 근거 조회는 끝났으므로 결정은 남는다. 프롬프트를 만들지 못해 공급자는 부르지 않는다.
    assert finalized["p_control_report"]["route"]["decision"] == "STANDARD"
    assert fake_llm.calls == 0


class _RecordingExporter:
    def __init__(self) -> None:
        self.turns: list[dict[str, Any]] = []

    def export(self, *, workspace_id: str, control_report: Any, persisted: bool) -> None:
        self.turns.append(
            {"workspace_id": workspace_id, "report": control_report, "persisted": persisted}
        )


@pytest.mark.asyncio
async def test_exporter_failure_cannot_reach_the_client_and_body_is_not_sent() -> None:
    posted: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        posted.append(request)
        raise httpx.ConnectError("worker down")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        exporter = HttpAskTurnExporter(client, url="http://worker:8081/", token="internal")  # noqa: S106
        with structlog.contextvars.bound_contextvars(trace_id="trace-1"):
            exporter.export(
                workspace_id="ws-1", control_report={"outcome": "resolved"}, persisted=True
            )
        await asyncio.gather(*ask_service_module._pending_turn_exports)

    assert str(posted[0].url) == "http://worker:8081/internal/ask-turn-export"
    assert posted[0].headers["authorization"] == "Bearer internal"
    assert posted[0].headers["x-trace-id"] == "trace-1"
    assert json.loads(posted[0].content) == {
        "workspace_id": "ws-1",
        "control_report": {"outcome": "resolved"},
        "persisted": True,
    }


def test_exporter_without_worker_address_does_nothing() -> None:
    # 내부 주소가 없는 로컬 환경에서 답변이 실패하면 안 된다. 태스크도 만들지 않는다.
    client = httpx.AsyncClient()
    HttpAskTurnExporter(client, url=None, token=None).export(  # noqa: S106
        workspace_id="ws-1", control_report={}, persisted=True
    )
    assert not ask_service_module._pending_turn_exports


@pytest.mark.asyncio
async def test_terminal_turn_is_handed_to_the_exporter_once() -> None:
    exporter = _RecordingExporter()
    base = _mock_prompt_and_content_transport()
    app = create_app(_settings(), git_sha="test-sha")
    async with app.router.lifespan_context(app):
        app.state.http_client = httpx.AsyncClient(transport=base)
        app.state.ask_service = AskService(
            _NonEmptyRetrievalService(),
            _FakeLlmStream(_UpstreamResponse(["data: [DONE]"])),
            exporter,
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.post(
                _ASK_PATH.format(workspace_id=uuid4()),
                json=_ask_body(requested_k=8),
                headers={"Authorization": "Bearer test-token"},
            )
        await app.state.http_client.aclose()

    assert len(exporter.turns) == 1
    assert exporter.turns[0]["persisted"] is True


@pytest.mark.asyncio
async def test_default_assembly_sends_terminal_turns_to_the_worker_route() -> None:
    # ⚠️ 다른 테스트는 `ask_service`를 주입해 실제 조립을 지나지 않는다. 여기서 빠지면 내보내기가
    #    오류 없이 사라진다.
    posted: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        posted.append(request)
        return httpx.Response(204)

    settings = _settings().model_copy(
        update={
            "LLM_STREAM_INTERNAL_URL": "http://worker:8081",
            "LLM_STREAM_INTERNAL_TOKEN": "internal",
        }
    )
    state = SimpleNamespace(
        settings=settings, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    service = _ask_service(SimpleNamespace(app=SimpleNamespace(state=state)))  # type: ignore[arg-type]

    service._export_turn(workspace_id=uuid4(), control_report={}, persisted=True)
    await asyncio.gather(*ask_service_module._pending_turn_exports)
    await state.http_client.aclose()

    assert [str(request.url) for request in posted] == [
        "http://worker:8081/internal/ask-turn-export"
    ]
    assert posted[0].headers["authorization"] == "Bearer internal"


@pytest.mark.asyncio
async def test_transport_failure_while_finalizing_does_not_escape_the_stream() -> None:
    # ⚠️ 빠져나가면 ASGI 스트림이 예외로 끊기고 내보내기도 남지 않는다.
    exporter = _RecordingExporter()
    base = _mock_prompt_and_content_transport()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/rpc/finalize_ask_turn":
            raise httpx.ReadTimeout("slow", request=request)
        return base.handler(request)

    app = create_app(_settings(), git_sha="test-sha")
    async with app.router.lifespan_context(app):
        app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        app.state.ask_service = AskService(
            _NonEmptyRetrievalService(),
            _FakeLlmStream(_UpstreamResponse(["data: [DONE]"])),
            exporter,
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

    # `done`은 저장에 성공했을 때만 보낸다. 저장 실패는 사본에 표시된다.
    assert "done" not in [name for name, _ in _parse_sse(response.text)]
    assert [turn["persisted"] for turn in exporter.turns] == [False]


@pytest.mark.asyncio
async def test_preparation_failure_log_keeps_its_classification(
    capfd: pytest.CaptureFixture[str],
) -> None:
    # `token` 키는 마스킹 대상이라 분류가 지워졌었다. 마스킹 처리기를 거친 실제 출력으로 확인한다.
    await _post_ask_capturing_finalize(_UpstreamResponse(["data: [DONE]"]), _FailingRetrieval())

    line = next(
        line for line in capfd.readouterr().out.splitlines() if "ask.preparation_failed" in line
    )
    assert "retrieval_unavailable" in line
    assert "[REDACTED]" not in line
    # 분류되지 않은 예외는 코드 결함이므로 오류 수준이다.
    assert "error" in line.split("ask.preparation_failed")[0]


@pytest.mark.asyncio
async def test_non_http_exporter_failure_stays_inside_the_task() -> None:
    # 닫힌 클라이언트처럼 `httpx.HTTPError`가 아닌 실패도 태스크 밖으로 나가면 안 된다.
    client = httpx.AsyncClient()
    await client.aclose()
    HttpAskTurnExporter(client, url="http://worker", token="internal").export(  # noqa: S106
        workspace_id="ws-1", control_report={}, persisted=True
    )
    await ask_service_module.drain_turn_exports(timeout_seconds=1.0)

    assert not ask_service_module._pending_turn_exports


@pytest.mark.asyncio
async def test_ask_context_budget_preserves_dual_evidence_and_records_budget_report() -> None:
    wiki_2 = str(uuid4())
    wiki_3 = str(uuid4())
    finalized: dict[str, Any] = {}
    base = _mock_prompt_and_content_transport()

    class _HeavyRetrieval:
        async def retrieve(self, *_: object) -> RetrievalResult:
            return RetrievalResult(
                evidence=[
                    EvidenceHit.wiki(wiki_id=_WIKI_ID, rank=1, metadata={"title": "위키 1"}),
                    EvidenceHit.wiki(wiki_id=wiki_2, rank=2, metadata={"title": "위키 2"}),
                    EvidenceHit.wiki(wiki_id=wiki_3, rank=3, metadata={"title": "위키 3"}),
                    EvidenceHit.source(
                        chunk_id=_SOURCE_CHUNK_ID,
                        rank=4,
                        metadata={"raw_source_id": _RAW_SOURCE_ID, "chunk_index": 0},
                    ),
                ],
                meta={"policy_version": "test-v1"},
            )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/wiki_pages":
            long_wiki = "위키 상세 설명 문장입니다. " * 120
            return httpx.Response(
                200,
                json=[
                    {"id": _WIKI_ID, "slug": "wiki-1", "title": "위키 1", "content": long_wiki},
                    {"id": wiki_2, "slug": "wiki-2", "title": "위키 2", "content": long_wiki},
                    {"id": wiki_3, "slug": "wiki-3", "title": "위키 3", "content": long_wiki},
                ],
            )
        if request.url.path == "/rest/v1/source_chunks":
            return httpx.Response(
                200,
                json=[{"id": _SOURCE_CHUNK_ID, "content": "원문 핵심 근거 문장입니다. " * 60}],
            )
        if request.url.path == "/rest/v1/rpc/finalize_ask_turn":
            finalized.update(json.loads(request.content))
        return base.handler(request)

    fake_llm = _FakeLlmStream(
        _UpstreamResponse(
            [
                (
                    'data: {"choices":[{"delta":{"content":'
                    '"결론 [[wiki:w1]] [[src:s1]] [[wiki:w2]]."}}]}'
                ),
                "data: [DONE]",
            ]
        )
    )
    app = create_app(_settings(), git_sha="test-sha")
    async with app.router.lifespan_context(app):
        app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        app.state.ask_service = AskService(
            _HeavyRetrieval(),  # type: ignore[arg-type]
            fake_llm,
            max_context_tokens=180,
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
    prompt_body = fake_llm.messages[1]["content"]
    assert "[[wiki:w1]]" in prompt_body
    assert "[[src:s1]]" in prompt_body
    assert "[[wiki:w2]]" not in prompt_body

    events = dict(_parse_sse(response.text))
    # 예산 초과로 제외된 w2는 발급되지 않았으므로 조작/미발급 앵커로 제거된다.
    assert "[[wiki:w2]]" not in events["citations"]["text"]
    assert events["citations"]["dual_citation_rate"] == 1.0

    budget_report = finalized["p_control_report"]["budget"]
    assert budget_report["max_context_tokens"] == 180
    assert budget_report["estimated_context_tokens"] <= 180
    assert budget_report["truncated"] is True
    assert budget_report["dual_evidence_preserved"] is True
    assert budget_report["dropped_blocks"] == 2
    assert budget_report["wiki_blocks"] == 1
    assert budget_report["source_blocks"] == 1
