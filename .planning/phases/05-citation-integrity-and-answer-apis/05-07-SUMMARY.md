---
phase: 05-citation-integrity-and-answer-apis
plan: 07
subsystem: database
tags: [supabase, postgrest, ask-budget, verification-audit, testing]
requires:
  - phase: 05-04
    provides: Ask monthly budget preflight
  - phase: 05-06
    provides: service-role conflict dispute writes
provides:
  - Complete service-role Ask usage aggregate with no pagination cap
  - Durable human verification audit fields through automated disputes
  - Local-stack and linked-Cloud evidence for both safety fixes
affects: [ask, worker, conflict-detection, supabase]
actuals:
  tokens: 12000
  tasks: 4
  commits: 4
tech-stack:
  added: []
  patterns: [service-only aggregate RPC, trigger preserves human audit on automation]
key-files:
  created:
    - supabase/migrations/0013_ask_budget_and_verification_audit.sql
  modified:
    - apps/worker/src/worker/db/service.py
    - apps/worker/tests/test_service_client.py
    - apps/worker/tests/test_queue.py
key-decisions:
  - "Ask spend is summed by PostgreSQL rather than a capped PostgREST row page."
  - "Only authenticated human transitions establish verification audit fields; automated disputes retain OLD values."
patterns-established:
  - "Privileged aggregate RPCs revoke default execution and grant only service_role."
requirements-completed: [QC-02, OPS-01]
coverage:
  - id: D1
    description: Complete Ask monthly-spend aggregate blocks exactly at the cap after more than 1,000 events.
    requirement: OPS-01
    verification:
      - kind: integration
        ref: apps/worker/tests/test_queue.py#test_local_budget_aggregate_is_complete_and_private
        status: pass
    human_judgment: false
  - id: D2
    description: Automated disputes retain a prior human verifier identity and timestamp.
    requirement: QC-02
    verification:
      - kind: integration
        ref: apps/worker/tests/test_queue.py#test_local_automated_dispute_retains_human_verification_audit
        status: pass
    human_judgment: false
---

# Phase 05 Plan 07: Citation Integrity Gap Closure Summary

**Ask budget preflight now reads the complete database aggregate, while service-role conflict automation preserves human verification audit history.**

## Accomplishments

- Added migration `0013` with a stable, service-role-only `sum_usage_events_since` RPC and audit-preserving verification trigger.
- Replaced the worker's capped `usage_events` read with the aggregate RPC and covered scalar/composite PostgREST responses.
- Proved both fixes against the local Supabase/PostgREST stack: 1,001 usage events, requester-RPC denial, inclusive cap rejection, and a real service-role dispute following human verification.
- Deployed migration `0013_ask_budget_and_verification_audit.sql` to the linked Supabase Cloud project and inspected its public-schema dump.

## Task Commits

1. **Task 1: Add a complete usage aggregate and preserve verification stamps** — `874b711`
2. **Task 2: Route Ask preflight through the aggregate RPC** — `9f0c711`
3. **Task 3: Prove both fixes on a real local stack** — `3063881`
4. **Task 4: Deploy migration to linked Supabase Cloud** — no source commit; deployment completed successfully.

## Verification

- `supabase db reset && supabase db lint` — passed.
- `uv run pytest apps/worker/tests/test_queue.py apps/worker/tests/test_service_client.py apps/worker/tests/test_handlers.py apps/worker/tests/test_worker_main.py -x -rs` — 66 passed.
- `uv run pytest -q` — 408 passed.
- `supabase db push --yes` — pushed only `0013_ask_budget_and_verification_audit.sql` to the linked remote.
- `supabase db dump --linked --schema public` — confirmed `sum_usage_events_since(uuid, timestamptz)`, its `service_role` grant, and the `old.verified_by` / `old.verified_at` preservation branch. The inspected disposable dump was removed afterward.
- `git diff --check HEAD -- apps/worker supabase .planning/phases/05-citation-integrity-and-answer-apis` — passed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

Phase 05's two verification gaps are closed. The phase is ready for a fresh verification pass and completion workflow. Existing unrelated dirty planning and documentation files were deliberately not staged or changed.
