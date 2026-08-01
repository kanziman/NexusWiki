# Project Research Summary

**Project:** NexusWiki
**Domain:** Multi-tenant LLM-compiled "Living Wiki" SaaS — source→wiki compilation + 5-channel hybrid retrieval with dual citations (Korean + English)
**Researched:** 2026-08-01
**Confidence:** MEDIUM-HIGH

## Executive Summary

NexusWiki is a *compile-first* knowledge product, not a RAG chatbot with a wiki skin. The closest named ancestor in the literature is Karpathy's "LLM Wiki" pattern (immutable `sources/`, entity pages with `[[wikilinks]]`, an `index.md`, an `AGENTS.md` of conventions, and three workflows: ingest / query / **maintain**), and the already-built schema maps onto it almost 1:1. The named competitors each ship one half of the promise — NotebookLM cites sources, Guru cites cards, Glean cites documents — and **nobody pairs the synthesized claim with its raw evidence per claim**. That pairing is the whole product, and it is also the thing that fails with no error message.

The application layer that experts would build on top of this data layer is: a thin FastAPI surface where routers never see a token (they receive an already-authorized workspace context); a resident single-process asyncio worker driving a **chained** job pipeline (parse → compile → link_sync → embed) rather than one monolithic `ingest` job; a two-wave retrieval pipeline where channels 1–4 run concurrently and the graph channel expands from their fused seeds; and a Next.js 15 App Router dashboard where reads go straight to Postgres under RLS and only writes/compute go through the API. The single highest-leverage structural decisions are (a) `packages/core` holding one tokenizer module shared by index-time and query-time, built and deployed as one image so drift is impossible rather than merely tested, and (b) making `service_role` *unreachable* from the API process by capability absence (no service-key field on `ApiSettings`, module split, ruff banned-api gate, CI grep) rather than by convention.

The risk profile is dominated by silent failures. Ranked: dual citation collapsing into unsourced prose while the UI renders a perfect-looking citation list (build `double_citation` from *parsed anchors*, never from the retrieval set); Korean tokenizer/normalization mismatch producing zero lexical hits with zero errors; HNSW post-filter shortfall where `strict_order` is set, considered solved, and recall is still short because `ef_search` defaults to 40; LLM-owned slugs drifting across recompiles so "idempotent" upserts generate duplicate wikis; and cost escaping through reap-driven double-billing and uncapped ingest. Every one of these is preventable with work that is cheap *now* and a rewrite later — which is why the roadmap must front-load constraints (transport, tokenizer, settings split, storage policies) before features.

## Key Findings

### Convergences — where researchers independently agreed

Independent agreement is evidence. These were reached by two or more researchers who did not see each other's work:

1. **PostgREST/supabase-py cannot express the retrieval query, and the DB transport must be chosen before any router is written.** (ARCHITECTURE Pattern 3; PITFALLS Pitfall 1; STACK §1.3.) All three independently found the same three blockers: no per-request GUC hook for `hnsw.iterative_scan`, no way to run a custom bigram `phraseto_tsquery`, no recursive CTE. All three also independently flagged that a shared mutated `supabase-py` client is a **cross-tenant read hazard under async concurrency** (STACK §1.3b, ARCHITECTURE AP1) — RLS authorizes it because the DB sees a valid-but-wrong JWT.
2. **The tail-delete idempotency gap.** ARCHITECTURE (Pattern 4 handler contract) and PITFALLS (Pitfall 5) independently concluded that upsert-on-key is idempotent only for rows written, and both prescribed a shared `upsert_and_truncate` helper. PITFALLS extends it beyond `source_chunks` to `wiki_embeddings` and `wiki_links`.
3. **Raw provider exceptions must never reach `jobs.last_error`.** ARCHITECTURE AP9 and PITFALLS Pitfall 15 / Security table, same reasoning: `jobs_select_member` grants viewers `select *`.
4. **`reap_stale_jobs` must not be left at its 15-minute default, and job monolithing is what breaks it.** ARCHITECTURE (AP7, Open Decision 5), PITFALLS (Pitfall 14) and STACK (§2.1 detail 4) all reached this independently; STACK and PITFALLS both independently asked whether `0003` exposes a heartbeat column.
5. **The Cytoscape canvas is the least load-bearing surface.** FEATURES argues cut it; ARCHITECTURE puts it last in build order (#14) and notes it hits the PostgREST 1000-row cap first; PITFALLS flags hub explosion and truncation. Three researchers, three routes, same conclusion about relative priority.
6. **Per-channel contribution metrics are the single detector for several independent failure modes** (PITFALLS 2/10/12/13; ARCHITECTURE `meta.channel_hits`). Both designed the same instrument.
7. **A per-workspace cost cap enforced at enqueue time is the v1 cost guardrail.** ARCHITECTURE (Scaling priority 1) and PITFALLS (Pitfall 19) independently, in the same order: cap → dedup index → revisit provider.

### Contradictions with PROJECT.md's locked decisions

| PROJECT.md says | Research found | Recommendation |
|---|---|---|
| "OpenRouter 경유라 structured output을 못 씀" | Only Anthropic's **native** `output_config.format` is unavailable. OpenRouter **does** support `response_format: {type:"json_schema", strict:true}` on endpoints that advertise it. Support varies **per provider endpoint**, so it needs `provider: {require_parameters: true}`, and a fallback model list silently degrades to unvalidated `json_object`. (PITFALLS 18; STACK §1.4 concurs.) | Keep the locked prompt+Pydantic+3-retries loop as the **mandatory backstop** (it must work for any env-swapped `LLM_MODEL`, and it is what catches enum drift). Add `response_format` as an opportunistic cost optimization behind a per-model capability probe. Correct the PROJECT.md wording — it is currently over-broad. |
| Supabase region = Seoul (implied by `checklists.json` open Q#2) | **Railway has no Seoul or Tokyo region.** Its only APAC region is `asia-southeast1` (Singapore). Seoul DB + Singapore compute costs ~60–80ms per DB round trip, multiplied across 5 retrieval channels and every worker query. Region is permanent per Supabase project. (STACK finding #2.) | **Choose Singapore `ap-southeast-1`** + Railway `asia-southeast1-eqsg3a`; accept one browser→API hop as the geographic penalty. P0 must measure actual RTT. Cannot be changed after project creation. |
| Constraint: `set local hnsw.iterative_scan = strict_order` 필수 | Necessary but **not sufficient**, and possibly the wrong mode. Iterative scan is bounded by `hnsw.ef_search` (default **40**) and `hnsw.max_scan_tuples` (20,000); pgvector's docs show ~4 rows returned when a predicate matches 10% of the table. And `strict_order` buys exact distance ordering that **RRF discards** — it consumes ranks only — at a measurable recall cost vs `relaxed_order`. (PITFALLS 2.) | Set all three GUCs. Benchmark `relaxed_order` vs `strict_order` on the real corpus in the retrieval phase and record the decision. Amend the constraint to "iterative_scan + ef_search + max_scan_tuples must all be set; mode is a measured decision." |
| v1 = all 32 tasks in Phases 0–4, scope unchanged | FEATURES recommends cutting the Cytoscape canvas and adds two missing items. See below. | User's call. Trade-off presented; not silently re-scoped. |

### Contradiction *between* researchers — the one decision the roadmap must force

**DB transport: raw asyncpg pool vs `SECURITY INVOKER` SQL functions over RPC.**

- **STACK §1.3 says asyncpg** for all DB access in both services. Argument: `SET LOCAL` is non-negotiable, PostgREST cannot issue it, and pushing the 5-channel search into SQL functions means putting RRF fusion, the recursive CTE and channel weighting into migrations — the layer just declared frozen. It supplies the exact mechanism (`set_config('request.jwt.claims', …, is_local=true)` inside a transaction, per Supabase discussions #30124/#22482) and the production detail that decides it (Supavisor **session** mode port 5432; direct 5432 is IPv6-only, 6543 kills prepared statements).
- **ARCHITECTURE Pattern 3 rejects raw asyncpg** for `SECURITY INVOKER` functions in a new migration `0007`, with the GUC attached to the function definition so a channel *cannot* be called without it. Argument: hand-forging the auth context makes a claim-construction bug a tenant crossing, and `SET LOCAL` on a pooled connection is a documented leak class.
- **PITFALLS Pitfall 1 lists both as viable and recommends the RPC path for v1** — a third independent vote.

**Assessment.** STACK's objection to RPC ("fusion moves into migrations") is **factually answered by ARCHITECTURE**: only the five per-channel queries live in SQL; RRF, weights, k and limits deliberately stay in Python (`retrieval/policy.py`), and ARCHITECTURE's AP3 independently forbids fusing in SQL. ARCHITECTURE's objection to asyncpg (pooled-connection tenant leak) is real but fully mitigated by `is_local=true` inside an explicit transaction, which STACK specifies correctly. Tiebreakers: RPC keeps exactly one auth path (the JWT, validated 38/38) and makes the GUC unforgettable; asyncpg avoids a migration per channel change and avoids PostgREST's `max_rows=1000`, which applies to RPC `setof` returns too — a genuine footgun the RPC side under-weights.

**Recommendation: RPC (`SECURITY INVOKER` functions in `0007`) for v1**, on 2-of-3 agreement plus the "one auth path" security argument, retaining STACK's Supavisor session-mode facts for migrations and the worker. **This must be an explicit forced decision in the first backend phase, resolved by a spike running the real 5-channel query with GUCs set — not settled by this document.** The empirical question that decides it: *does `create function ... SET hnsw.iterative_scan` actually take effect through a PostgREST RPC call?* If not, asyncpg wins immediately.

### Scope pressure on v1

The user has already decided v1 = all 32 tasks in Phases 0–4. FEATURES disagrees on three points:

- **Cut the Cytoscape knowledge canvas.** Evidence: Obsidian's graph view is the category's "graph theatre" cautionary tale; a new workspace's graph is 8 nodes and a mature one unreadable; Glean has a knowledge graph and deliberately keeps it a *ranking input*, not a user-facing canvas. Cost: Cytoscape + React 19 + fcose tuning + lens filters + `dynamic(ssr:false)`, and it is the surface most likely to hit the 1000-row cap. Proposed substitution: **per-page backlinks panel** (one reverse query on `wiki_links`; consistently rated more useful because it's in-context) + **ranked red-link backlog** (`count(*) group by target_slug` — "12 pages reference `[[온보딩 절차]]` and it doesn't exist"; no competitor ships this). Both LOW complexity, same phase. Net claim: more product for less work.
- **Two items the 32-task plan lacks.** The `maintain` workflow (dedupe / merge / lint) is the third Karpathy workflow and is what makes the wiki "living" rather than "accumulating" — FEATURES calls it the moat, HIGH complexity, v1.x. The **compile log** (which sources, which compile, which `prompt_template_id`) is the only way to settle "why does this page say that," and matters more here because prompts are swappable, so a page can change without any source changing. Both are P2 in FEATURES' own matrix — the recommendation is to *know* they are missing, not to add them to v1.
- **One schema-shaped warning.** `verification_status` has no `verified_by` / `verified_at` / `expires_at`. Sharpest empirical finding: Guru's verification is used because overdue content is **demoted in AI answers**; every product that shipped a badge with no downstream consequence saw it rot. Display-only ⇒ expect near-zero usage. Related: **do not** show the numeric `confidence` to users — two competing trust badges teach users to read neither.

Also for requirements time: FEATURES says **v1 wiki pages must be read-only by design** and the UI must say so out loud ("pages are compiled, not written"), because free-text editing collides head-on with the `(workspace_id, slug)` upsert that makes at-least-once jobs safe.

### Recommended Stack

All versions read from PyPI/npm registry JSON on 2026-08-01 (HIGH confidence). Deliberately minimal: no queue library, no ORM, no monorepo orchestrator, no React wrapper for Cytoscape.

- **uv 0.12.1 workspace** (`apps/api`, `apps/worker`, `packages/core`) — one lockfile. The *only* mechanism guaranteeing index-time and query-time bigram tokenizers are byte-identical, which PROJECT.md itself names as a silent-failure mode.
- **Python 3.13 / FastAPI 0.141.1 / Uvicorn 0.52.0** — `lifespan`, never `@app.on_event`; no Gunicorn (breaks Railway's SIGTERM drain, doubles idle memory on a $5/mo box).
- **asyncpg 0.31.0 + pgvector 0.5.0** — for whichever paths survive the transport decision; **Supavisor session mode, port 5432**.
- **openai 2.52.0 SDK for both providers** — one client at OpenRouter's base_url, one default for `text-embedding-3-small` @ 1536-d. Built-in retry covers 429/5xx, so the hand-rolled loop handles only *validation* failures.
- **pypdf 6.14.2 (BSD-3)** — chosen on **license**: PyMuPDF is AGPL-3.0, which reaches network users and is disqualifying for hosted SaaS. Quality gap matters less because the LLM rewrites the prose anyway.
- **structlog 26.1.0** — `merge_contextvars` binds `job_id`/`workspace_id` once and every downstream line carries it, including from library code.
- **Next.js 15.5.22** (hard floor 15.2.3 — CVE-2025-29927 lets a spoofed `x-middleware-subrequest` header skip middleware entirely, and this app's tenant gate *is* middleware) + React 19.2.8 + `@supabase/ssr` 0.12.4 + Tailwind 4.3.3 (CSS-first) + TypeScript pinned **5.9.3**.
- **Vitest 4.1.10 + Playwright** — Vitest **cannot render async Server Components**; documented, not configurable. Keep data fetching out of components.

Rejected: `react-cytoscapejs` (last published 2022-09-02, 45 open issues, predates React 18 StrictMode), Celery/arq/dramatiq/RQ (all need a broker, all duplicate the verified `claim_job` contract), Alembic/SQLAlchemy (second migration source of truth), Turborepo/Nx (one JS package).

### Expected Features

**Must have (table stakes):** PDF/URL/text ingest with **visible** dedupe ("이미 수집됨 — 건너뜀", never silent success); **per-source** job status plus retry on `dead`; inline citation markers **at the clause they support**, not in a trailing Sources block; hover preview; click-through to the exact passage; streaming answers; honest no-evidence state; WikiLink navigation; workspace switcher + email invite + 3 roles; answer language following question language.

**Should have (differentiators), by leverage-per-effort:** the **dual citation card pairing compiled page and source chunk per claim**; **`char_start`/`char_end` span highlight in the original** — the category's #1 unmet need and your cheapest structural advantage; **per-claim attribution enforced in Pydantic validation**; **ranked red-link backlog**; **backlinks panel**; **follow-up chips walked from `wiki_links`** at zero LLM cost.

**Defer (v1.x / v2+):** verification owner+expiry wired into RRF; typed conflict detection (temporal = staleness, should auto-resolve); `maintain` workflow; compile log; steerable compile outline; graph canvas reframed as a diagnostic; chat-only public sharing (opening the `anon` path is the highest-risk change to verified isolation); connectors; SSO/SAML.

**Do not build:** numeric confidence badge; free-text page editing; auto-recompile-everything; per-page permissions.

### Architecture Approach

*Reads go straight to Postgres under the requester's JWT; writes and compute go through FastAPI; anything slow or expensive goes through the `jobs` queue to the worker; the worker is the only thing holding the service key.* API and worker are siblings sharing `core/`, `db/`, `domain/`, `providers/`, neither importing the other — that is what makes service-key isolation structural. Layer-first, not feature-first, because at 4 routers the value is keeping `db/` and `deps.py` in exactly one place each.

1. **`domain/` (pure, zero I/O)** — tokenizer, slug normalization, chunker, citation anchor emit+parse, RRF fusion. Every correctness risk lives here; isolating it makes each a fast unit test needing neither Docker nor an API key.
2. **`db/user.py` vs `db/service.py`** — the security spine. `ApiSettings` has no service-key field at all (capability absence), enforced by four cheap layers: split settings, split module, ruff TID251 with a `worker/**` exemption, runtime tripwire. The 0-rows→403 mapping lives in `UserDb`, not scattered across routers.
3. **`worker/` — four chained job types, one per idempotency key**, advanced by a single `complete_job_and_chain()` transaction plus a `jobs_dedup_idx` partial unique index. Chaining is decided by the reaper: a monolith's p99 blows past the 15-minute window, so a *healthy* job gets stolen and double-billed.
4. **`retrieval/` — two-wave pipeline.** Channels 1–4 concurrent via `asyncio.gather(..., return_exceptions=True)` (a degraded channel drops out of fusion and is reported in `meta.channel_hits`, it does not fail the request); channel 5 expands from fused seeds because it has no query and no intrinsic score — its rank *is* hop distance, which is exactly why RRF is the right operator.
5. **Server-issued citation anchors with an alias table** — the model may only *copy* opaque short tokens (`[[src:s3]]`, not a 36-char UUID it will mangle); the server resolves them and discards anything not issued. SSE order: `meta` → `delta*` → `citations` → `done`. POST + `fetch` + `ReadableStream`, never `EventSource` (GET-only, cannot set `Authorization`).
6. **Next.js dashboard** — `/w/[workspaceId]` is the tenancy source of truth (a stale id in React state yields an empty result set with no error, indistinguishable from an empty workspace); `middleware.ts` is the only cookie writer; RSC reads direct via `@supabase/ssr`, removing roughly half the read API surface from the roadmap.

### Critical Pitfalls

1. **Dual citation collapses into unsourced prose, with no error.** The killer is building `double_citation` from *what was retrieved* instead of *what was cited* — the UI renders 12 perfect citation cards for an answer that used none. Fix: cite-then-render; `double_citation` = intersection of parsed anchors and the retrieved set; unresolved anchors are **fabricated**, stripped and counted. Instrument `cited_anchor_count`, `fabricated_anchor_count`, `unsourced_sentence_ratio`, and `dual_citation_rate` (≥1 wiki *and* ≥1 source anchor) — the north-star metric. Hard floor: zero anchors ⇒ explicit "근거를 찾지 못했습니다". **Tell: `double_citation` length always equals retrieval `k`.**
2. **Korean tokenizer — "same function" is only half of "identical tokenizers".** NFC vs NFD (macOS uploads and some PDF extractors emit NFD; a bigram over NFD produces *jamo* bigrams — disjoint index, zero results, zero errors), full-width vs half-width from Korean IMEs, and case. Fix: one module — `normalize()` doing NFKC + casefold + whitespace collapse, and `bigram()` that *requires* normalized input; `tsv_tokenizer_version` must encode the normalization form. The round-trip self-retrieval test over NFC/NFD/full-width is the highest-value test in the project. Related: **hybrid tokenization** (bigram Hangul runs, keep Latin/numeric whole) fixes index bloat and English-acronym recall in one change.
3. **HNSW post-filter shortfall.** `strict_order` alone is not the fix — set `ef_search` (100–200 for k=20) and `max_scan_tuples`, log `returned < requested_k` as a **first-class metric**, add an `EXPLAIN` regression test asserting `Index Scan using ..._hnsw_idx` (pgvector #721: the planner can silently abandon HNSW for a correct-but-20×-slower seq scan).
4. **Slug instability turns "idempotent" upserts into duplicate wikis.** Fix: the LLM emits `title`; the slug is a deterministic pure function of it, versioned like `tsv_tokenizer_version`; resolve against `aliases` and `wiki_links.target_slug` before creating a page. With at-least-once jobs, one reap-and-retry triggers this.
5. **Enum drift dead-letters every compile job.** Enum strings exist in three places — `0001` CHECK clauses, the `0006` seeded prompt, the coming Pydantic model — with no compiler between them. Fix: define once in Python, **startup assertion diffing `pg_constraint`**, inject allowed values into the prompt from that same source, and make retry #2/#3 *different* from #1 by feeding the validation error back.
6. **Isolation is lost above the database.** Beyond the known `service_client()` trap: caches keyed without tenant, chunk content in shared logs, error strings echoing another tenant's ids, an anchor map keyed on `chunk_index` instead of `chunk_id`, worker reads missing `where workspace_id` (composite FKs catch mismatched *writes*, not reads), and **prompt injection from ingested sources** — including a source that fabricates its own `[[...]]` anchors, which must be stripped at ingest.

## Implications for Roadmap

Research supports keeping the Phase 0–4 shape while **re-sequencing within phases so constraints precede features**. ARCHITECTURE's build-order items 1–3 are all "build the constraint before the feature," and each is a rewrite if deferred: the settings split touches every module, the `UserDb` wrapper touches every query, the tokenizer touches both read and write paths with a failure mode that produces no error.

### Phase 0: Bootstrap and Ground Truth
**Rationale:** Contains every decision that is permanent or gets more expensive weekly.
**Delivers:** migration `0005` with **real** `storage.objects` policies (the path convention is currently a comment, not enforcement); Supabase Cloud project in **Singapore** with **publishable/secret** keys; CLI upgraded before first push; Railway two services in `asia-southeast1` off one Dockerfile with Root Directory `/`; uv workspace with `packages/core` existing before either app; split `ApiSettings`/`WorkerSettings` + ruff banned-api + CI grep gate + client-bundle key grep; measured Railway↔Supabase RTT recorded against open question #2; production auth config hardening (currently unowned).
**Avoids:** Pitfalls 16, 17, the region trap, the `0005` ordering trap.
**P0 blockers:** `0005`; the `sb_publishable_`/`sb_secret_` env-var rename (legacy keys aren't issued to projects created after Nov 2025); region choice; uv workspace + single Dockerfile; `packages/core` before either app.

### Phase 1: Security Spine, Transport Decision, Shared Domain
**Rationale:** The transport decision is the convergent P0 architectural finding and must be settled by a **spike running the real 5-channel query with GUCs set**, before any router exists. The tokenizer must exist before both ingest and retrieval, or ingest grows its own and retrieval inherits a silent mismatch.
**Delivers:** transport decision recorded (RPC-in-`0007` recommended; asyncpg + Supavisor session mode documented as fallback); migration `0007` (retrieval functions with GUCs on the definition, `jobs_dedup_idx`, `complete_job_and_chain`, plus the free `embedding_version`/`chunker_version` columns); `db/user.py` + `db/service.py` + `deps.py` + 0-rows→403 + one isolation test; `domain/tokenizer.py` with `normalize()`/`bigram()` and the round-trip property test; worker skeleton with SIGTERM, reaper and a `noop` job type proving the queue contract before a single LLM dollar.
**Avoids:** Pitfalls 1, 10, 16.

### Phase 2: Ingest and Compile Pipeline
**Delivers:** ingest API (upload → `raw_sources` → enqueue → `202`, blocking work never in-process); `source.parse` with an **extraction quality gate** (chars/page threshold → `needs_ocr`, refuse to compile, surface the verdict in the UI); token-measured chunking with the `content[char_start:char_end] == chunk.content` property test; `wiki.compile` with deterministic slugs, the enum startup assertion and an error-feeding repair loop; `wiki.link_sync`; both embed handlers; `usage_events` + enqueue-time cost cap + input bounds + a cancel path.
**Avoids:** Pitfalls 3, 4, 5, 8, 9, 14, 15, 19.

### Phase 3: Retrieval, Fusion, Citation Integrity
**Rationale:** The product thesis, and citation integrity deserves its own slice rather than being a detail of the ask endpoint. The **golden question set (30–50 KO/EN/mixed) is a prerequisite for this phase, not an ops deliverable** — without it, every weight, `k`, chunk size and the graph channel is unfalsifiable.
**Delivers:** 5 channels with `channel_hits` metrics; rank-only RRF with explicit per-channel weights and pre-fusion dedupe of correlated wiki/source pairs (turning the correlation problem into the dual-citation feature); graph channel with depth ≤2, fan-out cap, cycle guard, `resolved = true`, **behind a default-off flag until the golden set justifies it**; server-issued alias anchors + parse + validation; SSE ask endpoint; `relaxed_order` vs `strict_order` benchmarked and recorded.
**Avoids:** Pitfalls 2, 6, 11, 12, 13.

### Phase 4: Dashboard
**Rationale:** Only needs the JWT contract, so the shell starts in parallel with Phase 2. Auth shape must be right from the first commit.
**Delivers:** auth + middleware + `/w/[workspaceId]` shell; dropzone + job-chain progress showing **real states**, not an indeterminate spinner (a 4-minute compile looking like a hang makes users re-submit, doubling cost); read-only wiki viewer with WikiLink nav, red links styled "아직 작성되지 않음 · 지금 생성", backlinks panel, ranked red-link backlog; ask UI with dual-citation cards, inline anchors resolving in-place during stream, distinct no-evidence state; canvas last (or cut).
**Avoids:** Pitfall 17 and the UX pitfalls table.

### Phase 5: Integration, Verification, Ops Baseline
**Delivers:** E2E ingest→compile→embed→search; idempotency verification including the **shrinkage** case (re-process into *fewer* units), not just same-`content_hash`; cross-tenant application-path suite; search quality/latency baseline; cost guardrails and observability; the "Looks Done But Isn't" checklist as an acceptance gate.

### Phase Ordering Rationale

- **Constraints before features**, three times over (settings split, tokenizer, transport) — each cheap now, a rewrite later, and each fails silently.
- **Two parallel tracks after the worker skeleton:** backend pipeline (2→3) and frontend shell (4) meet at the ask UI.
- **`source.embed` is independent of compile** and parallelizes with `wiki.compile`.
- **The golden set moves earlier** — from ops into retrieval — because it gates four tuning decisions.
- **Cost guardrails move earlier too**: `usage_events` + enqueue-time cap belong with the first LLM call; everything else is built on that table.

### Research Flags

Needs research/spike during planning:
- **Phase 1** — the DB transport disagreement, with a cheap empirical tiebreak. Spike it; do not plan around an assumption.
- **Phase 2** — Korean chunking parameters have **no literature**; empirical tuning, not research. PDF quality-gate thresholds need real fixtures (scanned, multi-column, table-heavy).
- **Phase 3** — RRF weight shape, `relaxed_order` vs `strict_order`, and the graph channel's net value are measurement questions requiring the golden set.

Standard patterns (skip research):
- **Phase 0** — Railway/Vercel/Supabase setup is fully documented and quoted verbatim; only the per-service config-path override is uncertain, with a documented fallback.
- **Phase 4** — the Supabase Next.js auth shape is canonical; deviating from it *is* the pitfall.
- **Worker loop** — ~150 lines of standard asyncio; research explicitly concludes nothing new should be installed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** on versions, MEDIUM on patterns | Versions read from PyPI/npm registry JSON on 2026-08-01, not memory. CVE-2025-29927 cross-confirmed across five sources. Comparative claims (PDF speed deltas, Singapore RTT) flagged as estimates. |
| Features | **MEDIUM** | Cross-verified across vendor primary docs (Guru, Glean, DeepWiki) plus peer-reviewed conflict work. No product trialed; no NexusWiki user research. Verification-feeds-ranking is the strongest single finding; graph-canvas skepticism is opinion-heavy but convergent. |
| Architecture | **MEDIUM-HIGH** | Structure recommendations HIGH — derived from the built data layer's own invariants and checked against `.planning/codebase/`. External ecosystem claims MEDIUM. |
| Pitfalls | **MEDIUM** | pgvector, OpenRouter and Supabase-Next.js claims verified against official docs and quoted. Korean normalization, RRF and cost claims are literature/practice synthesis. |

**Overall confidence:** MEDIUM-HIGH — higher than usual because the data layer is built and verified, so much of the research is *derived from ground truth* rather than inferred from the market.

### Gaps to Address

Cheap empirical checks worth doing early:

- **Does `create function ... SET hnsw.iterative_scan` survive a Supabase RPC call?** Decides the entire transport question. First thing in Phase 1's spike.
- **Does migration `0003`'s `jobs` table expose a heartbeat-writable column?** Flagged independently by STACK and PITFALLS. If a compile job can exceed the 15-minute reap without touching anything, the reaper hands a **live** job to a second worker — two concurrent LLM generations racing on the same `(workspace_id, slug)` upsert. If no such column: raise the reap timeout or split compilation into smaller jobs (splitting is better — retries get cheaper). Check before writing the worker loop.
- **Does the configured `LLM_MODEL`'s OpenRouter endpoint advertise `structured_outputs`?** One capability probe. Free money if yes; also corrects PROJECT.md.
- **Measure Railway `asia-southeast1` → Supabase `ap-southeast-1` RTT** on first deploy; the 1–2ms figure is a geographic estimate.
- **Is the `supabase-py` shared-client concurrency hazard real?** A 20-line concurrency test settles it. Not blocking.
- **Railway per-service config-as-code file path** — verify in the dashboard during the first P0 deploy, not in P4. Fallback always works.

Product questions for validation rather than research:
- **Are read-only wiki pages acceptable to users?** The biggest untested assumption in v1 scope.
- **Does anyone successfully surface contradictions to end users?** Strong academic grounding, no shipping product in the studied set. Treat typed conflict detection as an unvalidated bet.
- **Korean chunking parameters** — no literature; empirical, Phase 2.
- **Cost per compiled workspace** — no comparable public data for compile-first architectures; the cap must be set from `usage_events`.
- **"Cairni" is not findable as a product.** PROJECT.md's "Cairni 스타일" reference resolves to unrelated products. Do not anchor requirements on it; the real ancestor is the Karpathy LLM Wiki pattern.
- **Production auth config** — `config.toml` inherits CLI defaults (6-char passwords, unconfirmed email signup on a *team* product) and **no task currently owns hardening it**. Assign in Phase 0.

## Sources

### Primary (HIGH confidence)
- PyPI / npm registry JSON APIs, read 2026-08-01 — every version number in STACK.md
- `.planning/codebase/` (ARCHITECTURE, CONCERNS, CONVENTIONS, STRUCTURE, STACK) and `supabase/migrations/0001–0006` — the built data layer
- supabase.com/docs — API keys (publishable/secret → anon/service_role), signing keys/JWKS, server-side auth for Next.js, connecting to Postgres (Supavisor modes), platform regions
- docs.railway.com — config-as-code schema, regions (no Seoul/Tokyo), monorepo deployment
- pgvector README + issue #721 — `iterative_scan`, `ef_search` 40, `max_scan_tuples` 20000, planner index abandonment
- OpenRouter docs — Structured Outputs, `require_parameters`, per-endpoint variance
- CVE-2025-29927 fixed versions — JFrog, Datadog, OffSec, ProjectDiscovery, Zscaler
- RRF k=60 default — Elasticsearch, Azure AI Search, ParadeDB, Chroma

### Secondary (MEDIUM confidence)
- Guru verification docs; Glean per-claim attribution and knowledge-graph-as-ranking-input; Cognition DeepWiki `.devin/wiki.json`; NotebookLM citation UX and documented complaints; Onyx/Danswer connectors and roles
- Karpathy LLM Wiki pattern write-ups (ingest/query/maintain)
- arXiv 2412.18004, 2501.00269, 2506.08500, 2605.17301
- Supabase discussions #30124 / #22482 (`set_config` RLS pattern), #33811 / #37052 (shared-client concurrency)
- Unicode normalization for CJK search (NFC/NFD Hangul, full-width, Elasticsearch NFKC+casefold)
- astral.sh uv workspaces; railpack Python detection; nextjs.org Vitest guide (async RSC unsupported)

### Tertiary (LOW confidence — validate during implementation)
- PDF extractor speed/quality benchmark blogs (direction consistent, magnitudes unverified)
- Singapore↔Seoul RTT figures (geographic estimate — measure in P0)
- Obsidian "graph theatre" critiques (opinion-heavy but convergent)
- react-cytoscapejs React 19 failure modes (inferred, not reproduced)
- Generic SaaS sources on small-team multi-tenant needs

---
*Research completed: 2026-08-01*
*Ready for roadmap: yes*
