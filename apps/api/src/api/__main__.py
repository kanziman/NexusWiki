"""Railway API 프로세스 진입점.

관련 태스크: P0-INIT-02
설계 근거: 01-CONTEXT.md > D-03 (exec form CMD + 프로그래밍 방식 uvicorn — SIGTERM 전달)

⚠️ shell을 끼우면 shell이 PID 1이 되어 SIGTERM이 자식에게 전달되지 않는다.
이 실패는 재배포 시 잡 유실로만 나타나므로 Python 프로세스를 직접 실행한다.
"""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        log_config=None,
    )
