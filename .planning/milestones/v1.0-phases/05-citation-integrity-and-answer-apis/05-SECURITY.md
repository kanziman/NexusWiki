---
phase: 05
slug: citation-integrity-and-answer-apis
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-12
---

# Phase 05 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| API requester → Ask API | A workspace-scoped requester submits a question, optional template selector, and receives streamed output/citations. | JWT, question text, template ID, evidence/citations |
| API → worker LLM stream | The API authenticates its stream call using the internal bearer token. | Internal bearer token, workspace/job identity, prompt and evidence |
| Worker → OpenRouter | The worker makes rate-limited, budget-gated model calls. | Prompt/evidence content, provider credentials, usage cost |
| PostgREST/RPC → database | Graph, similarity, and Ask-cost functions enforce RLS/role boundaries. | Workspace IDs, page graph data, monthly usage aggregate |
| Automated worker → wiki verification | Service-role conflict automation can transition verification status without impersonating a human reviewer. | Verification status and audit fields |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-05-01 | Information Disclosure | `llm_stream.py`, internal token | high | mitigate | Token is confined to bearer-header authentication and not logged. | closed |
| T-05-02 | Elevation of Privilege | API settings | critical | mitigate | API settings reject secret-bearing provider/service-key fields in tests. | closed |
| T-05-03 | Tampering | Ask citation resolution | high | mitigate | Citations are the intersection of parsed anchors and server-issued aliases. | closed |
| T-05-04 | Denial of Service | LLM stream | medium | mitigate | Authentication, rate reservation, and concurrency limiting precede provider work. | closed |
| T-05-05 | Tampering | Ask evidence fetch | medium | mitigate | Evidence IDs originate from server retrieval and retain requester/workspace scoping. | closed |
| T-05-06 | Elevation of Privilege | `wiki_graph_neighborhood` RPC | high | mitigate | `security invoker` and bounded server-side graph parameters retain RLS. | closed |
| T-05-07 | Elevation of Privilege | `find_similar_wiki_pages` RPC | high | mitigate | `security invoker`, both-side workspace predicates, bounds, and service-role-only execution. | closed |
| T-05-08 | Tampering | Verification audit trigger | medium | mitigate | Human transitions use `auth.uid()`; automated transitions preserve old audit values. | closed |
| T-05-09 | Tampering | Parse handler | high | mitigate | Broad forged-anchor removal runs before chunking extracted content. | closed |
| T-05-10 | Information Disclosure | Ask template selection | low | mitigate | Foreign/invalid template IDs use indistinguishable default fallback. | closed |
| T-05-11 | Denial of Service / cost | Ask budget preflight | high | mitigate | Inclusive budget check occurs before rate reservation and model stream. | closed |
| T-05-12 | Repudiation | Usage aggregation | medium | mitigate | Missing/null aggregate normalizes to zero. | closed |
| T-05-13 | Information Disclosure | Wiki verification endpoint | medium | mitigate | Workspace-scoped update produces the shared forbidden outcome. | closed |
| T-05-14 | Elevation of Privilege | Wiki verification authorization | high | mitigate | Editor-only RLS policy and viewer-denial regression cover the route. | closed |
| T-05-15 | Denial of Service | Graph API | medium | mitigate | API and RPC both enforce fanout/total-limit bounds. | closed |
| T-05-16 | Denial of Service / cost | Conflict handler | medium | mitigate | Similar-page threshold and candidate limit bound downstream LLM work. | closed |
| T-05-17 | Tampering / indirect prompt injection | Conflict LLM judge | low | accept | See accepted-risk log; forged bracket anchors are removed before ingestion and judge has no tools. | closed |
| T-05-18 | Denial of Service / cost exhaustion | Ask cost aggregate RPC | high | mitigate | Database `sum()` covers all rows after UTC cutoff; no client page cap can bypass `spent < cap`. | closed |
| T-05-19 | Information Disclosure | Ask cost aggregate RPC | high | mitigate | RPC revokes public roles and grants execution only to `service_role`; requester JWT is denied. | closed |
| T-05-20 | Repudiation | `stamp_wiki_verification` | high | mitigate | Only a non-null requester identity is stamped; automated transitions preserve `OLD` audit fields. | closed |
| T-05-21 | Tampering | Integration fixtures | medium | mitigate | Tests are loopback-scoped, generate disposable fixtures, and preserve teardown ordering. | closed |
| T-05-SC | Supply-chain tampering | Dependency installation | high | accept | No Phase 05 plan adds a package, manifest, or lockfile dependency. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-05-01 | T-05-17 | Broader prompt injection in compiled page content remains a Phase 3 COMP-01 concern. This phase removes forged bracket anchors; the judge returns constrained JSON, has no tool access, and performs no follow-on action outside its owned update. | Phase 05 plan | 2026-08-12 |
| AR-05-02 | T-05-SC | All seven plans explicitly add no new dependency. The phase diff has no Python/npm/Cargo manifest or lockfile addition. | Phase 05 plan | 2026-08-12 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-12 | 22 | 22 | 0 | gsd-security-auditor (ASVS L1; block on high) |

Evidence was verified against the Phase 05 plans/summaries, current source and migrations, tests, and Phase verification artifacts. Key gap-closure checks include `0013_ask_budget_and_verification_audit.sql`, `apps/worker/src/worker/__main__.py`, `apps/worker/src/worker/db/service.py`, and `apps/worker/tests/test_queue.py`.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-12
