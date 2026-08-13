# Phase 5: Citation Integrity and Answer APIs - Pattern Map

**Mapped:** 2026-08-11
**Files analyzed:** 13 new + 2 modified
**Analogs found:** 13 / 13 (all have a strong, directly-read in-repo precedent — 05-RESEARCH.md already did most of this legwork; this file adds concrete line-anchored excerpts for the planner)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `apps/worker/src/worker/llm_stream.py` | service (worker-internal listener) | streaming | `apps/worker/src/worker/query_embedding.py` | exact (same shape: `Service` class + `create_*_app` factory + token-bucket + bearer auth) |
| `apps/worker/src/worker/__main__.py` (extend `_serve_query_embeddings`) | entry point / process wiring | event-driven | same file, `_serve_query_embeddings` (lines 37-59) | exact (extend, do not duplicate) |
| `apps/worker/src/worker/llm.py` (add `stream_chat()` sibling function) | service (provider client) | streaming | same file, `complete_structured()` (lines 138-208) + `openrouter_client()` (81-106) | exact (sibling function, same module, same client-construction helper reused) |
| `apps/worker/src/worker/handlers/parse.py` (add `strip_forged_anchors()` call before line 151) | transform step in existing handler | file-I/O / transform | same file, existing `chunk_text(content)` call site (line 151) | exact (single insertion point, already located) |
| `apps/api/src/api/services/ask.py` | service | request-response + streaming | `apps/api/src/api/services/retrieval.py` | strong (same DI shape: injected HTTP client protocol, dataclass result, `_rpc_channel`-style small helpers) |
| `apps/api/src/api/routers/ask.py` | controller (route) | streaming (SSE) | `apps/api/src/api/routers/retrieval.py` | strong (identical `HTTPBearer` + `_user_db()` + settings-from-`request.app.state` wiring; adds `StreamingResponse` on top) |
| `apps/api/src/api/routers/wiki.py` (verify endpoint + detail reads if needed) | controller (route) | CRUD (single-row update) | `apps/api/src/api/routers/jobs.py` (`retry_job`/`cancel_job` shape) + `UserDb.update_one()` | exact (0-rows-affected → `WorkspaceForbidden` → 403 pattern reused verbatim) |
| `apps/api/src/api/routers/graph.py` | controller (route) | request-response (bounded graph read) | `apps/api/src/api/routers/retrieval.py` (RPC-calling route shape) + `RetrievalService._graph()` (retrieval.py lines 230-262) | strong (same `UserDb.rpc()` call shape, same malformed-row defense) |
| `packages/core/src/nexuswiki_core/citations.py` | utility | transform (regex) | `apps/worker/src/worker/llm.py`'s `_PLACEHOLDER` regex (line 59) + `render_template()` (109-135) | role-match (single-scan regex substitution is the established house style) |
| `packages/core/src/nexuswiki_core/sentences.py` | utility | transform | no existing sentence-splitting code; nearest analog is `nexuswiki_core.tokenizer.bigram/normalize` (regex-based stdlib-only text transform, same package) | role-match, no direct analog (see "No Analog Found") |
| `apps/api/src/api/settings.py` (extend `ApiSettings`) | config | — | existing `QUERY_EMBEDDING_INTERNAL_URL`/`_TOKEN`/`_TIMEOUT_SECONDS` fields | exact (add `LLM_STREAM_INTERNAL_*` siblings) |
| `apps/worker/src/worker/settings.py` (extend `WorkerSettings`) | config | — | existing `QUERY_EMBEDDING_INTERNAL_TOKEN` + rate/concurrency fields | exact |
| `supabase/migrations/0012_ask_citation_and_graph.sql` | migration | batch (DDL + data UPDATE) | `supabase/migrations/0011_retrieval.sql` (`expand_wiki_graph`, security invoker/stable/set search_path pattern) + `0010_budget_error_sqlstate.sql` (numbered-migration style) | exact |
| `apps/worker/tests/test_llm_stream.py` | test | streaming | `apps/worker/tests/test_query_embedding.py` | exact (ASGITransport + bounded `asyncio.wait_for` pattern per Pitfall 5) |
| `apps/api/tests/test_ask_router.py`, `test_ask_citations.py` | test | request-response | existing `apps/api/tests/test_*.py` for `retrieval.py`/`jobs.py` (not read this pass — same package, same pytest-asyncio convention per RESEARCH.md's Validation Architecture) | role-match |

## Pattern Assignments

### `apps/worker/src/worker/llm_stream.py` (service, streaming)

**Analog:** `apps/worker/src/worker/query_embedding.py` (full file, 129 lines — read in full)

**Imports pattern** (lines 1-17):
```python
"""Private, worker-owned query-embedding HTTP boundary."""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict

from worker.embedding import EMBEDDING_DIMENSIONS

EmbeddingFunction = Callable[[str], Awaitable[list[float]]]
MonotonicClock = Callable[[], float]
```
`LlmStreamService` should mirror this exactly, swapping `EmbeddingFunction` for a `ChatStreamFunction = Callable[[LlmChatRequest], AsyncIterator[bytes]]`.

**Auth-before-work pattern** (lines 86-97, the entire contract to replicate):
```python
async def embed(
    self, request: QueryEmbeddingRequest, authorization: str | None
) -> QueryEmbeddingResponse:
    # Authenticate before quota/provider work, so unauthenticated calls cannot
    # consume capacity.
    if authorization != f"Bearer {self._internal_token}":
        raise HTTPException(status_code=401, detail="internal_unauthorized")
    if not request.text or len(request.text) > self._max_text_chars:
        raise HTTPException(status_code=422, detail="invalid_query")
    # A reservation covers every valid provider attempt, including failures,
    # timeouts, malformed output, and cancellation after work has begun.
    await self._reserve_token()
```

**Token-bucket rate limiter — copy verbatim, do NOT reinvent** (lines 70-84):
```python
async def _reserve_token(self) -> None:
    """Reserve one provider-attempt token, refilling from a monotonic clock."""
    async with self._request_lock:
        now = self._monotonic()
        elapsed = max(0.0, now - self._last_refill)
        self._tokens = min(
            float(self._rate_capacity),
            self._tokens + elapsed * self._refill_tokens_per_second,
        )
        # A clock cannot normally go backwards, but retaining the later value
        # makes a faulty injected clock unable to mint quota by oscillating.
        self._last_refill = max(self._last_refill, now)
        if self._tokens < 1:
            raise HTTPException(status_code=429, detail="rate_limited")
        self._tokens -= 1
```
⚠️ This is a monotonic-clock token bucket, NOT a lifetime counter — `docs/architecture/query-embedding-boundary.md` documents commit `6a14144` fixed exactly this bug once already in a prior listener. `LlmStreamService` needs its own `asyncio.Semaphore` and its own instance of this exact bucket shape (constants differ: research recommends ~2 concurrency / lower rate given 120s streaming calls vs. 5s embedding calls).

**App factory pattern** (lines 117-128):
```python
def create_query_embedding_app(service: QueryEmbeddingService) -> FastAPI:
    """Small ASGI app intended for the Railway private network only."""
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

    @app.post("/internal/query-embedding", response_model=QueryEmbeddingResponse)
    async def query_embedding(
        request: QueryEmbeddingRequest,
        authorization: Annotated[str | None, Header()] = None,
    ) -> QueryEmbeddingResponse:
        return await service.embed(request, authorization)

    return app
```
Per D-01's researcher discretion (resolved: same-process second route, not a second app/port), the new `/internal/llm-chat` route should be `add_llm_stream_route(app, service)` — a function that takes the *existing* FastAPI app instance and adds a route to it, rather than a second `create_*_app()`. Return type differs: `StreamingResponse` instead of a `response_model`-validated JSON body.

---

### `apps/worker/src/worker/__main__.py` (extend, entry point)

**Analog:** same file, `_serve_query_embeddings` (lines 37-59) and its wiring into `main()` (lines 155-172)

```python
async def _serve_query_embeddings(settings: WorkerSettings, stop: asyncio.Event) -> None:
    """Run the private listener until the queue process receives its stop signal."""
    if not settings.QUERY_EMBEDDING_INTERNAL_TOKEN:
        # No listener is safer than an unauthenticated listener during local setup.
        return
    service = QueryEmbeddingService(
        lambda text: _embed_query(settings, text),
        internal_token=settings.QUERY_EMBEDDING_INTERNAL_TOKEN,
        max_text_chars=settings.QUERY_EMBEDDING_MAX_TEXT_CHARS,
        timeout_seconds=settings.QUERY_EMBEDDING_TIMEOUT_SECONDS,
        max_concurrency=settings.QUERY_EMBEDDING_MAX_CONCURRENCY,
        rate_capacity=settings.QUERY_EMBEDDING_RATE_CAPACITY,
        refill_tokens_per_second=settings.QUERY_EMBEDDING_RATE_REFILL_TOKENS_PER_SECOND,
    )
    server = uvicorn.Server(
        uvicorn.Config(
            create_query_embedding_app(service), host="0.0.0.0", port=8081, log_level="warning"
        )
    )
    server_task = asyncio.create_task(server.serve())
    await stop.wait()
    server.should_exit = True
    await server_task
```
```python
async with asyncio.TaskGroup() as group:
    queue_task = group.create_task(
        run_queue_loop(db, worker_id=worker_id, stop=stop, ...)
    )
    group.create_task(_serve_query_embeddings(settings, stop))
```
**Since D-01/Pattern 1 resolved "same process, second route"**: `create_query_embedding_app(service)` must become a shared app builder that both `add_llm_stream_route()` and the existing query-embedding route attach to — i.e. `_serve_query_embeddings` should be extended (renamed, e.g. `_serve_internal_listeners`) to build one `FastAPI()` app, call both `add_query_embedding_route(app, qe_service)` and `add_llm_stream_route(app, llm_service)` on it, then wrap the single app in one `uvicorn.Server`. Do not add a second `uvicorn.Server`/`server_task` pair — the research explicitly flags this doubles SIGTERM-shutdown surface for no isolation benefit (`railway.json`'s private-networking toggle is per-service, not per-port).

---

### `apps/worker/src/worker/llm.py` (add `stream_chat()` sibling function)

**Analog:** same file — `openrouter_client()` (81-106) reused as-is; `complete_structured()` (138-208) is the sibling shape to diverge from, NOT rewrite.

**Client construction — reuse verbatim** (lines 81-106):
```python
def openrouter_client(
    settings: WorkerSettings,
    *,
    timeout_seconds: float = LLM_REQUEST_TIMEOUT_SECONDS,
) -> httpx.AsyncClient:
    api_key = getattr(settings, "OPENROUTER_API_KEY", None)
    if not isinstance(api_key, str) or not api_key:
        raise TypeError(
            "openrouter_client는 OPENROUTER_API_KEY를 가진 WorkerSettings를 요구한다 — "
            f"{type(settings).__name__}에는 그 필드가 없다 (02-CONTEXT.md > D-06)"
        )
    return httpx.AsyncClient(
        base_url=OPENROUTER_BASE_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=httpx.Timeout(timeout_seconds),
    )
```

**Body-building pattern to mirror for a streaming chat body** (lines 214-242, `_chat_body`) — the new `stream_chat()` needs its own body builder with `"stream": True` and no `response_format` (streaming + structured-JSON-with-retry are different call shapes per RESEARCH.md's "State of the Art" table — keep as sibling functions):
```python
body: dict[str, Any] = {
    "model": settings.LLM_MODEL,
    "messages": messages,
    "usage": {"include": True},   # ⚠️ required or cost_micros silently becomes 0
}
```

**Error-transport pattern to reuse** (lines 289-296):
```python
async def _send(client: httpx.AsyncClient, body: dict[str, Any]) -> httpx.Response:
    try:
        return await client.post("/chat/completions", json=body)
    except httpx.HTTPError:
        raise ProviderError(provider=PROVIDER_NAME, status_code=None, kind="transport") from None
```

**Cost extraction — reuse verbatim** (lines 333-344, `_cost_micros`) for the post-stream `insert_usage_event()` call.

**Template rendering — reuse `render_template()` exactly, do not reimplement** (lines 109-135):
```python
def render_template(template: str, values: Mapping[str, str]) -> str:
    matched = _PLACEHOLDER.findall(template)
    if template.count("{{") != len(matched):
        raise ValueError(...)
    def substitute(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            raise ValueError(f"플레이스홀더 {{{{{key}}}}}에 대응하는 값이 없다")
        return values[key]
    return _PLACEHOLDER.sub(substitute, template)
```
⚠️ Never `str.format` — CLAUDE.md anti-pattern, and single-scan substitution is what stops a source's `{{...}}` from re-injecting.

---

### `apps/worker/src/worker/handlers/parse.py` (CITE-06 insertion point)

**Exact insertion point** — before line 151:
```python
    chunks = chunk_text(content)
```
Becomes:
```python
    content = strip_forged_anchors(content)   # CITE-06 / D-04, before chunk_text
    chunks = chunk_text(content)
```
verified against `apps/worker/src/worker/handlers/parse.py:130-151` (both `url` and non-url branches converge on `content` before this line, so one insertion point covers all 3 source types per D-04's rationale).

---

### `apps/api/src/api/services/ask.py` (service, request-response + streaming)

**Analog:** `apps/api/src/api/services/retrieval.py` (full file, 396 lines — read in full)

**DI/Protocol pattern for the worker-internal HTTP client** (lines 19-62):
```python
class QueryEmbeddingClient(Protocol):
    async def embed(self, text: str) -> list[float]: ...

class HttpQueryEmbeddingClient:
    """The API's only embedding capability: an authenticated private worker call."""

    def __init__(self, client: httpx.AsyncClient, *, url: str | None, token: str | None,
                 timeout_seconds: float) -> None:
        self._client, self._url, self._token, self._timeout_seconds = client, url, token, timeout_seconds

    async def embed(self, text: str) -> list[float]:
        if not self._url or not self._token:
            raise RuntimeError("query_embedding_unavailable")
        response = await self._client.post(
            f"{self._url.rstrip('/')}/internal/query-embedding",
            json={"text": text},
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=self._timeout_seconds,
        )
        if response.is_error:
            raise RuntimeError("query_embedding_unavailable")
        ...
```
`AskService`'s worker-call client (`HttpLlmStreamClient`) should follow this identical shape but yield an `AsyncIterator[bytes]` from a `client.stream(...)` context manager instead of returning a parsed JSON body (see Pattern 5 / `stream_answer` sketch in RESEARCH.md lines 346-370 — already a concrete code example, reuse it directly).

**Result dataclass pattern** (lines 65-68):
```python
@dataclass(frozen=True, slots=True)
class RetrievalResult:
    evidence: list[EvidenceHit]
    meta: dict[str, Any]
```
Mirror this for any `AskService`-internal result shape (e.g., citation-resolution result), not a bare dict.

**Anchor issuance / citation resolution / metrics** — RESEARCH.md already has verbatim, ready-to-use code (do not re-derive):
- `build_issuance_map()` — RESEARCH.md lines 429-448
- `resolve_citations()` — RESEARCH.md lines 452-479
- `split_sentences()` — RESEARCH.md lines 484-500

**⚠️ Timeout anti-pattern to avoid** (`apps/api/src/api/main.py:33`, confirmed by RESEARCH.md's Anti-Patterns section): do not reuse `app.state.http_client`'s global 2.0s timeout for the worker LLM call — build a dedicated client or pass `timeout=httpx.Timeout(connect=5.0, read=timeout_seconds, write=5.0, pool=5.0)` per call, exactly like `HttpQueryEmbeddingClient.embed()` does with `timeout=self._timeout_seconds` (retrieval.py line 54).

---

### `apps/api/src/api/routers/ask.py` (controller, SSE)

**Analog:** `apps/api/src/api/routers/retrieval.py` (full file, 94 lines — read in full)

**Auth + settings wiring — copy verbatim structure** (lines 1-52):
```python
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

router = APIRouter(prefix="/workspaces", tags=["retrieval"])
_bearer = HTTPBearer()

class RetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str = Field(min_length=1)
    requested_k: int = Field(default=8, ge=1, le=8)

def _user_db(request: Request, credentials: HTTPAuthorizationCredentials) -> UserDb:
    settings = request.app.state.settings
    return UserDb(
        request.app.state.http_client,
        supabase_url=settings.SUPABASE_URL,
        publishable_key=settings.SUPABASE_PUBLISHABLE_KEY,
        access_token=credentials.credentials,
    )
```

**Route + service-lazy-init pattern** (lines 54-93):
```python
@router.post("/{workspace_id}/retrieval")
async def retrieve(
    workspace_id: UUID,
    body: RetrievalRequest,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> RetrievalResponse:
    settings = request.app.state.settings
    if len(body.query) > settings.RETRIEVAL_MAX_QUERY_CHARS:
        raise HTTPException(status_code=422, detail="invalid_query")
    service = getattr(request.app.state, "retrieval_service", None)
    if service is None:
        service = RetrievalService(HttpQueryEmbeddingClient(...))
    try:
        result = await service.retrieve(workspace_id, body.query, body.requested_k, _user_db(request, credentials))
    except ValueError:
        raise HTTPException(status_code=422, detail="invalid_query") from None
    return RetrievalResponse(...)
```
`ask.py`'s route differs only in: (1) it first calls `RetrievalService.retrieve()` exactly as above to get `evidence`, (2) branches on empty evidence for CITE-04's short-circuit (RESEARCH.md's `no_evidence_stream()` sketch, lines 503-512), (3) otherwise returns `StreamingResponse(AskService.stream_answer(...), media_type="text/event-stream")` instead of a Pydantic response model — SSE responses cannot use `response_model` validation the way `RetrievalResponse` does.

---

### `apps/api/src/api/routers/wiki.py` (QC-02 verification-transition endpoint)

**Analog:** `apps/api/src/api/routers/jobs.py`, `retry_job`/`cancel_job` shape (lines 133-146) + `UserDb.update_one()` (`apps/api/src/api/db/user.py` lines 115-129)

```python
@router.post("/{workspace_id}/jobs/{job_id}/retry")
async def retry_job(
    workspace_id: UUID, job_id: UUID, request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    db = _user_db(request, credentials)
    rows = await db.rpc("retry_dead_job", params={"p_job_id": str(job_id)})
    if not rows:
        raise JobNotRetryable
    row = rows[0]
    assert str(row["workspace_id"]) == str(workspace_id)  # noqa: S101
    return _job_response(row)
```
QC-02's `PATCH /{workspace_id}/wiki/{wiki_id}/verify` should instead call `UserDb.update_one()` directly (no RPC needed — `wiki_pages_update_editor` RLS policy already enforces editor+ role):
```python
async def update_one(self, table: str, *, match: Mapping[str, str], values: Mapping[str, Any]) -> dict[str, Any]:
    """정확히 한 행을 갱신하고 그 행을 돌려준다. 아니면 `WorkspaceForbidden`."""
    response = await self._client.patch(
        f"{self._base_url}/{table}",
        params=_require_filters(match),
        json=dict(values),
        headers={**self._headers, "Prefer": _REPRESENTATION},
    )
    return self._exactly_one(response, table=table)
```
Zero new authorization code needed — a viewer's UPDATE attempt returns 0 rows (RLS `USING` blocks it), `_exactly_one` raises `WorkspaceForbidden`, and the existing single exception handler in `api/errors.py` renders 403 automatically. Do not write a custom role-check in the router.

---

### `apps/api/src/api/routers/graph.py` (API-04 bounded graph read)

**Analog:** `apps/api/src/api/routers/retrieval.py`'s RPC-calling shape + `RetrievalService._graph()` (`apps/api/src/api/services/retrieval.py` lines 230-262)

```python
async def _graph(self, db: RpcUserDb, workspace_id: UUID, first_wave: list[EvidenceHit]):
    ...
    try:
        rows = await db.rpc(
            "expand_wiki_graph",
            params={
                "p_workspace_id": str(workspace_id),
                "p_seed_wiki_ids": seeds,
                "p_fanout": self._policy.graph_fanout,
                "p_total_limit": self._policy.graph_total_limit,
            },
        )
        if not isinstance(rows, list):
            raise ValueError("malformed")
        ...
    except asyncio.CancelledError:
        raise
    except Exception:
        return [], _failed_meta(...)
```
`GET /workspaces/{id}/graph` should call the new `wiki_graph_neighborhood` RPC (already sketched in full in RESEARCH.md's Pattern 4, lines 288-338) the same way `UserDb.rpc()` is called elsewhere — through the requester-JWT `UserDb`, never a `service_role` client, and the SQL function itself must be `security invoker` (not `definer`), matching `search_chunks`'s in-file warning against the reverse mistake.

---

### `packages/core/src/nexuswiki_core/citations.py` (utility, transform)

**Analog:** `apps/worker/src/worker/llm.py`'s `_PLACEHOLDER` regex + single-scan substitution style (lines 58-59, 109-135)

The two-regex design is already fully specified with rationale in RESEARCH.md's Architecture Patterns > Pattern 2 (lines 245-272) — copy directly:
```python
import re

BROAD_ANCHOR_PATTERN = re.compile(r"\[\[(?:wiki|src):[^\[\]]*\]\]")
ISSUED_ANCHOR_PATTERN = re.compile(r"\[\[(wiki:w\d+|src:s\d+)\]\]")

def strip_forged_anchors(text: str) -> str:
    return BROAD_ANCHOR_PATTERN.sub("", text)
```
Style precedent: `nexuswiki_core` modules are pure-function, stdlib-only, no classes for simple transforms — matches `tokenizer.py`'s `bigram()`/`normalize()` shape (referenced by `retrieval.py:16` but not re-read this pass since the pattern is already visible via its call sites in `retrieval.py`).

---

## Shared Patterns

### Bearer-token auth-before-work (worker-internal listeners)
**Source:** `apps/worker/src/worker/query_embedding.py:86-97`
**Apply to:** `llm_stream.py`'s `LlmStreamService.stream()` — authenticate the internal bearer token, THEN reserve rate-limiter capacity, THEN do provider work. Never reorder.

### Requester-JWT auth wiring (API routers)
**Source:** `apps/api/src/api/routers/retrieval.py:44-51` (`_user_db()` helper) — identical copy also exists in `jobs.py:46-54`.
**Apply to:** `ask.py`, `wiki.py`, `graph.py` — every new Phase 5 router needs its own `_user_db(request, credentials)` (small, intentionally duplicated per-router per existing convention, not extracted to a shared module).

### 0-rows-affected → 403, single exception-handler registration point
**Source:** `apps/api/src/api/errors.py` (full file, `register_error_handlers` at line 317) + `apps/api/src/api/db/user.py`'s `_exactly_one()` (lines 143-150)
**Apply to:** `wiki.py`'s verify endpoint (QC-02) — never add a new inline 403 in the router; raise `WorkspaceForbidden` (already thrown automatically by `UserDb.update_one()`) and let the existing single registration point in `errors.py` render it. Any new Phase 5 exception type (e.g., a citation-specific error for CITE-04) must be added to `errors.py`'s `__all__` and registered in `register_error_handlers()`, not handled inline in a router.

### service_client / ServiceDb for worker-side DB writes needing service_role
**Source:** `apps/worker/src/worker/__main__.py:155-156` (`async with service_client(settings) as client: db = ServiceDb(client)`)
**Apply to:** `LlmStreamService`'s post-stream `insert_usage_event()` write (Pattern 3 in RESEARCH.md) — this is the deliberate exception to the query-embedding listener's "no DB client" invariant; only `usage_events` INSERT (service_role-only) justifies it.

### Settings field pairs for internal boundaries
**Source:** existing `QUERY_EMBEDDING_INTERNAL_URL` / `QUERY_EMBEDDING_INTERNAL_TOKEN` / `QUERY_EMBEDDING_TIMEOUT_SECONDS` fields in `ApiSettings`/`WorkerSettings` (not re-read this pass — confirmed present via `retrieval.py`'s and `query_embedding.py`'s consuming code)
**Apply to:** new `LLM_STREAM_INTERNAL_URL` / `LLM_STREAM_INTERNAL_TOKEN` / `LLM_STREAM_TIMEOUT_SECONDS` — distinct token value from the query-embedding one per D-01, but identical settings-field shape and identical "fails fast at boot if missing" contract per CLAUDE.md's Error Handling section.

### Korean comments / English identifiers, ⚠️-prefixed footguns
**Source:** every file read this session (`llm.py`, `errors.py`, `query_embedding.py`, `user.py`, `jobs.py`)
**Apply to:** all Phase 5 new files — match this house style exactly, including the `⚠️` marker convention for footguns that silently corrupt security/correctness if ignored.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `packages/core/src/nexuswiki_core/sentences.py` | utility | transform | No existing sentence-splitting code anywhere in the codebase — this is a genuinely new capability. RESEARCH.md's Code Examples section (lines 484-500) already provides a complete, ready-to-use hand-rolled implementation with rationale for not adding `kss`; use that directly rather than searching further for a non-existent analog. |
| `supabase/migrations/0012_ask_citation_and_graph.sql` (the prompt-template `UPDATE` half specifically, D-10) | migration | batch (data UPDATE) | No prior migration in this project does a plain `UPDATE` on seed data (all prior migrations are DDL + `INSERT`, e.g. `0006_seed_prompts.sql`). The DDL half (new RPC) has a strong analog (`0011_retrieval.sql`); the `UPDATE ... SET system_prompt = ...` half does not — write it as a plain, idempotent `UPDATE ... WHERE target_type = 'ask'` following `0006`'s existing row-shape/column names, no special pattern needed beyond that. |

## Metadata

**Analog search scope:** `apps/worker/src/worker/` (query_embedding.py, __main__.py, llm.py, handlers/parse.py), `apps/api/src/api/` (services/retrieval.py, routers/retrieval.py, routers/jobs.py, errors.py, db/user.py), `packages/core/src/nexuswiki_core/` (rrf.py referenced, tokenizer.py referenced via call sites), `supabase/migrations/` (0011_retrieval.sql referenced via RESEARCH.md's already-read excerpt)
**Files read directly this pass:** `apps/worker/src/worker/query_embedding.py` (full, 129 lines), `apps/worker/src/worker/__main__.py` (full, 184 lines), `apps/worker/src/worker/llm.py` (full, 362 lines), `apps/api/src/api/services/retrieval.py` (full, 396 lines), `apps/api/src/api/routers/retrieval.py` (full, 94 lines), `apps/api/src/api/errors.py` (full, 339 lines), `apps/api/src/api/routers/jobs.py` (full, 200 lines), `apps/api/src/api/db/user.py` (full, 184 lines), `apps/worker/src/worker/handlers/parse.py` (lines 130-169, insertion point verified)
**Pattern extraction date:** 2026-08-11
