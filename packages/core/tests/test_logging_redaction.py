"""공용 로깅의 민감정보 마스킹 회귀 테스트."""

import json

from nexuswiki_core.logging import (
    REDACTED_KEYS,
    REDACTION_PLACEHOLDER,
    bind_job_context,
    clear_job_context,
    configure_logging,
    get_logger,
    redact_sensitive,
)


def test_redacted_keys_include_required_sensitive_fields() -> None:
    required = {
        "password",
        "authorization",
        "token",
        "api_key",
        "secret",
        "email",
        "access_token",
        "content",
    }

    assert required <= REDACTED_KEYS


def test_redact_sensitive_preserves_safe_fields() -> None:
    event = {
        "email": "a@b.com",
        "authorization": "Bearer x",
        "job_id": "j1",
    }

    result = redact_sensitive(None, "info", event)

    assert result["email"] == REDACTION_PLACEHOLDER
    assert result["authorization"] == REDACTION_PLACEHOLDER
    assert result["job_id"] == "j1"


def test_redact_sensitive_handles_nested_mappings() -> None:
    event = {"headers": {"authorization": "Bearer x"}}

    result = redact_sensitive(None, "info", event)

    assert result["headers"]["authorization"] == REDACTION_PLACEHOLDER


def test_bound_job_context_is_rendered_as_json(capsys) -> None:
    configure_logging(environment="production", log_level="INFO")
    bind_job_context(job_id="job-1", workspace_id="workspace-1")
    try:
        get_logger("test").info("job.test")
    finally:
        clear_job_context()

    payload = json.loads(capsys.readouterr().out)
    assert payload["job_id"] == "job-1"
    assert payload["workspace_id"] == "workspace-1"
