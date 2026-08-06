"""FastAPI 애플리케이션 팩토리.

관련 태스크: P0-INIT-02, P2-BE-01
설계 근거: 01-CONTEXT.md > D-13 · 02-CONTEXT.md > D-06, D-07, D-10
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from api.routers.health import router as health_router
from api.settings import ApiSettings
from nexuswiki_core.deployment import resolve_git_sha
from nexuswiki_core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: ApiSettings = app.state.settings
    configure_logging(
        environment=settings.ENVIRONMENT,
        log_level=settings.LOG_LEVEL,
    )
    app.state.http_client = httpx.AsyncClient(timeout=httpx.Timeout(2.0))
    try:
        yield
    finally:
        await app.state.http_client.aclose()


def create_app(settings: ApiSettings, *, git_sha: str | None = None) -> FastAPI:
    """주입된 설정만 보는 앱을 만든다.

    라우터는 환경이 아니라 `app.state`만 읽는다. 02-04가 여기에 라우터와 403 예외
    핸들러를 이어 등록한다 (02-CONTEXT.md > D-13의 "한 곳" 조건).
    """
    app = FastAPI(lifespan=lifespan)
    app.state.settings = settings
    app.state.git_sha = resolve_git_sha() if git_sha is None else git_sha
    app.include_router(health_router)
    return app


def build_app() -> FastAPI:
    """uvicorn 진입점 (`api.main:build_app`, factory 모드).

    ⚠️ 부팅 시점 실패가 일어나는 지점이다. 설정이 불완전하면 라우터를 세우기 전에
    `MissingSettingError`가 키 이름을 밝히며 프로세스를 죽인다. 반쯤 설정된 api가
    뜨는 것보다 안 뜨는 편이 안전하다. 근거: 02-CONTEXT.md > D-10.
    """
    return create_app(ApiSettings())
