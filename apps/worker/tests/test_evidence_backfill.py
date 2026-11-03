"""근거 백필의 무쓰기 보고서·검토·원자적 추가 회귀 (#211~#213)."""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest
from apps.api.tests.conftest import LOCAL_STACK
from apps.api.tests.conftest import local_stack as local_stack
from apps.api.tests.conftest import two_workspaces_two_users as two_workspaces_two_users

from worker.evidence_backfill import (
    SCHEMA,
    BackfillError,
    _bytes,
    _connection,
    _report,
    _safe_directory,
    _score,
    apply_approved,
    export_candidates,
    main,
    validate_files,
)


def _headers() -> dict[str, str]:
    key = LOCAL_STACK["admin_key"]
    return {"apikey": key, "Authorization": f"Bearer {key}", "Prefer": "return=representation"}


def _insert(stack: httpx.Client, table: str, rows: Any) -> Any:
    response = stack.post(f"/rest/v1/{table}", headers=_headers(), json=rows)
    assert response.status_code < 400, response.text
    return response.json()


def _rpc(
    stack: httpx.Client, name: str, body: dict[str, Any], headers: Any = None
) -> httpx.Response:
    return stack.post(f"/rest/v1/rpc/{name}", headers=headers or _headers(), json=body)


def _rows(stack: httpx.Client, table: str, workspace: str) -> list[dict[str, Any]]:
    response = stack.get(
        f"/rest/v1/{table}",
        headers=_headers(),
        params={"workspace_id": f"eq.{workspace}", "order": "id"}
        if table != "wiki_page_evidence"
        else {"workspace_id": f"eq.{workspace}", "order": "wiki_id,chunk_id"},
    )
    assert response.status_code < 400, response.text
    return response.json()


def _seed(stack: httpx.Client, owner: Any) -> tuple[str, str, list[dict[str, Any]]]:
    source = _insert(
        stack,
        "raw_sources",
        {
            "workspace_id": owner.workspace_id,
            "title": "원문",
            "source_type": "text",
            "content": "근거 문장😀\n다른 문장",
            "content_hash": uuid4().hex,
        },
    )[0]
    wiki = _insert(
        stack,
        "wiki_pages",
        {
            "workspace_id": owner.workspace_id,
            "slug": uuid4().hex,
            "title": "검증 제목",
            "category": "concepts",
            "content": "검증된 근거 문장😀",
            "sources": [source["id"]],
            "verification_status": "verified",
            "explored": True,
        },
    )[0]
    chunks = _insert(
        stack,
        "source_chunks",
        [
            {
                "workspace_id": owner.workspace_id,
                "raw_source_id": source["id"],
                "chunk_index": 0,
                "content": "근거 문장😀",
                "char_start": 0,
                "char_end": len("근거 문장😀"),
            },
            {
                "workspace_id": owner.workspace_id,
                "raw_source_id": source["id"],
                "chunk_index": 1,
                "content": "다른 문장",
                "char_start": len("근거 문장😀\n"),
                "char_end": len("근거 문장😀\n다른 문장"),
            },
        ],
    )
    return wiki["id"], source["id"], chunks


def _candidates(stack: httpx.Client, workspace: str) -> dict[str, Any]:
    response = _rpc(stack, "wiki_evidence_backfill_candidates", {"p_workspace_id": workspace})
    assert response.status_code == 200, response.text
    return response.json()


def _entries(batch: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "wiki_id": item["page"]["id"],
            "raw_source_id": chunk["raw_source_id"],
            "chunk_id": chunk["id"],
            "page_token": item["page_token"],
            "source_token": chunk["source_token"],
            "chunk_token": chunk["chunk_token"],
        }
        for item in batch["pages"]
        for chunk in item["chunks"]
    ]


def _approve(directory: Path, entries: list[dict[str, str]]) -> tuple[Path, Path]:
    candidates, approvals = directory / "candidates.json", directory / "approvals.json"
    document = json.loads(approvals.read_bytes())
    document["approved"] = [
        {key: row[key] for key in ("wiki_id", "raw_source_id", "chunk_id")} for row in entries
    ]
    approvals.write_bytes(_bytes(document))
    return candidates, approvals


def _files(tmp_path: Path) -> tuple[Path, Path]:
    workspace, wiki, source, chunk = [str(uuid4()) for _ in range(4)]
    manifest = {
        "schema": SCHEMA,
        "workspace_id": workspace,
        "pages": [
            {
                "page": {
                    "id": wiki,
                    "workspace_id": workspace,
                    "sources": [source],
                    "title": "<script>secret</script>",
                    "content": "<img src=x onerror=alert(1)>",
                    "verification_status": "verified",
                },
                "page_token": "a" * 64,
                "chunks": [
                    {
                        "id": chunk,
                        "workspace_id": workspace,
                        "raw_source_id": source,
                        "source_token": "b" * 64,
                        "chunk_token": "c" * 64,
                        "valid_coordinates": True,
                        "already_linked": False,
                        "content": "청크",
                        "chunk_index": 0,
                        "char_start": 0,
                        "char_end": 2,
                        "score": 0.0,
                    }
                ],
            }
        ],
    }
    raw = _bytes(manifest)
    candidates, approvals = tmp_path / "candidates.json", tmp_path / "approvals.json"
    candidates.write_bytes(raw)
    approvals.write_bytes(
        _bytes(
            {
                "schema": SCHEMA,
                "workspace_id": workspace,
                "candidates_sha256": hashlib.sha256(raw).hexdigest(),
                "approved": [],
            }
        )
    )
    return candidates, approvals


def test_html_and_local_validation_need_no_database(tmp_path: Path, monkeypatch: Any) -> None:
    candidates, approvals = _files(tmp_path)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    assert main(["validate", "--candidates", str(candidates), "--approvals", str(approvals)]) == 0
    manifest, entries = validate_files(candidates, approvals)
    report = _report(manifest)
    assert "<script>" not in report
    assert "<img " not in report
    assert "&lt;script&gt;" in report
    assert "default-src" in report
    assert entries == []
    assert _score("가나다", "xyz") == 0
    assert _score("Ａ B", "a b") == 1


@pytest.mark.parametrize("kind", ["hash", "workspace", "duplicate", "foreign", "limit", "fields"])
def test_invalid_review_is_rejected_before_database(tmp_path: Path, kind: str) -> None:
    candidates, approvals = _files(tmp_path)
    manifest = json.loads(candidates.read_bytes())
    item = manifest["pages"][0]
    pair = {
        "wiki_id": item["page"]["id"],
        "raw_source_id": item["chunks"][0]["raw_source_id"],
        "chunk_id": item["chunks"][0]["id"],
    }
    approval = json.loads(approvals.read_bytes())
    approval["approved"] = [pair]
    if kind == "hash":
        candidates.write_bytes(candidates.read_bytes() + b" ")
    elif kind == "workspace":
        approval["workspace_id"] = str(uuid4())
    elif kind == "duplicate":
        approval["approved"] = [pair, pair]
    elif kind == "foreign":
        pair["chunk_id"] = str(uuid4())
    elif kind == "limit":
        approval["approved"] = [pair] * 501
    else:
        pair["approve_all"] = True
    approvals.write_bytes(_bytes(approval))
    with pytest.raises(BackfillError):
        validate_files(candidates, approvals)


def test_duplicate_json_keys_are_rejected(tmp_path: Path) -> None:
    candidates, approvals = _files(tmp_path)
    approvals.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
    with pytest.raises(BackfillError, match="duplicate_json_key"):
        validate_files(candidates, approvals)


def test_repository_output_is_restricted() -> None:
    with pytest.raises(BackfillError, match="repository_output_not_ignored"):
        _safe_directory(Path.cwd() / "docs/evidence")
    assert _safe_directory(Path.cwd() / ".local/evidence-backfill/test").is_absolute()


@pytest.mark.parametrize(
    "url",
    [
        "https://key:secret@example.com",
        "http://remote.example",
        "https://example.com/?key=secret",
        "",
    ],
)
def test_connection_never_guesses_or_logs_credentials(monkeypatch: Any, url: str) -> None:
    monkeypatch.setenv("SUPABASE_URL", url)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "secret")
    with pytest.raises(BackfillError, match="explicit_connection_required") as exc:
        _connection()
    assert "secret" not in str(exc.value)


@pytest.mark.asyncio
async def test_empty_approval_makes_no_request(tmp_path: Path) -> None:
    candidates, approvals = _files(tmp_path)
    manifest, _ = validate_files(candidates, approvals)

    def forbidden(_: Any) -> Any:
        raise AssertionError("DB 호출 금지")

    async with httpx.AsyncClient(transport=httpx.MockTransport(forbidden)) as client:
        assert (await apply_approved(client, candidates, approvals, manifest["workspace_id"]))[
            "requested"
        ] == 0


@pytest.mark.asyncio
async def test_export_review_apply_repeat_and_quality_are_safe(
    local_stack: httpx.Client,
    two_workspaces_two_users: Any,
    tmp_path: Path,
) -> None:
    owner, _ = two_workspaces_two_users
    _seed(local_stack, owner)
    tables = (
        "wiki_pages",
        "wiki_embeddings",
        "wiki_links",
        "raw_sources",
        "source_chunks",
        "jobs",
        "usage_events",
        "wiki_page_revisions",
        "wiki_write_proposals",
    )
    before = {table: _rows(local_stack, table, owner.workspace_id) for table in tables}
    async with httpx.AsyncClient(
        base_url=f"{LOCAL_STACK['url']}/rest/v1/", headers=_headers()
    ) as client:
        summary = await export_candidates(client, owner.workspace_id, tmp_path)
        assert summary == {"pages": 1, "candidate_pairs": 2, "pages_without_candidates": 0}
        assert _rows(local_stack, "wiki_page_evidence", owner.workspace_id) == []
        manifest, empty = validate_files(tmp_path / "candidates.json", tmp_path / "approvals.json")
        assert empty == []
        assert all(chunk["valid_coordinates"] for chunk in manifest["pages"][0]["chunks"])
        all_entries = _entries({"pages": manifest["pages"]})
        candidates, approvals = _approve(tmp_path, all_entries[:1])
        result = await apply_approved(client, candidates, approvals, owner.workspace_id)
        assert result["inserted"] == 1
        assert result["requested"] == 1
        assert (await apply_approved(client, candidates, approvals, owner.workspace_id))[
            "inserted"
        ] == 0
        assert await asyncio.to_thread(lambda: len(list(tmp_path.glob("apply-result*.json")))) == 2
        with pytest.raises(BackfillError, match="output_exists"):
            await export_candidates(client, owner.workspace_id, tmp_path)
    assert before == {table: _rows(local_stack, table, owner.workspace_id) for table in tables}
    assert len(_rows(local_stack, "wiki_page_evidence", owner.workspace_id)) == 1
    quality = _rpc(
        local_stack,
        "control_quality_snapshot",
        {"p_workspace_id": owner.workspace_id, "p_since": "2026-01-01T00:00:00Z"},
        {"apikey": LOCAL_STACK["publishable_key"], "Authorization": f"Bearer {owner.access_token}"},
    )
    assert quality.json()[0]["wiki_pages_with_evidence"] == 1


@pytest.mark.asyncio
async def test_export_walks_multiple_pages_and_keeps_unresolved(
    local_stack: httpx.Client,
    two_workspaces_two_users: Any,
    tmp_path: Path,
) -> None:
    owner, _ = two_workspaces_two_users
    _insert(
        local_stack,
        "wiki_pages",
        [
            {
                "workspace_id": owner.workspace_id,
                "slug": f"page-{index}",
                "title": "후보 없는 페이지",
                "content": "본문",
                "category": "concepts",
            }
            for index in range(53)
        ],
    )
    async with httpx.AsyncClient(
        base_url=f"{LOCAL_STACK['url']}/rest/v1/", headers=_headers()
    ) as client:
        summary = await export_candidates(client, owner.workspace_id, tmp_path)
    assert summary == {"pages": 53, "candidate_pairs": 0, "pages_without_candidates": 53}


@pytest.mark.parametrize("target", ["wiki_pages", "wiki_sources", "raw_sources", "source_chunks"])
def test_changed_content_rejects_the_entire_batch(
    local_stack: httpx.Client,
    two_workspaces_two_users: Any,
    target: str,
) -> None:
    owner, _ = two_workspaces_two_users
    wiki, source, chunks = _seed(local_stack, owner)
    entries = _entries(_candidates(local_stack, owner.workspace_id))
    table = "wiki_pages" if target in {"wiki_pages", "wiki_sources"} else target
    row_id = (
        wiki
        if target in {"wiki_pages", "wiki_sources"}
        else source
        if target == "raw_sources"
        else chunks[0]["id"]
    )
    body: dict[str, Any] = {"content": "바뀜"}
    if target == "wiki_sources":
        extra_source = _insert(
            local_stack,
            "raw_sources",
            {
                "workspace_id": owner.workspace_id,
                "title": "추가 원문",
                "source_type": "text",
                "content": "추가",
                "content_hash": uuid4().hex,
            },
        )[0]
        body = {"sources": [source, extra_source["id"]]}
    changed = local_stack.patch(
        f"/rest/v1/{table}",
        headers=_headers(),
        params={"id": f"eq.{row_id}"},
        json=body,
    )
    assert changed.status_code < 400, changed.text
    response = _rpc(
        local_stack,
        "apply_wiki_evidence_backfill",
        {"p_workspace_id": owner.workspace_id, "p_entries": entries},
    )
    assert response.status_code == 400
    assert _rows(local_stack, "wiki_page_evidence", owner.workspace_id) == []


@pytest.mark.parametrize("failure", ["missing", "foreign", "source", "duplicate", "limit"])
def test_invalid_pair_does_not_partially_apply(
    local_stack: httpx.Client,
    two_workspaces_two_users: Any,
    failure: str,
) -> None:
    owner, other = two_workspaces_two_users
    _seed(local_stack, owner)
    _seed(local_stack, other)
    entries = _entries(_candidates(local_stack, owner.workspace_id))
    if failure == "missing":
        entries[1]["chunk_id"] = str(uuid4())
    elif failure == "foreign":
        entries[1] = _entries(_candidates(local_stack, other.workspace_id))[0]
    elif failure == "source":
        source = _insert(
            local_stack,
            "raw_sources",
            {
                "workspace_id": owner.workspace_id,
                "title": "별도 원문",
                "source_type": "text",
                "content": "x",
                "content_hash": uuid4().hex,
            },
        )[0]
        entries[1]["raw_source_id"] = source["id"]
    elif failure == "duplicate":
        entries = [entries[0], entries[0]]
    else:
        entries = entries * 251
    response = _rpc(
        local_stack,
        "apply_wiki_evidence_backfill",
        {"p_workspace_id": owner.workspace_id, "p_entries": entries},
    )
    assert response.status_code == 400
    assert _rows(local_stack, "wiki_page_evidence", owner.workspace_id) == []
    assert _rows(local_stack, "wiki_page_evidence", other.workspace_id) == []


def test_rpc_permissions_and_existing_links_are_preserved(
    local_stack: httpx.Client,
    two_workspaces_two_users: Any,
) -> None:
    owner, _ = two_workspaces_two_users
    _seed(local_stack, owner)
    entries = _entries(_candidates(local_stack, owner.workspace_id))
    for token in (None, owner.access_token):
        headers = {"apikey": LOCAL_STACK["publishable_key"]}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        for rpc, body in (
            ("wiki_evidence_backfill_token", {"p_row": {"id": owner.workspace_id}}),
            ("wiki_evidence_backfill_candidates", {"p_workspace_id": owner.workspace_id}),
            (
                "apply_wiki_evidence_backfill",
                {"p_workspace_id": owner.workspace_id, "p_entries": entries},
            ),
        ):
            response = _rpc(local_stack, rpc, body, headers)
            assert response.status_code in (401, 403)
    for subset in (entries[:1], entries[1:], entries):
        response = _rpc(
            local_stack,
            "apply_wiki_evidence_backfill",
            {"p_workspace_id": owner.workspace_id, "p_entries": subset},
        )
        assert response.status_code == 200, response.text
    assert response.json()["inserted"] == 0
    assert len(_rows(local_stack, "wiki_page_evidence", owner.workspace_id)) == 2


def test_other_source_evidence_is_not_replaced(
    local_stack: httpx.Client,
    two_workspaces_two_users: Any,
) -> None:
    owner, _ = two_workspaces_two_users
    wiki, source, _ = _seed(local_stack, owner)
    _, other_source, other_chunks = _seed(local_stack, owner)
    response = local_stack.patch(
        "/rest/v1/wiki_pages",
        headers=_headers(),
        params={"id": f"eq.{wiki}"},
        json={"sources": [source, other_source]},
    )
    assert response.status_code < 400
    _insert(
        local_stack,
        "wiki_page_evidence",
        {
            "workspace_id": owner.workspace_id,
            "wiki_id": wiki,
            "raw_source_id": other_source,
            "chunk_id": other_chunks[0]["id"],
        },
    )
    entries = [
        row
        for row in _entries(_candidates(local_stack, owner.workspace_id))
        if row["wiki_id"] == wiki and row["raw_source_id"] == source
    ]
    response = _rpc(
        local_stack,
        "apply_wiki_evidence_backfill",
        {"p_workspace_id": owner.workspace_id, "p_entries": entries},
    )
    assert response.status_code == 200, response.text
    rows = _rows(local_stack, "wiki_page_evidence", owner.workspace_id)
    assert len(rows) == 3
    assert any(row["raw_source_id"] == other_source for row in rows)


def test_five_hundred_valid_pairs_fit_one_atomic_batch(
    local_stack: httpx.Client,
    two_workspaces_two_users: Any,
) -> None:
    owner, _ = two_workspaces_two_users
    _, source, _ = _seed(local_stack, owner)
    _insert(
        local_stack,
        "wiki_pages",
        [
            {
                "workspace_id": owner.workspace_id,
                "slug": f"boundary-{index}",
                "title": "본문 보존",
                "content": "근거 문장😀",
                "category": "concepts",
                "sources": [source],
            }
            for index in range(499)
        ],
    )
    entries = []
    cursor = None
    while True:
        response = _rpc(
            local_stack,
            "wiki_evidence_backfill_candidates",
            {"p_workspace_id": owner.workspace_id, "p_after_wiki_id": cursor},
        )
        assert response.status_code == 200, response.text
        batch = response.json()
        entries.extend(
            _entries({"pages": [{**row, "chunks": row["chunks"][:1]} for row in batch["pages"]]})
        )
        if not batch["has_more"]:
            break
        cursor = batch["next_cursor"]
    assert len(entries) == 500
    response = _rpc(
        local_stack,
        "apply_wiki_evidence_backfill",
        {"p_workspace_id": owner.workspace_id, "p_entries": entries},
    )
    assert response.status_code == 200, response.text
    assert response.json()["inserted"] == 500


@pytest.mark.asyncio
async def test_receipt_uses_the_reviewed_bytes_even_if_files_change(tmp_path: Path) -> None:
    candidates, approvals = _files(tmp_path)
    manifest, _ = validate_files(candidates, approvals)
    entry = _entries({"pages": manifest["pages"]})[0]
    _approve(tmp_path, [entry])
    original_hash = hashlib.sha256(approvals.read_bytes()).hexdigest()

    def handler(_: Any) -> httpx.Response:
        approvals.write_bytes(b"changed after validation")
        return httpx.Response(
            200,
            json={
                "requested": 1,
                "inserted": 1,
                "existing": 0,
                "inserted_pairs": [
                    {key: entry[key] for key in ("wiki_id", "raw_source_id", "chunk_id")}
                ],
            },
        )

    async with httpx.AsyncClient(
        base_url="http://localhost/", transport=httpx.MockTransport(handler)
    ) as client:
        result = await apply_approved(client, candidates, approvals, manifest["workspace_id"])
    assert result["approvals_sha256"] == original_hash


@pytest.mark.asyncio
async def test_result_write_error_does_not_claim_rollback(tmp_path: Path, monkeypatch: Any) -> None:
    candidates, approvals = _files(tmp_path)
    manifest, _ = validate_files(candidates, approvals)
    entry = _entries({"pages": manifest["pages"]})[0]
    _approve(tmp_path, [entry])
    original_open = Path.open

    def failing_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path.name == "apply-result.json":
            raise OSError("private-provider-detail")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)

    def handler(_: Any) -> httpx.Response:
        return httpx.Response(
            200, json={"requested": 1, "inserted": 0, "existing": 1, "inserted_pairs": []}
        )

    async with httpx.AsyncClient(
        base_url="http://localhost/", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(BackfillError, match="committed_but_result_write_failed") as exc:
            await apply_approved(client, candidates, approvals, manifest["workspace_id"])
    assert "private-provider-detail" not in str(exc.value)


async def _psql(sql: str) -> str:
    process = await asyncio.create_subprocess_exec(
        "docker",
        "exec",
        "-i",
        "supabase_db_NexusWiki",
        "psql",
        "-U",
        "postgres",
        "-d",
        "postgres",
        "-At",
        "-v",
        "ON_ERROR_STOP=1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, error = await process.communicate(sql.encode("utf-8"))
    assert process.returncode == 0, error.decode("utf-8", errors="replace")
    return out.decode("utf-8")


@pytest.mark.parametrize("target", ["page", "chunk", "source_delete"])
@pytest.mark.asyncio
async def test_concurrent_writer_makes_review_stale_without_partial_insert(
    local_stack: httpx.Client,
    two_workspaces_two_users: Any,
    target: str,
) -> None:
    owner, _ = two_workspaces_two_users
    wiki, source, chunks = _seed(local_stack, owner)
    entries = _entries(_candidates(local_stack, owner.workspace_id))
    tag = f"backfill-test-{uuid4().hex}"
    statement = {
        "page": f"update public.wiki_pages set content='변경' where id='{wiki}';",  # noqa: S608 — 모든 보간값은 서버가 발급한 UUID 또는 uuid4다.
        "chunk": f"update public.source_chunks set content='변경' where id='{chunks[0]['id']}';",  # noqa: S608 — 모든 보간값은 서버가 발급한 UUID 또는 uuid4다.
        "source_delete": f"delete from public.raw_sources where id='{source}';",  # noqa: S608 — 모든 보간값은 서버가 발급한 UUID 또는 uuid4다.
    }[target]
    writer = asyncio.create_task(
        _psql(f"set application_name='{tag}'; begin; {statement} select pg_sleep(2); commit;")
    )
    try:
        for _ in range(40):
            active = await _psql(
                "select count(*) from pg_stat_activity "  # noqa: S608 — 모든 보간값은 uuid4다.
                f"where application_name='{tag}' and wait_event='PgSleep';"
            )
            if active.strip() == "1":
                break
            await asyncio.sleep(0.025)
        else:
            pytest.fail("동시 writer의 잠금 획득을 확인하지 못했다")
        async with httpx.AsyncClient(
            base_url=f"{LOCAL_STACK['url']}/rest/v1/", headers=_headers()
        ) as client:
            response = await client.post(
                "rpc/apply_wiki_evidence_backfill",
                json={"p_workspace_id": owner.workspace_id, "p_entries": entries},
            )
        assert response.status_code == 400, response.text
        assert _rows(local_stack, "wiki_page_evidence", owner.workspace_id) == []
    finally:
        await asyncio.wait_for(writer, timeout=15)


def test_cli_end_to_end_partial_approval_coordinates_and_re_review(
    local_stack: httpx.Client,
    two_workspaces_two_users: Any,
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    owner, other = two_workspaces_two_users
    wiki_approved, source_id, chunks = _seed(local_stack, owner)
    _seed(local_stack, other)
    _insert(
        local_stack,
        "raw_sources",
        {
            "workspace_id": owner.workspace_id,
            "title": "미연결 원문",
            "source_type": "text",
            "content": "페이지 출처 밖 본문",
            "content_hash": uuid4().hex,
        },
    )
    bad_chunk = _insert(
        local_stack,
        "source_chunks",
        {
            "workspace_id": owner.workspace_id,
            "raw_source_id": source_id,
            "chunk_index": 2,
            "content": "좌표가 어긋난 본문",
            "char_start": 0,
            "char_end": 3,
        },
    )[0]
    wiki_unresolved = _insert(
        local_stack,
        "wiki_pages",
        {
            "workspace_id": owner.workspace_id,
            "slug": f"unresolved-{uuid4().hex}",
            "title": "근거 미확정 페이지",
            "category": "concepts",
            "content": "비교했지만 확신할 수 없는 페이지 본문",
            "sources": [source_id],
            "verification_status": "verified",
            "explored": True,
        },
    )[0]["id"]
    _insert(
        local_stack,
        "wiki_pages",
        {
            "workspace_id": owner.workspace_id,
            "slug": f"no-cand-{uuid4().hex}",
            "title": "후보 없는 페이지",
            "category": "concepts",
            "content": "출처 없는 본문",
            "sources": [],
            "verification_status": "verified",
            "explored": True,
        },
    )
    derived = local_stack.patch(
        "/rest/v1/source_chunks",
        headers=_headers(),
        params={"id": f"eq.{chunks[0]['id']}"},
        json={"tsv_tokenizer_version": 2},
    )
    assert derived.status_code < 400, derived.text

    monkeypatch.setenv("SUPABASE_URL", LOCAL_STACK["url"])
    monkeypatch.setenv("SUPABASE_SECRET_KEY", LOCAL_STACK["admin_key"])
    run1 = tmp_path / "run-1"
    assert main(["export", "--workspace-id", owner.workspace_id, "--output-dir", str(run1)]) == 0
    report = (run1 / "review.html").read_text(encoding="utf-8")
    assert "좌표 불일치 · 승인 불가" in report
    assert "후보 없음 · 미확정" in report

    manifest = json.loads((run1 / "candidates.json").read_bytes())
    for item in manifest["pages"]:
        for candidate in item["chunks"]:
            assert candidate["workspace_id"] == owner.workspace_id
            assert candidate["raw_source_id"] == source_id

    bad_approval = json.loads((run1 / "approvals.json").read_bytes())
    bad_approval["approved"] = [
        {"wiki_id": wiki_approved, "raw_source_id": source_id, "chunk_id": bad_chunk["id"]}
    ]
    (run1 / "approvals.json").write_bytes(_bytes(bad_approval))
    with pytest.raises(BackfillError, match="selection_not_available:row_1"):
        validate_files(run1 / "candidates.json", run1 / "approvals.json")

    valid_approval = json.loads((run1 / "approvals.json").read_bytes())
    valid_approval["approved"] = [
        {"wiki_id": wiki_approved, "raw_source_id": source_id, "chunk_id": chunks[0]["id"]}
    ]
    (run1 / "approvals.json").write_bytes(_bytes(valid_approval))
    assert (
        main(
            [
                "validate",
                "--candidates",
                str(run1 / "candidates.json"),
                "--approvals",
                str(run1 / "approvals.json"),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "apply",
                "--candidates",
                str(run1 / "candidates.json"),
                "--approvals",
                str(run1 / "approvals.json"),
                "--confirm-workspace-id",
                owner.workspace_id,
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "apply",
                "--candidates",
                str(run1 / "candidates.json"),
                "--approvals",
                str(run1 / "approvals.json"),
                "--confirm-workspace-id",
                owner.workspace_id,
            ]
        )
        == 0
    )
    evidence_rows = _rows(local_stack, "wiki_page_evidence", owner.workspace_id)
    assert len(evidence_rows) == 1
    assert evidence_rows[0]["wiki_id"] == wiki_approved
    assert all(row["wiki_id"] != wiki_unresolved for row in evidence_rows)

    quality = _rpc(
        local_stack,
        "control_quality_snapshot",
        {"p_workspace_id": owner.workspace_id, "p_since": "2026-01-01T00:00:00Z"},
        {"apikey": LOCAL_STACK["publishable_key"], "Authorization": f"Bearer {owner.access_token}"},
    ).json()[0]
    assert quality["wiki_pages_total"] == 3
    assert quality["wiki_pages_with_evidence"] == 1

    patched = local_stack.patch(
        "/rest/v1/wiki_pages",
        headers=_headers(),
        params={"id": f"eq.{wiki_unresolved}"},
        json={"content": "검증된 근거 문장😀 재작성"},
    )
    assert patched.status_code < 400, patched.text
    stale_approval = json.loads((run1 / "approvals.json").read_bytes())
    stale_approval["approved"] = [
        {"wiki_id": wiki_unresolved, "raw_source_id": source_id, "chunk_id": chunks[0]["id"]}
    ]
    (run1 / "approvals.json").write_bytes(_bytes(stale_approval))
    assert (
        main(
            [
                "apply",
                "--candidates",
                str(run1 / "candidates.json"),
                "--approvals",
                str(run1 / "approvals.json"),
                "--confirm-workspace-id",
                owner.workspace_id,
            ]
        )
        == 1
    )

    run2 = tmp_path / "run-2"
    assert main(["export", "--workspace-id", owner.workspace_id, "--output-dir", str(run2)]) == 0
    re_approval = json.loads((run2 / "approvals.json").read_bytes())
    re_approval["approved"] = [
        {"wiki_id": wiki_unresolved, "raw_source_id": source_id, "chunk_id": chunks[0]["id"]}
    ]
    (run2 / "approvals.json").write_bytes(_bytes(re_approval))
    assert (
        main(
            [
                "apply",
                "--candidates",
                str(run2 / "candidates.json"),
                "--approvals",
                str(run2 / "approvals.json"),
                "--confirm-workspace-id",
                owner.workspace_id,
            ]
        )
        == 0
    )
    stdout = capsys.readouterr().out
    assert "근거 문장😀" not in stdout
    assert LOCAL_STACK["admin_key"] not in stdout
    assert len(_rows(local_stack, "wiki_page_evidence", owner.workspace_id)) == 2
