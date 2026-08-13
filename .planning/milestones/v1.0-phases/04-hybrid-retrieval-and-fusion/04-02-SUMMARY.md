---
phase: 04-hybrid-retrieval-and-fusion
plan: 02
subsystem: retrieval-database
tags: [supabase, rls, hnsw, lexical, graph]
requires:
  - "04-01 retrieval tracer and approved private query-embedding boundary"
provides:
  - "Service-role lexical materialization RPCs"
  - "Authenticated vector, lexical, and bounded graph retrieval RPCs"
  - "Local SQL and source-level retrieval contract gates"
affects:
  - "04-03 five-channel retrieval orchestration"
key-files:
  created:
    - supabase/migrations/0011_retrieval.sql
    - supabase/tests/0011_retrieval_contract.sql
    - docs/ops/migration-0011-record.md
  modified:
    - apps/worker/src/worker/db/service.py
    - apps/worker/src/worker/handlers/parse.py
    - apps/worker/src/worker/handlers/compile.py
requirements-completed: [RTV-03, RTV-07, RTV-08]
status: complete
---

# Phase 4 Plan 02 Summary

Established the database boundary for hybrid retrieval. Worker-only volatile
writers materialize Python-normalized bigrams; authenticated security-invoker
RPCs provide source/wiki vector and lexical retrieval plus bounded graph
expansion.

## Task Commits

1. **Task 1: retrieval RPC boundary and worker lexical writes** — `d1464f3`
2. **Task 2: retrieval SQL/API contract gates** — `fe6e949`
3. **Corrective migration validation** — `bc4fba0`

## Verification

- Local reset applied `0011` successfully.
- `scripts/verify_retrieval_contract.sh` printed `retrieval_contract: ok`.
- `bash scripts/ci_check_retrieval_contract.sh` passed.
- Focused worker/API tests: `32 passed, 1 skipped` (existing local-stack guard).
- Remote push applied `0011_retrieval.sql`; post-push ledger lists `0011` exactly once.
- Remote catalog check confirmed authenticated-only stable search/graph RPCs and service-role-only volatile lexical writers.

## Deviation

The first remote attempt exposed an unaliased lexical rank expression. The
single-transaction migration rolled back and did not enter the remote ledger.
After root-cause reproduction, `bc4fba0` added `AS rank` in both lexical
queries; local reset and contract verification passed before renewed approval.

## Next Phase Readiness

Plan 03 can orchestrate the five channels against these deployed RPC contracts.
