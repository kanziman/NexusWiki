"""고유 문자열이 전체 경로를 지나도 관측 값에 나타나지 않음을 실제 스택과 SDK로 고정한다 (#167).

⚠️ 어댑터 단위 테스트는 "넘겨받은 값을 거른다"만 보장한다. 호출 지점이 본문을 어떤 이름으로든
메타데이터에 실으면 그 테스트로는 잡히지 않아서, 수집과 Ask를 끝까지 돌린 뒤 외부로 나갈 값과
저장된 관측 값 전부를 문자열로 검사한다.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import httpx
import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from api import main as api_main
from api.services.ask import AskService
from api.services.retrieval import RetrievalService
from nexuswiki_core import observability
from nexuswiki_core.trace import bind_trace, new_trace_id
from tests.conftest import LOCAL_STACK
from tests.fixtures.pipeline import PipelineHarness

# ASCII만 쓴다. 한글은 JSON 직렬화나 콘솔 인코딩에서 형태가 바뀌어 부재 단언을 그냥 통과한다.
_UNIQUE = "zq81xLeakProbe"
_SECRET = "sk-lf-zq81x-leak-probe"  # noqa: S105 - 테스트 픽스처


class _QueryEmbedding:
    async def embed(self, _text: str, *, workspace_id: str) -> list[float]:
        return [0.0] * 1024


class _Upstream:
    status_code = 200

    async def aiter_lines(self) -> AsyncIterator[str]:
        frame = {"choices": [{"delta": {"content": f"{_UNIQUE} 답변입니다."}}]}
        yield f"data: {json.dumps(frame, ensure_ascii=False)}"
        yield "data: [DONE]"


class _LlmStream:
    def stream(self, *, workspace_id: str, messages: list[dict[str, str]]) -> _LlmStream:
        assert _UNIQUE in json.dumps(messages, ensure_ascii=False)
        return self

    async def __aenter__(self) -> _Upstream:
        return _Upstream()

    async def __aexit__(self, *exc: object) -> None:
        return None


def _rows(
    local_stack: httpx.Client, table: str, *, token: str, apikey: str, **params: str
) -> list[dict[str, Any]]:
    response = local_stack.get(
        f"/rest/v1/{table}",
        params=params,
        headers={"apikey": apikey, "Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    return response.json()


@pytest.mark.asyncio
async def test_unique_text_never_reaches_any_observability_value(
    two_workspaces_two_users,
    local_stack,
    authed_client,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    owner, _ = two_workspaces_two_users
    workspace_id = str(owner.workspace_id)
    memory = InMemorySpanExporter()

    # 앱 수명 주기가 테스트 중간에 내보내기를 끄거나 종료하지 않게 한 번만 켠다.
    monkeypatch.setattr(api_main, "configure_observability", lambda **kwargs: False)
    monkeypatch.setattr(api_main, "flush_observability", lambda: True)
    assert observability.configure_observability(
        public_key=f"pk-lf-{uuid4()}",
        secret_key=_SECRET,
        base_url="http://127.0.0.1:9",
        environment="test",
        span_exporter=memory,
    )
    client = observability._client
    assert client is not None

    try:
        async with PipelineHarness(local_stack, authed_client, owner) as pipeline:
            await pipeline.create_text(f"{_UNIQUE} 제목", f"{_UNIQUE} 본문입니다. " * 20)
            # 하네스는 워커 핸들러를 직접 돌려 큐가 묶어 주는 trace가 없다. API 요청이 끝날 때
            # 미들웨어가 값을 지우므로 요청 뒤에 묶는다.
            bind_trace(new_trace_id())
            await pipeline.drain()

            async with authed_client(owner) as api:
                api._transport.app.state.ask_service = AskService(  # type: ignore[attr-defined]
                    RetrievalService(_QueryEmbedding()), _LlmStream()
                )
                response = await api.post(
                    f"/workspaces/{workspace_id}/ask",
                    json={"query": f"{_UNIQUE} 파이프라인", "client_turn_id": str(uuid4())},
                )
            assert response.status_code == 200, response.text
            assert '"thread_id"' in response.text
            assert _UNIQUE in response.text

        client.flush()
    finally:
        observability.flush_observability()

    spans = memory.get_finished_spans()
    names = {span.name for span in spans}
    # 아래 부재 단언이 빈 값에 대한 통과가 되지 않도록 실제로 내보냈음을 먼저 확인한다.
    assert {"compile", "embed_source", "embed_wiki", "ask.turn"} <= names, names

    exported = json.dumps(
        [{"name": span.name, "attributes": dict(span.attributes or {})} for span in spans],
        ensure_ascii=False,
        default=str,
    )
    usage = _rows(
        local_stack,
        "usage_events",
        token=LOCAL_STACK["admin_key"],
        apikey=LOCAL_STACK["admin_key"],
        workspace_id=f"eq.{workspace_id}",
        select="*",
    )
    # `service_role`에는 `ask_messages` 조회 권한이 없다. 작성자 본인의 JWT로 읽는다.
    reports = _rows(
        local_stack,
        "ask_messages",
        token=owner.access_token,
        apikey=LOCAL_STACK["publishable_key"],
        workspace_id=f"eq.{workspace_id}",
        select="trace_id,control_report",
    )
    assert usage
    assert reports and reports[0]["control_report"]
    captured = capfd.readouterr()

    for label, value in {
        "exported": exported,
        "usage_events": json.dumps(usage, ensure_ascii=False),
        "control_report": json.dumps(reports, ensure_ascii=False),
        "logs": captured.out + captured.err,
    }.items():
        assert _UNIQUE not in value, label
        assert _SECRET not in value, label
    # 워크스페이스는 해시로만 나간다.
    assert workspace_id not in exported
