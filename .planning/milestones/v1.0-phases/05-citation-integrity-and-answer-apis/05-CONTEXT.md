# Phase 5: Citation Integrity and Answer APIs - Context

**Gathered:** 2026-08-11 (--auto mode — Claude selected all gray areas and recommended options; no interactive questions asked, per user's explicit request to continue the GSD process automatically through this transition)
**Status:** Ready for planning

<domain>
## Phase Boundary

Turn Phase 4's evidence-only retrieval into answers the user can trust: inject server-issued short citation anchors into the LLM prompt, resolve only the anchors the model actually cited against the anchors actually issued, stream the answer over SSE in a fixed event order, and expose the read/verification APIs the dashboard needs. This phase does not build the dashboard UI (Phase 6), does not add a graph database (rejected project-wide), and does not change Phase 4's retrieval/fusion policy — it consumes `RetrievalService.retrieve()` output as-is.

12 requirements: CITE-01~06 (anchor issuance/resolution, double-citation intersection, fabrication stripping at three points, citation metrics, no-evidence explicit response), API-01~04 (SSE ask endpoint, prompt-template selection, answer-language matching, read APIs), QC-01~02 (conflict detection → `disputed`, verification-transition audit trail).

</domain>

<decisions>
## Implementation Decisions

### LLM call transport boundary (auto-selected — mirrors Phase 4 precedent)

- **D-01:** The Ask endpoint's LLM call follows the exact boundary Phase 4 established for query embedding (`docs/architecture/query-embedding-boundary.md`): `apps/worker` is the only process holding `OPENROUTER_API_KEY`; it exposes a second private-network-only HTTP listener (alongside the existing query-embedding listener) that streams chat completions. `apps/api` calls that listener with a dedicated internal URL + token pair (distinct from `QUERY_EMBEDDING_INTERNAL_*`) and re-streams the SSE bytes to the browser. — **Reversibility:** costly — reversing this moves a live secret boundary and requires coordinated worker+API+Railway redeploy, same class as the embedding boundary's own rollback note.
  - **Rationale (why this is the recommended default, not a coin flip):** `02-CONTEXT.md > D-06` locked "capability absence, not import blocking" as this project's entire security model for `OPENROUTER_API_KEY` — it is deliberately absent from `ApiSettings`. Giving `apps/api` its own OpenRouter key for Ask would directly violate that locked decision. Phase 4 already solved the identical problem (a secret-only-in-worker capability that the API-facing request path needs) with a private internal listener + bounded token; Ask has the same shape (auth → bounded request → provider call → stream back), so re-deriving a different architecture would be inconsistent with zero benefit.
  - **Discretion for planner/researcher:** whether this reuses `QueryEmbeddingService`'s FastAPI app instance (same process, second route) or is a sibling app/port is left open — research the existing `apps/worker/src/worker/query_embedding.py` + its `__main__.py` wiring before deciding, and document the choice with a rationale.

### Citation anchor format and issuance (auto-selected)

- **D-02:** Anchors are short, server-issued, per-request-scoped aliases — `[[wiki:w1]]`, `[[wiki:w2]]`, `[[src:s1]]`, `[[src:s2]]`, ... — assigned by enumerating `RetrievalService.retrieve()`'s `evidence` list in return order (not by hashing or truncating the real UUID). The server holds an in-memory `{alias: (kind, real_id)}` map for the lifetime of the request/stream only; it is never persisted. This satisfies CITE-01's explicit reason ("36자 UUID를 모델이 정확히 복사하도록 요구하지 않음").
  - **Reversibility:** reversible — alias scheme is request-local and has no stored/migrated state.

### `double_citation` computation timing (auto-selected)

- **D-03:** Per API-01's mandated event order (`meta` → `delta*` → `citations` → `done`), the model's full answer text must be accumulated before the `citations` event can be computed — citations cannot be validated incrementally mid-stream because a `[[...]]` token can be split across delta chunks. The server buffers deltas server-side (streaming them to the client unbuffered as they arrive), and only after the provider stream ends does it regex-parse the accumulated text for `[[wiki:*]]`/`[[src:*]]` tokens, intersect them against the issuance map from D-02 (CITE-02: parsed ∩ issued, not parsed ∩ search-results), and emit `citations` then `done`.
  - **Fabricated anchors (CITE-03):** any parsed token not present in the issuance map is stripped from the rendered answer text sent as the final `citations`/answer payload and counted in `fabricated_anchor_count` — never resolved, never rendered as a working link.
  - **No evidence (CITE-04):** if the issuance map is empty (Phase 4 returned zero evidence — e.g., all channels failed or query didn't match), skip the LLM call entirely and return the explicit "근거를 찾지 못했습니다" response — do not spend a provider call on a request that cannot be grounded.

### Source-forged-anchor stripping point (auto-selected)

- **D-04:** CITE-06 ("수집된 소스가 위조한 `[[...]]` 앵커가 수집 시점에 제거된다") is implemented at **parse time**, in `apps/worker/src/worker/handlers/parse.py`, before chunking — not per-chunk. Rationale: a forged `[[wiki:...]]`/`[[src:...]]` token could straddle a chunk boundary and evade a naive per-chunk regex; stripping the raw extracted text once, before `chunk_text()` runs, closes that gap structurally. This is prompt-injection-through-source defense (CITE-06's stated purpose), independent of and prior to the per-response anchor issuance in D-02.
  - **Reversibility:** reversible — a text-transform step, not a schema change.

### Conflict detection trigger and method (Claude's discretion — flagged for researcher)

- **D-05:** QC-01 conflict detection ("의미적으로 유사하되 상충하는 내용") runs as a step appended to the existing `link_sync` or a new job type chained after `compile` (worker job-chain pattern already established, `complete_job_and_chain()`), not as a synchronous part of the Ask request path — conflict detection is a write-time concern (marking pages `disputed`), not a read-time one. Candidate approach for the researcher to validate: use `wiki_embeddings` (already computed, Phase 4) for semantic-similarity candidate pairs above a threshold, then an LLM classification call (structured output, reusing `worker.llm.complete_structured`) to decide contradiction vs. legitimate variation. **This is intentionally left for `gsd-phase-researcher` to firm up** — the detection *trigger point* (write-time, chained job) is decided; the detection *algorithm* is not, because it directly affects LLM cost (OPS budget guardrails, Phase 3) and needs research into false-positive rates before being locked.

### Verification-transition authorization (auto-selected — matches existing role pattern)

- **D-06:** QC-02's verification-transition API (`verified_by`/`verified_at`/`expires_at`, already columns on `wiki_pages` since `0007`) requires `editor` role or above (matches `workspace_role()` grading `owner(3) > editor(2) > viewer(1)` already enforced project-wide by RLS helpers) — `viewer` remains read-only. This mirrors every other write path in the project (SEC-04's 0-rows-affected → 403 pattern applies here too).

### Read APIs — scope per API-04's carve-out (auto-selected)

- **D-07:** API-04 explicitly excludes anything "RSC 직접 읽기로 대체 가능한" — plain-table reads the Next.js dashboard can do directly against Supabase under RLS need no API-layer duplicate. Phase 5 builds only the reads that need server-side computation the client cannot safely or efficiently do itself:
  1. **Graph read** — bounded `wiki_links` traversal (depth ≤ 2, fan-out cap, cycle guard — same bounds RTV-07 already fixed for the retrieval graph channel) is server-side because an unbounded recursive CTE run from the client via RLS-scoped RPC without server-side bound enforcement would let a client request an expensive/unbounded traversal.
  2. **Job status** — already substantially covered by the existing `apps/api/src/api/routers/jobs.py` (Phase 2/3). Phase 5 should audit it against API-04's wording rather than assume a gap; extend only if a genuine gap is found (e.g., aggregate progress across the `parse→compile→link_sync→embed` chain for a single `raw_source_id`).
  3. **Wiki/source detail reads** — the planner/researcher should verify per-endpoint whether direct RSC+RLS reads suffice (likely yes for a single wiki page or source-chunk list) versus needing computed fields (e.g., `disputed` rollups across a page's cited sources) that justify a dedicated endpoint.
  - This is intentionally scoped narrow rather than "build full CRUD read APIs for every table" — the requirement's own wording carves that out, and building unnecessary duplicate read paths contradicts CLAUDE.md's no-speculative-abstraction guidance.

### Prompt template selection and language matching (auto-selected — schema and seed already exist)

- **D-08:** API-02 (situational `ask` prompt template selection) and API-03 (answer language follows question language) consume the already-seeded `prompt_templates` table (`target_type='ask'`, 4 global defaults: 기술 심층 분석/경영진 요약/실행 항목 추출/FAQ·가이드 생성 — `0006_seed_prompts.sql`). The Ask request accepts an optional `template_id` (defaulting to the `is_default=true` row for `target_type='ask'`); language-following is a system-prompt instruction, not a separate translation pass — the existing `render_template()` (`worker/llm.py`, `{{variable}}` double-brace convention, `03-CONTEXT.md`'s "no `str.format`" anti-pattern) is reused, not reimplemented.

### Claude's Discretion

- Exact SSE event payload field names/shapes beyond the mandated `meta`/`delta`/`citations`/`done` event *names* and their *order* (API-01) — the planner should design these to carry what CITE-05's four metrics (`dual_citation_rate`, `unsourced_sentence_ratio`, `fabricated_anchor_count`, `cited_anchor_count`) need, computed once per response and attached to the `citations` or `done` event.
- `unsourced_sentence_ratio` measurement method (sentence-splitting approach for a Korean/English/mixed corpus) — no established pattern in this codebase yet; researcher should investigate options rather than the planner picking one unresearched.
- Internal LLM-listener route path and whether it lives in the same worker FastAPI app as query-embedding or a separate one (see D-01 discretion note above).

### Post-research addendum (auto-selected — resolves 05-RESEARCH.md's open questions)

`05-RESEARCH.md` (gsd-phase-researcher, committed `d0d857a`) surfaced findings not anticipated at discussion time and posed 3 open questions. Auto-mode resolves them here rather than leaving them for the planner to guess at:

- **D-09 (Ask budget-cap enforcement is IN SCOPE, not deferred):** The researcher found that `enqueue_source_job`'s monthly-budget check (`workspaces.monthly_budget_micros` vs `usage_events`, OPS-01) only gates *queued* jobs — Ask's synchronous LLM call has no budget gate at all, so it can silently blow through the cost cap this project explicitly built to prevent. Deferring this would ship Phase 5 with a real, known cost-safety hole in the exact area (`OPS-01`) the project's own budget guardrail exists for. Since the new worker-side LLM listener already needs a `service_client` to write `usage_events` (INSERT is `service_role`-only), checking the budget before opening the OpenRouter stream is a cheap addition to work already planned, not new scope. — **Reversibility:** reversible — an additional pre-check, not a schema or contract change.
- **D-10 (update the seeded `target_type='ask'` prompt templates unconditionally):** The researcher found the 4 seeded templates (`0006_seed_prompts.sql`) instruct the model to cite with the *real* slug/chunk-UUID, predating D-02's short-alias scheme (`[[wiki:w1]]`). Left unfixed, the model would be told to do something CITE-01 explicitly forbids (require the model to reproduce IDs verbatim), silently defeating the anchor-alias design this phase's whole citation-integrity story depends on. A new migration (`0012`, matching the project's append-only numbering convention) updates the instruction text — this is a correctness fix for a design conflict, not a discretionary improvement.
- **D-11 (graph-read RPC numeric bounds — planner's discretion, but anchored to existing precedent):** No UI consumer exists yet to empirically validate fanout/depth limits against (Phase 6 builds the canvas). Rather than inventing new numbers, mirror the bounds RTV-07 already fixed for Phase 4's graph *retrieval* channel (depth ≤ 2, fan-out cap, cycle guard) for consistency — two different bounded-graph-traversal limits in the same codebase, one for search-time expansion and one for read-time display, is exactly the kind of inconsistency a future session would have to reconcile later for no benefit.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contract and requirements
- `.planning/ROADMAP.md` §Phase 5 (211-224행) — goal, 12 requirements, 5 success criteria.
- `.planning/REQUIREMENTS.md` §Citation Integrity (CITE-01…06, 84-89행) · §Answer APIs (API-01…04, 93-96행) · §Quality Control (QC-01…02, 100-101행) — requirement text.
- `.planning/REQUIREMENTS.md` 277행 — QC-01/QC-02 rationale for being in Phase 5 (conflict detection sits on top of search; verification transitions depend on `0007`'s columns).
- `.planning/PROJECT.md` §Core Value — "원문 청크와 컴파일된 위키 페이지 양쪽으로 추적 가능해야 한다" is this phase's entire reason to exist; dual citation breaking makes the product "그냥 또 하나의 RAG 챗봇."

### Prior-phase decisions this phase inherits (do not re-litigate)
- `.planning/phases/02-security-spine-and-shared-domain/02-CONTEXT.md` > **D-06** — "capability absence, not import blocking" security model. Root cause of D-01 above.
- Same file > **D-07/D-08** — `BaseAppSettings`/`ApiSettings`/`WorkerSettings` split and `service_client()` factory pattern. The new internal LLM listener's settings follow the same shape as `QueryEmbeddingService`'s.
- Same file > **D-11~D-13** — 0-rows-affected → 403, no 404 (enumeration-attack defense), single exception handler in `api/errors.py`. D-06 (verification-transition auth) reuses this.
- `.planning/phases/03-ingest-and-compile-pipeline/03-CONTEXT.md` > **D-04/D-05** — embedding provider fixed to OpenRouter, no fallback, `embedding_version` encodes host+model. Not directly touched by Phase 5 but the internal-listener pattern D-01 reuses was proven here first (chronologically the embedding boundary came from this phase's provider decision, formalized in Phase 4).
- `.planning/phases/04-hybrid-retrieval-and-fusion/04-CONTEXT.md` > **D-05~D-08** — fusion policy lives in a versioned Python layer; Phase 5 must not reach into or duplicate that policy, only consume `RetrievalService.retrieve()`'s `RetrievalResult`.
- `docs/architecture/query-embedding-boundary.md` — the exact pattern D-01 mirrors. Read in full before designing the LLM listener; especially the "Required invariants" and "Rate-limit decision" sections (token-bucket, not lifetime counter — a past worker listener had this bug, already fixed in commit `6a14144`, do not reintroduce a lifetime-counter design for the new listener).
- `docs/ops/retrieval-policy-change-log.md` — if Phase 5 discovers Phase 4's evidence shape is insufficient for citation assembly (e.g., missing a field), the fix path is a policy-version bump there, not an ad hoc field bolted onto Phase 5's response model.

### Existing schema (reuse, do not reimplement)
- `supabase/migrations/0001_core_schema.sql:143-149` — `wiki_pages.verification_status` CHECK (`verified`/`partial`/`unverified`/`disputed`) and `disputed` boolean. QC-01's target field.
- `supabase/migrations/0007_search_and_queue_extensions.sql:239-260` — `verified_by`/`verified_at`/`expires_at` columns + comments. QC-02's target fields, already migrated and validated.
- `supabase/migrations/0006_seed_prompts.sql:129-249` — 4 seeded `target_type='ask'` prompt templates (icons, system prompts, `{{question}}` placeholder). API-02's data source.
- `supabase/migrations/0002_search_schema.sql:163-209` — `wiki_links` schema (`to_wiki_id IS NULL` = red link, `resolved` generated column). D-07's graph-read target.

### Existing code (reuse, do not reimplement)
- `packages/core/src/nexuswiki_core/rrf.py` — `EvidenceHit` dataclass (`kind`, `evidence_id`, `document_id`, `rank`, `metadata`, `channels`, `contributions`, `rrf_score`). D-02's anchor issuance enumerates this.
- `apps/api/src/api/services/retrieval.py` + `apps/api/src/api/routers/retrieval.py` — `RetrievalService`, `RetrievalResult`, existing `/workspaces/{id}/retrieval` route and its `HTTPBearer`+`UserDb` auth pattern. The Ask router follows the identical auth wiring.
- `apps/api/src/api/errors.py` — single exception-handler registration point (`register_error_handlers`), `WorkspaceForbidden`, SQLSTATE→HTTP mapping. Any new Phase 5 error types register here, not inline in routers.
- `apps/worker/src/worker/query_embedding.py` — `QueryEmbeddingService`, its token-bucket rate limiter, internal-bearer-token auth-before-quota ordering, and its `__main__.py` wiring. D-01's LLM listener is a sibling of this, built the same way.
- `apps/worker/src/worker/llm.py` — `complete_structured()`, `render_template()`, `openrouter_client()`, `STRUCTURED_OUTPUT_MAX_ATTEMPTS`. Ask's streaming call is a new function in this module (or a sibling), not a rewrite of the structured-output path COMP-01 uses — streaming and structured-JSON-with-retry are different call shapes against the same provider.
- `apps/api/src/api/routers/jobs.py` — existing job-status/control router. Audit against API-04 before adding new job-status endpoints (D-07.2).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RetrievalService.retrieve()` → `RetrievalResult(evidence: list[EvidenceHit], meta: dict)` — Phase 5's only input from Phase 4. Do not re-query the database directly for evidence.
- `worker.llm.openrouter_client()` / `WorkerSettings` — OpenRouter HTTP client construction pattern; the new streaming listener reuses the client construction, not `complete_structured()` itself (that function is non-streaming, retry-oriented — wrong shape for SSE).
- `api.errors.register_error_handlers` — single point for the "근거를 찾지 못했습니다" explicit-no-evidence response and any new citation-specific error types.

### Established Patterns
- **Worker owns provider secrets; API proxies via private internal HTTP + dedicated bearer token** (Phase 4, formalized in `docs/architecture/query-embedding-boundary.md`). D-01 is this pattern's second application.
- **0 rows affected on write → 403, single exception handler, no 404** (Phase 2, D-11~13). QC-02's verification-transition endpoint follows this.
- **Job chain via `complete_job_and_chain()`, jobs never UPDATEd directly** (Phase 2/3). D-05's conflict-detection trigger point follows this if implemented as a chained job.
- **Structured LLM output = prompt + Pydantic + 3 retries, never provider-native `response_format`** (`checklists.json > decisions.structured_output`, OpenRouter constraint from CLAUDE.md). Does not apply directly to Ask's streaming text generation, but any *classification* sub-call (e.g., D-05's conflict classifier) should use this existing pattern, not invent a new one.
- **Korean comments/commits, English identifiers** — maintained throughout Phase 1-4; Phase 5 code should match.

### Integration Points
- `apps/worker/src/worker/__main__.py` — where the query-embedding listener is wired into the worker process; the new LLM-streaming listener attaches here too (exact shape is D-01's discretion note).
- `apps/api/src/api/main.py` — `create_app()` lifespan/settings injection point; a new internal-LLM-client settings field (mirroring `QUERY_EMBEDDING_INTERNAL_URL`/`_TOKEN`) lands in `ApiSettings` here.
- `railway.json` — the query-embedding listener's private-only deployment property is declared here; the new LLM listener needs the same declaration, and `scripts/ci_check_query_embedding_boundary.sh` is the CI guard pattern to replicate for the new secret boundary (a sibling script, e.g. `ci_check_llm_boundary.sh`, or an extension of the existing one — planner's call).

</code_context>

<specifics>
## Specific Ideas

No user-supplied product-specific references (auto mode — this phase's discussion was Claude-run per explicit user instruction to continue the GSD process automatically at the Phase 4→5 boundary). All decisions above are derived from locked project-level decisions (`checklists.json`, prior phase CONTEXT.md files) and established codebase patterns, chosen to be the option most consistent with existing precedent rather than the most novel one.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (No scope-creep suggestions arose since this was an auto-run discussion, not an interactive one.)

</deferred>

---

*Phase: 5-Citation Integrity and Answer APIs*
*Context gathered: 2026-08-11*
