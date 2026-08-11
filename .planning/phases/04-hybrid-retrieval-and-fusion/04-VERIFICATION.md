---
phase: 04-hybrid-retrieval-and-fusion
verified: 2026-08-11T12:12:40Z
status: gaps_found
score: 8/9 requirements satisfied; 1 benchmark-evidence gap
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "The retained strict/relaxed records are a valid comparable pair for the order-mode decision."
    status: failed
    reason: "The retained v4 strict and relaxed records carry different git_sha values (6adb045 versus 4662056) and materially different first-wave populations (80 versus 0 vector hits). The comparator does not include git_sha/runner implementation identity in its pins, so it returns ok despite that uncontrolled difference."
human_verification: []
---

# Phase 4: Hybrid Retrieval and Fusion Verification Report

**Phase goal:** 질문 하나가 5채널을 거쳐 **측정 가능하게** 옳은 근거 집합을 돌려준다

**Result:** `gaps_found` — the Phase 04 retrieval implementation and the graph evidence closure are substantively verified. RTV-04 cannot be closed because the retained strict/relaxed order pair is not proven comparable.

## Re-verification scope

This report re-checks the two failures in the previous report after `04-08`.
Summary claims were treated as non-evidence. I inspected the runner, loader, service, four v4 records, the policy documents, and commits `e876cd0..dda4e02`, then reran focused tests, fixture verification, both record comparators, the retrieval contract script, and `git diff --check`.

## Must-have evidence

| Truth | Result | Evidence |
| --- | --- | --- |
| Four first-wave channels execute through `RetrievalService`, are fused by Python RRF, and labels evaluate rather than construct returned ranking. | VERIFIED | `scripts/benchmark_retrieval.py:174-195` calls `RetrievalService.retrieve()` for each golden query, maps the returned UUID evidence, and only then calls `_evaluate_query`. `scripts/benchmark_retrieval.py:136-166` rejects fixture/no-envelope records. Focused tests: 19 passed. |
| Graph-on invokes bounded real graph expansion from fused wiki seeds and re-fuses; graph-off disables that wave. | VERIFIED | `apps/api/src/api/services/retrieval.py:123-137,230-262` selects first-wave wiki seeds, calls `expand_wiki_graph`, and re-fuses. v4 graph-on has 36 `graph.status=ok` envelopes and graph contribution 366; graph-off has 36 `disabled` envelopes and contribution 0. `compare-graph-records` returned `status: ok`, quality delta `+0.02777777777777779`. |
| Retained raw records have canonical policy content/hash, UUID/logical evidence mapping, and observed channel/underfill/contribution/latency fields. | VERIFIED | All four v4 records contain the full policy object whose stored SHA recomputes; all contain 36 query results, five channel envelopes, raw UUIDs, logical IDs, evaluations, and aggregate metrics. The record validator and focused tests passed. |
| Strict/relaxed records provide a valid comparison for choosing the order mode. | FAILED — BLOCKER | `phase-04-rerun-v4-strict-order.json` records `git_sha=6adb0453…`, 80 vector hits, and 0.02778 strict-pass; `phase-04-rerun-v4-relaxed-order.json` records `git_sha=46620562…`, zero vector hits, and 0 strict-pass. These artifacts were generated from different runner revisions. `compare_order_records()` (`scripts/benchmark_retrieval.py:198-201`) omits `git_sha` or a runner/schema implementation hash from `_pins`, so its `ok` result is not a valid comparability proof. |
| Strict order and graph-off defaults were not adopted or altered without the policy-change gate. | VERIFIED | `supabase/migrations/0011_retrieval.sql:76,147` remains `strict_order`; `packages/core/src/nexuswiki_core/retrieval_policy.py:38` remains `graph_enabled=False`. The policy log records no approval/change and accurately marks Plan-07 records superseded. |

## Requirement accounting

| Requirement | Status | Evidence |
| --- | --- | --- |
| RTV-01 | SATISFIED | Four concurrent channels, optional bounded graph second wave, and re-fusion are implemented and tested. |
| RTV-02 | SATISFIED | Rank-only RRF and immutable Python policy remain in use. |
| RTV-03 | SATISFIED | All three HNSW GUCs remain set and contract-tested. |
| RTV-04 | GAP | Full-path measurement machinery exists, but the retained strict/relaxed pair is invalid for a decision because the executions are not pinned to the same runner revision and comparator accepts that mismatch. |
| RTV-05 | SATISFIED | Channel contribution and underfill are first-class service and record metrics. |
| RTV-06 | SATISFIED | Pinned 36-query multilingual golden set validates. |
| RTV-07 | SATISFIED | Bounded default-off graph behavior and actual on/off full-path evidence are verified; no default change was made. |
| RTV-08 | SATISFIED | Retrieval contract verifies named HNSW indexes/GUCs. |
| RTV-09 | SATISFIED | Failure isolation and safe response metadata remain focused-test covered. |

## Automated verification performed

| Command | Result |
| --- | --- |
| `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -q packages/core/tests/test_retrieval_golden.py apps/api/tests/test_retrieval_service.py` | PASS — 19 passed |
| `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run python scripts/benchmark_retrieval.py --verify` | PASS — explicitly fixture-only, not accepted as operational evidence |
| `… benchmark_retrieval.py compare-order-records --left v4-strict --right v4-relaxed` | Returns `ok`, but independently found UNSOUND because `_pins` omits implementation identity. |
| `… benchmark_retrieval.py compare-graph-records --off v4-graph-off --on v4-graph-on` | PASS — `ok`; both artifacts share `git_sha=4662056…` and identical non-graph policy/pins. |
| `bash scripts/verify_retrieval_contract.sh` | PASS — retrieval contract output included `retrieval_contract: ok`. |
| `git diff --check HEAD~10..HEAD` | PASS |

## Exact remaining gap

1. Regenerate append-only strict and relaxed **full-path** records from one identical committed runner revision and one freshly loaded controlled corpus. Record a runner identity pin (at least `git_sha`, preferably a dedicated canonical runner/loader hash) and make the order comparator reject mismatched identity, order mode, graph state, and pins. Retain the current invalid v4 pair as superseded evidence; do not overwrite it.

The graph-on/off v4 pair need not be regenerated to close this specific gap: it shares the same recorded runner revision, exercises the real bounded RPC, and its comparator’s allowed policy delta is exactly `graph_enabled`.

---

_Verified: 2026-08-11T12:12:40Z_
_Verifier: gsd verifier_
