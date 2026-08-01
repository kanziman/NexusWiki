<!-- refreshed: 2026-08-01 -->
# Codebase Concerns

**Analysis Date:** 2026-08-01

**Scope note:** The repository currently contains no application code. Everything shipped lives in
`supabase/migrations/` (0001–0004, 0006), `supabase/config.toml`, `checklists.json`, and `HANDOFF.md`.
All concerns below are therefore data-layer, security-policy, or process concerns. Line references
are to the files as they exist at this date.

---

## Tech Debt

**Migration numbering gap — `0005` is reserved but unwritten:**
- Issue: `supabase/migrations/` jumps `0004_rls_policies.sql` → `0006_seed_prompts.sql`. Slot `0005`
  is held for `P1-STO-01` (Storage buckets). Locally this is harmless because the workflow is always
  `supabase db reset`, but the Supabase CLI records applied versions on the remote and refuses / warns
  on out-of-order migrations. Once a cloud project is pushed with `0006` applied, adding `0005` after
  the fact requires `--include-all` or a repair.
- Files: `supabase/migrations/` (directory), `HANDOFF.md:245-247`
- Impact: Cloud push blocked or requires migration repair; risk of Storage policies never applying.
- Fix approach: Write `0005_storage.sql` **before** the first `supabase db push` (`P0-INIT-04`), or
  renumber the Storage migration to `0007` and drop the reservation convention entirely.

**`raw_sources`/`wiki_pages` cross-references stored as untyped JSONB:**
- Issue: `wiki_pages.sources jsonb not null default '[]'` (`0001_core_schema.sql:152`) holds
  `raw_source` ids with no FK, no CHECK, and no index. `wiki_pages.aliases jsonb` (`:139`) is the same.
  Deleting a `raw_source` (owner-permitted, `0004_rls_policies.sql:221-223`) leaves dangling ids in
  every wiki that cited it.
- Files: `supabase/migrations/0001_core_schema.sql:139,152`
- Impact: The "wiki → original source" half of the dual-citation promise silently breaks. Nothing
  detects it; the UI will render citations pointing at nonexistent rows.
- Fix approach: Either normalize to a `wiki_sources (wiki_id, raw_source_id, workspace_id)` join table
  with composite FKs (the same pattern already used for `source_chunks`/`wiki_embeddings`), or add a
  GIN index plus a reconciliation job. The normalized route is consistent with the `0002` decision to
  drop `related_wikis jsonb` for exactly this reason.

**Job `type` has no enumeration and no dedup key:**
- Issue: `jobs.type` is a free-text CHECK for non-emptiness only (`0003_jobs.sql:37`) — deliberate, per
  the comment. But there is also no partial unique index preventing two `compile` jobs for the same
  payload from being queued simultaneously.
- Files: `supabase/migrations/0003_jobs.sql:27-69`
- Impact: A double-clicked ingest or a retried API call enqueues duplicate LLM work — real money, and
  two workers compiling the same source concurrently race on the `(workspace_id, slug)` upsert.
- Fix approach: Add `create unique index jobs_dedup_idx on public.jobs (workspace_id, type, (payload->>'raw_source_id')) where status in ('queued','running','failed');`
  and have `P2-ING-01` treat the conflict as "already queued".

**No retention policy on `jobs`:**
- Issue: Nothing deletes `succeeded`/`dead` rows. `jobs_workspace_created_idx`
  (`0003_jobs.sql:82-83`) grows without bound.
- Files: `supabase/migrations/0003_jobs.sql`
- Impact: Table bloat, slower workspace job listings, growing backup size. Slow-burn, not urgent.
- Fix approach: A `delete from jobs where status in ('succeeded') and updated_at < now() - interval '30 days'`
  sweep in the worker loop, or `pg_cron` once on cloud.

**`prompt_templates` has no `updated_at`:**
- Issue: Every other mutable table gets `updated_at` + `set_updated_at()` trigger. `prompt_templates`
  is user-editable (`0004_rls_policies.sql:295-298`) but has only `created_at`.
- Files: `supabase/migrations/0001_core_schema.sql:180-191`
- Impact: No way to invalidate cached prompts or show "last edited"; re-running the `0006` seed cannot
  detect drift.
- Fix approach: Add the column + trigger in the next migration.

**`set_updated_at()` omits `set search_path`:**
- Issue: Every other function in the tree pins `set search_path = public`
  (`0004_rls_policies.sql:49,63,76,112`). `set_updated_at()` (`0001_core_schema.sql:18-26`) does not.
- Files: `supabase/migrations/0001_core_schema.sql:18-26`
- Impact: Low — it is SECURITY INVOKER and touches no relations. Style inconsistency that reads as an
  oversight during review.
- Fix approach: Add `set search_path = ''` for consistency with the house rule.

---

## Known Bugs

**Ownership transfer leaves the workspace unmanageable (highest-severity correctness issue found):**
- Symptoms: After `update workspaces set owner_id = <newUser>`, the new owner cannot update or delete
  the workspace, cannot manage members, and the *old* owner retains full owner powers.
- Files: `supabase/migrations/0004_rls_policies.sql:108-148` (`protect_owner_membership`),
  `:171-178` (`workspaces_update_owner`), `supabase/migrations/0001_core_schema.sql:68-84`
  (`add_owner_as_member`, AFTER INSERT only)
- Trigger: `workspaces.owner_id` is the RLS anchor for `SELECT` (`:165`) but **all privileged checks go
  through `has_workspace_role()`, which reads `workspace_members.role` only** (`:71-86`). Nothing syncs
  `owner_id` changes into `workspace_members`:
  - the new owner has no `owner` membership row → `has_workspace_role(id,'owner')` is false for them;
  - the old owner's `workspace_members.role` is still `'owner'` → they keep every owner privilege;
  - `protect_owner_membership` (`:128`) now compares `old.user_id = v_owner_id` against the *new*
    `owner_id`, so it no longer protects the row that actually grants control.
- Workaround: Perform transfers only as a two-step `service_role` operation that updates `owner_id`
  and both membership rows in one transaction. Proper fix: an `AFTER UPDATE OF owner_id ON workspaces`
  trigger that upserts the new owner as `role='owner'` and demotes the previous owner to `editor`.

**`protect_owner_membership` cannot block owner-role *promotion* of a third party, and its
cascade-detection is order-dependent:**
- Symptoms: The `v_owner_id is null → return` early-exit (`0004_rls_policies.sql:124-126`) assumes the
  parent `workspaces` row is already gone during a cascading delete. That holds today for
  `on delete cascade`, but the guard silently becomes a no-op for any future path where the row still
  exists (e.g. soft delete), disabling the protection without any error.
- Files: `supabase/migrations/0004_rls_policies.sql:117-141`
- Trigger: Any change to workspace deletion semantics.
- Workaround: Make the intent explicit — check a session flag or `tg_op`-specific condition rather than
  inferring cascade from a NULL lookup.

**Re-processing with *fewer* chunks leaves orphan rows (idempotency gap):**
- Symptoms: Re-chunking a source into 8 chunks when 12 existed upserts 0–7 and leaves 8–11 in place.
  Same for `wiki_embeddings`.
- Files: `supabase/migrations/0002_search_schema.sql:101` (`source_chunks_source_index_key`),
  `:142` (`wiki_embeddings_wiki_index_key`)
- Trigger: Chunking-parameter changes — an explicitly open question
  (`checklists.json` → `open_questions[2]`, "청킹 파라미터 … P2-ING-02에서 실측 후 확정").
- Workaround: Every re-processing handler must `delete from source_chunks where raw_source_id = $1 and chunk_index >= $n`
  after the upsert batch. `HANDOFF.md:323` states the upsert keys as the idempotency guarantee but does
  not mention the tail-deletion requirement — the doc is incomplete here.

**`reap_stale_jobs` appends to `last_error` without bound:**
- Symptoms: Each reap concatenates a new line onto `last_error`
  (`0003_jobs.sql:199-201`). A job reaped repeatedly accumulates an ever-growing text column.
- Files: `supabase/migrations/0003_jobs.sql:189-210`
- Trigger: A worker that keeps dying mid-job; bounded in practice by `max_attempts` (default 3), so
  impact is small, but the column is exposed to every workspace member via `jobs_select_member`.
- Workaround: Truncate to the last N entries or replace rather than append.

---

## Security Considerations

**`jobs.payload` and `jobs.last_error` are readable by every workspace member, including viewers:**
- Risk: `jobs_select_member` (`0004_rls_policies.sql:312-314`) grants `select *`. `payload jsonb`
  (`0003_jobs.sql:42`) and `last_error text` (`:49`) will, in the natural implementation, contain
  Storage paths, source ids, and raw exception text from the OpenRouter/embedding clients — which
  routinely echoes request URLs, model names, and occasionally auth-header fragments.
- Files: `supabase/migrations/0004_rls_policies.sql:312-314`, `supabase/migrations/0003_jobs.sql:42,49`
- Current mitigation: Tenant isolation only; no column-level restriction.
- Recommendations: Expose jobs to users through a view that projects
  `(id, workspace_id, type, status, attempts, max_attempts, run_after, created_at, updated_at)` plus a
  *sanitized* error summary, and move the `jobs_select_member` policy onto that view.
  `P2-JOB-01` must never write raw provider exceptions into `last_error` unfiltered.

**Local auth config is materially weaker than production should be:**
- Risk: `minimum_password_length = 6` (`supabase/config.toml:139`), `password_requirements = ""`
  (`:142`), `enable_confirmations = false` (`:173`), `secure_password_change = false` (`:175`),
  MFA TOTP `enroll_enabled = false` (`:238`), no captcha (`:160-164`). Unconfirmed-email signup on a
  team product means anyone can create a workspace under someone else's address.
- Files: `supabase/config.toml:116-179,236-240`
- Current mitigation: These are CLI defaults and only bind the local stack today.
- Recommendations: Treat `config.toml` as the production contract before `P0-INIT-04`. At minimum:
  `minimum_password_length = 10`, `password_requirements = "lower_upper_letters_digits"`,
  `enable_confirmations = true`, `secure_password_change = true`, and enable captcha. There is no
  checklist task that owns this — add one to Phase 0 or Phase 4.

**`service_role` bypasses every policy in `0004`, and no code-level guard exists yet:**
- Risk: The entire isolation model rests on the discipline described in `HANDOFF.md:236-243` — two
  distinct Supabase client factories, `service_client()` used only by the worker. One accidental
  `service_client()` in a request handler nullifies all 38 isolation cases.
- Files: `supabase/migrations/0004_rls_policies.sql:16-17` (documented), no enforcing code exists
- Current mitigation: Documentation only. The composite `(id, workspace_id)` FKs
  (`0002_search_schema.sql:45-49`) do catch *mismatched-tenant writes* by the worker, which is a
  genuine defense-in-depth win — but they do not catch a service-role *read* that forgets a filter.
- Recommendations: `P0-INIT-02` should put the two factories in separate modules, make
  `service_client()` importable only from a `workers/` package, and add a lint/CI grep that fails the
  build on `service_client` outside that package. Worth encoding as an explicit acceptance criterion
  on `P0-INIT-02` (it is currently only prose in HANDOFF).

**RLS violations on UPDATE/DELETE return 0 rows, not an error:**
- Risk: A viewer's `update wiki_pages` returns success with `rows=0`
  (`0004_rls_policies.sql:240-245`). If the API returns 200 on that path, the product silently lies to
  the user about having saved their edit.
- Files: `supabase/migrations/0004_rls_policies.sql:240-249`, documented at `HANDOFF.md:189-191,319-320`
- Current mitigation: Documented, not enforced.
- Recommendations: `P2-API-01` must map "affected rows = 0 on a mutation" to 403. Add this as an
  explicit test in `P4-SEC-01`.

**Global prompt templates are world-readable to any authenticated user:**
- Risk: `prompt_templates_select_global_or_member` (`0004_rls_policies.sql:287-289`) exposes all
  `workspace_id IS NULL` rows to every logged-in user, including the full `system_prompt`.
- Files: `supabase/migrations/0004_rls_policies.sql:287-289`, `supabase/migrations/0006_seed_prompts.sql`
- Current mitigation: Intentional and necessary — the Ask screen would be empty otherwise.
- Recommendations: Accept, but recognize that seeded system prompts are effectively public. Do not put
  anything proprietary or safety-critical in a *global* template; workspace-scoped templates stay private.

---

## Performance Bottlenecks

**HNSW post-filtering drops results below `k` — in two independent ways:**
- Problem: `where workspace_id = $1 order by embedding <=> $2 limit k` lets HNSW pick k candidates and
  *then* filters. Worse, the RLS policy itself acts as a second post-filter
  (`is_workspace_member(workspace_id)` appears as a `Filter:` node, per `HANDOFF.md:305-317`).
- Files: `supabase/migrations/0002_search_schema.sql:115-116,152-153`,
  `supabase/migrations/0004_rls_policies.sql:266-272`
- Cause: HNSW index has no tenant dimension; the indexes are unpartitioned and unqualified.
- Improvement path: Search queries (`P2-RAG-01`) must both (1) state `where workspace_id = $1` and
  (2) `set local hnsw.iterative_scan = strict_order`. Longer term, consider partial HNSW indexes per
  large tenant or partitioning by `workspace_id`. Note the HNSW indexes are created with default
  `m`/`ef_construction` — no tuning task exists; `P4-PERF-01` should own it.

**HNSW indexes exist before any bulk load:**
- Problem: Both vector indexes are created on empty tables (`0002_search_schema.sql:115,152`), so the
  first large embedding backfill pays per-row index maintenance.
- Files: `supabase/migrations/0002_search_schema.sql:115-116,152-153`
- Cause: Index-then-load ordering.
- Improvement path: For large historical imports, drop and rebuild the HNSW index around the batch.
  Acceptable as-is for incremental ingest.

**Lexical (bigram) search filters tenants after the GIN scan too:**
- Problem: `source_chunks_search_tsv_idx` and `wiki_pages_search_tsv_idx` are single-column GIN
  (`0002_search_schema.sql:119-120,222-223`). `workspace_id` is a separate btree (`:108-109`).
- Files: `supabase/migrations/0002_search_schema.sql:108-120,222-223`
- Cause: No composite/partial index combining tenant + tsvector (GIN needs `btree_gin` for that).
- Improvement path: Measure first in `P4-PERF-01`. If tenant selectivity is high, `create extension btree_gin`
  and index `(workspace_id, search_tsv)`.

**OpenRouter forfeits Anthropic prompt caching:**
- Problem: The compile system prompt is long and repeats per source; cost scales linearly with source
  count with no cache discount (`HANDOFF.md:328-329`, `supabase/migrations/0006_seed_prompts.sql`).
- Cause: `decisions.llm_provider` chose OpenRouter for model-swap freedom.
- Improvement path: Measure real cost in `P4-OPS-01`; revisit direct Anthropic if the delta is material.

---

## Fragile Areas

**Bigram tokenizer version coupling:**
- Files: `supabase/migrations/0002_search_schema.sql:79-94` (`search_tsv`, `tsv_tokenizer_version`),
  `:218-220` (same on `wiki_pages`)
- Why fragile: `search_tsv` is deliberately **not** a generated column — the application fills it. If
  the index-time and query-time tokenizers diverge, search degrades *silently*, with no error and no
  test that would notice. `tsv_tokenizer_version` is nullable with no default and nothing enforces that
  it is written.
- Safe modification: Keep one tokenizer module used by both the indexer and the query path
  (`P2-BE-02` is scoped exactly this way). Bump the version constant on any change and backfill rows
  where `tsv_tokenizer_version < current`.
- Test coverage: **None.** A round-trip property test (index a corpus, query each document's own text,
  assert self-retrieval) is the single highest-value test to write here.

**Query-side `tsquery` construction:**
- Files: `supabase/migrations/0002_search_schema.sql:88-93`
- Why fragile: Feeding a bigram string to `to_tsquery` raises a syntax error; `plainto_tsquery`
  produces false positives. The correct call is `phraseto_tsquery('simple', bigram(q))`. This is
  documented in a SQL comment and in `HANDOFF.md:302-303` — nowhere in code, because no code exists.
- Safe modification: Encapsulate in one function in `P2-BE-02`; never build tsquery strings inline.
- Test coverage: None.

**Job queue is at-least-once with a timing-dependent correctness boundary:**
- Files: `supabase/migrations/0003_jobs.sql:189-210`
- Why fragile: If `reap_stale_jobs(p_timeout)` (default 15 min) is shorter than the longest legitimate
  LLM compile, a live worker's job is stolen and processed twice. The `attempts`-on-claim design
  (`:116`) makes poison pills safe but means a reaped-then-retried job burns attempts honestly — a
  slow-but-healthy job can reach `dead` purely from timeouts.
- Safe modification: Set the timeout well above the p99 compile latency, and make every handler
  idempotent via the three unique keys (`HANDOFF.md:322-323`) — subject to the tail-deletion caveat
  noted under Known Bugs.
- Test coverage: The 8-worker/400-job concurrency run described in `HANDOFF.md:145-149` was ad-hoc and
  is **not committed anywhere**. It cannot be re-run.

**`workspaces` SELECT policy has two disjunct paths:**
- Files: `supabase/migrations/0004_rls_policies.sql:163-165`
- Why fragile: `is_workspace_member(id) or owner_id = auth.uid()` exists solely so that
  `insert … returning *` works before the AFTER-insert membership trigger fires. It is the same
  `owner_id`-vs-membership split that produces the ownership-transfer bug above. Any future change to
  either the trigger timing or the transfer path must re-examine this line.
- Safe modification: Making `add_owner_as_member` a BEFORE trigger is not possible (needs the new id);
  the clean fix is a `security definer` RPC `create_workspace(name)` that does both inserts, after
  which the `owner_id` disjunct can be dropped.
- Test coverage: Claimed 38/38 passing, artifact not committed.

---

## Scaling Limits

**PostgREST row cap:**
- Current capacity: `max_rows = 1000` (`supabase/config.toml:18`).
- Limit: Any direct client query over a workspace with >1000 wikis, chunks, or links silently truncates.
- Scaling path: All list endpoints must paginate explicitly; the graph canvas (`P3-UI-03`) is the most
  likely to hit this first since it fetches `wiki_links` in bulk.

**Embedding dimension is hard-coded to 1536:**
- Current capacity: `extensions.vector(1536)` on both tables
  (`0002_search_schema.sql:77,138`) — i.e. `text-embedding-3-small`.
- Limit: Switching embedding models requires an `alter column type` plus a full re-embed of every chunk
  and wiki, plus HNSW rebuilds. There is no `embedding_model`/`embedding_version` column, so a partial
  migration is indistinguishable from a complete one.
- Scaling path: Add `embedding_model text` + `embedding_version smallint` columns mirroring the
  `tsv_tokenizer_version` pattern already established for lexical search. The asymmetry (lexical search
  has versioning, vector search does not) looks like an oversight rather than a decision.

**Single job queue table, single poll index:**
- Current capacity: `jobs_poll_idx` on `(run_after, created_at) where status in ('queued','failed')`
  (`0003_jobs.sql:77-79`) — validated at 5000 rows.
- Limit: Every worker polls the same hot index; contention grows with worker count. Fine to tens of
  workers; not a design for thousands.
- Scaling path: Type-sharded partial indexes, or move to a dedicated broker. Not needed at current scale.

**Local port allocation collides with a sibling project:**
- Current capacity: Ports moved to the 544xx range because `zettlink` occupies 5432x
  (`supabase/config.toml:8,26,36,82,93`; `HANDOFF.md:253-264`).
- Limit: Any tutorial, script, or tool defaulting to `54321`/`54322` connects to the **wrong database**.
- Scaling path: Never hardcode ports in application code or test fixtures; read from a single
  `.env`-sourced `DATABASE_URL`. Note the repo has no `.env.example` yet despite `.gitignore:11`
  explicitly whitelisting one.

---

## Dependencies at Risk

**Supabase CLI 2.33.2 vs current 2.111.0:**
- Risk: ~78 minor versions behind. `config.toml` schema has almost certainly changed; upgrading may
  rewrite or reject the current file.
- Impact: An upgrade mid-flight could break `supabase start`/`db reset` — the only way anything in this
  repo is currently exercised.
- Migration plan: `HANDOFF.md:281` says upgrade after Phase 1. Phase 1 has one task left
  (`P1-STO-01`), so this is due now. Upgrade on a branch, diff the regenerated `config.toml`, and
  re-apply the port customizations deliberately.

**Docker host is at 94% disk with a 61GB `Docker.raw`:**
- Risk: The local stack is the entire test environment. `dockerd` has already died once
  (`HANDOFF.md:279-280`), producing 500s from every API call.
- Impact: Total loss of development capability, with a confusing failure mode.
- Migration plan: `docker builder prune` reclaims ~2.57GB but affects other projects — get explicit
  user confirmation. Longer term this argues for creating the cloud project sooner than
  `P0-INIT-04` implies.

**No cloud Supabase project exists:**
- Risk: Everything validated so far is local-only. PG 17 (`supabase/config.toml:31`), extension
  availability, and `hnsw.iterative_scan` support (pgvector 0.8.0 locally, per `HANDOFF.md:317`) are all
  unverified against the hosted platform.
- Impact: Migrations that pass locally may fail on push; the vector search workaround may be unavailable.
- Migration plan: Create the Seoul-region project early enough to smoke-test `db push` before it is on
  the critical path.

---

## Missing Critical Features

**Storage buckets and policies (`P1-STO-01`) are unimplemented:**
- Problem: `raw_sources.storage_path` / `mime_type` / `byte_size`
  (`0001_core_schema.sql:107-112`) reference a bucket that does not exist. The path convention
  `{workspace_id}/{raw_source_id}/{filename}` is documented in a comment only — no `storage.objects`
  RLS policy enforces that the first path segment matches a workspace the caller belongs to.
- Blocks: `P2-ING-01` (file upload) entirely, and the "immutable original preservation" product promise.
  Note `file_size_limit = "50MiB"` (`supabase/config.toml:103`) is the CLI default, unreviewed against
  actual PDF sizes.

**No ask/answer history table:**
- Problem: The dual-citation answer is the core product output, and there is nowhere to store one.
  Citations reference `[[src:chunk_id]]` (`HANDOFF.md:216`), but `source_chunks` cascade-delete with
  their parent (`0002_search_schema.sql:103-105`), so any persisted answer would dangle.
- Blocks: Answer permalinks, feedback loops, and the `disputed` knowledge-conflict input for `P2-QC-01`.
  Worth confirming this is intentionally out of scope for v1 rather than an omission.

**No user cancellation path for jobs:**
- Problem: `jobs` exposes only SELECT to users (`0004_rls_policies.sql:312-314`). A runaway or
  mistakenly-queued compile cannot be cancelled from the product.
- Blocks: Cost control (`P4-OPS-01`) and basic UX on `P3-UI-01`.

**No per-workspace LLM cost ceiling:**
- Problem: Listed as `checklists.json` → `open_questions[3]`, deferred to `P4-OPS-01`. Until then,
  nothing bounds spend — no quota column, no counter table.
- Blocks: Safe public exposure of the ingest endpoint.

---

## Test Coverage Gaps

**This is the largest single risk in the repository.**

**Zero committed tests of any kind:**
- What's not tested: everything. There is no `supabase/tests/`, no pgTAP, no CI workflow, no
  `.github/` directory, no seed fixture beyond the `[db.seed]` reference to a `./seed.sql` that does
  not exist (`supabase/config.toml:55-60`).
- Files: repository root, `supabase/`
- Risk: `HANDOFF.md` asserts 38/38 RLS isolation cases, 13 `EXPLAIN ANALYZE` plans, 10 queue
  behaviours, an 8-worker/400-job concurrency proof, and 9 seed-idempotency checks — **none of which
  exist as re-runnable artifacts.** Every one of those guarantees silently expires the moment a
  migration changes. Regression detection is currently zero.
- Priority: **High.** Convert the ad-hoc verification into `supabase/tests/*.sql` pgTAP files runnable
  via `supabase test db`, before writing application code. The RLS suite in particular is cheap to
  encode and protects the product's central security claim.

**RLS ownership-transfer path untested:**
- What's not tested: `update workspaces set owner_id = …` followed by the new owner attempting an
  owner-only action. This is exactly the gap that hides the bug documented above.
- Files: `supabase/migrations/0004_rls_policies.sql:163-203`
- Risk: A privilege model that reads as correct and is not.
- Priority: **High.**

**`protect_owner_membership` trigger untested for the cascade-delete path:**
- What's not tested: `delete from workspaces` where the owner has a membership row — the early-exit at
  `0004_rls_policies.sql:124-126` must not raise.
- Files: `supabase/migrations/0004_rls_policies.sql:108-148`
- Risk: Workspace deletion fails at runtime with a Korean-language exception.
- Priority: **High** — trivially cheap to test, catastrophic if wrong.

**Composite-FK tenant enforcement untested:**
- What's not tested: Inserting a `source_chunk` whose `workspace_id` differs from its parent
  `raw_source`. This constraint (`0002_search_schema.sql:103-105`) is the *only* thing standing between
  a worker bug and cross-tenant data mixing.
- Files: `supabase/migrations/0002_search_schema.sql:45-49,103-105,143-145,184-194`
- Risk: Silent cross-tenant contamination if a future migration drops the composite unique keys.
- Priority: **High.**

**Queue concurrency and reap semantics untested:**
- What's not tested: `SKIP LOCKED` non-blocking claim, exactly-once claim under N workers, backoff
  scheduling arithmetic (`0003_jobs.sql:171-174`), `dead` transition at `max_attempts`, and reap of a
  stale lock.
- Files: `supabase/migrations/0003_jobs.sql:103-210`
- Risk: Duplicate or lost LLM work — directly monetary.
- Priority: **Medium-High.** The concurrency portion needs a harness, so it may land with `P2-JOB-01`
  rather than as pgTAP.

**Function EXECUTE revocation untested:**
- What's not tested: That `anon`/`authenticated` genuinely cannot call `claim_job` et al. via
  PostgREST `/rpc/` (`0003_jobs.sql:221-229`).
- Files: `supabase/migrations/0003_jobs.sql:213-229`
- Risk: A future `create or replace function` re-grants default privileges and re-opens the hole
  without any signal.
- Priority: **Medium.** Cheap to assert with `has_function_privilege()`.

**Seed idempotency untested:**
- What's not tested: Re-running `0006_seed_prompts.sql` leaves row counts unchanged, and the
  `{{placeholder}}` set matches what `P2-LLM-01` will bind (`HANDOFF.md:207-216`).
- Files: `supabase/migrations/0006_seed_prompts.sql`
- Risk: Duplicate templates, or a template referencing a variable the binder never supplies — which
  fails as a literal `{{question}}` reaching the model, not as an exception.
- Priority: **Medium.**

---

*Concerns audit: 2026-08-01*
