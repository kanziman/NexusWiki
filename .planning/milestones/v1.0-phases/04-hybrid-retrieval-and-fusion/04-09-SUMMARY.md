---
phase: 04-hybrid-retrieval-and-fusion
plan: 09
subsystem: retrieval
tags: [retrieval, hnsw, benchmark, comparator, evidence, tdd]

requires:
  - phase: 04-08
    provides: full-path golden-query retrieval evidence and the initial (defective) order/graph comparator

provides:
  - a comparator that pins runner identity (git_sha) and validates the order-mode pair, so it cannot silently accept two records captured from different revisions
  - a genuinely comparable v5 strict/relaxed evidence pair from one identical committed revision
  - decision-log correction marking the v4 strict/relaxed pair superseded-invalid

affects: [retrieval, operations, policy-governance]

actuals:
  tokens: 102000
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Benchmark record comparators pin runner identity (git_sha) alongside data/policy pins so a runner-revision mismatch fails closed instead of silently comparing incomparable runs."
    - "compare_order_records() asserts the exact {strict_order, relaxed_order} shape independent of pin equality, so a same-order_mode pair cannot pass even when every other pin matches."

key-files:
  created:
    - docs/ops/benchmark-records/phase-04-rerun-v5-strict-order.json
    - docs/ops/benchmark-records/phase-04-rerun-v5-relaxed-order.json
  modified:
    - scripts/benchmark_retrieval.py
    - packages/core/tests/test_retrieval_golden.py
    - docs/ops/hnsw-order-benchmark.md

key-decisions:
  - "_pins() gains git_sha as its ninth pinned field; both compare_order_records() and compare_graph_records() inherit the fix via the shared helper, so no new error string was introduced for the git_sha case."
  - "The v4 strict/relaxed pair is retained byte-for-byte but is now explicitly documented as superseded-invalid; it is never deleted, overwritten, or renumbered."
  - "The v5 pair's relaxed arm again shows zero vector-channel hits, now measured from one pinned revision rather than a runner-mismatch artifact; this reinforces (does not newly justify) keeping strict_order as the default. Root-causing the relaxed-order zero-hit behavior is explicitly out of scope for this plan."

patterns-established:
  - "TDD RED/GREEN for a data-fidelity bug: write a test that replays the exact historical invalid pair before touching the fix, confirm it fails for the right reason, then fix and confirm GREEN."

requirements-completed: [RTV-04]

coverage:
  - id: D1
    description: "compare_order_records() rejects the historical invalid v4 strict/relaxed pair (differing git_sha) and any same-order_mode pair, while compare_graph_records() keeps accepting the historical valid v4 graph pair."
    requirement: RTV-04
    verification:
      - kind: unit
        ref: "packages/core/tests/test_retrieval_golden.py::test_compare_order_records_rejects_historical_invalid_v4_pair_with_mismatched_git_sha"
        status: pass
      - kind: unit
        ref: "packages/core/tests/test_retrieval_golden.py::test_compare_order_records_rejects_matching_order_mode_pair"
        status: pass
      - kind: unit
        ref: "packages/core/tests/test_retrieval_golden.py::test_compare_graph_records_still_accepts_historical_valid_v4_graph_pair"
        status: pass
      - kind: integration
        ref: "uv run python scripts/benchmark_retrieval.py compare-order-records --left docs/ops/benchmark-records/phase-04-rerun-v4-strict-order.json --right docs/ops/benchmark-records/phase-04-rerun-v4-relaxed-order.json (exit 2, order_pair_pin_or_policy_mismatch)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A new v5 strict/relaxed record pair, generated back-to-back from one identical committed git revision against a freshly loaded corpus, passes the fixed comparator with matching git_sha, and docs/ops/hnsw-order-benchmark.md records the outcome while marking v4 superseded."
    requirement: RTV-04
    verification:
      - kind: integration
        ref: "uv run python scripts/benchmark_retrieval.py compare-order-records --left docs/ops/benchmark-records/phase-04-rerun-v5-strict-order.json --right docs/ops/benchmark-records/phase-04-rerun-v5-relaxed-order.json (status: ok)"
        status: pass
      - kind: other
        ref: "docker exec supabase_db_NexusWiki psql -c \"select count(*) from public.workspaces where id='ca4d1e07-2a51-5701-94d5-41c9a6081c6b'\" == 0 after both arms"
        status: pass
    human_judgment: false

duration: 5min
completed: 2026-08-11
status: complete
---

# Phase 04 Plan 09: Order-Comparator Gap Closure Summary

**Fixed the exact runner-identity gap 04-VERIFICATION.md found in `compare_order_records()` — `_pins()` now includes `git_sha` and the comparator asserts a distinct `{strict_order, relaxed_order}` pair — then used the fixed comparator to produce and validate a genuinely comparable v5 strict/relaxed pair from one identical commit, closing RTV-04.**

## Performance

- **Duration:** ~5 min (test commit to final evidence commit)
- **Started:** 2026-08-11T13:26:14Z
- **Completed:** 2026-08-11T13:31:17Z
- **Tasks:** 2
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments

- Reproduced the exact 04-VERIFICATION.md defect as a failing regression test (RED) before touching the fix: the historical v4 strict (`git_sha 6adb0453...`) vs relaxed (`git_sha 4662056...`) pair passed `compare_order_records()` when it should not have.
- Fixed `_pins()` to include `git_sha` as its ninth pinned field — a single shared-helper change that both `compare_order_records()` and `compare_graph_records()` inherit via their existing `_pins(left) != _pins(right)` checks, so no new error string was needed.
- Added an explicit order-mode-pair assertion to `compare_order_records()` (`{left.order_mode, right.order_mode} == {"strict_order", "relaxed_order"}`), proven independent of pin equality by a test using two byte-identical copies of the same record.
- Confirmed no regression: `compare_graph_records()` still returns `status: ok` for the historical valid v4 graph-off/graph-on pair after the shared `_pins()` change.
- Ran the fixed comparator against the historical v4 strict/relaxed pair and confirmed it now exits non-zero with `order_pair_pin_or_policy_mismatch` — the exact proof the fix catches the gap that produced this plan.
- Generated a new v5 strict/relaxed record pair from one clean, committed revision (`git_sha b9cda858...`), running both arms back-to-back with nothing committed in between and confirming each arm's scoped benchmark workspace had 0 residual rows after cleanup.
- Ran the fixed comparator against the v5 pair: `status: ok`, `quality_delta: -0.7222222222222222`.
- Updated `docs/ops/hnsw-order-benchmark.md` to record the v5 outcome and explicitly mark the v4 strict/relaxed pair superseded-invalid, citing both differing `git_sha` values — the v4 JSON files themselves were preserved byte-for-byte.

## Task Commits

Each task was committed atomically (Task 1 followed TDD RED → GREEN):

1. **Task 1a: RED — failing regression tests** — `048d46c` (test)
2. **Task 1b: GREEN — pin git_sha, assert order-mode pair** — `b9cda85` (fix)
3. **Task 2: regenerate v5 pair, update decision log** — `e0f3837` (docs)

_No plan-metadata commit is listed separately; STATE.md/ROADMAP.md/REQUIREMENTS.md updates land in the final commit created by this execution step._

## Files Created/Modified

- `scripts/benchmark_retrieval.py` — `_pins()` now returns `git_sha` alongside the existing eight keys; `compare_order_records()` additionally rejects a pair whose `order_mode` values are not exactly `{strict_order, relaxed_order}`.
- `packages/core/tests/test_retrieval_golden.py` — three new regression tests proving the fix catches the historical invalid v4 pair, rejects any same-`order_mode` pair, and does not regress the graph comparator.
- `docs/ops/benchmark-records/phase-04-rerun-v5-strict-order.json` — new append-only valid strict-order full-path evidence, `git_sha b9cda858979619da23121a341569a58afed61c46`.
- `docs/ops/benchmark-records/phase-04-rerun-v5-relaxed-order.json` — new append-only valid relaxed-order full-path evidence, same `git_sha` as the strict record.
- `docs/ops/hnsw-order-benchmark.md` — new "v4 strict/relaxed 쌍 — superseded-invalid" and "v5 strict/relaxed 쌍" sections; v4 rows in the existing table are unchanged (not deleted/edited), just no longer cited as valid comparability evidence.

## Decisions Made

- Kept the shared `_pins()` fix flowing into both comparators rather than adding a separate `git_sha` check only to `compare_order_records()` — this matches the plan's explicit instruction not to invent a new error string for the `git_sha` case, and it is the reason Task 1 had to re-verify the graph comparator as a non-regression check.
- Did not attempt to fix or explain why the relaxed-order arm shows zero vector-channel hits on this corpus (both in the invalid v4 record and now in the valid v5 record) — that is a retrieval-behavior question, out of scope for a comparator/evidence-fidelity gap-closure plan. Documented the observation transparently in `docs/ops/hnsw-order-benchmark.md` instead of investigating further.
- Did not run `git stash` or otherwise touch the pre-existing unrelated uncommitted files (`.planning/`, `HANDOFF.md`, `checklists.json`, `docs/architecture/`, `docs/design-systems/`, untracked prior-session benchmark records) that were present in the working tree before this plan started. Instead, verified the invariant that actually matters for comparability — `git status --porcelain -- scripts/ apps/ packages/ supabase/` was clean throughout both v5 arm captures, and no commit occurred between the two arms — and documented this narrower, code-path-scoped clean-tree check explicitly in `docs/ops/hnsw-order-benchmark.md` rather than silently claiming a literal fully-clean `git status --porcelain`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 4 boundary, resolved without escalation — clean-tree precondition scope] Interpreted "clean working tree" as scoped to the benchmark's code paths, not the entire repo**
- **Found during:** Task 2 precondition check
- **Issue:** The task's `<precondition>` and `<action>` literally require `git status --porcelain` to be empty before running either arm. The working tree had pre-existing, plan-unrelated uncommitted changes (`.planning/STATE.md`, `.planning/config.json`, `HANDOFF.md`, `checklists.json`, several untracked docs/prior-session benchmark JSON files) that the orchestrator's context explicitly instructed me not to touch, revert, or include in any commit.
- **Fix:** Verified the invariant the precondition actually protects — that neither arm's `git_sha` (captured via `git rev-parse HEAD`) nor the executed code differs between arms — by confirming `git status --porcelain -- scripts/ apps/ packages/ supabase/` was clean (no dirty files in any directory that affects the benchmark's code path) and that no commit landed between the two arm invocations. Documented this narrower check explicitly in `docs/ops/hnsw-order-benchmark.md` (⚠️ git 작업 트리 참고 note) rather than silently asserting a full clean tree that wasn't true.
- **Files modified:** None beyond the plan's own file list; this was a verification-scope decision, not a code change.
- **Verification:** Both v5 records carry byte-identical `git_sha b9cda858979619da23121a341569a58afed61c46`; `git rev-parse HEAD` was checked immediately before and immediately after both arms and was unchanged.
- **Committed in:** `e0f3837` (Task 2 commit; the deviation is documented in the same commit's file, `docs/ops/hnsw-order-benchmark.md`)

---

**Total deviations:** 1 (precondition-scope interpretation, no code impact)
**Impact on plan:** None on correctness of the delivered evidence — the actual comparability guarantee (matching `git_sha`, no intervening commit, unaffected code paths) holds and is independently verifiable from the two JSON records' `git_sha` fields. The deviation is fully transparent in the decision-log documentation rather than hidden.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- RTV-04 is closed. All 9 Phase 04 requirements (RTV-01 through RTV-09) are now SATISFIED per `04-VERIFICATION.md` plus this plan's closure of the sole remaining gap.
- `supabase/migrations/0011_retrieval.sql`'s `strict_order` default and `packages/core/src/nexuswiki_core/retrieval_policy.py:38`'s `graph_enabled=False` default remain unchanged — no policy or migration decision was made by this plan.
- Phase 04 is ready for phase-level completion/transition; no known blockers remain from this plan.

## Self-Check: PASSED

- All 5 files listed under "Files Created/Modified" plus this SUMMARY.md exist on disk.
- All 3 task commit hashes (`048d46c`, `b9cda85`, `e0f3837`) exist in `git log --oneline --all`.

---
*Phase: 04-hybrid-retrieval-and-fusion*
*Completed: 2026-08-11*
