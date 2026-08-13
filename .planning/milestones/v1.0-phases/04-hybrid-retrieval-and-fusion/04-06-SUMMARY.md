---
phase: 04-hybrid-retrieval-and-fusion
plan: 06
subsystem: database-testing
tags: [postgres, pgvector, hnsw, explain-json, rls, regression-contract]
requires:
  - phase: 04-02
    provides: authenticated retrieval RPCs with named HNSW indexes
provides:
  - rollback-safe local JSON-plan proof for both deployed vector indexes
  - direct-query to RPC equivalence and exact-dataset HNSW preflight contract
affects: [retrieval, benchmarks, phase-04-plan-07]
actuals:
  tokens: 4800
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [security-equivalent direct EXPLAIN JSON probe, recursively checked named-index assertion, exact-dataset preflight]
key-files:
  created: []
  modified:
    - supabase/tests/0011_retrieval_contract.sql
    - scripts/ci_check_retrieval_contract.sh
    - docs/ops/migration-0011-record.md
key-decisions:
  - "Use direct authenticated/RLS queries plus explicit RPC body/GUC equivalence, never an outer RPC Function Scan, to prove HNSW planning."
  - "Keep the fixture transactional and permit Plan 07 to load only the reusable preflight mode for its own exact corpus."
requirements-completed: [RTV-08]
coverage:
  - id: D1
    description: Local transaction asserts the exact source and wiki HNSW index names from recursive EXPLAIN JSON plans under authenticated RLS context.
    requirement: RTV-08
    verification:
      - kind: integration
        ref: scripts/verify_retrieval_contract.sh
        status: pass
    human_judgment: false
  - id: D2
    description: CI source guard retains direct-query/RPC equivalence, reusable manifest/count preflight, named-index checks, and no unmatched planner forcing.
    requirement: RTV-08
    verification:
      - kind: other
        ref: bash scripts/ci_check_retrieval_contract.sh
        status: pass
    human_judgment: false
duration: 14 min
completed: 2026-08-11
status: complete
---

# Phase 04 Plan 06: HNSW Planner Regression Contract Summary

**A reset local Supabase stack now proves both vector retrieval shapes choose their exact deployed HNSW indexes through authenticated, security-equivalent direct JSON-plan queries.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-08-11T10:22:00Z
- **Completed:** 2026-08-11T10:36:16Z
- **Tasks:** 2/2
- **Files modified:** 3

## Accomplishments

- Added a rollback-only 100,000-vector fixture (50,000 rows per relation) with authenticated target and foreign decoy workspaces, valid deterministic 1024-dimensional vectors, and fresh statistics.
- Proved named HNSW scans recursively from `EXPLAIN (FORMAT JSON)` while matching deployed predicates, order, clamped limit, RLS/JWT context, and all three function HNSW GUCs.
- Added RPC catalog/body equivalence checks, an exact-manifest/count preflight for Plan 07, actionable expected-index failures, CI source guards, and operations documentation.

## Task Commits

1. **Task 1: build a rollback-safe, selective HNSW plan fixture** — `1f7335d` (feat)
2. **Task 2: recursively assert named HNSW index scans and make regression failures actionable** — `6d13be6` (test)

## Files Created/Modified

- `supabase/tests/0011_retrieval_contract.sql` — fixture, direct JSON-plan assertions, RPC equivalence checks, and reusable preflight mode.
- `scripts/ci_check_retrieval_contract.sh` — source-level guard for named-index, equivalence, preflight, and planner-forcing contracts.
- `docs/ops/migration-0011-record.md` — local corpus, command, design, and preflight operating record.

## Decisions Made

- An `EXPLAIN` of a public RPC may stop at Function Scan, so it is not accepted as evidence of an internal HNSW scan.
- Preflight mode validates an already-loaded manifest workspace without inserting or rolling back benchmark data.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] JSON plan root is an array, not a plan node.**
- **Found during:** Task 2
- **Issue:** The first recursive walker inspected the top-level JSON array and falsely reported a missing source index even though the observed plan contained `source_chunks_embedding_idx`.
- **Fix:** Start recursive traversal at `p_plan -> 0 -> 'Plan'` and make the failure report the requested index name.
- **Files modified:** `supabase/tests/0011_retrieval_contract.sql`
- **Verification:** Reset-stack positive plan showed the named source index; a deliberately changed expected index failed and included the expected-index failure path.
- **Committed in:** `6d13be6`

---

**Total deviations:** 1 auto-fixed (Rule 1 bug).
**Impact on plan:** Corrects the assertion itself; no production migration, policy, index, or planner settings changed.

## Issues Encountered

The HNSW fixture takes roughly a minute per relation to build locally because each insert maintains the real HNSW index. It remains transaction-local and rolls back completely.

## User Setup Required

None - no external service configuration required.

## Verification

- `supabase db reset` — passed; migrations `0001` through `0011` applied.
- `scripts/verify_retrieval_contract.sh` — passed against the reset local stack; the successful direct source and wiki plans contain their exact named HNSW indexes, then roll back fixture rows.
- Deliberate source expected-index mutation — failed as expected with `missing HNSW index source_chunks_embedding_idx_missing` and the observed plan.
- `bash scripts/ci_check_retrieval_contract.sh` — passed.
- `git diff --check` — passed.

## Next Phase Readiness

Plan 07 can source the contract with `-v retrieval_contract_preflight_only=1` and run `pg_temp.retrieval_contract_preflight(...)` against every newly loaded benchmark corpus before measuring.

---
*Phase: 04-hybrid-retrieval-and-fusion*
*Completed: 2026-08-11*
