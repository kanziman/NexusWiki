"""프로세스 생존 여부만 노출하는 liveness 라우터.

관련 태스크: P0-INIT-02
설계 근거: 01-SPEC.md > R6
"""

import os
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from api.health_check import check_db_roundtrip

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "git_sha": os.environ.get(
            "RAILWAY_GIT_COMMIT_SHA", os.environ.get("GIT_SHA", "unknown")
        ),
    }


@router.get("/health/ready", response_model=None)
async def ready(request: Request) -> dict[str, Any] | JSONResponse:
    required_env = ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY")
    for key in required_env:
        if not os.environ.get(key):
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": f"missing_env:{key}"},
            )

    result = await check_db_roundtrip(
        request.app.state.http_client,
        supabase_url=os.environ["SUPABASE_URL"],
        publishable_key=os.environ["SUPABASE_PUBLISHABLE_KEY"],
    )
    if result.ok:
        return {"status": "ready", "elapsed_ms": result.elapsed_ms}
    return JSONResponse(
        status_code=503,
        content={
            "status": "not_ready",
            "reason": result.reason,
            "elapsed_ms": result.elapsed_ms,
        },
    )
