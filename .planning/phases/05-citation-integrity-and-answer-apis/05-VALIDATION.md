---
phase: 5
slug: citation-integrity-and-answer-apis
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-11
validated: 2026-08-12
---

# Phase 5 — Validation Strategy

> Retroactive Nyquist audit. All Phase 05 roadmap requirements have executable, passing automated coverage.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 with pytest-asyncio 1.4.0 |
| **Config file** | root `pyproject.toml` (`asyncio_mode = auto`, `--import-mode=importlib`; all core/API/worker test paths) |
| **Quick run command** | `uv run pytest apps/api/tests/test_ask_router.py apps/api/tests/test_ask_citations.py apps/api/tests/test_graph_router.py apps/worker/tests/test_llm_stream.py apps/worker/tests/test_handlers.py apps/worker/tests/test_queue.py -x` |
| **Full suite command** | `uv run pytest -q` |
| **Observed runtime** | 28s on 2026-08-12, exit status 0 |

## Sampling Rate

- After every task commit, run the focused command recorded for that task.
- After every wave and before phase verification, run `uv run pytest -q`.
- The slowest focused coverage is the disposable local-Supabase integration fixture; it remains bounded and is included in the full suite.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement(s) | Automated evidence | Status |
|---------|------|------|----------------|--------------------|--------|
| 05-01-1 | 01 | 1 | API-01 | `apps/worker/tests/test_llm_stream.py::{test_unauthenticated_request_is_rejected_before_any_provider_call,test_authenticated_request_relays_injected_bytes_unchanged}` | ✅ green |
| 05-01-2 | 01 | 1 | CITE-01, CITE-02, CITE-03, CITE-04, API-01, API-03 | `apps/api/tests/test_ask_router.py::{test_no_evidence_short_circuits_before_any_llm_call,test_grounded_answer_streams_meta_delta_citations_done_with_fabrication_stripped}`; `packages/core/tests/test_citations.py` | ✅ green |
| 05-02-1 | 02 | 1 | API-04, QC-01, QC-02 | schema behavior exercised by graph, conflict, and verification integration tests below; migration structure check recorded in `05-02-SUMMARY.md` | ✅ green |
| 05-02-2 | 02 | 1 | API-04, QC-01, QC-02 | local and linked-Cloud migration application recorded in `05-02-SUMMARY.md` | ✅ green |
| 05-03-1 | 03 | 2 | CITE-06 | `apps/worker/tests/test_handlers.py::test_parse_strips_forged_anchors_before_chunk_offsets_are_calculated` | ✅ green |
| 05-03-2 | 03 | 2 | CITE-05 | `packages/core/tests/test_sentences.py`; `apps/api/tests/test_ask_citations.py::test_resolve_citations_reports_dual_and_unsourced_sentence_metrics` | ✅ green |
| 05-03-3 | 03 | 2 | API-02 | `apps/api/tests/test_ask_router.py::{test_visible_requested_template_is_used_for_ask,test_invisible_requested_template_falls_back_to_default}` | ✅ green |
| 05-04-1 | 04 | 2 | API-01 | `apps/worker/tests/test_service_client.py::{test_workspace_budget_helpers_read_the_cap_and_sum_usage_since,test_workspace_budget_helpers_distinguish_no_cap_from_zero_spend}` | ✅ green |
| 05-04-2 | 04 | 2 | API-01 | `apps/worker/tests/test_llm_stream.py::{test_over_budget_request_is_rejected_before_any_provider_call,test_completed_stream_records_latest_provider_usage_once,test_completed_stream_without_usage_records_an_empty_usage_event}` | ✅ green |
| 05-05-1 | 05 | 2 | QC-02 | `apps/api/tests/test_workspaces_isolation.py::{test_verify_foreign_wiki_is_forbidden,test_owner_verification_is_trigger_stamped_and_viewer_cannot_change_it}` | ✅ green |
| 05-05-2 | 05 | 2 | API-04 | `apps/api/tests/test_graph_router.py::{test_authenticated_tenants_cannot_read_each_others_graph_scope,test_graph_endpoint_returns_resolved_outgoing_edges,test_graph_bounds_are_rejected_before_the_rpc}` | ✅ green |
| 05-06-1 | 06 | 3 | QC-01 | `apps/worker/tests/test_service_client.py::{test_conflict_candidate_rpc_posts_its_bounded_similarity_arguments,test_set_wiki_page_disputed_writes_only_dispute_state}` | ✅ green |
| 05-06-2 | 06 | 3 | QC-01 | `apps/worker/tests/test_handlers.py::{test_embed_chains_wiki_scope_to_conflict_check_but_leaves_source_terminal,test_conflict_check_marks_both_pages_only_for_real_contradictions,test_conflict_check_skips_variations_and_zero_candidate_llm_calls}`; `apps/api/tests/test_jobs_router.py::test_conflict_check_has_a_named_final_job_progress_step` | ✅ green |
| 05-07-1 | 07 | 4 | QC-02, OPS-01 | real-stack `apps/worker/tests/test_queue.py::{test_local_budget_aggregate_is_complete_and_private,test_local_automated_dispute_retains_human_verification_audit}` | ✅ green |
| 05-07-2 | 07 | 4 | OPS-01 | `apps/worker/tests/test_service_client.py::test_usage_aggregate_accepts_scalar_and_rejects_unexpected_shape`; `apps/worker/tests/test_worker_main.py::test_ask_budget_uses_monthly_spend_and_rejects_equal_cap` | ✅ green |
| 05-07-3 | 07 | 4 | QC-02, OPS-01 | real local-Supabase coverage in `apps/worker/tests/test_queue.py::{test_local_budget_aggregate_is_complete_and_private,test_local_automated_dispute_retains_human_verification_audit}` | ✅ green |
| 05-07-4 | 07 | 4 | QC-02, OPS-01 | `supabase db push --yes` plus linked schema dump recorded in `05-07-SUMMARY.md`; local behavioral regression tests above remain repeatable | ✅ green |

## Requirement Coverage

| Requirement | Automated tests | Status |
|-------------|-----------------|--------|
| CITE-01 | `test_issued_pattern_matches_the_exact_alias_shape_this_server_issues`; grounded Ask SSE test | COVERED |
| CITE-02 | grounded Ask SSE test asserts resolved citations are issued-alias intersection | COVERED |
| CITE-03 | `packages/core/tests/test_citations.py`; grounded Ask SSE fabricated-count/assertion | COVERED |
| CITE-04 | `test_no_evidence_short_circuits_before_any_llm_call` | COVERED |
| CITE-05 | `test_resolve_citations_reports_dual_and_unsourced_sentence_metrics`; sentence fixtures | COVERED |
| CITE-06 | `test_parse_strips_forged_anchors_before_chunk_offsets_are_calculated` | COVERED |
| API-01 | worker private-listener, Ask SSE-order, budget preflight, and usage-recording tests | COVERED |
| API-02 | visible and RLS-hidden template-selection tests | COVERED |
| API-03 | grounded Ask test exercises the seeded/template question path without a translation layer | COVERED |
| API-04 | graph tenant/bounds/integration tests; jobs progress route test | COVERED |
| QC-01 | candidate-RPC, conflict handler, job-chain/status tests | COVERED |
| QC-02 | requester verification/RLS test and real service-role dispute audit-preservation test | COVERED |
| OPS-01 | complete 1,001-row aggregate, requester-denial, inclusive-cap integration test | COVERED |

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Browser `fetch`/`ReadableStream` rendering of the SSE stream | API-01 | No Ask frontend exists until Phase 6; server framing is covered through ASGITransport. | In Phase 6, exercise a browser client against a grounded question and confirm `meta → delta* → citations → done`. |
| Conflict false-positive rate on a production-scale corpus | QC-01 | Fixture tests establish decision and safety boundaries, not real-corpus semantic quality. | Review a production compile batch, sample candidate pairs, and tune the similarity threshold only with recorded evidence. |
| Repeat linked-Cloud migration inspection | QC-02, OPS-01 | Requires the linked production-like Supabase project and deployment authority. It was completed for `0013`, with definition evidence in `05-07-SUMMARY.md`. | Before a future schema change, run the plan's `supabase db push --yes` and linked schema-dump check. |

## Validation Sign-Off

- [x] All 17 tasks have automated verification or downstream behavioral integration coverage.
- [x] Sampling continuity has no sequence of three tasks without an automated command.
- [x] All 13 requirements (12 roadmap requirements plus OPS-01 gap-closure invariant) are covered by green automated tests.
- [x] No watch-mode flags are used.
- [x] Full-suite feedback completed in 28s on this audit.
- [x] `nyquist_compliant: true` is set.

## Validation Audit 2026-08-12

| Metric | Count |
|--------|-------|
| Tasks audited | 17 |
| Requirements audited | 13 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Full-suite result | PASS (`uv run pytest -q`, exit 0) |

**Approval:** validated — Nyquist-compliant. Manual-only items are environment/product-quality observations, not missing automated requirement coverage.
