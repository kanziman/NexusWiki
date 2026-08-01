# Stack Research

**Domain:** Multi-tenant "Living Wiki" SaaS — LLM source→wiki compilation + 5-channel hybrid retrieval with dual citations. Application layer (FastAPI API + resident worker + Next.js 15 dashboard) on top of an already-implemented Supabase/PG17 data layer.
**Researched:** 2026-08-01
**Confidence:** HIGH on versions (read directly from the PyPI/npm registry JSON APIs on 2026-08-01), MEDIUM on patterns/config (official docs via fetch), LOW→MEDIUM on comparative claims (web search, cross-checked where noted).

> **Scope guard.** The Supabase/PostgreSQL 17 data layer is Validated and out of scope. Nothing below proposes schema changes. Locked decisions (OpenRouter, prompt+Pydantic+3 retries, OpenAI 1536-d embeddings, app-layer bigram tokenization, Postgres `jobs` queue, hybrid JWT/service_role DB access, no graph DB, Railway+Vercel+Supabase Cloud) are treated as given; where one carries a cost, the cost is stated, not the alternative.

---

## Three findings that change the plan

Read these before the tables. Each contradicts something currently written in `checklists.json` / `.planning/codebase/STACK.md`.

### 1. `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_KEY` are the wrong env var names for a project created today

Supabase replaced `anon` / `service_role` API keys with **publishable** (`sb_publishable_…`) and **secret** (`sb_secret_…`) keys. Timeline: full launch July 2025, **new projects stopped receiving legacy keys in November 2025**, monthly nag from March 2026, legacy keys permanently deleted late 2026.

The NexusWiki Supabase Cloud project **has not been created yet**. When you create it, it will only issue publishable/secret keys. Planning around `SUPABASE_ANON_KEY` guarantees a rename before first deploy.

The Postgres role mapping is unchanged, so **no RLS work is invalidated**: publishable → `anon` (or `authenticated` once a user JWT is present), secret → `service_role` with `BYPASSRLS`. Only the names and the header rules change (publishable/secret keys go in the `apikey` header; they cannot be sent as `Authorization: Bearer` unless the two values are identical).

| Old planned name | Use this instead |
|---|---|
| `SUPABASE_ANON_KEY` | `SUPABASE_PUBLISHABLE_KEY` / `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` |
| `SUPABASE_SERVICE_KEY` | `SUPABASE_SECRET_KEY` (worker + migrations only) |

Related: Supabase Auth now issues **asymmetrically signed** JWTs (ES256 on NIST P-256, or RS256) published at `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json`. The shared HS256 secret still works but is explicitly "not recommended for production." This makes local, zero-network JWT verification in FastAPI the correct pattern — see §1.7.

*Confidence: HIGH (supabase.com/docs, two independent doc pages).*

### 2. Put Supabase Cloud in **Singapore**, not Seoul

`checklists.json` open question #2 is the Supabase/Railway region pairing. It resolves cleanly:

- **Railway has no Seoul or Tokyo region.** The full list is `us-west2`, `us-east4-eqdc4a`, `europe-west4-drams3a`, `asia-southeast1-eqsg3a` (Singapore). Singapore is the only APAC option.
- Supabase offers both Northeast Asia (Seoul) and Southeast Asia (Singapore).

A Seoul DB + Singapore compute pairing costs ~60–80 ms **per database round trip**. The 5-channel hybrid search issues multiple round trips per Ask, and the worker issues many per job — that latency multiplies. Co-locating in Singapore makes DB RTT ~1–2 ms and moves the geographic penalty to a **single** browser→API hop that Vercel's edge already partly absorbs.

**Decision: Supabase region = Southeast Asia (Singapore) `ap-southeast-1`; Railway region = `asia-southeast1-eqsg3a`.** Region is permanent per Supabase project — get this right on first creation.

*Confidence: HIGH on the region lists (official docs); MEDIUM on the exact RTT figures (geographic estimate, not measured — the P0 deploy task should measure it).*

### 3. Next.js: pin `15.5.22`, and never an earlier 15.x

`next@latest` on npm is **16.2.12**. The 15.x line is still actively backported (`backport` dist-tag = 15.5.22, published the same minute as 16.2.12 on 2026-07-25). PROJECT.md locks Next 15, so pin **15.5.22** — every current `@supabase/ssr` guide targets 15.x App Router and the ecosystem is settled there.

**Hard floor: ≥ 15.2.3.** Next.js 15.0–15.2.2 carry **CVE-2025-29927**, an authorization bypass where a spoofed `x-middleware-subrequest` header skips middleware entirely. This app's auth gate *is* middleware (`updateSession`), so that CVE is a full tenant-isolation bypass in this design. Do not scaffold from a stale tutorial's `next@15.0.x`.

Cost of staying on 15: new framework features land in 16 only. Budget a Next 16 upgrade as a post-v1 chore; React peer range is identical (`^18.2.0 || ^19.0.0`) so it is not a rewrite.

*Confidence: HIGH (npm registry dist-tags + time map; CVE fixed-version list cross-confirmed across JFrog/Datadog/OffSec).*

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **uv** | 0.12.1 | Python packaging, venv, workspace | Railway's Railpack **natively detects `pyproject.toml` + `uv.lock`** and installs uv automatically (default build `uv sync --locked --no-dev --no-install-project`). Workspaces give api + worker + shared `packages/core` **one lockfile**, which is the only way to guarantee the index-time and query-time bigram tokenizers are byte-identical. Poetry needs a custom build step on Railway and has no equivalent single-lock workspace. |
| **Python** | 3.13.x | Runtime | Railpack's default is 3.13.2. Every wheel this stack needs (asyncpg 0.31, cryptography 50, pypdf 6.14) ships prebuilt for 3.13. 3.14 is GA but buys nothing here and risks source builds. Pin with `.python-version` + `requires-python = ">=3.13,<3.14"`. |
| **FastAPI** | 0.141.1 | HTTP API | Requires ≥3.10. Use the **`lifespan` async context manager** (create the asyncpg pool, the JWKS client, and the two `AsyncOpenAI` clients once) — `@app.on_event` is deprecated. Per-request resources go through `Depends` with `yield`. |
| **Uvicorn** | 0.52.0 | ASGI server | `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. One process; Railway scales by replica, not by worker fork. Do **not** put Gunicorn in front — the extra process layer breaks Railway's SIGTERM drain and doubles idle memory on a $5/mo box. |
| **asyncpg** | 0.31.0 | **Primary DB driver for both api and worker** | See §1.3. This is the highest-leverage choice in the doc. |
| **Pydantic** | 2.13.4 | Models + LLM structured-output validation | The locked "prompt + Pydantic + 3 retries" contract runs on `model_validate_json` → `ValidationError` → re-prompt with the serialized error. |
| **pydantic-settings** | 2.14.2 | Config | One `Settings(BaseSettings)` in `packages/core`, `SettingsConfigDict(env_file=".env", extra="ignore")`, accessed via `@lru_cache`. Both api and worker import the same class so a missing var fails fast at boot on both services. |
| **openai** | 2.52.0 | OpenRouter **and** OpenAI embeddings | Two `AsyncOpenAI` instances: one with `base_url="https://openrouter.ai/api/v1"` + `api_key=OPENROUTER_API_KEY` + `default_headers={"HTTP-Referer","X-Title"}`, one default for `text-embedding-3-small` at `dimensions=1536`. Built-in `max_retries` already covers 429/5xx with jittered backoff, so the hand-rolled retry loop only has to handle *validation* failures. One SDK, one set of timeout semantics. |
| **httpx** | 0.28.1 | Fetching URL sources | Already a transitive dep of the openai SDK; make it direct for the URL ingest path. One shared `AsyncClient` in lifespan with `follow_redirects=True` and an explicit `timeout`. |
| **structlog** | 26.1.0 | Structured logging | See §1.8. |
| **PyJWT** + **cryptography** | 2.13.0 / 50.0.0 | Local JWT verification | `PyJWKClient` against the project JWKS URL; ES256 needs `cryptography`. Zero network calls per request after the first. |
| **pypdf** | 6.14.2 | PDF text extraction | **BSD-3.** See §1.5 — the license is the deciding factor, not the quality. |
| **Next.js** | 15.5.22 | Dashboard | Pinned; see finding #3. |
| **React** | 19.2.8 | UI | Peer of Next 15.5 (`^18.2.0 \|\| ^19.0.0`). |
| **@supabase/ssr** | 0.12.4 | Browser + server Supabase clients | Peer `@supabase/supabase-js ^2.111.0`. Current cookie contract is `getAll` / `setAll(cookiesToSet, headers)` — note the **second `headers` argument is new**; it carries `Cache-Control`/`Expires`/`Pragma` that must be applied to the response or a CDN can cache one tenant's session. |
| **@supabase/supabase-js** | 2.111.0 | Auth SDK | Auth only in the browser. Not used for data — data goes to FastAPI. |
| **Tailwind CSS** | 4.3.3 | Styling | v4 is CSS-first. Install `tailwindcss @tailwindcss/postcss postcss`; `postcss.config.mjs = { plugins: { "@tailwindcss/postcss": {} } }`; `@import "tailwindcss";` in `globals.css`. **No `tailwind.config.js`** — theme lives in `@theme {}`. |
| **cytoscape** | 3.34.0 | Knowledge canvas | Used **directly**, no React wrapper. See §3.5. |
| **Vitest** | 4.1.10 | Frontend tests | See §3.6, including the async-RSC limitation. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pgvector` (python) | 0.5.0 | Registers the `vector` type codec on asyncpg connections | Required on every pooled connection (`await register_vector(conn)` in the pool's `init=`) or embeddings come back as strings. |
| `orjson` | 3.11.9 | Fast JSON | structlog's JSON renderer; asyncpg jsonb codec; FastAPI `ORJSONResponse`. |
| `python-multipart` | 0.0.32 | Multipart parsing | Required by FastAPI for the file dropzone `UploadFile` endpoint. Easy to forget — the endpoint 500s without it. |
| `storage3` | 2.31.0 | Supabase Storage client | Only if you don't want to hand-roll the Storage REST calls. Pulled in transitively by `supabase`; installing it standalone avoids dragging in `realtime`/`gotrue`/`postgrest` you won't use. |
| `pytest` / `pytest-asyncio` / `pytest-cov` | 9.1.1 / 1.4.0 / 7.1.0 | Backend tests | `asyncio_mode = "auto"` in pyproject. |
| `respx` | 0.23.1 | Mock httpx/openai HTTP | Deterministic tests for the compiler retry loop without burning OpenRouter credits. |
| `tenacity` | 9.1.4 | Retry decorator | **Optional.** The openai SDK already retries transport errors and the Pydantic repair loop must be hand-written (it feeds the error back into the prompt). Add only if the URL-fetch path needs its own policy. |
| `trafilatura` | 2.2.0 | HTML → clean main text | For the URL ingest source type. Beats BeautifulSoup for boilerplate stripping and is what news/RAG pipelines standardize on. |
| `pymupdf4llm` | 1.28.0 | Better PDF → Markdown | **Only if** an Artifex commercial license is purchased or the product goes AGPL-compatible. See §1.5. |
| `docling` | 2.117.0 | OCR + table-structure PDF | Apache-2.0, handles scanned PDFs. Pulls torch — must live in a **separate** service/image if ever adopted. Not v1. |
| `@tanstack/react-query` | 5.101.4 | Client-side data + job polling | `refetchInterval` on job status + `invalidateQueries` after ingest is exactly the ingest→job→wiki loop. `swr@2.4.2` is the lighter alternative if you end up with <5 client queries. |
| `@types/cytoscape` | 3.31.0 | Cytoscape TS types | Cytoscape ships no types. |
| `cytoscape-fcose` | 2.2.0 | Force-directed layout | Best-quality compound-aware layout for a wiki link graph; `cose` (built-in) is noticeably worse at this node count. |
| `@testing-library/react` / `jest-dom` / `user-event` | 16.3.2 / 7.0.0 / 14.6.1 | Component tests | — |
| `jsdom` / `@vitejs/plugin-react` / `vite-tsconfig-paths` | 30.0.1 / 6.0.5 / 6.1.1 | Vitest env | Per the official Next.js Vitest guide. |
| `zod` | 4.4.3 | Frontend response validation | Validate the FastAPI dual-citation payload at the client boundary so a backend contract drift is a loud error, not a blank citation card. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `ruff` 0.16.1 | Python lint **+ format** | Replaces black + isort + flake8 in one binary. Config in root `[tool.ruff]`. |
| `prettier` 3.9.6 | TS/TSX/MD/JSON format | Scope to `apps/dashboard` via `.prettierignore` so it never touches Python-adjacent files. |
| `pre-commit` | Hook orchestration | `astral-sh/ruff-pre-commit` (`ruff-check --fix`, `ruff-format`) + a local node hook for prettier. |
| `pnpm` 11.18.0 | Dashboard package manager | Only one JS package — **no pnpm workspace, no Turborepo, no Nx.** |
| `TypeScript` **5.9.3** | Type checking | `typescript@latest` is now **7.0.2** (the Go-native rewrite, GA 2026-07-08). Pin **5.9.3**: `eslint-config-next`, the Vitest/Vite type plumbing, and most `@types/*` are still validated against 5.x, and TS 7 is 3 weeks old at time of writing. Revisit after v1. |
| Supabase CLI | Local stack | 2.33.2 installed, upstream 2.111.0. Upgrade deliberately deferred (per codebase map) — but **it must be upgraded before the first cloud `db push`**, and `0005` must land first. |
| Playwright | E2E | Required, not optional — Vitest cannot render async Server Components (§3.6). |

---

## 1. Python / FastAPI decisions

### 1.1 uv, not Poetry

| | uv 0.12.1 | Poetry |
|---|---|---|
| Railway build | auto-detected, zero config | needs a custom `buildCommand` / Dockerfile step |
| Monorepo | `[tool.uv.workspace]`, **one** `uv.lock` for all members | per-package locks or path deps |
| Speed | 10–100× resolve | slow |
| Toolchain fit | same vendor as ruff | separate |

Workspace root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = ["apps/api", "apps/worker", "packages/core"]
```

`uv run --package api …` / `uv sync --package worker` target one member from anywhere.

**Constraint to know:** a uv workspace enforces a **single intersected `requires-python`** across all members, and is explicitly the wrong tool when members have *conflicting* dependencies. Both are fine here — api and worker share ~90% of their deps by design.

*Confidence: HIGH (docs.astral.sh + railpack.com, cross-checked against Railway community answers).*

### 1.2 FastAPI async patterns

- **Lifespan, not `on_event`.** One `asynccontextmanager` creates: asyncpg pool, `PyJWKClient`, `AsyncOpenAI(openrouter)`, `AsyncOpenAI(openai)`, shared `httpx.AsyncClient`. Yield them; close in reverse.
- **Never `def` for a route that touches the DB.** A sync `def` route runs in a threadpool and cannot await the pool; you get silent serialization under load.
- **Blocking work stays out of the API.** `pypdf` parsing, embedding, LLM calls are CPU/IO-blocking and belong to the worker. The ingest endpoint's only job is: upload to Storage → insert `raw_sources` → enqueue job → return `202`. If any blocking call *must* run in-process, wrap it in `anyio.to_thread.run_sync`.
- **RLS zero-row rule.** Per PROJECT.md, a `USING`-blocked UPDATE/DELETE returns 0 rows with no error. Centralize this: one `execute_scoped()` helper that raises `HTTPException(403)` when `cur.rowcount == 0` on a mutation. Do not scatter the check.

### 1.3 asyncpg for the data path — not supabase-py

**Recommendation: `asyncpg` 0.31.0 for all database access in both api and worker. Use the `supabase`/`storage3` client only for Storage. Use Supabase Auth only in the browser.**

Three reasons, in order of weight:

**(a) `SET LOCAL` is non-negotiable and PostgREST cannot issue it.** PROJECT.md's performance constraint requires `set local hnsw.iterative_scan = strict_order` (pgvector 0.8+) because vector search is post-filtered by RLS. PostgREST has no mechanism for arbitrary session GUCs. Going through supabase-py means wrapping the entire 5-channel search in SQL functions — which pushes RRF fusion, the recursive CTE, and channel weighting into migrations, i.e. into the layer you just declared Validated and frozen.

**(b) supabase-py's per-request auth is stateful and unsafe under concurrency.** The common patterns (`client.auth.set_session(...)`, `client.postgrest.auth(token)`) **mutate a shared client object**. In a concurrent ASGI app, request A can overwrite request B's token between B's `auth()` call and B's `execute()`. That is a cross-tenant read, and RLS will happily authorize it because the DB sees the wrong-but-valid JWT. The safe variant — constructing a fresh `AsyncClient` per request — creates a new httpx connection pool per request. Neither is good.

**(c) asyncpg gives the exact PostgREST mechanism, explicitly.** Per request:

```python
async with pool.acquire() as conn:
    async with conn.transaction():
        await conn.execute(
            "select set_config('request.jwt.claims', $1, true),"
            "       set_config('role', 'authenticated', true)",
            json.dumps(claims),
        )
        await conn.execute("set local hnsw.iterative_scan = strict_order")
        ...
```

`is_local = true` scopes both to the transaction, so the connection returns to the pool as the base role. `auth.uid()` reads `request.jwt.claims->>'sub'`, so all 38 existing policies work unchanged. The worker uses a **separate pool** connected as the secret/`service_role` user and simply never calls `set_config`.

**Connection string — this is where it breaks in production.** Supabase direct connections (port 5432) are **IPv6-only** without the paid IPv4 add-on. Use the **Supavisor shared pooler in session mode, port 5432** — IPv4 on every tier, supports prepared statements, and is what the docs recommend for persistent servers. Do *not* use transaction mode (port 6543): it does not support prepared statements and asyncpg will fail unless you set `statement_cache_size=0`, which throws away asyncpg's main performance advantage.

**Cost of this choice, stated honestly:** you write SQL by hand and you own the mapping from rows to Pydantic models. That is ~200 lines of query modules. It is the right trade when the schema is already frozen and the queries are the product.

*Confidence: MEDIUM-HIGH. Connection/pooler facts are HIGH (supabase.com/docs). The `set_config` pattern is confirmed by Supabase's own discussions #30124 / #22482. The supabase-py concurrency hazard is inferred from the documented stateful API surface and community discussion #37052 — validate it with a concurrency test in P1 if you want certainty before committing.*

### 1.4 HTTP client

Use the **openai SDK for both providers**. OpenRouter is OpenAI-wire-compatible; `AsyncOpenAI(base_url="https://openrouter.ai/api/v1")` gets you connection pooling, timeouts, and 429/5xx retry-with-backoff for free, and `extra_body` passes OpenRouter's `provider` routing block through. Keep `httpx` as a direct dep for URL source fetching only.

**On structured output:** OpenRouter *does* now support `response_format: {type: "json_schema"}` — but only for models whose active provider advertises it, and a request to a model that doesn't support it **fails with an error rather than degrading**. The locked decision (prompt + Pydantic + 3 retries) stays, because `LLM_MODEL` is env-swappable and the retry loop must work for any model. If you later want the tighter path, treat `response_format` as an opportunistic optimization behind a per-model capability flag with the validation loop still underneath as the mandatory backstop — never as a replacement for it.

### 1.5 PDF: pypdf, and the reason is the license

| | pypdf 6.14.2 | PyMuPDF 1.28.0 | docling 2.117.0 |
|---|---|---|---|
| License | **BSD-3** | **AGPL-3.0** | Apache-2.0 |
| Speed | baseline | ~10–50× faster on digital text | slowest |
| Layout / tables | weak | good | best (preserves table structure) |
| Scanned PDFs | nothing | nothing | OCR, works |
| Install weight | pure Python | C ext | torch models |

**AGPL-3.0 is disqualifying for a hosted SaaS.** It reaches network users, so shipping PyMuPDF inside NexusWiki means either open-sourcing the service or buying an Artifex commercial license. That decision does not belong in a P2 ingest task.

The quality gap matters less here than in a typical RAG pipeline, because **the LLM compiler rewrites the prose anyway** — reading-order noise gets normalized during compilation in a way it never would in a chunk-and-embed-verbatim system. And the architecture already anticipates parser upgrades: `raw_sources` is immutable, originals live in Storage (`0005`), and re-parse is a designed path.

**Required guardrail:** pypdf silently returns empty strings for scanned/image PDFs. Add a post-extraction check — if `chars / page_count < ~50`, **fail the job** with a `needs_ocr` error code rather than ingesting an empty document. Without this, a user uploads a scanned PDF, the job succeeds, and they get an empty wiki with no explanation. That is the single most likely "product feels broken" bug in the ingest path.

*Confidence: HIGH on licenses and versions (PyPI metadata). MEDIUM on the speed/quality deltas (multiple benchmark blogs, consistent direction, unverified magnitudes).*

### 1.6 pydantic-settings

One `Settings` class in `packages/core/config.py`, imported by both services. Group by concern (`supabase_url`, `supabase_secret_key`, `database_url`, `openrouter_api_key`, `llm_model = "claude-sonnet-4-6"`, `openai_api_key`, `embedding_model`, `embedding_dimensions = 1536`, `worker_concurrency`, `tsv_tokenizer_version`). Use `SecretStr` for all keys so they can't be `repr()`'d into a log line. `extra="ignore"` because Railway injects `RAILWAY_*` vars into every service.

### 1.7 JWT verification

Verify **locally** with `PyJWT`'s `PyJWKClient` against `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json`, algorithms `["ES256", "RS256"]`, `audience="authenticated"`. Construct the client once in lifespan — it caches keys and handles rotation without a redeploy.

**Do not** call `supabase.auth.get_user(token)` per request: that is a network round trip to GoTrue on the hot path of every API call, and it defeats the entire point of asymmetric signing keys. Reserve it for the rare case where you need fresh server-side revocation checking.

The verified claims dict is exactly what goes into `set_config('request.jwt.claims', …)` in §1.3 — verify once, then hand it to Postgres.

### 1.8 structlog, not loguru

`structlog` 26.1.0 wins on one feature this app needs: **`structlog.contextvars.merge_contextvars`**. Bind `request_id`, `workspace_id`, `user_id` once in middleware (or `job_id`, `job_type`, `attempt` once in the worker loop) and every downstream log line carries them automatically — including from library code that never sees your logger. For a job queue where you debug by grepping one `job_id` across a compile→link→embed chain, that is the whole ballgame.

structlog also routes **uvicorn's and httpx's own stdlib loggers** through the same pipeline via `ProcessorFormatter`, so you get one JSON stream instead of two formats interleaved in Railway's log view. loguru is more ergonomic to start with but is a parallel sink system with no contextvars-native binding, so framework logs stay unstructured.

Config: `JSONRenderer` (orjson) in prod, `ConsoleRenderer(colors=True)` in dev, switched off `settings.env`.

*Confidence: MEDIUM (multiple 2026 practitioner guides converge; the contextvars claim is verified against structlog's own API).*

---

## 2. Worker process

### 2.1 Shape

Single process, single event loop, `asyncio.run(main())`. Roughly:

```
main()
├─ build settings, structlog, service_role asyncpg pool, LLM/embed clients
├─ stop = asyncio.Event()
├─ loop.add_signal_handler(SIGTERM, stop.set); same for SIGINT
├─ sem = asyncio.Semaphore(WORKER_CONCURRENCY)   # 2–4
├─ inflight: set[asyncio.Task] = set()
└─ while not stop.is_set():
     if len(inflight) >= CONCURRENCY: await first-completed; continue
     job = await claim_job(...)                   # existing SQL function
     if job is None: await wait_or_stop(backoff.next()); continue
     backoff.reset()
     t = create_task(run_job(job)); inflight.add(t); t.add_done_callback(inflight.discard)
   # drain
   await asyncio.wait(inflight, timeout=DRAIN_SECONDS)
   await pool.close()
```

**Four details that are easy to get wrong:**

1. **`loop.add_signal_handler`, not `signal.signal`.** The stdlib handler fires on an arbitrary thread and cannot safely touch the loop. `add_signal_handler` schedules on the loop and is what lets `stop.set()` unblock the sleep.
2. **Sleep on the event, not on the clock.** `await asyncio.wait_for(stop.wait(), timeout=delay)` — catching `TimeoutError` as "keep going." A plain `asyncio.sleep(15)` means SIGTERM waits up to 15 s before you even notice it.
3. **Full-jitter backoff on empty polls**, not fixed. `delay = random.uniform(0, min(cap, base * 2**n))` with `base=0.5s`, `cap=15s`. Fixed-interval pollers from N replicas synchronize and hammer the DB in lockstep; jitter is what makes `SKIP LOCKED` cheap.
4. **`reap_stale_jobs` is your real shutdown safety net, not `drainingSeconds`.** Railway's drain window is bounded; a compile job waiting on an LLM can exceed it. The queue is at-least-once by design and every handler must be idempotent (the three upsert keys exist for exactly this). Drain is best-effort; the reaper is the guarantee. **Verify** whether the `jobs` schema exposes a heartbeat column — if a job can legitimately run longer than the 15-minute reap timeout, it must touch that column periodically or the reaper will hand a still-running job to a second worker.

### 2.2 Concurrency model

`asyncio.Semaphore` + a task set, **not** `multiprocessing`, **not** a threadpool. Every unit of work here is IO-bound (LLM call, embedding call, Postgres round trip); one event loop with concurrency 2–4 saturates the useful throughput at a fraction of the memory. Railway bills CPU-actual, which is precisely why this design was chosen — an async worker parked on an LLM response bills near zero.

The one CPU-bound step is PDF parsing. Wrap it: `await anyio.to_thread.run_sync(parse_pdf, data)`. pypdf holds the GIL for parts of that, so keep the parse concurrency lower than the LLM concurrency if you see loop-lag warnings.

### 2.3 Libraries: write it, don't install it

| Don't install | Why | Write instead |
|---|---|---|
| **Celery** | Requires Redis/RabbitMQ — explicitly out of scope. Its own queue semantics duplicate and conflict with `claim_job`/`complete_job`/`fail_job`. Heavyweight, sync-first. | ~150 lines above |
| **arq / saq / RQ** | All Redis-backed. Same conflict. | — |
| **dramatiq** | Broker-based; its Postgres broker is a third-party plugin with its own schema. | — |
| **APScheduler** | Solves scheduling, not queue claiming. `reap_stale_jobs` cadence can be a simple `asyncio.create_task` timer loop. | ~15 lines |
| **procrastinate** | *Actually* a Postgres-native async queue and a genuine alternative — but it owns its own tables and job model. Migration `0003` already exists and is verified at 8 workers / 400 jobs. Adopting it means throwing that away. | — |
| **uvloop** | Marginal for an LLM-latency-dominated worker; adds a platform-specific wheel. | Optional, revisit if profiling says so |

The entire "worth pulling in" list for the worker is: **nothing beyond what the API already depends on.** That is the correct answer for a Postgres-native queue with ~150 lines of well-understood asyncio.

*Confidence: MEDIUM-HIGH. The asyncio patterns are standard and well-attested; the "don't add a queue library" conclusion follows directly from the locked queue decision.*

---

## 3. Next.js 15 App Router

### 3.1 Supabase auth — the four files

```
lib/supabase/client.ts     createBrowserClient(url, publishableKey)
lib/supabase/server.ts     createServerClient(...) with cookies {getAll, setAll}   [async, per-request]
lib/supabase/middleware.ts updateSession(request)
middleware.ts              export async function middleware(req) { return await updateSession(req) }
```

Non-negotiable rules from the current docs:

- **`setAll` now takes `(cookiesToSet, headers)`.** The `headers` object carries `Cache-Control` / `Expires` / `Pragma` and **must** be applied to the HTTP response. Skipping it lets a CDN cache a response containing one user's session. Older tutorials show a one-argument `setAll` — those are stale.
- **Never trust `getSession()` in server code.** Use **`getClaims()`**, which verifies the JWT signature against the published JWKS. `getSession()` reads the cookie without revalidation. (`getUser()` remains valid but costs a network round trip.)
- **Return `supabaseResponse` unmodified from middleware.** If you build a fresh `NextResponse` you drop the refreshed auth cookies and users get logged out at random. If you need to redirect, copy the cookies onto the redirect response.
- Keep `middleware.ts` thin — it runs on every matched request. Session refresh only; do authorization in Server Components / route handlers.
- `matcher` must exclude `_next/static`, `_next/image`, and image extensions, or you pay a Supabase call per asset.

Env: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (see finding #1). The **secret key never appears in the dashboard**, not even server-side — the frontend has no service_role path by design.

### 3.2 Data fetching against a JWT-scoped API

The dashboard talks to FastAPI, not to PostgREST. One helper:

```ts
// lib/api/server.ts — Server Components / Server Actions / Route Handlers
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();   // also validates
  const token = /* access token from the session cookie */;
  const res = await fetch(`${process.env.API_URL}${path}`, {
    ...init,
    headers: { ...init?.headers, Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json();
}
```

- **`cache: "no-store"` is mandatory on every tenant-scoped fetch.** Next 15 no longer caches `fetch` by default, but an explicit `no-store` documents intent and survives a future default flip. A cached cross-tenant response is the worst bug this product can have.
- Read paths (wiki page, source list, graph) → **Server Components** with `apiFetch`. No client JS, token never reaches the browser bundle.
- Interactive paths (Ask streaming, dropzone, job polling, workspace switch) → **Client Components** + TanStack Query, token supplied by `createBrowserClient`'s session.
- Job status polling: `useQuery({ refetchInterval: (q) => isTerminal(q.state.data?.status) ? false : 2000 })`.
- Ask streaming: server-side `ReadableStream` proxy through a Route Handler, or read the FastAPI SSE stream directly with the browser token. Prefer the Route Handler — it keeps `API_URL` private and lets you attach the request id.
- **Validate the dual-citation payload with `zod`** at the boundary. Dual citation is the Core Value; a silent shape drift that renders an empty citation card is the failure mode you cannot afford to ship.

### 3.3 Tailwind

```bash
pnpm add tailwindcss@4.3.3 @tailwindcss/postcss postcss
```

```js
// postcss.config.mjs
const config = { plugins: { "@tailwindcss/postcss": {} } };
export default config;
```

```css
/* app/globals.css */
@import "tailwindcss";
```

No `tailwind.config.js`, no `@tailwind base/components/utilities` (v3 syntax). Theme tokens go in `@theme { --color-…: …; }`.

### 3.4 (see §3.5)

### 3.5 Cytoscape: no wrapper

**Use `cytoscape@3.34.0` + `@types/cytoscape@3.31.0` directly. Do not install `react-cytoscapejs`.**

Evidence: `react-cytoscapejs` latest is **2.0.0, published 2022-09-02** — nearly four years stale. The repo (plotly) was last pushed 2025-01-27 with **45 open issues**, including a known Next.js failure (`Cannot use import statement outside a module` from the CJS/ESM boundary). Its peers are `react >=15.0.0`, so npm won't block React 19 — it will install and then misbehave. It predates React 18 StrictMode's double-invoked effects, which is exactly the class of bug that produces duplicate graph instances.

The wrapper is ~120 lines you don't need. The integration:

```tsx
"use client";
// components/graph/canvas.tsx
useEffect(() => {
  const cy = cytoscape({ container: ref.current!, elements, style, layout: { name: "fcose" } });
  cyRef.current = cy;
  return () => { cy.destroy(); };   // non-negotiable under StrictMode
}, []);                              // then drive updates via cy.json()/cy.batch(), not by remounting
```

Mount it through `next/dynamic(() => import("./canvas"), { ssr: false })` — Cytoscape touches `document` at import time and will crash SSR.

Register `cytoscape-fcose` once at module scope (`cytoscape.use(fcose)`), guarded so HMR doesn't double-register.

Lens filtering (per PROJECT.md, reuse `wiki_pages.category`) should use `cy.elements().style('display', …)` or collection filtering — **never** re-fetch and re-instantiate. Re-running layout on every filter toggle is the #1 perceived-jank source in Cytoscape UIs.

*Confidence: HIGH on the staleness evidence (npm registry `time` map + GitHub API). MEDIUM on the specific React 19 failure modes (inferred from age + open-issue titles, not reproduced).*

### 3.6 Testing

```bash
pnpm add -D vitest@4.1.10 @vitejs/plugin-react@6.0.5 jsdom@30.0.1 \
  @testing-library/react@16.3.2 @testing-library/jest-dom@7.0.0 \
  @testing-library/user-event@14.6.1 vite-tsconfig-paths@6.1.1
```

`vitest.config.ts`: `plugins: [react(), tsconfigPaths()]`, `test: { environment: "jsdom", setupFiles: ["./vitest.setup.ts"], globals: true }`.

**The limitation that shapes your test strategy: Vitest cannot render async Server Components.** React's RSC runtime isn't available in the test environment — the moment a component does `const data = await apiFetch(...)`, the render throws. This is documented in the official Next.js Vitest guide, not a bug you can configure around.

Consequence — a three-layer split:

| Layer | Tool | Covers |
|---|---|---|
| Pure functions | Vitest | `apiFetch`, zod schemas, slug normalization, citation-anchor parsing (`[[wiki:slug]]` / `[[src:chunk_id]]`), graph→cytoscape element mapping |
| Client + sync server components | Vitest + Testing Library | Dropzone, Ask input, citation card, wiki viewer link rendering |
| Async RSC, auth flows, middleware | **Playwright** | Login, workspace switch, ingest→job→wiki E2E |

**So: keep data fetching out of components.** Every async RSC should be a thin shell over a testable `lib/api/*` function. That is good architecture independently; here the test runner enforces it.

*Confidence: HIGH (nextjs.org official guide, corroborated by multiple 2026 write-ups).*

---

## 4. Deployment

### 4.1 Railway — the monorepo problem and its answer

The obvious approach (per-service **Root Directory** = `apps/api` / `apps/worker`) **breaks the uv workspace**: Root Directory isolates the build context, so `apps/worker` can no longer see `packages/core` or the root `uv.lock`. Since `packages/core` is where the shared bigram tokenizer must live (index-time and query-time must be byte-identical, and mismatch fails *silently* per PROJECT.md), that isolation is unacceptable.

**Recommended: two services, both Root Directory `/`, one shared Dockerfile, differentiated only by start command.**

```
railway.api.json        →  service "api"
railway.worker.json     →  service "worker"
Dockerfile              →  builds the whole uv workspace, used by both
```

```json
// railway.api.json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile",
    "watchPatterns": ["apps/api/**", "packages/**", "pyproject.toml", "uv.lock", "Dockerfile"]
  },
  "deploy": {
    "startCommand": "uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 60,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5,
    "drainingSeconds": "30"
  }
}
```

```json
// railway.worker.json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile",
    "watchPatterns": ["apps/worker/**", "packages/**", "pyproject.toml", "uv.lock", "Dockerfile"]
  },
  "deploy": {
    "startCommand": "uv run python -m worker",
    "restartPolicyType": "ALWAYS",
    "drainingSeconds": "120"
  }
}
```

Point each service at its config file via the service's **config-as-code file path** setting. Railway's own docs only guarantee "we look for `railway.toml` or `railway.json`" at the root directory; the per-service config-path override is documented in community answers rather than the reference page.

**Fallback if that setting isn't available in your dashboard (HIGH-confidence, always works):** delete both JSON files, keep `railway.toml` absent, and set **Custom Start Command** + **Watch Paths** per service in the dashboard/CLI. You lose config-as-code, not capability. Verify which path works during the first P0 deploy task; don't discover it in P4.

**Do not use Railpack here.** It auto-detects `pyproject.toml` + `uv.lock` and would work for a single flat app, but its inferred start command targets a single entrypoint. With two services off one image, an explicit Dockerfile is clearer and reproducible locally. (`NIXPACKS` no longer appears in Railway's current builder list — `RAILPACK` is the default, `DOCKERFILE` the explicit option.)

**Dockerfile shape:**

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
COPY packages/ packages/
COPY apps/api/ apps/api/
COPY apps/worker/ apps/worker/
RUN uv sync --locked --no-dev
```

One image for both services means api and worker **provably run identical tokenizer code** — the mismatch failure mode from PROJECT.md becomes structurally impossible rather than merely tested.

**Worker service specifics:** no `PORT`, no `healthcheckPath` (Railway will not health-check a service with no exposed port), `restartPolicyType: ALWAYS`. Shared vars (`DATABASE_URL`, `SUPABASE_*`, `OPENROUTER_API_KEY`, `LLM_MODEL`, `OPENAI_API_KEY`) belong in a **shared variable group** referenced by both services so they can't drift.

Cross-service references use `${{ServiceName.RAILWAY_PUBLIC_DOMAIN}}` — e.g. the api's `ALLOWED_ORIGINS`.

*Confidence: MEDIUM-HIGH. The `railway.json` schema and field names are HIGH (docs.railway.com/reference/config-as-code, quoted). The per-service config-path override is MEDIUM (community, not reference docs) — hence the stated fallback.*

### 4.2 Vercel

- Root Directory `apps/dashboard`; framework preset Next.js auto-detects.
- Ignored Build Step: `git diff --quiet HEAD^ HEAD -- apps/dashboard packages` so backend-only commits don't trigger a frontend rebuild.
- Env: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `API_URL` (server-only, → the Railway api public domain). Set all three for Production **and** Preview.
- Middleware runs on the Edge runtime — `updateSession` only. No Node-only imports in `middleware.ts` or the build fails late.
- Vercel region: choose Singapore (`sin1`) for function execution to keep the Vercel→Railway hop short.
- Add the Vercel preview and production domains to the api's CORS `ALLOWED_ORIGINS`; preview URLs are per-deploy, so allow the `*.vercel.app` project pattern via regex rather than an exact list.

### 4.3 Supabase Cloud

1. **Region: Southeast Asia (Singapore).** Permanent per project — see finding #2.
2. **Apply `0005` (Storage) before the first `db push`.** PROJECT.md flags this; it is the one ordering mistake that is expensive to undo.
3. **Upgrade the Supabase CLI (2.33.2 → current) before the first push,** and re-run `supabase db reset` locally afterward to confirm `config.toml` still parses. Pushing from a two-year-old CLI is a worse risk than the config-schema churn the deferral was protecting against.
4. Create **publishable + secret** keys (finding #1). The secret key goes to Railway only — never to Vercel.
5. Connection string for both Railway services: **Supavisor session mode, port 5432** (IPv4 on all tiers, prepared statements OK). Not the direct connection (IPv6-only without the paid add-on), not transaction mode 6543.
6. Confirm the project's Auth signing keys are asymmetric (ES256) and note the JWKS URL for `PyJWKClient`.
7. Free tier pauses after 7 days idle. For a project with a resident worker polling continuously this won't trigger, but know that the worker's polling is what keeps it awake — and that this is also a (small) continuous cost.

---

## 5. Monorepo layout and tooling

```
NexusWiki/
├── pyproject.toml                 # [tool.uv.workspace] + [tool.ruff] + [tool.pytest.ini_options]
├── uv.lock                        # ONE lock for api + worker + core
├── .python-version                # 3.13
├── Dockerfile                     # builds the uv workspace; used by both Railway services
├── railway.api.json
├── railway.worker.json
├── .pre-commit-config.yaml
├── .editorconfig
├── .env.example
├── apps/
│   ├── api/          pyproject.toml, app/{main,deps,routers,queries}.py
│   ├── worker/       pyproject.toml, worker/{__main__,loop,handlers}.py
│   └── dashboard/    package.json (pnpm), Next.js 15 — NOT a uv member
├── packages/
│   └── core/         pyproject.toml
│                     config.py       Settings (pydantic-settings)
│                     db.py           asyncpg pools + set_config scoping helper
│                     logging.py      structlog setup
│                     tokenizer.py    ★ Korean bigram — SHARED BY api AND worker
│                     llm.py          OpenRouter client + Pydantic retry loop
│                     models.py       shared Pydantic models
└── supabase/migrations/            frozen; 0005 pending
```

**`packages/core/tokenizer.py` is the reason this is a workspace and not two independent projects.** PROJECT.md: "색인 시점과 질의 시점 토크나이저가 동일해야 함 — 불일치는 조용히 실패함." The worker writes `search_tsv`; the api builds the query `tsquery`. If they can drift, they eventually will, and the symptom is degraded recall with no error anywhere. A shared workspace member + one lockfile + one Docker image removes the drift channel entirely. `tsv_tokenizer_version` should be a constant *in that module*, not in each app.

### Tooling

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.1
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
  - repo: local
    hooks:
      - id: prettier
        name: prettier
        entry: pnpm --dir apps/dashboard exec prettier --write
        language: system
        files: ^apps/dashboard/.*\.(ts|tsx|css|json|md)$
```

Ruff config in the root `pyproject.toml` (`[tool.ruff]` with `target-version = "py313"`, `line-length = 100`; `[tool.ruff.lint]` selecting at least `E,F,I,UP,B,ASYNC,S`). **`ASYNC`** catches blocking calls inside async functions — directly relevant to §1.2. **`S`** (bandit) catches hardcoded secrets.

`files:` scoping on the prettier hook is what stops the two formatters from fighting.

**What NOT to add at this size:** Turborepo / Nx / Lerna (one JS package — nothing to orchestrate); a pnpm workspace (same reason); `mypy` as a blocking gate (Pydantic + asyncpg row access make full strict typing expensive here; run `ruff` + `pyright` in non-blocking advisory mode if you want it); a shared TS/Python codegen step (the API surface is small enough that hand-written zod schemas are cheaper than an OpenAPI codegen pipeline — revisit if the API exceeds ~25 endpoints).

---

## Installation

```bash
# --- Python workspace ---
uv init --no-workspace .
# root pyproject.toml: [tool.uv.workspace] members = ["apps/api","apps/worker","packages/core"]

uv add --package core \
  pydantic==2.13.4 pydantic-settings==2.14.2 asyncpg==0.31.0 pgvector==0.5.0 \
  structlog==26.1.0 orjson==3.11.9 openai==2.52.0 httpx==0.28.1 \
  pyjwt==2.13.0 cryptography==50.0.0

uv add --package api  fastapi==0.141.1 uvicorn==0.52.0 python-multipart==0.0.32
uv add --package worker pypdf==6.14.2 trafilatura==2.2.0 storage3==2.31.0

uv add --dev pytest==9.1.1 pytest-asyncio==1.4.0 pytest-cov==7.1.0 \
             respx==0.23.1 ruff==0.16.1 pre-commit

# --- Dashboard ---
cd apps/dashboard
pnpm create next-app@15.5.22 . --ts --app --tailwind --eslint --src-dir=false
pnpm add next@15.5.22 react@19.2.8 react-dom@19.2.8 \
  @supabase/ssr@0.12.4 @supabase/supabase-js@2.111.0 \
  @tanstack/react-query@5.101.4 zod@4.4.3 \
  cytoscape@3.34.0 cytoscape-fcose@2.2.0
pnpm add -D typescript@5.9.3 @types/cytoscape@3.31.0 \
  tailwindcss@4.3.3 @tailwindcss/postcss postcss \
  vitest@4.1.10 @vitejs/plugin-react@6.0.5 jsdom@30.0.1 vite-tsconfig-paths@6.1.1 \
  @testing-library/react@16.3.2 @testing-library/jest-dom@7.0.0 @testing-library/user-event@14.6.1 \
  prettier@3.9.6
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| uv 0.12.1 | Poetry | You already have deep Poetry plugin investment, or you deploy via a Poetry-aware buildpack elsewhere. Not the case here. |
| asyncpg 0.31.0 | `supabase-py` 2.31.0 for data | If the 5-channel search + RRF fusion ends up living entirely in SQL functions anyway, `.rpc()` becomes viable and you get less code. Reconsider only if you decide to own the search in migrations. |
| asyncpg | `psycopg` 3.3.4 | psycopg3 is more forgiving with the transaction-mode pooler (no prepared-statement wall) and has a richer type system. Choose it if you're forced onto port 6543. Otherwise asyncpg is faster and its pool API is simpler. |
| Hand-written SQL | SQLAlchemy 2.0.51 + Alembic | Only if the schema stops being owned by `supabase/migrations`. Today Alembic would create a **second** migration source of truth over the same tables — a real hazard, not a style preference. |
| pypdf 6.14.2 | pymupdf4llm 1.28.0 | The moment an Artifex commercial license is bought. Materially better multi-column reading order and table handling. |
| pypdf | docling 2.117.0 | When scanned-PDF support becomes a requirement. Deploy as a **separate** Railway service — do not put torch in the API image. |
| TanStack Query 5.101.4 | SWR 2.4.2 | If the dashboard ends up with fewer than ~5 client-side queries and no optimistic mutations. Half the bundle. |
| structlog 26.1.0 | stdlib `logging` + `python-json-logger` 4.1.0 | If you want zero new deps and are willing to hand-roll contextvar propagation. Not worth it. |
| Vitest 4.1.10 | Jest | Only if a dependency hard-requires Jest transforms. Vitest is the documented Next.js path now. |
| TypeScript 5.9.3 | TypeScript 7.0.2 | After the `@types/*` and eslint ecosystem catches up — realistically post-v1. |
| Dockerfile on Railway | Railpack + per-service Root Directory | Only if you abandon the uv workspace and vendor the tokenizer into both apps. Don't — that's the silent-failure mode. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **`react-cytoscapejs`** | Last publish 2022-09-02; 45 open issues incl. a Next.js CJS/ESM import failure; predates React 18 StrictMode and React 19. Peer `react >=15` means it installs cleanly and *then* misbehaves. | `cytoscape` 3.34.0 directly in a `"use client"` component with `useRef` + `useEffect` + `cy.destroy()`, via `next/dynamic({ssr:false})` |
| **Next.js < 15.2.3** | **CVE-2025-29927** — spoofing `x-middleware-subrequest` bypasses middleware entirely. This app's tenant gate *is* middleware. | `next@15.5.22` |
| **PyMuPDF / pymupdf4llm (unlicensed)** | **AGPL-3.0** reaches network users; a hosted SaaS must open-source or buy an Artifex license. | `pypdf` 6.14.2 (BSD-3) |
| **Celery / arq / dramatiq / RQ / saq** | All require Redis or another broker (explicitly out of scope), and duplicate the verified `claim_job`/`complete_job`/`fail_job` contract in migration `0003`. | ~150 lines of asyncio (§2.1) |
| **A shared, mutated `supabase-py` client for per-request user auth** | `auth.set_session()` / `postgrest.auth()` mutate a shared object. Under concurrency, request A can overwrite request B's token mid-flight → cross-tenant read that RLS *correctly* authorizes for the wrong user. | asyncpg + `set_config(..., is_local=true)` inside a transaction |
| **`service_role` / secret key on any user request path** | It is `BYPASSRLS`. One use turns all 38 isolation policies into decoration. | Requester JWT via `set_config`; secret key confined to the worker's pool and migrations |
| **`SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_KEY` as env names** | Legacy keys aren't issued to projects created after Nov 2025 and are deleted late 2026. Your project doesn't exist yet. | `SUPABASE_PUBLISHABLE_KEY` / `SUPABASE_SECRET_KEY` |
| **`supabase.auth.getSession()` in server code** | Reads the cookie without revalidating. Supabase docs say do not trust it server-side. | `getClaims()` (verifies against JWKS) |
| **Supabase direct connection (5432, non-pooler)** | IPv6-only without the paid IPv4 add-on; Railway egress will fail or need the add-on. | Supavisor **session mode**, port 5432 |
| **Supavisor transaction mode (6543)** | No prepared statements — asyncpg fails unless `statement_cache_size=0`, which discards its main advantage. | Session mode |
| **Gunicorn in front of Uvicorn on Railway** | Extra process layer complicates SIGTERM drain and doubles idle memory on a $5/mo instance; Railway scales by replica. | Bare `uvicorn`, one process |
| **Tailwind 3 / `tailwind.config.js` / `@tailwind base;`** | v3 syntax; v4 is CSS-first via `@theme` and `@tailwindcss/postcss`. | v4 setup in §3.3 |
| **Alembic / SQLAlchemy migrations** | Creates a second migration source of truth over tables already owned by `supabase/migrations`. | `supabase/migrations/*.sql` only |
| **Turborepo / Nx / pnpm workspace** | One JS package. Pure overhead. | Plain pnpm in `apps/dashboard` |
| **`signal.signal()` for worker SIGTERM** | Fires on an arbitrary thread; cannot safely touch the event loop. | `loop.add_signal_handler(SIGTERM, stop.set)` |
| **`asyncio.sleep()` in the poll loop** | SIGTERM waits out the full sleep before shutdown begins. | `await asyncio.wait_for(stop.wait(), timeout=delay)` |
| **Fixed-interval polling** | N replicas synchronize and hammer the DB in lockstep. | Full-jitter exponential backoff, `base=0.5s`, `cap=15s` |
| **Neo4j / any graph DB** | Already out of scope: no GDS on Aura basic, no RLS, no traversal win at this scale. | `wiki_links` + recursive CTE |

---

## Stack Patterns by Variant

**If the Railway per-service "config file path" setting is unavailable:**
- Delete `railway.api.json` / `railway.worker.json`; set **Custom Start Command** and **Watch Paths** per service in the dashboard or via `railway service`.
- Because you lose config-as-code, record both start commands in `README.md` and in `.planning/` so they're reviewable.

**If the Ask endpoint needs token streaming:**
- FastAPI `StreamingResponse` with SSE + `httpx-sse` 0.4.3 on the OpenRouter side (or the openai SDK's native `stream=True`).
- Proxy through a Next.js Route Handler, not a direct browser→Railway call — keeps `API_URL` private and lets you attach the request id to both sides of the trace.
- **Emit citation anchors as discrete SSE events, not inline in the token stream.** Parsing `[[wiki:slug]]` out of a partially-arrived token buffer is a guaranteed source of broken citation cards, and dual citation is the Core Value.

**If a compile job can exceed the 15-minute `reap_stale_jobs` timeout:**
- Add a heartbeat: a background task per in-flight job touching the `jobs` lock timestamp every ~60 s.
- **Verify against `0003`'s schema first** — if there's no heartbeat-writable column, either raise the reap timeout or split compilation into smaller jobs. Splitting is better: it also makes retries cheaper.

**If worker throughput becomes the bottleneck:**
- Scale **replicas** in Railway, not `WORKER_CONCURRENCY`. `FOR UPDATE SKIP LOCKED` is already proven at 8 workers / 400 jobs, and replicas give you memory isolation and independent restarts.
- Watch the OpenRouter rate limit before the DB — add `aiolimiter` 1.2.1 if you hit 429s that the SDK's retry can't absorb.

**If PDF quality complaints arrive:**
- The path is already built: originals are immutable in Storage, `content_hash` makes re-ingest idempotent. Swap the parser, bump a parser-version marker, re-enqueue. Do **not** retrofit OCR into the api image.

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `next@15.5.22` | `react@19.2.8` | Peer range `^18.2.0 \|\| ^19.0.0`. Identical on Next 16 — the upgrade is not a React bump. |
| `@supabase/ssr@0.12.4` | `@supabase/supabase-js@^2.111.0` | Hard peer. Bumping one without the other breaks the cookie contract. |
| `@supabase/ssr@0.12.4` | `cookie@^1.0.2` | Direct dep. `cookie` v1 changed its API from v0 — don't pin an old `cookie` transitively. |
| `fastapi@0.141.1` | Python ≥3.10, `pydantic@2.x` | Pydantic v1 unsupported. |
| `asyncpg@0.31.0` | Python ≥3.9, PG 17 | With Supavisor **transaction** mode you must pass `statement_cache_size=0`. Session mode: no restriction. |
| `pgvector@0.5.0` (py) | `asyncpg` | `await register_vector(conn)` in the pool's `init=` hook, on **every** connection. |
| `pymupdf@1.28.0` | `pymupdf4llm@1.28.0` | Versions track in lockstep. Both AGPL. |
| `tailwindcss@4.3.3` | `@tailwindcss/postcss@4.3.3` | Must match exactly; they ship as a pair. |
| `vitest@4.1.10` | `@vitejs/plugin-react@6.0.5` | Vitest 4 requires the Vite 6-era plugin. |
| `@testing-library/react@16.3.2` | `react@19` | v16 is the React 19-compatible line; v14/v15 are not. |
| `cytoscape@3.34.0` | `@types/cytoscape@3.31.0` | Types lag minor versions; harmless. |
| `typescript@5.9.3` | `eslint-config-next@15.x` | Do **not** jump to `typescript@7.0.2` yet (GA 2026-07-08). |
| Railpack default Python | 3.13.2 | Matches the recommended `.python-version`; keeps the Dockerfile and any Railpack fallback aligned. |
| Supabase CLI 2.33.2 → 2.111.0 | `supabase/config.toml` | Upgrade **before** the first cloud `db push`; re-run `supabase db reset` locally to confirm the config still parses. |

---

## Open Items for Phase Planning

Flag these into the roadmap rather than assuming them resolved:

1. **`jobs` heartbeat column** — does migration `0003` expose one? Determines whether long compile jobs are safe against `reap_stale_jobs` (§2.1 detail 4). Cheap to check, expensive to discover in production.
2. **Railway per-service config-as-code path** — verify in the dashboard during the first P0 deploy. Fallback documented (§4.1).
3. **supabase-py concurrency hazard** — the §1.3(b) argument is inferred from the documented stateful API. If you want it settled, a 20-line concurrency test proves or disproves it. Either way the asyncpg recommendation stands on (a) and (c) alone.
4. **Singapore RTT** — the §finding-2 latency figures are geographic estimates. Measure Railway `asia-southeast1` → Supabase `ap-southeast-1` on first deploy and record it against `checklists.json` open question #2.
5. **`response_format: json_schema` per-model support** — worth a capability probe against the configured `LLM_MODEL` in P4, but only as an optimization behind the mandatory Pydantic retry loop (§1.4).

---

## Sources

**Registry APIs, read directly on 2026-08-01 — HIGH confidence.** These are first-party, machine-readable, and deterministic; every version number in this document came from here, not from memory.
- `pypi.org/pypi/<pkg>/json` — fastapi 0.141.1, uvicorn 0.52.0, pydantic 2.13.4, pydantic-settings 2.14.2, httpx 0.28.1, asyncpg 0.31.0, psycopg 3.3.4, supabase 2.31.0, storage3 2.31.0, pypdf 6.14.2, pymupdf 1.28.0, pymupdf4llm 1.28.0, docling 2.117.0, structlog 26.1.0, ruff 0.16.1, openai 2.52.0, tenacity 9.1.4, pyjwt 2.13.0, cryptography 50.0.0, pgvector 0.5.0, orjson 3.11.9, trafilatura 2.2.0, pytest 9.1.1, pytest-asyncio 1.4.0, pytest-cov 7.1.0, respx 0.23.1, python-multipart 0.0.32, aiolimiter 1.2.1, httpx-sse 0.4.3
- `registry.npmjs.org/<pkg>` (incl. `dist-tags` + `time` maps) — next 16.2.12 / 15.5.22, react 19.2.8, @supabase/ssr 0.12.4, @supabase/supabase-js 2.111.0, tailwindcss 4.3.3, vitest 4.1.10, @testing-library/react 16.3.2, cytoscape 3.34.0, react-cytoscapejs 2.0.0 (published 2022-09-02), typescript 7.0.2 / 5.9.3, prettier 3.9.6, zod 4.4.3, @tanstack/react-query 5.101.4, pnpm 11.18.0, jsdom 30.0.1, @vitejs/plugin-react 6.0.5
- `api.github.com/repos/astral-sh/uv/releases/latest` — uv 0.12.1 (2026-07-31)
- `api.github.com/repos/plotly/react-cytoscapejs` — pushed 2025-01-27, 45 open issues, not archived
- `nodejs.org/dist/index.json` — Node 24.18.1 LTS (Krypton)
- `endoflife.date/api/python.json` — 3.13 EOL 2029-10-31

**Official documentation (fetched) — MEDIUM confidence.**
- supabase.com/docs/guides/getting-started/api-keys — publishable/secret → anon/service_role role mapping, `BYPASSRLS`, `apikey` vs `Authorization` header rule
- supabase.com/docs/guides/auth/signing-keys — ES256/RS256, JWKS discovery path, HS256 discouraged
- supabase.com/docs/guides/auth/server-side/nextjs — `getAll`/`setAll(cookiesToSet, headers)`, `getClaims()` over `getSession()`, preserve `supabaseResponse`
- supabase.com/docs/guides/database/connecting-to-postgres — direct IPv6-only, Supavisor session vs transaction mode, `statement_cache_size=0`
- supabase.com/docs/guides/platform/regions — Seoul and Singapore both available
- docs.railway.com/reference/config-as-code — `railway.json` schema, `RAILPACK`/`DOCKERFILE`, `watchPatterns`, `startCommand`, `drainingSeconds` (quoted verbatim)
- docs.railway.com/reference/regions — four regions, no Seoul/Tokyo
- docs.railway.com/guides/deploying-a-monorepo — Root Directory per service, `${{Service.RAILWAY_PUBLIC_DOMAIN}}`
- docs.astral.sh/uv/concepts/projects/workspaces — `[tool.uv.workspace]`, single lockfile, `--package`, when not to use
- tailwindcss.com/docs/installation/framework-guides/nextjs — exact v4 install (quoted verbatim)
- nextjs.org/docs/app/guides/testing/vitest (via search synthesis) — async Server Components unsupported
- railpack.com/languages/python — uv auto-detection, default build command, Python 3.13.2 default

**Web search synthesis — LOW→MEDIUM confidence, direction consistent across independent sources.**
- PDF extractor benchmarks (pdfmux, zysec, kooexperience) — PyMuPDF speed advantage, docling OCR/table capability, AGPL warning
- CVE-2025-29927 fixed versions — cross-confirmed across JFrog, Datadog Security Labs, OffSec, ProjectDiscovery, Zscaler (five independent sources → treated as HIGH)
- structlog + FastAPI production patterns — Dash0, nymous gist, multiple 2026 practitioner guides
- supabase-py FastAPI patterns and hazards — supabase discussions #33811, #28843, #37052; supabase-py issue #798
- asyncpg `set_config('request.jwt.claims', …)` RLS pattern — supabase discussions #30124, #22482

---
*Stack research for: multi-tenant Living Wiki SaaS — FastAPI + resident worker + Next.js 15 application layer*
*Researched: 2026-08-01*
