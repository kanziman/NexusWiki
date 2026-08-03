"""프로세스 생존 여부만 노출하는 liveness 라우터.

관련 태스크: P0-INIT-02
설계 근거: 01-SPEC.md > R6
"""

import os

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "git_sha": os.environ.get(
            "RAILWAY_GIT_COMMIT_SHA", os.environ.get("GIT_SHA", "unknown")
        ),
    }
