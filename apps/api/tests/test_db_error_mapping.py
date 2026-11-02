"""PostgREST 오류의 HTTP 매핑. 위조 토큰과 격리 위반, 진짜 장애가 섞이지 않아야 한다."""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from api.main import create_app
from api.settings import ApiSettings


def _settings() -> ApiSettings:
    return ApiSettings(
        SUPABASE_URL="http://supabase.test",
        SUPABASE_PUBLISHABLE_KEY="sb_publishable_test",
        ENVIRONMENT="development",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("upstream_status", "code", "expected", "detail"),
    [
        (401, "PGRST301", 401, "unauthorized"),
        (401, "PGRST303", 401, "unauthorized"),
        # 게이트웨이의 401은 JWT가 아니라 배포 설정 문제다. 재로그인 요구로 위장하면 안 된다.
        (401, None, 500, "database_error"),
        # 42501은 상태 코드와 무관하게 격리 위반이다. 익명 역할의 거부가 401로 와도 403이어야 한다.
        (401, "42501", 403, "forbidden"),
        (403, "42501", 403, "forbidden"),
        (500, "XX000", 500, "database_error"),
    ],
)
async def test_postgrest_failures_keep_distinct_responses(
    upstream_status: int, code: str | None, expected: int, detail: str
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(upstream_status, json={"code": code, "message": "secret-detail"})

    app = create_app(_settings(), git_sha="test-sha")
    async with app.router.lifespan_context(app):
        app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/workspaces/{uuid4()}/retrieval",
                json={"query": "질의"},
                headers={"Authorization": "Bearer token"},
            )
        await app.state.http_client.aclose()

    assert response.status_code == expected
    assert response.json() == {"detail": detail}


@pytest.mark.asyncio
async def test_rejected_jwt_is_not_folded_into_a_per_video_failure() -> None:
    # ⚠️ 202 안의 영상별 `failed`로 접히면 재로그인이 필요하다는 신호가 사라진다.
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"code": "PGRST301", "message": "secret-detail"})

    app = create_app(_settings(), git_sha="test-sha")
    async with app.router.lifespan_context(app):
        app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/workspaces/{uuid4()}/sources/youtube-videos",
                json={
                    "channel_id": "UC123",
                    "videos": [{"video_id": "dQw4w9WgXcQ", "title": "제목"}],
                },
                headers={"Authorization": "Bearer token"},
            )
        await app.state.http_client.aclose()

    assert response.status_code == 401, response.text
    assert response.json() == {"detail": "unauthorized"}
