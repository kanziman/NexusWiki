"""공용 구조화 로깅 설정.

관련 태스크: P0-INIT-02
설계 근거: 01-CONTEXT.md > D-13
"""

from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any

import orjson
import structlog

REDACTED_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "authorization",
        "token",
        "api_key",
        "apikey",
        "secret",
        "email",
        "access_token",
        "refresh_token",
        "content",
        "supabase_secret_key",
        "openrouter_api_key",
        "openai_api_key",
        "database_url",
    }
)
REDACTION_PLACEHOLDER = "[REDACTED]"


def _redact_mapping(value: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    for key, item in value.items():
        if key.casefold() in REDACTED_KEYS:
            value[key] = REDACTION_PLACEHOLDER
        elif isinstance(item, MutableMapping):
            value[key] = _redact_mapping(item)
    return value


def redact_sensitive(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """민감 키의 값을 로그 렌더링 전에 마스킹한다."""
    del logger, method_name

    # ⚠️ denylist에서 키를 빠뜨리면 로그에 값이 조용히 새어 나간다.
    # 키 목록 자체를 단위 테스트로 고정한다. 근거: 01-CONTEXT.md > D-13.
    return _redact_mapping(event_dict)


def configure_logging(*, environment: str, log_level: str) -> None:
    """API와 worker가 공유하는 structlog 프로세서 체인을 설정한다."""
    renderer: structlog.types.Processor
    logger_factory: structlog.typing.WrappedLogger
    if environment == "development":
        renderer = structlog.dev.ConsoleRenderer(colors=True)
        logger_factory = structlog.PrintLoggerFactory()
    else:
        renderer = structlog.processors.JSONRenderer(serializer=orjson.dumps)
        logger_factory = structlog.BytesLoggerFactory()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redact_sensitive,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        logger_factory=logger_factory,
        cache_logger_on_first_use=True,
    )


def bind_job_context(*, job_id: str | None = None, workspace_id: str | None = None) -> None:
    """현재 실행 컨텍스트에 선택적으로 작업 식별자를 바인딩한다."""
    values = {
        key: value
        for key, value in {"job_id": job_id, "workspace_id": workspace_id}.items()
        if value is not None
    }
    structlog.contextvars.bind_contextvars(**values)


def clear_job_context() -> None:
    """현재 실행 컨텍스트의 모든 structlog 값을 지운다."""
    structlog.contextvars.clear_contextvars()


def get_logger(name: str) -> structlog.typing.FilteringBoundLogger:
    """이름이 지정된 공용 structlog 로거를 반환한다."""
    return structlog.get_logger(name)
