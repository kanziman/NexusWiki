"""Storage 삭제 잡의 멱등성과 service-role 테넌트 경계를 검증한다."""

import httpx
import pytest

from worker.errors import StorageObjectMissing
from worker.handlers.delete_source_storage import run_delete_source_storage

WORKSPACE_ID = "11111111-1111-4111-8111-111111111111"
SOURCE_ID = "22222222-2222-4222-8222-222222222222"
PATH = f"{WORKSPACE_ID}/{SOURCE_ID}/report.pdf"


@pytest.mark.asyncio
async def test_delete_job_deletes_only_the_scoped_object() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(204)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://example.invalid/storage/v1"
    ) as client:
        await run_delete_source_storage(
            workspace_id=WORKSPACE_ID,
            payload={"raw_source_id": SOURCE_ID, "storage_path": PATH},
            object_client=client,
        )

    assert [request.method for request in seen] == ["DELETE"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "workspace_id,raw_source_id",
    [
        ("33333333-3333-4333-8333-333333333333", SOURCE_ID),
        (WORKSPACE_ID, "33333333-3333-4333-8333-333333333333"),
    ],
)
async def test_delete_job_rejects_mismatched_scope(workspace_id: str, raw_source_id: str) -> None:
    async with httpx.AsyncClient(base_url="https://example.invalid/storage/v1") as client:
        with pytest.raises(StorageObjectMissing):
            await run_delete_source_storage(
                workspace_id=workspace_id,
                payload={"raw_source_id": raw_source_id, "storage_path": PATH},
                object_client=client,
            )
