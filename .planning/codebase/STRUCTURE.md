# Codebase Structure

**Analysis Date:** 2026-08-01

> The repository currently contains only the database layer, planning artifacts, and rendered docs. Application directories (`apps/`) do not exist yet. Sections are tagged **[EXISTS]** or **[PLANNED]**.

## Directory Layout

### Current [EXISTS]

```
NexusWiki/
├── supabase/
│   ├── config.toml              # Local stack config — ports moved to 544xx
│   ├── migrations/              # The entire implemented codebase
│   │   ├── 0001_core_schema.sql
│   │   ├── 0002_search_schema.sql
│   │   ├── 0003_jobs.sql
│   │   ├── 0004_rls_policies.sql
│   │   └── 0006_seed_prompts.sql   # 0005 reserved for Storage
│   ├── .branches/               # Supabase CLI state (not source)
│   └── .temp/                   # Supabase CLI state (not source)
├── docs/
│   ├── architecture/            # Rendered HTML architecture explainer
│   │   ├── index.html
│   │   └── 2026-08-01-explanation-nexuswiki-architecture.html
│   └── design-systems/          # Design tokens (CSS + JSON)
├── .planning/
│   └── codebase/                # GSD codebase map (this document)
├── .agents/                     # GSD tooling — skills, hooks, agent defs (not project code)
├── HANDOFF.md                   # Session handoff: state, deviations, traps
├── checklists.json              # 32 tasks + 10 decisions + 4 open questions
└── .gitignore
```

### Target [PLANNED] — per `checklists.json > P0-INIT-01..03`

```
NexusWiki/
├── apps/
│   ├── fastapi-backend/
│   │   ├── main.py              # API entrypoint (uvicorn, CORS, /health)
│   │   ├── worker.py            # Queue poll loop, graceful shutdown
│   │   ├── pyproject.toml
│   │   ├── .env.example
│   │   ├── Procfile             # Railway api/worker split
│   │   ├── app/
│   │   │   ├── config.py        # pydantic-settings Settings
│   │   │   ├── db.py            # user_client() / service_client() factories
│   │   │   ├── auth.py          # Supabase JWT verification
│   │   │   └── deps.py          # Workspace context dependency
│   │   ├── routers/             # ask.py, ingest, wiki, graph, jobs
│   │   ├── services/            # hybrid_search.py, jobs.py, tokenizer, llm
│   │   └── tests/               # test_hybrid_search.py, test_jobs.py, ...
│   └── dashboard/               # Next.js 15 App Router + Tailwind + TS strict
│       ├── package.json
│       ├── vitest.config.ts
│       ├── lib/supabase.ts
│       └── .env.example
├── supabase/                    # unchanged
├── railway.json
├── .pre-commit-config.yaml      # ruff + prettier
└── README.md
```

## Directory Purposes

**`supabase/migrations/`:** [EXISTS]
- Purpose: the schema is the product's contract — isolation, search channels, and queue semantics all live here
- Contains: forward-only, numbered SQL migrations with extensive Korean rationale comments
- Key files: `0001_core_schema.sql` (tenancy + Layer 1/2 tables), `0002_search_schema.sql` (5 search channels), `0003_jobs.sql` (queue + 4 functions), `0004_rls_policies.sql` (20+ policies, 3 helper functions, owner-protection trigger), `0006_seed_prompts.sql` (5 global templates)

**`supabase/`:** [EXISTS]
- Purpose: local dev stack definition
- Key file: `config.toml` — Postgres major 17, non-default 544xx ports, storage limit 50MiB

**`docs/architecture/`:** [EXISTS]
- Purpose: human-readable explanation of the DB and 5-way search design; `index.html` is the DB-access structure walkthrough, the dated file is the long-form explainer with a self-check quiz
- Generated: yes (rendered HTML)

**`docs/design-systems/`:** [EXISTS]
- Purpose: design tokens for the future dashboard
- Key files: `design-tokens.css`, `design-tokens.json`

**`.planning/`:** [EXISTS]
- Purpose: GSD planning artifacts; `codebase/` holds this map

**`.agents/`:** [EXISTS]
- Purpose: GSD framework installation (skills, hooks, agent definitions). **Not project source.** Do not modify while implementing product features.

## Key File Locations

**Entry Points:**
- `supabase/migrations/` — applied in filename order by `supabase db reset` / `db push`
- `supabase/config.toml` — local stack boot
- `apps/fastapi-backend/main.py` [PLANNED] — API
- `apps/fastapi-backend/worker.py` [PLANNED] — worker

**Configuration:**
- `supabase/config.toml` — ports, auth, storage, edge runtime
- `apps/fastapi-backend/.env.example` [PLANNED] — `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `OPENROUTER_API_KEY`, `LLM_MODEL`, `OPENAI_API_KEY`
- `apps/dashboard/.env.example` [PLANNED]

**Core Logic:**
- `supabase/migrations/0002_search_schema.sql` — the physical basis of all 5 retrieval channels
- `supabase/migrations/0003_jobs.sql` — queue function contract used by the worker
- `supabase/migrations/0004_rls_policies.sql` — the authorization model
- `apps/fastapi-backend/services/hybrid_search.py` [PLANNED] — RRF fusion + dual citation

**Planning / Context:**
- `HANDOFF.md` — current state, per-migration deviations, and the "traps you will hit later" list
- `checklists.json` — `decisions` (locked, do not re-litigate), `open_questions`, `phases[].tasks[]` with `target_files` and `verification`

**Testing:**
- No test directory exists. DB verification was performed ad hoc via `psql` in the Supabase container; results are recorded in `HANDOFF.md` §3–3d and `checklists.json`.
- `apps/fastapi-backend/tests/` and `apps/dashboard/*.test.ts` [PLANNED]

## Naming Conventions

**Migrations:**
- `NNNN_snake_case_topic.sql`, four-digit zero-padded, forward-only, gaps reserved intentionally (`0005` = Storage)
- Every file opens with a banner comment: title, related task ID (`P1-DB-02`), and design rationale pointing at `checklists.json > decisions.*`

**SQL identifiers:**
- Tables and columns: `snake_case`, tables plural (`workspaces`, `wiki_pages`, `source_chunks`)
- Indexes: `{table}_{columns}_idx` (`wiki_pages_workspace_category_idx`, `jobs_poll_idx`)
- Constraints: `{table}_{purpose}_{key|check|fkey}` (`source_chunks_source_index_key`, `wiki_links_no_self_link`, `wiki_links_from_fkey`)
- Policies: `{table}_{action}_{audience}` (`wiki_pages_insert_editor`, `jobs_select_member`, `prompt_templates_select_global_or_member`)
- Triggers: `{table}_{action}` (`workspaces_add_owner_member`, `workspace_members_protect_owner`)
- Functions: verb-first snake_case (`claim_job`, `reap_stale_jobs`, `is_workspace_member`, `has_workspace_role`)
- All SQL keywords lowercase

**Docs:**
- `docs/architecture/YYYY-MM-DD-explanation-{topic}.html`
- Root planning docs UPPERCASE (`HANDOFF.md`)

**Python / TS [PLANNED]:**
- Python `snake_case` modules; routers named after the resource (`routers/ask.py`)
- Next.js App Router conventions; `lib/` for shared clients

## Where to Add New Code

**New schema change:**
- Add `supabase/migrations/000N_topic.sql` with the standard banner comment and the deviation rationale
- Enable RLS in the same file that creates the table (deny-all until policies land)
- If the table is workspace-scoped, carry `workspace_id` and use a composite FK to `(id, workspace_id)` of its parent
- Verify with `supabase db reset`, then record results in `HANDOFF.md` and flip status in `checklists.json`

**New API endpoint [PLANNED]:**
- Router: `apps/fastapi-backend/routers/{resource}.py`
- Business logic: `apps/fastapi-backend/services/{domain}.py`
- Inject `user_client(access_token)` — never `service_client()`
- Tests: `apps/fastapi-backend/tests/test_{domain}.py`

**New worker job type [PLANNED]:**
- Handler in `apps/fastapi-backend/services/`, registered in `worker.py`
- Must be idempotent (upsert on the documented unique keys) and must always filter `workspace_id` explicitly
- Unknown job types must go straight to `dead` with `last_error`

**New frontend surface [PLANNED]:**
- `apps/dashboard/app/` route segment; shared clients in `apps/dashboard/lib/`
- Style with tokens from `docs/design-systems/design-tokens.css`

**New prompt template:**
- Migration seed like `supabase/migrations/0006_seed_prompts.sql`, `workspace_id IS NULL` for global
- Placeholders are `{{name}}`; `ask` uses `{{question}} {{wiki_context}} {{source_context}}`, `compile` uses `{{source_title}} {{source_type}} {{existing_slugs}} {{source_content}}`
- Seeds must be idempotent — re-running the file must not change row counts

## Special Directories

**`.agents/`:**
- Purpose: GSD framework install (skills, hooks, agents, scripts)
- Generated: yes
- Committed: currently untracked

**`supabase/.branches/`, `supabase/.temp/`:**
- Purpose: Supabase CLI local state
- Generated: yes
- Committed: no

**`.planning/`:**
- Purpose: GSD planning + codebase map output
- Generated: yes (by GSD commands)

**`docs/`:**
- Purpose: rendered explainers and design tokens
- Generated: yes (HTML is authored output, not built from source in-repo)
- Committed: currently untracked

## Local Environment Notes

- Ports are **not** Supabase defaults: API `54421`, DB `54422`, Studio `54423`, Inbucket `54424`, Analytics `54427`, Pooler `54429`, shadow `54420`. Tutorials using `54321`/`54322` will hit the unrelated `zettlink` stack on this machine.
- `psql` is not installed locally: `docker exec -it supabase_db_NexusWiki psql -U postgres -d postgres`
- Supabase CLI 2.33.2 — do not upgrade until Phase 1 closes (`config.toml` schema may change)
- No cloud Supabase project exists yet; finish `0005_storage.sql` before the first cloud push

---

*Structure analysis: 2026-08-01*
