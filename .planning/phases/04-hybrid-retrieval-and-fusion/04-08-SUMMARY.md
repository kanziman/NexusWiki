---
phase: 04-hybrid-retrieval-and-fusion
plan: 08
subsystem: retrieval
tags: [retrieval, hnsw, rrf, graph, benchmark, evidence]
requires:
  - phase: 04-07
    provides: immutable HNSW benchmark records and the initial default-decision documentation
provides:
  - full-path golden-query retrieval evidence with canonical paired-record validation
  - measured bounded graph second-wave evidence and corrected decision documentation
affects: [retrieval, operations, policy-governance]
actuals:
  tasks: 3
  commits: 10
tech-stack:
  added: []
  patterns:
    - "Operational benchmark rankings are serialized only from RetrievalService channel envelopes, then evaluated against logical labels."
    - "Paired records retain complete canonical policy content; comparators fail closed on pin or policy mismatch."
key-files:
  created:
    - docs/ops/benchmark-records/phase-04-rerun-v4-strict-order.json
    - docs/ops/benchmark-records/phase-04-rerun-v4-relaxed-order.json
    - docs/ops/benchmark-records/phase-04-rerun-v4-graph-off.json
    - docs/ops/benchmark-records/phase-04-rerun-v4-graph-on.json
  modified:
    - scripts/generate_retrieval_benchmark_corpus.py
    - scripts/benchmark_retrieval.py
    - packages/core/tests/test_retrieval_golden.py
    - apps/api/tests/test_retrieval_service.py
    - docs/ops/hnsw-order-benchmark.md
    - docs/ops/retrieval-policy-change-log.md
key-decisions:
  - "Plan-07 v2 records remain byte-for-byte preserved but are superseded invalid historical evidence, not full-path retrieval measurements."
  - "Strict order and graph off remain current safe defaults; v4 measurement alone did not authorize a policy or migration change."
requirements-completed: [RTV-04, RTV-07]
coverage:
  - id: D1
    description: Strict/relaxed v4 records execute 36 golden query texts through the real four first-wave RetrievalService channels and Python RRF.
    requirement: RTV-04
    verification:
      - kind: unit
        ref: "UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -q packages/core/tests/test_retrieval_golden.py apps/api/tests/test_retrieval_service.py"
        status: pass
      - kind: integration
        ref: "compare-order-records v4 strict/relaxed"
        status: pass
    human_judgment: false
  - id: D2
    description: Graph-on v4 record executes bounded expand_wiki_graph second waves and re-fuses their observed results.
    requirement: RTV-07
    verification:
      - kind: integration
        ref: "compare-graph-records v4 graph-off/graph-on"
        status: pass
      - kind: integration
        ref: scripts/verify_retrieval_contract.sh
        status: pass
    human_judgment: false
duration: unknown
completed: 2026-08-11
status: complete
---

# Phase 04 Plan 08: Full-Path Retrieval Evidence Summary

**RTV-04 and RTV-07 now have append-only, full-path measurements: real golden-query
retrieval/RRF for strict versus relaxed and real bounded graph second waves for graph off
versus on.**

## Accomplishments

- Made the controlled corpus executable for actual lexical, vector, RRF, and bounded
  graph retrieval, with deterministic UUID/logical-ID mapping and scoped cleanup.
- Replaced synthetic operational ranking construction with `RetrievalService.retrieve()`
  observations, full five-channel envelopes, canonical policy content, and fail-closed
  pair comparators.
- Retained four v4 immutable records. The order comparator reports quality delta
  `-0.027777777777777776` (relaxed minus strict); the graph comparator reports quality
  `+0.02777777777777779`, contribution `+366`, underfill `0`, and p50 latency
  `+49.169500000000085 ms` (on minus off).
- Confirmed the graph-on record contains 36 successful real graph RPC envelopes and
  contribution 366; scoped cleanup leaves zero rows for the fixed benchmark workspace.
- Corrected the operations decision documents: Plan-07 records are preserved as invalid
  historical evidence, and v4 measurements do not by themselves approve a default change.

## Task Commits

1. **Task 1: executable deterministic corpus** — `af7a7f1`, `c08c764`, `a912e01`, `4662056`
2. **Task 2: full-path runner and record validation** — `e876cd0`, `990d94e`, `361049f`, `6adb045`
3. **Task 3: append-only evidence and decision documents** — `3616312`, `c41f197`

## Verification

- `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -q packages/core/tests/test_retrieval_golden.py apps/api/tests/test_retrieval_service.py` — **19 passed**
- `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run python scripts/benchmark_retrieval.py --verify` — passed (fixture-only record)
- `scripts/verify_retrieval_contract.sh` — passed; named HNSW fixture/preflight completed and rolled back
- `compare-order-records` on v4 strict/relaxed — `status: ok`, quality delta `-0.027777777777777776`
- `compare-graph-records` on v4 graph off/on — `status: ok`, quality `+0.02777777777777779`, contribution `+366`, underfill `0`, p50 `+49.169500000000085 ms`
- `git diff --check` — passed

## Deviations from Plan

None. A duplicate local retrieval-contract invocation was terminated before it completed
because it conflicted with the sequential verification run; the subsequent single run
passed. It did not alter repository or production data.

## Decisions Made

- The observed relaxed quality delta is not a deployed-RPC change claim: relaxed remains
  a controlled caller-session direct-vector measurement.
- The positive graph measurement is evidence for the existing review gate, not approval to
  enable graph. `strict_order` and `graph_enabled = False` remain unchanged safe defaults.

## Self-Check: PASSED

- The four v4 records have complete canonical policy objects whose stored SHA values
  recompute correctly; strict/relaxed policies are identical and graph records differ only
  in `graph_enabled`.
- Original Plan-07 records are unchanged and documented as superseded invalid evidence.
- Only the documentation files and this summary were added during closeout; unrelated
  dirty and untracked workspace paths were not staged or modified.

---
*Phase: 04-hybrid-retrieval-and-fusion*
*Completed: 2026-08-11*
