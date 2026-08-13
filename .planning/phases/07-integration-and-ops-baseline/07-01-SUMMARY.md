---
phase: 07-integration-and-ops-baseline
plan: 01
status: complete
completed: 2026-08-13
requirements: [OPS-02, OPS-03]
commits: [0caf9c7, 6525e7a, d82548e, 40f5e99]
---

# Phase 7 Plan 01 Summary

Implemented a real local-Supabase pipeline tracer and re-ingestion regression suite.

## Completed

- API creation of one text, file, and URL source, including workspace-prefixed Storage evidence.
- Queue-RPC-driven parse → compile → link-sync → embed chain with real Postgres, RLS, Storage, and retrieval; URL/LLM/embedding are deterministic transports only.
- Duplicate normalized text has no scoped row-count growth.
- A multi-chunk source reprocessed to a shorter body deletes stale chunks and embeds, retaining contiguous indexes.
- Added `run_embed()` injection seam so the real embed persistence path can run under deterministic provider transport.

## Verification

`UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -rs apps/api/tests/test_pipeline_e2e.py apps/api/tests/test_reingestion_idempotency.py`

Result: 3 passed. Existing CI's normal pytest job invokes `uv run pytest -rs`, so local-stack skips remain visible.

## Task Commits

1. `0caf9c7` / `6525e7a` — RED then GREEN OPS-02 tracer.
2. `d82548e` / `40f5e99` — RED then GREEN OPS-03 regression coverage.
3. No code change required: confirmed existing pytest PR gate collects conventionally named modules with `-rs`.

## Deviations

- Rule 2: exposed `run_embed()` from the existing handler. The plan requires established injectable worker run seams; embed was the only stage without one. The wrapper preserves production behavior and makes the real persistence path testable without provider traffic.

## Self-check

- No cloud URL, OpenRouter client, direct jobs-table mutation, or mocked persistence is used by the tests.
- Local integration tests completed successfully against loopback Supabase in this run.
