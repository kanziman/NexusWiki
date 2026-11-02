"""외부 관측 어댑터 회귀 테스트 (#167).

`langfuse`를 페이크로 바꾸지 않고 실제 SDK에 메모리 내보내기를 연결한다. 본문 금지의 판정 대상은
어댑터에 넘긴 인자가 아니라 SDK가 전송 직전에 만든 값이기 때문이다.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import threading
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
import structlog
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from structlog.testing import capture_logs

from nexuswiki_core import observability
from nexuswiki_core.trace import bind_trace

_TRACE_ID = "7f3a19c2-1111-4222-8333-444455556666"
_WORKSPACE_ID = "11111111-2222-4333-8444-555555555555"
_SECRET = "sk-lf-unique-secret-zq81x"  # noqa: S105 - 테스트 픽스처
# ASCII만 쓴다. 한글은 JSON 직렬화에서 XXXX로 바뀌어 유출되어도 부재 단언을 통과한다.
_BODY = "unique-body-zq81x"


def _generation(**overrides: Any) -> dict[str, Any]:
    return {
        "name": "compile",
        "as_type": "generation",
        "workspace_id": _WORKSPACE_ID,
        "model": "test-model",
        "provider": "test-provider",
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
        "cost_micros": 2_500,
        "duration_ms": 120,
        "metadata": {"call": "compile", "attempt": 1},
        **overrides,
    }


def _exported(memory: InMemorySpanExporter) -> list[dict[str, Any]]:
    client = observability._client
    assert client is not None
    client.flush()
    return [
        {
            "name": span.name,
            "trace_id": format(span.context.trace_id, "032x"),
            "attributes": dict(span.attributes or {}),
        }
        for span in memory.get_finished_spans()
    ]


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(observability, "_client", None)
    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()


@pytest.fixture
def memory() -> Iterator[InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    enabled = observability.configure_observability(
        # SDK가 공개 키별로 자원을 재사용하므로 테스트마다 다른 값을 쓴다.
        public_key=f"pk-lf-{uuid4()}",
        secret_key=_SECRET,
        base_url="http://127.0.0.1:9",
        environment="test",
        span_exporter=exporter,
    )
    assert enabled is True
    bind_trace(_TRACE_ID)
    yield exporter
    observability.flush_observability()


def test_import_does_not_load_the_sdk() -> None:
    # ⚠️ import에 부작용을 두지 않는 규칙이다. 키 없는 프로세스에 전송 스레드가 생기면 안 된다.
    code = "import sys, nexuswiki_core.observability; print('langfuse' in sys.modules)"
    result = subprocess.run(  # noqa: S603 - 고정된 인자로 현재 인터프리터를 실행한다
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "False"


def test_no_credentials_leaves_export_disabled_and_harmless() -> None:
    enabled = observability.configure_observability(
        public_key=None, secret_key=None, base_url=None, environment="test"
    )
    bind_trace(_TRACE_ID)

    assert enabled is False
    observability.export_generation(**_generation())
    observability.export_job_outcome(
        workspace_id=_WORKSPACE_ID,
        job_type="parse",
        outcome="succeeded",
        duration_ms=1.0,
        attempts=1,
    )
    assert observability.flush_observability() is True


@pytest.mark.parametrize(("public_key", "secret_key"), [("pk-lf-only", None), (None, "sk-lf-only")])
def test_partial_credentials_stay_disabled_with_a_warning(
    public_key: str | None, secret_key: str | None
) -> None:
    with capture_logs() as logs:
        enabled = observability.configure_observability(
            public_key=public_key, secret_key=secret_key, base_url=None, environment="test"
        )

    assert enabled is False
    assert logs[0]["log_level"] == "warning"
    assert logs[0]["reason"] == "partial_credentials"
    assert "sk-lf-only" not in json.dumps(logs)


def test_sdk_constructor_failure_does_not_stop_the_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import langfuse

    def explode(**_: Any) -> None:
        raise RuntimeError(f"초기화 실패 {_SECRET}")

    monkeypatch.setattr(langfuse, "Langfuse", explode)

    with capture_logs() as logs:
        enabled = observability.configure_observability(
            public_key="pk-lf-a", secret_key=_SECRET, base_url=None, environment="test"
        )

    assert enabled is False
    assert observability._client is None
    assert _SECRET not in json.dumps(logs, ensure_ascii=False)


def test_generation_carries_usage_cost_and_a_stable_trace_without_the_workspace(
    memory: InMemorySpanExporter,
) -> None:
    from langfuse import Langfuse

    observability.export_generation(**_generation())

    [span] = _exported(memory)
    attributes = json.dumps(span["attributes"], ensure_ascii=False)
    assert span["name"] == "compile"
    # 같은 trace 값이면 API와 워커가 만든 관측이 하나의 Langfuse trace로 모인다.
    assert span["trace_id"] == Langfuse.create_trace_id(seed=_TRACE_ID)
    assert span["attributes"]["langfuse.observation.type"] == "generation"
    assert span["attributes"]["langfuse.observation.model.name"] == "test-model"
    assert json.loads(span["attributes"]["langfuse.observation.usage_details"]) == {
        "input": 10,
        "output": 5,
        "total": 15,
    }
    assert json.loads(span["attributes"]["langfuse.observation.cost_details"]) == {"total": 0.0025}
    assert _WORKSPACE_ID not in attributes
    assert hashlib.sha256(_WORKSPACE_ID.encode()).hexdigest() in attributes
    assert _TRACE_ID in attributes


def test_unlisted_metadata_and_body_never_reach_the_wire(memory: InMemorySpanExporter) -> None:
    observability.export_generation(
        **_generation(
            metadata={
                "call": "compile",
                "raw_source_id": _BODY,
                "prompt": _BODY,
                "anything_else": _BODY,
            }
        )
    )

    [span] = _exported(memory)
    assert _BODY not in json.dumps(span, ensure_ascii=False)


@pytest.mark.parametrize(
    "data",
    [
        {"prompt": _BODY},
        {"nested": {"question": _BODY}},
        {"nested": [{"answer_text": _BODY}]},
        {"LANGFUSE_SECRET_KEY": _BODY},
        {"harmless_name": _BODY * 40},
    ],
)
def test_mask_is_a_second_line_of_defense(data: dict[str, Any]) -> None:
    assert _BODY not in json.dumps(observability._mask(data=data), ensure_ascii=False)


def test_mask_keeps_the_values_the_exports_actually_send() -> None:
    data = {"outcome": "resolved", "duration_ms": 12, "rate": 0.5, "persisted": True}

    assert observability._mask(data=data) == data


def test_mask_is_wired_into_the_real_sdk(memory: InMemorySpanExporter) -> None:
    # 허용 목록을 우회한 호출을 가정한다. SDK가 실제로 마스크를 부르지 않으면 이 테스트가 실패한다.
    observability._export(
        name="probe",
        as_type="span",
        workspace_id=_WORKSPACE_ID,
        metadata={"prompt": _BODY},
    )

    [span] = _exported(memory)
    assert _BODY not in json.dumps(span, ensure_ascii=False)


def test_ask_turn_exports_only_named_report_fields(memory: InMemorySpanExporter) -> None:
    observability.export_ask_turn(
        workspace_id=_WORKSPACE_ID,
        persisted=True,
        control_report={
            "outcome": "resolved",
            "total_ms": 90,
            "route": {"decision": "STANDARD", "reason": "default"},
            "spans": [{"name": "retrieval", "start_ms": 0, "duration_ms": 40}],
            "evidence": {"wiki": 1, "source": 2},
            "retrieval": {"policy_version": "v1", "missing_channels": ["vector"]},
            "citation": {"dual_citation_rate": 1.0},
            # 보고서가 나중에 늘어나도 전송 범위가 함께 늘지 않아야 한다.
            "future_field": _BODY,
        },
    )

    [span] = _exported(memory)
    serialized = json.dumps(span, ensure_ascii=False)
    assert span["name"] == "ask.turn"
    assert _BODY not in serialized
    assert "span_retrieval_ms" in serialized
    assert "STANDARD" in serialized


def test_job_outcome_marks_failures_and_sends_no_error_text(
    memory: InMemorySpanExporter,
) -> None:
    observability.export_job_outcome(
        workspace_id=_WORKSPACE_ID,
        job_type="compile",
        outcome="failed",
        duration_ms=12.4,
        attempts=2,
        error_type="RuntimeError",
    )

    [span] = _exported(memory)
    assert span["name"] == "job.compile"
    assert span["attributes"]["langfuse.observation.level"] == "ERROR"
    assert "RuntimeError" in json.dumps(span["attributes"])


def test_work_without_a_trace_is_not_exported(memory: InMemorySpanExporter) -> None:
    structlog.contextvars.clear_contextvars()

    observability.export_generation(**_generation())

    assert _exported(memory) == []


def test_empty_workspace_is_not_hashed(memory: InMemorySpanExporter) -> None:
    # 이전 버전 API가 보낸 질의 임베딩은 워크스페이스가 비어 있다.
    observability.export_generation(**_generation(workspace_id=""))

    [span] = _exported(memory)
    assert "workspace_hash" not in json.dumps(span["attributes"])


def test_export_failure_is_swallowed_and_logs_no_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Broken:
        def create_trace_id(self, *, seed: str) -> str:
            return seed

        def start_observation(self, **_: Any) -> None:
            raise RuntimeError(f"401 Authorization: Bearer {_SECRET}")

    monkeypatch.setattr(observability, "_client", Broken())
    bind_trace(_TRACE_ID)

    with capture_logs() as logs:
        observability.export_generation(**_generation())

    assert logs[0]["event"] == "observability.export_failed"
    assert logs[0]["error_type"] == "RuntimeError"
    assert _SECRET not in json.dumps(logs, ensure_ascii=False)


def test_flush_returns_within_its_limit_when_the_service_hangs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release = threading.Event()
    monkeypatch.setattr(
        observability, "_client", SimpleNamespace(shutdown=lambda: release.wait(30))
    )

    with capture_logs() as logs:
        finished = observability.flush_observability(timeout_seconds=0.05)
    release.set()

    assert finished is False
    assert logs[0]["event"] == "observability.flush_timed_out"
    # 시간 초과 뒤의 내보내기는 종료 중인 SDK에 닿지 않는다.
    assert observability._client is None


def test_flush_failure_is_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode() -> None:
        raise RuntimeError(f"전송 실패 {_SECRET}")

    monkeypatch.setattr(observability, "_client", SimpleNamespace(shutdown=explode))

    with capture_logs() as logs:
        finished = observability.flush_observability(timeout_seconds=1.0)

    assert finished is True
    assert _SECRET not in json.dumps(logs, ensure_ascii=False)
