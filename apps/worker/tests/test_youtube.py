import httpx
import pytest
from fastapi import FastAPI, HTTPException

from worker.youtube import (
    YoutubeQuotaExceeded,
    YoutubeSearchRequest,
    YoutubeSearchResponse,
    YoutubeSearchService,
    YoutubeUnavailable,
    add_youtube_search_route,
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
