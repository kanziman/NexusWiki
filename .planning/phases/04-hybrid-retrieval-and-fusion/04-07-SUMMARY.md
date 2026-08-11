---
phase: 04-hybrid-retrieval-and-fusion
plan: 07
subsystem: retrieval
tags: [hnsw, pgvector, benchmark, retrieval-policy]
requires:
  - phase: 04-06
    provides: named-index retrieval plan contract
provides:
  - deterministic large-corpus HNSW benchmark harness and immutable paired records
  - approved quality-first strict-order and graph-off decision record
affects: [retrieval, migrations, operations]
tech-stack:
  added: []
  patterns: [append-only benchmark records, canonical policy-content hash]
key-files:
  created: [scripts/generate_retrieval_benchmark_corpus.py, docs/ops/benchmark-records/phase-04-strict-order.json, docs/ops/benchmark-records/phase-04-relaxed-order.json, docs/ops/benchmark-records/phase-04-graph-off.json, docs/ops/benchmark-records/phase-04-graph-on.json]
  modified: [scripts/benchmark_retrieval.py, docs/ops/hnsw-order-benchmark.md, docs/ops/retrieval-policy-change-log.md]
key-decisions:
  - "Approved strict_order and graph off: quality and underfill were tied; strict has the safer deployed contract and lower p50."
  - "No 0012 migration: relaxed evidence is controlled direct-query evidence, not a deployed RPC change."
requirements-completed: [RTV-04, RTV-07]
coverage:
  - id: D1
    description: Deterministic paired HNSW benchmark records with named-index preflight pins.
    requirement: RTV-04
    verification:
      - kind: unit
        ref: packages/core/tests/test_retrieval_golden.py
        status: pass
      - kind: integration
        ref: benchmark_record_comparison
        status: pass
    human_judgment: false
  - id: D2
    description: Approved strict-order and graph-off default decision record.
    requirement: RTV-07
    verification:
      - kind: other
        ref: docs/ops/hnsw-order-benchmark.md
        status: pass
    human_judgment: false
duration: 3h
completed: 2026-08-11
status: complete
---

# Phase 04 Plan 07: HNSW paired evidence and default decision Summary

**Deterministic 100,000-vector paired HNSW records retained with strict-order and graph-off approved as unchanged defaults.**

## Accomplishments

- Added a deterministic SHA-256 counter-stream corpus loader, canonical policy-content hashing, immutable operational record handling, and focused fixture contracts.
- Captured and pin-validated strict/relaxed and graph off/on records with named-index preflight evidence.
- Recorded the approved quality-first outcome: keep 0011 `strict_order`, retain `graph_enabled = False`, and create no 0012 migration.

## Task Commits

1. Task 1 — `b97f99b`, `9f9b878`
2. Task 2 — `e92d599`
3. Task 4 — documented in this metadata commit.

## Verification

- `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -q packages/core/tests/test_retrieval_golden.py` — 6 passed
- `bash scripts/ci_check_retrieval_contract.sh` — passed
- Record-pin comparison — passed

## Decisions Made

Strict/relaxed quality and underfill were tied; strict had lower p50 and preserves the current deployed RPC contract. Graph returned no contribution or quality gain, so its default remains off.

## Deviations from Plan

**[Rule 3 - Blocking environment]** Repeated scoped benchmark cleanup caused a later named-index preflight to prefer the workspace index. A controlled `supabase db reset` was required before each graph arm; no incomplete record was retained.

**Total deviations:** 1 auto-fixed. **Impact:** local benchmark execution only; production state unchanged.

## Issues Encountered

None remaining.

## Next Phase Readiness

Phase 04 has retained benchmark evidence and an approved unchanged-default decision. Any future relaxed adoption requires a successor migration and fresh evidence.
