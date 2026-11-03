"""본문을 보존하는 관리용 근거 백필 CLI (#210).

계약: openspec/changes/backfill-wiki-evidence/design.md.
export는 DB 읽기만 수행한다. 운영 마이그레이션과 apply는 운영자가 직접 실행한다.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx

from nexuswiki_core.tokenizer import bigram, normalize

SCHEMA = "wiki-evidence-backfill-v1"
MAX_PAIRS = 500
MAX_FILE_BYTES = 64 * 1024 * 1024
_TOKEN = re.compile(r"[0-9a-f]{64}")


class BackfillError(Exception):
    """본문·자격증명을 포함하지 않는 고정 오류 코드."""


def _uuid(value: Any) -> str:
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError
    except (ValueError, TypeError, AttributeError) as exc:
        raise BackfillError("invalid_identifier") from exc
    return value


def _token(value: Any) -> str:
    if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
        raise BackfillError("invalid_token")
    return value


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BackfillError("duplicate_json_key")
        result[key] = value
    return result


def _read(path: Path) -> tuple[bytes, dict[str, Any]]:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            raise BackfillError("file_too_large")
        raw = path.read_bytes()
        if len(raw) > MAX_FILE_BYTES:
            raise BackfillError("file_too_large")
        value = json.loads(raw, object_pairs_hook=_object)
    except (OSError, ValueError, UnicodeError) as exc:
        raise BackfillError("invalid_file") from exc
    if not isinstance(value, dict):
        raise BackfillError("invalid_document")
    return raw, value


def _bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _score(page: str, chunk: str) -> float:
    left = set(bigram(normalize(page)).split())
    right = set(bigram(normalize(chunk)).split())
    return round(len(left & right) / len(left | right), 6) if left | right else 0.0


def _safe_directory(path: Path) -> Path:
    resolved = path.resolve()
    # 설치 위치뿐 아니라 현재 checkout에서도 저장소 경계를 찾는다.
    for start in (Path.cwd().resolve(), Path(__file__).resolve().parent):
        for root in (start, *start.parents):
            if (root / ".git").exists() and resolved.is_relative_to(root):
                if not resolved.is_relative_to((root / ".local/evidence-backfill").resolve()):
                    raise BackfillError("repository_output_not_ignored")
                break
    return resolved


def _report(manifest: dict[str, Any]) -> str:
    escape = lambda text: html.escape(str(text), quote=True)  # noqa: E731
    parts = [
        '<!doctype html><html lang="ko"><meta charset="utf-8">',
        '<meta http-equiv="Content-Security-Policy" '
        'content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;">',
        "<title>청크 근거 검토</title><style>body{max-width:1100px;margin:32px auto;"
        "font:16px system-ui;padding:0 16px}pre{white-space:pre-wrap;overflow-wrap:anywhere}"
        "article{border-top:1px solid #ccc;padding:24px 0}section{background:#f5f6f7;"
        "padding:16px;margin:12px 0}code{overflow-wrap:anywhere}</style><body>",
        "<h1>청크 근거 검토</h1><p>로컬 민감 자료. 점수는 정렬용이며 근거 확정이나 "
        "문장별 완전성 검증이 아닙니다. 근거를 확정할 수 없으면 승인하지 마세요.</p>",
    ]
    for item in manifest["pages"]:
        page = item["page"]
        link_state = (
            "기존 연결 있음"
            if any(chunk.get("already_linked") for chunk in item["chunks"])
            else "기존 연결 없음"
        )
        parts.append(
            f"<article><h2>{escape(page['title'])}</h2><code>{escape(page['id'])}</code>"
            f"<p>검증: {escape(page['verification_status'])} · {link_state} · 새 승인 없음</p>"
            f"<pre>{escape(page['content'])}</pre>"
        )
        if not item["chunks"]:
            parts.append("<p>후보 없음 · 미확정</p>")
        for chunk in item["chunks"]:
            state = "기존 연결" if chunk["already_linked"] else "미승인"
            if not chunk["valid_coordinates"]:
                state = "좌표 불일치 · 승인 불가"
            parts.append(
                f"<section><p>{state} · 점수 {chunk['score']}</p>"
                f"<p>원문 <code>{escape(chunk['raw_source_id'])}</code> / "
                f"청크 <code>{escape(chunk['id'])}</code> / "
                f"순번 {escape(chunk['chunk_index'])} / "
                f"좌표 {escape(chunk['char_start'])}–{escape(chunk['char_end'])}</p>"
                f"<pre>{escape(chunk['content'])}</pre></section>"
            )
        parts.append("</article>")
    if not manifest["pages"]:
        parts.append("<p>페이지 0개 · 후보 0개</p>")
    return "".join([*parts, "</body></html>"])


async def _rpc(client: httpx.AsyncClient, name: str, body: dict[str, Any]) -> Any:
    try:
        response = await client.post(f"rpc/{name}", json=body)
    except httpx.HTTPError as exc:
        code = "apply_outcome_unknown" if name.startswith("apply_") else "read_failed"
        raise BackfillError(code) from exc
    if response.is_error:
        # 오류 본문에 SQL이나 원문이 있을 수 있어 고정된 코드만 보고한다.
        code = "read_rejected"
        if name.startswith("apply_"):
            code = "apply_outcome_unknown" if response.status_code >= 500 else "apply_rejected"
        raise BackfillError(code)
    try:
        return response.json()
    except ValueError as exc:
        raise BackfillError("invalid_server_response") from exc


async def export_candidates(
    client: httpx.AsyncClient, workspace_id: str, output_dir: Path
) -> dict[str, int]:
    workspace_id = _uuid(workspace_id)
    directory = _safe_directory(output_dir)
    names = ("candidates.json", "review.html", "approvals.json")
    if any((directory / name).exists() for name in names):
        raise BackfillError("output_exists")
    pages: list[dict[str, Any]] = []
    cursor: str | None = None
    seen: set[str] = set()
    while True:
        batch = await _rpc(
            client,
            "wiki_evidence_backfill_candidates",
            {"p_workspace_id": workspace_id, "p_after_wiki_id": cursor, "p_limit": 50},
        )
        if not isinstance(batch, dict) or not isinstance(batch.get("pages"), list):
            raise BackfillError("invalid_server_response")
        items = batch["pages"]
        for item in items:
            page = item["page"]
            page_id = _uuid(page["id"])
            if page_id in seen or page["workspace_id"] != workspace_id:
                raise BackfillError("invalid_page_scope")
            if cursor is not None and page_id <= cursor:
                raise BackfillError("invalid_cursor")
            seen.add(page_id)
            for chunk in item["chunks"]:
                chunk["score"] = _score(page["content"], chunk["content"])
            item["chunks"].sort(key=lambda row: (-row["score"], row["raw_source_id"], row["id"]))
            pages.append(item)
        if batch.get("has_more") is False:
            break
        next_cursor = batch.get("next_cursor")
        if batch.get("has_more") is not True or not items or next_cursor != items[-1]["page"]["id"]:
            raise BackfillError("invalid_cursor")
        if cursor is not None and next_cursor <= cursor:
            raise BackfillError("invalid_cursor")
        cursor = _uuid(next_cursor)
    manifest = {
        "schema": SCHEMA,
        "workspace_id": workspace_id,
        "created_at": datetime.now(UTC).isoformat(),
        "tool_version": 1,
        "pages": pages,
    }
    raw = _bytes(manifest)
    approval = {
        "schema": SCHEMA,
        "workspace_id": workspace_id,
        "candidates_sha256": hashlib.sha256(raw).hexdigest(),
        "approved": [],
    }
    directory.mkdir(parents=True, exist_ok=True)
    try:
        for name, data in zip(
            names, (raw, _report(manifest).encode("utf-8"), _bytes(approval)), strict=True
        ):
            with (directory / name).open("xb") as handle:
                handle.write(data)
    except OSError as exc:
        raise BackfillError("export_file_write_failed") from exc
    return {
        "pages": len(pages),
        "candidate_pairs": sum(len(row["chunks"]) for row in pages),
        "pages_without_candidates": sum(not row["chunks"] for row in pages),
    }


def validate_files(
    candidates: Path, approvals: Path
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    raw, manifest = _read(candidates)
    approval_raw, approval = _read(approvals)
    workspace_id = _uuid(manifest.get("workspace_id"))
    if manifest.get("schema") != SCHEMA or approval.get("schema") != SCHEMA:
        raise BackfillError("invalid_schema")
    if approval.get("workspace_id") != workspace_id:
        raise BackfillError("workspace_mismatch")
    if approval.get("candidates_sha256") != hashlib.sha256(raw).hexdigest():
        raise BackfillError("candidates_hash_mismatch")
    if set(approval) != {"schema", "workspace_id", "candidates_sha256", "approved"}:
        raise BackfillError("invalid_approval_fields")
    selected = approval.get("approved")
    if not isinstance(selected, list) or len(selected) > MAX_PAIRS:
        raise BackfillError("invalid_batch_size")
    if not isinstance(manifest.get("pages"), list):
        raise BackfillError("invalid_document")
    available: dict[tuple[str, str, str], dict[str, str]] = {}
    for item in manifest["pages"]:
        try:
            page = item["page"]
            wiki_id = _uuid(page["id"])
            if page["workspace_id"] != workspace_id or not isinstance(page["sources"], list):
                raise BackfillError("invalid_page_scope")
            page_token = _token(item["page_token"])
            for chunk in item["chunks"]:
                chunk_id, source_id = _uuid(chunk["id"]), _uuid(chunk["raw_source_id"])
                if chunk["workspace_id"] != workspace_id or source_id not in page["sources"]:
                    raise BackfillError("invalid_chunk_scope")
                if chunk.get("valid_coordinates") is not True:
                    continue
                key = (wiki_id, source_id, chunk_id)
                if key in available:
                    raise BackfillError("duplicate_candidate")
                available[key] = {
                    "wiki_id": wiki_id,
                    "raw_source_id": source_id,
                    "chunk_id": chunk_id,
                    "page_token": page_token,
                    "source_token": _token(chunk["source_token"]),
                    "chunk_token": _token(chunk["chunk_token"]),
                }
        except (KeyError, TypeError) as exc:
            raise BackfillError("invalid_document") from exc
    entries: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, row in enumerate(selected, start=1):
        if not isinstance(row, dict) or set(row) != {"wiki_id", "raw_source_id", "chunk_id"}:
            raise BackfillError(f"invalid_selection:row_{index}")
        try:
            key = (_uuid(row["wiki_id"]), _uuid(row["raw_source_id"]), _uuid(row["chunk_id"]))
        except BackfillError as exc:
            raise BackfillError(f"{exc}:row_{index}") from exc
        if key in seen:
            raise BackfillError(f"duplicate_selection:row_{index}")
        if key not in available:
            raise BackfillError(f"selection_not_available:row_{index}")
        seen.add(key)
        entries.append(available[key])
    manifest = {
        **manifest,
        "validated_hashes": {
            "candidates": hashlib.sha256(raw).hexdigest(),
            "approvals": hashlib.sha256(approval_raw).hexdigest(),
        },
    }
    return manifest, entries


async def apply_approved(
    client: httpx.AsyncClient,
    candidates: Path,
    approvals: Path,
    confirm_workspace_id: str,
    *,
    validated: tuple[dict[str, Any], list[dict[str, str]]] | None = None,
) -> dict[str, Any]:
    manifest, entries = (
        validated if validated is not None else validate_files(candidates, approvals)
    )
    if _uuid(confirm_workspace_id) != manifest["workspace_id"]:
        raise BackfillError("confirmation_mismatch")
    if not entries:
        return {"requested": 0, "inserted": 0, "existing": 0, "inserted_pairs": []}
    result_path = _safe_directory(approvals.parent) / "apply-result.json"
    if result_path.exists():
        result_path = result_path.with_name(f"apply-result-{uuid4().hex}.json")
    result = await _rpc(
        client,
        "apply_wiki_evidence_backfill",
        {"p_workspace_id": manifest["workspace_id"], "p_entries": entries},
    )
    if (
        not isinstance(result, dict)
        or set(result) != {"requested", "inserted", "existing", "inserted_pairs"}
        or any(type(result.get(key)) is not int for key in ("requested", "inserted", "existing"))
        or result["requested"] != len(entries)
        or result["inserted"] < 0
        or result["existing"] < 0
        or result["inserted"] + result["existing"] != len(entries)
        or not isinstance(result["inserted_pairs"], list)
        or len(result["inserted_pairs"]) != result["inserted"]
    ):
        raise BackfillError("apply_result_unknown")
    expected = {(row["wiki_id"], row["raw_source_id"], row["chunk_id"]) for row in entries}
    inserted = set()
    for row in result["inserted_pairs"]:
        if not isinstance(row, dict) or set(row) != {"wiki_id", "raw_source_id", "chunk_id"}:
            raise BackfillError("apply_result_unknown")
        pair = (row["wiki_id"], row["raw_source_id"], row["chunk_id"])
        if (
            any(not isinstance(item, str) for item in pair)
            or pair not in expected
            or pair in inserted
        ):
            raise BackfillError("apply_result_unknown")
        inserted.add(pair)
    result["workspace_id"] = manifest["workspace_id"]
    result["candidates_sha256"] = manifest["validated_hashes"]["candidates"]
    result["approvals_sha256"] = manifest["validated_hashes"]["approvals"]
    try:
        with result_path.open("xb") as handle:
            handle.write(_bytes(result))
    except OSError as exc:
        raise BackfillError("committed_but_result_write_failed") from exc
    return result


def _connection() -> tuple[str, str]:
    url, key = os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_SECRET_KEY", "")
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
    except ValueError as exc:
        raise BackfillError("explicit_connection_required") from exc
    if (
        not key
        or not hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
        or (
            parsed.scheme != "https"
            and not (parsed.scheme == "http" and hostname in {"127.0.0.1", "localhost", "::1"})
        )
    ):
        raise BackfillError("explicit_connection_required")
    return url.rstrip("/"), key


async def _run(args: argparse.Namespace) -> None:
    if args.command == "validate":
        manifest, entries = validate_files(args.candidates, args.approvals)
        print(json.dumps({"workspace_id": manifest["workspace_id"], "approved": len(entries)}))
        return
    url, key = _connection()
    reviewed = None
    if args.command == "apply":
        reviewed = validate_files(args.candidates, args.approvals)
        if _uuid(args.confirm_workspace_id) != reviewed[0]["workspace_id"]:
            raise BackfillError("confirmation_mismatch")
        print(
            json.dumps(
                {
                    "approved": len(reviewed[1]),
                    "candidates_sha256": reviewed[0]["validated_hashes"]["candidates"],
                }
            )
        )
    print(
        json.dumps(
            {
                "target": url,
                "workspace_id": args.workspace_id
                if args.command == "export"
                else args.confirm_workspace_id,
            }
        )
    )
    async with httpx.AsyncClient(
        base_url=f"{url}/rest/v1/",
        timeout=60,
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    ) as client:
        if args.command == "export":
            result = await export_candidates(client, args.workspace_id, args.output_dir)
        else:
            result = await apply_approved(
                client,
                args.candidates,
                args.approvals,
                args.confirm_workspace_id,
                validated=reviewed,
            )
    print(json.dumps(result, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="본문을 보존하는 근거 백필 관리 도구")
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", help="읽기 전용 후보 보고서")
    export.add_argument("--workspace-id", required=True)
    export.add_argument("--output-dir", type=Path, required=True)
    for command in ("validate", "apply"):
        sub = commands.add_parser(command)
        sub.add_argument("--candidates", type=Path, required=True)
        sub.add_argument("--approvals", type=Path, required=True)
        if command == "apply":
            sub.add_argument("--confirm-workspace-id", required=True)
    args = parser.parse_args(argv)
    try:
        asyncio.run(_run(args))
    except (BackfillError, OSError) as exc:
        print(
            f"backfill_error:{exc}" if isinstance(exc, BackfillError) else "backfill_error:file_io"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
