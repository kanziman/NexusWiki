---
phase: 07-integration-and-ops-baseline
plan: 03
status: complete
completed: 2026-08-13
requirements: [OPS-05]
commits: [49ece13, 135a0f1, 06bb515]
---

# Phase 7 Plan 03 Summary

Established an append-only canonical 50k full-path retrieval baseline with scoped,
schema-validated EXPLAIN evidence and no retrieval-policy change.

## Completed

- Added `retrieval-hnsw-explain-v1` records for both vector channels, including raw
  scoped plans, channel/function/relation/query/order/graph pins, validated HNSW
  selection, and per-channel p50/p95 latency summaries.
- Added fail-closed tests for absent/malformed/scoping-mismatched EXPLAIN evidence and
  unsupported HNSW conclusions.
- Captured comparable strict and relaxed immutable arms from revision
  `135a0f16a548ca54ad2d4dad01c326b42d55235a`; the comparator returned `ok` with
  relaxed-minus-strict quality delta `-0.2222222222222222`.
- Both local raw plans selected `source_chunks_embedding_idx` and
  `wiki_embeddings_embedding_idx`; their truthful decision is
  `representative_hnsw_observed`, so no Railway escalation is needed.

## Verification

- `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -q packages/core/tests/test_retrieval_golden.py` — 18 passed.
- `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run python scripts/benchmark_retrieval.py compare-order-records ...` — `{"status": "ok"}`.
- JSON schema assertions passed for both Phase 7 records; scoped benchmark cleanup left
  the deterministic workspace with zero rows.

## Deviations

- The interactive command window cannot accommodate the load plus measured pass in one
  foreground process. Each arm still used fresh canonical load/ANALYZE and scoped cleanup;
  the runner’s internal reuse flag only resumed the already-loaded deterministic workspace
  for the measured pass, without changing corpus, policy, or pins.
