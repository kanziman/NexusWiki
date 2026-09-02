"""원문 DB 삭제 뒤 남은 Storage 객체를 재시도 가능하게 정리한다."""

from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Any, Final

import httpx

from worker.errors import StorageObjectMissing
from worker.settings import WorkerSettings
from worker.storage import delete_source_object, storage_client

__all__ = [
    "DELETE_SOURCE_STORAGE_JOB_TYPE",
    "handle_delete_source_storage",
    "run_delete_source_storage",
]

DELETE_SOURCE_STORAGE_JOB_TYPE: Final[str] = "delete_source_storage"


async def handle_delete_source_storage(
    *, job_id: str, workspace_id: str, payload: dict[str, Any]
) -> None:
    """잡 진입점 — service key Storage 클라이언트의 수명을 실행에 한정한다."""
    del job_id
    settings = WorkerSettings()
    async with AsyncExitStack() as stack:
        client = await stack.enter_async_context(storage_client(settings))
        await run_delete_source_storage(
            workspace_id=workspace_id,
            payload=payload,
            object_client=client,
        )


async def run_delete_source_storage(
    *, workspace_id: str, payload: dict[str, Any], object_client: httpx.AsyncClient
) -> None:
    """잡의 테넌트와 원문 UUID가 모두 일치하는 객체만 삭제한다."""
    storage_path = payload.get("storage_path")
    raw_source_id = payload.get("raw_source_id") or payload.get("target_id")
    if not isinstance(storage_path, str) or not storage_path:
        raise ValueError("Storage 삭제 잡 payload에 storage_path가 없다")
    if not isinstance(raw_source_id, str) or not raw_source_id:
        raise ValueError("Storage 삭제 잡 payload에 raw_source_id가 없다")

    segments = storage_path.split("/")
    # ⚠️ service role은 Storage RLS를 우회한다. 두 식별자를 모두 잡의 값과 대조하지
    # 않으면 변조된 payload 하나가 다른 테넌트나 다른 원문의 객체를 삭제할 수 있다.
    if len(segments) != 3 or segments[0] != workspace_id or segments[1] != raw_source_id:
        raise StorageObjectMissing()

    await delete_source_object(object_client, path=storage_path)
