"""Private, worker-owned YouTube Data API boundary.

관련 태스크: openspec/changes/youtube-channel-import/tasks.md Task 1.1
설계 근거: 같은 change의 `design.md` > D5

⚠️ YouTube API 키는 **워커만** 소유한다. `ApiSettings`에는 provider 자격증명을 담을
필드가 존재할 수 없고(SEC-01), api와 worker가 단일 이미지를 공유하므로 import 차단으로
그 격리를 되찾을 수도 없다. 그래서 검색은 여기(키를 가진 쪽)에서 일어나고 API는
내부 호출자 토큰으로 이 경계를 호출하기만 한다 — `query_embedding`·`llm_stream`과 같은
형태다.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Annotated, Any

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict

__all__ = [
    "YoutubeChannel",
    "YoutubeQuotaExceeded",
    "YoutubeSearchRequest",
    "YoutubeSearchResponse",
    "YoutubeSearchService",
    "YoutubeUnavailable",
    "add_youtube_search_route",
    "search_channels",
]

MonotonicClock = Callable[[], float]

_SEARCH_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"

# ⚠️ `search.list`는 호출당 100유닛이고 일일 기본 한도가 10,000유닛이다. 이 경계에서
#    한 번 새는 호출이 곧 서비스 전체의 검색 100분의 1이라, 캐시(API 쪽)와 레이트 제한
#    (여기)을 둘 다 둔다.
_MAX_RESULTS = 20


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

    try:
        response = await client.get(_SEARCH_ENDPOINT, params=params, timeout=timeout_seconds)
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


SearchFunction = Callable[[YoutubeSearchRequest], Awaitable[YoutubeSearchResponse]]


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
        if not internal_token:
            raise ValueError("internal token is required")
        if (
            min(
                max_query_chars,
                timeout_seconds,
                max_concurrency,
                rate_capacity,
                refill_tokens_per_second,
            )
            <= 0
        ):
            raise ValueError("youtube search bounds must be positive")
        self._search = search
        self._internal_token = internal_token
        self._max_query_chars = max_query_chars
        self._timeout_seconds = timeout_seconds
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._rate_capacity = rate_capacity
        self._refill_tokens_per_second = refill_tokens_per_second
        self._monotonic = monotonic
        self._tokens = float(rate_capacity)
        self._last_refill = monotonic()
        self._request_lock = asyncio.Lock()

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

    async def search(
        self, request: YoutubeSearchRequest, authorization: str | None
    ) -> YoutubeSearchResponse:
        # Authenticate before quota/provider work, so unauthenticated calls cannot
        # consume capacity.
        if authorization != f"Bearer {self._internal_token}":
            raise HTTPException(status_code=401, detail="internal_unauthorized")
        if not request.query or len(request.query) > self._max_query_chars:
            raise HTTPException(status_code=422, detail="invalid_query")
        await self._reserve_token()
        try:
            async with self._semaphore:
                return await asyncio.wait_for(self._search(request), timeout=self._timeout_seconds)
        except asyncio.CancelledError:
            raise
        except YoutubeQuotaExceeded:
            # ⚠️ 502로 뭉개지 않는다. 호출자가 사용자에게 설명할 수 있어야 하는
            #    유일한 업스트림 실패다.
            raise HTTPException(status_code=503, detail="youtube_quota_exceeded") from None
        except TimeoutError:
            raise HTTPException(status_code=504, detail="youtube_unavailable") from None
        except Exception:
            # Provider bodies and exception strings are not caller-visible.
            raise HTTPException(status_code=502, detail="youtube_unavailable") from None


def add_youtube_search_route(app: FastAPI, service: YoutubeSearchService) -> None:
    """Register `POST /internal/youtube-search` on an existing app."""

    @app.post("/internal/youtube-search", response_model=YoutubeSearchResponse)
    async def youtube_search(
        request: YoutubeSearchRequest,
        authorization: Annotated[str | None, Header()] = None,
    ) -> YoutubeSearchResponse:
        return await service.search(request, authorization)
