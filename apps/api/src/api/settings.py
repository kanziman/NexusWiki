"""api 프로세스 설정 — secret을 담을 필드가 존재하지 않는다.

관련 태스크: P2-BE-01
설계 근거: 02-CONTEXT.md > D-06, D-07

소비자: `api.main.create_app` (`app.state.settings`), 이후 모든 라우터
"""

from __future__ import annotations

from nexuswiki_core.settings import BaseAppSettings

__all__ = ["ApiSettings"]


class ApiSettings(BaseAppSettings):
    """`BaseAppSettings` + secret이 **아닌** 운영 토글만.

    ⚠️ 이 클래스에 `SUPABASE_SECRET_KEY` · `DATABASE_URL` · `OPENROUTER_API_KEY` ·
    `OPENAI_API_KEY` 중 하나라도 추가하는 순간 SEC-01이 무너진다. api와 worker가 단일
    이미지를 공유하므로(01-CONTEXT.md > D-01) api 프로세스는 worker 모듈을 물리적으로
    import 할 수 있고, 따라서 import 차단으로는 이 격리를 되찾을 수 없다. 격리는 오직
    "키를 담을 필드가 없다"로만 성립한다. 근거: 02-CONTEXT.md > D-06.

    ⚠️ 불변식은 **secret 필드의 부재**이지 "필드 개수 0"이 아니다. 두 문장을 섞으면
    운영 토글 하나를 더할 때마다 SEC-01 단언을 손대게 되고, 손대는 습관이 붙으면 그
    단언이 실제로 지켜야 할 것을 지키던 날의 기억만 남는다.
    `packages/core/tests/test_settings.py`가 secret 부재를 단언하고, 추가 필드는
    **명시적 허용 목록**으로 고정한다 — 그 목록에 없는 필드가 생기면 red가 된다.
    단언을 느슨하게 만들어 통과시키지 말 것.
    """

    # 요청 본문 텍스트 길이 상한 (OPS-01의 "입력 크기 상한", T-03-24).
    # 자격증명이 아니라 운영 토글이므로 기본값을 갖는다.
    # ⚠️ 단위는 **유니코드 코드 포인트**이지 바이트가 아니다. 한글은 UTF-8에서 3바이트라
    #    바이트 상한과 값이 세 배 어긋난다.
    MAX_TEXT_CHARS: int = 500_000
