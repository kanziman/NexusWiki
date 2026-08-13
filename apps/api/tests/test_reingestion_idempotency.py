"""Local-Supabase duplicate and shrinking-reprocess evidence (OPS-03)."""

import pytest

from tests.fixtures.pipeline import PipelineHarness


@pytest.mark.asyncio
async def test_duplicate_normalized_text_does_not_grow_rows(
    two_workspaces_two_users, local_stack, authed_client
) -> None:
    owner, _ = two_workspaces_two_users
    async with PipelineHarness(local_stack, authed_client, owner) as pipeline:
        source = await pipeline.create_text("같은 본문", "  같은   본문\n")
        await pipeline.drain()
        before = await pipeline.row_counts()
        duplicate_status = await pipeline.create_duplicate_text("같은 본문", "같은 본문")
        assert duplicate_status == 409
        assert await pipeline.row_counts() == before
        assert source["raw_source_id"]


@pytest.mark.asyncio
async def test_shorter_reprocess_removes_stale_chunks_and_embeddings(
    two_workspaces_two_users, local_stack, authed_client
) -> None:
    owner, _ = two_workspaces_two_users
    async with PipelineHarness(local_stack, authed_client, owner) as pipeline:
        source = await pipeline.create_text("긴 본문", "긴 증거 " * 2500)
        await pipeline.drain()
        old_count = await pipeline.source_chunk_count(source["raw_source_id"])
        assert old_count > 1
        await pipeline.reprocess_text(source["raw_source_id"], "짧은 증거 " * 50)
        await pipeline.drain()
        await pipeline.assert_shrunk(source["raw_source_id"], old_count)
