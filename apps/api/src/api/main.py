"""FastAPI 애플리케이션 팩토리.

관련 태스크: P0-INIT-02, P2-BE-01
설계 근거: 01-CONTEXT.md > D-13 · 02-CONTEXT.md > D-06, D-07, D-10
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import errors
from api.routers.ask import router as ask_router
from api.routers.graph import router as graph_router
from api.routers.health import router as health_router
from api.routers.jobs import router as jobs_router
from api.routers.retrieval import router as retrieval_router
from api.routers.sources import router as sources_router
from api.routers.wiki import router as wiki_router
from api.routers.workspaces import router as workspaces_router
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

    라우터는 환경이 아니라 `app.state`만 읽는다. 격리 예외의 등록 지점은 아래 한 줄이
    전부이며 02-04의 라우터는 상태 코드를 직접 다루지 않는다 (02-CONTEXT.md > D-13의
    "한 곳" 조건).
    """
    app = FastAPI(lifespan=lifespan)
    app.state.settings = settings
    app.state.git_sha = resolve_git_sha() if git_sha is None else git_sha
    # ⚠️ Authorization 헤더(요청자 JWT)를 브라우저가 보내려면 allow_credentials=True와
    # 명시적 origin 목록이 둘 다 필요하다 — allow_origins=["*"]는 credentials와
    # 동시에 쓸 수 없다(브라우저가 거부). CORS_ALLOWED_ORIGINS 참조.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip() for origin in settings.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Ask-Thread-Id"],
    )
    errors.register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(workspaces_router)
    # ⚠️ `app.state.http_client`의 타임아웃 2.0초는 그대로 둔다. 이 라우터의 PostgREST
    #    왕복은 전부 그 안에 들어야 하며 LLM 호출은 워커의 일이다 — 여기서 전역
    #    타임아웃을 늘려야 한다면 그것은 블로킹 작업이 라우터로 새어 들어왔다는 신호다
    #    (ING-01).
    #    유일한 예외는 Storage 업로드이고, 그것은 전역값이 아니라 호출 단위 상한으로
    #    분리되어 있다(`api.storage.UPLOAD_TIMEOUT_SECONDS`). 예외일 수 있는 이유는 그
    #    왕복의 최악값이 `MAX_UPLOAD_BYTES`로 미리 유한하게 잘려 있기 때문이다.
    app.include_router(sources_router)
    app.include_router(jobs_router)
    app.include_router(retrieval_router)
    app.include_router(ask_router)
    app.include_router(graph_router)
    app.include_router(wiki_router)
    return app


def build_app() -> FastAPI:
    """uvicorn 진입점 (`api.main:build_app`, factory 모드).

    ⚠️ 부팅 시점 실패가 일어나는 지점이다. 설정이 불완전하면 라우터를 세우기 전에
    `MissingSettingError`가 키 이름을 밝히며 프로세스를 죽인다. 반쯤 설정된 api가
    뜨는 것보다 안 뜨는 편이 안전하다. 근거: 02-CONTEXT.md > D-10.
    """
    return create_app(ApiSettings())
