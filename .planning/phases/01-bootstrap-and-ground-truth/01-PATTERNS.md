# Phase 1: Bootstrap and Ground Truth - Pattern Map

**Mapped:** 2026-08-02
**Files analyzed:** 24 new/modified files
**Analogs found:** 4 / 24 (in-repo analogs exist only for the SQL migration + config/doc families)

> **Reality check for the planner.** The repo today contains only `supabase/migrations/` (0001–0004, 0006), `supabase/config.toml`, `checklists.json`, `HANDOFF.md`, `.env.sample`, `.gitignore`, `docs/`, `.planning/`. There is **no Python, no TypeScript, no package manifest, no Dockerfile** on disk. So for 20 of the 24 files below there is genuinely **no in-repo analog** — do not invent one. For those, the binding artifact is the **convention set** in §Shared Patterns, extracted from the SQL migrations and `.claude/CLAUDE.md`. Reach for `.planning/research/STACK.md` for library-level shape.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `supabase/migrations/0005_storage.sql` | migration | CRUD (policy) | `supabase/migrations/0004_rls_policies.sql` | **exact** |
| `supabase/config.toml` (modify: `[auth]`, CLI upgrade) | config | — | itself (in-place edit) | **exact** |
| `checklists.json` (modify: paths, OQ#2) | config/ledger | — | itself | **exact** |
| `.claude/CLAUDE.md` (modify: `apps/fastapi-backend` → `apps/api`+`apps/worker`) | config/doc | — | itself | **exact** |
| `docs/ops/rtt-baseline.md` | doc | — | `HANDOFF.md` §3 (verification-record style) | partial |
| `README.md` (root) | doc | — | none (`HANDOFF.md` tone only) | none |
| `pyproject.toml` (root, uv workspace) | config | — | none | **none** |
| `uv.lock` | config (generated) | — | none | **none** |
| `.python-version` | config | — | none | **none** |
| `packages/core/pyproject.toml` | config | — | none | **none** |
| `packages/core/src/nexuswiki_core/logging.py` | utility | transform (log pipeline) | none | **none** |
| `packages/core/tests/test_logging_redaction.py` | test | — | none | **none** |
| `apps/api/pyproject.toml` | config | — | none | **none** |
| `apps/api/src/api/main.py` (FastAPI + `lifespan`) | entrypoint | request-response | none | **none** |
| `apps/api/src/api/routers/health.py` (`/health`, `/health/ready`) | route | request-response | none | **none** |
| `apps/api/src/api/health_check.py` (DB-roundtrip adapter, 2s timeout) | service | request-response | none | **none** |
| `apps/api/src/api/__main__.py` (programmatic uvicorn, reads `$PORT`) | entrypoint | — | none | **none** |
| `apps/worker/pyproject.toml` | config | — | none | **none** |
| `apps/worker/src/worker/__main__.py` (startup + RTT probe + SIGTERM) | entrypoint | batch | none | **none** |
| `Dockerfile` (single, multistage, `CMD` defaults to api) | config | — | none | **none** |
| `.dockerignore` | config | — | `.gitignore` | partial |
| `railway.json` | config | — | none | **none** |
| `.pre-commit-config.yaml` | config | — | none | **none** |
| `.editorconfig` | config | — | none | **none** |
| `apps/dashboard/**` (Next 15.5.22+, Tailwind 4, TS strict, Vitest) | scaffold | — | none (`docs/design-systems/design-tokens.css` is a *consumable asset*, not a code analog) | **none** |

---

## Pattern Assignments

### `supabase/migrations/0005_storage.sql` (migration, policy CRUD) — the one exact analog

**Analog:** `supabase/migrations/0004_rls_policies.sql`
Secondary: `supabase/migrations/0003_jobs.sql` (function comment + revoke/grant block), `supabase/migrations/0001_core_schema.sql:107-110` (the path rule this migration promotes from comment to enforcement).

**1. File header pattern** — copy this shape verbatim (`0004_rls_policies.sql:1-24`, same in `0001`, `0003`, `0006`):

```sql
-- =============================================================================
-- NexusWiki 0004: 멀티테넌트 RLS 정책
--
-- 관련 태스크: P1-SEC-01
-- 설계 근거:  checklists.json > decisions.tenancy (team-first)
--             checklists.json > decisions.db_access (hybrid)
--
-- 0001~0003은 9개 테이블에 RLS를 "정책 없이" 켜 뒀습니다(= 전면 거부).
-- 이 파일이 그 위에 실제 정책을 부여합니다.
--
-- 전제
--   - anon/authenticated는 public 스키마 테이블에 이미 전권 GRANT를 가집니다
--     (Supabase 기본값). 즉 격리를 강제하는 것은 GRANT가 아니라 RLS 정책뿐입니다.
--   - service_role은 BYPASSRLS라 워커/마이그레이션은 이 파일의 영향을 받지 않습니다.
--     ⚠️ 그래서 워커 코드에는 workspace_id 필터를 반드시 명시해야 합니다 (P4-SEC-01).
--
-- 역할 등급:  owner(3) > editor(2) > viewer(1)
-- =============================================================================
```

Required fields for `0005`: `관련 태스크: P1-STO-01`; `설계 근거: checklists.json > decisions.original_file_retention`; a `전제` block; a `⚠️` note. Sections separated by `-- ---...` rules with numbered titles (`-- 1. 헬퍼 함수`).

**2. SECURITY DEFINER helper pattern** — the shape `public.storage_path_workspace(text)` must copy (`0004_rls_policies.sql:44-56`):

```sql
create or replace function public.is_workspace_member(ws_id uuid)
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select exists (
    select 1 from public.workspace_members m
    where m.workspace_id = ws_id
      and m.user_id = (select auth.uid())
  );
$$;
```

Note for D-05: `storage_path_workspace` is a **pure parser**, so it needs `immutable`/`stable` + `set search_path = public` but **not** `security definer` (it touches no table). Keep the `⚠️` comment explaining that direct `(storage.foldername(name))[1]::uuid` raises 22P02 (error, not denial) — mirroring the "무한 재귀 42P17" explanation style at `0004:30-41`.

**3. Comment + grant/revoke closing pattern** (`0004:88-95` and `0003_jobs.sql:221-229`):

```sql
comment on function public.is_workspace_member(uuid) is
  '호출자가 해당 워크스페이스 멤버인지. RLS 정책 전용 — 재귀 차단용 SECURITY DEFINER.';

grant execute on function public.is_workspace_member(uuid)     to authenticated;
grant execute on function public.workspace_role(uuid)          to authenticated;
grant execute on function public.has_workspace_role(uuid, text) to authenticated;
```

Restrictive form when service_role-only (`0003_jobs.sql:221-229`) — aligned columns:

```sql
revoke all on function public.claim_job(text, text[])                      from public, anon, authenticated;
grant execute on function public.claim_job(text, text[])                   to service_role;
```

`storage_path_workspace` is called from policies evaluated as `authenticated`, so it takes the `0004` grant form, not the `0003` one.

**4. Policy naming + role grading pattern (D-06)** — copy directly from `0004:213-223` (`raw_sources`, the closest semantic sibling):

```sql
create policy raw_sources_select_member on public.raw_sources
  for select to authenticated
  using (public.is_workspace_member(workspace_id));

create policy raw_sources_insert_editor on public.raw_sources
  for insert to authenticated
  with check (public.has_workspace_role(workspace_id, 'editor'));

create policy raw_sources_delete_owner on public.raw_sources
  for delete to authenticated
  using (public.has_workspace_role(workspace_id, 'owner'));
```

Policy name form: `<table>_<verb>_<minrole>`. For `storage.objects` the table part cannot be the table name (all buckets share it) — use the bucket: `sources_objects_select_member` / `_insert_editor` / `_delete_owner`, and every policy predicate must additionally pin `bucket_id = 'sources'`.

**5. "Absent policy = immutability" pattern (D-07)** — the exact precedent and its comment (`0004:206-212`). Reuse this rationale voice for the missing UPDATE policy:

```sql
-- UPDATE 정책이 없는 것은 의도입니다. "불변 원본 보존"이 제품의 약속이고
-- (decisions.original_file_retention), 파서 개선 시 재처리는 워커
-- (service_role, BYPASSRLS) 경로이므로 사용자 UPDATE는 필요 없습니다.
```

**6. The rule being promoted** — `0001_core_schema.sql:107-110`, currently comment-only:

```sql
  -- 원본 파일 보관 (decisions.original_file_retention).
  -- 경로 규칙: {workspace_id}/{raw_source_id}/{filename}
  -- 텍스트 직접 입력처럼 원본 파일이 없는 경우 NULL.
  storage_path text,
```

`0005` should carry a back-reference comment noting it now *enforces* what `0001:108` only *documented*.

**7. Idempotent seed pattern (D-08)** — `0006_seed_prompts.sql` is the seed analog; use `on conflict (id) do nothing` for the bucket insert, with `public = false` and `file_size_limit` = 50 MiB matching `supabase/config.toml:103` (`file_size_limit = "50MiB"`). Do **not** set `allowed_mime_types`.

---

### `supabase/config.toml` (config, modify)

**Analog:** itself. `[storage]` at line 100-114, `[auth]` at line 116+. Current state relevant to R10/D-08:

- `supabase/config.toml:103` — `file_size_limit = "50MiB"` (stack-wide; the bucket-level limit in `0005` should match, not contradict)
- `supabase/config.toml:109-114` — a **commented-out** `[storage.buckets.images]` example. Decide deliberately: the `sources` bucket is created by migration `0005` (portable to cloud), **not** by `config.toml` (local-only). Do not create it twice.
- `supabase/config.toml:116+` — `[auth]` currently has `site_url`, `jwt_expiry = 3600`, `enable_refresh_token_rotation = true`. R10 adds `[auth.email] enable_confirmations` and the 12-char minimum here **and** in the cloud dashboard (local-only change leaves production on defaults).

Style: the file is upstream-CLI-generated with **English** comments. This is the one file where Korean-comment house style does not apply — keep the generated comments untouched and add minimal annotation.

---

### `.dockerignore` (config)

**Analog:** `.gitignore` — partial match (same "exclusion list, Korean section banners" form):

```
# --- Supabase ---
supabase/.temp/

# --- Python (apps/fastapi-backend) ---
__pycache__/
.venv/
.ruff_cache/

# --- Node / Next.js (apps/dashboard) ---
node_modules/
.next/
```

Copy the `# --- 주제 ---` Korean banner convention. Per CONTEXT deferred note, `.dockerignore` must additionally exclude `apps/dashboard/`, `.planning/`, `docs/`, `supabase/` so a frontend or docs commit does not rebuild the Python image.

⚠️ `.gitignore` currently says `# --- Python (apps/fastapi-backend) ---` and `# --- Node / Next.js (apps/dashboard) ---`. The Python banner is stale under D-09 (`apps/api` + `apps/worker`) — update it in the same commit that updates `CLAUDE.md` and `checklists.json`.

---

### `docs/ops/rtt-baseline.md` (doc)

**Analog:** `HANDOFF.md` §3–3d — the repo's only precedent for "measurement written down as a verification record" (method + numbers + pass statements, Korean prose). `checklists.json` `verification_result` objects (`date` / `method` / `results[]`) are the structured twin; mirror those three fields as document headings.

Prohibition P4 makes this doc a grep target: it must contain no project ref, no `DATABASE_URL`, no key. Referring to the target as "Supabase `ap-southeast-1` 프로젝트" is sufficient.

---

### Files with no analog — what binds them instead

For every Python/TypeScript/Docker/Railway file in the classification table marked **none**, there is nothing in-repo to copy. The planner should treat §Shared Patterns below as the substitute contract, plus:

- `.env.sample` is the **key-name authority** for every settings module (`SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`, `ENVIRONMENT`, `LOG_LEVEL`, `NEXT_PUBLIC_*`). Its section-banner style (`# --- 1. Supabase ... ---`, Korean explanatory lines) is the pattern for any new sample/env file. Note the two known drifts: `LLM_MODEL=anthropic/claude-3.5-sonnet` vs PROJECT.md `claude-sonnet-4-6` (deferred), and `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` which will not match the Railway `$PORT`-driven api.
- `docs/design-systems/design-tokens.css` / `.json` are **consumable assets** for the Tailwind 4 theme, not code analogs. The CSS-variable naming (`--color-primary`, `--typography-*`, `--border-radius-*`, `--spacing-*`) and the numbered banner sectioning are already the project's design contract.
- `packages/core/src/nexuswiki_core/logging.py` has zero precedent. Its only in-repo tether is the `⚠️`-comment discipline: the redaction denylist (D-13) is exactly a "무시하면 보안이 조용히 깨지는" site and should carry a `⚠️` block explaining that a missing key in the denylist leaks silently.

---

## Shared Patterns

These are cross-cutting and apply to **every** new file in the phase.

### 1. Korean comments, English identifiers
**Source:** `.claude/CLAUDE.md` §Comment Conventions; every file in `supabase/migrations/`
**Apply to:** all new files
All comments, docstrings, commit messages, and Markdown are **Korean**. Identifiers, keywords, and filenames stay English/ASCII. This is house style, not accident. Exception: CLI-generated files (`supabase/config.toml`, Next.js scaffold output) keep their generated English comments.

### 2. File header cites task ID + decision key
**Source:** `0001:1-13`, `0003:1-21`, `0004:1-24`, `0006:1-11`
**Apply to:** `0005_storage.sql`, and (adapted to `"""docstring"""`) every new Python module

```sql
-- NexusWiki 000N: <주제>
--
-- 관련 태스크: P1-DB-03 (소비자는 P2-JOB-01 워커, 생산자는 P2-ING-01 수집 API)
-- 설계 근거:  checklists.json > decisions.job_queue
```

Two invariants: **name downstream consumers by task ID**, and **never restate a decision's reasoning — point at the ledger.** For Phase 1 Python files the decision keys live in `01-CONTEXT.md` (`D-01`…`D-14`); cite those (e.g. `설계 근거: 01-CONTEXT.md > D-03 (exec form CMD + 프로그래밍 방식 uvicorn — SIGTERM 전달)`).

### 3. `⚠️` marks a silent-failure footgun
**Source:** `0003_jobs.sql:186`, `0004_rls_policies.sql:17`, `:30`
**Apply to:** `0005` (22P02 cast), `Dockerfile` (PID 1 / SIGTERM, D-03), `railway.json` (env scope, prohibition P1), `logging.py` (redaction denylist, prohibition P2)
Every `⚠️` carries a "what breaks otherwise" sentence. Example (`0004:30-34`):

```sql
-- ⚠️ 이 함수들이 없으면 workspace_members의 정책이 "내가 이 워크스페이스
--    멤버인가"를 확인하려고 workspace_members를 다시 조회하면서 무한 재귀
--    (42P17 infinite recursion detected in policy)로 죽습니다.
```

### 4. Every non-obvious choice carries its counterfactual
**Source:** `0003_jobs.sql:31-36` (why `jobs.type` has no CHECK), `0001:36-38` (`on delete restrict`), `0004:159-162` (why `owner_id` is in the SELECT predicate)
**Apply to:** all new files
This is the single most distinctive habit in the codebase: the comment explains *what would break with the obvious alternative*, not what the line does. The Phase 1 decisions that most need this treatment — because their failure modes are silent — are D-01 (multistage targets break digest equality), D-03 (shell PID 1 swallows SIGTERM → jobs lost on redeploy), D-05 (direct cast → 500 not 403), D-07 (UPDATE policy would break `content_hash` idempotency).

### 5. Migration numbering = apply order
**Source:** `.claude/CLAUDE.md` §Naming Patterns; `.planning/codebase/STACK.md` §Known Stack Risks
**Apply to:** `0005_storage.sql`
`NNNN_snake_case_topic.sql`. `0005` is a reserved gap and must land **before** the first cloud `db push`; landing after `0006` diverges cloud order from local. This ordering constraint is a plan-sequencing fact, not just a naming one.

### 6. SQL style
**Source:** all of `supabase/migrations/`
Lowercase keywords (`create policy`, `on delete cascade`) — no uppercase anywhere. 2-space indent, one column per line, aligned inline comments, `-- ---` rule lines with numbered section titles. Enums are `text` + inline `check (col in (...))`, never Postgres `enum`. Function params take a `p_` prefix (`p_worker_id`), except RLS helpers which use a short domain name (`ws_id`, `min_role`) — `storage_path_workspace(p_name text)` should follow the `p_` form since it is not a membership helper.

### 7. Error-handling contract inherited by `apps/api`
**Source:** `.claude/CLAUDE.md` §Error Handling; `0004` policy semantics
**Apply to:** `apps/api` (and honored, not implemented, in Phase 1)
An RLS `USING` failure on UPDATE/DELETE returns **0 rows, not an exception** → API maps *affected rows == 0* to **403**. A `WITH CHECK` violation raises SQLSTATE `42501` → also 403. Phase 1 exposes no such route, but `/health/ready` establishes the precedent that **config errors fail fast at boot naming the specific missing key**, and that every outbound call has an explicit timeout (2s, D-11) rather than inheriting a library default.

### 8. Commit convention
**Source:** `.claude/CLAUDE.md` §Commit Conventions; `git log`
`type(scope): <주제> — <구체적 변경>`, Korean, quantified subject, **one task = one commit**. Migration commits lead with the number. Scope so far is `db`; this phase introduces `api`, `worker`, `web`, `ops`, `infra`. Examples in the existing log: `spec(phase-1): add SPEC.md for Bootstrap and Ground Truth — 10 requirements`, `docs(01): capture phase context`.

### 9. Ledger update is part of the work, not after it
**Source:** `.claude/CLAUDE.md` §Task Ledger Convention; `checklists.json`
Each task sets `status` (`pending` → `in_progress` → `done`) and records `verification_result` with `date`, `method`, `results[]`. Design divergences go under `deviations_from_plan` **in-file and in the ledger together**. Never restate rationale twice — link `decisions.<key>`. Phase 1 additionally must: resolve open question #2 (RTT), and rewrite `apps/fastapi-backend` → `apps/api`/`apps/worker` in both `checklists.json` and `.claude/CLAUDE.md`.

---

## No Analog Found

Planner should use `.planning/research/STACK.md` and library docs for these; there is nothing in-repo to copy from.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `pyproject.toml` (root + 3 members), `uv.lock`, `.python-version` | config | — | No Python packaging has ever existed in this repo |
| `packages/core/src/nexuswiki_core/logging.py` | utility | transform | No logging framework chosen in code; `.planning/codebase/STACK.md` marks it [PLANNED] |
| `packages/core/tests/test_logging_redaction.py` | test | — | No automated test suite exists — migration verification was ad hoc `psql` + `EXPLAIN ANALYZE` recorded in `HANDOFF.md` |
| `apps/api/**` (`main.py`, `routers/health.py`, `health_check.py`, `__main__.py`) | entrypoint/route/service | request-response | No FastAPI code exists; no HTTP layer of any kind |
| `apps/worker/src/worker/__main__.py` | entrypoint | batch | No worker code; job-queue *contract* exists in `0003_jobs.sql` but Phase 1 does not call it |
| `Dockerfile`, `railway.json` | config | — | No containerization or deploy config has ever existed |
| `.pre-commit-config.yaml`, `.editorconfig` | config | — | `.gitignore` reserves `.ruff_cache/`/`.mypy_cache/`, signaling intent, but no config file exists |
| `apps/dashboard/**` | scaffold | — | No `package.json`, no lockfile, no TS anywhere. Design tokens exist as assets only |
| `README.md` (root) | doc | — | No root README; `HANDOFF.md` is session state, not a project intro |

**Cross-cutting note for all of the above:** absence of an analog does **not** mean absence of constraint. §Shared Patterns 1–4 and 8–9 (Korean comments, task-ID+decision-key headers, `⚠️` footguns, counterfactual comments, commit form, ledger updates) apply to every one of these files and are the planner's substitute for a code analog.

---

## Metadata

**Analog search scope:** `supabase/migrations/` (5 files), `supabase/config.toml`, repo root (`.gitignore`, `.env.sample`, `checklists.json`, `HANDOFF.md`), `docs/`, `.claude/CLAUDE.md`
**Files scanned:** 11
**Pattern extraction date:** 2026-08-02
