---
phase: 05-citation-integrity-and-answer-apis
plan: 02
subsystem: database
tags: [postgresql, pgvector, hnsw, rls, security-invoker, plpgsql, prompt-templates, supabase]

# Dependency graph
requires:
  - phase: 04-hybrid-retrieval-and-fusion
    provides: "expand_wiki_graph / search_wiki_embeddings HNSW GUC + recursive-CTE bound patterns (0011_retrieval.sql) that this plan's RPCs mirror"
provides:
  - "public.wiki_graph_neighborhood(uuid, uuid, int, int) — bounded, SECURITY INVOKER graph-read RPC returning edge triples for API-04's dashboard graph read"
  - "public.find_similar_wiki_pages(uuid, uuid, double precision, int) — bounded, service_role-only cosine-similarity candidate RPC for QC-01's conflict-detection job"
  - "public.stamp_wiki_verification() BEFORE UPDATE trigger on wiki_pages — DB-asserted verified_by/verified_at on verification_status transitions (QC-02)"
  - "target_type='ask' prompt_templates corrected to instruct the D-02 short-alias citation format ([[wiki:wN]]/[[src:sN]]) instead of the pre-D-02 real-slug/chunk-UUID wording, plus an answer-language-follows-question instruction (API-03)"
affects: [05-03-PLAN, 05-05-PLAN, 05-06-PLAN]

# Actuals (#2632)
actuals:
  tokens: 3050
  tasks: 2
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pgvector session warmup (`select '[1,2,3]'::extensions.vector`) is required at the top of ANY migration file that sets `hnsw.*` GUCs inside a function definition, if that migration might ever be pushed alone via `supabase db push` (a fresh session) — `supabase db reset` hides this because earlier migrations in the same reset session already warmed the extension"
    - "Recursive CTEs: ORDER BY/LIMIT cannot be attached directly to a UNION ALL arm in Postgres — must be wrapped in a subquery, mirroring `expand_wiki_graph`'s lateral-subquery-per-hop shape"
    - "RETURNS TABLE OUT-parameter names that collide with a CTE's own column names inside the function body become ambiguous in the final SELECT — must be table-qualified (`walk.from_wiki_id`, not bare `from_wiki_id`)"

key-files:
  created:
    - supabase/migrations/0012_ask_citation_and_graph.sql
  modified: []

key-decisions:
  - "D-10 applied via append-only UPDATE (not a literal find/replace) on the four ask templates' system_prompt — avoids brittle matching across four differently-worded passages; the appended instruction is the model's most recent instruction and functionally overrides the stale 0006 wording"
  - "D-07.1/D-11: wiki_graph_neighborhood is a new, independently-versioned function (not a reuse of expand_wiki_graph) with wider bounds (fanout 1..20, total 1..200) than the retrieval-time expansion (1..5/1..50), matching the reasoning that a dashboard browse is a single explicit user action, not a per-request retrieval-cost multiplier"
  - "D-05: find_similar_wiki_pages is SECURITY INVOKER + service_role-only EXECUTE (never authenticated) since it is called exclusively from the worker's conflict-detection job, never a user request path"
  - "D-06: stamp_wiki_verification only fires on verification_status transitions (`new is distinct from old`), leaving compile.py's recompile upsert path (which omits verification_status from its payload, T-03-28) unaffected — verified empirically, not just by code reading"

patterns-established:
  - "Migration files that define hnsw.*-setting functions must include the pgvector warmup query even if a prior migration in the same repo already has one — session-scoping means each migration file executed alone (db push) needs its own warmup"

requirements-completed: [API-04, QC-01, QC-02]

coverage:
  - id: D1
    description: "target_type='ask' prompt_templates instruct the D-02 short-alias citation format ([[wiki:wN]]/[[src:sN]]) plus answer-language-follows-question, applied to all 4 global default templates"
    requirement: "API-03"
    verification:
      - kind: other
        ref: "docker exec supabase_db_NexusWiki psql -c \"select system_prompt like '%[[wiki:wN]]%' ... from prompt_templates where target_type='ask' and workspace_id is null\" -> t"
        status: pass
    human_judgment: false
  - id: D2
    description: "public.wiki_graph_neighborhood(uuid, uuid, int, int) — bounded, SECURITY INVOKER edge-triple graph read; bound violations raise 22023"
    requirement: "API-04"
    verification:
      - kind: other
        ref: "docker exec psql functional test: seeded 2 wiki_pages + 1 wiki_links row, RPC returned the expected (from,to,depth) edge; fanout=0 call raised 'wiki_graph_neighborhood fan-out must be 1..20'"
        status: pass
    human_judgment: false
  - id: D3
    description: "public.find_similar_wiki_pages(uuid, uuid, double precision, int) — bounded, service_role-only cosine-candidate RPC with the search_wiki_embeddings HNSW GUC triad"
    requirement: "QC-01"
    verification:
      - kind: other
        ref: "docker exec psql: function exists (security_type=INVOKER), callable and returns 0 rows against an empty-embedding fixture with no error"
        status: pass
    human_judgment: false
  - id: D4
    description: "stamp_wiki_verification BEFORE UPDATE trigger stamps verified_by/verified_at from auth.uid()/now() on verification_status transitions only, never on unrelated column updates"
    requirement: "QC-02"
    verification:
      - kind: other
        ref: "docker exec psql functional test: UPDATE ... SET verification_status='verified' set verified_at (not null); a subsequent UPDATE ... SET title=... left verified_at unchanged (still set, not re-stamped/nulled)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Migration 0012 applied cleanly to both the local stack (supabase db reset, 0001-0012 in order) and Supabase Cloud (supabase db push --yes)"
    verification:
      - kind: other
        ref: "supabase migration list -> local/remote both report 0012 after push; local db reset exited 0"
        status: pass
    human_judgment: false

# Metrics
duration: ~25min
completed: 2026-08-11
status: complete
---

# Phase 5 Plan 2: Ask Citation Fix, Bounded Graph/Conflict RPCs, Verification Trigger Summary

**Migration `0012_ask_citation_and_graph.sql` — corrected ask-template citation wording to D-02's short-alias scheme, added a bounded SECURITY INVOKER graph-read RPC (`wiki_graph_neighborhood`), a bounded service_role-only conflict-candidate RPC (`find_similar_wiki_pages`), and a DB-enforced verification-transition audit trigger (`stamp_wiki_verification`) — applied to both local stack and Supabase Cloud.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-08-11T23:15:01Z (immediately following 05-01)
- **Completed:** 2026-08-11T23:22:56Z (measurement window; actual wall-clock work included multiple local `supabase db reset` cycles and one cloud `supabase db push`)
- **Tasks:** 2/2
- **Files modified:** 1

## Accomplishments
- Fixed the D-02/D-10 prompt-template conflict: all four seeded `target_type='ask'` templates now instruct the model to copy the server-issued short alias (`[[wiki:wN]]`/`[[src:sN]]`), not the real slug/chunk UUID the 0006 seed originally specified — closes a design conflict that would have silently defeated CITE-01's whole anchor-alias scheme.
- Added `public.wiki_graph_neighborhood` — a new, independently-versioned, SECURITY INVOKER, bounded graph-read RPC returning edge triples for API-04's dashboard graph consumer, distinct from and non-interfering with Phase 4's retrieval-fusion-owned `expand_wiki_graph`.
- Added `public.find_similar_wiki_pages` — a bounded, service_role-only, SECURITY INVOKER cosine-candidate RPC for QC-01's future conflict-detection worker job, reusing `search_wiki_embeddings`'s exact HNSW GUC triad.
- Added the `wiki_pages_stamp_verification` trigger (`stamp_wiki_verification()`) so `verified_by`/`verified_at` are always database-asserted from `auth.uid()`/`now()` on `verification_status` transitions, never trusted from client-supplied request values — verified empirically that it does not fire on the worker's recompile upsert path.
- Applied the migration to both the local Supabase stack (`supabase db reset`, 0001-0012 clean) and Supabase Cloud (`supabase db push --yes`); `supabase migration list` confirms local and remote both report `0012`.

## Task Commits

Each task was committed atomically, with two additional Rule-1 auto-fix commits produced by Task 2's own verification work surfacing bugs in Task 1's SQL:

1. **Task 1: Write migration 0012** - `5b0b74e` (feat)
2. **Rule-1 fix (found during Task 2's local `supabase db reset`):** recursive-CTE syntax error (`ORDER BY`/`LIMIT` directly on a `UNION ALL` arm) and an ambiguous `OUT`-parameter/CTE-column-name collision in `wiki_graph_neighborhood` - `5f27b7d` (fix)
3. **Rule-1 fix (found during Task 2's cloud `supabase db push`):** missing pgvector session-warmup query — `find_similar_wiki_pages`'s `hnsw.*` GUC assignments failed with `42501 permission denied to set parameter` in a fresh cloud session that had never loaded the vector extension - `de8a963` (fix)
4. **Task 2: [BLOCKING] Apply migration 0012 to local stack and Cloud** - verified via the two fix commits above plus the final clean `db reset` + `db push --yes` run (no separate commit — this task's "work" was iterative verification that produced the fix commits)

**Plan metadata:** (this commit, following SUMMARY)

## Files Created/Modified
- `supabase/migrations/0012_ask_citation_and_graph.sql` - Ask-template citation/language instruction fix (D-10/API-03), `wiki_graph_neighborhood` RPC (API-04/D-07.1/D-11), `find_similar_wiki_pages` RPC (QC-01/D-05), `stamp_wiki_verification()` trigger (QC-02/D-06), pgvector session warmup

## Decisions Made
- Append-only UPDATE for the ask-template citation fix rather than a literal substring replace, since the four templates phrase the old instruction differently — the appended text is the model's most recent instruction, functionally superseding the stale wording without a fragile find/replace across four passages.
- `wiki_graph_neighborhood` deliberately duplicates rather than reuses `expand_wiki_graph`'s recursive-CTE shape, per 05-CONTEXT.md's explicit instruction that Phase 5 must not reach into Phase 4's retrieval-fusion-owned function — the two RPCs are allowed to diverge (edge triples vs. node-only rows, wider bounds) because they serve different consumers.
- `find_similar_wiki_pages` grants EXECUTE to `service_role` only, never `authenticated` — this RPC is a worker-internal conflict-detection primitive, not a user-facing read.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Recursive CTE syntax error in `wiki_graph_neighborhood`**
- **Found during:** Task 2 (`supabase db reset` against the local stack)
- **Issue:** The first arm of the `WITH RECURSIVE walk AS (...)` had `ORDER BY l.to_wiki_id LIMIT p_fanout` attached directly before `UNION ALL` — Postgres rejects `ORDER BY`/`LIMIT` on an individual `UNION` arm unless wrapped in a subquery, raising `42601 syntax error at or near "union"`.
- **Fix:** Wrapped the first-hop query in a plain subquery (`first_hop`), matching `expand_wiki_graph`'s lateral-subquery-per-hop pattern for the recursive arm.
- **Files modified:** `supabase/migrations/0012_ask_citation_and_graph.sql`
- **Verification:** `supabase db reset` completed with no error; functional psql test confirmed the RPC returns the expected edge triple.
- **Committed in:** `5f27b7d`

**2. [Rule 1 - Bug] Ambiguous column reference in `wiki_graph_neighborhood`'s final SELECT**
- **Found during:** Same `db reset` cycle, next error surfaced after fixing #1
- **Issue:** `RETURNS TABLE (from_wiki_id uuid, to_wiki_id uuid, depth int)` creates PL/pgSQL OUT-parameter variables with those exact names, colliding with the `walk` CTE's own columns of the same name in the final bare `select from_wiki_id, to_wiki_id, depth from walk` — Postgres raised `column reference "from_wiki_id" is ambiguous`.
- **Fix:** Table-qualified the final SELECT (`select walk.from_wiki_id, walk.to_wiki_id, walk.depth from walk`).
- **Files modified:** `supabase/migrations/0012_ask_citation_and_graph.sql`
- **Verification:** Functional psql test (seeded workspace/wiki_pages/wiki_links, called the RPC, got back the expected row); bound-violation test also confirmed the `raise exception` path still fires correctly.
- **Committed in:** `5f27b7d`

**3. [Rule 1 - Bug] Missing pgvector session warmup causes cloud-only `42501` failure**
- **Found during:** Task 2 (`supabase db push --yes` against Supabase Cloud)
- **Issue:** `find_similar_wiki_pages`'s `SET hnsw.iterative_scan = 'strict_order'` (and the other two HNSW GUCs) failed with `permission denied to set parameter "hnsw.iterative_scan"` (SQLSTATE 42501) when pushed to Cloud. `0011_retrieval.sql` avoids this by opening with `select '[1,2,3]'::extensions.vector as pgvector_warmup;` before any function that sets an `hnsw.*` GUC, loading the extension into that session first. `0012` omitted this line. Locally the bug was invisible because `db reset` runs 0001-0012 in one continuous session, and 0011's own functions (defined earlier in that same session) already warmed the extension by the time 0012 ran — but `db push` executes each pending migration file as its own fresh session, so 0012 alone had never loaded `extensions.vector`.
- **Fix:** Added the identical `select '[1,2,3]'::extensions.vector as pgvector_warmup;` line immediately after `begin;` in 0012.
- **Files modified:** `supabase/migrations/0012_ask_citation_and_graph.sql`
- **Verification:** Local `db reset` re-confirmed clean; `supabase db push --yes` succeeded; `supabase migration list` shows local and remote both at `0012`.
- **Committed in:** `de8a963`

---

**Total deviations:** 3 auto-fixed (all Rule 1 — SQL bugs caught by the plan's own mandatory local-reset-then-cloud-push verification sequence, exactly the failure mode that sequence exists to catch before any downstream plan depends on this schema).
**Impact on plan:** All three fixes were necessary for the migration to be applicable at all (not stylistic). No scope creep — the migration's four sections match the plan's Task 1 action exactly; only bugs within those sections were corrected.

## Issues Encountered
None beyond the three Rule-1 SQL bugs documented above, all caught and fixed within Task 2's own verification loop before any commit was left in a broken state.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `public.wiki_graph_neighborhood`, `public.find_similar_wiki_pages`, and the `stamp_wiki_verification` trigger are live on both local and Cloud — 05-03/05-05/05-06 can call/rely on them without touching `supabase/migrations/` again, per this plan's own success criteria.
- The corrected ask-template citation instructions are live in `prompt_templates` — any plan building the Ask endpoint (05-01, already complete; downstream ask-consuming plans) will see the D-02-aligned instruction text by default.
- No blockers identified for downstream plans in this wave.

---
*Phase: 05-citation-integrity-and-answer-apis*
*Completed: 2026-08-11*

## Self-Check: PASSED

- FOUND: `supabase/migrations/0012_ask_citation_and_graph.sql`
- FOUND: `.planning/phases/05-citation-integrity-and-answer-apis/05-02-SUMMARY.md`
- FOUND commit `5b0b74e` (feat: migration 0012)
- FOUND commit `5f27b7d` (fix: recursive CTE syntax errors)
- FOUND commit `de8a963` (fix: pgvector warmup)
