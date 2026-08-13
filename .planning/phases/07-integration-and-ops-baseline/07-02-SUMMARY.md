---
phase: 07-integration-and-ops-baseline
plan: 02
status: complete
completed: 2026-08-13
requirements: [OPS-04]
commits: [d38f440, 0b030e2]
---

# Phase 7 Plan 02 Summary

Delivered the local-Supabase full-path tenant-isolation gate.

## Completed

- Added function-scoped A owner/editor/viewer, B owner, and authenticated
  non-member principals; all identities are fresh and cleanup-backed.
- Added the nine-table requester-JWT read matrix for workspaces,
  workspace_members, raw_sources, wiki_pages, source_chunks, wiki_embeddings,
  wiki_links, prompt_templates, and jobs.
- Reused the Phase 7 pipeline harness's API-created text/file/URL sources and
  real queue processing; service role is confined to the link setup row that
  has no requester-visible creation path.
- Added role/anonymous controls, an API 403 write control, a direct definer-RPC
  42501 assertion, and requester-JWT Storage access proof for the API-created
  file path.
- Confirmed the conventional module is collected by the existing CI
  `uv run pytest -rs` job; no cloud credentials or separate workflow were added.

## Verification

`UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -rs apps/api/tests/test_tenant_isolation_full_path.py`

Result: 13 passed against the local Supabase stack.

## Task Commits

1. `d38f440` — role-complete local isolation principals and freshness control.
2. `0b030e2` — nine-table, queue-RPC, and Storage isolation evidence.
3. No code change: existing CI already collects this standard pytest module with `-rs`.

## Deviations

- Rule 2: the derived `wiki_links` setup row uses service role because the
  product intentionally has no requester-visible link creation path. Every
  authorization assertion remains requester-JWT or anonymous.
