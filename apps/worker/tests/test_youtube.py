import httpx
import pytest
from fastapi import FastAPI, HTTPException

from worker.youtube import (
    YoutubeChannelNotFound,
    YoutubeQuotaExceeded,
    YoutubeSearchRequest,
    YoutubeSearchResponse,
    YoutubeSearchService,
    YoutubeUnavailable,
    YoutubeVideoListRequest,
    YoutubeVideoListResponse,
    YoutubeVideoListService,
    add_youtube_search_route,
    add_youtube_videos_route,
    list_channel_videos,
    search_channels,
)

_INTERNAL_TOKEN = "test-internal-token"  # noqa: S105 - non-secret test fixture
_API_KEY = "test-api-key"  # noqa: S105 - non-secret test fixture


class MonotonicClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _app(service: YoutubeSearchService) -> FastAPI:
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    add_youtube_search_route(app, service)
    return app


def _search_response(**overrides: object) -> YoutubeSearchResponse:
    del overrides
    return YoutubeSearchResponse(channels=[], next_page_token=None)


# -----------------------------------------------------------------------------
# 내부 경계 — 인증이 쿼터보다 앞선다
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_private_endpoint_rejects_missing_token_before_searching() -> None:
    calls = 0

    async def search(request: YoutubeSearchRequest) -> YoutubeSearchResponse:
        nonlocal calls
        calls += 1
        return _search_response()

    app = _app(YoutubeSearchService(search, internal_token=_INTERNAL_TOKEN))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/internal/youtube-search", json={"query": "요리"})

    assert response.status_code == 401
    # 인증 실패가 업스트림 호출을 소비하면 미인증 요청으로 일일 쿼터를 태울 수 있다.
    assert calls == 0


@pytest.mark.asyncio
async def test_private_endpoint_returns_channels_for_authorized_caller() -> None:
    async def search(request: YoutubeSearchRequest) -> YoutubeSearchResponse:
        assert request.query == "요리"
        assert request.region_code == "KR"
        return YoutubeSearchResponse(
            channels=[
                {
                    "channel_id": "UC123",
                    "title": "쿠킹",
                    "description": "요리 채널",
                    "thumbnail_url": "https://i.ytimg.com/x.jpg",
                }  # type: ignore[list-item]
            ],
            next_page_token="NEXT",  # noqa: S106 - 페이지 토큰은 자격증명이 아니다
        )

    app = _app(YoutubeSearchService(search, internal_token=_INTERNAL_TOKEN))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/internal/youtube-search",
            json={"query": "요리"},
            headers={"authorization": f"Bearer {_INTERNAL_TOKEN}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["channels"][0]["channel_id"] == "UC123"
    assert body["next_page_token"] == "NEXT"  # noqa: S105 - 페이지 토큰


@pytest.mark.asyncio
async def test_quota_exhaustion_is_distinguishable_from_other_failures() -> None:
    async def search(request: YoutubeSearchRequest) -> YoutubeSearchResponse:
        raise YoutubeQuotaExceeded

    service = YoutubeSearchService(search, internal_token=_INTERNAL_TOKEN)
    with pytest.raises(HTTPException) as excinfo:
        await service.search(YoutubeSearchRequest(query="요리"), f"Bearer {_INTERNAL_TOKEN}")

    # ⚠️ 쿼터 소진은 502(일반 업스트림 실패)로 뭉개지면 안 된다 — 사용자에게 설명해야
    #    하는 유일한 업스트림 실패다.
    assert excinfo.value.status_code == 503
    assert excinfo.value.detail == "youtube_quota_exceeded"


@pytest.mark.asyncio
async def test_upstream_failure_does_not_leak_provider_detail() -> None:
    async def search(request: YoutubeSearchRequest) -> YoutubeSearchResponse:
        raise YoutubeUnavailable("key=SECRET&q=...")

    service = YoutubeSearchService(search, internal_token=_INTERNAL_TOKEN)
    with pytest.raises(HTTPException) as excinfo:
        await service.search(YoutubeSearchRequest(query="요리"), f"Bearer {_INTERNAL_TOKEN}")

    assert excinfo.value.status_code == 502
    assert excinfo.value.detail == "youtube_unavailable"
    assert "SECRET" not in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_rate_limit_reserves_before_calling_upstream() -> None:
    calls = 0

    async def search(request: YoutubeSearchRequest) -> YoutubeSearchResponse:
        nonlocal calls
        calls += 1
        return _search_response()

    clock = MonotonicClock()
    service = YoutubeSearchService(
        search,
        internal_token=_INTERNAL_TOKEN,
        rate_capacity=1,
        refill_tokens_per_second=1.0,
        monotonic=clock,
    )
    await service.search(YoutubeSearchRequest(query="요리"), f"Bearer {_INTERNAL_TOKEN}")

    with pytest.raises(HTTPException) as excinfo:
        await service.search(YoutubeSearchRequest(query="요리"), f"Bearer {_INTERNAL_TOKEN}")
    assert excinfo.value.status_code == 429
    assert calls == 1

    clock.advance(1.0)
    await service.search(YoutubeSearchRequest(query="요리"), f"Bearer {_INTERNAL_TOKEN}")
    assert calls == 2


@pytest.mark.asyncio
async def test_blank_query_is_rejected_without_consuming_quota() -> None:
    calls = 0

    async def search(request: YoutubeSearchRequest) -> YoutubeSearchResponse:
        nonlocal calls
        calls += 1
        return _search_response()

    service = YoutubeSearchService(search, internal_token=_INTERNAL_TOKEN)
    with pytest.raises(HTTPException) as excinfo:
        await service.search(YoutubeSearchRequest(query="   "), f"Bearer {_INTERNAL_TOKEN}")

    assert excinfo.value.status_code == 422
    assert calls == 0


# -----------------------------------------------------------------------------
# 업스트림 파싱 — 403의 두 얼굴을 구분한다
# -----------------------------------------------------------------------------


def _client(handler: object) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_search_channels_parses_items_and_next_page_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["type"] == "channel"
        assert request.url.params["regionCode"] == "KR"
        assert request.url.params["pageToken"] == "PAGE2"
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": {"channelId": "UC1"},
                        "snippet": {
                            "title": "채널1",
                            "description": "설명",
                            "thumbnails": {"medium": {"url": "https://i/1.jpg"}},
                        },
                    },
                    # id가 깨진 항목 하나가 나머지 결과를 버리게 하면 안 된다.
                    {"id": {}, "snippet": {"title": "깨짐"}},
                ],
                "nextPageToken": "PAGE3",
            },
        )

    async with _client(handler) as client:
        result = await search_channels(
            client,
            api_key=_API_KEY,
            query="요리",
            region_code="KR",
            page_token="PAGE2",  # noqa: S106 - 페이지 토큰
            timeout_seconds=5.0,
        )

    assert [c.channel_id for c in result.channels] == ["UC1"]
    assert result.channels[0].thumbnail_url == "https://i/1.jpg"
    assert result.next_page_token == "PAGE3"  # noqa: S105 - 페이지 토큰


@pytest.mark.asyncio
async def test_quota_exceeded_403_is_not_confused_with_invalid_key_403() -> None:
    def quota_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"errors": [{"reason": "quotaExceeded"}]}})

    async with _client(quota_handler) as client:
        with pytest.raises(YoutubeQuotaExceeded):
            await search_channels(
                client,
                api_key=_API_KEY,
                query="요리",
                region_code="KR",
                page_token=None,
                timeout_seconds=5.0,
            )

    def key_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"errors": [{"reason": "keyInvalid"}]}})

    # ⚠️ 키 설정 실수가 "오늘 쿼터를 다 썼다"로 위장되면 배포 문제를 영원히 못 찾는다.
    async with _client(key_handler) as client:
        with pytest.raises(YoutubeUnavailable):
            await search_channels(
                client,
                api_key=_API_KEY,
                query="요리",
                region_code="KR",
                page_token=None,
                timeout_seconds=5.0,
            )


@pytest.mark.asyncio
async def test_transport_error_becomes_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    async with _client(handler) as client:
        with pytest.raises(YoutubeUnavailable):
            await search_channels(
                client,
                api_key=_API_KEY,
                query="요리",
                region_code="KR",
                page_token=None,
                timeout_seconds=5.0,
            )


# -----------------------------------------------------------------------------
# 영상 목록 — design D4 (`search.list` 금지)
# -----------------------------------------------------------------------------


def _videos_handler(
    *,
    uploads: str | None = "UU1",
    playlist_ids: tuple[str, ...] = ("v1", "v2"),
    next_page_token: str | None = None,
    detail_items: list[dict[str, object]] | None = None,
    seen: dict[str, httpx.URL] | None = None,
) -> object:
    """세 업스트림 호출을 경로로 갈라 받는 MockTransport 핸들러."""
    if detail_items is None:
        detail_items = [
            {
                "id": video_id,
                "snippet": {
                    "title": f"영상 {video_id}",
                    "publishedAt": "2026-01-02T03:04:05Z",
                    "thumbnails": {"medium": {"url": f"https://i/{video_id}.jpg"}},
                },
                "contentDetails": {"duration": "PT12M34S"},
            }
            for video_id in playlist_ids
        ]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if seen is not None:
            seen[path] = request.url
        # ⚠️ `search.list`가 이 경로에서 불리면 목록 한 페이지가 3유닛이 아니라
        #    100유닛이 된다 — design D4가 금지한 바로 그 형태다.
        assert not path.endswith("/search"), "영상 목록은 search.list를 쓰지 않는다"
        if path.endswith("/channels"):
            items: list[dict[str, object]] = []
            if uploads is not None:
                items = [{"contentDetails": {"relatedPlaylists": {"uploads": uploads}}}]
            return httpx.Response(200, json={"items": items})
        if path.endswith("/playlistItems"):
            body: dict[str, object] = {
                "items": [{"contentDetails": {"videoId": v}} for v in playlist_ids]
            }
            if next_page_token:
                body["nextPageToken"] = next_page_token
            return httpx.Response(200, json=body)
        if path.endswith("/videos"):
            return httpx.Response(200, json={"items": detail_items})
        raise AssertionError(f"예상하지 못한 업스트림 경로: {path}")

    return handler


@pytest.mark.asyncio
async def test_list_channel_videos_pages_uploads_playlist_without_search_list() -> None:
    seen: dict[str, httpx.URL] = {}

    async with _client(_videos_handler(next_page_token="PAGE2", seen=seen)) as client:  # noqa: S106
        result = await list_channel_videos(
            client,
            api_key=_API_KEY,
            channel_id="UC1",
            page_token=None,
            timeout_seconds=5.0,
        )

    assert [v.video_id for v in result.videos] == ["v1", "v2"]
    assert result.videos[0].duration_seconds == 12 * 60 + 34
    assert result.videos[0].published_at == "2026-01-02T03:04:05Z"
    assert result.videos[0].thumbnail_url == "https://i/v1.jpg"
    assert result.next_page_token == "PAGE2"  # noqa: S105 - 페이지 토큰
    # uploads 재생목록으로 페이징한다 — 채널 id를 playlistId에 그대로 넣지 않는다.
    assert seen["/youtube/v3/playlistItems"].params["playlistId"] == "UU1"


@pytest.mark.asyncio
async def test_video_page_token_is_forwarded_to_playlist_items() -> None:
    seen: dict[str, httpx.URL] = {}

    async with _client(_videos_handler(seen=seen)) as client:
        await list_channel_videos(
            client,
            api_key=_API_KEY,
            channel_id="UC1",
            page_token="PAGE2",  # noqa: S106 - 페이지 토큰
            timeout_seconds=5.0,
        )

    assert seen["/youtube/v3/playlistItems"].params["pageToken"] == "PAGE2"
    # ⚠️ 페이지 토큰이 `channels.list`로 새면 매 페이지가 다른 재생목록을 가리킬 수 있다.
    assert "pageToken" not in seen["/youtube/v3/channels"].params


@pytest.mark.asyncio
async def test_videos_missing_from_detail_response_are_dropped() -> None:
    # 비공개·삭제된 영상은 `videos.list` 응답에 오지 않는다. 목록에 남기면 사용자가
    # 자막을 절대 얻을 수 없는 영상을 고르게 된다.
    handler = _videos_handler(
        playlist_ids=("v1", "gone", "v2"),
        detail_items=[
            {"id": "v2", "snippet": {"title": "둘"}, "contentDetails": {"duration": "PT1M"}},
            {"id": "v1", "snippet": {"title": "하나"}, "contentDetails": {"duration": "PT2M"}},
        ],
    )
    async with _client(handler) as client:
        result = await list_channel_videos(
            client, api_key=_API_KEY, channel_id="UC1", page_token=None, timeout_seconds=5.0
        )

    # ⚠️ 순서의 기준은 `playlistItems`(업로드 순)이지 `videos.list` 응답 순서가 아니다.
    assert [v.video_id for v in result.videos] == ["v1", "v2"]


@pytest.mark.asyncio
async def test_unreadable_duration_is_none_not_zero() -> None:
    handler = _videos_handler(
        playlist_ids=("v1",),
        detail_items=[{"id": "v1", "snippet": {"title": "라이브"}, "contentDetails": {}}],
    )
    async with _client(handler) as client:
        result = await list_channel_videos(
            client, api_key=_API_KEY, channel_id="UC1", page_token=None, timeout_seconds=5.0
        )

    # 0초는 "길이를 모른다"가 아니라 "빈 영상"으로 읽힌다.
    assert result.videos[0].duration_seconds is None


@pytest.mark.asyncio
async def test_missing_channel_is_not_reported_as_empty_video_list() -> None:
    async with _client(_videos_handler(uploads=None)) as client:
        with pytest.raises(YoutubeChannelNotFound):
            await list_channel_videos(
                client, api_key=_API_KEY, channel_id="UC1", page_token=None, timeout_seconds=5.0
            )


@pytest.mark.asyncio
async def test_empty_page_skips_detail_call_and_keeps_continuation() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path.endswith("/channels"):
            return httpx.Response(
                200,
                json={"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]},
            )
        if request.url.path.endswith("/playlistItems"):
            return httpx.Response(200, json={"items": [], "nextPageToken": "PAGE2"})
        raise AssertionError("빈 페이지에서 videos.list를 부를 이유가 없다")

    async with _client(handler) as client:
        result = await list_channel_videos(
            client, api_key=_API_KEY, channel_id="UC1", page_token=None, timeout_seconds=5.0
        )

    assert result.videos == []
    assert result.next_page_token == "PAGE2"  # noqa: S105 - 페이지 토큰
    assert "/youtube/v3/videos" not in calls


@pytest.mark.asyncio
async def test_video_quota_exhaustion_stays_distinguishable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"errors": [{"reason": "quotaExceeded"}]}})

    async with _client(handler) as client:
        with pytest.raises(YoutubeQuotaExceeded):
            await list_channel_videos(
                client, api_key=_API_KEY, channel_id="UC1", page_token=None, timeout_seconds=5.0
            )


# -----------------------------------------------------------------------------
# 영상 목록 리스너 — 검색과 같은 관문, 다른 예산
# -----------------------------------------------------------------------------


def _videos_app(service: YoutubeVideoListService) -> FastAPI:
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    add_youtube_videos_route(app, service)
    return app


@pytest.mark.asyncio
async def test_video_listener_rejects_missing_token_before_calling_upstream() -> None:
    calls = 0

    async def list_videos(request: YoutubeVideoListRequest) -> YoutubeVideoListResponse:
        nonlocal calls
        calls += 1
        return YoutubeVideoListResponse(videos=[], next_page_token=None)

    app = _videos_app(YoutubeVideoListService(list_videos, internal_token=_INTERNAL_TOKEN))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/internal/youtube-videos", json={"channel_id": "UC1"})

    assert response.status_code == 401
    assert calls == 0


@pytest.mark.asyncio
async def test_video_listener_maps_missing_channel_to_404() -> None:
    async def list_videos(request: YoutubeVideoListRequest) -> YoutubeVideoListResponse:
        raise YoutubeChannelNotFound

    service = YoutubeVideoListService(list_videos, internal_token=_INTERNAL_TOKEN)
    with pytest.raises(HTTPException) as excinfo:
        await service.list_videos(
            YoutubeVideoListRequest(channel_id="UC1"), f"Bearer {_INTERNAL_TOKEN}"
        )

    # ⚠️ 502(업스트림 장애)로 뭉개면 "다른 채널을 고르라"와 "잠시 후 재시도하라"가
    #    한 문구로 합쳐진다.
    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "youtube_channel_not_found"


@pytest.mark.asyncio
async def test_video_listener_has_its_own_rate_budget() -> None:
    search_calls = 0
    video_calls = 0

    async def search(request: YoutubeSearchRequest) -> YoutubeSearchResponse:
        nonlocal search_calls
        search_calls += 1
        return _search_response()

    async def list_videos(request: YoutubeVideoListRequest) -> YoutubeVideoListResponse:
        nonlocal video_calls
        video_calls += 1
        return YoutubeVideoListResponse(videos=[], next_page_token=None)

    clock = MonotonicClock()
    search_service = YoutubeSearchService(
        search,
        internal_token=_INTERNAL_TOKEN,
        rate_capacity=1,
        refill_tokens_per_second=1.0,
        monotonic=clock,
    )
    video_service = YoutubeVideoListService(
        list_videos,
        internal_token=_INTERNAL_TOKEN,
        rate_capacity=1,
        refill_tokens_per_second=1.0,
        monotonic=clock,
    )

    # 목록 호출이 검색 예산을 태우면 3유닛짜리 페이징이 100유닛짜리 검색을 굶긴다.
    await video_service.list_videos(
        YoutubeVideoListRequest(channel_id="UC1"), f"Bearer {_INTERNAL_TOKEN}"
    )
    await search_service.search(YoutubeSearchRequest(query="요리"), f"Bearer {_INTERNAL_TOKEN}")

    assert search_calls == 1
    assert video_calls == 1


@pytest.mark.asyncio
async def test_blank_channel_id_is_rejected_without_consuming_quota() -> None:
    calls = 0

    async def list_videos(request: YoutubeVideoListRequest) -> YoutubeVideoListResponse:
        nonlocal calls
        calls += 1
        return YoutubeVideoListResponse(videos=[], next_page_token=None)

    service = YoutubeVideoListService(list_videos, internal_token=_INTERNAL_TOKEN)
    with pytest.raises(HTTPException) as excinfo:
        await service.list_videos(
            YoutubeVideoListRequest(channel_id="   "), f"Bearer {_INTERNAL_TOKEN}"
        )

    assert excinfo.value.status_code == 422
    assert calls == 0
