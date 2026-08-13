---
phase: 05-citation-integrity-and-answer-apis
reviewed: 2026-08-12T11:30:00+09:00
depth: standard
scope: 05-07 gap closure, with call-site and migration security review
files_reviewed: 9
files_reviewed_list:
  - supabase/migrations/0013_ask_budget_and_verification_audit.sql
  - supabase/migrations/0012_ask_citation_and_graph.sql
  - supabase/migrations/0010_budget_error_sqlstate.sql
  - supabase/migrations/0004_rls_policies.sql
  - apps/worker/src/worker/db/service.py
  - apps/worker/src/worker/__main__.py
  - apps/worker/src/worker/handlers/conflict.py
  - apps/worker/tests/test_service_client.py
  - apps/worker/tests/test_queue.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
status: passed
---

# Phase 05: Code Review Report

**Reviewed:** 2026-08-12T11:30:00+09:00
**Depth:** standard
**Scope:** Plan 05-07 gap closure plus the affected worker call paths, prior trigger/RLS definitions, and local-stack regressions.
**Status:** passed

## Summary

Both prior warnings are closed. Ask preflight now calls a database `sum()` aggregate with no row limit, and its existing `spent < cap` decision still rejects exactly at the inclusive cap boundary. The new RPC is `security invoker`, accepts only the workspace and UTC boundary, has its default execute permissions revoked, and is granted only to `service_role`; the requester-JWT integration test verifies the HTTP boundary is denied.

The replacement verification trigger stamps audit fields only when `auth.uid()` supplies an authenticated human identity. A service-role conflict update therefore copies the prior `verified_by` and `verified_at` pair rather than overwriting it. The local-stack regression performs the real requester verification, then routes the confirmed conflict through the real service-role `set_wiki_page_disputed()` write and confirms the original audit pair remains unchanged.

The expanded `_rpc()` return normalization remains compatible with its existing row-returning callers: object responses retain the former all-null record handling, while the aggregate helper alone accepts scalar or one-column object results and rejects populated unexpected shapes.

## Previously Reported Warnings

### WR-01 — High-volume monthly-cap bypass

**Resolved.** `public.sum_usage_events_since(uuid, timestamptz)` executes `coalesce(sum(u.cost_micros), 0)` over every matching `usage_events` row. `ServiceDb.sum_usage_events_since()` POSTs only the two typed inputs to that RPC and no longer reads `/usage_events` with `limit=1000`.

`test_local_budget_aggregate_is_complete_and_private` inserts 1,001 same-window rows, receives the full total from the service-role RPC, verifies requester access is denied, and confirms `_check_ask_budget()` returns `False` when the cap equals the total.

### WR-02 — Automated dispute overwrites human verification audit

**Resolved.** `stamp_wiki_verification()` preserves `OLD.verified_by` and `OLD.verified_at` whenever the status changes without an authenticated identity. This is the service-role conflict path; requester transitions still receive a DB-derived `auth.uid()` and `now()` stamp. The migration does not alter the editor-only `wiki_pages` update policy.

`test_local_automated_dispute_retains_human_verification_audit` first creates a genuine requester-JWT verification stamp, runs a deterministic confirmed conflict that delegates its dispute write to `ServiceDb`, and asserts the verified page becomes disputed while retaining its exact original audit pair.

## Security and Regression Assessment

- The privileged aggregate has no caller-controlled SQL fragment, collection input, pagination control, or authenticated/anonymous execute grant.
- `security invoker` avoids an unnecessary privilege escalation; the service-role grant and worker-only client provide the intended boundary.
- The trigger is scoped to real verification-status changes and leaves unrelated fields and RLS policies unchanged.
- The local-stack tests exercise PostgREST permissions, PostgreSQL aggregation, and the actual trigger rather than mocks for either fixed behavior.

## Verification

- `git diff --check 874b711^..f414878 -- apps/worker supabase .planning/phases/05-citation-integrity-and-answer-apis` — passed.
- `uv run pytest apps/worker/tests/test_service_client.py apps/worker/tests/test_worker_main.py apps/worker/tests/test_queue.py -x -rs` — passed, 49 tests.
- `uv run pytest -q` — passed (exit code 0).

No Critical, Warning, or Info findings remain in the reviewed gap-closure scope.

---

_Reviewer: Codex (GSD code reviewer)_
_Depth: standard_
