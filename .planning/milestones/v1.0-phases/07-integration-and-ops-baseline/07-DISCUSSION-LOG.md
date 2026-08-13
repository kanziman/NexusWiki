# Phase 7: Integration and Ops Baseline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-13
**Phase:** 7-Integration and Ops Baseline
**Areas discussed:** E2E scenario execution (OPS-02), Cost/pipeline observability surface (OPS-06), Tenant isolation full-path suite (OPS-04, auto-selected), Search quality/latency baseline scale (OPS-05, auto-selected)

---

## E2E scenario execution (OPS-02)

### LLM call mode

| Option | Description | Selected |
|--------|-------------|----------|
| Mock (repeatable, $0 cost) | Matches TESTING.md convention; CI-safe, deterministic | ✓ |
| Hybrid (real once for evidence, mock for repeatable suite) | Real LLM once, documented in docs/ops; repeatable suite mocked | |
| Real LLM every run | Most accurate but costs money every run, flaky | |

**User's choice:** Mock

### Execution layer

| Option | Description | Selected |
|--------|-------------|----------|
| pytest drives real API+worker processes (API level) | Extends 03-04 tracer through link_sync/embed/search | ✓ |
| Playwright UI E2E | Same pattern as Phase 6 UAT, catches UI regressions too | |
| Hybrid — pytest API-level primary, Playwright for UAT only | | |

**User's choice:** pytest at API level

### CI integration

| Option | Description | Selected |
|--------|-------------|----------|
| Fold into existing pytest job (mock-premised) | Fast, deterministic, runs every PR | ✓ |
| Separate job (manual/scheduled trigger) | For slow/expensive suites | |

**User's choice:** Fold into existing pytest job

### Shared test fixtures

| Option | Description | Selected |
|--------|-------------|----------|
| Shared minimal fixture (1 file, 1 URL, 1 text source) | Matches TESTING.md's planned E2E fixture | ✓ |
| Separate fixtures per test type | Clearer intent per test, more maintenance | |

**User's choice:** Shared minimal fixture

**Notes:** User confirmed all four via structured question rounds; no free-text deviation.

---

## Cost/pipeline observability surface (OPS-06)

### Panel placement

| Option | Description | Selected |
|--------|-------------|----------|
| New tab/panel inside existing workspace Settings page | Matches 06-CONTEXT.md D-04 (invite form lives in Settings, not a modal) | ✓ |
| Independent new route (`/w/[id]/usage`) | More visible but expands Phase 6's "5 surfaces" nav design | |

**User's choice:** Settings page tab/panel

### Panel content scope

| Option | Description | Selected |
|--------|-------------|----------|
| Cost + job pipeline state together on one page | Matches OPS-06's single-sentence requirement wording | ✓ |
| Separate sections/tabs for cost vs. job state | Cleaner scaling, less convenient overview | |

**User's choice:** Both together on one page

### Refresh mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Page load / manual refresh only (no polling) | Matches JobStepper precedent (polls only while a job is in-progress) | ✓ |
| Periodic polling (e.g. 30s) | Adds network/complexity for a summary view with no natural in-progress trigger | |

**User's choice:** Page load / manual refresh only

### Access permission

| Option | Description | Selected |
|--------|-------------|----------|
| editor and above (owner + editor) | Matches 05-CONTEXT.md D-06 precedent (editor+ for operational writes) | ✓ |
| All members including viewer | More transparent but exposes financial/operational data to read-only collaborators | |

**User's choice:** editor and above

**Notes:** User confirmed all four via structured question rounds.

---

## Tenant isolation full-path suite (OPS-04) — auto-selected

User instructed "추천안대로 진행해줘" (proceed with the recommended option) partway through the session; this area was resolved using the recommended option documented in CONTEXT.md D-09 rather than further interactive questions:

- pytest integration suite, API level, against the real local Supabase stack (Postgres never mocked)
- Extends the existing `test_workspaces_isolation.py` (Phase 2 SEC-06, single-table) to all 9 tables × SELECT/INSERT/UPDATE/DELETE × job-queue RPCs × Storage
- Local-only scope (not re-run on Supabase Cloud) — RLS policies are schema-defined and identical once migrations apply; re-running on cloud would test migration-apply correctness, not isolation logic
- Reuses the A/B/non-member/anon principal fixture set already specified in `.planning/codebase/TESTING.md`
- Folds into the same pytest CI job as OPS-02/03

## Search quality/latency baseline scale (OPS-05, resolves WINDOWS.md #10) — auto-selected

Also resolved via "추천안대로 진행해줘" using the path already documented as available in `docs/ops/hnsw-order-benchmark.md` and `STATE.md`'s Phase 4 blocker note:

- Synthetic 1024-dim vectors pad the corpus to 10^4–10^5 rows locally, free of cost — resolves the specific gap where the prior 12/12/8-row corpus never made the query planner select HNSW at all
- The real RTV-06 golden set (30-50 queries) is layered into the padded corpus so recall/rank metrics come from real evidence-labeled queries
- Local-first: run the padded-corpus benchmark locally before considering any Railway/production-like hardware run, consistent with the project's tight budget

---

## Claude's Discretion

- Exact panel layout/component structure for the OPS-06 usage panel — reuses Phase 6's Settings-page component patterns.
- Precise pytest fixture helper API for the shared minimal fixture set (OPS-02/03) and the 9-table isolation matrix (OPS-04) — researcher/planner should design for reuse across all three rather than three separate fixture-setup paths.
- Exact synthetic-vector generation method and corpus composition ratio (OPS-05) — researcher should investigate what produces a representative HNSW plan shape without requiring real embeddings.

## Deferred Ideas

None — discussion stayed within phase scope. No scope-creep suggestions arose.
