"""api와 worker가 공유하는 설정 조상 클래스.

관련 태스크: P2-BE-01
설계 근거: 02-CONTEXT.md > D-06, D-07, D-10

⚠️ pydantic-settings가 python-dotenv를 전이 의존으로 끌고 들어오지만 이 프로젝트는
`.env` 파일을 읽지 않는다 — `model_config`가 `env_file`을 열지 않으므로 python-dotenv는
설치만 되고 사용되지 않는 의존이다. 값의 출처는 프로세스 환경 하나뿐이며, 이 단일 출처가
Railway 서비스별 env 스코프(01-CONTEXT.md > D-12)를 SEC-01의 집행 지점으로 만든다.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError, field_validator
from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["BaseAppSettings", "MissingSettingError"]


class MissingSettingError(RuntimeError):
    """필수 설정이 누락되었거나 빈 문자열일 때 키 이름과 함께 보고한다."""

    def __init__(self, keys: list[str], *, settings_name: str) -> None:
        self.keys = keys
        super().__init__(
            f"{settings_name}: 필수 설정이 없거나 비어 있다 — {', '.join(keys)}. "
            "프로세스 환경에 해당 키를 채운 뒤 다시 기동할 것."
        )


class BaseAppSettings(BaseSettings):
    """api와 worker가 공통으로 갖는 네 개의 비밀 아닌 설정.

    ⚠️ 이 클래스에는 secret을 절대 추가하지 않는다. 여기에 넣는 순간 `ApiSettings`가
    그것을 상속받아 api 프로세스가 키를 담을 그릇을 갖게 되고, SEC-01이 무너진다.
    secret은 `WorkerSettings`에만 선언한다. 근거: 02-CONTEXT.md > D-06, D-07.

    ⚠️ 필수 설정이 없으면 프로세스는 라우터나 워커 루프를 세우기 전에 죽는다. worker가
    `SUPABASE_SECRET_KEY` 없이 조용히 뜨면 BYPASSRLS 경로가 자격증명 없이 도는 것과
    같아지므로, 반쯤 설정된 프로세스보다 안 뜨는 편이 안전하다. 근거: 02-CONTEXT.md > D-10.
    """

    model_config = SettingsConfigDict(
        env_file=None,
        case_sensitive=True,
        extra="ignore",
    )

    SUPABASE_URL: str
    SUPABASE_PUBLISHABLE_KEY: str
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    @field_validator("*", mode="after")
    @classmethod
    def _reject_blank_string(cls, value: Any, info: ValidationInfo) -> Any:
        # 기존 `health.py`의 `if not os.environ.get(key)` 의미론을 그대로 옮긴다 —
        # 빈 문자열과 공백뿐인 값은 "설정되지 않음"과 구별하지 않는다.
        if isinstance(value, str) and not value.strip():
            raise ValueError(f"{info.field_name} is empty")
        return value

    def __init__(self, **values: Any) -> None:
        try:
            super().__init__(**values)
        except ValidationError as exc:
            # 현재 모든 필드가 `str`이므로 검증 실패는 전부 "누락 또는 빈 값"이다.
            # 나중에 다른 타입의 필드가 생기면 여기서 사유를 갈라야 한다.
            keys = sorted({str(error["loc"][0]) for error in exc.errors() if error["loc"]})
            raise MissingSettingError(keys, settings_name=type(self).__name__) from exc
