"""api 프로세스 설정 — secret을 담을 필드가 존재하지 않는다.

관련 태스크: P2-BE-01
설계 근거: 02-CONTEXT.md > D-06, D-07

소비자: `api.main.create_app` (`app.state.settings`), 이후 모든 라우터
"""

from __future__ import annotations

from nexuswiki_core.settings import BaseAppSettings

__all__ = ["ApiSettings"]


class ApiSettings(BaseAppSettings):
    """`BaseAppSettings`에 필드를 하나도 추가하지 않는다.

    ⚠️ 이 클래스에 `SUPABASE_SECRET_KEY` · `DATABASE_URL` · `OPENROUTER_API_KEY` ·
    `OPENAI_API_KEY` 중 하나라도 추가하는 순간 SEC-01이 무너진다. api와 worker가 단일
    이미지를 공유하므로(01-CONTEXT.md > D-01) api 프로세스는 worker 모듈을 물리적으로
    import 할 수 있고, 따라서 import 차단으로는 이 격리를 되찾을 수 없다. 격리는 오직
    "키를 담을 필드가 없다"로만 성립한다. 근거: 02-CONTEXT.md > D-06.

    `packages/core/tests/test_settings.py`가 이 부재를 단언하므로, 필드를 추가하면
    테스트가 red가 된다. 그 테스트를 고쳐서 통과시키지 말 것 — 그것이 방어선 자체다.
    """
