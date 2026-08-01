# Coding Conventions

**Analysis Date:** 2026-08-01

> **Scope note.** This repository currently contains **no application source code**. The only
> executable artifacts are five SQL migrations under `supabase/migrations/`, plus design tokens
> in `docs/design-systems/` and the task ledger `checklists.json`. Conventions below are derived
> from those files and from the constraints declared in `HANDOFF.md`. Sections marked
> **(planned)** are commitments recorded in `checklists.json` / `HANDOFF.md` that no code has
> yet exercised — follow them when writing the first Python/TypeScript files.

## Naming Patterns

**Files:**
- Migrations: `NNNN_snake_case_topic.sql`, zero-padded 4-digit sequence — `supabase/migrations/0001_core_schema.sql`, `0002_search_schema.sql`, `0003_jobs.sql`, `0004_rls_policies.sql`, `0006_seed_prompts.sql`.
- **Number order is apply order.** `0005` is deliberately reserved for the Storage bucket migration (`supabase/migrations/0005_storage.sql`, task `P1-STO-01`) and must land *before* a cloud project is created — see `HANDOFF.md` §3e.
- Python (planned): `snake_case.py` under `apps/fastapi-backend/` — `services/tokenizer.py`, `routers/sources.py`, `app/config.py`.
- Python tests (planned): `apps/fastapi-backend/tests/test_<module>.py`.
- React components (planned): `PascalCase.tsx` under `apps/dashboard/components/` — `WorkspaceSwitcher.tsx`, `AskCanvas.tsx`, `GraphCanvas.tsx`.
- Next.js routes (planned): App Router lowercase segments with route groups — `apps/dashboard/app/(auth)/login/page.tsx`.

**SQL identifiers:**
- All lowercase `snake_case`; SQL keywords are also lowercase (`create table`, `on delete cascade`). No uppercase keywords anywhere in `supabase/migrations/`.
- Tables: plural nouns — `workspaces`, `workspace_members`, `raw_sources`, `wiki_pages`, `source_chunks`, `wiki_embeddings`, `wiki_links`, `prompt_templates`, `jobs`.
- Indexes: `<table>_<columns>_idx` — `workspaces_owner_id_idx`, `wiki_pages_workspace_category_idx`, `jobs_poll_idx`, `source_chunks_embedding_idx`.
- Triggers: `<table>_<action>` — `workspaces_set_updated_at`, `wiki_pages_set_updated_at`, `jobs_set_updated_at`, `workspaces_add_owner_member`.
- Named CHECK constraints: `<table>_<intent>` — `jobs_lock_consistency` (`supabase/migrations/0003_jobs.sql:65`).
- Functions: verb-first `snake_case`, always schema-qualified as `public.<name>` at definition and call sites — `public.set_updated_at()`, `public.is_workspace_member()`, `public.claim_job()`.
- Function parameters: `p_` prefix to avoid collision with column names — `p_worker_id`, `p_job_id`, `p_backoff`, `p_max_backoff`, `p_timeout` (`supabase/migrations/0003_jobs.sql:103-196`). RLS helper params use a short domain name instead (`ws_id`, `min_role`).

**Types/enums:**
- Enumerations are `text` columns with an inline `check (col in (...))`, **not** Postgres `enum` types — `wiki_pages.category`, `jobs.status`, `workspace_members.role`.
- One documented exception: `jobs.type` has no enumeration CHECK (only non-empty), because job kinds churn during Phase 2. The worker must route unknown `type` values straight to `dead` with `last_error` set — rationale is inline at `supabase/migrations/0003_jobs.sql:31-36`.

## Code Style

**Formatting:**
- SQL: 2-space indent, one column per line, aligned inline comments, `-- ---` rule lines separating numbered sections within a file.
- Python (planned): `ruff` via pre-commit (`P0-INIT-01`, target file `.pre-commit-config.yaml`).
- TypeScript/TSX (planned): `prettier` via pre-commit; TypeScript `strict` mode with `tsc --noEmit` clean (`P0-INIT-03`).

**Linting:**
- Not yet configured. `.gitignore` already reserves `.ruff_cache/` and `.mypy_cache/`, so ruff (and likely mypy) are the intended Python toolchain.
- Gate: `pre-commit run --all-files` must pass from the repo root (`P0-INIT-01` verification).

**Language of prose:**
- All comments, commit messages, and docs are **Korean**. Identifiers, keywords, and file names stay English/ASCII. Match this — a Korean codebase with English identifiers is the house style, not an accident.

## File Header Convention

Every migration opens with a boxed header giving file identity, owning task ID, and decision provenance. Reproduce this for new migrations:

```sql
-- =============================================================================
-- NexusWiki 0003: 잡 큐
--
-- 관련 태스크: P1-DB-03 (소비자는 P2-JOB-01 워커, 생산자는 P2-ING-01 수집 API)
-- 설계 근거:  checklists.json > decisions.job_queue
--
-- <ASCII state diagram or invariant summary>
-- =============================================================================
```

Rules observed in all five migrations:
- **Cite the task ID** (`P1-DB-03`) and the **decision key** in `checklists.json` (`decisions.job_queue`). Never restate a decision's reasoning inline — point at the ledger.
- Name downstream consumers by task ID so a reader knows who depends on the object.
- ASCII state/flow diagrams live in the header when the file encodes a state machine (`supabase/migrations/0003_jobs.sql:9-15`).

## Comment Conventions

Comments are load-bearing here and unusually dense (~40% of migration lines). The rule is: **comment the reason, never the mechanic.**

- Every non-obvious DDL choice carries a "what breaks otherwise" note. Example, `supabase/migrations/0001_core_schema.sql:36-38`:
  ```sql
  -- on delete restrict: 워크스페이스를 소유한 사용자는 삭제 전에
  -- 소유권을 이전해야 합니다. cascade로 두면 계정 삭제가 팀 데이터를 날립니다.
  owner_id uuid not null references auth.users (id) on delete restrict,
  ```
- `⚠️` prefixes a footgun that will silently corrupt data or security if ignored — `supabase/migrations/0003_jobs.sql:186`, `supabase/migrations/0004_rls_policies.sql:17`, `:30`.
- Deviations from the original plan are annotated in-file **and** recorded in `checklists.json` → `<task>.deviations_from_plan`. Both must be updated together.
- Public functions get a `comment on function ... is '...'` describing contract and caller restriction — see `supabase/migrations/0003_jobs.sql:130`.
- Placeholder/path conventions are documented at the column that stores them (e.g. storage path rule `{workspace_id}/{raw_source_id}/{filename}` at `supabase/migrations/0001_core_schema.sql:108`).

## SQL Patterns (mandatory)

**Primary keys:** `uuid primary key default gen_random_uuid()`. Text PKs were explicitly rejected (`HANDOFF.md` §2).

**Timestamps:** `created_at timestamptz not null default now()`; mutable tables add `updated_at` plus a `before update` trigger calling the shared `public.set_updated_at()` (`supabase/migrations/0001_core_schema.sql:18-26`). Do not hand-maintain `updated_at` in application code.

**Tenancy:** every domain table carries `workspace_id uuid not null references public.workspaces (id) on delete cascade`. Child tables of `raw_sources`/`wiki_pages` use a **composite FK on `(id, workspace_id)`** so a wrong tenant id is rejected by the FK even when the writer is `service_role` and bypasses RLS.

**Idempotency keys are schema-level:** `unique (workspace_id, content_hash)`, `unique (workspace_id, slug)`, `(raw_source_id, chunk_index)`, `(wiki_id, chunk_index)`. New pipelines must upsert on these, not `select`-then-`insert` (`HANDOFF.md` §5).

**RLS:** enable RLS in the table's own migration with **no policies** (= deny-all), then grant policies in a dedicated policy migration. This removes the window where a table is reachable by the `anon` key (`supabase/migrations/0001_core_schema.sql:207-219`).

**SECURITY DEFINER helpers** must always carry all three modifiers:
```sql
security definer stable set search_path = public
```
Omitting `stable` makes the policy an O(n) function call per row; omitting `set search_path` is a privilege-escalation hole (`supabase/migrations/0004_rls_policies.sql:36-38`).

**`auth.uid()` is wrapped as `(select auth.uid())`** inside policy predicates so the planner hoists it to an InitPlan instead of re-evaluating per row (`supabase/migrations/0004_rls_policies.sql:54`).

**Extension objects are schema-qualified:** pgvector lives in `extensions`, so migrations write `extensions.vector` / `extensions.vector_cosine_ops` rather than relying on the executing role's `search_path`.

**Function privileges are revoked, then granted:** Supabase auto-grants EXECUTE on new `public` functions to `anon`/`authenticated`. Server-only functions must explicitly `revoke all ... from public, anon, authenticated` and `grant execute ... to service_role` (`supabase/migrations/0003_jobs.sql:221-229`).

**Seeds are idempotent:** re-running `supabase/migrations/0006_seed_prompts.sql` must not change row counts.

## Error Handling

**DB layer:** invariants are enforced by CHECK constraints, partial unique indexes, and triggers rather than by application validation. Prefer adding a constraint over adding a Python guard.

**API layer (planned, non-negotiable — `HANDOFF.md` §3c/§5):**
- An RLS `USING` failure on UPDATE/DELETE returns **0 rows, not an exception**. The API must map **affected rows == 0 → HTTP 403**.
- A `WITH CHECK` violation surfaces as SQLSTATE `42501` → also 403.
- Config errors fail fast at boot: a missing environment variable must abort startup naming the specific key (`P0-INIT-02` verification).
- LLM structured output uses prompt + Pydantic validation + **3 retries** (`decisions.structured_output`); OpenRouter cannot use Anthropic native output formats.

**Job errors:** never `UPDATE public.jobs` directly. Use `claim_job` / `complete_job` / `fail_job` / `reap_stale_jobs` — attempt accounting and the `jobs_lock_consistency` invariant live inside those functions (`HANDOFF.md` §3b).

## Logging

- Planned: structured logging configured in `apps/fastapi-backend/app/config.py` (`P0-INIT-02`). No framework chosen in code yet.
- SQL-side diagnostics are appended to `jobs.last_error` with a `[reaped]` marker rather than logged out-of-band (`supabase/migrations/0003_jobs.sql:199-201`).

## Module Design

**Database client factories (planned, security-critical):** split into two files/functions and never blur them —

```text
user_client(access_token)  요청자 JWT. RLS enforced → all user request paths
service_client()           service_role. BYPASSRLS → worker + migrations only
```

Using `service_client()` on a user request path voids the entire isolation model. Worker code using `service_client()` must pass an explicit `workspace_id` filter on every query (`HANDOFF.md` §3e, §5).

**Single-source shared logic:** the Korean bigram tokenizer must be one module used by both indexing and querying (`apps/fastapi-backend/services/tokenizer.py`). Divergence produces silently wrong search results with no error.

**Template rendering:** prompt templates use `{{variable}}`. **Do not use `str.format`** — injected markdown/JSON contains single braces and will raise `KeyError` or corrupt content. Use plain string substitution (`HANDOFF.md` §3d).

## Design Tokens

Frontend styling reads from `docs/design-systems/design-tokens.css` (CSS custom properties) and `docs/design-systems/design-tokens.json` (W3C design-tokens format). Both are generated from `DESIGN-airbnb.md` and carry a `Generated:` date header.

- CSS variable naming: `--<category>-<name>[-<modifier>]` — `--color-primary`, `--color-primary-active`, `--color-surface-soft`.
- Categories: `color`, `typography` (fontFamily + named scales `display-xl`/`display-lg`/`title-md`/`body-md`/`body-sm`), `border.radius` (`none`…`full`), `spacing` (`xxs`…`section`).
- The CSS file is sectioned with numbered banner comments (`1. COLOR TOKENS`) and each token carries a usage comment.
- Consume tokens; do not introduce raw hex values or ad-hoc px spacing in components.

## Commit Conventions

Conventional Commits with a **Korean subject** and an em-dash detail clause:

```text
feat(db): 0006 전역 프롬프트 템플릿 시드 — ask 4종 + compile 1종
feat(db): 0004 멀티테넌트 RLS 정책 — 9개 테이블 전체
feat(db): 0003 잡 큐 — jobs 테이블 + SKIP LOCKED 큐 조작 함수
feat(db): 0002 검색 스키마 — source_chunks/wiki_embeddings/wiki_links
chore: 프로젝트 기반 — 실행 계획 및 코어 스키마
```

- Form: `type(scope): <migration number or subject> — <what changed, concretely>`.
- Scope so far is `db`; expect `api`, `worker`, `web` as apps land.
- Migration commits lead with the migration number.
- Subjects quantify (`9개 테이블 전체`, `ask 4종 + compile 1종`) rather than saying "add policies".
- One task = one commit. Commits map 1:1 onto `checklists.json` task IDs.

## Task Ledger Convention

`checklists.json` is the source of truth for scope and rationale. When completing work:
- Set `status` (`pending` → `in_progress` → `done`).
- Record `verification_result` with `date`, `method`, and a `results` array of pass statements.
- Record any DDL/design divergence under `deviations_from_plan` with its reason.
- Never restate rationale in a second place — link to `decisions.<key>`.
- No derived/summary fields (they go stale immediately) and no `$schema` — per `_notes` in `checklists.json`.

---

*Convention analysis: 2026-08-01*
