"""Settings 3계층의 역량 경계와 부팅 시점 실패 회귀 테스트."""

import pytest
from api.settings import ApiSettings
from nexuswiki_core.settings import BaseAppSettings, MissingSettingError

# ⚠️ 이 네 이름이 `ApiSettings`에 하나라도 생기면 SEC-01이 무너진다.
SECRET_FIELD_NAMES = frozenset(
    {
        "SUPABASE_SECRET_KEY",
        "DATABASE_URL",
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
    }
)

REQUIRED_BASE_ENV = ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY")


def _set_complete_base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")


def test_api_settings_has_no_field_that_could_hold_a_secret() -> None:
    overlap = SECRET_FIELD_NAMES & set(ApiSettings.model_fields)

    assert not overlap, sorted(overlap)


def test_api_settings_adds_no_field_beyond_the_shared_ancestor() -> None:
    assert set(ApiSettings.model_fields) == set(BaseAppSettings.model_fields)


def test_base_settings_expose_only_the_four_non_secret_keys() -> None:
    assert set(BaseAppSettings.model_fields) == {
        "SUPABASE_URL",
        "SUPABASE_PUBLISHABLE_KEY",
        "ENVIRONMENT",
        "LOG_LEVEL",
    }


def test_api_settings_reads_values_from_the_process_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_complete_base_env(monkeypatch)

    settings = ApiSettings()

    assert settings.SUPABASE_URL == "https://example.invalid"
    assert settings.SUPABASE_PUBLISHABLE_KEY == "sb_publishable_test"
    assert settings.ENVIRONMENT == "development"
    assert settings.LOG_LEVEL == "INFO"


@pytest.mark.parametrize("missing_key", REQUIRED_BASE_ENV)
def test_absent_required_setting_fails_and_names_the_key(
    monkeypatch: pytest.MonkeyPatch, missing_key: str
) -> None:
    _set_complete_base_env(monkeypatch)
    monkeypatch.delenv(missing_key, raising=False)

    with pytest.raises(MissingSettingError) as excinfo:
        ApiSettings()

    assert missing_key in str(excinfo.value)


@pytest.mark.parametrize("blank_key", REQUIRED_BASE_ENV)
def test_empty_string_setting_fails_exactly_like_an_absent_one(
    monkeypatch: pytest.MonkeyPatch, blank_key: str
) -> None:
    _set_complete_base_env(monkeypatch)
    monkeypatch.setenv(blank_key, "")

    with pytest.raises(MissingSettingError) as excinfo:
        ApiSettings()

    assert blank_key in str(excinfo.value)


def test_whitespace_only_setting_is_treated_as_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_complete_base_env(monkeypatch)
    monkeypatch.setenv("SUPABASE_URL", "   ")

    with pytest.raises(MissingSettingError) as excinfo:
        ApiSettings()

    assert "SUPABASE_URL" in str(excinfo.value)


def test_dotenv_file_is_never_consulted_for_settings_values() -> None:
    assert ApiSettings.model_config.get("env_file") is None
