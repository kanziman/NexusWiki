"""service_role Storage 다운로드가 경로를 재조립하지 않는지 고정한다."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx
import pytest

from worker.errors import StorageObjectMissing
from worker.storage import download_source_object, storage_client

WORKSPACE_ID = "11111111-1111-4111-8111-111111111111"
SOURCE_ID = "22222222-2222-4222-822222222222"
PATH = f"{WORKSPACE_ID}/{SOURCE_ID}/source file.pdf"


@pytest.mark.asyncio
async def test_download_preserves_the_supplied_three_segment_path() -> None:
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=b"original bytes")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://example.invalid/storage/v1"
    ) as client:
        data = await download_source_object(client, path=PATH)

    assert data == b"original bytes"
    assert seen[0].url.raw_path.endswith(("/object/sources/" + PATH.replace(" ", "%20")).encode())
    assert len(seen[0].url.path.split("/object/sources/", 1)[1].split("/")) == 3


@pytest.mark.asyncio
async def test_download_maps_missing_object_to_own_error() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(404)),
        base_url="https://example.invalid/storage/v1",
    ) as client:
        with pytest.raises(StorageObjectMissing, match="storage_object_missing"):
            await download_source_object(client, path=PATH)


def test_storage_client_requires_worker_secret_and_carries_it() -> None:
    secret_key = "service" + "-key"
    settings = SimpleNamespace(
        SUPABASE_URL="https://example.invalid", SUPABASE_SECRET_KEY=secret_key
    )
    client = storage_client(settings)
    try:
        assert client.headers["apikey"] == secret_key
        assert str(client.base_url) == "https://example.invalid/storage/v1/"
    finally:
        asyncio.run(client.aclose())


def test_storage_client_rejects_settings_without_service_key() -> None:
    with pytest.raises(TypeError, match="SUPABASE_SECRET_KEY"):
        storage_client(SimpleNamespace(SUPABASE_URL="https://example.invalid"))
