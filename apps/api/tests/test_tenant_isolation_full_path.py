"""Full-path local Supabase tenant-isolation evidence (OPS-04)."""

# ruff: noqa: ASYNC212

from __future__ import annotations

from collections.abc import Callable
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

# This is intentionally a public-boundary registry, rather than a claim that
# all tables have a CRUD UI.  `UserDb` is the application's requester-JWT
# PostgREST boundary when a route does not exist.  The four worker-derived
# tables below have *no* legitimate client mutation surface: their expected
# own-workspace result is therefore the same explicit 42501 denial as a foreign
# attempt.  The test keeps that product boundary explicit instead of silently
# using the service role to manufacture a misleading "allowed" control.
MUTATION_BOUNDARIES = {
    "workspaces": "PATCH/DELETE /workspaces/{id}",
    "workspace_members": "requester-JWT UserDb (owner-only membership administration)",
    "raw_sources": "POST /workspaces/{id}/sources/{text,file,url}; requester-JWT delete",
    "wiki_pages": (
        "PATCH /workspaces/{id}/wiki/{id}/verify; "
        "PUT/DELETE /workspaces/{id}/wiki/{id}/publication; "
        "requester-JWT UserDb for policy-only CRUD"
    ),
    "source_chunks": "no client mutation; worker/service-role only",
    "wiki_embeddings": "no client mutation; worker/service-role only",
    "wiki_links": "no client mutation; compiler/service-role only",
    "prompt_templates": "requester-JWT UserDb CRUD",
    "jobs": "POST retry/cancel and enqueue RPC; no direct client table mutation",
}
DERIVED_READ_ONLY_TABLES = ("source_chunks", "wiki_embeddings", "wiki_links", "jobs")
_PATCH_VALUES = {
    "workspaces": {"name": "isolation-update"},
    "workspace_members": {"role": "viewer"},
    "raw_sources": {"title": "immutable-source"},
    "wiki_pages": {"title": "isolation-update"},
    "source_chunks": {"content": "forbidden"},
    "wiki_embeddings": {"chunk_content": "forbidden"},
    "wiki_links": {"target_slug": "forbidden"},
    "prompt_templates": {"template": "isolation-update"},
    "jobs": {"type": "forbidden"},
}


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
    foreign_ids: dict[str, str]
    storage_path: str


@pytest.fixture
async def pipeline_isolation_dataset(
    isolation_principals: tuple[TenantActor, ...],
    local_stack: httpx.Client,
    authed_client: Any,
    workspace_member_with_role: Callable[[TenantActor, str], TenantActor],
) -> IsolationDataset:
    owner_a, editor_a, _viewer_a, owner_b, _non_member = isolation_principals
    editor_b = workspace_member_with_role(owner_b, "editor")
    # This is the one D-04 text/file/URL source set.  It reaches real queue, worker,
    # RLS and Storage before this suite derives no requester-creatable records.
    async with PipelineHarness(local_stack, authed_client, owner_a) as pipeline:
        created = await pipeline.create_three_sources()
        await pipeline.drain()

    # A second API-created fixture set is deliberately minimal in purpose: it
    # gives A a real B-owned target for the reverse direction.  It uses the
    # exact same D-04 text/file/URL fixture contract rather than inventing a
    # privileged data path for raw sources or jobs.
    async with PipelineHarness(local_stack, authed_client, owner_b) as pipeline_b:
        created_b = await pipeline_b.create_three_sources()
        await pipeline_b.drain()

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
    page_b = local_stack.get(
        "/rest/v1/wiki_pages",
        params={"workspace_id": f"eq.{owner_b.workspace_id}", "select": "id", "limit": "1"},
        headers=_admin_headers(),
    ).json()[0]
    source_b = created_b[0]["raw_source_id"]
    chunk_b = local_stack.get(
        "/rest/v1/source_chunks",
        params={"raw_source_id": f"eq.{source_b}", "select": "id", "limit": "1"},
        headers=_admin_headers(),
    ).json()[0]
    embedding_b = local_stack.get(
        "/rest/v1/wiki_embeddings",
        params={"wiki_id": f"eq.{page_b['id']}", "select": "id", "limit": "1"},
        headers=_admin_headers(),
    ).json()[0]
    link_b_response = local_stack.post(
        "/rest/v1/wiki_links",
        headers={**_admin_headers(), "Prefer": "return=representation"},
        json={
            "workspace_id": owner_b.workspace_id,
            "from_wiki_id": page_b["id"],
            "target_slug": f"isolation-target-{uuid4().hex}",
        },
    )
    link_b_response.raise_for_status()
    template_b = local_stack.post(
        "/rest/v1/prompt_templates",
        headers={**_headers(owner_b), "Prefer": "return=representation"},
        json={
            "workspace_id": owner_b.workspace_id,
            "name": f"isolation-{uuid4().hex}",
            "target_type": "ask",
            "system_prompt": "system",
            "template": "template",
        },
    )
    template_b.raise_for_status()
    job_b = local_stack.get(
        "/rest/v1/jobs",
        params={"workspace_id": f"eq.{owner_b.workspace_id}", "select": "id", "limit": "1"},
        headers=_admin_headers(),
    ).json()[0]
    return IsolationDataset(
        workspace_id=owner_a.workspace_id,
        ids={
            "workspaces": owner_a.workspace_id,
            "workspace_members": editor_a.user_id,
            "raw_sources": raw["id"],
            "wiki_pages": page["id"],
            "source_chunks": chunk["id"],
            "wiki_embeddings": embedding["id"],
            "wiki_links": link["id"],
            "prompt_templates": template.json()[0]["id"],
            "jobs": job["id"],
        },
        foreign_ids={
            "workspaces": owner_b.workspace_id,
            "workspace_members": editor_b.user_id,
            "raw_sources": source_b,
            "wiki_pages": page_b["id"],
            "source_chunks": chunk_b["id"],
            "wiki_embeddings": embedding_b["id"],
            "wiki_links": link_b_response.json()[0]["id"],
            "prompt_templates": template_b.json()[0]["id"],
            "jobs": job_b["id"],
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


@pytest.mark.parametrize("table", TABLES)
async def test_requester_jwt_update_matrix_has_own_controls_and_both_foreign_directions(
    table: str,
    pipeline_isolation_dataset: IsolationDataset,
    isolation_principals: tuple[TenantActor, ...],
    local_stack: httpx.Client,
) -> None:
    """Every table declares its mutation boundary and proves its RLS outcome.

    Writable rows return one representation for their own owner.  The
    immutable/derived public boundary deliberately returns 42501 even to the
    owner; foreign updates must never become writable in either direction.
    """
    owner_a, _editor_a, _viewer_a, owner_b, non_member = isolation_principals
    dataset = pipeline_isolation_dataset

    def patch(actor: TenantActor, row_id: str) -> httpx.Response:
        params = {"id": f"eq.{row_id}"}
        if table == "workspace_members":
            workspace_id = (
                owner_b.workspace_id
                if row_id == dataset.foreign_ids[table]
                else owner_a.workspace_id
            )
            params = {"workspace_id": f"eq.{workspace_id}", "user_id": f"eq.{row_id}"}
        return local_stack.patch(
            f"/rest/v1/{table}",
            params=params,
            headers={**_headers(actor), "Prefer": "return=representation"},
            json=_PATCH_VALUES[table],
        )

    # Own controls distinguish an intentional read-only boundary from a suite
    # that would pass merely because every request is denied.
    own_a = patch(owner_a, dataset.ids[table])
    own_b = patch(owner_b, dataset.foreign_ids[table])
    if table in DERIVED_READ_ONLY_TABLES or table == "raw_sources":
        # These policies have no UPDATE grant.  PostgREST exposes that as the
        # database's 42501, not as the 0-row behavior of a filtered writable
        # policy.  Assert the distinction so a grant/policy regression cannot
        # hide behind a generic forbidden response.
        assert own_a.status_code == own_b.status_code == 403, MUTATION_BOUNDARIES[table]
        assert own_a.json()["code"] == own_b.json()["code"] == "42501"
    else:
        assert own_a.status_code == own_b.status_code == 200, MUTATION_BOUNDARIES[table]
        assert len(own_a.json()) == len(own_b.json()) == 1, MUTATION_BOUNDARIES[table]

    # A -> B and B -> A are separate requests over real requester JWTs.
    for actor, foreign_id in (
        (owner_a, dataset.foreign_ids[table]),
        (owner_b, dataset.ids[table]),
        (non_member, dataset.ids[table]),
    ):
        blocked = patch(actor, foreign_id)
        if table in DERIVED_READ_ONLY_TABLES or table == "raw_sources":
            assert blocked.status_code == 403 and blocked.json()["code"] == "42501"
        else:
            assert blocked.status_code == 200, blocked.text
            assert blocked.json() == [], f"{table}: {MUTATION_BOUNDARIES[table]}"

    anonymous_params = {"id": f"eq.{dataset.ids[table]}"}
    if table == "workspace_members":
        anonymous_params = {
            "workspace_id": f"eq.{owner_a.workspace_id}",
            "user_id": f"eq.{dataset.ids[table]}",
        }
    anonymous = local_stack.patch(
        f"/rest/v1/{table}",
        params=anonymous_params,
        headers={**_headers(None), "Prefer": "return=representation"},
        json=_PATCH_VALUES[table],
    )
    assert anonymous.status_code in {401, 403}


@pytest.mark.parametrize("table", TABLES)
async def test_requester_jwt_delete_matrix_blocks_both_foreign_directions(
    table: str,
    pipeline_isolation_dataset: IsolationDataset,
    isolation_principals: tuple[TenantActor, ...],
    local_stack: httpx.Client,
) -> None:
    """DELETE has the same requester-JWT isolation contract as UPDATE.

    Cross-tenant attempts occur before each owner's destructive control, so the
    test proves both denial and the legitimate owning mutation without using a
    worker or service-role assertion path.
    """
    owner_a, _editor_a, _viewer_a, owner_b, non_member = isolation_principals
    dataset = pipeline_isolation_dataset

    def delete(actor: TenantActor, row_id: str) -> httpx.Response:
        params = {"id": f"eq.{row_id}"}
        if table == "workspace_members":
            workspace_id = (
                owner_b.workspace_id
                if row_id == dataset.foreign_ids[table]
                else owner_a.workspace_id
            )
            params = {"workspace_id": f"eq.{workspace_id}", "user_id": f"eq.{row_id}"}
        return local_stack.delete(
            f"/rest/v1/{table}",
            params=params,
            headers={**_headers(actor), "Prefer": "return=representation"},
        )

    for actor, foreign_id in (
        (owner_a, dataset.foreign_ids[table]),
        (owner_b, dataset.ids[table]),
        (non_member, dataset.ids[table]),
    ):
        blocked = delete(actor, foreign_id)
        if table in DERIVED_READ_ONLY_TABLES:
            assert blocked.status_code == 403 and blocked.json()["code"] == "42501"
        else:
            assert blocked.status_code == 200, blocked.text
            assert blocked.json() == [], f"{table}: {MUTATION_BOUNDARIES[table]}"

    own_a = delete(owner_a, dataset.ids[table])
    own_b = delete(owner_b, dataset.foreign_ids[table])
    if table in DERIVED_READ_ONLY_TABLES:
        assert own_a.status_code == own_b.status_code == 403
        assert own_a.json()["code"] == own_b.json()["code"] == "42501"
    else:
        assert own_a.status_code == own_b.status_code == 200
        assert len(own_a.json()) == len(own_b.json()) == 1

    anonymous_params = {"id": f"eq.{dataset.ids[table]}"}
    if table == "workspace_members":
        anonymous_params = {
            "workspace_id": f"eq.{owner_a.workspace_id}",
            "user_id": f"eq.{dataset.ids[table]}",
        }
    anonymous = local_stack.delete(
        f"/rest/v1/{table}",
        params=anonymous_params,
        headers={**_headers(None), "Prefer": "return=representation"},
    )
    assert anonymous.status_code in {401, 403}


async def test_supported_api_insert_surfaces_have_controls_and_all_requester_denials(
    isolation_principals: tuple[TenantActor, ...], authed_client: Any
) -> None:
    """The API-created source/job path is the supported public INSERT boundary."""
    owner_a, _editor_a, _viewer_a, owner_b, non_member = isolation_principals

    async def create(actor: TenantActor, workspace_id: str) -> int:
        async with authed_client(actor) as client:
            response = await client.post(
                f"/workspaces/{workspace_id}/sources/text",
                json={"title": f"matrix-{uuid4().hex}", "text": "requester mutation matrix"},
            )
        return response.status_code

    assert await create(owner_a, owner_a.workspace_id) == 202
    assert await create(owner_b, owner_b.workspace_id) == 202
    for actor, foreign_workspace in (
        (owner_a, owner_b.workspace_id),
        (owner_b, owner_a.workspace_id),
        (non_member, owner_a.workspace_id),
    ):
        assert await create(actor, foreign_workspace) == 403
    async with authed_client(None) as client:
        anonymous = await client.post(
            f"/workspaces/{owner_a.workspace_id}/sources/text",
            json={"title": "anonymous", "text": "denied"},
        )
    assert anonymous.status_code == 401
