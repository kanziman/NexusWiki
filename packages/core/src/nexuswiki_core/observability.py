"""자격 증명이 있을 때만 trace 메타데이터를 Langfuse로 내보내는 어댑터.

관련 이슈: #167
설계 근거: openspec/changes/ai-control-flow-accounting/design.md > D8
계약: openspec/changes/ai-control-flow-accounting/specs/ai-request-tracing/spec.md

이 모듈의 모든 공개 함수는 예외를 밖으로 던지지 않는다. 월 상한과 Control Room의 원천은
Postgres이고 여기는 개발자용 사본일 뿐이므로, 내보내기 실패가 요청이나 잡의 결과를 바꾸면
안 된다.

⚠️ `input`과 `output`을 절대 넘기지 않는다. 고객 원문을 외부 서비스로 복제하지 않는 것이 이
경계의 존재 이유다. `_mask`는 호출자의 실수를 막는 2차 방어선이지 허용 근거가 아니다.

⚠️ SDK는 구간 시작 시각을 소급 지정할 수 없다. 관측 객체는 내보내는 순간에 만들어져 Langfuse
타임라인의 길이가 0에 가깝게 보이므로, 실제 소요 시간은 `duration_ms` 메타데이터로 읽는다.

⚠️ 키는 워커만 갖는다. API는 턴 보고서를 내부 라우트로 넘기고 이 모듈을 직접 켜지 않는다.

소비자: `worker.__main__`, `worker.ask_turn_export`, `worker.llm_gateway`, `worker.queue`
"""

from __future__ import annotations

import hashlib
import re
import threading
from collections.abc import Mapping
from typing import Any, Final

from nexuswiki_core.logging import REDACTED_KEYS, REDACTION_PLACEHOLDER, get_logger
from nexuswiki_core.trace import current_trace_id

__all__ = [
    "FLUSH_TIMEOUT_SECONDS",
    "configure_observability",
    "export_ask_turn",
    "export_generation",
    "export_job_outcome",
    "flush_observability",
]

# ⚠️ `WORKER_GRACE_SECONDS`(20초)와 합쳐도 플랫폼의 SIGKILL(30초)보다 짧아야 한다.
FLUSH_TIMEOUT_SECONDS: Final[float] = 3.0

# SDK의 HTTP 타임아웃(초). 전송은 백그라운드 스레드에서 일어나지만, 프로세스 종료 시 남은 배치를
# 보내는 시간도 이 값이 결정하므로 위 상한 안에 들어오도록 짧게 둔다.
_EXPORT_TIMEOUT_SECONDS: Final[int] = 2

# 이보다 긴 문자열은 식별자나 enum일 수 없으므로 본문으로 간주한다.
_MAX_STRING_CHARS: Final[int] = 128

_BODY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "answer",
        "answer_text",
        "body",
        "citations",
        "completion",
        "input",
        "markdown",
        "messages",
        "output",
        "prompt",
        "query",
        "question",
        "system_prompt",
        "text",
        "user_prompt",
    }
)

# 호출자가 넘긴 사용량 메타데이터 중 외부로 보내도 되는 키. 새 키는 본문이 아님을 확인하고 더한다.
_GENERATION_METADATA_KEYS: Final[frozenset[str]] = frozenset(
    {
        "attempt",
        "call",
        "fingerprint",
        "incomplete",
        "route",
        "route_reason",
        "truncated_input",
    }
)

# 턴 보고서에서 외부로 보내도 되는 값의 모양. 식별자와 enum만 통과한다. 공백이 있는 문장은 본문일 수
# 있고, 이 값은 프로세스 경계를 넘어 오므로 호출자의 조립을 믿지 않는다.
_TOKEN_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
_SPAN_NAMES: Final[frozenset[str]] = frozenset(
    {"retrieval", "context", "llm_stream", "repair", "citation"}
)

_client: Any | None = None


def _logger() -> Any:
    return get_logger(__name__)


def configure_observability(
    *,
    public_key: str | None,
    secret_key: str | None,
    base_url: str | None,
    environment: str,
    release: str | None = None,
    span_exporter: Any | None = None,
) -> bool:
    """프로세스 기동 시 한 번 부른다. 내보내기가 켜졌으면 `True`를 돌려준다.

    ⚠️ SDK는 여기서만 import한다. import 시점에 부작용을 두지 않는 기존 규칙을 지키고, 키가 없는
    프로세스에 백그라운드 전송 스레드를 만들지 않기 위해서다.

    `span_exporter`는 테스트가 실제 SDK의 전송 값을 검사하기 위한 주입점이다.
    """
    global _client
    _client = None

    if not public_key and not secret_key:
        _logger().info("observability.disabled", reason="no_credentials")
        return False
    if not public_key or not secret_key:
        # 한쪽만 있으면 설정 실수다. 기동은 막지 않되 조용히 꺼지지 않도록 흔적을 남긴다.
        _logger().warning("observability.disabled", reason="partial_credentials")
        return False

    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            base_url=base_url,
            environment=environment.lower(),
            release=release,
            timeout=_EXPORT_TIMEOUT_SECONDS,
            mask=_mask,
            span_exporter=span_exporter,
        )
    except Exception as exc:  # noqa: BLE001 - 외부 관측 때문에 프로세스가 죽으면 안 된다.
        _warn_failure("observability.configure_failed", exc)
        _client = None
        return False

    _logger().info("observability.enabled", base_url=base_url)
    return True


def export_generation(
    *,
    name: str,
    as_type: str,
    workspace_id: str,
    model: str,
    provider: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    cost_micros: int,
    duration_ms: int,
    metadata: Mapping[str, Any],
) -> None:
    """공급자 호출 한 건을 내보낸다. `as_type`은 `generation` 또는 `embedding`이다."""
    _export(
        name=name,
        as_type=as_type,
        workspace_id=workspace_id,
        metadata={
            **{key: value for key, value in metadata.items() if key in _GENERATION_METADATA_KEYS},
            "provider": provider,
            "duration_ms": duration_ms,
        },
        model=model,
        usage_details={
            "input": prompt_tokens,
            "output": completion_tokens,
            "total": total_tokens,
        },
        cost_details={"total": cost_micros / 1_000_000},
    )


def export_ask_turn(
    *, workspace_id: str, control_report: Mapping[str, Any], persisted: bool
) -> None:
    """종결된 Ask 턴의 구간과 결정을 내보낸다.

    `control_report`는 이미 허용 필드로 조립된 값이지만, 여기서도 필요한 필드만 꺼낸다. 보고서에
    나중에 필드가 늘어도 외부 전송 범위가 함께 늘지 않게 하기 위해서다.
    """
    try:
        route = _mapping(control_report.get("route"))
        evidence = _mapping(control_report.get("evidence"))
        retrieval = _mapping(control_report.get("retrieval"))
        citation = _mapping(control_report.get("citation"))
        outcome = _token(control_report.get("outcome"))
        missing = retrieval.get("missing_channels")
        metadata: dict[str, Any] = {
            "outcome": outcome,
            "persisted": persisted is True,
            "duration_ms": _number(control_report.get("total_ms")),
            "route": _token(route.get("decision")),
            "reason": _token(route.get("reason")),
            "evidence_wiki": _number(evidence.get("wiki")),
            "evidence_source": _number(evidence.get("source")),
            "policy_version": _token(retrieval.get("policy_version")),
            "missing_channels": ",".join(
                name for name in (_token(item) for item in _sequence(missing)) if name
            ),
            "cited_anchor_count": _number(citation.get("cited_anchor_count")),
            "fabricated_anchor_count": _number(citation.get("fabricated_anchor_count")),
            "dual_citation_rate": _number(citation.get("dual_citation_rate")),
            "unsourced_sentence_ratio": _number(citation.get("unsourced_sentence_ratio")),
        }
        for span in _sequence(control_report.get("spans")):
            span = _mapping(span)
            # ⚠️ 이름이 곧 메타데이터 키다. 닫지 않으면 키에 실린 본문은 값 검사를 지나간다.
            if span.get("name") in _SPAN_NAMES:
                metadata[f"span_{span['name']}_ms"] = _number(span.get("duration_ms"))
    except Exception as exc:  # noqa: BLE001 - 형태가 틀린 보고서가 호출자를 실패시키면 안 된다.
        _warn_failure("observability.export_failed", exc)
        return
    _export(
        name="ask.turn",
        as_type="span",
        workspace_id=workspace_id,
        metadata=metadata,
        level="ERROR" if outcome == "error" or not persisted else "DEFAULT",
    )


def export_job_outcome(
    *,
    workspace_id: str,
    job_type: str,
    outcome: str,
    duration_ms: float,
    attempts: int | None,
    error_type: str | None = None,
) -> None:
    """잡 한 번의 종결을 내보낸다.

    ⚠️ 정제된 오류 문구도 보내지 않는다. 문구에는 원문 URL 같은 사용자 입력이 섞일 수 있어
    예외 클래스 이름만 보낸다.
    """
    _export(
        name=f"job.{job_type}",
        as_type="span",
        workspace_id=workspace_id,
        metadata={
            "outcome": outcome,
            "duration_ms": round(duration_ms),
            "attempts": attempts,
            "error_type": error_type,
        },
        level="ERROR" if outcome in {"failed", "dead"} else "DEFAULT",
    )


def flush_observability(*, timeout_seconds: float = FLUSH_TIMEOUT_SECONDS) -> bool:
    """남은 데이터를 제한 시간 안에서만 보낸다. 시간 안에 끝났으면 `True`를 돌려준다.

    ⚠️ `True`는 종료 절차가 끝났다는 뜻이지 전송에 성공했다는 뜻이 아니다. SDK의 백그라운드 전송
    실패는 stderr의 평문 한 줄로만 남으므로, 배포 뒤 첫 trace 수신은 Langfuse 화면에서 확인한다.

    ⚠️ SDK의 `flush`에는 시간 제한이 없어 데몬 스레드에서 돌리고 `join`으로 기다린다.

    ⚠️ `flush`가 아니라 `shutdown`을 부르는 이유는 SDK가 등록한 atexit 처리기를 먼저 해제하기
    때문이다. 해제하지 않으면 인터프리터 종료 시점에 제한 없는 flush가 한 번 더 돌아, 여기서 지킨
    상한이 무의미해진다.
    """
    global _client
    client = _client
    if client is None:
        return True
    # 종료된 SDK에 뒤늦은 내보내기가 들어가지 않게 먼저 비운다.
    _client = None

    def run() -> None:
        try:
            client.shutdown()
        except Exception as exc:  # noqa: BLE001 - 종료 경로에서 잡 처리 결과를 바꾸면 안 된다.
            _warn_failure("observability.flush_failed", exc)

    thread = threading.Thread(target=run, name="observability-flush", daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        _logger().warning("observability.flush_timed_out", timeout_seconds=timeout_seconds)
        return False
    return True


def _export(
    *,
    name: str,
    as_type: str,
    workspace_id: str,
    metadata: Mapping[str, Any],
    **fields: Any,
) -> None:
    client = _client
    if client is None:
        return
    trace_id = current_trace_id()
    # 마이그레이션 이전 잡처럼 trace가 없는 작업은 어느 trace에도 이을 수 없다.
    if trace_id is None:
        return
    try:
        observation = client.start_observation(
            trace_context={"trace_id": client.create_trace_id(seed=trace_id)},
            name=name,
            as_type=as_type,
            metadata={
                **{key: value for key, value in metadata.items() if value is not None},
                # Control Room과 대조하기 위한 원래 값이다. Langfuse trace ID는 이 값의 해시다.
                "trace_id": trace_id,
                **_workspace_attribute(workspace_id),
            },
            **fields,
        )
        observation.end()
    except Exception as exc:  # noqa: BLE001 - 내보내기 실패는 호출자의 결과를 바꾸지 않는다.
        _warn_failure("observability.export_failed", exc)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _token(value: Any) -> str | None:
    return value if isinstance(value, str) and _TOKEN_PATTERN.fullmatch(value) else None


def _number(value: Any) -> int | float | None:
    return value if isinstance(value, int | float) and not isinstance(value, bool) else None


def _workspace_attribute(workspace_id: str) -> dict[str, str]:
    # 이전 버전 API가 보낸 질의 임베딩은 워크스페이스가 비어 있다. 빈 값의 해시는 의미가 없다.
    if not workspace_id:
        return {}
    return {"workspace_hash": hashlib.sha256(workspace_id.encode("utf-8")).hexdigest()}


def _mask(*, data: Any, **_: Any) -> Any:
    """SDK가 전송 직전에 부르는 2차 방어선."""
    if isinstance(data, Mapping):
        return {
            key: REDACTION_PLACEHOLDER
            if str(key).casefold() in REDACTED_KEYS or str(key).casefold() in _BODY_KEYS
            else _mask(data=value)
            for key, value in data.items()
            # 키에 실린 긴 문자열은 값 검사로 잡히지 않는다.
            if len(str(key)) <= _MAX_STRING_CHARS
        }
    if isinstance(data, list | tuple):
        return [_mask(data=item) for item in data]
    if isinstance(data, str) and len(data) > _MAX_STRING_CHARS:
        return REDACTION_PLACEHOLDER
    return data


def _warn_failure(event: str, exc: Exception) -> None:
    # ⚠️ 예외 문구를 남기지 않는다. HTTP 클라이언트 예외에는 요청 헤더나 자격 증명이 섞일 수 있다.
    _logger().warning(event, error_type=type(exc).__name__)
