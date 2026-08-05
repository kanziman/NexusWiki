"""FastAPI 애플리케이션 팩토리.

관련 태스크: P0-INIT-02
설계 근거: 01-CONTEXT.md > D-13
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from api.routers.health import router as health_router
from nexuswiki_core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(
        environment=os.environ.get("ENVIRONMENT", "development"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
    app.state.http_client = httpx.AsyncClient(timeout=httpx.Timeout(2.0))
    try:
        yield
    finally:
        await app.state.http_client.aclose()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.include_router(health_router)
    return app


app = create_app()
