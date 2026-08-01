# Testing Patterns

**Analysis Date:** 2026-08-01

## Test Framework

**Runner:**
- **Not detected.** No test framework is installed or configured in this repository. There is no `pyproject.toml`, `package.json`, `pytest.ini`, `vitest.config.ts`, or `conftest.py` anywhere in the tree. No test file exists.
- Config: Not detected.

**Assertion Library:**
- Not detected.

**Run Commands:**
- Not detected. The only executable verification loop today is the Supabase migration cycle:

```bash
supabase start                    # bring the local stack up
supabase db reset                 # reapply 0001..0006 from scratch
supabase stop

# psql is not installed locally — go through the container
docker exec -it supabase_db_NexusWiki psql -U postgres -d postgres
```

⚠️ Local ports are **not** the Supabase defaults. This machine runs a second Supabase stack
(`zettlink`) on `54321-54327`. NexusWiki lives on the `544xx` band — API `54421`,
DB `54422`, Studio `54423`, Inbucket `54424`, Analytics `54427`, Pooler `54429`,
Shadow DB `54420` (`supabase/config.toml`, `HANDOFF.md` §4). Copy-pasting `54322`
from any tutorial connects you to the wrong project's database.

## Planned Test Stack (from `checklists.json` / `HANDOFF.md`)

| Surface | Runner | Established by | Location |
|---|---|---|---|
| FastAPI backend + worker | pytest (implied) | `P0-INIT-02` | `apps/fastapi-backend/tests/` |
| Next.js dashboard | **Vitest + Testing Library** (explicitly decided) | `P0-INIT-03` | `apps/dashboard/` |
| Lint/format gate | pre-commit (`ruff` + `prettier`) | `P0-INIT-01` | `.pre-commit-config.yaml` |
| Type gate | `tsc --noEmit`, zero errors | `P0-INIT-03` | `apps/dashboard/` |

The Python runner is never named outright, but `.gitignore` reserves `.pytest_cache/`,
every planned backend test file is `test_*.py`, and `P2-BE-02` calls for a **property test** —
so pytest (plus a property-based library such as Hypothesis) is the intended target.

Frontend gate (`P0-INIT-03` verification): `pnpm dev` boots, `pnpm test` passes one sample
test, `tsc --noEmit` reports zero errors. Package manager is **pnpm**.

## Test File Organization

**Location (planned):**
- Backend: a single `tests/` directory beside the app — **not** co-located with sources.
- Frontend: not specified beyond "Vitest + Testing Library".

**Naming (planned):** `test_<module under test>.py`, one file per service module.

**Structure (planned, from `checklists.json` `target_files`):**
```
apps/fastapi-backend/
├── services/
│   ├── tokenizer.py
│   ├── chunker.py
│   ├── jobs.py
│   ├── compiler.py
│   ├── wikilinks.py
│   ├── embeddings.py
│   └── hybrid_search.py
└── tests/
    ├── test_tokenizer.py          # P2-BE-02
    ├── test_chunker.py            # P2-ING-02
    ├── test_jobs.py               # P2-JOB-01
    ├── test_compiler.py           # P2-LLM-01
    ├── test_wikilinks.py          # P2-LNK-01
    ├── test_embeddings.py         # P2-EMB-01
    ├── test_hybrid_search.py      # P2-RAG-01
    ├── test_e2e.py                # P4-E2E-01
    ├── test_idempotency.py        # P4-QA-01
    ├── test_tenant_isolation.py   # P4-SEC-01
    ├── test_search_quality.py     # P4-PERF-01
    └── fixtures/
        └── golden_queries.json    # P4-PERF-01
```

## Current Practice: SQL Verification Harnesses

Until a runner exists, every completed task is validated by an **ad-hoc SQL session against the
local stack**, and the outcome is recorded in `checklists.json` under
`<task>.verification_result` as `{date, method, results[]}`. The scripts themselves are not
committed — only the recorded evidence. Follow this pattern for the remaining migration work
(`P1-STO-01`), and port these cases into `tests/` once pytest exists.

The house pattern for a migration verification, as executed for `0001`–`0006`:

1. **Seed at realistic scale** — 2000 rows for the search schema, 5000 jobs for the queue.
2. **Prove the plan, not just the result** — `EXPLAIN ANALYZE` each access path and assert the
   intended index appears by name:
   ```text
   Index Scan using wiki_embeddings_embedding_idx     -- HNSW, channel 1
   Index Scan using source_chunks_embedding_idx       -- HNSW, channel 2
   Bitmap Index Scan on wiki_pages_search_tsv_idx     -- GIN,  channel 3
   Bitmap Index Scan on source_chunks_search_tsv_idx  -- GIN,  channel 4
   Index Scan using wiki_links_from_idx               -- 3-hop CTE, channel 5
   ```
3. **Assert negative cases** — every CHECK constraint must be shown rejecting bad input
   (6 constraint rejections for `0002`, 4 for `0003`).
4. **Assert concurrency where it matters** — for `0003`: 2 jobs / 2 workers take distinct rows;
   1 job / 2 workers has the loser return empty in **172 ms** without blocking on the winner's
   5-second lock; **8 workers × 400 jobs → `sum(attempts) = 400`**, zero residual locks, zero
   double-processing.
5. **Assert idempotency** — re-running `0006_seed_prompts.sql` end-to-end leaves row counts
   unchanged.
6. **Record pass counts, not prose** — `38/38 PASS`, `2000/2000 slice consistency`, `9종 전부 통과`.

### RLS test fixture pattern (`P1-SEC-01`, 38/38)

The matrix that must be reproduced by `tests/test_tenant_isolation.py`:

- Workspace **A** with three principals (`owner`, `editor`, `viewer`), workspace **B** with an
  `owner`, plus a **non-member** authenticated user and **anon**.
- For each principal × each of the 9 tables × each of SELECT/INSERT/UPDATE/DELETE, assert the
  exact expected outcome.
- Distinguish the two failure shapes explicitly — this is the single most important assertion
  discipline in the project:
  - `USING` violation on UPDATE/DELETE → **0 rows, no exception**
  - `WITH CHECK` violation → **SQLSTATE `42501`**
  - owner-membership trigger → **SQLSTATE `P0001`**
  - RLS recursion regression → **SQLSTATE `42P17`** must never appear
- Assert privilege-escalation paths specifically: editor adding self as `owner` (42501),
  editor raising own role (0 rows), owner deleting/demoting own membership (P0001).
- Assert derived tables are forge-proof: editor INSERT into `source_chunks` / `wiki_links` → 42501
  (a forged chunk would fake the source side of a dual citation).
- Assert the plan survives RLS: vector search still uses `source_chunks_embedding_idx` with
  policies active.

## Mocking

**Framework:** Not detected.

**What to mock (planned):**
- OpenRouter LLM calls in `test_compiler.py` — responses must be deterministic, and the retry
  path (Pydantic validation failure → up to 3 retries) needs injectable malformed output.
- The embeddings provider in `test_embeddings.py`.
- URL fetching in the ingestion path.

**What NOT to mock:**
- **Postgres.** Every guarantee the project relies on — RLS isolation, `SKIP LOCKED` claim
  semantics, composite-FK tenant enforcement, HNSW plan selection, partial-index usage,
  constraint rejection — is a database behavior. A mocked DB tests nothing here. Run against the
  local Supabase stack.
- The tokenizer, in search tests. Index-time and query-time tokenization must go through the same
  real module; substituting one is exactly the bug the tests exist to catch.

## Fixtures and Factories

**Committed fixture (planned):** `apps/fastapi-backend/tests/fixtures/golden_queries.json` —
20 questions with expected wiki/source citations, the tuning baseline for RRF weights (`P4-PERF-01`).

**E2E fixture (planned):** 3 real sources, one each of PDF / URL / plain text (`P4-E2E-01`).

**Tenant fixture (planned):** the A/B/non-member/anon principal set described above.

## Coverage

**Requirements:** No coverage target is defined anywhere. Not enforced.

**View Coverage:** Not detected.

The project gates on **named acceptance criteria per task** instead of coverage percentage.
`checklists.json` `_notes` states the rule: each task's `verification` is written as
"a criterion that can be judged pass/fail mechanically." Written targets:

| Task | Threshold |
|---|---|
| `P4-PERF-01` | recall@5 ≥ 0.8, p95 search latency ≤ 1.5 s; on miss, print per-channel contribution |
| `P4-SEC-01` | every cross-workspace endpoint call returns 403 or 404; zero foreign rows in search results |
| `P4-E2E-01` | one run yields `raw_sources = 3`, `source_chunks > 0`, `wiki_pages > 0`, `wiki_links > 0`, and both arrays of `double_citation` non-empty |
| `P0-INIT-03` | `pnpm test` passes ≥ 1 test, `tsc --noEmit` zero errors |
| `P0-INIT-01` | `pre-commit run --all-files` passes |

## Test Types

**Unit (planned):** per-service module under `apps/fastapi-backend/tests/`. Tokenizer, chunker,
wikilink parsing, job state transitions, compiler output validation.

**Property-based (planned):** `P2-BE-02` explicitly requires a property test asserting that
index-time tokens and query-time tokens are identical for the same input. Concrete cases named:
`'지식관리를' → ['지식','식관','관리','리를']`, and `'KPT-2 회고'` must preserve `KPT-2` intact
(Hangul → 2-char bigrams, Latin/numeric → whole words).

**Integration (planned):** `test_hybrid_search.py` across all five retrieval channels;
`test_jobs.py` against the real queue functions.

**E2E (planned):** `test_e2e.py` — ingest → compile → embed → ask, asserting dual citations.

**Security (planned):** `test_tenant_isolation.py` — see the RLS fixture pattern above.

**Performance (planned):** `test_search_quality.py` against `golden_queries.json`.

## Common Patterns to Establish

**Idempotency testing (`P4-QA-01`):** the project's definition of idempotent is *not* "the LLM
returns identical text" — that is unachievable. It is: **re-ingesting the same `content_hash`
adds no rows, and `(workspace_id, slug)` upsert produces no duplicate wiki pages**
(`HANDOFF.md` §5). Assert row-count deltas, never output equality.

**At-least-once job semantics:** `reap_stale_jobs` can hand a live worker's job to a second
worker if its timeout (default 15 min) is shorter than the job's real runtime, and LLM compile
jobs take minutes. Every handler must be idempotent via `(workspace_id, slug)`,
`(raw_source_id, chunk_index)`, `(wiki_id, chunk_index)`. Tests should deliberately double-deliver
a job and assert row counts are unchanged.

**Never `UPDATE public.jobs` from a test.** Drive state through `claim_job` / `complete_job` /
`fail_job` / `reap_stale_jobs`; the lock-consistency CHECK and `attempts` accounting live inside
them (`supabase/migrations/0003_jobs.sql`).

**Silent-failure assertions:** the two highest-value classes of bug in this project fail without
raising — an RLS `USING` denial returns 0 rows, and a tokenizer version mismatch returns
plausible-but-wrong search results. Assertions must check row counts and result identity
explicitly rather than merely asserting "no exception was raised."

**Vector-search assertions:** queries must set `where workspace_id = $1` explicitly and
`set local hnsw.iterative_scan = strict_order`; without both, HNSW post-filtering silently
returns fewer than `k` rows (`HANDOFF.md` §5, verified on local pgvector 0.8.0). Tests should
assert result cardinality, not just relevance.

---

*Testing analysis: 2026-08-01*
