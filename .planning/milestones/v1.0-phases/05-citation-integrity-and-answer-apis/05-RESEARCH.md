# Phase 5: Citation Integrity and Answer APIs - Research

**Researched:** 2026-08-11
**Domain:** Streaming LLM answer generation, server-issued citation anchors, worker-owned provider boundary, bounded graph SQL, verification-transition APIs
**Confidence:** MEDIUM-HIGH (architecture grounded in read source; SSE/OpenRouter mechanics cross-checked via web search; sentence-splitting and conflict-detection algorithm choices are LOW-confidence design recommendations flagged as assumptions)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 (LLM call transport boundary):** The Ask endpoint's LLM call follows the exact boundary Phase 4 established for query embedding (`docs/architecture/query-embedding-boundary.md`): `apps/worker` is the only process holding `OPENROUTER_API_KEY`; it exposes a second private-network-only HTTP listener (alongside the existing query-embedding listener) that streams chat completions. `apps/api` calls that listener with a dedicated internal URL + token pair (distinct from `QUERY_EMBEDDING_INTERNAL_*`) and re-streams the SSE bytes to the browser. Reversibility: costly.
  - Discretion left to researcher: whether this reuses `QueryEmbeddingService`'s FastAPI app instance (same process, second route) or is a sibling app/port.
- **D-02 (Citation anchor format and issuance):** Anchors are short, server-issued, per-request-scoped aliases — `[[wiki:w1]]`, `[[wiki:w2]]`, `[[src:s1]]`, `[[src:s2]]`, ... — assigned by enumerating `RetrievalService.retrieve()`'s `evidence` list in return order. The server holds an in-memory `{alias: (kind, real_id)}` map for the lifetime of the request/stream only; never persisted. Reversibility: reversible.
- **D-03 (`double_citation` computation timing):** Per API-01's mandated event order (`meta` → `delta*` → `citations` → `done`), the model's full answer text must be accumulated before the `citations` event can be computed. The server buffers deltas server-side (streaming them to the client unbuffered as they arrive), and only after the provider stream ends does it regex-parse the accumulated text for `[[wiki:*]]`/`[[src:*]]` tokens, intersect them against the issuance map from D-02 (CITE-02: parsed ∩ issued, not parsed ∩ search-results), and emit `citations` then `done`.
  - Fabricated anchors (CITE-03): any parsed token not present in the issuance map is stripped from the rendered answer text sent as the final `citations`/answer payload and counted in `fabricated_anchor_count` — never resolved, never rendered as a working link.
  - No evidence (CITE-04): if the issuance map is empty (Phase 4 returned zero evidence), skip the LLM call entirely and return the explicit "근거를 찾지 못했습니다" response — do not spend a provider call on a request that cannot be grounded.
- **D-04 (Source-forged-anchor stripping point):** CITE-06 is implemented at **parse time**, in `apps/worker/src/worker/handlers/parse.py`, before chunking — not per-chunk. A forged `[[wiki:...]]`/`[[src:...]]` token could straddle a chunk boundary and evade a naive per-chunk regex; stripping the raw extracted text once, before `chunk_text()` runs, closes that gap structurally. Reversibility: reversible.
- **D-05 (Conflict detection trigger and method — flagged for researcher):** QC-01 runs as a step appended to `link_sync` or a new job type chained after `compile` (write-time, not part of the Ask request path). Candidate approach to validate: use `wiki_embeddings` for semantic-similarity candidate pairs above a threshold, then an LLM classification call (structured output, reusing `worker.llm.complete_structured`) to decide contradiction vs. legitimate variation. Detection *trigger point* is decided; detection *algorithm* is not — left to this research.
- **D-06 (Verification-transition authorization):** QC-02's verification-transition API requires `editor` role or above (matches `workspace_role()` grading owner(3) > editor(2) > viewer(1)). Mirrors SEC-04's 0-rows-affected → 403 pattern.
- **D-07 (Read APIs scope):** API-04 excludes anything RSC-direct-readable. Phase 5 builds only: (1) bounded graph read (depth ≤ 2, fan-out cap, cycle guard — RTV-07's bounds), (2) job status — audit existing `apps/api/src/api/routers/jobs.py` against API-04 before adding endpoints, (3) wiki/source detail reads — verify per-endpoint whether RSC+RLS suffices vs. needing computed fields.
- **D-08 (Prompt template selection and language matching):** API-02/API-03 consume the already-seeded `prompt_templates` table (`target_type='ask'`, 4 global defaults). The Ask request accepts an optional `template_id` (defaulting to `is_default=true` for `target_type='ask'`); language-following is a system-prompt instruction, not a separate translation pass — reuse `render_template()`, never `str.format`.

### Claude's Discretion

- Exact SSE event payload field names/shapes beyond the mandated `meta`/`delta`/`citations`/`done` event *names* and their *order* — should carry what CITE-05's four metrics (`dual_citation_rate`, `unsourced_sentence_ratio`, `fabricated_anchor_count`, `cited_anchor_count`) need.
- `unsourced_sentence_ratio` measurement method (sentence-splitting approach for Korean/English/mixed corpus) — no established pattern in this codebase yet.
- Internal LLM-listener route path and whether it lives in the same worker FastAPI app as query-embedding or a separate one.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope (auto-run discussion, no scope-creep suggestions).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CITE-01 | 인용 앵커가 서버 발급 짧은 별칭으로 프롬프트에 주입되고 서버가 실제 id로 해소한다 | D-02 issuance map design + `EvidenceHit` enumeration source (`packages/core/src/nexuswiki_core/rrf.py`) confirmed; "Anchor Grammar" pattern below; **prompt-template mismatch pitfall** documented (seed system_prompts currently instruct `[[wiki:slug]]`/`[[src:청크id]]`, not the alias form) |
| CITE-02 | `double_citation`이 파싱된 앵커 ∩ 검색 결과로 구성된다 | D-03 buffer-then-parse design confirmed sound; intersection logic against issuance map (not raw search results) documented in Code Examples |
| CITE-03 | 발급되지 않은 앵커는 조작으로 간주해 제거하고 카운트한다 | Two-regex design (broad strip vs. narrow issued-alias parse) documented under Architecture Patterns |
| CITE-04 | 앵커가 하나도 없으면 "근거를 찾지 못했습니다"를 명시적으로 반환한다 | Empty-evidence short-circuit before LLM call; `api.errors` single-registration-point pattern reused |
| CITE-05 | `dual_citation_rate`·`unsourced_sentence_ratio`·`fabricated_anchor_count`·`cited_anchor_count`가 측정된다 | Sentence-splitting research (hand-rolled regex recommended over `kss`); metric computation documented in Code Examples |
| CITE-06 | 수집된 소스가 위조한 `[[...]]` 앵커가 수집 시점에 제거된다 | Exact insertion point in `worker/handlers/parse.py` verified (before `chunk_text(content)` at line 151, covers all 3 source types) |
| API-01 | Ask 엔드포인트가 SSE로 스트리밍한다 (POST+fetch+ReadableStream, `meta`→`delta*`→`citations`→`done`) | FastAPI `StreamingResponse` + httpx `client.stream()` relay pattern researched and documented; EventSource-incompatibility confirmed via web search |
| API-02 | 상황별 `ask` 프롬프트 템플릿을 선택해 질문할 수 있다 | `prompt_templates` schema read in full (0001, 0006); 4 seeded templates confirmed with exact placeholder contract |
| API-03 | 답변 언어가 질문 언어를 따른다 | System-prompt instruction approach confirmed consistent with `render_template()`'s single-scan substitution (no separate translation call) |
| API-04 | 위키·소스·그래프·잡 상태 조회 API가 제공된다 (RSC 대체 가능한 것 제외) | `jobs.py` router audited (already covers list/retry/cancel/budget); graph-read RPC design recommended as a **new** function distinct from retrieval's `expand_wiki_graph` |
| QC-01 | 지식 충돌이 감지되어 `disputed`로 표시된다 | Cosine-threshold + LLM-judge two-stage design researched; `wiki_pages.disputed`/`verification_status` CHECK values read verbatim from 0001 |
| QC-02 | 검증 상태 전이 API가 누가·언제·언제까지를 기록한다 | `wiki_pages_update_editor` RLS policy read verbatim from 0004 — already enforces editor+ role; `UserDb.update_one` is sufficient, no new authorization code needed |
</phase_requirements>

## Summary

Phase 5 adds one new runtime component (a worker-owned streaming LLM listener), one new regex-based token grammar shared between two enforcement points, one small metrics module, and three-to-four new API endpoints. Every one of these has a directly analogous, already-implemented precedent in this codebase from Phases 2-4: the query-embedding boundary (`apps/worker/src/worker/query_embedding.py`) is the template for D-01's LLM listener; the compile handler's `complete_structured()` + `insert_usage_event()` pairing is the template for cost accounting on the new streaming call; `expand_wiki_graph`'s recursive-CTE shape is the template for the D-07.1 graph-read RPC; `wiki_pages_update_editor`'s RLS policy already enforces QC-02's editor-role requirement with zero new authorization code. The work in Phase 5 is almost entirely **composition of existing patterns into new call sites**, not new architecture.

Two non-obvious risks surfaced during research that are not visible from the requirements text alone. First, the four seeded `ask` prompt templates (`0006_seed_prompts.sql`) instruct the model to cite using `[[wiki:slug]]` and `[[src:청크id]]` (the real slug / full chunk UUID) — this is the **pre-D-02 anchor format**. D-02's short-alias scheme (`[[wiki:w1]]`) requires either a new migration updating the seeded instruction text, or empirical validation that showing `[[wiki:w1]]`-prefixed context blocks is enough to override the instruction text's literal wording. Second, `enqueue_source_job` — the only budget-cap enforcement point in the codebase (OPS-01) — fires only for queued compile-pipeline jobs; the Ask endpoint's LLM call never goes through it, and `usage_events` INSERT is `service_role`-only, so the API process cannot write cost records itself. The natural, and recommended, place to close both the cost-observability gap and a soft budget check is inside the new worker-side LLM listener itself, which already needs a service-role DB client for a different reason (see Architecture Patterns).

**Primary recommendation:** Add a second route (not a second FastAPI app / second port) to the worker's existing internal-listener process for the LLM streaming call, backed by a new `LlmStreamService` mirroring `QueryEmbeddingService`'s token-bucket-before-provider-work shape; give the API a request-scoped anchor-issuance map and a two-regex citation grammar (broad strip-time pattern in `packages/core`, narrow issued-alias pattern also in `packages/core`); update the seeded `ask` prompt templates' citation instruction text in a new migration (`0012`) to match the alias scheme; and reuse `expand_wiki_graph`'s exact recursive-CTE shape (not the function itself) for a new, independently-versioned graph-read RPC.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| OpenRouter streaming chat call | Worker (private listener) | — | Only process holding `OPENROUTER_API_KEY` (`02-CONTEXT.md > D-06`); mirrors query-embedding boundary |
| SSE byte relay to browser | API (backend) | — | API terminates the browser's authenticated HTTPS connection; worker has no public route (`railway.json`) |
| Citation anchor issuance (alias map) | API (backend) | — | Request-scoped, never persisted (D-02); lives exactly as long as the HTTP request |
| Citation anchor parsing/intersection | API (backend) | Shared grammar in `packages/core` | Parsing happens once, after the full answer is buffered (D-03); the *pattern* is shared with worker-side stripping so both recognize the identical token shape |
| Forged-anchor stripping in ingested text | Worker (parse handler) | Shared grammar in `packages/core` | D-04: happens at parse time, before chunking, in the same process that already owns text extraction |
| Citation metrics (CITE-05) computation | API (backend) | — | Computed once per response after buffering, attached to `citations`/`done` event; no persistence required this phase |
| Conflict detection (QC-01) | Worker (chained job) | Database (pgvector cosine query) | Write-time concern (D-05); reuses `wiki_embeddings` already computed by Phase 4, and `worker.llm.complete_structured` for the LLM-judge step |
| Verification-transition write (QC-02) | Database (RLS) | API (backend, thin) | `wiki_pages_update_editor` RLS policy already enforces the authorization; API is a thin `UserDb.update_one` wrapper, no new authz logic |
| Bounded graph read (D-07.1) | Database (SECURITY INVOKER RPC) | API (backend, thin) | Same reasoning as `search_chunks`/`expand_wiki_graph`: RLS-enforcing SQL owns the bound enforcement, not application code |
| LLM cost accounting for Ask | Worker (LLM listener) | Database (`usage_events`) | Only `service_role` can INSERT into `usage_events` (0009 §8 ACL); API/`authenticated` has SELECT only |
| Prompt template selection/rendering | API (backend) | Database (`prompt_templates` read) | Existing `render_template()` reused verbatim; no new templating engine |

## Standard Stack

### Core

No new external packages are required for this phase. Every capability composes existing project dependencies:

| Library | Version | Purpose | Why Standard (already in this project) |
|---------|---------|---------|--------------|
| `httpx` | 0.28.1 (pinned, both `apps/api` and `apps/worker`) [VERIFIED: apps/api/pyproject.toml:9-14, apps/worker/pyproject.toml:8-11] | `AsyncClient.stream()` for the SSE relay (API→worker) and OpenRouter call (worker→provider) | Already the sole HTTP client library project-wide; `client.stream()` is the documented httpx pattern for proxying SSE without full buffering [CITED: web search, cross-checked against httpx GitHub discussions] |
| `fastapi` | 0.141.1 [VERIFIED: apps/api/pyproject.toml:9] | `StreamingResponse` for both the worker-internal listener's chat route and the API's public Ask route | Already the API framework; `StreamingResponse` accepts any async generator [CITED: web search] |
| `re` (stdlib) | — | Anchor-grammar regex, sentence-boundary regex | Existing convention: `worker/llm.py`'s `_PLACEHOLDER` regex is the established house style for this kind of single-scan token matching |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| None recommended | — | — | Sentence splitting (CITE-05) and streaming (API-01) are both achievable with stdlib + existing deps; adding a package increases the dependency surface for marginal gain (see Alternatives below) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled regex sentence splitter | `kss` (Korean Sentence Splitter, PyPI) [ASSUMED — package name from web search, not verified via `npm view`-equivalent this session] | `kss`'s lightest pure-Python backend still bundles a morpheme analyzer (Pynori) [CITED: web search, pypi.org/project/kss]. This project has an explicit, repeated precedent of rejecting Korean morphological analyzers for a much higher-stakes use case (lexical search tokenization — `CLAUDE.md`: "Postgres에 한국어 형태소 분석기 없음"). Pulling one in for a best-effort *quality metric* (not a correctness-critical path) is inconsistent with that precedent and adds a second Python-ecosystem NLP dependency chain with its own security-audit surface. **Recommendation: do not add.** |
| Hand-rolled SSE relay | `sse-starlette` (EventSourceResponse) [ASSUMED — not verified] | Provides named-event SSE framing helpers, but API-01's exact 4-event order (`meta`→`delta*`→`citations`→`done`) is simple enough to hand-write with `StreamingResponse` + a generator, matching the project's consistent "hand-roll small, well-understood primitives, avoid a new abstraction layer" pattern (`chunk_text`, `normalize`/`bigram`, `render_template` are all hand-rolled for the same reason). **Recommendation: do not add**, but note as a legitimate lower-effort alternative if the planner wants named SSE event types instead of manually formatting `event: ...\ndata: ...\n\n` frames. |
| LLM-judge conflict classification via `complete_structured` | A dedicated similarity/NLI model (e.g., cross-encoder) | Would require a new model dependency and a new provider call shape (not chat-completion-based); OpenRouter routing plus the existing Pydantic-validated structured-output backstop is already proven in `worker/llm.py` and keeps this on the same cost/observability rails as compile. **Recommendation: reuse `complete_structured`.** |

**Installation:** No `pyproject.toml` changes required in any workspace member for this phase, assuming the recommendations above are followed.

**Version verification:** N/A — no new packages recommended. If the planner chooses to add `kss` or `sse-starlette` despite the above, run `pip index versions kss` / `pip index versions sse-starlette` and complete a Package Legitimacy Audit before locking the plan.

## Package Legitimacy Audit

No new external packages are required or recommended for this phase (see Standard Stack above — every capability is implemented with `httpx`, `fastapi`, and the Python standard library, all already present in the workspace). No packages were installed or verified against the registry this session because none are recommended.

**Packages removed due to [SLOP] verdict:** none (none proposed)
**Packages flagged as suspicious [SUS]:** none (none proposed)

If the planner decides to add `kss` (Korean sentence splitter) despite the recommendation against it, run `gsd_run query package-legitimacy check --ecosystem pypi kss` and gate the install behind a `checkpoint:human-verify` task before locking the plan — its name was discovered via WebSearch, not an authoritative source, and is therefore `[ASSUMED]` regardless of PyPI registry presence.

## Architecture Patterns

### System Architecture Diagram

```text
Browser (fetch POST, Authorization: Bearer <user JWT>)
   │
   ▼
apps/api  POST /workspaces/{id}/ask  (StreamingResponse, text/event-stream)
   │
   ├─ 1. UserDb(JWT) → RetrievalService.retrieve() [Phase 4, unchanged]
   │        └─ evidence: list[EvidenceHit]  (wiki + source hits, RRF-fused)
   │
   ├─ 2. if evidence is empty → CITE-04 short-circuit
   │        emit meta{no_evidence:true} → citations{} → done   (no LLM call spent)
   │
   ├─ 3. else: build alias issuance map (D-02)
   │        {w1: (wiki, real_wiki_id), s1: (source, real_chunk_id), ...}
   │        assemble {{wiki_context}} / {{source_context}} with "[[wiki:w1]] ..." headers
   │        select prompt_templates row (API-02: template_id or is_default)
   │
   ├─ 4. emit `meta` event (template used, evidence counts, policy_version)
   │
   ├─ 5. open httpx.AsyncClient().stream("POST", LLM_INTERNAL_URL, ...)
   │        │  Authorization: Bearer <LLM_STREAM_INTERNAL_TOKEN>  (distinct from QUERY_EMBEDDING_INTERNAL_TOKEN)
   │        ▼
   │     apps/worker  POST /internal/llm-chat   (second route, same listener process as query-embedding)
   │        │
   │        ├─ authenticate internal bearer token BEFORE quota/provider work
   │        ├─ reserve token-bucket slot (mirrors QueryEmbeddingService._reserve_token, NOT a lifetime counter)
   │        ├─ open OpenRouter stream: POST /chat/completions {stream:true, usage:{include:true}}
   │        ├─ relay each SSE "delta.content" chunk upstream immediately (no buffering here)
   │        └─ on stream end: insert_usage_event(workspace_id, kind=llm, cost_micros, ...) via service_client
   │              (job_id = null — Ask is not a queued job)
   │
   ├─ 6. API relays each delta chunk to the browser AS `delta` events (unbuffered client-to-client hop)
   │        while ALSO appending to a server-side accumulator string (buffer-then-parse, D-03)
   │
   ├─ 7. on worker stream end: regex-parse accumulated text for [[wiki:w\d+]] / [[src:s\d+]]
   │        intersect parsed ∩ issuance-map (CITE-02) → resolved citations
   │        parsed − issuance-map → fabricated_anchor_count (CITE-03), stripped from rendered text
   │        compute dual_citation_rate / unsourced_sentence_ratio / cited_anchor_count (CITE-05)
   │
   └─ 8. emit `citations` event (resolved anchors + metrics) → emit `done` event → close stream

Separately, write-time (not in the Ask request path):
apps/worker  compile → link_sync → [new] conflict_check  (D-05, chained job)
   │  wiki_embeddings cosine-similarity candidate pairs (pgvector, threshold ~0.85-0.92)
   │  → complete_structured() LLM-judge classification (contradiction vs. legitimate variation)
   └─ UPDATE wiki_pages SET disputed = true, verification_status = 'disputed' WHERE ...

Dashboard-facing read APIs (no LLM involved):
apps/api  PATCH /workspaces/{id}/wiki/{wiki_id}/verify   → UserDb.update_one("wiki_pages", ...)
                                                              (wiki_pages_update_editor RLS enforces editor+)
apps/api  GET   /workspaces/{id}/graph                   → UserDb.rpc("wiki_graph_neighborhood", ...)
                                                              (new SQL fn, same bounds as expand_wiki_graph)
```

### Recommended Project Structure

```
apps/worker/src/worker/
├── query_embedding.py       # existing — QueryEmbeddingService, create_query_embedding_app
├── llm_stream.py            # NEW — LlmStreamService, add_llm_stream_route(app, service)
├── llm.py                   # existing — complete_structured() unchanged; add stream_chat() sibling function
└── __main__.py              # extend _serve_query_embeddings → wire second route on same app/port

apps/api/src/api/
├── services/
│   ├── retrieval.py         # existing, unchanged
│   └── ask.py                # NEW — AskService: issuance map, SSE assembly, citation resolution, metrics
├── routers/
│   ├── retrieval.py         # existing, unchanged
│   ├── ask.py                # NEW — POST /workspaces/{id}/ask (StreamingResponse)
│   ├── wiki.py                # NEW — PATCH .../wiki/{wiki_id}/verify ; GET .../wiki/{slug} (if RSC insufficient)
│   └── graph.py                # NEW — GET /workspaces/{id}/graph
└── settings.py                # extend ApiSettings: LLM_STREAM_INTERNAL_URL/_TOKEN/_TIMEOUT_SECONDS

packages/core/src/nexuswiki_core/
├── citations.py              # NEW — BROAD_ANCHOR_PATTERN, ISSUED_ANCHOR_PATTERN, strip_forged_anchors()
└── sentences.py               # NEW — split_sentences() heuristic (Korean/English/mixed)

supabase/migrations/
└── 0012_ask_citation_and_graph.sql   # NEW — ask-template instruction text update (see Pitfall below),
                                        #       wiki_graph_neighborhood() RPC, its ACL grants
```

### Pattern 1: Worker-owned streaming provider listener (second route, same process)

**What:** Add `/internal/llm-chat` as a second FastAPI route in the same small ASGI app / same `uvicorn.Server` instance that already serves `/internal/query-embedding`, rather than a second app on a second port.

**When to use:** Any time a second worker-owned, provider-secret-backed capability needs to be exposed to the API process privately.

**Why (grounded in read code, not assumed):**
- `railway.json`'s `privateNetworking`/`publicNetworking` toggle [VERIFIED: railway.json:7-10] applies at the **service** level, not per-port — a second port buys no additional isolation.
- `apps/worker/src/worker/__main__.py`'s `_serve_query_embeddings` [VERIFIED: apps/worker/src/worker/__main__.py:37-59] already wires exactly one `uvicorn.Server` task into the `asyncio.TaskGroup` alongside the queue loop; adding a second `uvicorn.Server` doubles the SIGTERM-shutdown surface (`server.should_exit = True; await server_task`, once per server) for no isolation benefit.
- Each route still independently authenticates its own bearer token before doing any quota/provider work — `QueryEmbeddingService.embed()`'s ordering (`apps/worker/src/worker/query_embedding.py:86-97`, "인증이 quota/provider 작업보다 먼저") is the contract to replicate per-route, not per-app. D-01 already requires the new token be *distinct* from `QUERY_EMBEDDING_INTERNAL_TOKEN`; that distinctness is a settings/token-value concern, not an app-topology concern.
- The two capabilities have very different traffic shapes (5s/4-concurrent embedding calls vs. 120s/few-concurrent streaming LLM calls per `LLM_REQUEST_TIMEOUT_SECONDS` [VERIFIED: apps/worker/src/worker/llm.py:52]) — this is handled by giving `LlmStreamService` its **own** `asyncio.Semaphore` and its **own** token bucket, not by process/port separation.

**Example (skeleton, mirrors `query_embedding.py`'s exact shape):**
```python
# apps/worker/src/worker/llm_stream.py
class LlmStreamService:
    def __init__(self, chat_stream: ChatStreamFunction, *, internal_token: str,
                 max_concurrency: int = 2, rate_capacity: int = 20,
                 refill_tokens_per_second: float = 0.5, monotonic=time.monotonic) -> None:
        ...  # identical _reserve_token() token-bucket shape as QueryEmbeddingService — NOT a
             # lifetime counter (docs/architecture/query-embedding-boundary.md's explicit warning,
             # commit 6a14144 fixed exactly this bug in the embedding listener once already)

    async def stream(self, request: LlmChatRequest, authorization: str | None
                      ) -> AsyncIterator[bytes]:
        if authorization != f"Bearer {self._internal_token}":
            raise HTTPException(status_code=401, detail="internal_unauthorized")
        await self._reserve_token()
        async with self._semaphore:
            async for chunk in self._chat_stream(request):
                yield chunk
        # usage accounting happens after the generator is fully drained by the caller —
        # see Pattern 3 below for why this listener (unlike query-embedding) legitimately
        # needs a service-role DB client.

def add_llm_stream_route(app: FastAPI, service: LlmStreamService) -> None:
    @app.post("/internal/llm-chat")
    async def llm_chat(request: LlmChatRequest, authorization: Annotated[str | None, Header()] = None):
        return StreamingResponse(service.stream(request, authorization), media_type="text/event-stream")
```

### Pattern 2: Two-regex citation anchor grammar (shared, not duplicated)

**What:** Define **two** distinct regexes in `packages/core`, not one:
1. `BROAD_ANCHOR_PATTERN` — matches *any* `[[wiki:...]]` / `[[src:...]]`-shaped substring regardless of content, used **only** at parse-time (D-04, CITE-06) to strip forged anchors from freshly-extracted source text.
2. `ISSUED_ANCHOR_PATTERN` — matches **only** the exact alias grammar the server ever issues (`[[wiki:w\d+]]` / `[[src:s\d+]]`), used **only** at Ask-time (D-02/D-03) to parse the model's answer and intersect against the per-request issuance map.

**Why these must be different patterns, not one reused pattern:** A malicious source cannot predict a future request's exact alias numbers, but it *can* embed literal text shaped like `[[wiki:w1]]` — which, if a future Ask request's evidence enumeration happens to assign alias `w1` to some real wiki page (a common low-numbered alias), would make the forged token collide with a real entry in that request's issuance map and pass D-03's `parsed ∩ issued` intersection check as if the model had genuinely cited it. Stripping must therefore be **broader** than what the narrow parser recognizes as valid, so nothing that *could* later fool the narrow parser survives ingestion. Using the narrow `w\d+`/`s\d+` pattern at strip-time would under-strip (e.g. `[[wiki:homepage]]` or `[[src:not-a-real-id]]` would sail through into `source_chunks.content` and later into an Ask context block, unstripped, still capable of being echoed as literal-looking bracket text even if it never resolves).

**Example:**
```python
# packages/core/src/nexuswiki_core/citations.py
import re

# D-04 / CITE-06: strip-time — deliberately permissive, matches any bracket-anchor shape.
BROAD_ANCHOR_PATTERN = re.compile(r"\[\[(?:wiki|src):[^\[\]]*\]\]")

# D-02 / D-03 / CITE-01~03: parse-time — deliberately narrow, matches only what the
# server itself ever issues this request.
ISSUED_ANCHOR_PATTERN = re.compile(r"\[\[(wiki:w\d+|src:s\d+)\]\]")

def strip_forged_anchors(text: str) -> str:
    """CITE-06: remove every bracket-anchor-shaped token from freshly ingested text.

    ⚠️ Must run once on the full extracted text, before chunk_text() — a forged anchor
    can straddle a chunk boundary and evade a naive per-chunk regex (D-04).
    """
    return BROAD_ANCHOR_PATTERN.sub("", text)
```

### Pattern 3: LLM listener owns its own usage-event write (deliberate asymmetry from query-embedding)

**What:** Unlike `QueryEmbeddingService` — whose documented invariant is "The worker boundary has no database client" [VERIFIED: docs/architecture/query-embedding-boundary.md:29-30, quoted verbatim] — the new `LlmStreamService` **should** open a `service_client(settings)` / `ServiceDb` after each completed stream to call `insert_usage_event(workspace_id=..., row={"job_id": None, "kind": UsageKind.LLM.value, ...})`, mirroring exactly what `worker/handlers/compile.py` already does after `complete_structured()` [VERIFIED: apps/worker/src/worker/handlers/compile.py:146-171, exact call shape quoted in Code Examples below].

**Why this is not a violation of the embedding-boundary precedent:** That invariant was scoped to the *query-embedding* listener specifically, because query embedding is a pure compute operation with no cost/accounting need of its own (embedding cost is already captured elsewhere in the compile/embed job chain). The LLM listener is categorically different: OpenRouter streaming responses carry per-call `usage` data (prompt/completion/total tokens, cost) exactly like `complete_structured()`'s non-streaming responses do, and `usage_events` INSERT is `service_role`-only [VERIFIED: supabase/migrations/0009_pipeline_ops.sql:531-534, quoted: `grant select, insert on table public.usage_events to service_role;` vs. `grant select on table public.usage_events to authenticated;`] — the API process (requester-JWT, `authenticated` role) **cannot** write this row itself even if it wanted to. The worker-side listener is the only place in the architecture with both the token-usage data and the DB privilege to record it.

**Open gap this also closes (see Common Pitfalls):** because the listener already needs a `service_client` for this write, it can also cheaply read `workspaces.monthly_budget_micros` and sum this month's `usage_events` before opening the OpenRouter stream, closing the otherwise-unenforced Ask budget gap described below.

### Pattern 4: Bounded graph-read RPC — new function, not reuse of `expand_wiki_graph`

**What:** `expand_wiki_graph(p_workspace_id, p_seed_wiki_ids, p_fanout, p_total_limit)` [VERIFIED: supabase/migrations/0011_retrieval.sql:163-215, full body read] already implements exactly the bounds D-07.1 asks for — depth fixed at 2 hops (`walk.depth < 2`), fan-out cap via `limit p_fanout` inside a `cross join lateral`, cycle guard via `not edge.to_wiki_id = any(walk.path)` — but it returns only `(wiki_id, depth)` node pairs, no edges, and it is explicitly owned by Phase 4's retrieval-fusion policy (its seeds come only from already-fused first-wave evidence; `04-CONTEXT.md > D-05~D-08` locks that policy layer and Phase 5's CONTEXT.md explicitly says "Phase 5 must not reach into or duplicate that policy").

**Recommendation:** write a **new** function (e.g. `public.wiki_graph_neighborhood`) for API-04's graph-read endpoint, copying `expand_wiki_graph`'s exact recursive-CTE shape (same `security invoker`, `stable`, `set search_path = public`, same depth/fanout/cycle-guard mechanics) but (a) selecting `(from_wiki_id, to_wiki_id, depth)` edge triples instead of node-only rows, so a future graph UI (Phase 6, UI-06) has edges to draw, and (b) versioning it independently of `POLICY_VERSION`/`hybrid-rrf-v1` since its caller (a dashboard "browse the graph" feature) has nothing to do with retrieval fusion. This keeps the two SQL contracts free to evolve independently, consistent with why Phase 4 didn't build the other 4 search-channel functions until their own weights were fixed.

```sql
-- supabase/migrations/0012_..._graph.sql (sketch — verify exact bound values against
-- product requirements before locking; mirrored from 0011_retrieval.sql:163-215)
create or replace function public.wiki_graph_neighborhood(
  p_workspace_id uuid,
  p_seed_wiki_id uuid,
  p_fanout       int default 10,
  p_total_limit  int default 100
)
returns table (from_wiki_id uuid, to_wiki_id uuid, depth int)
language plpgsql
security invoker
stable
set search_path = public
as $$
begin
  if p_fanout < 1 or p_fanout > 20 then
    raise exception 'wiki_graph_neighborhood fan-out must be 1..20' using errcode = '22023';
  end if;
  if p_total_limit < 1 or p_total_limit > 200 then
    raise exception 'wiki_graph_neighborhood total limit must be 1..200' using errcode = '22023';
  end if;
  return query
  with recursive walk as (
    select p_seed_wiki_id as from_wiki_id, l.to_wiki_id, 1 as depth,
           array[p_seed_wiki_id, l.to_wiki_id]::uuid[] as path
      from public.wiki_links l
     where l.workspace_id = p_workspace_id
       and l.from_wiki_id = p_seed_wiki_id
       and l.resolved
     order by l.to_wiki_id
     limit p_fanout
    union all
    select walk.to_wiki_id, edge.to_wiki_id, walk.depth + 1, walk.path || edge.to_wiki_id
      from walk
      cross join lateral (
        select l.to_wiki_id from public.wiki_links l
         where l.workspace_id = p_workspace_id
           and l.from_wiki_id = walk.to_wiki_id
           and l.resolved and l.to_wiki_id is not null
         order by l.to_wiki_id limit p_fanout
      ) edge
     where walk.depth < 2 and not edge.to_wiki_id = any(walk.path)
  )
  select from_wiki_id, to_wiki_id, depth from walk limit p_total_limit;
end;
$$;

revoke all on function public.wiki_graph_neighborhood(uuid, uuid, int, int) from public, anon, service_role;
grant execute on function public.wiki_graph_neighborhood(uuid, uuid, int, int) to authenticated;
```

### Pattern 5: SSE relay without full buffering (API ↔ worker), buffer-then-parse (API accumulator, separate concern)

**What:** Two different "buffering" concepts must not be conflated:
1. **Byte relay (unbuffered):** API → browser and worker → API both relay each chunk immediately as it arrives — this is what makes the UI feel like streaming.
2. **Text accumulation (buffered, server-side only):** the API *also* appends every delta chunk's text to an in-memory string accumulator, purely to run the citation regex against the complete answer once the stream ends (D-03). This accumulator is never sent to the browser as a single blob — the browser only ever sees the same unbuffered `delta` events as (1).

**Example (httpx relay, cross-checked against httpx streaming discussions):**
```python
# apps/api/src/api/services/ask.py (sketch)
async def stream_answer(worker_client: httpx.AsyncClient, *, url: str, token: str,
                         body: dict, timeout_seconds: float) -> AsyncIterator[str]:
    accumulated: list[str] = []
    async with worker_client.stream(
        "POST", url, json=body,
        headers={"Authorization": f"Bearer {token}"},
        # ⚠️ do NOT reuse app.state.http_client's global 2.0s timeout
        # (apps/api/src/api/main.py:33 — that timeout is calibrated for PostgREST
        # round-trips, not 120s LLM completions). Mirror HttpQueryEmbeddingClient's
        # per-call timeout override instead.
        timeout=httpx.Timeout(connect=5.0, read=timeout_seconds, write=5.0, pool=5.0),
    ) as upstream:
        async for line in upstream.aiter_lines():
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            delta = json.loads(line[len("data: "):])["choices"][0]["delta"].get("content", "")
            if delta:
                accumulated.append(delta)
                yield f"event: delta\ndata: {json.dumps({'text': delta})}\n\n"
    full_text = "".join(accumulated)
    # ... regex-parse full_text here (D-03), then yield citations/done events
```

### Anti-Patterns to Avoid

- **Reusing `app.state.http_client` for the LLM listener call:** its global 2.0s timeout [VERIFIED: apps/api/src/api/main.py:33, quoted: `app.state.http_client = httpx.AsyncClient(timeout=httpx.Timeout(2.0))`] is explicitly calibrated for PostgREST round-trips and documented as intentionally tight ("LLM 호출은 워커의 일이다" — LLM calls are the worker's job [VERIFIED: apps/api/src/api/main.py:53-59, comment quoted]). A streaming Ask call through that client would abort after 2 seconds. Use a dedicated client or a per-call timeout override, exactly like `HttpQueryEmbeddingClient.embed()` already does (`apps/api/src/api/services/retrieval.py:47-62`, passes `timeout=self._timeout_seconds` per request).
- **Using the narrow `ISSUED_ANCHOR_PATTERN` for CITE-06 stripping:** under-strips forged anchors that don't happen to match the current alias grammar (see Pattern 2).
- **Treating a token-bucket capacity/refill pair as a lifetime request counter:** `docs/architecture/query-embedding-boundary.md` explicitly documents that a prior worker listener had this exact bug, fixed in commit `6a14144` — the fix pattern (`_reserve_token()`'s monotonic-clock-based refill, protected by an `asyncio.Lock`) must be replicated for the new listener's rate limiter, not reinvented.
- **Testing the new SSE listener route with `httpx.ASGITransport` + `client.stream()` without a bound:** at least one documented GitHub discussion reports `AsyncClient.stream()` against an SSE endpoint hanging indefinitely under `ASGITransport` in test environments [CITED: web search, encode/httpx#1787] — wrap streaming test assertions in `asyncio.wait_for(..., timeout=...)` rather than a bare `async for`.
- **Logging the new internal token settings field by attribute name:** `nexuswiki_core.logging.REDACTED_KEYS` is an **exact-match** set on casefolded log keys [VERIFIED: packages/core/src/nexuswiki_core/logging.py:16-33, full set quoted: `password, authorization, token, api_key, apikey, secret, email, access_token, refresh_token, content, supabase_secret_key, openrouter_api_key, openai_api_key, database_url`], not a substring match. A field like `LLM_STREAM_INTERNAL_TOKEN` logged under that literal key would **not** be redacted (only a bare key named exactly `token` is). Keep the new token exclusively inside `Authorization` header dicts (which already redacts, since `authorization` is in the set) and never log the settings attribute directly, matching how `QUERY_EMBEDDING_INTERNAL_TOKEN` is handled today.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenRouter streaming protocol parsing | A custom SSE/chunk parser from scratch | `httpx.AsyncClient.stream()` + `aiter_lines()`, splitting on the standard `data: ` prefix and `[DONE]` sentinel | This is the documented OpenAI-compatible SSE shape [CITED: web search, openrouter.ai/docs]; no library needed but the parsing logic (strip `data: `, handle `[DONE]`, ignore SSE comment lines) should be one small function, not duplicated at every call site |
| Cost/token accounting for the new call | A new usage-tracking table or field | `usage_events` + `insert_usage_event()` (already exists, already has `kind='llm'`, already has the `job_id` nullable FK) | The schema already supports job-less usage rows; a parallel table would fragment OPS-06's cost observability |
| Bounded recursive graph traversal | Fetching all `wiki_links` rows and walking them in Python | A SQL recursive CTE inside a `SECURITY INVOKER stable` function (Pattern 4) | RLS + bound enforcement belong in SQL per this project's established contract (`search_chunks`, `expand_wiki_graph`); doing it in Python means either bypassing RLS (service-role) or making N+1 RLS-scoped round trips |
| Editor-role authorization for verification transitions | A new role-check decorator/middleware in the API | The existing `wiki_pages_update_editor` RLS policy [VERIFIED: supabase/migrations/0004_rls_policies.sql:240-245, quoted: `create policy wiki_pages_update_editor on public.wiki_pages for update to authenticated using (public.has_workspace_role(workspace_id, 'editor')) with check (public.has_workspace_role(workspace_id, 'editor'));`] | Already enforces exactly D-06's requirement; a plain `UserDb.update_one("wiki_pages", match={"id": ..., "workspace_id": ...}, values={...})` call gets 403 for free on any non-editor attempt |

**Key insight:** every "Don't Hand-Roll" item in this phase already has a hand-rolled, tested, in-repo primitive from Phases 1-4 that solves the identical shape of problem. The risk in Phase 5 is not missing a library — it's *not noticing* the existing precedent and reinventing it slightly differently (e.g., a second rate-limiter implementation that reintroduces the lifetime-counter bug, or a second citation-anchor regex that doesn't match the strip-time one).

## Common Pitfalls

### Pitfall 1: Seeded `ask` prompt templates instruct the pre-alias citation format

**What goes wrong:** All four seeded `target_type='ask'` prompt templates' `system_prompt` text says, verbatim, "위키 근거는 `[[wiki:slug]]`, 원문 근거는 `[[src:청크id]]` 형식 그대로 쓰세요" [VERIFIED: supabase/migrations/0006_seed_prompts.sql, quoted from the "기술 심층 분석" template body read in full this session] — i.e., cite using the real slug and the real chunk UUID. D-02 changed the anchor scheme to short per-request aliases (`w1`, `s1`). If the assembled `{{wiki_context}}`/`{{source_context}}` blocks correctly show `[[wiki:w1]]`-style headers per chunk (per D-02/D-08) but the instructional prose still says "슬러그"/"청크id" literally, the model receives two conflicting signals about what to copy.
**Why it happens:** The seed data (0006) predates D-02's decision by construction — CITE-01's short-alias requirement ("36자 UUID를 모델이 정확히 복사하도록 요구하지 않음") is exactly what motivated D-02, but the seed migration was written before this phase existed.
**How to avoid:** Add a migration (`0012` or next available number) that `UPDATE`s the four `target_type='ask'` rows' `system_prompt` text, replacing the literal `[[wiki:slug]]`/`[[src:청크id]]` phrasing with instruction to copy the exact anchor shown at the head of each context block (e.g., "각 컨텍스트 항목 머리에 표시된 `[[wiki:wN]]`/`[[src:sN]]` 앵커를 그대로 복사해 인용하세요, 슬러그나 원본 id를 직접 쓰지 마세요"). Also update the `0006` header-comment's documentation of the `{{wiki_context}}`/`{{source_context}}` placeholder contract if it's kept as living documentation.
**Warning signs:** `fabricated_anchor_count` is unexpectedly high in early testing, or the model emits real slugs/UUIDs instead of `w1`/`s1` tokens.

### Pitfall 2: Ask's LLM spend has no budget-cap enforcement path

**What goes wrong:** `enqueue_source_job` is the *only* function in the schema that compares `usage_events` spend against `workspaces.monthly_budget_micros` [VERIFIED: supabase/migrations/0010_budget_error_sqlstate.sql:14-88, comment quoted: "이번 달 usage_events 합이 workspaces.monthly_budget_micros 이상이면 NW402으로 거부한다"], and it only gates enqueuing a `parse` job. The Ask endpoint's LLM call never calls `enqueue_source_job` — it goes straight to the new internal listener. A workspace that has already exceeded its monthly budget via ingestion can still make unlimited-cost Ask calls.
**Why it happens:** OPS-01 was scoped ("인큐 시점 워크스페이스별 비용 상한") to the job-queue path that existed at the time it was implemented (Phase 3); Ask is a new, synchronous, non-queued LLM call path that didn't exist yet.
**How to avoid:** Since `LlmStreamService` already needs a `service_client` for `insert_usage_event` (Pattern 3), have it also `SELECT workspaces.monthly_budget_micros` and sum this month's `usage_events` **before** opening the OpenRouter stream, rejecting with a 402-equivalent response if already at/over cap — same computation `enqueue_source_job` does, just read-only and inside the listener instead of a `SECURITY DEFINER` SQL function. This is not explicitly required by CITE/API/QC IDs but is a direct consequence of D-01's architecture; flag it to the user/planner as a scope decision if out-of-budget Ask behavior needs to be explicitly locked.
**Warning signs:** A workspace shows `budget_exceeded` on new ingestion but Ask still responds normally.

### Pitfall 3: `wiki_links` FK column names (`from_wiki_id`/`to_wiki_id`) are already fixed — a new graph function must match them exactly

**What goes wrong:** Writing the new graph-read RPC (Pattern 4) with different column names than `wiki_links`' actual schema.
**Why it happens:** Easy to copy-paste from a conceptual sketch instead of the real schema.
**How to avoid:** `wiki_links` columns are `from_wiki_id`, `target_slug`, `to_wiki_id`, `resolved` (generated) [VERIFIED: supabase/migrations/0002_search_schema.sql:163-195, full CREATE TABLE read]. `resolved` is a generated column (`to_wiki_id is not null`) — filter on `l.resolved` (not `l.to_wiki_id is not null` redundantly, though both work) to match `expand_wiki_graph`'s existing style exactly.
**Warning signs:** `42703` (undefined column) at migration apply time — caught immediately, low severity, but avoidable.

### Pitfall 4: `hnsw.iterative_scan = strict_order` is a per-function `SET`, not a session default — conflict detection's cosine query needs it too if it queries `wiki_embeddings` via HNSW

**What goes wrong:** QC-01's candidate-pair query against `wiki_embeddings` returns fewer/different rows than expected if run without the same `set hnsw.*` GUCs as `search_wiki_embeddings`.
**Why it happens:** `strict_order` is set inside each individual `SECURITY INVOKER` function definition (`create function ... set hnsw.iterative_scan = 'strict_order'`), not globally — a new ad hoc query (even one written directly by the worker, since QC-01 runs `service_role`-side and could theoretically skip RLS/RPC entirely) would silently fall back to Postgres/pgvector defaults, which this project's own benchmarking found materially worse (RTV-03/RTV-04 precedent: `strict_order` was deliberately chosen over the default).
**How to avoid:** If the conflict-detection candidate-pair query is implemented as a new `SECURITY INVOKER`/`security definer` SQL function (recommended, consistent with "search queries are owned by migrations" per `checklists.json > decisions.db_transport`), copy the exact `set hnsw.iterative_scan = 'strict_order' / set hnsw.ef_search = '200' / set hnsw.max_scan_tuples = '40000'` triad from `search_wiki_embeddings`/`search_chunks`.
**Warning signs:** Conflict-detection candidate pairs vary run-to-run for the same corpus, or `EXPLAIN` shows a sequential scan instead of the HNSW index (RTV-08's regression-test pattern is directly reusable here).

### Pitfall 5: Testing an SSE endpoint through `ASGITransport` can hang

See Anti-Patterns above (Pattern 5 section) — `AsyncClient.stream()` against an in-process ASGI SSE endpoint has a documented hang risk under certain httpx/anyio versions [CITED: web search, encode/httpx#1787]. Bound all such test assertions with `asyncio.wait_for`.

## Code Examples

### Anchor issuance map construction (D-02)

```python
# apps/api/src/api/services/ask.py (sketch)
def build_issuance_map(evidence: list[EvidenceHit]) -> dict[str, tuple[str, str]]:
    """Enumerate RetrievalService.retrieve()'s evidence in return order (D-02).

    Real ids are never exposed to the model — only the alias. `kind` distinguishes
    wiki (document_id) from source (evidence_id, i.e. chunk id) per rrf.py's
    EvidenceHit shape (packages/core/src/nexuswiki_core/rrf.py:14-68).
    """
    wiki_n = source_n = 0
    issuance: dict[str, tuple[str, str]] = {}
    for hit in evidence:
        if hit.kind == "wiki":
            wiki_n += 1
            issuance[f"w{wiki_n}"] = ("wiki", hit.document_id)
        else:
            source_n += 1
            issuance[f"s{source_n}"] = ("source", hit.evidence_id)
    return issuance
```

### Citation intersection and metrics (CITE-02, CITE-03, CITE-05)

```python
# apps/api/src/api/services/ask.py (sketch)
from nexuswiki_core.citations import ISSUED_ANCHOR_PATTERN
from nexuswiki_core.sentences import split_sentences

def resolve_citations(full_text: str, issuance: dict[str, tuple[str, str]]) -> dict:
    parsed = {m.group(1) for m in ISSUED_ANCHOR_PATTERN.finditer(full_text)}
    # normalize "wiki:w1" -> "w1" / "src:s1" -> "s1" to match issuance keys
    parsed_aliases = {token.split(":", 1)[1] for token in parsed}
    resolved = parsed_aliases & issuance.keys()          # CITE-02: parsed ∩ issued
    fabricated = parsed_aliases - issuance.keys()          # CITE-03

    sentences = split_sentences(full_text)
    cited_sentences = sum(1 for s in sentences if ISSUED_ANCHOR_PATTERN.search(s))
    dual_cited_sentences = sum(
        1 for s in sentences
        if any(a.startswith("wiki:") for a in ISSUED_ANCHOR_PATTERN.findall(s))
        and any(a.startswith("src:") for a in ISSUED_ANCHOR_PATTERN.findall(s))
    )
    return {
        "cited_anchor_count": len(resolved),
        "fabricated_anchor_count": len(fabricated),
        "dual_citation_rate": dual_cited_sentences / len(sentences) if sentences else 0.0,
        "unsourced_sentence_ratio": (
            (len(sentences) - cited_sentences) / len(sentences) if sentences else 0.0
        ),
    }
```

### Hand-rolled sentence splitter (CITE-05, Korean/English/mixed)

```python
# packages/core/src/nexuswiki_core/sentences.py
import re

# Sentence-final punctuation: ASCII .!? plus full-width Korean/CJK 。！？, followed
# by optional closing quote/bracket, followed by whitespace or end of string.
# A negative lookbehind for a preceding digit avoids splitting "3.14" or "1."-style
# list markers; this is a bounded heuristic (CITE-05 is a quality metric, not a
# correctness-critical parse), not a linguistically complete sentence tokenizer.
_SENTENCE_BOUNDARY = re.compile(r"(?<![0-9])[.!?。！？]+[\"'\)\]]*(?:\s+|$)")

def split_sentences(text: str) -> list[str]:
    """Best-effort Korean/English/mixed sentence split. See CITE-05 rationale in
    05-RESEARCH.md Standard Stack > Alternatives Considered for why this is
    hand-rolled instead of pulling in `kss` (Korean morphological analyzer)."""
    pieces = _SENTENCE_BOUNDARY.split(text)
    return [p.strip() for p in pieces if p.strip()]
```

### Empty-evidence short circuit (CITE-04)

```python
# apps/api/src/api/routers/ask.py (sketch)
if not evidence:
    async def no_evidence_stream() -> AsyncIterator[str]:
        yield f"event: meta\ndata: {json.dumps({'no_evidence': True})}\n\n"
        yield f"event: citations\ndata: {json.dumps({'text': NO_EVIDENCE_MESSAGE, 'cited_anchor_count': 0})}\n\n"
        yield "event: done\ndata: {}\n\n"
    return StreamingResponse(no_evidence_stream(), media_type="text/event-stream")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `EventSource` for all SSE consumption | `fetch()` + `ReadableStream` for any SSE endpoint needing POST or custom headers | N/A — always been true, not a recent change; `EventSource` has never supported POST/custom headers | Confirmed by API-01's own requirement text; not a new finding but worth confirming was not stale training-data assumption [CITED: web search, MDN-adjacent sources] |
| Non-streaming `complete_structured()` for all LLM calls | Streaming call for Ask, structured-JSON-retry call unchanged for compile/conflict-classification | This phase | Two call shapes now coexist in `worker/llm.py`; keep them as sibling functions, not a unified abstraction, since their retry/validation semantics are fundamentally different (a partial stream cannot be "retried" the way a malformed JSON response can) |

**Deprecated/outdated:** None identified — this phase adds new capability rather than replacing an existing approach.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `kss` PyPI package name and its Pynori dependency chain | Standard Stack > Alternatives Considered | Low — this claim only supports a "do not add" recommendation; even if package details are slightly stale, the underlying argument (avoid a second NLP dependency for a quality metric) still holds independent of the exact package name |
| A2 | `sse-starlette` as a named-event SSE helper library exists and would be a viable alternative | Standard Stack > Alternatives Considered | Low — mentioned only as a rejected alternative, not a recommendation; not load-bearing for the plan |
| A3 | Cosine-similarity threshold range (0.85-0.92) for near-duplicate/contradiction candidate surfacing | Architecture Patterns > Pattern 4 context (QC-01), Pitfall 4 | Medium — if the actual optimal threshold for this corpus differs substantially, QC-01's candidate-pair query will over- or under-surface pairs for the LLM judge, affecting cost (too many candidates → more `complete_structured` calls) or recall (too few → missed conflicts). Recommend validating empirically against the RTV-06 golden query set's corpus before locking a constant, same discipline as RTV-04's benchmark-before-lock precedent. |
| A4 | OpenRouter's stream error-mid-flight behavior (SSE data payload carrying an error object, since HTTP status is already 200) | Architecture Patterns > System Diagram, Anti-Patterns | Medium — if the actual error shape differs from what was found via web search, the API's error-handling branch for a mid-stream provider failure may not correctly detect it and could silently truncate the answer instead of surfacing an error to the client. Recommend a manual smoke test against a deliberately-failing request (e.g., invalid model slug) before locking the error-handling code path. |
| A5 | `sse-starlette`/`kss` not verified via `pip index versions` this session (no packages recommended, so the Package Legitimacy Gate protocol's registry-verification step was not exercised) | Package Legitimacy Audit | Low — moot unless the planner overrides the "do not add" recommendation |

**If this table is empty:** N/A — see entries above. All *architectural* claims (D-01 through D-08's implementation mechanics, existing schema, existing code shapes) are `[VERIFIED]` against files read this session; only the *external-library* and *numeric-threshold* recommendations carry residual uncertainty.

## Open Questions (RESOLVED)

1. **Should Ask's LLM spend be gated by the monthly budget cap in this phase, or explicitly deferred?**
   - RESOLVED: see 05-CONTEXT.md > D-09 — in scope, not deferred. `LlmStreamService` gates on the budget cap before opening the OpenRouter stream (05-04-PLAN.md).
   - What we know: no code path currently enforces it (Pitfall 2); the natural fix point (inside `LlmStreamService`) is cheap given the listener already needs a service-role DB client for usage-event writes.
   - What's unclear: whether this is in-scope for Phase 5's 12 requirement IDs (none of CITE/API/QC explicitly mention budget) or should be explicitly deferred to a later OPS phase with an interim soft warning instead of a hard block.
   - Recommendation: raise this explicitly during planning/discuss rather than silently deciding either way — it's a real architectural gap discovered mid-research, not a requirement ambiguity.

2. **Does the seeded `ask` prompt template instruction text get updated in Phase 5, or does context-block anchor-header alone suffice?**
   - RESOLVED: see 05-CONTEXT.md > D-10 — update unconditionally. `0012_ask_citation_and_graph.sql` (05-02-PLAN.md) rewrites the 4 seeded `target_type='ask'` templates' citation instruction text to match D-02's short-alias scheme.
   - What we know: the literal instruction text says `[[wiki:slug]]`/`[[src:청크id]]` (Pitfall 1); LLMs often follow a shown few-shot pattern (the `[[wiki:w1]]` header actually present in context) over conflicting prose instructions, but this is a "usually" not a "always."
   - What's unclear: whether this needs empirical validation (a smoke test with the current unmodified seed data) before deciding whether the migration is strictly necessary, or whether it should be done unconditionally as the more robust choice.
   - Recommendation: update the seed text unconditionally (cheap, one migration, removes an entire class of ambiguity) rather than relying on the model correctly resolving the conflict.

3. **Exact numeric bounds for the new `wiki_graph_neighborhood` RPC (fanout/total_limit defaults).**
   - RESOLVED: see 05-CONTEXT.md > D-11 — planner's discretion, anchored to existing bounds; conservative defaults are set directly in `0012_ask_citation_and_graph.sql` (05-02-PLAN.md).
   - What we know: `expand_wiki_graph`'s bounds (fanout ≤5, total_limit ≤50, seeds ≤10) were tuned for the *retrieval* use case (bounded re-fusion cost). A dashboard "browse the graph" feature (this phase's read API, consumed by Phase 6's UI) may reasonably want a larger neighborhood (e.g., fanout ≤20, total_limit ≤200 as sketched above) since it's a single explicit user action, not a per-request retrieval cost multiplier.
   - What's unclear: the actual UX target (how large a graph view Phase 6 wants to render) — not decided anywhere in read materials.
   - Recommendation: planner should pick conservative defaults now (this phase has no UI consumer yet) and note in the migration comment that Phase 6 may request a bump, mirroring how `0007`'s comment on `search_chunks` explicitly deferred the other 4 channels to Phase 4.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker Desktop | Local Supabase stack | ✓ | 24.0.6 (client) [VERIFIED: `docker info` this session] | — |
| Supabase CLI | Local migrations, `db reset` | ✓ | 2.111.0 [VERIFIED: `supabase --version` this session] | — |
| Supabase local stack | RLS/RPC testing | ✓ running | DB 54422, API 54421, Studio 54423 [VERIFIED: `supabase status` this session] | — |
| Python | worker/api runtime | ✓ | 3.12.3 [VERIFIED: `python3 --version`] | — |
| uv | Python workspace management | ✓ | 0.11.32 [VERIFIED: `uv --version`] | — |
| pytest | Test execution | ✓ | 9.1.1 [VERIFIED: `uv run pytest --version`] | — |
| Node.js | tooling (not app runtime) | ✓ | v25.9.0 [VERIFIED: `node --version`] | — |
| OpenRouter API reachability | LLM streaming calls | ✓ (HTTP 200 from `/api/v1/models`) [VERIFIED: `curl` this session, network reachability only — not an auth/quota check] | — | — |
| `OPENROUTER_API_KEY` local value | Actual streaming calls in local dev | Not checked this session (would require reading `.env`/`.env.local`, out of scope for a read-only research pass — no `.env.example` exists on disk per CLAUDE.md) | — | Worker fails fast at boot without it (`WorkerSettings` required field) |

**Missing dependencies with no fallback:** none identified.
**Missing dependencies with fallback:** none identified — all required tooling is present and working locally.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-asyncio 1.4.0 [VERIFIED: pyproject.toml:14-17, `uv run pytest --version`] |
| Config file | root `pyproject.toml` (`[tool.pytest.ini_options]`, `--import-mode=importlib`, `testpaths` covers all 3 workspace members) |
| Quick run command | `uv run pytest apps/worker/tests/test_llm_stream.py apps/api/tests/test_ask_router.py -x` (new test files, planner names them) |
| Full suite command | `uv run pytest` (from repo root; runs `packages/core/tests`, `apps/api/tests`, `apps/worker/tests`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|--------------|
| CITE-01/02/03 | Anchor issuance, intersection, fabrication stripping | unit | `pytest apps/api/tests/test_ask_citations.py -x` | ❌ Wave 0 |
| CITE-04 | Empty-evidence short circuit skips LLM call | unit | `pytest apps/api/tests/test_ask_router.py::test_no_evidence_skips_llm -x` | ❌ Wave 0 |
| CITE-05 | Metrics computation (dual/unsourced/fabricated/cited) | unit | `pytest packages/core/tests/test_sentences.py packages/core/tests/test_citations.py -x` | ❌ Wave 0 |
| CITE-06 | Forged-anchor stripping at parse time | unit | `pytest apps/worker/tests/test_handlers.py::test_parse_strips_forged_anchors -x` (extend existing file) | ✅ (extend `apps/worker/tests/test_handlers.py`) |
| API-01 | SSE event order, ASGITransport streaming | integration | `pytest apps/worker/tests/test_llm_stream.py -x` (mirrors `test_query_embedding.py` shape) | ❌ Wave 0 (new), pattern exists |
| API-02/API-03 | Template selection, language matching | unit | `pytest apps/api/tests/test_ask_router.py -k template_or_language -x` | ❌ Wave 0 |
| API-04 | Graph read RPC bounds, job-status audit | integration (RLS, real DB) | `pytest apps/api/tests/test_graph_router.py -x` (mirrors `test_hybrid_search_integration.py`'s real-DB pattern) | ❌ Wave 0, pattern exists |
| QC-01 | Conflict detection candidate pairs + LLM judge | unit + integration | `pytest apps/worker/tests/test_handlers.py -k conflict -x` | ❌ Wave 0 |
| QC-02 | Verification-transition editor-role enforcement | integration (RLS, real DB) | `pytest apps/api/tests/test_workspaces_isolation.py -k verify -x` (extend existing isolation-test file — mirrors that file's real-RLS pattern) | ✅ (extend) |

### Sampling Rate

- **Per task commit:** targeted file (`pytest <changed test file> -x`)
- **Per wave merge:** `uv run pytest` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `apps/worker/tests/test_llm_stream.py` — covers API-01 (mirrors `apps/worker/tests/test_query_embedding.py`'s ASGITransport pattern; must bound stream-consumption assertions with `asyncio.wait_for` per Pitfall 5)
- [ ] `apps/api/tests/test_ask_router.py` — covers CITE-04, API-02, API-03
- [ ] `apps/api/tests/test_ask_citations.py` — covers CITE-01, CITE-02, CITE-03
- [ ] `packages/core/tests/test_citations.py` — covers the two-regex grammar (Pattern 2) in isolation
- [ ] `packages/core/tests/test_sentences.py` — covers `split_sentences()` against Korean/English/mixed fixtures
- [ ] `apps/api/tests/test_graph_router.py` — covers API-04's graph read, mirrors `test_hybrid_search_integration.py`'s real-DB RLS pattern

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | yes | Existing `HTTPBearer` + requester-JWT pattern (`UserDb`), unchanged this phase; new internal listener uses bearer-token-before-work pattern (`QueryEmbeddingService` precedent) |
| V3 Session Management | no | No new session state introduced (anchor issuance map is request-scoped, never persisted — D-02) |
| V4 Access Control | yes | `wiki_pages_update_editor` RLS policy (QC-02); new `wiki_graph_neighborhood` RPC must be `security invoker` (RLS-enforced), never `security definer`, mirroring `search_chunks`'s explicit warning against the reverse mistake |
| V5 Input Validation | yes | Pydantic request models for the new Ask/verify/graph endpoints (existing project convention, `model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)` per `RetrievalRequest`) |
| V6 Cryptography | no | No new cryptographic primitives; internal bearer tokens are opaque shared secrets, same class as `QUERY_EMBEDDING_INTERNAL_TOKEN` |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Prompt injection via forged citation anchors embedded in ingested sources | Tampering / Spoofing | D-04's parse-time broad-pattern stripping (Pattern 2) — closes the injection vector structurally rather than relying on the model to ignore malicious instructions |
| Anchor-alias collision (forged low-numbered alias matching a future request's real issuance) | Spoofing | The broad strip-time pattern (not the narrow issued-alias pattern) at ingestion time, per Pattern 2's explicit rationale |
| Cross-tenant graph traversal via an unbounded or `security definer` graph RPC | Elevation of Privilege | `security invoker` (not `definer`) on `wiki_graph_neighborhood`, exactly matching `search_chunks`'s explicit in-file warning ("definer로 바꾸면 RLS가 우회되어 교차 테넌트 검색이 열립니다") |
| Cost-exhaustion via unlimited Ask calls (no budget gate, no per-listener quota beyond token bucket) | Denial of Service | Pitfall 2's recommended budget check inside `LlmStreamService`, plus the token-bucket rate limiter (mirrors `QueryEmbeddingService`) |
| Internal listener token leakage via structured logs | Information Disclosure | Anti-Patterns' logging pitfall — keep the new token exclusively inside `Authorization` header dicts, never log the settings attribute by name |
| Enumeration attack via verification-transition endpoint's error responses | Information Disclosure | Reuse `api.errors`' existing "0 rows affected → 403, no 404" single-registration-point convention (D-06, SEC-04 precedent) — do not add a new error path that distinguishes "wiki not found" from "not authorized" |

## Sources

### Primary (HIGH confidence — read directly this session)
- `apps/worker/src/worker/query_embedding.py` — full file read; template for D-01's LLM listener
- `apps/worker/src/worker/__main__.py` — full file read; worker process wiring
- `docs/architecture/query-embedding-boundary.md` — full file read; D-01's exact precedent
- `apps/worker/src/worker/llm.py` — full file read; `complete_structured()`, `render_template()`, cost accounting
- `apps/api/src/api/services/retrieval.py`, `apps/api/src/api/routers/retrieval.py` — full files read; `RetrievalService`/`RetrievalResult`, `HttpQueryEmbeddingClient`'s per-call timeout override pattern
- `apps/api/src/api/errors.py`, `apps/api/src/api/db/user.py` — full files read; single-registration-point error pattern, `UserDb` write methods
- `apps/api/src/api/routers/jobs.py`, `apps/api/src/api/main.py` — full files read; existing job-status audit target, `app.state.http_client` timeout
- `apps/api/src/api/settings.py`, `apps/worker/src/worker/settings.py` — full files read; secret-boundary invariants
- `railway.json`, `scripts/ci_check_query_embedding_boundary.sh` — full files read; private-networking CI guard pattern
- `supabase/migrations/0001_core_schema.sql`, `0002_search_schema.sql` (wiki_links section), `0004_rls_policies.sql` (full file), `0006_seed_prompts.sql` (full ask-template text), `0007_search_and_queue_extensions.sql` (search_chunks, verified_by/at/expires_at, ACL matrix), `0009_pipeline_ops.sql` (usage_events, enqueue_source_job budget check), `0010_budget_error_sqlstate.sql`, `0011_retrieval.sql` (expand_wiki_graph full body) — all read directly this session
- `packages/core/src/nexuswiki_core/rrf.py`, `retrieval_policy.py`, `logging.py` — full files read
- `apps/worker/src/worker/handlers/parse.py`, `handlers/compile.py` (partial, usage-event section) — read directly this session
- `apps/worker/tests/test_query_embedding.py` — read directly this session; test pattern precedent
- `.planning/phases/05-citation-integrity-and-answer-apis/05-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md` — read directly this session

### Secondary (MEDIUM confidence — WebSearch, cross-checked against multiple results)
- OpenRouter streaming SSE chunk format, `[DONE]` sentinel, mid-stream error handling — [OpenRouter API Streaming docs](https://openrouter.ai/docs/api/reference/streaming)
- FastAPI `StreamingResponse` + fetch/ReadableStream vs. `EventSource` POST/auth-header limitation — [FastAPI Streaming Responses (DeepWiki)](https://deepwiki.com/fastapi/fastapi/3.7-streaming-responses), [Server-Sent Events with Python FastAPI (Medium)](https://medium.com/@nandagopal05/server-sent-events-with-python-fastapi-f1960e0c8e4b)
- httpx `AsyncClient.stream()` proxy/relay pattern, ASGITransport streaming test hang risk — [httpx StreamingResponse discussion #6173](https://github.com/fastapi/fastapi/discussions/6173), [httpx.AsyncClient.stream() SSE test hang #1787](https://github.com/encode/httpx/discussions/1787)
- `kss` Korean sentence splitter package and its Pynori dependency — [kss on PyPI](https://pypi.org/project/kss/3.7.0/), [hyunwoongko/kss GitHub](https://github.com/hyunwoongko/kss)
- Cosine similarity thresholds for near-duplicate/contradiction detection and LLM-as-judge mitigation — general web search synthesis, no single authoritative source; treated as directional guidance only (see Assumption A3)

### Tertiary (LOW confidence — flagged for validation)
- Exact numeric cosine threshold (0.85 vs 0.92) — genuinely varies by embedding model and corpus; must be validated against this project's own `wiki_embeddings` (bge-m3-family, per `03-CONTEXT.md > D-04/D-05`) before locking, not taken as a universal constant

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages recommended; every capability maps to code read directly this session
- Architecture: HIGH — every pattern (listener topology, anchor grammar, graph RPC, usage-event write) is grounded in a specific file+line read this session, not inferred
- Pitfalls: HIGH for the schema/code-level pitfalls (1, 2, 3, 4 — all backed by direct reads); MEDIUM for pitfall 5 (SSE testing hang — single web-search source, not verified against this project's actual httpx/pytest-asyncio version combination)

**Research date:** 2026-08-11
**Valid until:** 2026-09-10 (30 days — this is a stable-stack phase with no fast-moving external dependencies; the only external-API surface, OpenRouter's streaming format, is OpenAI-compatible and has been stable for a long period)
