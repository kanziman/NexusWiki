"""youtube-channel-import 슬라이스 1·2 — 채널 검색·영상 목록 경계의 회귀.

⚠️ 멤버십 게이트는 로컬 스택 픽스처를 쓰므로 스택이 없으면 skip된다. 캐시와 업스트림
사유 매핑은 스택 없이도 항상 돌아야 하는 순수 로직이라 아래쪽에 따로 둔다.
"""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi import status

from api.errors import (
    FORBIDDEN_BODY,
    YoutubeChannelNotFound,
    YoutubeQuotaExceeded,
    YoutubeUnavailable,
)
from api.routers.youtube import SearchCache, _call_worker_search, _call_worker_videos

SEARCH_PATH = "/workspaces/{workspace_id}/youtube/channels"
VIDEOS_PATH = "/workspaces/{workspace_id}/youtube/channels/{channel_id}/videos"


# -----------------------------------------------------------------------------
# 캐시 — 쿼터 보존 계약 (spec: Search quota conservation)
# -----------------------------------------------------------------------------


def test_cache_returns_stored_payload_within_ttl() -> None:
    cache = SearchCache(ttl_seconds=10.0, max_entries=4)
    key = ("요리", "KR", "", "relevance", "")
    cache.put(key, {"channels": [], "next_page_token": None}, now=100.0)

    assert cache.get(key, now=105.0) is not None


def test_cache_entry_expires_after_ttl() -> None:
    cache = SearchCache(ttl_seconds=10.0, max_entries=4)
    key = ("요리", "KR", "", "relevance", "")
    cache.put(key, {"channels": []}, now=100.0)

    assert cache.get(key, now=111.0) is None


def test_cache_distinguishes_query_region_and_page_token() -> None:
    cache = SearchCache(ttl_seconds=10.0, max_entries=8)
    cache.put(("요리", "KR", "", "relevance", ""), {"channels": ["a"]}, now=0.0)

    # ⚠️ 다섯 축 중 하나라도 키에서 빠지면 다른 검색 결과가 서로를 덮어쓴다.
    assert cache.get(("요리", "US", "", "relevance", ""), now=1.0) is None
    assert cache.get(("요리", "KR", "PAGE2", "relevance", ""), now=1.0) is None
    assert cache.get(("베이킹", "KR", "", "relevance", ""), now=1.0) is None


def test_cache_distinguishes_order_and_relevance_language() -> None:
    cache = SearchCache(ttl_seconds=10.0, max_entries=8)
    cache.put(("요리", "KR", "", "relevance", ""), {"channels": ["a"]}, now=0.0)

    # ⚠️ 정렬이나 언어를 바꿨는데 캐시가 이전 조합의 결과를 그대로 돌려주면
    #    사용자에게는 "바꿨는데 안 바뀜"으로 보이는 조용한 실패다.
    assert cache.get(("요리", "KR", "", "videoCount", ""), now=1.0) is None
    assert cache.get(("요리", "KR", "", "relevance", "ko"), now=1.0) is None


def test_cache_evicts_least_recently_used_entry() -> None:
    cache = SearchCache(ttl_seconds=100.0, max_entries=2)
    cache.put(("a", "KR", "", "relevance", ""), {"channels": []}, now=0.0)
    cache.put(("b", "KR", "", "relevance", ""), {"channels": []}, now=1.0)
    cache.get(("a", "KR", "", "relevance", ""), now=2.0)  # a를 최근 사용으로 올린다
    cache.put(("c", "KR", "", "relevance", ""), {"channels": []}, now=3.0)

    assert cache.get(("a", "KR", "", "relevance", ""), now=4.0) is not None
    assert cache.get(("b", "KR", "", "relevance", ""), now=4.0) is None
    assert cache.get(("c", "KR", "", "relevance", ""), now=4.0) is not None


# -----------------------------------------------------------------------------
# 업스트림 사유 매핑 — 쿼터 소진이 다른 실패로 뭉개지지 않는다
# -----------------------------------------------------------------------------


def _request(handler: Callable[[httpx.Request], httpx.Response], **setting_overrides: Any) -> Any:
    values: dict[str, Any] = {
        "YOUTUBE_SEARCH_INTERNAL_URL": "http://worker.internal:8081",
        "YOUTUBE_SEARCH_INTERNAL_TOKEN": "internal-token",
        "YOUTUBE_SEARCH_TIMEOUT_SECONDS": 5.0,
        "YOUTUBE_VIDEOS_TIMEOUT_SECONDS": 8.0,
    }
    values.update(setting_overrides)
    settings = SimpleNamespace(**values)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(settings=settings, http_client=client))
    )


@pytest.mark.asyncio
async def test_worker_quota_status_maps_to_quota_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "youtube_quota_exceeded"})

    with pytest.raises(YoutubeQuotaExceeded):
        await _call_worker_search(
            _request(handler), query="요리", region_code="KR", page_token=None
        )


@pytest.mark.asyncio
async def test_other_worker_errors_map_to_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, json={"detail": "youtube_unavailable"})

    with pytest.raises(YoutubeUnavailable):
        await _call_worker_search(
            _request(handler), query="요리", region_code="KR", page_token=None
        )


@pytest.mark.asyncio
async def test_missing_internal_config_is_not_reported_as_quota_exhaustion() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - 도달하면 안 된다
        raise AssertionError("설정이 없으면 업스트림을 부르지 않아야 한다")

    # ⚠️ 배포 설정 누락이 "오늘 쿼터를 다 썼다"로 위장되면 원인을 영원히 못 찾는다.
    with pytest.raises(YoutubeUnavailable):
        await _call_worker_search(
            _request(handler, YOUTUBE_SEARCH_INTERNAL_TOKEN=None),
            query="요리",
            region_code="KR",
            page_token=None,
        )


@pytest.mark.asyncio
async def test_transport_failure_maps_to_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    with pytest.raises(YoutubeUnavailable):
        await _call_worker_search(
            _request(handler), query="요리", region_code="KR", page_token=None
        )


@pytest.mark.asyncio
async def test_worker_receives_query_region_and_page_token() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        seen.update(json.loads(request.content))
        assert request.headers["authorization"] == "Bearer internal-token"
        return httpx.Response(200, json={"channels": [], "next_page_token": None})

    await _call_worker_search(
        _request(handler),
        query="요리",
        region_code="KR",
        page_token="PAGE2",  # noqa: S106 - 페이지 토큰은 자격증명이 아니다
    )
    assert seen == {
        "query": "요리",
        "region_code": "KR",
        "page_token": "PAGE2",
        "order": "relevance",
        "relevance_language": None,
    }


@pytest.mark.asyncio
async def test_worker_receives_order_and_relevance_language() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"channels": [], "next_page_token": None})

    await _call_worker_search(
        _request(handler),
        query="요리",
        region_code="KR",
        page_token=None,
        order="videoCount",
        relevance_language="ko",
    )
    assert seen["order"] == "videoCount"
    assert seen["relevance_language"] == "ko"


# -----------------------------------------------------------------------------
# 영상 목록 프록시 — 404의 두 얼굴을 구분한다
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_worker_receives_channel_id_and_page_token() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        assert request.url.path == "/internal/youtube-videos"
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"videos": [], "next_page_token": None})

    await _call_worker_videos(
        _request(handler),
        channel_id="UC1",
        page_token="PAGE2",  # noqa: S106 - 페이지 토큰은 자격증명이 아니다
    )
    assert seen == {"channel_id": "UC1", "page_token": "PAGE2"}


@pytest.mark.asyncio
async def test_worker_channel_not_found_maps_to_its_own_reason() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "youtube_channel_not_found"})

    with pytest.raises(YoutubeChannelNotFound):
        await _call_worker_videos(_request(handler), channel_id="UC1", page_token=None)


@pytest.mark.asyncio
async def test_gateway_503_without_the_token_is_not_reported_as_quota_exhaustion() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        # 워커 앞의 프록시·로드밸런서가 내는 503이다. ⚠️ 이것을 쿼터 소진으로 읽으면
        # 워커 장애가 "내일 다시 시도하세요"로 위장되고 원인을 영원히 못 찾는다.
        return httpx.Response(503, text="upstream connect error")

    with pytest.raises(YoutubeUnavailable):
        await _call_worker_videos(_request(handler), channel_id="UC1", page_token=None)


@pytest.mark.asyncio
async def test_unregistered_route_404_is_not_reported_as_missing_channel() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        # `YOUTUBE_API_KEY`가 없으면 워커가 이 라우트를 등록하지 않아 FastAPI의 기본
        # 404가 온다. ⚠️ 이것을 "채널이 삭제됐다"로 읽으면 배포 설정 누락이 사용자에게
        # 채널 문제로 위장된다.
        return httpx.Response(404, json={"detail": "Not Found"})

    with pytest.raises(YoutubeUnavailable):
        await _call_worker_videos(_request(handler), channel_id="UC1", page_token=None)


@pytest.mark.asyncio
async def test_video_quota_exhaustion_stays_distinguishable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "youtube_quota_exceeded"})

    with pytest.raises(YoutubeQuotaExceeded):
        await _call_worker_videos(_request(handler), channel_id="UC1", page_token=None)


# -----------------------------------------------------------------------------
# 워크스페이스 경계 — 로컬 스택 필요
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_requires_credentials(
    two_workspaces_two_users: tuple[Any, ...], authed_client: Callable[..., Any]
) -> None:
    owner, _ = two_workspaces_two_users
    async with authed_client(None) as client:
        response = await client.get(
            SEARCH_PATH.format(workspace_id=owner.workspace_id), params={"q": "요리"}
        )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_non_member_cannot_consume_shared_search_quota(
    two_workspaces_two_users: tuple[Any, ...], authed_client: Callable[..., Any]
) -> None:
    owner, outsider = two_workspaces_two_users
    async with authed_client(outsider) as client:
        response = await client.get(
            SEARCH_PATH.format(workspace_id=owner.workspace_id), params={"q": "요리"}
        )

    # ⚠️ 이 경로는 DB를 읽지 않아 RLS가 저절로 막아주지 않는다. 403이 아니라 200이
    #    나오면 비멤버가 워크스페이스 id만으로 서비스 공용 쿼터를 태울 수 있다.
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == FORBIDDEN_BODY


@pytest.mark.asyncio
async def test_unknown_workspace_is_forbidden_not_found(
    two_workspaces_two_users: tuple[Any, ...], authed_client: Callable[..., Any]
) -> None:
    owner, _ = two_workspaces_two_users
    async with authed_client(owner) as client:
        response = await client.get(SEARCH_PATH.format(workspace_id=uuid4()), params={"q": "요리"})
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_non_member_cannot_list_channel_videos(
    two_workspaces_two_users: tuple[Any, ...], authed_client: Callable[..., Any]
) -> None:
    owner, outsider = two_workspaces_two_users
    async with authed_client(outsider) as client:
        response = await client.get(
            VIDEOS_PATH.format(workspace_id=owner.workspace_id, channel_id="UC1")
        )

    # ⚠️ 검색과 같은 이유다 — 이 경로도 DB를 읽지 않아 RLS가 저절로 막아주지 않는다.
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == FORBIDDEN_BODY
