# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Living Wiki MVP

**Shipped:** 2026-08-13
**Phases:** 7 | **Plans:** 55 | **Timeline:** 2026-08-01 → 2026-08-13 (12 days, 393 commits)

### What Was Built
- Irreversible decisions locked first (Singapore region both sides, `sb_publishable_`/`sb_secret_` key scheme, uv monorepo) before any application code, so nothing downstream had to be rewritten around them
- Tenant isolation enforced as capability absence (not code convention) plus a DB-transport spike that picked `SECURITY INVOKER` RPC over asyncpg from measured evidence, not documentation
- Full ingest → compile → embed pipeline with a job chain (`parse → compile → link_sync → embed`), enqueue-time cost caps, and structured-output retry backstop
- 5-channel hybrid retrieval (2-wave RRF fusion) with a versioned Python policy layer and a golden-query-set benchmarking harness
- Dual-citation Ask API — server-issued short anchors, `double_citation` = parsed ∩ issued (never raw retrieval), SSE streaming
- A complete browser-only dashboard: auth, workspace switching/invite, source dropzone with real job-stage progress, Ask UI, read-only wiki viewer, Cytoscape knowledge canvas
- Integration/ops baseline closing every prior phase's deferred verification debt: real E2E pipeline test, actual shrinking-reprocess idempotency, a 9-table full-path tenant isolation matrix, a 25k+25k-row HNSW baseline that finally made `strict_order` vs `relaxed_order` a real comparison, and a per-workspace cost/pipeline observability panel

### What Worked
- **Tracer-first plan ordering.** Nearly every phase led with one production-quality end-to-end slice before expanding (`01-01`, `03-04`, `06-01`, `07-01`) — later plans built on a proven path instead of untested horizontal layers.
- **Spike-before-commit on genuinely ambiguous calls.** DB transport, region RTT, and (in Phase 7) HNSW plan-selection scale were all resolved by actual measurement, not by picking the more-cited option. Every decision in PROJECT.md's Key Decisions table that got a real spike converted cleanly to ✓ Good at milestone close.
- **Capability-absence security model paid for itself early.** The Phase 2 DB-transport spike incidentally discovered that `authenticated`/`service_role` had zero DML grants on all 9 tables — the `0004` RLS policies were completely inert — and this was caught before a single router existed, not after ship.
- **Explicit deferred-work tracking (WINDOWS.md) closed the loop.** Both WINDOWS #6 (shrinking-reprocess deletion path never actually observed) and #10 (HNSW order comparison never run at meaningful scale) were flagged in Phase 3/4, explicitly assigned to Phase 7, and actually closed there — nothing got silently forgotten.
- **Local-stack-first verification with targeted cloud spot-checks.** Most correctness work ran against the local Supabase stack (free, fast, repeatable); cloud was reserved for things that are genuinely environment-sensitive (RTT, first `db push`, pg_default_acl differences) — kept cost and iteration time down without sacrificing real evidence.

### What Was Inefficient
- **SDD (`/gsd-spec-phase`) was a locked Key Decision but only actually used for Phase 1-2.** Phases 3-7 went straight from discuss-phase to plan-phase, with the spec-less probe fallback filling in edge/prohibition coverage instead. The decision was never revisited or explicitly walked back — it just quietly stopped being followed.
- **PROJECT.md fell three phases behind.** It was last updated after Phase 4 and not touched again until this milestone close, even though Phase 5/6/7 each produced real decisions worth logging incrementally. The full-review-only-at-milestone-boundary safety net caught it, but per-phase evolution would have kept it current.
- **`audit-open`'s debug-session scanner has a naming false positive** against `.planning/debug/knowledge-base.md` (the persistent resolved-sessions index, not a live session) — cost a manual investigation at milestone close to confirm it wasn't real open work.

### Patterns Established
- **Tracer-first decomposition** — one full-fidelity end-to-end slice leads every phase; expansion tasks come after it's proven, not before.
- **Silent-failure-first assertion discipline** — tests assert row-count deltas and the `0 rows` (USING) vs `42501` (WITH CHECK) distinction explicitly; "no exception was raised" is never treated as proof.
- **Worker-owns-secret, API-proxies-via-internal-listener** — used for query embedding (Phase 4) and reused verbatim for Ask LLM streaming (Phase 5); a boundary pattern that generalized cleanly on its second use.
- **Broken-windows ledger (`WINDOWS.md`)** — cross-phase defects get an id, an owning future phase, and a `fixed`/`waived` resolution instead of living only in a session's memory.

### Key Lessons
1. A decision left as "Pending" in the Key Decisions table without a scheduled measurement stays unresolved indefinitely (LLM-cost linearity, Cytoscape canvas value both remained ⚠️ Revisit through ship) — spikes need an owner and a phase, not just an intention.
2. Capability-absence beats code-review discipline for security invariants: the RLS-inert bug at Phase 2 was found by a spike that happened to exercise the real path, not by anyone reviewing the migration for grants — structural checks (CI grep, ruff banned-api) generalize better than review vigilance.
3. A written deferred-items ledger with an explicit owning phase is what makes "we'll get to it later" actually true. Both major carried-forward gaps in this milestone (WINDOWS #6, #10) were closed exactly where they were promised, twelve days later.
4. Full-document reviews should not be milestone-boundary-only for fast-moving projects — three phases' worth of PROJECT.md drift accumulated silently between Phase 4 and this close.

### Cost Observations
- Model mix and per-session cost were not tracked as structured data during v1.0 — not available to report here without fabricating numbers.
- Sessions: multiple across the 12-day window, including at least one autonomous planning+execution pass for Phase 7 that completed outside interactive discussion (discovered mid-session via `/catchup`, not initiated by the interactive session that had been discussing Phase 7's CONTEXT.md).
- Notable: the Phase 7 F-01/F-02 gap-closure cycle (isolation matrix completion + planning-state sync) ran and resolved within the same session that produced the initial Phase 7 verification — no multi-day gap-closure loop was needed.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | multiple (untracked count) | 7 | First milestone — established tracer-first, capability-absence security, and the WINDOWS.md deferred-defect ledger as house patterns |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 435+ (Python, `uv run pytest -rs` collected 435; dashboard adds 82 Vitest) | Not measured as a percentage — gated on named acceptance criteria per task instead (`checklists.json` convention, carried into GSD requirements) | Postgres-only job queue (no broker), app-layer bigram tokenizer (no pg_bigm/pgroonga), `wiki_links` + recursive CTE (no graph DB) |

### Top Lessons (Verified Across Milestones)

1. Spike-and-measure decisions converge to ✓ Good; guessed decisions stay ⚠️ Revisit — one milestone of evidence so far, worth re-checking at v1.1 close.
2. A deferred-items ledger with an owning phase is what makes deferred work actually get done — one milestone of evidence (WINDOWS #6, #10 both closed on schedule).
