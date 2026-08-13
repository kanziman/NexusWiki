"""Real-local-stack ingest-to-retrieval tracer (OPS-02)."""

import pytest

from tests.fixtures.pipeline import PipelineHarness


@pytest.mark.asyncio
async def test_ingest_pipeline_reaches_retrieval(
    two_workspaces_two_users, local_stack, authed_client
) -> None:
    owner, _ = two_workspaces_two_users
    async with PipelineHarness(local_stack, authed_client, owner) as pipeline:
        created = await pipeline.create_three_sources()
        await pipeline.drain()
        await pipeline.assert_retrieval(created)
