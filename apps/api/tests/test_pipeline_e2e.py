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


@pytest.mark.asyncio
async def test_whole_chain_and_its_usage_share_one_trace(
    two_workspaces_two_users, local_stack, authed_client
) -> None:
    owner, _ = two_workspaces_two_users
    async with PipelineHarness(local_stack, authed_client, owner) as pipeline:
        await pipeline.create_text("trace 체인", "체인 전 단계의 추적을 확인하는 본문입니다. " * 20)
        await pipeline.drain()
        await pipeline.assert_single_trace_across_chain()


@pytest.mark.asyncio
async def test_reprocessing_adds_usage_rows_and_never_overwrites_earlier_ones(
    two_workspaces_two_users, local_stack, authed_client
) -> None:
    # 비용은 호출마다 이미 지불한 값이다. 재실행이 앞선 행을 덮어쓰면 월 상한이 조용히 줄어든다.
    owner, _ = two_workspaces_two_users
    async with PipelineHarness(local_stack, authed_client, owner) as pipeline:
        created = await pipeline.create_text("재실행", "재실행 전의 본문입니다. " * 20)
        await pipeline.drain()
        before = await pipeline.usage_rows()

        await pipeline.reprocess_text(created["raw_source_id"], "재실행 뒤의 본문입니다. " * 20)
        await pipeline.drain()
        after = await pipeline.usage_rows()

    assert before
    assert len(after) > len(before)
    after_by_id = {row["id"]: row for row in after}
    assert all(after_by_id[row["id"]] == row for row in before)
