---
phase: 07-integration-and-ops-baseline
plan: 04
status: complete
completed: 2026-08-13
requirements: [OPS-06]
commits: [310f58d, 24603c1]
---

# Phase 7 Plan 04 Summary

Delivered an owner/editor-only Operations snapshot in the existing Settings route.

## Completed

- Added `GET /workspaces/{workspace_id}/operations`, with requester-JWT role enforcement through the existing `has_workspace_role` helper and RLS-scoped direct reads.
- The fixed allowlisted DTO provides display-only monthly budget data, UTC month boundary, 1,000-event truncation signal, five server-ordered stage counts, and observation time. It does not expose payloads, errors, usage metadata, provider, or model fields.
- Added server-side Settings membership lookup and accessible 멤버/운영 현황 tabs. Viewer has no Operations tab and sends no Operations request.
- Added one-entry fetch plus explicit manual refresh only; no timer, polling, retry, cancel, payload, or raw backend error UI exists.
- Added skeleton, refresh retention, cap-zero, zero-usage, partial aggregate, unavailable aggregation, all-zero pipeline, server label tooltip/truncation, and large formatting backstop coverage.

## Verification

`UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -q apps/api/tests/test_jobs_router.py && pnpm --dir apps/dashboard test -- OperationsPanel.test.tsx && pnpm --dir apps/dashboard typecheck`

Result: 16 API tests passed; 17 dashboard test files / 82 tests passed; TypeScript check passed.

## Task Commits

1. `310f58d` — owner/editor-authorized Operations API snapshot and router coverage.
2. `24603c1` — Settings tabs, manual-refresh Operations panel, and component coverage.
3. No code change: ran the complete focused OPS-06 API/dashboard evidence set.

## Deviations

- Rule 2: used the existing server-side `has_workspace_role` RPC for the authoritative editor-or-owner gate. Its fixed, requester-JWT membership check is already the project security primitive; no new migration or parallel authorization model was introduced.
