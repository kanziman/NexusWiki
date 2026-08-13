---
phase: 7
slug: integration-and-ops-baseline
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-08-13
---

# Phase 7 — Validation Strategy

> Validate real local Supabase behavior while mocking only paid, nondeterministic providers.

## Test Infrastructure

| Property | Value |
|---|---|
| **Backend** | pytest 9.1.1 + pytest-asyncio 1.4.0 |
| **Frontend** | Vitest 4.1.10 + Testing Library |
| **Quick backend run** | `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -q apps/api/tests/test_pipeline_e2e.py apps/api/tests/test_reingestion_idempotency.py apps/api/tests/test_tenant_isolation_full_path.py apps/api/tests/test_jobs_router.py` |
| **Dashboard run** | `pnpm --dir apps/dashboard test && pnpm --dir apps/dashboard typecheck` |
| **Full suite** | `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -rs` |

## Sampling Rate

- **After every task commit:** run the affected focused pytest or Vitest file.
- **After every plan wave:** run the quick backend set and dashboard test/typecheck where applicable.
- **Before verification:** start the local Supabase stack, run the root pytest suite with `-rs`, dashboard tests/typecheck, and the pinned benchmark comparator.
- **Max feedback latency:** 60 seconds for focused tests; benchmark runs are recorded separately.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | Status |
|---|---|---|---|---|---|---|---|
| 07-01-* | 01 | 1 | OPS-02, OPS-03 | Real RLS/queue/Storage state is exercised; doubles replace only providers. | local-stack integration | focused backend pytest | ⬜ pending |
| 07-02-* | 02 | 2 | OPS-04 | The Plan 07-01 shared file/URL/text fixture is reused; foreign reads are empty; foreign writes/RPC/Storage are denied; own-workspace controls succeed. | local-stack integration matrix | focused backend pytest | ⬜ pending |
| 07-03-* | 03 | 2 | OPS-05 | Corpus, golden set, policy, and git revision pins remain comparable; records append only. | benchmark + comparator | benchmark runner and comparator | ⬜ pending |
| 07-04-* | 04 | 1 | OPS-06 | Owner/editor endpoint and UI work; viewer request/tab is denied/absent; response leaks no payload/error/provider data. | API + component | focused backend pytest and dashboard test/typecheck | ⬜ pending |

## Wave 0 Requirements

Existing pytest and Vitest infrastructure covers this phase. No dependency installation or test-runner bootstrap is allowed.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|---|---|---|---|
| Local HNSW plan is meaningful | OPS-05 | Hardware/planner behavior cannot be made stable in the normal unit suite. | Run the pinned 50k corpus benchmark locally; record EXPLAIN plan and comparator result. Escalate only if inconclusive. |
| Narrow Settings layout | OPS-06 | Browser rendering is complementary to DOM assertions. | Inspect the Operations tab at a narrow viewport: stage container scrolls horizontally and text/counts are not clipped. |

## Validation Sign-Off

- [ ] Every task has a focused automated command.
- [ ] No suite mocks Postgres, RLS, queue, Storage, or HNSW behavior.
- [ ] Benchmark evidence is append-only and pinned for comparability.
- [ ] `nyquist_compliant: true` is set after task-to-plan mapping is finalized.

**Approval:** pending
