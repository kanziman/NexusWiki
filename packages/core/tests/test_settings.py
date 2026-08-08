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


# ⚠️ 이 목록은 "필드를 더해도 된다"가 아니라 **"더한 필드가 secret이 아님을 사람이
#    확인했다"**는 기록이다. 새 이름을 여기 넣기 전에 위 SECRET_FIELD_NAMES와 대조할 것.
#    (03-04: MAX_TEXT_CHARS — 요청 본문 길이 상한, OPS-01)
NON_SECRET_API_FIELDS = frozenset({"MAX_TEXT_CHARS"})


def test_api_settings_adds_only_reviewed_non_secret_fields() -> None:
    # 불변식은 "필드 개수 0"이 아니라 "secret 필드의 부재"다. 그러나 아무 필드나
    # 조용히 늘어나는 것도 막아야 하므로 추가분을 허용 목록으로 고정한다.
    added = set(ApiSettings.model_fields) - set(BaseAppSettings.model_fields)

    assert added == NON_SECRET_API_FIELDS, sorted(added)
    assert not (added & SECRET_FIELD_NAMES)


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
