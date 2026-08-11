"""API-04 제한 그래프 읽기의 로컬 스택 회귀."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import status


async def test_authenticated_tenants_cannot_read_each_others_graph_scope(
    two_workspaces_two_users: tuple[Any, Any], user_db: Any
) -> None:
    """실제 requester JWT 양방향에서 foreign workspace RPC는 빈 목록이다."""
    alice, bob = two_workspaces_two_users
    async with user_db(alice) as alice_db:
        alice_foreign = await alice_db.rpc(
            "wiki_graph_neighborhood",
            params={
                "p_workspace_id": bob.workspace_id,
                "p_seed_wiki_id": str(uuid4()),
                "p_fanout": 10,
                "p_total_limit": 100,
            },
        )
    async with user_db(bob) as bob_db:
        bob_foreign = await bob_db.rpc(
            "wiki_graph_neighborhood",
            params={
                "p_workspace_id": alice.workspace_id,
                "p_seed_wiki_id": str(uuid4()),
                "p_fanout": 10,
                "p_total_limit": 100,
            },
        )
    assert alice_foreign == []
    assert bob_foreign == []


async def test_graph_endpoint_returns_resolved_outgoing_edges(
    two_workspaces_two_users: tuple[Any, Any],
    authed_client: Any,
    seed_wiki_link: Any,
    user_db: Any,
) -> None:
    """소유자 JWT가 만든 두 해소 간선을 깊이 1로만 돌려준다."""
    owner, _ = two_workspaces_two_users
    async with user_db(owner) as db:
        pages = [
            await db.insert_one(
                "wiki_pages",
                values={
                    "workspace_id": owner.workspace_id,
                    "slug": f"graph-{index}-{uuid4().hex}",
                    "title": f"Graph {index}",
                    "category": "concepts",
                    "content": "graph content",
                },
            )
            for index in range(3)
        ]
    for target in pages[1:]:
        seed_wiki_link(owner.workspace_id, pages[0]["id"], target["id"], target["slug"])
    async with authed_client(owner) as client:
        response = await client.get(
            f"/workspaces/{owner.workspace_id}/graph", params={"seed_wiki_id": pages[0]["id"]}
        )
    assert response.status_code == status.HTTP_200_OK
    edges = {
        (edge["from_wiki_id"], edge["to_wiki_id"], edge["depth"])
        for edge in response.json()["edges"]
    }
    assert edges == {
        (pages[0]["id"], pages[1]["id"], 1),
        (pages[0]["id"], pages[2]["id"], 1),
    }


async def test_graph_bounds_are_rejected_before_the_rpc(
    two_workspaces_two_users: tuple[Any, Any], authed_client: Any
) -> None:
    owner, _ = two_workspaces_two_users
    path = f"/workspaces/{owner.workspace_id}/graph?seed_wiki_id={uuid4()}"
    async with authed_client(owner) as client:
        bad_fanout = await client.get(f"{path}&fanout=21")
        bad_total_limit = await client.get(f"{path}&total_limit=201")
    assert bad_fanout.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert bad_total_limit.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
