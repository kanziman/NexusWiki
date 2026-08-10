# Phase 4: Hybrid Retrieval and Fusion - Context

**Gathered:** 2026-08-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a measured five-channel retrieval path: four first-wave channels run concurrently, RRF fuses their results, and a bounded graph expansion runs as a second wave. The phase establishes the golden corpus and benchmark evidence needed to tune this path. It does not produce answer generation or dual-citation APIs (Phase 5), a dashboard (Phase 6), or a separate graph database.

</domain>

<decisions>
## Implementation Decisions

### Golden Query Set
- **D-01:** Evaluate every golden query with evidence-unit gold labels: required source chunks and wiki pages, plus explicitly allowed alternative evidence.
- **D-02:** Build 30–50 queries around real user scenarios, distributed across Korean, English, and mixed-language queries.
- **D-03:** Use a small representative corpus with clear provenance and a version-pinned dataset for repeatable evaluation.
- **D-04:** A retrieval result passes when required evidence is recovered within top-k and its ranking position meets the recorded threshold.

### Fusion Policy
- **D-05:** Keep channel weights, `k`, and candidate limits in a versioned Python policy layer, never in SQL. — **Reversibility:** costly — every benchmark, API consumer, and retrieval experiment must continue to identify the exact policy version that produced its result.
- **D-06:** Start the four first-wave channels at equal RRF weights. Change weights only when a golden-set benchmark records evidence for the change.
- **D-07:** Define separate, versioned policy constants for per-channel over-fetch and final `requested_k`; tune them against the golden set rather than fixing them in database functions.
- **D-08:** Require a recorded before/after golden-set benchmark, including recall and rank metrics, before adopting a fusion-policy change.

### the agent's Discretion
- The planner and researcher may select the precise metric names, initial numeric values, corpus content, and benchmark tooling, provided they preserve the decisions above and make their choices reproducible.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contract and product constraints
- `.planning/ROADMAP.md` §Phase 4 — phase goal, nine RTV requirements, and success criteria.
- `.planning/REQUIREMENTS.md` §Retrieval (RTV-01…RTV-09) — mandatory two-wave retrieval, observability, failure behavior, and benchmark requirements.
- `.planning/PROJECT.md` §Constraints and §Key Decisions — Postgres/RLS boundary, Korean tokenizer contract, HNSW post-filter risk, and graph-store decision.

### Existing search and index contracts
- `supabase/migrations/0007_search_and_queue_extensions.sql` — current `search_chunks` RPC, authenticated/RLS path, and all three HNSW GUCs.
- `supabase/tests/0008_search_contract.sql` — executable contract for search-function shape, GUC configuration, ACLs, embedding dimensions, and HNSW index plans.
- `supabase/migrations/0002_search_schema.sql` — the five-channel schema: vector, lexical bigram, and `wiki_links` graph foundations.
- `packages/core/src/nexuswiki_core/tokenizer.py` — shared index/query Korean bigram normalization and tokenization contract.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `packages/core/src/nexuswiki_core/tokenizer.py` — shared normalization and bigram functions already enforce the lexical-query contract.
- `apps/worker/src/worker/embedding.py` and `apps/worker/src/worker/handlers/embed.py` — established 1024-dimensional embedding provider and persistence path.
- `supabase/migrations/0007_search_and_queue_extensions.sql` — existing source-vector RPC demonstrates the RLS-safe HNSW search pattern.

### Established Patterns
- Search uses Postgres RPC with requester JWT, not `service_role`, so RLS remains active.
- HNSW filtering is post-index: `hnsw.iterative_scan`, `hnsw.ef_search`, and `hnsw.max_scan_tuples` must be configured together and insufficient returns must remain observable.
- Korean lexical search uses application-produced bigrams with `phraseto_tsquery('simple', bigram(query))`.

### Integration Points
- Retrieval will consume `source_chunks`, `wiki_embeddings`, `wiki_pages.search_tsv`, `source_chunks.search_tsv`, and `wiki_links`.
- The Phase 4 policy layer must attach enough metadata to later Phase 5 answer APIs for citation assembly without changing the database-owned fusion policy boundary.

</code_context>

<specifics>
## Specific Ideas

No additional product-specific references were supplied. Use ordinary retrieval-quality metrics, but preserve the evidence-unit labels, language mix, versioned corpus, and policy-change audit trail above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 4-Hybrid Retrieval and Fusion*
*Context gathered: 2026-08-11*
