# Phase 7: Integration and Ops Baseline - Context

**Gathered:** 2026-08-13 (interactive discussion for E2E execution and cost/pipeline observability surface; tenant-isolation-suite and search-quality-baseline areas auto-selected on the recommended option per user's explicit "추천안대로 진행해줘" mid-session instruction)
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove the pieces actually work together and establish baselines future regressions get judged against. This phase does not add product capability — it builds verification and observability on top of what Phases 1-6 already shipped. 5 requirements: OPS-02 (E2E ingest→compile→embed→search scenario from an empty workspace), OPS-03 (re-ingestion idempotency including the shrink-reprocessing case), OPS-04 (full-path cross-tenant isolation suite across all 9 tables × read/write/job/Storage), OPS-05 (golden-set search quality + per-channel latency baseline), OPS-06 (per-workspace LLM/embedding cost + job-pipeline observability, surfaced in the dashboard per REQUIREMENTS.md's explicit wording).

</domain>

<decisions>
## Implementation Decisions

### E2E scenario execution (OPS-02)
- **D-01:** The E2E test uses a mocked LLM/embedding provider, never a real OpenRouter call — matches the established codebase convention (`.planning/codebase/TESTING.md`: "OpenRouter LLM calls... responses must be deterministic"; "what NOT to mock: Postgres" — the DB stays real, only the provider is mocked). Zero cost, safe to run repeatedly.
- **D-02:** The test drives real API + worker code through pytest at the API level — `POST /sources → enqueue_source_job → parse → compile → link_sync → embed → search`, extending the existing `03-04-PLAN.md` tracer pattern (which already proved `POST /sources → enqueue → parse → compile` end-to-end) through the remaining chain stages and into a retrieval call. No browser/Playwright involved.
- **D-03:** The new OPS-02/03/04 test suites fold into the existing pytest job in the PR gate (`02-09-PLAN.md`'s 4-job CI gate: pre-commit · service-import grep · bundle-secret grep · pytest) rather than a separate on-demand job — safe because D-01 makes the suite fast and free (mocked LLM, no per-PR cost).
- **D-04:** E2E, idempotency, and isolation tests share one minimal fixture set — one file source, one URL source, one text source — matching what `TESTING.md`'s planned E2E fixture already specified ("3 real sources, one each of PDF/URL/plain text"). Avoids maintaining N parallel fixture sets.

### Cost/pipeline observability surface (OPS-06)
- **D-05:** The observability panel lives inside the existing workspace Settings page as a new tab/panel, not a new top-level nav route — consistent with `06-CONTEXT.md`'s D-04 (member invite already lives in a Settings-page form, not a modal or separate route). Reuses Phase 6's Settings-page shell rather than extending the "5 surfaces" primary navigation Phase 6 already built.
- **D-06:** Cost (`usage_events` aggregate vs. `workspaces.monthly_budget_micros`) and job-pipeline health (per-stage queued/running/dead counts) render together on one panel — REQUIREMENTS.md's OPS-06 wording ties them in a single sentence ("LLM/임베딩 비용과 잡 파이프라인 상태가 관측 가능해") rather than describing two separate features.
- **D-07:** Data refreshes on page load / manual refresh only — no polling loop. Mirrors `06-05-PLAN.md`'s JobStepper, which polls only while a job is actively in-progress; a workspace-wide cost/health summary has no equivalent "in-progress" trigger to poll against.
- **D-08:** Visible to `editor` role and above (owner + editor), not `viewer` — mirrors `05-CONTEXT.md`'s D-06 (verification-transition API also gated at editor+). Cost data is operational/financial information, not content a read-only collaborator needs.

### Tenant isolation full-path suite (OPS-04) — auto-selected, recommended option
- **D-09:** Built as a pytest integration suite at the API level (same layer as D-02/D-03) hitting the real local Supabase stack — Postgres is never mocked (`TESTING.md`'s explicit rule; RLS/composite-FK enforcement is a database behavior no mock can simulate). Extends the existing `test_workspaces_isolation.py` (Phase 2's SEC-06, single-table) to all 9 tables × SELECT/INSERT/UPDATE/DELETE × the job-queue RPCs × Storage paths.
  - **Rationale for local-only scope (not re-run against Supabase Cloud):** `STATE.md`'s Phase 2 blocker note flags cloud isolation as unconfirmed, but the RLS policies under test are schema-defined (`0004`/`0007`) and identical between local and cloud once migrations are applied — re-running the full matrix on cloud would verify migration-apply correctness, not isolation logic, and duplicates cost/time for near-zero incremental signal. Reuses the fixture principal set `TESTING.md` already specifies: workspace A (owner/editor/viewer) + workspace B (owner) + non-member + anon.
  - Folds into the same pytest CI job as D-03.

### Search quality/latency baseline scale (OPS-05, resolves WINDOWS.md #10) — auto-selected, recommended option
- **D-10:** Use synthetic 1024-dim vectors to pad the corpus to 10^4–10^5 rows locally, free of cost — this is the exact path `docs/ops/hnsw-order-benchmark.md`'s own limitations section and `STATE.md`'s Phase 4 blocker note already identify as available ("언더필·플랜 형태는 합성 1024차원 벡터로 로컬에서 무료 선행 가능"). This resolves the specific gap `04-04-PLAN.md`'s Task 3 left open: at the prior 12/12/8-row corpus the planner never selected HNSW at all (btree+sort cost 233 vs. HNSW 349,657), making a `strict_order` vs. `relaxed_order` comparison meaningless.
- **D-11:** Layer the real RTV-06 golden set (30-50 Korean/English/mixed queries, already built in Phase 4) into the padded corpus so recall/rank metrics are measured against real evidence-labeled queries, not synthetic ones — synthetic rows only need to exist to push the planner into HNSW territory; they are not queried directly.
- **D-12:** Run the padded-corpus benchmark locally first (free); escalate to Railway/production-like hardware only if the local result is inconclusive — consistent with the project's budget constraint (개인 프로젝트 수준 예산, `PROJECT.md` §Constraints) and the precedent that Phase 2's transport spike and Phase 2's RTT baseline were the only prior cases that required actual cloud measurement.

### Claude's Discretion
- Exact panel layout/component structure for the OPS-06 usage panel (D-05/D-06) — planner's call, reusing Phase 6's existing Settings-page component patterns.
- Precise pytest fixture helper API for the shared minimal fixture set (D-04) and the 9-table isolation matrix (D-09) — researcher/planner should design for reuse across OPS-02/03/04 without inventing three separate fixture-setup code paths.
- Exact synthetic-vector generation method and corpus composition ratio (D-10/D-11) — researcher should investigate what produces a representative HNSW plan shape without requiring real embeddings.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contract and requirements
- `.planning/ROADMAP.md` §Phase 7 (277-291행) — goal, 5 requirements (OPS-02…06), 5 success criteria.
- `.planning/REQUIREMENTS.md` §Cost, Verification & Ops (OPS-01…06, 112-119행) — requirement text; OPS-06's explicit "대시보드에서" wording is the source of D-05/D-06.
- `.planning/REQUIREMENTS.md` 279행 — SEC-06 vs OPS-04 boundary note (SEC-06 = single Phase 2 isolation test; OPS-04 = full post-application-complete suite). Do not re-litigate this split.
- `.planning/PROJECT.md` §Constraints — budget line ("개인 프로젝트 수준 예산") backing D-12's local-first-then-escalate approach.

### Open items this phase must close
- `.planning/WINDOWS.md` id 10 — HNSW strict_order/relaxed_order comparison never run at meaningful scale; D-10/D-11 close this.
- `.planning/WINDOWS.md` id 6 — COMP-07 shrink-reprocessing deletion path never observed with an actually-shrinking input (only same-size smoke tested); OPS-03 must exercise a genuine chunk-count-decrease case, not repeat the same-body smoke test.
- `docs/ops/hnsw-order-benchmark.md` §한계 — documents exactly what corpus scale and comparability conditions D-10/D-11 must satisfy.
- `.planning/STATE.md` Blockers/Concerns (Phase 2 entry) — "격리 왕복 증명은 workspaces 한 테이블·로컬 스택에 한정... 전수 스위트는 Phase 7 OPS-04" — this phase is where that debt is paid.

### Prior-phase decisions this phase inherits (do not re-litigate)
- `.planning/phases/06-dashboard/06-CONTEXT.md` > **D-04** — Settings-page form pattern (not modal), reused by D-05.
- `.planning/phases/05-citation-integrity-and-answer-apis/05-CONTEXT.md` > **D-06** — editor+ role gate pattern for operational/write endpoints, reused by D-08.
- `.planning/phases/04-hybrid-retrieval-and-fusion/04-CONTEXT.md` > **D-05~D-08** — fusion policy stays in a versioned Python layer; any OPS-05 finding that suggests a policy change must go through `docs/ops/retrieval-policy-change-log.md`, not be applied directly in this phase.
- `.planning/phases/03-ingest-and-compile-pipeline/03-CONTEXT.md` and `03-04-PLAN.md` — the tracer pattern D-02 extends (`POST /sources → enqueue → parse → compile`), and COMP-07's `upsert_and_truncate` shrink-reprocessing contract that OPS-03 must verify end-to-end.
- `.planning/phases/02-security-spine-and-shared-domain/02-CONTEXT.md` — RLS/isolation model (`USING` violation → 0 rows, `WITH CHECK` violation → 42501) that OPS-04's assertions must distinguish, per the existing `test_workspaces_isolation.py` pattern.

### Existing schema/API (reuse, do not reimplement)
- `apps/api/tests/test_workspaces_isolation.py` — Phase 2's SEC-06 single-table isolation test; OPS-04 extends this pattern to all 9 tables, not a rewrite.
- `apps/worker/src/worker/db/service.py` — `upsert_and_truncate` shrink-reprocessing logic (COMP-07); OPS-03's target.
- `supabase/migrations/0009_*.sql` — `usage_events` table + workspace `monthly_budget_micros`; OPS-06's cost-panel data source.
- `apps/api/src/api/routers/jobs.py` — existing job-status router; OPS-06's pipeline-health panel reads from here rather than duplicating job-state logic.
- `.planning/codebase/TESTING.md` §Idempotency testing / §RLS test fixture pattern — the exact assertion discipline (row-count deltas, not output equality; 0-rows-vs-42501 distinction; A/B/non-member/anon principal matrix) this phase's suites must follow.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/api/tests/test_workspaces_isolation.py` — isolation test scaffolding (principal fixtures, auth helpers) to extend for the 9-table matrix.
- `apps/worker/tests/test_handlers.py` — existing parse/compile/link_sync/embed handler test patterns, useful as building blocks for the E2E chain test (D-02).
- Phase 6 Settings-page components (`apps/dashboard/`, member-invite panel per `06-03-PLAN.md`) — layout/pattern to extend for the D-05 usage panel.

### Established Patterns
- Mock the LLM/embedding provider, never Postgres (`TESTING.md`) — governs D-01/D-09.
- 0-rows-affected → 403, single exception handler (`api/errors.py`, Phase 2 D-11~13) — governs OPS-04 assertion shapes.
- Job state only ever transitions through `claim_job`/`complete_job`/`fail_job`/`reap_stale_jobs` — never `UPDATE jobs` directly, including from tests.
- Korean comments/commit messages, English identifiers — maintained throughout; Phase 7 code matches.

### Integration Points
- `apps/api/tests/` and `apps/worker/tests/` — where OPS-02/03/04 suites land, following the existing `test_<module>.py` naming.
- `.github/workflows/` (from `02-09-PLAN.md`) — the pytest job these new suites fold into (D-03).
- `apps/dashboard/app/w/[workspaceId]/settings/` (Phase 6) — where the OPS-06 usage panel attaches.

</code_context>

<specifics>
## Specific Ideas

User confirmed recommended options interactively for two areas (E2E execution mode, cost/pipeline observability surface) via four-question rounds each, then explicitly instructed "추천안대로 진행해줘" (proceed with the recommended option) for the remaining two areas — tenant isolation suite structure and search-quality-baseline scale — which were resolved using the already-documented recommended paths from `docs/ops/hnsw-order-benchmark.md` and `TESTING.md` rather than further interactive questions.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. No scope-creep suggestions arose.

</deferred>

---

*Phase: 7-Integration and Ops Baseline*
*Context gathered: 2026-08-13*
