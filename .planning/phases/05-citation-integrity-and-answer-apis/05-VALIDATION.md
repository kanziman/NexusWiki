---
phase: 5
slug: citation-integrity-and-answer-apis
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-11
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio 1.4.0 [VERIFIED: `pyproject.toml:14-17`, `uv run pytest --version`] |
| **Config file** | root `pyproject.toml` (`[tool.pytest.ini_options]`, `--import-mode=importlib`, `testpaths` covers all 3 workspace members) |
| **Quick run command** | `uv run pytest apps/worker/tests/test_llm_stream.py apps/api/tests/test_ask_router.py -x` (new test files; planner assigns final names) |
| **Full suite command** | `uv run pytest` (from repo root — runs `packages/core/tests`, `apps/api/tests`, `apps/worker/tests`) |
| **Estimated runtime** | ~30s (current suite is 182 tests / 29s; Phase 5 adds a bounded number of new unit + 2 real-DB integration files) |

---

## Sampling Rate

- **After every task commit:** Run the targeted changed test file — `uv run pytest <changed test file> -x`
- **After every plan wave:** Run `uv run pytest` (full suite)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30s (full-suite runtime; no long-running/watch-mode tooling in this project)

---

## Per-Task Verification Map

*Pre-planning stub — `gsd-planner` assigns concrete Task IDs/Wave numbers per `04-VALIDATION.md`'s established pattern; requirement→test mapping below is the authoritative source until then.*

| Requirement | Behavior | Test Type | Automated Command | File Exists |
|-------------|----------|-----------|---------------------|-------------|
| CITE-01/02/03 | Anchor issuance (short alias), parsed∩issued intersection, fabrication stripping+counting | unit | `pytest apps/api/tests/test_ask_citations.py -x` | ❌ Wave 0 |
| CITE-04 | Empty-evidence request short-circuits before any LLM call | unit | `pytest apps/api/tests/test_ask_router.py::test_no_evidence_skips_llm -x` | ❌ Wave 0 |
| CITE-05 | `dual_citation_rate`/`unsourced_sentence_ratio`/`fabricated_anchor_count`/`cited_anchor_count` computed per response | unit | `pytest packages/core/tests/test_sentences.py packages/core/tests/test_citations.py -x` | ❌ Wave 0 |
| CITE-06 | Forged `[[...]]` anchors stripped at parse time (broad pattern, before chunking) | unit | `pytest apps/worker/tests/test_handlers.py::test_parse_strips_forged_anchors -x` | ✅ extends existing file |
| API-01 | SSE `meta`→`delta*`→`citations`→`done` order via `StreamingResponse`/`ASGITransport` | integration | `pytest apps/worker/tests/test_llm_stream.py -x` (mirrors `test_query_embedding.py` shape) | ❌ Wave 0 (pattern exists) |
| API-02/03 | Prompt-template selection; answer language follows question language | unit | `pytest apps/api/tests/test_ask_router.py -k "template or language" -x` | ❌ Wave 0 |
| API-04 | Bounded graph-read RPC (`wiki_graph_neighborhood`); job-status audit vs. existing `jobs.py` | integration (real DB, RLS) | `pytest apps/api/tests/test_graph_router.py -x` (mirrors `test_hybrid_search_integration.py`) | ❌ Wave 0 (pattern exists) |
| QC-01 | Conflict-candidate detection (embeddings similarity) + LLM classification, chained job | unit + integration | `pytest apps/worker/tests/test_handlers.py -k conflict -x` | ❌ Wave 0 |
| QC-02 | Verification-transition endpoint enforces editor+ role, 0-rows→403 | integration (real DB, RLS) | `pytest apps/api/tests/test_workspaces_isolation.py -k verify -x` | ✅ extends existing isolation-test file |

*Status: all rows ⬜ pending until execution.*

---

## Wave 0 Requirements

- [ ] `apps/worker/tests/test_llm_stream.py` — new; covers API-01 (mirror `apps/worker/tests/test_query_embedding.py`'s `ASGITransport` pattern; bound stream-consumption assertions with `asyncio.wait_for`)
- [ ] `apps/api/tests/test_ask_router.py` — new; covers CITE-04, API-02, API-03
- [ ] `apps/api/tests/test_ask_citations.py` — new; covers CITE-01, CITE-02, CITE-03
- [ ] `packages/core/tests/test_citations.py` — new; covers the two-regex grammar (broad strip-time vs. narrow issued-alias) in isolation
- [ ] `packages/core/tests/test_sentences.py` — new; covers `split_sentences()` against Korean/English/mixed fixtures
- [ ] `apps/api/tests/test_graph_router.py` — new; covers API-04's graph read, real-DB RLS pattern

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE stream renders correctly in an actual browser fetch+ReadableStream consumer (not just ASGITransport) | API-01 | No frontend exists yet (Phase 6) to drive a real browser client; ASGITransport integration test covers server-side framing only | Deferred to Phase 6's dashboard Ask UI — re-verify event order end-to-end once a real client exists |
| Conflict-detection false-positive rate at production-scale corpus | QC-01 | Requires real multi-page corpus with genuine semantic overlap/contradiction, not available in unit-test fixtures | Manual review during/after first production compile batch; track false-positive rate, revisit threshold if noisy (flagged as an assumption in `05-RESEARCH.md`) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (6 new test files above)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
