# External Integrations

**Analysis Date:** 2026-08-01

> **Implemented vs Planned.** The only integration wired up in code today is **Supabase (local Docker stack)** through `supabase/config.toml` and the SQL migrations. Every entry marked **[PLANNED]** is specified in `HANDOFF.md` / `checklists.json` but has no code in this repository — there is no application source tree yet.

## APIs & External Services

**LLM (generation) — [PLANNED], task `P2-LLM-01`:**
- **OpenRouter** — all wiki compilation and Ask answers route through it
  - SDK/Client: plain HTTP (no SDK committed)
  - Auth: `OPENROUTER_API_KEY`
  - Model: env `LLM_MODEL`, default `claude-sonnet-4-6`
  - **Open question:** the real OpenRouter slug is unverified (assumed `anthropic/claude-sonnet-4.6`) — confirm before starting `P2-LLM-01`
  - Constraint: no Anthropic-native `output_config.format` and no prompt caching. Structured output is enforced by prompt-embedded JSON schema + Pydantic validation + up to 3 error-feedback retries.

**Embeddings — [PLANNED], task `P2-EMB-01`:**
- **OpenAI `text-embedding-3-small`** (1536 dims — matches `extensions.vector(1536)` in `supabase/migrations/0002_search_schema.sql:77,138`)
  - Auth: `OPENAI_API_KEY`
  - Requirements: batched calls, rate-limit backoff on 429, resumable on partial failure

**Content ingestion — [PLANNED], task `P2-ING-01` / `P2-ING-02`:**
- **Arbitrary user-supplied URLs** fetched and parsed (HTML), plus PDF (`pypdf`), Markdown, TXT
  - SSRF guard is specified: private ranges such as `http://169.254.169.254` must be rejected with 400

**Studio-side (implemented, dev-only):**
- `supabase/config.toml:86` — `openai_api_key = "env(OPENAI_API_KEY)"` for Supabase Studio's AI assistant. Local convenience only; unrelated to the embedding pipeline.

## Data Storage

**Databases (implemented):**
- **Supabase PostgreSQL 17**
  - Local connection: `postgresql://postgres:postgres@127.0.0.1:54422/postgres` (dev-only default credentials)
  - Cloud project: **not created yet** — deferred until `P0-INIT-04`
  - Client: **[PLANNED]** `supabase-py` with two factories (see Authentication below); migrations applied by Supabase CLI
  - Schema: 9 tables — `workspaces`, `workspace_members`, `raw_sources`, `wiki_pages`, `prompt_templates` (`0001`), `source_chunks`, `wiki_embeddings`, `wiki_links` (`0002`), `jobs` (`0003`)
  - Extension: `pgvector` in the `extensions` schema (`0002_search_schema.sql:30`)

**Vector search (implemented):**
- pgvector HNSW cosine indexes on `source_chunks.embedding` and `wiki_embeddings.embedding`
- Query-side requirements recorded in `HANDOFF.md` §5: always pass `where workspace_id = $1` explicitly **and** `set local hnsw.iterative_scan = strict_order`, otherwise HNSW post-filtering (including the RLS predicate itself) silently returns fewer than `k` rows

**Lexical search (implemented):**
- App-layer **bigram tokenizer → `tsvector('simple', …)`** on `wiki_pages.search_tsv` and `source_chunks.search_tsv`, GIN-indexed. Chosen because Postgres has no Korean morphological analyzer and `pg_bigm`/`pgroonga` are unavailable on Supabase.
- `tsv_tokenizer_version smallint` on both tables lets a tokenizer swap target only stale rows for reindex
- Query side must use `phraseto_tsquery('simple', bigram(q))` — raw bigrams into `to_tsquery` are a syntax error, and `plainto_tsquery` produces order-insensitive false positives

**File Storage:**
- **Supabase Storage** — enabled in `supabase/config.toml` (`file_size_limit = "50MiB"`), but **no buckets or policies exist yet**. That is task `P1-STO-01` / migration `0005_storage.sql`, currently the only outstanding schema work.
- Purpose: honor the "immutable original preservation" promise and enable reprocessing after parser improvements. Enforced at the DB level too — `raw_sources` has **no UPDATE policy** at all.
- S3 protocol config in `config.toml` references `S3_HOST`, `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` by env reference.

**Caching:**
- None. No Redis, no external cache. Prompt caching is explicitly unavailable via OpenRouter.

**Graph store:**
- **Deliberately none.** Neo4j was evaluated and rejected (GDS not on the Aura base tier; no traversal advantage at 10³–10⁴ pages; Neo4j has no RLS, so tenant isolation would move into app code). Replaced by the `wiki_links` table + recursive CTE, which serves as search channel 5.

## Authentication & Identity

**Auth Provider:**
- **Supabase Auth (GoTrue)** — enabled in `supabase/config.toml`
  - JWT expiry 3600s, refresh-token rotation on, reuse interval 10s
  - Email signup enabled, confirmations **disabled** (local dev posture), minimum password length 6, no password complexity requirement
  - Anonymous sign-ins disabled, manual account linking disabled
  - MFA (TOTP / phone / WebAuthn) all disabled
  - No external OAuth provider is enabled; Apple secret is stubbed by env reference only
  - `site_url = http://127.0.0.1:3000`, redirect allowlist `https://127.0.0.1:3000`
  - Local email capture via Inbucket at `http://127.0.0.1:54424`

**Authorization (implemented — this is the load-bearing integration):**
- **RLS on all 9 tables** — `supabase/migrations/0004_rls_policies.sql`, 38/38 isolation cases verified
- Helper functions `is_workspace_member(ws_id)`, `workspace_role(ws_id)`, `has_workspace_role(ws_id, min_role)` are `security definer stable set search_path = public` — required to break the `workspace_members` self-reference infinite recursion
- `protect_owner_membership` trigger blocks an owner from deleting/demoting/reassigning their own membership row
- Baseline rule: member = SELECT, editor = INSERT/UPDATE, owner = DELETE. Deviations: `workspaces` UPDATE and all `workspace_members` writes are owner-only (privilege-escalation vectors); `source_chunks` / `wiki_embeddings` / `wiki_links` / `jobs` are read-only to users (worker-owned data — an editor inserting fake `source_chunks` would forge the source side of a dual citation); `raw_sources` has no UPDATE policy.

**DB access model (hybrid) — [PLANNED] client factories, `P0-INIT-02`:**
```text
user_client(access_token)   requester JWT  → RLS enforced  → all user request paths
service_client()            service_role   → BYPASSRLS     → worker + migrations only
```
Using `service_client()` on a user request path voids the entire isolation layer. Worker code must always name `workspace_id` explicitly. Keep the two factories in separate files.

**API-layer contract:** a `USING`-clause rejection returns **0 rows, not an error**. Map "0 rows affected" to HTTP 403. Only `WITH CHECK` violations surface as SQLSTATE `42501`.

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry, no APM, no configuration for either.

**Logs:**
- Supabase Analytics container on port 54427 (local defaults only)
- **[PLANNED]** structured logging in the FastAPI settings module (`P0-INIT-02`); LLM/embedding cost guardrails and observability are task `P4-OPS-01`

## CI/CD & Deployment

**Hosting:**
- **[PLANNED] Railway** — `api` (web) + `worker` (resident) as two services in one project, with a Usage Limit to cap cost runaway
- **[PLANNED] Vercel** — Next.js dashboard
- **[PLANNED] Supabase Cloud** — Seoul region recommended

**CI Pipeline:**
- **None.** No `.github/` directory, no workflow files, no `railway.json`, no `Procfile` in the repo.
- **[PLANNED]** GitHub-linked auto-deploy on Railway (`P0-INIT-04`)

## Environment Configuration

**Referenced env vars (implemented, in `supabase/config.toml`):**
- `OPENAI_API_KEY` (Studio AI)
- `SUPABASE_AUTH_SMS_TWILIO_AUTH_TOKEN`, `SUPABASE_AUTH_EXTERNAL_APPLE_SECRET`
- `S3_HOST`, `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`

**[PLANNED] application env vars (`P0-INIT-02`):**
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `OPENROUTER_API_KEY`, `LLM_MODEL`, `OPENAI_API_KEY`
- Requirement: missing keys must fail fast at boot, naming exactly which key is absent; every key in `.env.example` must exist in `config.py`

**Secrets location:**
- No secret files are committed. `.gitignore` covers `.env`, `.env.*` (with a `!.env.example` exception), and `supabase/.env`. `config.toml` uses `env(...)` references exclusively.
- Local Postgres credentials are the Supabase dev defaults (`postgres:postgres`) and must not be reused in cloud.

## Webhooks & Callbacks

**Incoming:**
- None. Auth hooks (`before_user_created`, `custom_access_token`) are present but commented out in `supabase/config.toml`.

**Outgoing:**
- None implemented. The worker polls `claim_job` rather than receiving pushes — there is no callback surface by design.

## Job Queue Contract (implemented, `supabase/migrations/0003_jobs.sql`)

Consumers must use the four functions; **never `UPDATE jobs` directly** — lock-consistency CHECK and `attempts` accounting live inside them.

```sql
claim_job(worker_id, types[])                  -- SKIP LOCKED; 0 rows if none
complete_job(job_id)                           -- → succeeded
fail_job(job_id, error, backoff, max_backoff)  -- → failed + backoff, or dead
reap_stale_jobs(timeout)                       -- lock timeout → back to queued
```

`failed` means "will retry after backoff"; `dead` is the only human-attention terminal state. Delivery is **at-least-once** — if the reap timeout (default 15 min) is shorter than a real LLM compile, a live worker's job gets stolen and processed twice. All handlers must be idempotent via the three unique keys in `0002`: `(workspace_id, slug)`, `(raw_source_id, chunk_index)`, `(wiki_id, chunk_index)`.

## Prompt Template Contract (implemented, `supabase/migrations/0006_seed_prompts.sql`)

Five global templates (`workspace_id IS NULL`): 1 `compile` + 4 `ask`.

- Placeholders are `{{double_brace}}`. **Do not use `str.format`** — injected markdown/code/JSON contains single braces and will raise `KeyError` or corrupt content. Use plain string replacement.
- `ask` variables: `{{question}}`, `{{wiki_context}}`, `{{source_context}}`
- `compile` variables: `{{source_title}}`, `{{source_type}}`, `{{existing_slugs}}`, `{{source_content}}`
- The context assembler **must** prefix each chunk with a citation anchor — `[[wiki:slug]]` for wiki chunks, `[[src:chunk_id]]` for source chunks. Without anchors the model has nothing to cite and dual citation silently collapses.
- `compile` output enum values are aligned with the CHECK constraints in `0001`; drift means Pydantic passes and the INSERT fails.

---

*Integration audit: 2026-08-01*
