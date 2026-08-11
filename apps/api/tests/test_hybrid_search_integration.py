"""Local-stack proof that authenticated retrieval RPCs keep the requester RLS boundary."""

from typing import Any

import pytest


@pytest.mark.asyncio
async def test_authenticated_tenants_cannot_read_each_others_retrieval_scope(
    two_workspaces_two_users: tuple[Any, Any], user_db: Any
) -> None:
    """A real JWT is used in both directions; a foreign workspace has no rows."""
    alice, bob = two_workspaces_two_users
    assert alice.workspace_id != bob.workspace_id

    async with user_db(alice) as alice_db:
        alice_foreign = await alice_db.rpc(
            "search_source_lexical",
            params={
                "p_workspace_id": bob.workspace_id,
                "p_bigrams": "ne ex xu us",
                "p_tokenizer_version": "bigram-nfkc-cf-v1",
                "p_k": 1,
            },
        )
    async with user_db(bob) as bob_db:
        bob_foreign = await bob_db.rpc(
            "search_source_lexical",
            params={
                "p_workspace_id": alice.workspace_id,
                "p_bigrams": "ne ex xu us",
                "p_tokenizer_version": "bigram-nfkc-cf-v1",
                "p_k": 1,
            },
        )

    assert alice_foreign == []
    assert bob_foreign == []
