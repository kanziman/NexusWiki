"""Full-path local Supabase tenant-isolation evidence (OPS-04)."""

from __future__ import annotations


async def test_isolation_fixture_supplies_distinct_role_complete_principals(
    isolation_principals,
) -> None:
    owner_a, editor_a, viewer_a, owner_b, non_member = isolation_principals
    assert len({actor.user_id for actor in isolation_principals}) == 5
    assert owner_a.workspace_id == editor_a.workspace_id == viewer_a.workspace_id
    assert owner_a.workspace_id != owner_b.workspace_id
    assert non_member.workspace_id not in {owner_a.workspace_id, owner_b.workspace_id}
