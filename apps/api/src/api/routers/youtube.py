"""YouTube 채널 검색·영상 목록 경계.

관련 태스크: openspec/changes/youtube-channel-import/tasks.md Task 1.2 · 1.3 · 1.4 · 2.1
설계 근거: 같은 change의 `design.md` > D3, D4, D5

⚠️ 이 라우터는 YouTube를 **직접 호출하지 않는다.** provider 키는 워커만 소유하므로
(`ApiSettings`에는 키를 담을 필드가 없다 — SEC-01) 여기서는 워커의 사설 리스너를
내부 호출자 토큰으로 부르기만 한다. 키를 이 프로세스로 옮기고 싶어지면 그것이 곧
SEC-01을 깨는 순간이다.

⚠️ 이 라우터는 `raw_sources`를 만들지 않는다. 선택 영상 등록은 `routers/sources.py`가
소유한다 — 원문 행을 만드는 경로가 두 라우터로 갈라지면 `_insert_and_enqueue`가 함께
들고 있는 중복 판정·예산 프리플라이트도 갈라진다.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Annotated, Any, Literal
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from api.db.user import UserDb
from api.errors import (
    WorkspaceForbidden,
    YoutubeChannelNotFound,
    YoutubeQuotaExceeded,
    YoutubeUnavailable,
)

router = APIRouter(prefix="/workspaces", tags=["youtube"])

_bearer = HTTPBearer(auto_error=True)

_MAX_QUERY_CHARS = 100

# `UC` + base64url 22자가 채널 id의 형태다. 길이를 못 박지 않고 문자 집합과 상한만 재는
# 이유는 형태가 바뀌어도 이 값이 **경로 조각이 아니라 업스트림 쿼리 파라미터**로만
# 쓰이기 때문이다 — 여기서 막는 것은 위조가 아니라 의미 없는 업스트림 호출이다.
_MAX_CHANNEL_ID_CHARS = 64


class YoutubeChannel(BaseModel):
    channel_id: str
    title: str
    description: str
    thumbnail_url: str | None = None
    subscriber_count: int | None = None
    video_count: int | None = None
    handle: str | None = None


class ChannelSearchResponse(BaseModel):
    channels: list[YoutubeChannel]
    next_page_token: str | None = None


class YoutubeVideo(BaseModel):
    video_id: str
    title: str
    published_at: str | None = None
    duration_seconds: int | None = None
    thumbnail_url: str | None = None
    has_captions: bool | None = None
    view_count: int | None = None
    like_count: int | None = None


class ChannelVideosResponse(BaseModel):
    videos: list[YoutubeVideo]
    next_page_token: str | None = None


def _user_db(request: Request, credentials: HTTPAuthorizationCredentials) -> UserDb:
    settings = request.app.state.settings
    return UserDb(
        request.app.state.http_client,
        supabase_url=settings.SUPABASE_URL,
        publishable_key=settings.SUPABASE_PUBLISHABLE_KEY,
        access_token=credentials.credentials,
    )


async def _require_membership(db: UserDb, *, workspace_id: UUID) -> None:
    """검색은 멤버 전용이다.

    ⚠️ 이 경로는 DB를 읽지 않으므로 RLS가 저절로 막아주지 않는다. 명시적으로 묻지 않으면
    비멤버가 워크스페이스 id만 알아도 서비스 공용 쿼터를 태울 수 있다 — 쿼터가 곧
    비용이자 다른 워크스페이스의 검색 가능 횟수다.
    """
    result = await db.rpc(
        "has_workspace_role",
        params={"ws_id": str(workspace_id), "min_role": "viewer"},
    )
    if not result or result[0] is not True:
        raise WorkspaceForbidden(table="workspace_members", affected=0)


class SearchCache:
    """`(질의, 지역, 페이지 토큰, 정렬, 언어)` → 응답. TTL과 최대 항목 수를 둘 다 가진 LRU.

    ⚠️ 프로세스 메모리다 — 재배포하면 사라지고 인스턴스 사이에 공유되지 않는다.
    그래도 DB 캐시 테이블을 쓰지 않는 이유는 `design.md` D3에 있다: 이 데이터는
    테넌트 데이터가 아니라 격리할 `workspace_id`가 없는데, 사용자 경로가 RLS 하에서
    쓰려면 `authenticated`에게 공유 테이블 INSERT를 줘야 하고 그 순간 임의의 멤버가
    캐시를 오염시킬 수 있는 표면이 생긴다.

    ⚠️ 키의 다섯 축 중 하나라도 빠지면 정렬이나 언어를 바꿔 재검색했을 때 이전
    조합으로 캐시된 결과가 그대로 나온다 — 사용자에게는 "정렬을 바꿨는데 안 바뀜"으로
    보이는 조용한 실패다.
    """

    def __init__(self, *, ttl_seconds: float, max_entries: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._entries: OrderedDict[tuple[str, str, str, str, str], tuple[float, dict[str, Any]]] = (
            OrderedDict()
        )

    def get(self, key: tuple[str, str, str, str, str], *, now: float) -> dict[str, Any] | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        stored_at, payload = entry
        if now - stored_at > self._ttl_seconds:
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return payload

    def put(
        self, key: tuple[str, str, str, str, str], payload: dict[str, Any], *, now: float
    ) -> None:
        self._entries[key] = (now, payload)
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)


def _cache(request: Request) -> SearchCache:
    cache = getattr(request.app.state, "youtube_search_cache", None)
    if cache is None:
        settings = request.app.state.settings
        cache = SearchCache(
            ttl_seconds=settings.YOUTUBE_SEARCH_CACHE_TTL_SECONDS,
            max_entries=settings.YOUTUBE_SEARCH_CACHE_MAX_ENTRIES,
        )
        request.app.state.youtube_search_cache = cache
    return cache


def _error_detail(response: httpx.Response) -> str:
    """오류 응답의 `detail` 토큰만 꺼낸다. 못 읽으면 빈 문자열이다."""
    try:
        body = response.json()
    except ValueError:
        return ""
    detail = body.get("detail") if isinstance(body, dict) else None
    return detail if isinstance(detail, str) else ""


async def _call_worker(
    request: Request, *, path: str, payload: dict[str, Any], timeout_seconds: float
) -> dict[str, Any]:
    """워커의 사설 리스너 하나를 부른다. 업스트림 사유는 세 갈래로만 올린다.

    ⚠️ 상태 코드**만으로** 사유를 읽지 않는다. 503과 404는 우리 워커가 각각 쿼터 소진과
    채널 소멸에만 쓰는 코드지만, 그 앞에 프록시나 로드밸런서가 끼는 순간 같은 코드가
    전혀 다른 뜻으로 도착한다 — 게이트웨이의 503은 워커 장애이고, `YOUTUBE_API_KEY`가
    없으면 워커가 이 라우트를 아예 등록하지 않아 FastAPI 기본 404가 온다. 뭉개면 워커
    장애가 "내일 다시 시도하세요"로, 배포 설정 누락이 "그 채널은 삭제됐습니다"로
    위장되고 그 화면에서는 원인을 영원히 찾을 수 없다. 그래서 두 코드 모두 워커 자신이
    붙인 토큰까지 대조한다.
    """
    settings = request.app.state.settings
    url = settings.YOUTUBE_SEARCH_INTERNAL_URL
    token = settings.YOUTUBE_SEARCH_INTERNAL_TOKEN
    if not url or not token:
        # 설정 누락을 쿼터 소진으로 위장하지 않는다.
        raise YoutubeUnavailable

    client: httpx.AsyncClient = request.app.state.http_client
    try:
        response = await client.post(
            f"{url.rstrip('/')}{path}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout_seconds,
        )
    except httpx.HTTPError as error:
        raise YoutubeUnavailable from error

    if response.is_error:
        detail = _error_detail(response)
        if response.status_code == 503 and detail == "youtube_quota_exceeded":
            raise YoutubeQuotaExceeded
        if response.status_code == 404 and detail == "youtube_channel_not_found":
            raise YoutubeChannelNotFound
        raise YoutubeUnavailable

    body = response.json()
    if not isinstance(body, dict):
        raise YoutubeUnavailable
    return body


async def _call_worker_search(
    request: Request,
    *,
    query: str,
    region_code: str,
    page_token: str | None,
    order: str = "relevance",
    relevance_language: str | None = None,
) -> dict[str, Any]:
    """워커의 사설 채널 검색 리스너를 부른다."""
    return await _call_worker(
        request,
        path="/internal/youtube-search",
        payload={
            "query": query,
            "region_code": region_code,
            "page_token": page_token,
            "order": order,
            "relevance_language": relevance_language,
        },
        timeout_seconds=request.app.state.settings.YOUTUBE_SEARCH_TIMEOUT_SECONDS,
    )


async def _call_worker_videos(
    request: Request, *, channel_id: str, page_token: str | None
) -> dict[str, Any]:
    """워커의 사설 영상 목록 리스너를 부른다."""
    return await _call_worker(
        request,
        path="/internal/youtube-videos",
        payload={"channel_id": channel_id, "page_token": page_token},
        timeout_seconds=request.app.state.settings.YOUTUBE_VIDEOS_TIMEOUT_SECONDS,
    )


@router.get("/{workspace_id}/youtube/channels", response_model=ChannelSearchResponse)
async def search_channels(
    workspace_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    q: Annotated[str, Query(min_length=1, max_length=_MAX_QUERY_CHARS)],
    region_code: Annotated[str, Query(min_length=2, max_length=2)] = "KR",
    page_token: Annotated[str | None, Query(max_length=512)] = None,
    order: Annotated[
        Literal["relevance", "date", "rating", "title", "videoCount", "viewCount"], Query()
    ] = "relevance",
    relevance_language: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
) -> ChannelSearchResponse:
    """키워드로 채널 후보를 돌려준다.

    ⚠️ 멤버십 확인이 캐시 조회보다 **앞선다.** 캐시 히트를 먼저 돌려주면 비멤버가
    남이 데워놓은 결과를 읽을 수 있고, 그것 자체가 워크스페이스 경계를 넘는 응답이 된다.
    """
    query = q.strip()
    if not query:
        raise HTTPException(status_code=422, detail="invalid_query")

    await _require_membership(_user_db(request, credentials), workspace_id=workspace_id)

    cache = _cache(request)
    key = (query, region_code.upper(), page_token or "", order, relevance_language or "")
    now = time.monotonic()
    cached = cache.get(key, now=now)
    if cached is not None:
        return ChannelSearchResponse.model_validate(cached)

    payload = await _call_worker_search(
        request,
        query=query,
        region_code=region_code.upper(),
        page_token=page_token,
        order=order,
        relevance_language=relevance_language,
    )
    result = ChannelSearchResponse.model_validate(payload)
    cache.put(key, result.model_dump(), now=now)
    return result


@router.get(
    "/{workspace_id}/youtube/channels/{channel_id}/videos",
    response_model=ChannelVideosResponse,
)
async def list_channel_videos(
    workspace_id: UUID,
    channel_id: str,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    page_token: Annotated[str | None, Query(max_length=512)] = None,
) -> ChannelVideosResponse:
    """선택한 채널의 영상 한 페이지를 돌려준다.

    ⚠️ 검색과 달리 캐시하지 않는다. 목록 한 페이지는 3유닛이라 캐시가 지킬 쿼터가 거의
    없는 반면(`search.list`는 100유닛), 캐시가 있으면 방금 올라온 영상이 TTL 동안 목록에
    나타나지 않는다 — 지킬 것보다 잃을 것이 큰 교환이다.

    ⚠️ 멤버십 확인은 검색과 같은 이유로 여기서도 필수다. 이 경로 역시 DB를 읽지 않아
    RLS가 저절로 막아주지 않으므로, 묻지 않으면 비멤버가 워크스페이스 id만으로 서비스
    공용 쿼터를 태울 수 있다.
    """
    identifier = channel_id.strip()
    if not identifier or len(identifier) > _MAX_CHANNEL_ID_CHARS:
        raise HTTPException(status_code=422, detail="invalid_channel_id")

    await _require_membership(_user_db(request, credentials), workspace_id=workspace_id)

    payload = await _call_worker_videos(request, channel_id=identifier, page_token=page_token)
    return ChannelVideosResponse.model_validate(payload)
