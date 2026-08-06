"""프로세스 생존 여부만 노출하는 liveness 라우터.

관련 태스크: P0-INIT-02, P2-BE-01
설계 근거: 01-SPEC.md > R6 · 02-CONTEXT.md > D-07, D-10
"""

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from api.health_check import check_db_roundtrip

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    return {
        "status": "ok",
        "git_sha": request.app.state.git_sha,
    }


@router.get("/health/ready", response_model=None)
async def ready(request: Request) -> dict[str, Any] | JSONResponse:
    # ⚠️ 필수 설정 검사 루프를 여기에 되살리지 말 것. 기동 시점 검증(D-10)이 이미
    # 그 역할을 했으므로 런타임에 같은 검사를 반복하면 절대 참이 되지 않는 죽은
    # 분기가 되고, readiness가 진짜로 확인해야 할 DB 왕복을 가린다.
    settings = request.app.state.settings

    result = await check_db_roundtrip(
        request.app.state.http_client,
        supabase_url=settings.SUPABASE_URL,
        publishable_key=settings.SUPABASE_PUBLISHABLE_KEY,
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
