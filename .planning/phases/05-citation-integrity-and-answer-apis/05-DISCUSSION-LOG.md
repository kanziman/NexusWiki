# Phase 5: Citation Integrity and Answer APIs - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-11
**Phase:** 5-Citation Integrity and Answer APIs
**Areas discussed:** LLM call transport boundary, Citation anchor format/issuance, double_citation computation timing, Source-forged-anchor stripping point, Conflict detection trigger/method, Verification-transition authorization, Read API scope

**Mode:** `--auto` — run per explicit user instruction ("실행하고 그 이후에도 GSD 프로세스에 따라서 자동으로 계속 진행해줘. 승인게이트시 추천안대로 진행") after user confirmed via AskUserQuestion to proceed automatically into Phase 5. No interactive AskUserQuestion calls were made during this discussion; Claude selected the recommended option for every gray area, single-pass, and logged rationale inline in CONTEXT.md.

---

## LLM call transport boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Mirror query-embedding boundary (worker owns secret, private listener, API proxies) | Consistent with locked `02-CONTEXT.md > D-06` ("capability absence, not import blocking") and Phase 4 precedent | ✓ |
| Give `apps/api` its own `OPENROUTER_API_KEY` | Simpler wiring, but directly violates D-06's locked security model | |

**Claude's choice:** Mirror the query-embedding boundary (D-01 in CONTEXT.md).
**Notes:** This is not a coin-flip default — it is the only option consistent with a decision the user already locked in Phase 2. The alternative was rejected, not merely deprioritized.

---

## Citation anchor format and issuance

| Option | Description | Selected |
|--------|-------------|----------|
| Sequential per-request alias (`[[wiki:w1]]`, `[[src:s1]]`, ...) | Short, request-scoped, no stored state | ✓ |
| Hash-derived short alias | Adds complexity with no requirement-driven benefit | |

**Claude's choice:** Sequential per-request alias, enumerated from `RetrievalService.retrieve()` evidence order.

---

## `double_citation` computation timing

| Option | Description | Selected |
|--------|-------------|----------|
| Post-hoc parse after full stream accumulation | Required by API-01's fixed event order (citations after all deltas) | ✓ |
| Incremental validation mid-stream | Impossible to do correctly — anchor tokens can split across delta chunks | |

**Claude's choice:** Buffer server-side, parse once the provider stream ends, emit `citations` then `done`.

---

## Source-forged-anchor stripping point

| Option | Description | Selected |
|--------|-------------|----------|
| Strip at parse time (before chunking) | Closes the chunk-boundary evasion gap structurally | ✓ |
| Strip per-chunk | A forged anchor split across a chunk boundary would evade a naive per-chunk regex | |

**Claude's choice:** Parse-time stripping in `apps/worker/src/worker/handlers/parse.py`.

---

## Conflict detection trigger and method

| Option | Description | Selected |
|--------|-------------|----------|
| Write-time, chained job after compile/link_sync | Matches existing job-chain pattern; conflict marking is a write concern | ✓ (trigger point only) |
| Read-time, computed during Ask requests | Would add unbounded LLM cost to every read; inconsistent with OPS budget guardrails | |

**Claude's choice:** Trigger point decided (write-time, chained job). **Algorithm intentionally left open** — flagged for `gsd-phase-researcher` to investigate semantic-similarity + LLM-classification approaches and their false-positive rate before locking, since it directly affects LLM cost.

---

## Verification-transition authorization

| Option | Description | Selected |
|--------|-------------|----------|
| `editor` role or above | Matches every other write path's role gate project-wide | ✓ |
| `viewer` can also verify | Would make verification meaningless as a quality signal; inconsistent with role grading | |

**Claude's choice:** `editor`+ only, enforced the same way as existing write paths (0-rows-affected → 403).

---

## Read API scope (API-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Build only what needs server-side computation (graph traversal, possibly job-chain aggregation) | Matches API-04's explicit carve-out for RSC-replaceable reads | ✓ |
| Build a full CRUD read-API layer for every table | Contradicts API-04's own wording and CLAUDE.md's no-speculative-abstraction guidance | |

**Claude's choice:** Narrow scope — graph read (bounded traversal) is definitely needed; job-status and wiki/source detail reads should be audited against the existing `jobs.py` router and RSC capabilities before adding anything new.

---

## Claude's Discretion

- SSE payload field shapes beyond the mandated event names/order (API-01).
- `unsourced_sentence_ratio` measurement method — no established pattern in this codebase; deferred to research.
- Whether the new LLM listener shares a FastAPI app with `QueryEmbeddingService` or is a sibling app.

## Deferred Ideas

None — auto-mode discussion stayed within phase scope; no scope-creep suggestions arose (no user present to suggest them).
