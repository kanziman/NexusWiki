# Technology Stack

**Analysis Date:** 2026-08-01

> **Implemented vs Planned.** Today this repository contains **only** a Supabase/PostgreSQL data layer (5 SQL migrations) plus planning artifacts. There is no application source code, no `package.json`, and no `pyproject.toml` on disk. Everything marked **[PLANNED]** comes from `HANDOFF.md` and `checklists.json` and does not yet exist in the repo.

## Languages

**Primary:**
- **SQL (PostgreSQL 17 dialect)** — the entire implemented codebase. `supabase/migrations/0001_core_schema.sql`, `0002_search_schema.sql`, `0003_jobs.sql`, `0004_rls_policies.sql`, `0006_seed_prompts.sql` (1,288 lines total)
- **TOML** — local stack configuration. `supabase/config.toml`
- **JSON** — task/decision ledger. `checklists.json`
- **Markdown** — session handoff. `HANDOFF.md`

**[PLANNED] Secondary:**
- **Python** (FastAPI API + queue worker) — `apps/fastapi-backend/` (task `P0-INIT-02`)
- **TypeScript** (Next.js 15 dashboard, `strict` mode) — `apps/dashboard/` (task `P0-INIT-03`)

## Runtime

**Environment (implemented):**
- **PostgreSQL 17** — `major_version = 17` in `supabase/config.toml:32`
- **Supabase local stack via Docker** — containers named `supabase_*_NexusWiki`
- **Supabase CLI 2.33.2** (upstream latest 2.111.0; upgrade deliberately deferred until Phase 1 closes — `config.toml` schema may change)

**[PLANNED]:**
- Python 3.x runtime for `api` + `worker` services
- Node.js runtime for the Next.js dashboard

**Package Manager:**
- None present at repo root — no `package.json`, no lockfile, no `pyproject.toml`
- **[PLANNED]** `uv` or `poetry` for Python (`P0-INIT-02`); `pnpm` for the dashboard (`P0-INIT-03`)

## Frameworks

**Core (implemented):**
- **Supabase platform** — Postgres + PostgREST + GoTrue Auth + Storage + Realtime, all configured in `supabase/config.toml`
- **PostgREST** — auto-exposed API over `public` and `graphql_public` schemas (`config.toml:11`), `max_rows = 1000`

**[PLANNED] Core:**
- **FastAPI** — HTTP API layer (`P0-INIT-02`)
- **Pydantic / pydantic-settings** — settings + LLM structured-output validation with 3-attempt retry (`decisions.llm.structured_output`)
- **Next.js 15 (App Router)** + **Tailwind CSS** — dashboard (`P0-INIT-03`)
- **Cytoscape** — knowledge graph canvas (`P3-UI-03`)

**Testing:**
- **Implemented:** none as automated suites. Migration verification was performed ad hoc via `psql` + `EXPLAIN ANALYZE` inside the DB container; results are recorded in `HANDOFF.md` §3–3d and `checklists.json` task `verification` fields.
- **[PLANNED]** `pytest` for the Python backend; **Vitest + Testing Library** for the dashboard (`P0-INIT-03`)

**Build/Dev (implemented):**
- **Supabase CLI** — `supabase start`, `supabase db reset`, `supabase stop`
- **Docker Desktop** — required host dependency for the local stack

**[PLANNED] Build/Dev:**
- `pre-commit` running `ruff` (Python) + `prettier` (TS) — `P0-INIT-01`
- `.editorconfig`, root `README.md` — `P0-INIT-01`

## Key Dependencies

**Critical (implemented):**
- **pgvector** (`vector` extension, local v0.8.0) — installed into the `extensions` schema at `supabase/migrations/0002_search_schema.sql:30`. All references are schema-qualified (`extensions.vector(1536)`, `extensions.vector_cosine_ops`) so behavior does not depend on the executing role's `search_path`.
- **pgcrypto / `gen_random_uuid()`** — UUID primary keys across all 9 tables
- **HNSW indexes** — `source_chunks_embedding_idx`, `wiki_embeddings_embedding_idx` (cosine)
- **GIN tsvector indexes** — `wiki_pages_search_tsv_idx`, `source_chunks_search_tsv_idx` over app-generated bigram `tsvector('simple', …)`

**[PLANNED] Critical:**
- `httpx`-style HTTP client for OpenRouter + OpenAI embeddings
- `pypdf` for PDF text extraction (`P2-ING-02`)

**Infrastructure (implemented):**
- Postgres job queue in-database: `jobs` table + `claim_job` / `complete_job` / `fail_job` / `reap_stale_jobs`, `FOR UPDATE SKIP LOCKED` (`supabase/migrations/0003_jobs.sql`). `EXECUTE` revoked from `anon` and `authenticated`; `service_role` only.

## Configuration

**Environment (implemented):**
- `supabase/config.toml` is the only committed config. It reads secrets by reference, never by value: `OPENAI_API_KEY` (Studio AI, line 86), `SUPABASE_AUTH_SMS_TWILIO_AUTH_TOKEN`, `SUPABASE_AUTH_EXTERNAL_APPLE_SECRET`, `S3_HOST` / `S3_REGION` / `S3_ACCESS_KEY` / `S3_SECRET_KEY`.
- No `.env` or `.env.example` exists on disk. `.gitignore` excludes `.env`, `.env.*` (allowing `.env.example`) and `supabase/.env`.

**Non-default local ports** — a separate `zettlink` Supabase stack permanently occupies the default 543xx range on this machine, so NexusWiki was moved to 544xx:

| Service | URL / Port |
|---|---|
| API | `http://127.0.0.1:54421` |
| DB | `postgresql://…@127.0.0.1:54422/postgres` |
| Studio | `http://127.0.0.1:54423` |
| Inbucket | `http://127.0.0.1:54424` |
| Analytics | `54427` |
| Pooler (disabled) | `54429` |
| Shadow DB | `54420` |

Using `54321`/`54322` from any tutorial connects to the **wrong project's** database.

**[PLANNED] required env vars** (`P0-INIT-02`): `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `OPENROUTER_API_KEY`, `LLM_MODEL`, `OPENAI_API_KEY`.

**Build:**
- Implemented: `supabase/config.toml` only
- **[PLANNED]** `apps/fastapi-backend/pyproject.toml`, `apps/dashboard/package.json`, `apps/dashboard/vitest.config.ts`, `railway.json`, `apps/fastapi-backend/Procfile`

## Platform Requirements

**Development:**
- Docker Desktop (Docker engine has crashed once here — symptom is HTTP 500 with `apiproxy: connection refused`; fix is restarting Docker Desktop)
- Supabase CLI 2.33.2
- No local `psql` — use `docker exec -it supabase_db_NexusWiki psql -U postgres -d postgres`
- Disk pressure noted: 94% used, `Docker.raw` at 61GB

**Production:**
- **Supabase Cloud** — project **not yet created**; recommended region Northeast Asia (Seoul)
- **[PLANNED] Railway** — one project, two services (`api` web + `worker` resident). Hobby $5/mo is billed per workspace, not per service; CPU-actual billing suits LLM-wait workers.
- **[PLANNED] Vercel** — frontend hosting
- Alternatives evaluated and rejected: Fly.io (~$6.5/mo), Render ($14/mo fixed)

## Known Stack Risks

- `0005` is a **gap in the migration sequence**, reserved for `P1-STO-01` (Storage buckets). Local `db reset` applies by filename order so it is harmless today, but adding `0005` *after* pushing `0006` to a cloud project breaks ordering. Must land before `P0-INIT-04`.
- OpenRouter routing forfeits Anthropic native prompt caching and `output_config.format`; compiler cost scales linearly with source count (revisit in `P4-OPS-01`).

---

*Stack analysis: 2026-08-01*
