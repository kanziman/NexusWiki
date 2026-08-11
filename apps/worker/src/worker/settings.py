"""worker 프로세스 설정 — secret이 실제로 들어오는 유일한 경계.

관련 태스크: P2-BE-01
설계 근거: 02-CONTEXT.md > D-06, D-07, D-10, D-22

소비자: `worker.__main__.main`, 이후 02-03의 `service_client(settings: WorkerSettings)`
"""

from __future__ import annotations

from pydantic import Field

from nexuswiki_core.settings import BaseAppSettings

__all__ = ["WorkerSettings"]


class WorkerSettings(BaseAppSettings):
    """`BaseAppSettings` + worker에만 주입되는 secret 3종과 모델 슬러그."""

    # ⚠️ 아래 세 필드의 이름을 casefold한 문자열이 `nexuswiki_core.logging`의
    # `REDACTED_KEYS` 원소와 정확히 일치해야 한다. 이름을 바꾸거나 새 secret을
    # 추가하면서 그 집합을 갱신하지 않으면 로그 마스킹이 **에러 없이** 이 값들을
    # 덮지 않게 되고, 값이 로그에 찍힌 뒤에야 사실이 드러난다.
    # `packages/core/tests/test_logging_redaction.py`가 이 커플링을 단언한다.
    SUPABASE_SECRET_KEY: str
    DATABASE_URL: str
    OPENROUTER_API_KEY: str
    # `openai_api_key`는 Studio AI의 별도 소비자 때문에 REDACTED_KEYS에는 남는다.

    # ⚠️ 코드 기본값을 두지 않는다. `.env.sample`과 PROJECT.md의 기본값이 서로 다르고
    # Phase 2에는 LLM 호출이 없어 어느 쪽이 맞는지 검증할 수단이 없다. Phase 3에서
    # 실제 OpenRouter 슬러그를 확인하며 정리한다. 근거: 02-CONTEXT.md > D-22.
    LLM_MODEL: str

    # Dedicated caller credential for the private API-to-worker query-embedding
    # boundary. It is never a provider credential and never belongs in ApiSettings.
    QUERY_EMBEDDING_INTERNAL_TOKEN: str | None = None
    QUERY_EMBEDDING_MAX_TEXT_CHARS: int = 10_000
    QUERY_EMBEDDING_TIMEOUT_SECONDS: float = 5.0
    QUERY_EMBEDDING_MAX_CONCURRENCY: int = 4
    QUERY_EMBEDDING_RATE_CAPACITY: int = Field(default=100, gt=0)
    QUERY_EMBEDDING_RATE_REFILL_TOKENS_PER_SECOND: float = Field(default=1.0, gt=0)

    # 자격증명이 아니라 운영 토글이므로 기본값을 갖는다 — 없다고 worker가 못 뜰
    # 이유가 없다. 배포 환경에서 RTT 프로브만 끄고 싶을 때 쓴다.
    RTT_PROBE_ENABLED: bool = True

    # ⚠️ 기본값이 `False`인 것이 이 토글의 요점이다. 큐 기준선 프로브는 기동 시
    # 200회가 넘는 claim→complete 왕복을 돌리고 그만큼의 잡 행을 남긴다. 기본이
    # 참이면 모든 재배포·재시작이 운영 큐에 그 부하와 잔여 행을 더한다.
    # 배포 후 한 번만 켜고 측정이 끝나면 되돌린다. 근거: 02-CONTEXT.md > D-17.
    QUEUE_BASELINE_ENABLED: bool = False

    # 프로브가 잡을 만들 워크스페이스. `service_role`은 `workspaces`에 SELECT만
    # 가지므로(0007 섹션 8) 프로브가 스스로 만들 수 없고, `jobs`에는 DELETE 권한이
    # 없어 남긴 행을 스스로 지울 수도 없다. 그래서 처분 가능한 워크스페이스 id를
    # 밖에서 주입받고, 정리는 그 워크스페이스 삭제의 cascade에 맡긴다.
    QUEUE_BASELINE_WORKSPACE_ID: str | None = None

    # -- 원격 원본 페치 (03-06) ---------------------------------------------
    FETCH_MAX_BYTES: int = 10_485_760
    FETCH_TIMEOUT_SECONDS: float = 20.0
    FETCH_MAX_REDIRECTS: int = 3
    # ⚠️ 참이면 사용자가 지정한 사설망 주소(플랫폼 메타데이터 포함)로 워커가 나갈 수
    #    있다. 로컬 개발에서만 켜고 배포 환경에서는 절대 켜지 않는다.
    ALLOW_PRIVATE_FETCH_TARGETS: bool = False

    # -- 컴파일 상한 (OPS-01) -------------------------------------------------
    #
    # 자격증명이 아니라 운영 토글이므로 기본값을 갖는다 (`RTT_PROBE_ENABLED`와 같은 결).
    #
    # ⚠️ 두 상한은 장식이 아니다. 컴파일 비용은 입력 길이와 출력 페이지 수에 선형이고
    #    `0009`의 인큐 시점 상한은 **이미 쓴 돈**만 본다 — 진행 중인 한 잡이 상한을
    #    얼마나 넘길지는 막지 못한다. 그 창을 좁히는 것이 아래 둘이다 (T-03-24).
    COMPILE_MAX_PAGES: int = 8
    COMPILE_MAX_INPUT_TOKENS: int = 24000

    # -- 임베딩 (03-09이 소비한다) --------------------------------------------
    #
    # ⚠️ 아래 셋을 소비하는 코드는 이 플랜에 없다. 그럼에도 여기서 한 번에 정의하는
    #    이유는 `settings.py` 하나를 03-06과 03-09가 같은 wave에서 동시에 열지 않게
    #    하기 위해서다 — 설정 파일 하나를 두 플랜이 병렬로 고치는 것이 이 페이즈에서
    #    가장 흔한 충돌 형태다.
    #
    # ⚠️ 두 슬러그에 **코드 기본값을 지어내지 않는다.** 실제 값은 03-04 Task 2가
    #    OpenRouter에서 관측해 `.env.sample`에 적었고, 값의 소유자는 `.env`다.
    #    `None`은 "아직 주입되지 않았다"는 사실 그대로이며, 소비자(03-09)가 사용
    #    직전에 키 이름을 밝히며 끊는다. 없는 값을 그럴듯한 문자열로 채우면 그 오타가
    #    임베딩 잡의 런타임 실패로만 드러난다.
    EMBEDDING_MODEL: str | None = None
    EMBEDDING_PROVIDER: str | None = None
    EMBED_BATCH_SIZE: int = 32

    REAP_TIMEOUT_SECONDS: int = 900
    REAP_ENABLED: bool = True
