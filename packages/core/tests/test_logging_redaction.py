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


def test_worker_settings_secret_fields_stay_inside_the_denylist() -> None:
    # ⚠️ `WorkerSettings`가 secret 필드를 추가하거나 이름을 바꾸면서 이 단언을
    # 갱신하지 않으면, 마스킹이 멈춘 사실이 로그에 값이 찍힌 뒤에야 드러난다.
    from worker.settings import WorkerSettings

    secret_fields = {
        "SUPABASE_SECRET_KEY",
        "DATABASE_URL",
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
    }

    assert secret_fields <= set(WorkerSettings.model_fields)
    assert {name.casefold() for name in secret_fields} <= REDACTED_KEYS


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


def test_redacts_sensitive_values_inside_one_level_sequences() -> None:
    event = {
        "items": [{"authorization": "Bearer sequence-secret", "status": "safe-list"}],
        "contacts": ({"email": "sequence@example.com", "active": True},),
    }

    result = redact_sensitive(None, "info", event)

    assert isinstance(result["items"], list)
    assert result["items"][0]["authorization"] == REDACTION_PLACEHOLDER
    assert result["items"][0]["status"] == "safe-list"
    assert isinstance(result["contacts"], tuple)
    assert result["contacts"][0]["email"] == REDACTION_PLACEHOLDER
    assert result["contacts"][0]["active"] is True


def test_redacts_sensitive_values_across_nested_sequences() -> None:
    event = {
        "payload": [
            (
                {
                    "metadata": [{"token": "nested-token-sentinel"}],
                    "content": "nested-content-sentinel",
                    "kind": "safe-neighbor",
                },
            )
        ]
    }

    result = redact_sensitive(None, "info", event)

    assert isinstance(result["payload"], list)
    assert isinstance(result["payload"][0], tuple)
    nested = result["payload"][0][0]
    assert isinstance(nested["metadata"], list)
    assert nested["metadata"][0]["token"] == REDACTION_PLACEHOLDER
    assert nested["content"] == REDACTION_PLACEHOLDER
    assert nested["kind"] == "safe-neighbor"


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
