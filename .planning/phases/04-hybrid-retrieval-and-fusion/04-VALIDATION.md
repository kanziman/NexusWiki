---
phase: 4
slug: hybrid-retrieval-and-fusion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-11
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 with pytest-asyncio 1.4.0 |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest -q packages/core/tests apps/api/tests` |
| **Full suite command** | `uv run pytest -rs` |
| **Estimated runtime** | ~60 seconds locally; Supabase SQL contracts run separately |

## Sampling Rate

- **After every task commit:** Run the focused tests named by that task, then `uv run pytest -q packages/core/tests apps/api/tests` when shared contracts change.
- **After every plan wave:** Run `uv run pytest -rs` plus the applicable retrieval SQL contract runner.
- **Before `/gsd-verify-work`:** Full Python suite, retrieval SQL contracts, and the reproducible benchmark record must be green.
- **Max feedback latency:** 60 seconds for pure-Python/API tests; 10 minutes for local Supabase plan contracts.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-* | tracer | 1 | RTV-02, RTV-09 | T-04-01 | API cannot access the embedding-provider credential; a bounded injected worker-owned embedder is used | unit/API | `uv run pytest -q packages/core/tests/test_rrf.py packages/core/tests/test_retrieval_policy.py apps/api/tests/test_retrieval_service.py` | ❌ W0 | ⬜ pending |
| 04-02-* | database | 1 | RTV-03, RTV-07, RTV-08 | T-04-02 | Retrieval RPCs are SECURITY INVOKER/RLS-safe, bounded, ACL-restricted, and retain all HNSW GUCs | SQL/integration | `scripts/verify_retrieval_contract.sh` | ❌ W0 | ⬜ pending |
| 04-03-* | orchestration | 2 | RTV-01, RTV-05, RTV-09 | T-04-03 | Four first-wave channels isolate failures; graph remains default-off and bounded; meta contains safe diagnostics | API/integration | `uv run pytest -q apps/api/tests/test_retrieval_service.py apps/api/tests/test_hybrid_search_integration.py` | ❌ W0 | ⬜ pending |
| 04-04-* | measurement | 2 | RTV-04, RTV-06, RTV-07 | T-04-04 | Golden/corpus/policy hashes are pinned and graph/order tuning is adopted only with comparable recorded evidence | unit/benchmark | `uv run pytest -q packages/core/tests/test_retrieval_golden.py && uv run python scripts/benchmark_retrieval.py --verify` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

## Wave 0 Requirements

- [ ] `packages/core/tests/test_rrf.py` and `packages/core/tests/test_retrieval_policy.py` — rank-only fusion, deterministic dedupe/tie-break, policy version, graph feature flag.
- [ ] `apps/api/tests/test_retrieval_service.py` — concurrency, shared query embedding, cancellation, degraded results, safe metadata.
- [ ] `apps/api/tests/test_hybrid_search_integration.py` — two-tenant/RLS and RPC contracts using local Supabase.
- [ ] `supabase/tests/0011_retrieval_contract.sql` and `scripts/verify_retrieval_contract.sh` — ACL/GUC/index/EXPLAIN behavior with an adequately selective corpus.
- [ ] `packages/core/tests/fixtures/retrieval/golden_queries.v1.json` plus schema/metric tests — 30–50 labelled Korean, English, and mixed queries.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Select the production default between `strict_order` and `relaxed_order` | RTV-04 | Performance depends on real database/hardware/corpus conditions | Run the benchmark with matching pinned corpus/golden/policy/model versions; record both quality and latency in `docs/ops/hnsw-order-benchmark.md`, including the decision rationale. |
| Consider enabling graph by default | RTV-07 | Product-value choice follows evidence rather than a fixed code assertion | Compare graph-off vs. graph-on benchmark output on the pinned golden set; leave the flag off unless the recorded result justifies promotion. |

## Validation Sign-Off

- [ ] All tasks have `<automated>` verification or Wave 0 dependencies.
- [ ] Sampling continuity: no three consecutive tasks without automated verification.
- [ ] Wave 0 covers all missing test references.
- [ ] No watch-mode flags.
- [ ] Feedback latency is below the stated limits.
- [ ] `nyquist_compliant: true` set in frontmatter after execution evidence is captured.

**Approval:** pending
