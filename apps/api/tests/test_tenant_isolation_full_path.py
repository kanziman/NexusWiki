"""Full-path local Supabase tenant-isolation evidence (OPS-04)."""

# ruff: noqa: ASYNC212

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import httpx
import pytest

from api.errors import DatabaseError
from tests.conftest import LOCAL_STACK, TenantActor
from tests.fixtures.pipeline import PipelineHarness

TABLES = (
    "workspaces",
    "workspace_members",
    "raw_sources",
    "wiki_pages",
    "source_chunks",
    "wiki_embeddings",
    "wiki_links",
    "prompt_templates",
    "jobs",
)


def _headers(actor: TenantActor | None) -> dict[str, str]:
    headers = {"apikey": LOCAL_STACK["publishable_key"]}
    if actor is not None:
        headers["Authorization"] = f"Bearer {actor.access_token}"
    return headers


def _admin_headers() -> dict[str, str]:
    key = LOCAL_STACK["admin_key"]
    return {"apikey": key, "Authorization": f"Bearer {key}"}


@dataclass(frozen=True)
class IsolationDataset:
    """Existing pipeline rows; admin access is setup-only and never an assertion path."""

    workspace_id: str
    ids: dict[str, str]
    storage_path: str


@pytest.fixture
async def pipeline_isolation_dataset(
    isolation_principals: tuple[TenantActor, ...], local_stack: httpx.Client, authed_client: Any
) -> IsolationDataset:
    owner_a, editor_a = isolation_principals[:2]
    # This is the one D-04 text/file/URL source set.  It reaches real queue, worker,
    # RLS and Storage before this suite derives no requester-creatable records.
    async with PipelineHarness(local_stack, authed_client, owner_a) as pipeline:
        created = await pipeline.create_three_sources()
        await pipeline.drain()

    source_id = created[0]["raw_source_id"]
    file_id = created[1]["raw_source_id"]
    raw = local_stack.get(
        "/rest/v1/raw_sources",
        params={"id": f"eq.{source_id}", "select": "id"},
        headers=_admin_headers(),
    ).json()[0]
    page = local_stack.get(
        "/rest/v1/wiki_pages",
        params={"workspace_id": f"eq.{owner_a.workspace_id}", "select": "id", "limit": "1"},
        headers=_admin_headers(),
    ).json()[0]
    chunk = local_stack.get(
        "/rest/v1/source_chunks",
        params={"raw_source_id": f"eq.{source_id}", "select": "id", "limit": "1"},
        headers=_admin_headers(),
    ).json()[0]
    embedding = local_stack.get(
        "/rest/v1/wiki_embeddings",
        params={"wiki_id": f"eq.{page['id']}", "select": "id", "limit": "1"},
        headers=_admin_headers(),
    ).json()[0]
    # Link rows have no requester-visible creation path; this is deliberately
    # narrow service-role setup, while every assertion below uses a user JWT.
    link_response = local_stack.post(
        "/rest/v1/wiki_links",
        headers={**_admin_headers(), "Prefer": "return=representation"},
        json={
            "workspace_id": owner_a.workspace_id,
            "from_wiki_id": page["id"],
            "target_slug": f"isolation-target-{uuid4().hex}",
        },
    )
    link_response.raise_for_status()
    link = link_response.json()[0]
    job = local_stack.get(
        "/rest/v1/jobs",
        params={"workspace_id": f"eq.{owner_a.workspace_id}", "select": "id", "limit": "1"},
        headers=_admin_headers(),
    ).json()[0]
    template = local_stack.post(
        "/rest/v1/prompt_templates",
        headers={**_headers(editor_a), "Prefer": "return=representation"},
        json={
            "workspace_id": owner_a.workspace_id,
            "name": f"isolation-{uuid4().hex}",
            "target_type": "ask",
            "system_prompt": "system",
            "template": "template",
        },
    )
    template.raise_for_status()
    return IsolationDataset(
        workspace_id=owner_a.workspace_id,
        ids={
            "workspaces": owner_a.workspace_id,
            "workspace_members": owner_a.user_id,
            "raw_sources": raw["id"],
            "wiki_pages": page["id"],
            "source_chunks": chunk["id"],
            "wiki_embeddings": embedding["id"],
            "wiki_links": link["id"],
            "prompt_templates": template.json()[0]["id"],
            "jobs": job["id"],
        },
        storage_path=local_stack.get(
            "/rest/v1/raw_sources",
            params={"id": f"eq.{file_id}", "select": "storage_path"},
            headers=_admin_headers(),
        ).json()[0]["storage_path"],
    )


async def test_isolation_fixture_supplies_distinct_role_complete_principals(
    isolation_principals,
) -> None:
    owner_a, editor_a, viewer_a, owner_b, non_member = isolation_principals
    assert len({actor.user_id for actor in isolation_principals}) == 5
    assert owner_a.workspace_id == editor_a.workspace_id == viewer_a.workspace_id
    assert owner_a.workspace_id != owner_b.workspace_id
    assert non_member.workspace_id not in {owner_a.workspace_id, owner_b.workspace_id}


@pytest.mark.parametrize("table", TABLES)
async def test_each_table_has_owner_control_and_bidirectional_foreign_read_denial(
    table: str,
    pipeline_isolation_dataset: IsolationDataset,
    isolation_principals: tuple[TenantActor, ...],
    local_stack: httpx.Client,
) -> None:
    """All nine RLS tables expose own rows and hide them from B and from a non-member."""
    owner_a, _editor_a, _viewer_a, owner_b, non_member = isolation_principals
    dataset = pipeline_isolation_dataset
    filters = {"id": f"eq.{dataset.ids[table]}", "select": "id"}
    if table == "workspace_members":
        filters = {
            "workspace_id": f"eq.{dataset.workspace_id}",
            "user_id": f"eq.{dataset.ids[table]}",
            "select": "user_id",
        }
    own = local_stack.get(f"/rest/v1/{table}", params=filters, headers=_headers(owner_a))
    assert own.status_code == 200, own.text
    assert len(own.json()) == 1
    for foreign in (owner_b, non_member):
        blocked = local_stack.get(f"/rest/v1/{table}", params=filters, headers=_headers(foreign))
        assert blocked.status_code == 200, blocked.text
        assert blocked.json() == []


async def test_editor_viewer_and_anonymous_controls_are_not_confused_with_isolation(
    pipeline_isolation_dataset: IsolationDataset,
    isolation_principals: tuple[TenantActor, ...],
    local_stack: httpx.Client,
) -> None:
    owner_a, editor_a, viewer_a, _owner_b, _non_member = isolation_principals
    params = {"id": f"eq.{pipeline_isolation_dataset.ids['raw_sources']}", "select": "id"}
    for member in (owner_a, editor_a, viewer_a):
        assert local_stack.get(
            "/rest/v1/raw_sources", params=params, headers=_headers(member)
        ).json()
    anonymous = local_stack.get("/rest/v1/raw_sources", params=params, headers=_headers(None))
    assert anonymous.status_code in {401, 403}


async def test_requester_writes_use_api_mapping_and_direct_with_check_denials(
    pipeline_isolation_dataset: IsolationDataset,
    isolation_principals: tuple[TenantActor, ...],
    authed_client: Any,
    user_db: Any,
) -> None:
    """API writes map 0-row RLS effects to 403; definer RPC violations retain 42501."""
    owner_a, editor_a, _viewer_a, owner_b, _non_member = isolation_principals
    dataset = pipeline_isolation_dataset
    async with user_db(editor_a) as db:
        own = await db.insert_one(
            "prompt_templates",
            values={
                "workspace_id": dataset.workspace_id,
                "name": f"control-{uuid4().hex}",
                "target_type": "ask",
                "system_prompt": "system",
                "template": "template",
            },
        )
        assert own["workspace_id"] == dataset.workspace_id
    async with authed_client(owner_a) as client:
        # Router mapping makes an RLS-blocked source creation canonical 403.
        foreign = await client.post(
            f"/workspaces/{owner_b.workspace_id}/sources/text",
            json={"title": "foreign", "text": f"foreign-{uuid4().hex}"},
        )
    assert foreign.status_code == 403
    async with user_db(owner_b) as db:
        with pytest.raises(DatabaseError) as denied:
            await db.rpc(
                "enqueue_source_job",
                params={
                    "p_workspace_id": owner_b.workspace_id,
                    "p_raw_source_id": dataset.ids["raw_sources"],
                },
            )
    assert denied.value.sqlstate == "42501"


async def test_storage_file_and_queue_reads_follow_requester_jwt(
    pipeline_isolation_dataset: IsolationDataset,
    isolation_principals: tuple[TenantActor, ...],
    local_stack: httpx.Client,
) -> None:
    owner_a, _editor_a, _viewer_a, owner_b, non_member = isolation_principals
    path = pipeline_isolation_dataset.storage_path
    for actor in (owner_a,):
        allowed = local_stack.get(f"/storage/v1/object/sources/{path}", headers=_headers(actor))
        assert allowed.status_code == 200, allowed.text
    for actor in (owner_b, non_member):
        blocked = local_stack.get(f"/storage/v1/object/sources/{path}", headers=_headers(actor))
        assert blocked.status_code in {400, 401, 403, 404}
    foreign_jobs = local_stack.get(
        "/rest/v1/jobs",
        params={"workspace_id": f"eq.{pipeline_isolation_dataset.workspace_id}", "select": "id"},
        headers=_headers(owner_b),
    )
    assert foreign_jobs.status_code == 200 and foreign_jobs.json() == []
