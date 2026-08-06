"""worker 프로세스 설정 — secret이 실제로 들어오는 유일한 경계.

관련 태스크: P2-BE-01
설계 근거: 02-CONTEXT.md > D-06, D-07, D-10, D-22

소비자: `worker.__main__.main`, 이후 02-03의 `service_client(settings: WorkerSettings)`
"""

from __future__ import annotations

from nexuswiki_core.settings import BaseAppSettings

__all__ = ["WorkerSettings"]


class WorkerSettings(BaseAppSettings):
    """`BaseAppSettings` + worker에만 주입되는 secret 4종과 모델 슬러그."""

    # ⚠️ 아래 네 필드의 이름을 casefold한 문자열이 `nexuswiki_core.logging`의
    # `REDACTED_KEYS` 원소와 정확히 일치해야 한다. 이름을 바꾸거나 새 secret을
    # 추가하면서 그 집합을 갱신하지 않으면 로그 마스킹이 **에러 없이** 이 값들을
    # 덮지 않게 되고, 값이 로그에 찍힌 뒤에야 사실이 드러난다.
    # `packages/core/tests/test_logging_redaction.py`가 이 커플링을 단언한다.
    SUPABASE_SECRET_KEY: str
    DATABASE_URL: str
    OPENROUTER_API_KEY: str
    OPENAI_API_KEY: str

    # ⚠️ 코드 기본값을 두지 않는다. `.env.sample`과 PROJECT.md의 기본값이 서로 다르고
    # Phase 2에는 LLM 호출이 없어 어느 쪽이 맞는지 검증할 수단이 없다. Phase 3에서
    # 실제 OpenRouter 슬러그를 확인하며 정리한다. 근거: 02-CONTEXT.md > D-22.
    LLM_MODEL: str

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
