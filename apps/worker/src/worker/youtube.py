"""Private, worker-owned YouTube Data API boundary.

관련 태스크: openspec/changes/youtube-channel-import/tasks.md Task 1.1 · 2.1
설계 근거: 같은 change의 `design.md` > D4, D5

⚠️ YouTube API 키는 **워커만** 소유한다. `ApiSettings`에는 provider 자격증명을 담을
필드가 존재할 수 없고(SEC-01), api와 worker가 단일 이미지를 공유하므로 import 차단으로
그 격리를 되찾을 수도 없다. 그래서 검색은 여기(키를 가진 쪽)에서 일어나고 API는
내부 호출자 토큰으로 이 경계를 호출하기만 한다 — `query_embedding`·`llm_stream`과 같은
형태다.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, Final

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict

__all__ = [
    "YoutubeChannel",
    "YoutubeChannelNotFound",
    "YoutubeQuotaExceeded",
    "YoutubeSearchRequest",
    "YoutubeSearchResponse",
    "YoutubeSearchService",
    "YoutubeUnavailable",
    "YoutubeVideo",
    "YoutubeVideoListRequest",
    "YoutubeVideoListResponse",
    "YoutubeVideoListService",
    "add_youtube_search_route",
    "add_youtube_videos_route",
    "list_channel_videos",
    "search_channels",
]

MonotonicClock = Callable[[], float]

_SEARCH_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"
_CHANNELS_ENDPOINT = "https://www.googleapis.com/youtube/v3/channels"
_PLAYLIST_ITEMS_ENDPOINT = "https://www.googleapis.com/youtube/v3/playlistItems"
_VIDEOS_ENDPOINT = "https://www.googleapis.com/youtube/v3/videos"

# ⚠️ `search.list`는 호출당 100유닛이고 일일 기본 한도가 10,000유닛이다. 이 경계에서
#    한 번 새는 호출이 곧 서비스 전체의 검색 100분의 1이라, 캐시(API 쪽)와 레이트 제한
#    (여기)을 둘 다 둔다.
_MAX_RESULTS = 20

# `playlistItems.list`·`videos.list`가 한 번에 받는 상한이 둘 다 50이다. 한쪽만 50을
# 넘기면 다른 쪽에서 잘려 목록에 구멍이 나므로 둘을 같은 상수로 묶는다.
_MAX_VIDEO_RESULTS: Final[int] = 50

# `PT1H2M3S` 형태만 받는다. 정규식이 아니라 문자열 스캔으로 풀면 `P1DT…`(라이브 아카이브)
# 같은 형태에서 조용히 틀린 초를 만든다.
_ISO8601_DURATION = re.compile(
    r"^P(?:(?P<days>\d+)D)?T?(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?$"
)


class YoutubeQuotaExceeded(Exception):
    """일일 쿼터가 소진됐다.

    ⚠️ 일반 실패와 반드시 구분한다. 이것을 "결과 0건"으로 뭉개면 사용자는 검색어가
    잘못됐다고 믿고 다른 키워드로 재시도하며, 그 재시도는 쿼터가 이미 없으므로
    영원히 0건을 돌려준다 — 무엇이 왜 막혔는지가 화면에서 사라진다.
    """


class YoutubeUnavailable(Exception):
    """업스트림이 우리가 고칠 수 없는 이유로 실패했다.

    ⚠️ 응답 본문을 담을 필드를 두지 않는다. 업스트림 오류 본문에는 키가 실린 요청 URL이
    되비쳐 나올 수 있어, 그대로 올리면 그것이 그대로 노출 경로가 된다.
    """


class YoutubeChannelNotFound(Exception):
    """채널이 없거나 업로드 재생목록을 노출하지 않는다.

    ⚠️ "영상 0건"으로 뭉개지 않는다. 검색 결과에서 고른 채널이 그 사이 삭제된 경우와
    "이 채널은 영상을 아직 안 올렸다"는 사용자가 취할 다음 행동이 서로 다르고, 뭉개면
    화면에는 둘 다 빈 목록으로만 보인다 — 쿼터 소진을 0건으로 위장하지 않는 것과 같은
    이유다.
    """


class YoutubeChannel(BaseModel):
    """검색 결과 한 건 — 채널을 고르는 데 필요한 것만 담는다."""

    channel_id: str
    title: str
    description: str
    thumbnail_url: str | None


class YoutubeSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str
    region_code: str = "KR"
    page_token: str | None = None


class YoutubeSearchResponse(BaseModel):
    channels: list[YoutubeChannel]
    next_page_token: str | None = None


class YoutubeVideo(BaseModel):
    """영상 한 건 — 주제 관련성을 사람이 판단하는 데 필요한 것만 담는다."""

    video_id: str
    title: str
    published_at: str | None
    duration_seconds: int | None
    thumbnail_url: str | None


class YoutubeVideoListRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    channel_id: str
    page_token: str | None = None


class YoutubeVideoListResponse(BaseModel):
    videos: list[YoutubeVideo]
    next_page_token: str | None = None


def _parse_thumbnail(snippet: dict[str, Any]) -> str | None:
    thumbnails = snippet.get("thumbnails")
    if not isinstance(thumbnails, dict):
        return None
    for size in ("medium", "default", "high"):
        entry = thumbnails.get(size)
        if isinstance(entry, dict) and isinstance(entry.get("url"), str):
            return str(entry["url"])
    return None


def _is_quota_error(payload: dict[str, Any]) -> bool:
    """403 본문에서 쿼터 소진을 다른 403(잘못된 키·차단된 키)과 구분한다.

    ⚠️ 상태 코드만으로 판정하면 안 된다. `quotaExceeded`와 `keyInvalid`가 같은 403으로
    오고, 둘을 뭉개면 키 설정 실수가 "오늘 쿼터를 다 썼다"는 안내로 위장된다.
    """
    error = payload.get("error")
    if not isinstance(error, dict):
        return False
    for item in error.get("errors") or []:
        if isinstance(item, dict) and item.get("reason") in {
            "quotaExceeded",
            "dailyLimitExceeded",
            "rateLimitExceeded",
        }:
            return True
    return False


async def _get_json(
    client: httpx.AsyncClient,
    endpoint: str,
    *,
    params: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Data API 호출 하나를 사유 두 갈래로만 접어서 돌려준다.

    ⚠️ 실패 사유를 여기 한 곳에 모으는 것이 계약이다. 호출부마다 403을 따로 해석하면
    `quotaExceeded`와 `keyInvalid`를 구분하는 판정이 엔드포인트 수만큼 복제되고, 그중
    하나만 갱신을 놓쳐도 그 경로에서 배포 설정 실수가 "쿼터 소진"으로 위장된다.
    """
    try:
        response = await client.get(endpoint, params=params, timeout=timeout_seconds)
    except httpx.HTTPError as error:
        raise YoutubeUnavailable from error

    if response.status_code == 403:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if isinstance(payload, dict) and _is_quota_error(payload):
            raise YoutubeQuotaExceeded
        raise YoutubeUnavailable
    if response.status_code >= 400:
        raise YoutubeUnavailable

    try:
        body = response.json()
    except ValueError as error:
        raise YoutubeUnavailable from error
    if not isinstance(body, dict):
        raise YoutubeUnavailable
    return body


async def search_channels(
    client: httpx.AsyncClient,
    *,
    api_key: str,
    query: str,
    region_code: str,
    page_token: str | None,
    timeout_seconds: float,
) -> YoutubeSearchResponse:
    """`search.list`로 채널 후보를 읽는다. 클라이언트는 주입받는다."""
    params: dict[str, Any] = {
        "part": "snippet",
        "type": "channel",
        "q": query,
        "maxResults": _MAX_RESULTS,
        "regionCode": region_code,
        "key": api_key,
    }
    if page_token:
        params["pageToken"] = page_token

    body = await _get_json(client, _SEARCH_ENDPOINT, params=params, timeout_seconds=timeout_seconds)

    channels: list[YoutubeChannel] = []
    for item in body.get("items") or []:
        if not isinstance(item, dict):
            continue
        snippet = item.get("snippet")
        identifier = item.get("id")
        channel_id = identifier.get("channelId") if isinstance(identifier, dict) else None
        if not isinstance(snippet, dict) or not isinstance(channel_id, str):
            # 부분적으로 깨진 항목 하나 때문에 나머지 결과를 버리지 않는다.
            continue
        channels.append(
            YoutubeChannel(
                channel_id=channel_id,
                title=str(snippet.get("title") or ""),
                description=str(snippet.get("description") or ""),
                thumbnail_url=_parse_thumbnail(snippet),
            )
        )

    next_page_token = body.get("nextPageToken")
    return YoutubeSearchResponse(
        channels=channels,
        next_page_token=next_page_token if isinstance(next_page_token, str) else None,
    )


def _parse_duration_seconds(value: object) -> int | None:
    """ISO-8601 기간(`PT12M34S`)을 초로 옮긴다. 못 읽으면 `None`이다.

    ⚠️ 못 읽은 값을 `0`으로 접지 않는다. 0초는 "길이를 모른다"가 아니라 "빈 영상"으로
    읽히고, 목록에서 그 둘은 사용자가 내리는 판단이 다르다.
    """
    if not isinstance(value, str):
        return None
    match = _ISO8601_DURATION.match(value)
    if match is None:
        return None
    parts = {key: int(raw) for key, raw in match.groupdict(default="0").items()}
    return parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]


async def _uploads_playlist_id(
    client: httpx.AsyncClient, *, api_key: str, channel_id: str, timeout_seconds: float
) -> str:
    """채널의 uploads 재생목록 id를 읽는다 (1유닛)."""
    body = await _get_json(
        client,
        _CHANNELS_ENDPOINT,
        params={"part": "contentDetails", "id": channel_id, "key": api_key},
        timeout_seconds=timeout_seconds,
    )
    for item in body.get("items") or []:
        if not isinstance(item, dict):
            continue
        details = item.get("contentDetails")
        related = details.get("relatedPlaylists") if isinstance(details, dict) else None
        uploads = related.get("uploads") if isinstance(related, dict) else None
        if isinstance(uploads, str) and uploads:
            return uploads
    raise YoutubeChannelNotFound


async def list_channel_videos(
    client: httpx.AsyncClient,
    *,
    api_key: str,
    channel_id: str,
    page_token: str | None,
    timeout_seconds: float,
) -> YoutubeVideoListResponse:
    """채널 영상 한 페이지를 읽는다 — `channels.list` → `playlistItems.list` → `videos.list`.

    ⚠️ `search.list`에 `channelId`를 넘기는 방법을 쓰지 않는다(design D4). 그 호출은
    100유닛이라 목록을 몇 페이지만 넘겨도 일일 쿼터 10,000이 녹고, 그러면 이 기능에서
    유일하게 비싼 호출이어야 할 채널 검색이 영상 목록 때문에 먼저 막힌다. 아래 세 호출은
    합쳐서 3유닛이다.
    """
    uploads_playlist_id = await _uploads_playlist_id(
        client, api_key=api_key, channel_id=channel_id, timeout_seconds=timeout_seconds
    )

    params: dict[str, Any] = {
        "part": "contentDetails",
        "playlistId": uploads_playlist_id,
        "maxResults": _MAX_VIDEO_RESULTS,
        "key": api_key,
    }
    if page_token:
        params["pageToken"] = page_token
    page = await _get_json(
        client, _PLAYLIST_ITEMS_ENDPOINT, params=params, timeout_seconds=timeout_seconds
    )

    # ⚠️ 업로드 순서는 `playlistItems`에만 있다. 아래 `videos.list`는 응답 순서를
    #    보장하지 않으므로 이 목록이 최종 정렬의 기준이다.
    ordered_ids: list[str] = []
    for item in page.get("items") or []:
        details = item.get("contentDetails") if isinstance(item, dict) else None
        video_id = details.get("videoId") if isinstance(details, dict) else None
        if isinstance(video_id, str) and video_id and video_id not in ordered_ids:
            ordered_ids.append(video_id)

    next_page_token = page.get("nextPageToken")
    next_token = next_page_token if isinstance(next_page_token, str) else None
    if not ordered_ids:
        return YoutubeVideoListResponse(videos=[], next_page_token=next_token)

    # ⚠️ 길이는 `playlistItems`에 없어서 이 호출이 필요하다. 그리고 이 호출은 부수적으로
    #    **비공개·삭제된 영상을 걸러낸다** — 그런 영상은 응답에 아예 오지 않으므로, 여기
    #    없는 id를 버리면 목록에서 고를 수 없는 영상이 사라진다. 제목 문자열
    #    ("Private video")로 거르는 방법은 언어별로 달라 쓰지 않는다.
    detail = await _get_json(
        client,
        _VIDEOS_ENDPOINT,
        params={
            "part": "snippet,contentDetails",
            "id": ",".join(ordered_ids),
            "key": api_key,
        },
        timeout_seconds=timeout_seconds,
    )

    by_id: dict[str, YoutubeVideo] = {}
    for item in detail.get("items") or []:
        if not isinstance(item, dict):
            continue
        video_id = item.get("id")
        snippet = item.get("snippet")
        if not isinstance(video_id, str) or not isinstance(snippet, dict):
            # 깨진 항목 하나 때문에 나머지 페이지를 버리지 않는다 (검색 파싱과 같은 규약).
            continue
        content_details = item.get("contentDetails")
        published_at = snippet.get("publishedAt")
        by_id[video_id] = YoutubeVideo(
            video_id=video_id,
            title=str(snippet.get("title") or ""),
            published_at=published_at if isinstance(published_at, str) else None,
            duration_seconds=_parse_duration_seconds(
                content_details.get("duration") if isinstance(content_details, dict) else None
            ),
            thumbnail_url=_parse_thumbnail(snippet),
        )

    return YoutubeVideoListResponse(
        videos=[by_id[video_id] for video_id in ordered_ids if video_id in by_id],
        next_page_token=next_token,
    )


SearchFunction = Callable[[YoutubeSearchRequest], Awaitable[YoutubeSearchResponse]]
VideoListFunction = Callable[[YoutubeVideoListRequest], Awaitable[YoutubeVideoListResponse]]


class _InternalGuard:
    """내부 리스너 공통 관문 — 인증 → 레이트 예약 → 동시성 → 타임아웃 → 사유 매핑.

    ⚠️ **순서가 계약이다.** 인증이 레이트 예약보다 앞서야 미인증 요청이 용량을 태우지
    못하고, 레이트 예약이 업스트림 호출보다 앞서야 일일 쿼터가 이 경계에서 유한하게
    유지된다. 두 리스너가 이 구현을 공유하는 이유도 같다 — 토큰 버킷을 리스너마다
    복제하면 한쪽만 고친 순서 버그가 다른 쪽에 남는다.
    """

    def __init__(
        self,
        *,
        internal_token: str,
        timeout_seconds: float,
        max_concurrency: int,
        rate_capacity: int,
        refill_tokens_per_second: float,
        monotonic: MonotonicClock,
    ) -> None:
        if not internal_token:
            raise ValueError("internal token is required")
        if (
            min(timeout_seconds, max_concurrency, rate_capacity, refill_tokens_per_second) <= 0
        ):  # fmt: skip
            raise ValueError("youtube bounds must be positive")
        self._internal_token = internal_token
        self._timeout_seconds = timeout_seconds
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._rate_capacity = rate_capacity
        self._refill_tokens_per_second = refill_tokens_per_second
        self._monotonic = monotonic
        self._tokens = float(rate_capacity)
        self._last_refill = monotonic()
        self._request_lock = asyncio.Lock()

    def authenticate(self, authorization: str | None) -> None:
        """Authenticate before quota/provider work, so unauthenticated calls cannot
        consume capacity."""
        if authorization != f"Bearer {self._internal_token}":
            raise HTTPException(status_code=401, detail="internal_unauthorized")

    async def _reserve_token(self) -> None:
        """Reserve one provider-attempt token, refilling from a monotonic clock."""
        async with self._request_lock:
            now = self._monotonic()
            elapsed = max(0.0, now - self._last_refill)
            self._tokens = min(
                float(self._rate_capacity),
                self._tokens + elapsed * self._refill_tokens_per_second,
            )
            self._last_refill = max(self._last_refill, now)
            if self._tokens < 1:
                raise HTTPException(status_code=429, detail="rate_limited")
            self._tokens -= 1

    async def run(self, call: Callable[[], Awaitable[Any]]) -> Any:
        await self._reserve_token()
        try:
            async with self._semaphore:
                return await asyncio.wait_for(call(), timeout=self._timeout_seconds)
        except asyncio.CancelledError:
            raise
        except YoutubeQuotaExceeded:
            # ⚠️ 502로 뭉개지 않는다. 호출자가 사용자에게 설명할 수 있어야 하는
            #    유일한 업스트림 실패다.
            raise HTTPException(status_code=503, detail="youtube_quota_exceeded") from None
        except YoutubeChannelNotFound:
            # 채널 소멸은 업스트림 장애가 아니다 — 사용자가 다른 채널을 고르면 되는
            # 상황이라 재시도 안내와 구분되어야 한다.
            raise HTTPException(status_code=404, detail="youtube_channel_not_found") from None
        except TimeoutError:
            raise HTTPException(status_code=504, detail="youtube_unavailable") from None
        except Exception:
            # Provider bodies and exception strings are not caller-visible.
            raise HTTPException(status_code=502, detail="youtube_unavailable") from None


class YoutubeSearchService:
    """Binds authenticated, bounded requests to an injected channel search."""

    def __init__(
        self,
        search: SearchFunction,
        *,
        internal_token: str,
        max_query_chars: int = 100,
        timeout_seconds: float = 10.0,
        max_concurrency: int = 4,
        rate_capacity: int = 60,
        refill_tokens_per_second: float = 0.2,
        monotonic: MonotonicClock = time.monotonic,
    ) -> None:
        if max_query_chars <= 0:
            raise ValueError("youtube search bounds must be positive")
        self._search = search
        self._max_query_chars = max_query_chars
        self._guard = _InternalGuard(
            internal_token=internal_token,
            timeout_seconds=timeout_seconds,
            max_concurrency=max_concurrency,
            rate_capacity=rate_capacity,
            refill_tokens_per_second=refill_tokens_per_second,
            monotonic=monotonic,
        )

    async def search(
        self, request: YoutubeSearchRequest, authorization: str | None
    ) -> YoutubeSearchResponse:
        self._guard.authenticate(authorization)
        if not request.query or len(request.query) > self._max_query_chars:
            raise HTTPException(status_code=422, detail="invalid_query")
        result: YoutubeSearchResponse = await self._guard.run(lambda: self._search(request))
        return result


class YoutubeVideoListService:
    """Binds authenticated, bounded requests to an injected channel video listing.

    ⚠️ 검색 서비스와 **레이트 예산을 공유하지 않는다.** 영상 목록 한 페이지는 3유닛,
    채널 검색 한 번은 100유닛이다. 하나의 버킷에 묶으면 목록 넘기기가 검색 예산을
    갉아먹거나, 반대로 검색 기준으로 좁힌 버킷이 정상적인 목록 탐색을 막는다.
    """

    def __init__(
        self,
        list_videos: VideoListFunction,
        *,
        internal_token: str,
        timeout_seconds: float = 15.0,
        max_concurrency: int = 4,
        rate_capacity: int = 120,
        refill_tokens_per_second: float = 2.0,
        monotonic: MonotonicClock = time.monotonic,
    ) -> None:
        self._list_videos = list_videos
        self._guard = _InternalGuard(
            internal_token=internal_token,
            timeout_seconds=timeout_seconds,
            max_concurrency=max_concurrency,
            rate_capacity=rate_capacity,
            refill_tokens_per_second=refill_tokens_per_second,
            monotonic=monotonic,
        )

    async def list_videos(
        self, request: YoutubeVideoListRequest, authorization: str | None
    ) -> YoutubeVideoListResponse:
        self._guard.authenticate(authorization)
        if not request.channel_id:
            raise HTTPException(status_code=422, detail="invalid_channel_id")
        result: YoutubeVideoListResponse = await self._guard.run(lambda: self._list_videos(request))
        return result


def add_youtube_search_route(app: FastAPI, service: YoutubeSearchService) -> None:
    """Register `POST /internal/youtube-search` on an existing app."""

    @app.post("/internal/youtube-search", response_model=YoutubeSearchResponse)
    async def youtube_search(
        request: YoutubeSearchRequest,
        authorization: Annotated[str | None, Header()] = None,
    ) -> YoutubeSearchResponse:
        return await service.search(request, authorization)


def add_youtube_videos_route(app: FastAPI, service: YoutubeVideoListService) -> None:
    """Register `POST /internal/youtube-videos` on an existing app."""

    @app.post("/internal/youtube-videos", response_model=YoutubeVideoListResponse)
    async def youtube_videos(
        request: YoutubeVideoListRequest,
        authorization: Annotated[str | None, Header()] = None,
    ) -> YoutubeVideoListResponse:
        return await service.list_videos(request, authorization)
