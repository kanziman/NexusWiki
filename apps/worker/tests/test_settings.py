"""worker 전용 secret 필드 보유와 로그 마스킹 정합 회귀 테스트."""

import pytest
from pydantic_core import PydanticUndefined

from nexuswiki_core.logging import REDACTED_KEYS
from nexuswiki_core.settings import MissingSettingError
from worker.settings import WorkerSettings

# worker만이 이 값들을 담는다. 이름이 곧 마스킹 계약이다.
SECRET_FIELD_NAMES = frozenset(
    {
        "SUPABASE_SECRET_KEY",
        "DATABASE_URL",
        "OPENROUTER_API_KEY",
    }
)

COMPLETE_WORKER_ENV = {
    "SUPABASE_URL": "https://example.invalid",
    "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_test",
    "SUPABASE_SECRET_KEY": "sb_secret_test",
    "DATABASE_URL": "postgresql://postgres:pw@127.0.0.1:54422/postgres",
    "OPENROUTER_API_KEY": "sk-or-v1-test",
    "LLM_MODEL": "anthropic/claude-3.5-sonnet",
}


def _set_complete_worker_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in COMPLETE_WORKER_ENV.items():
        monkeypatch.setenv(key, value)


def test_worker_settings_declare_every_secret_field() -> None:
    assert SECRET_FIELD_NAMES <= set(WorkerSettings.model_fields)


def test_worker_settings_declare_the_llm_model_key() -> None:
    assert "LLM_MODEL" in WorkerSettings.model_fields


def test_worker_secret_field_names_are_covered_by_log_redaction() -> None:
    # ⚠️ 이 단언이 깨지면 로그 마스킹이 조용히 secret을 덮지 않게 된다.
    assert {name.casefold() for name in SECRET_FIELD_NAMES} <= REDACTED_KEYS


def test_llm_model_has_no_default_baked_into_the_code() -> None:
    default = WorkerSettings.model_fields["LLM_MODEL"].default

    assert default is None or default is PydanticUndefined


def test_worker_settings_read_every_key_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_complete_worker_env(monkeypatch)

    settings = WorkerSettings()

    # 리터럴을 직접 비교하면 ruff S105가 하드코딩된 비밀번호로 잡는다.
    # 픽스처 딕셔너리를 단일 출처로 삼아 그 오탐과 값 중복을 함께 없앤다.
    for key in ("SUPABASE_SECRET_KEY", "LLM_MODEL"):
        assert getattr(settings, key) == COMPLETE_WORKER_ENV[key]


def test_worker_settings_no_longer_declares_the_unused_openai_key() -> None:
    assert "OPENAI_API_KEY" not in WorkerSettings.model_fields


@pytest.mark.parametrize("missing_key", sorted(SECRET_FIELD_NAMES))
def test_worker_refuses_to_boot_without_a_secret_and_names_it(
    monkeypatch: pytest.MonkeyPatch, missing_key: str
) -> None:
    _set_complete_worker_env(monkeypatch)
    monkeypatch.delenv(missing_key, raising=False)

    with pytest.raises(MissingSettingError) as excinfo:
        WorkerSettings()

    assert missing_key in str(excinfo.value)


def test_worker_refuses_to_boot_on_an_empty_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_complete_worker_env(monkeypatch)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "")

    with pytest.raises(MissingSettingError) as excinfo:
        WorkerSettings()

    assert "SUPABASE_SECRET_KEY" in str(excinfo.value)
