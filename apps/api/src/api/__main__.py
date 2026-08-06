"""Railway API 프로세스 진입점.

관련 태스크: P0-INIT-02, P2-BE-01
설계 근거: 01-CONTEXT.md > D-03 (exec form CMD + 프로그래밍 방식 uvicorn — SIGTERM 전달)
          · 02-CONTEXT.md > D-07 (진입 경로는 환경을 직접 읽지 않는다)

⚠️ shell을 끼우면 shell이 PID 1이 되어 SIGTERM이 자식에게 전달되지 않는다.
이 실패는 재배포 시 잡 유실로만 나타나므로 Python 프로세스를 직접 실행한다.
"""

import uvicorn

from nexuswiki_core.deployment import resolve_port

if __name__ == "__main__":
    # factory 모드를 쓰는 이유: 모듈 로드 시점에 앱을 즉시 만들면 `api.main`을 import
    # 하는 것만으로 프로덕션 환경 전체가 요구된다. 설정 구성은 기동 시점에만 일어난다.
    uvicorn.run(
        "api.main:build_app",
        factory=True,
        host="0.0.0.0",
        port=resolve_port(),
        log_config=None,
    )
