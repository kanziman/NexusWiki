"""YouTube 채널 검색 경계.

관련 태스크: openspec/changes/youtube-channel-import/tasks.md Task 1.2 · 1.3 · 1.4
설계 근거: 같은 change의 `design.md` > D3, D5

⚠️ 이 라우터는 YouTube를 **직접 호출하지 않는다.** provider 키는 워커만 소유하므로
(`ApiSettings`에는 키를 담을 필드가 없다 — SEC-01) 여기서는 워커의 사설 리스너를
내부 호출자 토큰으로 부르기만 한다. 키를 이 프로세스로 옮기고 싶어지면 그것이 곧
SEC-01을 깨는 순간이다.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Annotated, Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from api.db.user import UserDb
from api.errors import WorkspaceForbidden, YoutubeQuotaExceeded, YoutubeUnavailable

router = APIRouter(prefix="/workspaces", tags=["youtube"])

_bearer = HTTPBearer(auto_error=True)

_MAX_QUERY_CHARS = 100


class YoutubeChannel(BaseModel):
    channel_id: str
    title: str
    description: str
    thumbnail_url: str | None = None


class ChannelSearchResponse(BaseModel):
    channels: list[YoutubeChannel]
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
    """`(질의, 지역, 페이지 토큰)` → 응답. TTL과 최대 항목 수를 둘 다 가진 LRU.

    ⚠️ 프로세스 메모리다 — 재배포하면 사라지고 인스턴스 사이에 공유되지 않는다.
    그래도 DB 캐시 테이블을 쓰지 않는 이유는 `design.md` D3에 있다: 이 데이터는
    테넌트 데이터가 아니라 격리할 `workspace_id`가 없는데, 사용자 경로가 RLS 하에서
    쓰려면 `authenticated`에게 공유 테이블 INSERT를 줘야 하고 그 순간 임의의 멤버가
    캐시를 오염시킬 수 있는 표면이 생긴다.
    """

    def __init__(self, *, ttl_seconds: float, max_entries: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._entries: OrderedDict[tuple[str, str, str], tuple[float, dict[str, Any]]] = (
            OrderedDict()
        )

    def get(self, key: tuple[str, str, str], *, now: float) -> dict[str, Any] | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        stored_at, payload = entry
        if now - stored_at > self._ttl_seconds:
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return payload

    def put(self, key: tuple[str, str, str], payload: dict[str, Any], *, now: float) -> None:
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


async def _call_worker_search(
    request: Request, *, query: str, region_code: str, page_token: str | None
) -> dict[str, Any]:
    """워커의 사설 검색 리스너를 부른다. 업스트림 사유는 두 갈래로만 올린다."""
    settings = request.app.state.settings
    url = settings.YOUTUBE_SEARCH_INTERNAL_URL
    token = settings.YOUTUBE_SEARCH_INTERNAL_TOKEN
    if not url or not token:
        # 설정 누락을 쿼터 소진으로 위장하지 않는다.
        raise YoutubeUnavailable

    client: httpx.AsyncClient = request.app.state.http_client
    try:
        response = await client.post(
            f"{url.rstrip('/')}/internal/youtube-search",
            json={"query": query, "region_code": region_code, "page_token": page_token},
            headers={"Authorization": f"Bearer {token}"},
            timeout=settings.YOUTUBE_SEARCH_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as error:
        raise YoutubeUnavailable from error

    if response.status_code == 503:
        # 워커가 쿼터 소진에만 쓰는 코드다 (`worker.youtube`). 다른 5xx와 섞지 않는다.
        raise YoutubeQuotaExceeded
    if response.is_error:
        raise YoutubeUnavailable

    payload = response.json()
    if not isinstance(payload, dict):
        raise YoutubeUnavailable
    return payload


@router.get("/{workspace_id}/youtube/channels", response_model=ChannelSearchResponse)
async def search_channels(
    workspace_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    q: Annotated[str, Query(min_length=1, max_length=_MAX_QUERY_CHARS)],
    region_code: Annotated[str, Query(min_length=2, max_length=2)] = "KR",
    page_token: Annotated[str | None, Query(max_length=512)] = None,
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
    key = (query, region_code.upper(), page_token or "")
    now = time.monotonic()
    cached = cache.get(key, now=now)
    if cached is not None:
        return ChannelSearchResponse.model_validate(cached)

    payload = await _call_worker_search(
        request, query=query, region_code=region_code.upper(), page_token=page_token
    )
    result = ChannelSearchResponse.model_validate(payload)
    cache.put(key, result.model_dump(), now=now)
    return result
