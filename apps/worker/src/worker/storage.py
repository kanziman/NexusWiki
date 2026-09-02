"""service_role로 이미 저장된 원본 객체를 다운로드한다.

관련 태스크: P2-ING-01
설계 근거: 03-06-PLAN.md > D-P17

경로 규약은 `0001_core_schema.sql:107-110`과 `0005_storage.sql:29`가 소유하며, 업로드
측(03-05)이 조립한다. 이 모듈은 받은 `{workspace_id}/{raw_source_id}/{filename}`를 소비만
해 두 구현이 갈라지는 축을 만들지 않는다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final
from urllib.parse import quote

import httpx

from worker.errors import StorageObjectMissing

if TYPE_CHECKING:
    from worker.settings import WorkerSettings

__all__ = [
    "StorageObjectMissing",
    "delete_source_object",
    "download_source_object",
    "storage_client",
]

STORAGE_REQUEST_TIMEOUT_SECONDS: Final[float] = 20.0


def storage_client(
    settings: WorkerSettings, *, timeout_seconds: float = STORAGE_REQUEST_TIMEOUT_SECONDS
) -> httpx.AsyncClient:
    """명시적으로 주입된 worker 설정에서만 service key 클라이언트를 만든다."""
    secret_key = getattr(settings, "SUPABASE_SECRET_KEY", None)
    if not isinstance(secret_key, str) or not secret_key:
        raise TypeError("storage_client는 SUPABASE_SECRET_KEY를 가진 WorkerSettings를 요구한다")
    return httpx.AsyncClient(
        base_url=f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1",
        headers={"apikey": secret_key, "Authorization": f"Bearer {secret_key}"},
        timeout=httpx.Timeout(timeout_seconds),
    )


async def download_source_object(client: httpx.AsyncClient, *, path: str) -> bytes:
    """`sources` 버킷의 객체를 그대로 받은 3세그먼트 경로로 읽는다."""
    # ⚠️ service key는 0005 Storage 정책을 지나지 않는다. 호출부가 첫 세그먼트와 잡의
    # workspace_id를 대조해야 하며, 여기서는 경로를 조립하거나 재해석하지 않는다.
    response = await client.get(f"/object/sources/{quote(path, safe='/')}")
    if response.status_code == 404:
        raise StorageObjectMissing()
    response.raise_for_status()
    return response.content


async def delete_source_object(client: httpx.AsyncClient, *, path: str) -> None:
    """`sources` 버킷 객체를 멱등 삭제한다. 이미 없으면 성공으로 취급한다."""
    response = await client.delete(f"/object/sources/{quote(path, safe='/')}")
    if response.status_code == 404:
        return
    response.raise_for_status()
