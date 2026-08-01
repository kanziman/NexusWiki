# Architecture Research

**Domain:** Multi-tenant "Living Wiki" SaaS — LLM-compiled knowledge base with 5-channel hybrid retrieval and dual citation
**Researched:** 2026-08-01
**Confidence:** MEDIUM-HIGH (structure recommendations HIGH — derived from the already-implemented data layer's own invariants; external ecosystem claims MEDIUM)

> **Scope.** The data layer (`supabase/migrations/0001–0004, 0006`) is DECIDED AND BUILT and is treated here as fixed ground truth. This document covers only the application layer that sits on top: FastAPI API service, resident worker process, Next.js 15 dashboard. Every recommendation below was checked against `.planning/codebase/ARCHITECTURE.md` and `CONCERNS.md`; where a recommendation implies a *new* migration it is called out explicitly as additive (`0007`), never as a change to `0001–0006`.

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│  apps/dashboard  —  Next.js 15 App Router                                │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐               │
│  │ RSC (default)  │ │ Client islands │ │ middleware.ts  │               │
│  │ wiki / graph / │ │ AskPanel       │ │ session refresh│               │
│  │ jobs / list    │ │ Dropzone       │ │ (cookie write) │               │
│  │  reads         │ │ GraphCanvas    │ └────────────────┘               │
│  └───────┬────────┘ └───────┬────────┘                                   │
│          │ supabase-ssr     │ fetch → BFF route handler                  │
└──────────┼──────────────────┼────────────────────────────────────────────┘
           │ (JWT, RLS)       │ (JWT forwarded as Bearer)
           │                  ▼
           │      ┌─────────────────────────────────────────────────┐
           │      │  apps/backend/api   —  FastAPI  (Railway: web)  │
           │      │  ┌───────────┐  ┌────────────┐  ┌────────────┐  │
           │      │  │ routers/  │→ │ services/  │→ │ db/user.py │  │
           │      │  │ ingest    │  │ retrieval/ │  │ UserDb     │  │
           │      │  │ ask       │  │ ingest.py  │  │ (JWT-bound)│  │
           │      │  │ graph     │  │ citations  │  └─────┬──────┘  │
           │      │  └───────────┘  └────────────┘        │         │
           │      │  ⛔ cannot import db/service.py — the service   │
           │      │     key is absent from ApiSettings              │
           │      └────────────────┬───────────────────────┼────────┘
           │                       │ enqueue (jobs)        │
           │                       ▼                       │
           │      ┌─────────────────────────────────────────────────┐
           │      │  apps/backend/worker — resident (Railway: worker)│
           │      │  claim_job → dispatch(type) → handler → chain    │
           │      │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │
           │      │  │ parse  │→│compile │→│link_   │→│ embed  │    │
           │      │  │        │ │  (LLM) │ │ sync   │ │        │    │
           │      │  └────────┘ └────────┘ └────────┘ └────────┘    │
           │      │  db/service.py — BYPASSRLS, explicit ws filter  │
           │      └────────────────┬────────────────────────────────┘
           ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Supabase Postgres 17  [IMPLEMENTED — do not redesign]                   │
│  9 tables · RLS everywhere · composite FKs carry workspace_id            │
│  jobs + claim/complete/fail/reap · pgvector HNSW · bigram GIN            │
│  + retrieval SQL functions (security invoker)  ← NEW in 0007             │
│  + Storage bucket `sources`                    ← 0005 (must land first)  │
└─────────────────────────────────────────────────────────────────────────┘
                     │                       │
                     ▼                       ▼
        OpenRouter (compile + answer)   OpenAI (embeddings, 1536-d)
```

**The one-sentence shape:** *Reads go straight to Postgres under the requester's JWT; writes and compute go through FastAPI; anything slow or expensive goes through the queue to the worker; the worker is the only thing holding the service key.*

### Component Responsibilities

| Component | Responsibility (owns) | Explicitly does NOT own |
|-----------|----------------------|-------------------------|
| `db/user.py` (`UserDb`) | Every user-request DB call, bound to the requester's JWT. Maps *affected rows = 0* → 403 and `42501` → 403. | Job mutation, service_role anything |
| `db/service.py` (`service_client`) | Worker + migration DB access. Requires an explicit `workspace_id` on every query. | Anything reachable from an HTTP handler |
| `api/routers/*` | HTTP surface, request/response schemas, status codes. Thin. | Business logic, SQL, retry policy |
| `api/services/*` | Orchestration over `UserDb` + external providers. | HTTP concerns, direct client construction |
| `domain/*` (pure) | Tokenizer, RRF fusion, anchor parse/emit, slug normalization, chunker. Zero I/O. | Any DB or network call |
| `worker/handlers/*` | One pipeline stage each. Idempotent. Returns the next chain link. | Queue mechanics, claiming, backoff |
| `worker/loop.py` | claim → dispatch → complete/fail, unknown-type → dead, SIGTERM drain, reaper. | Anything domain-specific |
| `retrieval/channels/*` | One SQL channel each → `list[Candidate]`. | Fusion, weighting, context assembly |
| `retrieval/fusion.py` | Weighted RRF. Pure function. | Knowing what a channel is |
| Next.js RSC pages | Reads via `@supabase/ssr` server client (RLS applies). | Mutations, LLM calls |
| Next.js route handlers (BFF) | Forward the session JWT to FastAPI; proxy the SSE stream. | Business logic |
| Next.js client islands | Interactivity only: stream rendering, upload, canvas. | Fetching what the RSC already had |

---

## Recommended Project Structure

```
NexusWiki/
├── apps/
│   ├── backend/
│   │   ├── pyproject.toml           # ruff banned-api rule lives here
│   │   ├── Procfile                 # web: api  |  worker: worker
│   │   ├── core/
│   │   │   ├── settings.py          # BaseSettings + ApiSettings + WorkerSettings
│   │   │   ├── logging.py           # structlog; redaction filter for provider errors
│   │   │   └── errors.py            # Forbidden / NotFound / UpstreamError + handlers
│   │   ├── db/
│   │   │   ├── user.py              # user_db(token) -> UserDb        [API ONLY]
│   │   │   └── service.py           # service_client()                [WORKER ONLY]
│   │   ├── domain/                  # ← pure, no I/O, 100% unit-testable
│   │   │   ├── tokenizer.py         # bigram + phraseto_tsquery builder (ONE module)
│   │   │   ├── slug.py              # [[WikiLink]] → slug normalization
│   │   │   ├── chunking.py          # char-window chunker
│   │   │   ├── citations.py         # anchor emit + parse + alias table
│   │   │   └── fusion.py            # weighted RRF
│   │   ├── retrieval/
│   │   │   ├── policy.py            # RetrievalPolicy (k, weights, limits, hops)
│   │   │   ├── channels/            # 5 modules, each returns list[Candidate]
│   │   │   ├── assemble.py          # Candidates → ContextBlock with anchors
│   │   │   └── pipeline.py          # gather(1-4) → fuse → seed(5) → fuse → assemble
│   │   ├── providers/
│   │   │   ├── llm.py               # OpenRouter; AnswerModel + CompileModel protocols
│   │   │   ├── embed.py             # Embedder protocol; OpenAI impl
│   │   │   └── prompts.py           # {{var}} substitution (NOT str.format)
│   │   ├── api/
│   │   │   ├── main.py              # uvicorn entry; loads ApiSettings
│   │   │   ├── deps.py              # principal → workspace_ctx → UserDb
│   │   │   ├── routers/             # ingest.py ask.py graph.py health.py
│   │   │   └── schemas/             # pydantic request/response models
│   │   ├── worker/
│   │   │   ├── main.py              # entry; loads WorkerSettings
│   │   │   ├── loop.py              # claim/dispatch/complete/fail/reap/SIGTERM
│   │   │   ├── registry.py          # {type: handler}
│   │   │   └── handlers/            # parse.py compile.py link_sync.py embed.py
│   │   └── tests/
│   │       ├── unit/                # domain/ + fusion + citations — no DB, no net
│   │       ├── db/                  # against local Supabase; RLS + channel plumbing
│   │       └── fixtures/            # retrieval fixtures, golden LLM outputs, queries.yaml
│   └── dashboard/
│       ├── middleware.ts            # session refresh (only place cookies are written)
│       ├── lib/supabase/
│       │   ├── server.ts            # RSC / Server Action / Route Handler client
│       │   └── browser.ts           # client-component client
│       ├── lib/api.ts               # typed fetch → FastAPI, attaches Bearer
│       ├── app/
│       │   ├── (auth)/login/
│       │   ├── w/[workspaceId]/     # workspace is a URL segment, not state
│       │   │   ├── layout.tsx       # RSC: membership check + workspace shell
│       │   │   ├── page.tsx         # overview
│       │   │   ├── ask/             # AskPanel (client island)
│       │   │   ├── sources/         # Dropzone + job chain progress
│       │   │   ├── wiki/[slug]/     # RSC read, red-link rendering
│       │   │   └── graph/           # GraphCanvas (dynamic, ssr:false)
│       │   └── api/                 # BFF: ask stream proxy, upload signing
│       └── components/
└── supabase/migrations/
    ├── 0005_storage.sql             # MUST land before first cloud push
    └── 0007_retrieval_and_chain.sql # search fns + jobs_dedup_idx + complete_job_and_chain
```

### Structure Rationale

- **`domain/` exists so the interesting logic has no dependencies.** Bigram tokenization, RRF, anchor parsing and slug normalization are where the correctness risk lives (`CONCERNS.md`: tokenizer divergence "fails silently, with no error and no test that would notice"). Isolating them into an I/O-free package means every one of those risks is covered by a fast unit test that needs neither Docker nor an API key.
- **`api/` and `worker/` are siblings, not parent/child.** They share `core/`, `db/`, `domain/`, `providers/` but neither imports the other. This is what lets the service-key isolation be structural rather than aspirational.
- **`retrieval/` is not under `api/`.** Retrieval is used by the ask endpoint today and plausibly by a "related pages" worker step later. Coupling it to the HTTP layer would force a rewrite.
- **Feature-first vs layer-first:** layer-first here. The common FastAPI advice (feature modules each with `router.py`/`service.py`/`schemas.py`) pays off past ~10 features; this codebase has 4 routers and one dominant cross-cutting pipeline (retrieval). Layer-first keeps the security-critical files (`db/`, `deps.py`) in exactly one place each, which is worth more than feature cohesion at this size.
- **`w/[workspaceId]` in the URL:** the tenancy root is in the route so that every RSC has it from `params` without any client state. See anti-patterns.

---

## Architectural Patterns

### Pattern 1: Capability Absence — make `service_role` unreachable, not merely discouraged

**What:** The API process must be *incapable* of constructing a service_role client, rather than instructed not to. Four layers, cheapest first:

1. **Split the settings model.** `ApiSettings` has no `supabase_service_key` field at all; `WorkerSettings` does. Railway injects the key only into the `worker` service. `service_client()` in the API process then fails at *config resolution*, not at review time.
2. **Split the module.** `db/service.py` is importable only from `worker/`.
3. **Lint gate.** `ruff` `flake8-tidy-imports` banned-api (TID251) on `db.service.service_client`, with a `per-file-ignores` exemption for `worker/**`. CI fails on violation.
4. **Runtime tripwire.** `service_client()` asserts `os.environ.get("NEXUSWIKI_ROLE") == "worker"`.

**When to use:** Any invariant where a single accidental call voids the whole security model. `CONCERNS.md` names this as the top unmitigated risk ("38 isolation cases become decorative").

**Trade-offs:** Two settings classes is mild duplication and one more env var per Railway service. In exchange the invariant survives an unreviewed commit at 2am. Worth it.

```python
# core/settings.py
class BaseSettings_(BaseSettings):
    supabase_url: str
    supabase_anon_key: str

class ApiSettings(BaseSettings_):
    """API 프로세스 설정. service key 필드가 존재하지 않는다 — 이것이 격리 강제 장치."""
    cors_origins: list[str] = []

class WorkerSettings(BaseSettings_):
    supabase_service_key: SecretStr        # 워커에만 존재
    openrouter_api_key: SecretStr
    llm_model: str = "claude-sonnet-4-6"
    reap_timeout_seconds: int = 900        # 명시적으로 전달 — 기본값에 의존하지 말 것
```

```toml
# pyproject.toml
[tool.ruff.lint.flake8-tidy-imports.banned-api]
"db.service".msg = "service_role은 worker/ 에서만. 사용자 요청 경로는 db.user.UserDb 사용."
[tool.ruff.lint.per-file-ignores]
"worker/**" = ["TID251"]
```

---

### Pattern 2: Pre-scoped Context Dependency — routers never see a token

**What:** Routers receive an already-authorized `WorkspaceContext`, never a raw token or a raw client. The chain is `bearer → Principal → WorkspaceContext(UserDb)`. Services take `ctx` as their first parameter.

**Why this shape:** it removes the *opportunity* to pick the wrong client. There is no `client` variable in scope inside a handler.

**Trade-offs:** slightly more ceremony per endpoint; makes ad-hoc scripts awkward (good).

```python
# api/deps.py
@dataclass(frozen=True)
class WorkspaceContext:
    workspace_id: UUID
    user_id: UUID
    role: Literal["owner", "editor", "viewer"]
    db: UserDb                 # 이미 요청자 JWT에 바인딩됨

async def workspace_ctx(
    workspace_id: UUID = Path(...),
    principal: Principal = Depends(current_principal),
) -> WorkspaceContext:
    db = user_db(principal.access_token)          # 요청 단위, 공유 httpx 재사용
    role = await db.workspace_role(workspace_id)  # RLS가 비멤버에게는 None을 돌려줌
    if role is None:
        raise Forbidden("workspace")              # 404가 아님 — 존재 여부도 누설 금지
    return WorkspaceContext(workspace_id, principal.user_id, role, db)

# api/routers/ingest.py
router = APIRouter(prefix="/w/{workspace_id}", dependencies=[Depends(require_role("editor"))])
```

**The 403 mapping lives in `UserDb`, not in routers.** `CONCERNS.md` warns that an RLS-blocked UPDATE returns *0 rows and no exception* — if the API returns 200, "the product silently lies to the user about having saved their edit." Make the safe method the ergonomic one:

```python
class UserDb:
    async def mutate_one(self, table, *, match, values) -> dict:
        res = await self._table(table).update(values).match(match).execute()
        if not res.data:                       # USING 차단 = 0행, 예외 없음
            raise Forbidden(table)
        return res.data[0]
```

---

### Pattern 3: Retrieval channels as SECURITY INVOKER SQL functions (not PostgREST query building)

**What:** Each of the five channels is a Postgres function created in migration `0007`, marked `security invoker`, granted to `authenticated`, revoked from `anon`, and carrying its GUC on the definition. The API calls them via `rpc()` with the requester's JWT.

**Why this and not the alternatives:**

| Approach | Verdict |
|---|---|
| PostgREST query builder from Python | **Impossible.** Cannot express a recursive CTE, cannot express `<=>` ordering with `set local hnsw.iterative_scan`, cannot express `phraseto_tsquery` ranking. |
| Raw asyncpg pool + `set local role authenticated; set local request.jwt.claims=…` | **Rejected.** You hand-forge the auth context, so a claim-construction bug is a tenant crossing. `SET LOCAL` must be per-transaction, never per-connection — reusing a pooled connection with a stale tenant context is a well-documented leak class. Strictly more surface than the RLS model already validated 38/38. |
| `security invoker` SQL functions via RPC | **Chosen.** RLS applies unchanged, the tenant context is still the JWT, GUCs are settable, and there stays exactly one way for the API to reach the database. |

**Critical detail:** put `hnsw.iterative_scan` on the function definition, so it is impossible to call the channel without it — this is the `Architectural Constraints` requirement from `codebase/ARCHITECTURE.md` made unforgettable:

```sql
create function public.search_wiki_vector(
  p_workspace_id uuid, p_query extensions.vector(1536), p_limit int
) returns table (wiki_id uuid, slug text, chunk_index int, distance float)
language sql
security invoker                      -- ⚠️ definer로 바꾸면 RLS가 사라진다
stable
set search_path = public
set hnsw.iterative_scan = 'strict_order'   -- post-filter로 k 미만이 되는 것을 방지
as $$
  select e.wiki_id, w.slug, e.chunk_index, e.embedding <=> p_query
  from public.wiki_embeddings e
  join public.wiki_pages w on w.id = e.wiki_id and w.workspace_id = e.workspace_id
  where e.workspace_id = p_workspace_id           -- RLS와 별개로 명시적 필터
  order by e.embedding <=> p_query
  limit p_limit;
$$;
revoke all on function public.search_wiki_vector(uuid, extensions.vector, int) from public, anon;
grant execute on function public.search_wiki_vector(uuid, extensions.vector, int) to authenticated;
```

**Trade-off:** retrieval SQL lives in a migration rather than in Python, so changing a channel needs a migration. Acceptable — this repo has already decided the schema is the contract, and the *tunable* parts (weights, k, limits) deliberately stay in Python where they belong.

---

### Pattern 4: Chained job types, one stage per idempotency key

**What:** Five job types, not one. Each maps 1:1 onto a documented upsert key:

```
source.parse   → source_chunks   (raw_source_id, chunk_index)
   ├─→ source.embed  → source_chunks.embedding   (same key, UPDATE)
   └─→ wiki.compile  → wiki_pages     (workspace_id, slug)
         └─→ wiki.link_sync → wiki_links   (from_wiki_id, target_slug)
         └─→ wiki.embed     → wiki_embeddings (wiki_id, chunk_index)
```

**Why chained rather than one `ingest` job — four independent reasons, in order of force:**

1. **The 15-minute reaper is a global knob and a monolith blows past it.** A monolith's p99 is parse + compile + embed. If that exceeds the reap timeout, a *healthy* job is stolen and processed twice — double LLM spend, and `CONCERNS.md` already flags that "a slow-but-healthy job can reach `dead` purely from timeouts." Splitting keeps every stage's p99 comfortably under one timeout. This alone decides it.
2. **Retry granularity is money.** Compile is the expensive step. With a monolith, one embedding-provider 503 re-runs the compile at full cost, up to `max_attempts` times.
3. **Observability is free.** `jobs.type × status` is already exposed to members via `jobs_select_member`. A 4-link chain renders as a real progress bar ("파싱 완료 · 컴파일 중 · 임베딩 대기") with zero new schema and zero new endpoint.
4. **The upsert keys already told you where the seams are.** Three keys, three write stages. That is not a coincidence; the data layer was designed around these boundaries.

**Cost, and how to pay it:** chaining introduces "the next link was never enqueued." Fix it in the queue, not in the handler:

```sql
-- 0007 (additive; 0003의 네 함수는 건드리지 않음)
create unique index jobs_dedup_idx on public.jobs
  (workspace_id, type, (payload->>'entity_id'))
  where status in ('queued','running','failed');

create function public.complete_job_and_chain(
  p_job_id uuid, p_next_type text, p_next_payload jsonb
) returns uuid language plpgsql security invoker set search_path = public as $$
...  -- complete_job(p_job_id) + insert ... on conflict do nothing, 한 트랜잭션
$$;
```

Two properties fall out: chain advancement is atomic with completion (no lost link, no double-enqueue on reap), and the duplicate-ingest problem `CONCERNS.md` raises ("a double-clicked ingest enqueues duplicate LLM work — real money") is solved by the same index.

**Handler contract:**

```python
class Handler(Protocol):
    type: ClassVar[str]
    async def run(self, job: Job, db: ServiceDb) -> NextJob | None
```

Rules every handler must obey (enforce with a shared base class, not a docstring):
- Always filter `workspace_id` explicitly — `service_role` bypasses RLS.
- Re-running the whole handler must be a no-op. Upsert on the documented key; never select-then-insert.
- **Tail-delete after sequence upserts.** `CONCERNS.md` documents a live idempotency gap: re-chunking 12 chunks into 8 leaves chunks 8–11 orphaned. Every sequence writer ends with `delete … where parent = $1 and chunk_index >= $n`. Put this in one `upsert_sequence()` helper so no handler can forget.
- Never write a raw provider exception into `last_error` — every workspace member including viewers can read it. Redact to `{code, provider, http_status, message[:200]}`.

**Worker loop shape:** single resident asyncio process; in-flight jobs bounded by a semaphore (start at 4 — the work is LLM-wait-bound, which is exactly why Railway's CPU-actual billing was chosen); `claim_job(worker_id, [types this worker serves])`; unknown `type` → straight to `dead` with `last_error` (`jobs.type` has no CHECK by design); SIGTERM → stop claiming, drain in-flight, exit — anything not drained gets reaped, which is safe because handlers are idempotent. One designated reaper coroutine calls `reap_stale_jobs(explicit_timeout)`; do not let every worker race on it, and do not rely on the default.

---

### Pattern 5: Two-wave retrieval — the graph channel is not a peer of the other four

**What:** Channels 1–4 (wiki vector, source vector, wiki lexical, source lexical) run concurrently off the query. Channel 5 (`wiki_links` N-hop recursive CTE) has **no intrinsic relevance score and no query to run against** — its input is *seed wiki ids*, which only exist after wave 1. So:

```
                 ┌─ ch1 wiki vector   ─┐
query ─embed──┬──┼─ ch2 source vector ─┼──► RRF ──► seeds = top-S wiki ids
              └──┼─ ch3 wiki lexical  ─┤            │
                 └─ ch4 source lexical─┘            ▼
                                            ch5 graph expand (N-hop CTE)
                                                    │  rank = hop distance
                                                    ▼
                                        RRF (4 channels + graph) ──► assemble
```

The graph channel's rank is hop distance from the seed set (`hop 1` outranks `hop 2`), which slots into RRF cleanly because RRF consumes ranks, not scores — that is precisely why RRF is the right fusion operator for a channel that has no comparable score.

**Trade-off:** two round trips instead of one, so latency = `max(ch1..ch4) + ch5` rather than `max(ch1..ch5)`. The CTE is index-backed and shallow (2 hops), so this is tens of milliseconds. The alternative — running the CTE off a raw slug guess in parallel — buys latency at the cost of seeding the graph from nothing. Take the two waves.

**Wave-1 concurrency:** `asyncio.gather(*channels, return_exceptions=True)`. A degraded channel must not fail the request — log it, drop it from the fusion input, and report `channel_hits` in the response `meta`. This is only possible *because* channels are separate calls; it is the strongest argument against doing all five in one giant SQL statement.

---

### Pattern 6: RetrievalPolicy as a value object, keyed off the prompt template

**Where k and weights belong:** in a frozen dataclass resolved per request — not in env vars, not in module constants scattered across channels, and (in v1) not in the database.

```python
# retrieval/policy.py
@dataclass(frozen=True)
class RetrievalPolicy:
    rrf_k: int = 60                    # 업계 표준 상수. 라벨링된 질의 셋 없이 건드리지 말 것
    weights: Mapping[Channel, float] = ...   # 실제 튜닝 노브
    limits:  Mapping[Channel, int]   = ...   # 채널별 후보 수 (두 번째 노브)
    graph_hops: int = 2
    graph_seeds: int = 5
    context_budget_tokens: int = 6000

DEFAULT = RetrievalPolicy(weights={c: 1.0 for c in Channel}, limits={c: 30 for c in Channel})

# ask 템플릿 target_type → 정책. 상황별 프롬프트 칩이 곧 검색 의도이기도 하다.
POLICIES = {
    "ask_evidence":  replace(DEFAULT, weights={**base, SOURCE_VEC: 1.5, SOURCE_LEX: 1.5}),
    "ask_concept":   replace(DEFAULT, weights={**base, WIKI_VEC: 1.5, GRAPH: 1.3}),
    ...
}
```

**Rationale:** the product already ships four situational `ask` templates. A situation *is* a retrieval intent — "원문 근거를 보여줘" wants source channels upweighted; "개념을 정리해줘" wants wiki + graph. Keying the policy off the same `target_type` the prompt is keyed off means the two never drift.

**On k specifically:** k = 60 is the near-universal empirical default (Elasticsearch, Azure AI Search, ParadeDB, Chroma, MariaDB). Low k lets one channel's top hit dominate; high k rewards cross-channel consensus. **Do not tune k first.** Per-channel weights and per-channel `limit` are the knobs that move recall at this scale; k only matters once you have a labeled query set to measure against.

**v2 move, noted not taken:** promoting the policy to a `prompt_templates.retrieval_policy jsonb` column so it is editable per workspace. Requires a migration and, more importantly, requires having measured something first. Keep it in code for v1.

---

### Pattern 7: Server-issued citation anchors with an alias table

**What:** anchors are opaque tokens the model may only *copy*. The server issues them, the server resolves them, and anything the model emits that is not in the issued set is discarded.

**The flow:**

```
assemble()   ── issues alias table ──►  {"w1": wiki_id, "s3": chunk_id, ...}
     │                                            │
     ▼                                            │
context block:                                    │
  [[wiki:정규화]] 정규화란 …                       │
  [[src:s3]] 원문 발췌 …                           │
     │                                            │
     ▼ (OpenRouter)                               │
answer text containing [[wiki:정규화]] [[src:s3]]  │
     │                                            │
     ▼ parse (one regex, one module) ◄────────────┘
resolved → citations[] + double_citation{}   |   unresolved → dropped + counted
```

**Recommended refinement (flag as a phase decision).** `codebase/ARCHITECTURE.md` specifies `[[src:chunk_id]]` literally, and `chunk_id` is a UUID — 36 characters the model must reproduce byte-perfect. LLMs mangle UUIDs, and a mangled anchor is a *silently dropped citation*, i.e. exactly the product's core-value failure. **Use short per-request aliases inside the prompt (`[[src:s3]]`) and resolve them to `chunk_id` server-side.** Wiki anchors keep the slug verbatim — slugs are short, meaningful, and already the model's vocabulary from the compile prompt. The wire format the frontend sees still carries `chunk_id`; only the prompt-side token shrinks. Zero cost, materially higher citation fidelity.

**Response contract (backend ↔ frontend):**

```jsonc
{
  "answer": "정규화는 … [[wiki:정규화]] … 원문에서는 … [[src:s3]] 라고 기술합니다.",
  "citations": [
    { "marker": "wiki:정규화", "kind": "wiki", "ordinal": 1,
      "wiki": { "id": "…", "slug": "정규화", "title": "…", "category": "개념",
                "verification_status": "verified", "confidence": "high", "disputed": false } },
    { "marker": "src:s3", "kind": "source", "ordinal": 2,
      "source": { "chunk_id": "…", "raw_source_id": "…", "title": "…", "source_type": "pdf",
                  "chunk_index": 3, "char_start": 1024, "char_end": 1536, "excerpt": "…" } }
  ],
  "double_citation": {                      // 문서에 이미 약속된 형태. 중복 제거 + 최초 등장 순
    "wiki_pages":  [ /* … */ ],
    "raw_sources": [ /* … */ ]
  },
  "meta": { "channel_hits": {"wiki_vec": 12, "graph": 4, …}, "unresolved_anchors": 0,
            "policy": "ask_evidence", "latency_ms": 2140 }
}
```

**Frontend contract rule:** the frontend never *interprets* an anchor — it splits `answer` on the shared regex and looks the `marker` up in `citations`. A marker with no entry renders as plain text, never as a link. `unresolved_anchors > 0` is the citation-faithfulness alarm and belongs on a dashboard, not in a log file.

**Streaming version (SSE):** the citations map cannot be sent until the answer is complete, so:

| event | payload | when |
|---|---|---|
| `meta` | `{request_id, policy, channel_hits}` | immediately after retrieval, before the first token — gives the UI "12개 근거에서 답변 중" |
| `delta` | `{text}` | per token chunk |
| `citations` | the `citations` + `double_citation` block above | after generation, after server-side validation |
| `done` | `{usage, latency_ms, model}` | terminal |
| `error` | `{code, message}` — **redacted**, never a raw provider exception | terminal |

The client renders anchors as grey placeholder chips during `delta`, then upgrades them in place when `citations` arrives.

**Use POST + `fetch` + `ReadableStream`, not `EventSource`.** `EventSource` is GET-only and cannot set an `Authorization` header — the single most common trap in this exact stack.

**Known gap:** there is no answers table (`CONCERNS.md`), so answers are ephemeral: no permalinks, no feedback loop, and `disputed` has no evidence trail. Either accept explicitly for v1 or add `ask_answers` + `ask_citations` in `0007`. Decide it, don't drift into it.

---

### Pattern 8: Reads direct to Supabase, writes and compute through FastAPI

**What:** RSC pages read `wiki_pages`, `wiki_links`, `raw_sources` and `jobs` directly through the `@supabase/ssr` server client. RLS is the authorization layer, so there is nothing FastAPI would add except a hop and a hand-written endpoint. FastAPI owns only what needs orchestration: **ingest** (Storage upload + `raw_sources` + enqueue), **ask** (retrieval + LLM + citation resolution), and **graph query** (the N-hop CTE, if the canvas needs anything beyond a flat `wiki_links` select).

**Why:** it removes roughly half the read API surface from the roadmap, and it puts the authorization decision in the one place already validated 38/38. Building `GET /w/{id}/wiki/{slug}` in FastAPI would be re-implementing, in Python, a check Postgres is already making.

**Trade-offs:** two data-access idioms in the frontend (`supabase` for reads, `lib/api.ts` for writes). Mitigate with one rule stated in the README: *if it's a select, use supabase; if it costs money or changes state, use the API.* Also: PostgREST `max_rows = 1000` applies to direct reads — every list must paginate, and the graph canvas is the surface most likely to hit it first.

---

## Data Flow

### Request Flow — question to dual-cited answer

```
AskPanel (client) ──POST──► app/api/ask/route.ts (BFF, reads session cookie)
                                     │ Authorization: Bearer <user JWT>
                                     ▼
                            FastAPI POST /w/{id}/ask
                                     │ deps: principal → WorkspaceContext(UserDb)
                                     ▼
                            retrieval/pipeline.py
                              ├─ embed(query)                      → providers/embed
                              ├─ gather(ch1..ch4) via rpc(...)     → Postgres (RLS applies)
                              ├─ fusion.rrf(policy)                → pure
                              ├─ ch5 graph expand(seeds)           → Postgres
                              ├─ fusion.rrf(policy)                → pure
                              └─ assemble() → ContextBlock + alias table   → pure
                                     ▼
                            prompts.render(ask template, {{question}}, {{wiki_context}}, {{source_context}})
                                     ▼
                            providers/llm stream ──► SSE: meta → delta* → citations → done
                                     ▲
                            citations.parse(answer, alias_table)   → pure
```

Every box marked *pure* is a unit test with no Docker and no API key.

### Write Flow — source to wiki

```
Dropzone ──► BFF signs upload ──► Supabase Storage {workspace_id}/{raw_source_id}/{filename}
                                     │
         ──POST /w/{id}/sources──► FastAPI: insert raw_sources (content_hash dedupe)
                                     │  ON CONFLICT (workspace_id, content_hash) → 200 "이미 수집됨"
                                     ▼
                            enqueue source.parse  (jobs_dedup_idx makes double-click a no-op)
                                     ▼
  worker: claim_job → parse → upsert source_chunks + tail-delete
                            └─ complete_job_and_chain → wiki.compile
                            └─ complete_job_and_chain → source.embed
          wiki.compile → OpenRouter + Pydantic (3 retries) → upsert wiki_pages (workspace_id, slug)
                            └─ chain → wiki.link_sync → upsert wiki_links (미해결 = 레드 링크)
                            └─ chain → wiki.embed     → upsert wiki_embeddings
```

### State Management

```
Postgres  ── the only durable state. No cache, no broker, no graph store.
   │
   ├─ session      → cookie, refreshed in middleware.ts (only cookie writer)
   ├─ workspace    → URL segment /w/[workspaceId]  (never client state alone)
   ├─ server data  → RSC fetch, passed down as props; no client refetch
   ├─ job progress → poll jobs (4-link chain) every 2s from a client island
   └─ answer stream→ reducer over SSE events inside AskPanel; nothing global
```

### Key Data Flows

1. **Tokenizer round trip.** `domain/tokenizer.py` is called by the parse handler (writes `search_tsv` + `tsv_tokenizer_version`) *and* by channels 3–4 (builds `phraseto_tsquery('simple', bigram(q))`). One module, two callers, one version constant. Divergence fails silently — this is the single highest-value property test in the project: index a corpus, query each document with its own text, assert self-retrieval.
2. **Anchor round trip.** `domain/citations.py` both emits anchors during assembly and parses them out of the answer, so the emit/parse pair can never disagree. The alias table is the authorization boundary for citations.
3. **Job chain as progress model.** The UI derives progress from `jobs` rows alone. No progress table, no websocket, no extra endpoint.
4. **Red link as backlog.** `wiki_links.to_wiki_id IS NULL` is read by the wiki viewer (render red) and by the graph canvas (render ghost node) with no additional state.

---

## Suggested Build Order

| # | Component | Depends on | Why here |
|---|-----------|-----------|----------|
| 0 | `0005_storage.sql` | — | Hard ordering constraint: must land before the first cloud `db push`. Blocks all ingest. |
| 1 | Monorepo tooling + **split settings** | 0 | The settings split *is* the enforcement mechanism for the central invariant. Retrofitting it later means touching every module. |
| 2 | `db/user.py` + `db/service.py` + `deps.py` + 0-rows→403 + ruff ban + one isolation test | 1 | Security spine. Everything downstream imports it. Build before any feature. |
| 3 | `domain/tokenizer.py` (+ round-trip test) | 1 | Shared by the write path (5) and the read path (8). If ingest ships first it will grow its own tokenizer and retrieval inherits a silent mismatch. Cheapest to satisfy by building it before both. |
| 4 | Worker skeleton: loop, registry, SIGTERM, reaper, `noop` job type | 2 | Proves the queue contract end-to-end before a single LLM dollar is spent. |
| 5 | `0007` (retrieval fns + `jobs_dedup_idx` + `complete_job_and_chain`) | 0 | One migration, consumed by both 6 and 8. Do it once. |
| 6 | Ingest API + `source.parse` handler | 2,3,4,5 | First real chain link; exercises Storage, dedupe, enqueue, tail-delete. |
| 7 | `wiki.compile` + `wiki.link_sync` handlers | 6 | Needs the LLM provider + Pydantic repair loop + `{{var}}` renderer. |
| 7b | `source.embed` + `wiki.embed` handlers | 6 (source), 7 (wiki) | `source.embed` is independent of compile — **parallelizable with 7**. |
| 8 | Retrieval channels + RRF + assembly | 3,5 | Testable against fixtures *before* real embeddings exist. Can start alongside 7. |
| 9 | Ask endpoint + citation resolution + SSE | 7b,8 | The core-value surface. |
| 10 | Dashboard: auth, middleware, workspace shell | 2 | Only needs the JWT contract. **Start in parallel with 6.** |
| 11 | Dropzone + job chain progress | 6,10 | |
| 12 | Wiki viewer + red links | 7,10 | Direct Supabase reads — needs no FastAPI endpoint. |
| 13 | Ask UI + dual-citation cards | 9,10 | |
| 14 | Graph canvas (Cytoscape) | 7,10 | Last: least load-bearing, most likely to hit the 1000-row cap, and `dynamic(ssr:false)` makes it isolated. |

**Two tracks after step 4:** backend pipeline (6→9) and frontend shell (10→11) run in parallel; they meet at 13.

**Ordering rationale worth restating:** items 1, 2 and 3 are all "build the constraint before the feature." Each of them is a rewrite if deferred — the settings split touches every module, the `UserDb` wrapper touches every query, and the tokenizer touches both the write and read paths with a failure mode that produces no error.

---

## Scaling Considerations

Framed by workspace size rather than user count — this is a small-team product on a $5/mo budget.

| Scale | Adjustments |
|-------|-------------|
| 1–5 workspaces, <500 sources | Nothing. Single API dyno, single worker, semaphore 4. Defaults everywhere. |
| ~50 workspaces, ~10k chunks | Add `btree_gin` and a composite `(workspace_id, search_tsv)` GIN if lexical latency shows tenant post-filtering. Tune `hnsw.ef_search`. Add a `jobs` retention sweep (`succeeded` older than 30d) to the worker loop. Paginate every list. |
| 500+ workspaces / >1M chunks | Second Railway worker replica (`claim_job` is already `SKIP LOCKED`-safe, so this is a config change). Type-sharded partial poll indexes. Partial HNSW indexes for the largest tenants, or partition by `workspace_id`. Consider moving the answer path off the same dyno as ingest. |

### Scaling Priorities

1. **First bottleneck is cost, not compute.** OpenRouter forfeits Anthropic prompt caching and the compile prompt repeats per source, so spend is linear in source count with no discount. Fix order: (a) per-workspace monthly ceiling enforced at enqueue time, (b) `jobs_dedup_idx` to kill duplicate compiles, (c) revisit direct Anthropic if the caching delta is material.
2. **Second is worker throughput.** Single resident process, LLM-wait-bound. Raise the in-flight semaphore first (it is nearly free — the process is idle on network), then add a replica. Do not add a broker; `SKIP LOCKED` at 8 workers / 400 jobs is already verified.
3. **Third is HNSW post-filter recall on large workspaces.** Both indexes are unpartitioned and untuned (default `m`/`ef_construction`, created on empty tables). `strict_order` mitigates the "fewer than k rows" symptom but not the recall cliff. Measure before tuning.
4. **Fourth is the PostgREST 1000-row cap** — the graph canvas hits it first.

---

## Anti-Patterns

*(DB-layer anti-patterns are already catalogued in `.planning/codebase/ARCHITECTURE.md`; these are the application-layer ones.)*

### AP1: Mutating a shared Supabase client's auth token per request

**What people do:** hold one module-level `AsyncClient` and call `client.postgrest.auth(token)` at the top of each handler to "avoid client construction overhead."
**Why it's wrong:** in an async FastAPI process, two concurrent requests interleave between `auth()` and `execute()`. Request A can execute with request B's token — a cross-tenant read that RLS will happily authorize because, from Postgres's point of view, it *is* B. This is the one failure mode RLS cannot save you from.
**Do this instead:** share the `httpx.AsyncClient` (that is where the real cost is — client-wrapper construction is cheap) and bind the JWT per request or per call. Never mutate shared auth state.

### AP2: Gating `service_client()` behind a config flag

**What people do:** `if settings.admin_mode: client = service_client()`.
**Why it's wrong:** a flag is a runtime value; someone will set it in the wrong environment, and the failure is silent and total.
**Do this instead:** absence of capability. The API process's settings model has no service-key field; the key is not in its environment.

### AP3: Fusing all five channels inside one giant SQL statement

**What people do:** one CTE chain doing five retrievals, RRF arithmetic, and ranking in Postgres.
**Why it's wrong:** you lose per-channel failure isolation (one slow channel fails the whole request rather than degrading), you cannot unit-test the fusion, and reweighting per prompt template becomes a migration.
**Do this instead:** five small SQL functions + `asyncio.gather` + pure-Python fusion. Wall clock is `max(channel)`, not `sum(channel)`, so the round-trip argument does not hold.

### AP4: Letting the model's citation ids reach the response unvalidated

**What people do:** regex the answer, look the id up, render whatever comes back.
**Why it's wrong:** a hallucinated or mangled id either renders as a broken link or, worse, resolves to an unrelated real row. Dual citation is the product's core value; a wrong citation is worse than no citation.
**Do this instead:** validate every parsed marker against the request's alias table. Unmatched markers are dropped, counted in `unresolved_anchors`, and rendered as plain text.

### AP5: `EventSource` for the ask stream

**What people do:** `new EventSource('/api/ask?q=…')`.
**Why it's wrong:** GET-only, no custom headers, so no `Authorization` — which pushes people toward putting the token in a query string.
**Do this instead:** POST + `fetch` + `ReadableStream` reader on the client; the Next route handler returns the upstream stream unbuffered (`runtime = 'nodejs'`, `dynamic = 'force-dynamic'`).

### AP6: Storing the active workspace only in React state

**What people do:** a `WorkspaceProvider` context with the selected id.
**Why it's wrong:** the URL and the state drift on refresh, back-navigation and deep links. Worse, a stale id produces queries RLS answers with an *empty result set and no error* — indistinguishable from "this workspace is empty."
**Do this instead:** `/w/[workspaceId]/…` is the source of truth; a cookie stores only "last used" for redirecting `/`.

### AP7: One monolithic `ingest` job

**What people do:** parse + compile + link + embed in a single handler because "it's one logical operation."
**Why it's wrong:** its p99 can exceed the 15-minute reap window, so healthy jobs get stolen and double-billed; and any late-stage failure re-runs the expensive early stages.
**Do this instead:** the four-link chain, advanced atomically with completion.

### AP8: Enqueuing the next stage before completing the current one

**What people do:** `enqueue(next); complete_job(current)` as two calls.
**Why it's wrong:** a crash between them leaves the current job to be reaped and re-run, enqueuing the next stage twice.
**Do this instead:** `complete_job_and_chain()` — one function, one transaction — plus `jobs_dedup_idx` as the belt-and-braces.

### AP9: Writing raw provider exceptions to `jobs.last_error`

**What people do:** `fail_job(id, str(exc))`.
**Why it's wrong:** `jobs_select_member` grants `select *` to every workspace member including viewers, and provider exceptions routinely echo request URLs, model names and occasionally auth-header fragments.
**Do this instead:** redact to a structured summary. Longer term, expose `jobs` to users through a projecting view.

### AP10: Re-fetching in a client island what the RSC already loaded

**What people do:** `'use client'` at the page level, then `useEffect` + `supabase.from(...)`.
**Why it's wrong:** doubles the query, moves auth to the browser, and loses streaming SSR.
**Do this instead:** RSC fetches, passes serialized props down; the island owns interaction only.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes / gotchas |
|---------|---------------------|-----------------|
| Supabase Auth | Cookie session via `@supabase/ssr`; `middleware.ts` is the only cookie writer; FastAPI verifies the Bearer JWT | Use `getUser()` server-side (verified), never `getSession()` (unverified cookie read). Local auth config is materially weaker than production should be — treat `config.toml` as the prod contract before the first push. |
| Supabase Postgres | API → PostgREST + `security invoker` RPC under the user JWT; worker → `service_role` with explicit `workspace_id` | `max_rows = 1000`. RLS blocks return 0 rows, not errors. |
| Supabase Storage | BFF signs an upload URL; browser uploads directly; path `{workspace_id}/{raw_source_id}/{filename}` | `0005` must define the `storage.objects` policy that checks the first path segment against membership — the path convention is currently a comment, not an enforcement. |
| OpenRouter (compile + answer) | `providers/llm.py` behind `CompileModel` / `AnswerModel` protocols; model from `LLM_MODEL` env | No native structured output → prompt + Pydantic + 3 retries. No prompt caching → cost is linear in source count. Set an explicit request timeout well under the reap window. |
| OpenAI (embeddings) | `providers/embed.py` behind an `Embedder` protocol; batch per job | Dimension hard-coded to 1536 in the schema with no `embedding_model` column — a partial re-embed is indistinguishable from a complete one. Consider adding `embedding_version` mirroring `tsv_tokenizer_version`. |
| Railway | Two services from one repo via `Procfile`: `web: api`, `worker: worker` | The service key env var is set **only** on `worker`. This is the deployment half of Pattern 1. |
| Vercel | Dashboard only | Route handlers proxying SSE must not buffer; verify streaming survives the platform. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Dashboard ↔ Postgres (reads) | Direct, `@supabase/ssr` server client, RLS | No FastAPI hop. Paginate everything. |
| Dashboard ↔ FastAPI (writes, ask) | BFF route handler forwards the session JWT as Bearer | Keeps CORS and token handling in one place. |
| FastAPI ↔ Worker | **Only** through the `jobs` table | No HTTP between them, ever. Enqueue is a row insert. |
| API ↔ retrieval | `retrieval/pipeline.py` takes `WorkspaceContext` | Retrieval never constructs a client. |
| Handlers ↔ queue | `claim_job` / `complete_job_and_chain` / `fail_job` only | Never `UPDATE jobs` directly. |
| `domain/` ↔ everything | Imported by all, imports nothing | The testability seam. |

---

## Open Decisions This Research Surfaces

These need a call during phase planning; none of them contradict the built data layer.

1. **Short prompt-side citation aliases (`[[src:s3]]`) vs literal UUIDs (`[[src:<uuid>]]`).** Recommendation: aliases. Affects the assembly/parse contract and the ask template text.
2. **Migration `0007` scope** — retrieval functions + `jobs_dedup_idx` + `complete_job_and_chain`, and optionally `ask_answers`. Recommendation: all four; the answers table is the only one genuinely optional for v1.
3. **Job progress: polling vs Supabase Realtime.** Recommendation: poll (2s) for v1. Realtime requires adding `jobs` to the publication — a schema change, not a freebie.
4. **Direct-Supabase reads from RSC vs a full FastAPI read API.** Recommendation: direct reads. Cuts roughly half the read endpoints from the roadmap.
5. **`reap_stale_jobs` timeout value.** Must be set explicitly (not left at the 15-minute default) to ≈3× the slowest single stage's p99 once stage latencies are measured in the ingest phase.

---

## Sources

- [Supabase — Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security) · [Postgres Roles](https://supabase.com/docs/guides/database/postgres/roles) · [service_role client troubleshooting](https://supabase.com/docs/guides/troubleshooting/why-is-my-service-role-key-client-getting-rls-errors-or-not-returning-data-7_1K9z) — MEDIUM
- [supabase/discussions#33811 — Supabase + FastAPI, per-request RLS](https://github.com/orgs/supabase/discussions/33811) — shared-client token mutation is unsafe under concurrency — MEDIUM
- [Supabase — Creating a client for SSR](https://supabase.com/docs/guides/auth/server-side/creating-a-client) · [Server-Side Auth for Next.js](https://supabase.com/docs/guides/auth/server-side/nextjs) — MEDIUM
- [Supabase — RAG with Permissions](https://supabase.com/docs/guides/ai/rag-with-permissions) · [Securing Supabase RPC functions](https://www.audityour.app/guides/supabase-rpc-security-guide) — `security invoker` preserves RLS — MEDIUM
- [Elasticsearch — Reciprocal rank fusion](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion) · [Azure AI Search — Hybrid ranking (RRF)](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking) · [ParadeDB — RRF](https://www.paradedb.com/learn/search-concepts/reciprocal-rank-fusion) — k=60 default, cross-checked across four independent implementations — HIGH
- [pgvector README / HNSW config](https://github.com/pgvector/pgvector) · [Supabase — HNSW indexes](https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes) — `iterative_scan` GUC semantics — MEDIUM
- [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices) — layer vs feature structure, router-level dependencies — LOW
- [River — Writing reliable workers](https://riverqueue.com/docs/reliable-workers) · [Designing Laravel queues that survive failure](https://emtiazzahid.github.io/writing/designing-laravel-queues-that-survive-failure/) — "one job, one responsibility", chained stages, at-least-once idempotency — MEDIUM
- [Why tenant context must be scoped per transaction](https://dev.to/m_zinger_2fc60eb3f3897908/why-tenant-context-must-be-scoped-per-transaction-3aop) — the `SET LOCAL` pooling leak that motivates rejecting raw asyncpg — MEDIUM
- [FastAPI — Server-Sent Events](https://fastapi.tiangolo.com/tutorial/server-sent-events/) · [Upstash — SSE streaming LLM responses in Next.js](https://upstash.com/blog/sse-streaming-llm-responses) — MEDIUM
- Internal ground truth (HIGH): `.planning/codebase/ARCHITECTURE.md`, `CONCERNS.md`, `CONVENTIONS.md`, `STRUCTURE.md`, `STACK.md`, `.planning/PROJECT.md`

---
*Architecture research for: multi-tenant LLM-compiled wiki with dual-citation hybrid retrieval*
*Researched: 2026-08-01*
