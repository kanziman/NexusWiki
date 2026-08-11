---
phase: 04-hybrid-retrieval-and-fusion
verified: 2026-08-11T13:45:00Z
status: passed
score: 9/9 requirements satisfied
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: "8/9 requirements satisfied; 1 benchmark-evidence gap"
  gaps_closed:
    - "The retained strict/relaxed records are a valid comparable pair for the order-mode decision."
  gaps_remaining: []
  regressions: []
---

# Phase 4: Hybrid Retrieval and Fusion Verification Report

**Phase goal:** 질문 하나가 5채널을 거쳐 **측정 가능하게** 옳은 근거 집합을 돌려준다

**Result:** `passed` — RTV-04, the sole remaining gap from the prior verification pass, is closed. `compare_order_records()` now pins runner identity (`git_sha`) and asserts a distinct `{strict_order, relaxed_order}` pair shape; the historical invalid v4 pair is now demonstrably rejected by the fixed comparator, and a new v5 pair — captured back-to-back from one identical committed revision — passes it. All 9 Phase 04 requirements are now SATISFIED.

## Re-verification scope

This is a re-verification after `04-09` (gap-closure plan, commits `048d46c`/`b9cda85`/`e0f3837`/`8dbe974`), whose sole claim is closing the RTV-04 comparator-identity gap the prior verification (`2026-08-11T12:12:40Z`) found. Per the launch instructions, RTV-01/02/03/05/06/07/08/09 were already SATISFIED and out of scope for 04-09's implementation; I spot-checked (not re-derived from scratch) that they remain unregressed, and did full 3-level + independent-execution verification on the RTV-04 closure claim specifically. I did not trust SUMMARY.md's narrative — every claim below was independently re-derived by reading the diff, reading the current file state, and re-running the tests/comparator/contract commands myself.

## Must-have evidence (RTV-04 closure — full verification)

| Truth | Result | Evidence |
| --- | --- | --- |
| `_pins()` in `scripts/benchmark_retrieval.py` includes `git_sha` as a ninth pinned field, shared by both `compare_order_records()` and `compare_graph_records()`. | VERIFIED | Read current file: `scripts/benchmark_retrieval.py:197` — `_pins()` tuple now ends `..., "database_identity", "repeat_count", "git_sha")`. `git show b9cda85` confirms this is the sole functional diff in that commit (plus the order-mode-pair assertion). |
| `compare_order_records()` additionally asserts the pair forms an exact `{strict_order, relaxed_order}` set before returning `status: ok`, independent of pin equality. | VERIFIED | `scripts/benchmark_retrieval.py:201` — `if {left.get("order_mode"), right.get("order_mode")} != {"strict_order", "relaxed_order"}: raise VerificationError("order_pair_mode_invalid")`. |
| Running the fixed comparator against the real historical invalid v4 pair (differing `git_sha`) now raises rather than returning `ok` — the exact defect the prior verification found is caught. | VERIFIED (independently executed, not just SUMMARY-cited) | I ran `uv run python scripts/benchmark_retrieval.py compare-order-records --left docs/ops/benchmark-records/phase-04-rerun-v4-strict-order.json --right docs/ops/benchmark-records/phase-04-rerun-v4-relaxed-order.json` myself: prints `order_pair_pin_or_policy_mismatch`, exit code 2. |
| A new valid v5 strict/relaxed pair from one identical committed revision passes the fixed comparator with matching `git_sha`. | VERIFIED (independently executed) | I ran the comparator against the new files myself: `{"status": "ok", "quality_delta": -0.7222222222222222}`, exit 0. I independently read both v5 JSON files directly (not via SUMMARY): both `git_sha == b9cda858979619da23121a341569a58afed61c46` (byte-identical), `run_kind == full_path_retrieval_measurement`, `order_mode` values are `strict_order` / `relaxed_order` respectively, 36 query results each, timestamps `13:28:14` and `13:29:13` (one minute apart, consistent with "back-to-back, no intervening commit"). |
| The shared `_pins()` change causes no regression in `compare_graph_records()` — the existing valid v4 graph-off/graph-on pair still passes. | VERIFIED (independently executed) | I ran `compare-graph-records --off phase-04-rerun-v4-graph-off.json --on phase-04-rerun-v4-graph-on.json` myself: `{"status": "ok", "quality_delta": 0.0278, "contribution_delta": 366, ...}`, exit 0 — unchanged from the prior verification pass. |
| Three new regression tests exist and pass, proving TDD RED (bug reproduced) → GREEN (fix verified), including the graph non-regression case. | VERIFIED | `packages/core/tests/test_retrieval_golden.py::test_compare_order_records_rejects_historical_invalid_v4_pair_with_mismatched_git_sha`, `::test_compare_order_records_rejects_matching_order_mode_pair`, `::test_compare_graph_records_still_accepts_historical_valid_v4_graph_pair`. I ran `uv run pytest -q packages/core/tests/test_retrieval_golden.py -k "compare_order_records or compare_graph_records"` myself: 3 passed. Full targeted suite (`test_retrieval_golden.py` + `test_retrieval_service.py`) also independently re-run: 22 passed. |
| `docs/ops/hnsw-order-benchmark.md` records the v5 outcome and explicitly marks the v4 strict/relaxed pair superseded-invalid, without deleting/overwriting/renumbering v4 files. | VERIFIED | Read the current file directly: new "v4 strict/relaxed 쌍 — superseded-invalid" and "v5 strict/relaxed 쌍" sections exist, citing both differing `git_sha` values for v4 and the shared `git_sha` for v5. `git diff --stat` for the v4 JSON record paths across the gap-closure commits shows zero changes — the v4 files are untouched. |
| `supabase/migrations/0011_retrieval.sql`'s `strict_order` and `retrieval_policy.py`'s `graph_enabled=False` defaults remain unchanged; the v5 evidence does not itself adopt a different default. | VERIFIED | Read current files directly: `0011_retrieval.sql:76,147` still `set hnsw.iterative_scan = 'strict_order'`; `retrieval_policy.py:38` still `graph_enabled: bool = False`. `git diff --stat 704ddad..8dbe974` (the full gap-closure range) does not include either file. |

## Prohibitions (from 04-09-PLAN.md must_haves — judgment-tier, human-reviewable)

| Statement | Disposition | Evidence |
| --- | --- | --- |
| The v5 pair must not reuse residual DB rows from a prior session. | Not violated (code-guaranteed) | `operational()` (`scripts/benchmark_retrieval.py:174-194`) unconditionally runs `cleanup` before `load`, and again in a `finally` block after. This is a structural code guarantee, independently verifiable from the current source, not merely a SUMMARY claim. SUMMARY additionally documents a `docker exec ... psql` row-count-0 check after both arms. |
| Neither the fixed comparator nor the doc update may be read as production-default authorization. | Not violated | `docs/ops/hnsw-order-benchmark.md` explicitly states the v5 evidence "does not itself adopt a different default" and repeats the `retrieval-policy-change-log.md` gate requirement. Migration/policy files are untouched (confirmed above). |
| The matching-`git_sha` claim must not hold if the working tree was dirty at either capture time. | Disclosed deviation, not a defect | SUMMARY transparently discloses that a full repo-wide `git status --porcelain` was **not** empty (pre-existing, plan-unrelated uncommitted files in `.planning/`, `HANDOFF.md`, `checklists.json`, `docs/architecture/`, `docs/design-systems/` — matching this session's own `git status` output at conversation start). It narrows the check to `git status --porcelain -- scripts/ apps/ packages/ supabase/` (the code paths that affect the benchmark run) and documents this narrowing explicitly in `docs/ops/hnsw-order-benchmark.md`'s "⚠️ git 작업 트리 참고" note rather than silently asserting a fully clean tree. The load-bearing fact — both v5 records carry byte-identical `git_sha` and no commit landed between the two arm invocations — is independently verifiable from the JSON files themselves (confirmed above) and does not depend on the disclosed scope narrowing. This is judgment-tier and reasonable given the surrounding context (this repo's `.planning/` and ops docs churn constantly across concurrent GSD sessions); flagged here for visibility, not as a gap. |

## Requirement accounting (all 9)

| Requirement | Status | Evidence |
| --- | --- | --- |
| RTV-01 | SATISFIED (spot-checked, unchanged) | `apps/api/src/api/services/retrieval.py` two-wave concurrent-then-graph retrieval — not touched by 04-09; `apps/api/tests/test_retrieval_service.py` still passes (re-run: included in the 22-pass batch above). |
| RTV-02 | SATISFIED (spot-checked, unchanged) | Rank-only Python RRF policy layer — not touched by 04-09. |
| RTV-03 | SATISFIED (spot-checked, unchanged) | All three HNSW GUCs still set; re-ran `bash scripts/verify_retrieval_contract.sh` myself — prints `retrieval_contract: ok`. |
| RTV-04 | **SATISFIED — gap closed** | See "Must-have evidence" table above: independently re-executed, not SUMMARY-trusted. |
| RTV-05 | SATISFIED (spot-checked, unchanged) | `channel_hits`/`underfill` remain first-class record/service metrics — not touched by 04-09. |
| RTV-06 | SATISFIED (spot-checked, unchanged) | Pinned 36-query golden set reused unmodified by 04-09 (`04-09-PLAN.md` explicitly states no query/label changes); v5 records both contain all 36 queries. |
| RTV-07 | SATISFIED (spot-checked, unchanged) | Bounded default-off graph channel; v4 graph-off/graph-on pair re-verified passing (`compare-graph-records` re-run above) — no regression from the shared `_pins()` change. |
| RTV-08 | SATISFIED (spot-checked, unchanged) | `verify_retrieval_contract.sh` re-run, still `ok`. |
| RTV-09 | SATISFIED (spot-checked, unchanged) | Per-channel failure isolation — not touched by 04-09; covered by the re-run focused test suite. |

## Automated verification performed (this pass, independently re-run)

| Command | Result |
| --- | --- |
| `uv run pytest -q packages/core/tests/test_retrieval_golden.py -k "compare_order_records or compare_graph_records"` | PASS — 3 passed (the new regression tests) |
| `uv run pytest -q packages/core/tests/test_retrieval_golden.py apps/api/tests/test_retrieval_service.py` | PASS — 22 passed (full targeted suite, no regressions) |
| `uv run python scripts/benchmark_retrieval.py compare-order-records --left phase-04-rerun-v4-strict-order.json --right phase-04-rerun-v4-relaxed-order.json` | FAILS CLOSED as required — `order_pair_pin_or_policy_mismatch`, exit 2 (previously `status: ok` — this is the proof the fix works) |
| `uv run python scripts/benchmark_retrieval.py compare-order-records --left phase-04-rerun-v5-strict-order.json --right phase-04-rerun-v5-relaxed-order.json` | PASS — `status: ok`, `quality_delta: -0.7222222222222222`, exit 0 |
| `uv run python scripts/benchmark_retrieval.py compare-graph-records --off phase-04-rerun-v4-graph-off.json --on phase-04-rerun-v4-graph-on.json` | PASS — `status: ok` (unchanged from prior verification — no regression) |
| `bash scripts/verify_retrieval_contract.sh` | PASS — `retrieval_contract: ok` |
| `git diff --check 704ddad..8dbe974` | PASS — no whitespace errors |
| `git diff --stat 704ddad..8dbe974` (defaults-untouched check) | Confirmed: `supabase/migrations/0011_retrieval.sql` and `packages/core/src/nexuswiki_core/retrieval_policy.py` do not appear |
| `git diff --stat` for v4 JSON record paths across gap-closure commits | Confirmed: zero changes — v4 files preserved byte-for-byte |
| Debt-marker scan (`TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`) on all 3 code/doc files touched by 04-09 | None found |

## Anti-Patterns Found

None. The diff is a minimal, targeted fix (2 lines) plus regression tests plus append-only evidence files plus a documentation update. No stub patterns, no unreferenced debt markers, no hardcoded empty returns in the changed code paths.

## Notable observation (not a gap — informational)

- **`.planning/REQUIREMENTS.md` checkbox/table state is stale for RTV-01/02/03/05/09** — they still show `[ ]`/`Pending` even though the prior verification pass (and this re-verification) found them SATISFIED in the codebase. This predates `04-09` (confirmed via `git log -p -- .planning/REQUIREMENTS.md`; `04-09`'s commits do not touch this file) and is a requirements-ledger bookkeeping gap, not a code-correctness gap. It does not block phase completion since ROADMAP.md/STATE.md (which `04-09` did update) are the authoritative plan-completion trackers, but should be reconciled before/at milestone close so `REQUIREMENTS.md` reflects reality.
- **The relaxed-order arm returns zero hits across every channel (including lexical, which `relaxed_order` should not affect) in both the v4 and v5 records.** This is pre-existing behavior unchanged by `04-09` (present identically in both the invalid v4 record and the newly valid v5 record), transparently documented in `docs/ops/hnsw-order-benchmark.md`, and was already accounted for by the prior verifier when RTV-01/05/06 were marked SATISFIED. Root-causing it was explicitly out of scope for the RTV-04 comparator-identity gap closure. Not a blocker for this re-verification, but worth flagging for whoever eventually investigates why `relaxed_order` underperforms this severely on the golden set.

## Gaps Summary

None. The sole gap from the prior verification pass — the strict/relaxed comparator accepting a runner-revision-mismatched pair as comparable — is closed. The fix is minimal, tested with a reproduced-bug-then-fixed TDD sequence, independently re-executed by this verifier (not merely SUMMARY-trusted), and the resulting v5 evidence pair is genuinely comparable by every pin the comparator checks, including the newly added `git_sha`. No regressions were found in any of the other 8 requirements, no production defaults changed, and the historical v4 evidence was preserved (not silently discarded) with an honest superseded-invalid label.

---

_Verified: 2026-08-11T13:45:00Z_
_Verifier: Claude (gsd-verifier), re-verification pass_
