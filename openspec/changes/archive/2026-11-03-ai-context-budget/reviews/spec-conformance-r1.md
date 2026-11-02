# Spec Conformance Review — `ai-context-budget` (Round 1)

- **Change**: `ai-context-budget`
- **Archive 경로**: `openspec/changes/archive/2026-11-03-ai-context-budget`
- **판정 등급**: `pass`
- **미충족 항목 개수**: `0`

---

## 1. `grounded-answering` (`openspec/changes/archive/2026-11-03-ai-context-budget/specs/grounded-answering/spec.md`)

### Requirement: Ask 컨텍스트 토큰 예산과 이중 근거 쿼터

| Scenario | 판정 | 코드 경로 (WHEN / THEN) | 검증 테스트 |
| --- | --- | --- | --- |
| **긴 위키 근거가 있어도 원문 근거가 함께 보존된다** | `pass` | `packages/core/src/nexuswiki_core/context_budget.py:87-234` (`allocate_ask_context_budget`이 `has_both_kinds`일 때 `mandatory_indices = sorted([first_wiki_idx, first_source_idx])`를 1단계에서 우선 배정·절단하여 위키/원문 최소 1건씩 보장하고 `AskContextBudgetResult.as_report()` 생성), `apps/api/src/api/services/ask.py:527, 686, 792-805` (`AskService.ask`에서 `allocate_ask_context_budget` 호출 결과를 `build_issuance_map`·`_context_blocks` 및 `control_report["budget"]`에 반영) | `packages/core/tests/test_context_budget.py:8-40` (`test_allocate_ask_context_budget_preserves_dual_evidence_under_tight_budget`), `apps/api/tests/test_ask_router.py:848-938` (`test_ask_context_budget_preserves_dual_evidence_and_records_budget_report`), `apps/worker/tests/test_controlled_ai_evidence.py:514-628` (`ask_context_budget_quota`) |
| **한 종류 근거만 있을 때 남은 예산을 사용한다** | `pass` | `packages/core/src/nexuswiki_core/context_budget.py:120-128` (`has_both_kinds`가 `False`일 때 `mandatory_indices = [0]`으로 설정), `packages/core/src/nexuswiki_core/context_budget.py:140-156` (`remaining_slots == 1`이므로 `slot_cap = remaining_budget`으로 전체 예산 할당), `packages/core/src/nexuswiki_core/context_budget.py:180-205` (후속 동일 종류 근거가 잔여 토큰 상한까지 사용) | `apps/api/tests/test_ask_router.py:442-449` (`test_meta_reports_only_failed_channels_and_not_disabled_graph` — 단일 종류 `source` 근거로 `AskService.ask` 및 `allocate_ask_context_budget` 실행), `packages/core/tests/test_context_budget.py:42-58` |
| **벡터 채널과 어휘 채널이 같은 위키 문서를 반환한다** | `pass` | `packages/core/src/nexuswiki_core/rrf.py:104-108` (`fuse_ranked_hits`에서 동일 `canonical_id` 적중 시 `metadata={**hit.metadata, **previous.metadata}`로 선행 키를 보존하며 후행 채널의 `slug`·`title` 병합), `apps/api/src/api/services/ask.py:316-357, 429, 786-791` (`_fetch_evidence_content`에서 `wiki_pages`의 `slug`·`title` 보강 후 `decide_ask_route` 재판정 및 `_context_blocks` 제목 조립) | `packages/core/tests/test_rrf.py:76-104` (`test_rrf_merges_channel_metadata_without_overwriting_first_hit_keys`), `packages/core/tests/test_router.py:41-53` (`test_exact_title_with_both_kinds_is_a_lookup`, `test_exact_slug_with_both_kinds_is_a_lookup`), `apps/api/tests/test_ask_router.py:305-324` (`test_lookup_decision_is_recorded_but_the_llm_still_runs`) |

---

## 2. `usage-guardrails` (`openspec/changes/archive/2026-11-03-ai-context-budget/specs/usage-guardrails/spec.md`)

### Requirement: 구조화 출력 호출의 입력·출력 토큰 상한

| Scenario | 판정 | 코드 경로 (WHEN / THEN) | 검증 테스트 |
| --- | --- | --- | --- |
| **컴파일과 충돌 판정이 공급자를 호출한다** | `pass` | `apps/worker/src/worker/settings.py:123, 126` (`COMPILE_MAX_OUTPUT_TOKENS = 4096`, `CONFLICT_MAX_OUTPUT_TOKENS = 512`), `apps/worker/src/worker/llm.py:217, 251, 316, 327-328, 359, 378` (`_chat_body`에 `max_tokens` 포함), `apps/worker/src/worker/llm_gateway.py:86, 92-93, 108-118` (`attempt_meta["max_tokens"]` 기록 및 `complete_structured` 전달), `apps/worker/src/worker/handlers/compile.py:183, 203`, `apps/worker/src/worker/handlers/conflict.py:78, 122` | `apps/worker/tests/test_llm_gateway.py:162-183` (`test_max_tokens_is_forwarded_to_provider_and_recorded_in_usage_metadata`), `apps/worker/tests/test_handlers.py:870-877` (`test_unchanged_input_without_existing_pages_still_runs_the_llm`), `apps/worker/tests/test_handlers.py:899-966` (`test_conflict_check_truncates_oversized_pages_and_sends_max_tokens`) |
| **긴 위키 본문 쌍의 충돌 판정 입력 제한** | `pass` | `apps/worker/src/worker/settings.py:125` (`CONFLICT_MAX_INPUT_TOKENS = 4000`), `apps/worker/src/worker/handlers/conflict.py:77, 79, 85-87, 103-115` (`per_page_budget = max(1, max_input_tokens // 2)`로 두 페이지를 `truncate_text_to_tokens`로 절단하고 `metadata`에 `truncated_input`, `max_input_tokens` 기록) | `apps/worker/tests/test_handlers.py:899-966` (`test_conflict_check_truncates_oversized_pages_and_sends_max_tokens`), `apps/worker/tests/test_controlled_ai_evidence.py:296-366` (`structured_output_max_tokens`) |

---

## 3. `ai-request-tracing` (`openspec/changes/archive/2026-11-03-ai-context-budget/specs/ai-request-tracing/spec.md`)

### Requirement: Router 결정의 shadow 기록

| Scenario | 판정 | 코드 경로 (WHEN / THEN) | 검증 테스트 |
| --- | --- | --- | --- |
| **제목과 정확히 일치하는 질문** | `pass` | `packages/core/src/nexuswiki_core/router.py:57-77` (`decide_ask_route`에서 `AskRoute.LOOKUP` 판정), `apps/api/src/api/services/ask.py:745, 791, 856-927` (`route`를 `control_report`에 기록하고 LLM 스트림 호출은 그대로 진행) | `packages/core/tests/test_router.py:41-53`, `apps/api/tests/test_ask_router.py:305-324` (`test_lookup_decision_is_recorded_but_the_llm_still_runs`) |
| **근거가 없는 질문** | `pass` | `packages/core/src/nexuswiki_core/router.py:64-65` (`AskRoute.NO_EVIDENCE` 반환), `apps/api/src/api/services/ask.py:745, 752-782` (`if not result.evidence:` 분기에서 LLM 호출 없이 `no-evidence` 상태로 턴 종결) | `packages/core/tests/test_router.py:24-25`, `apps/api/tests/test_ask_router.py:168-194` (`test_no_evidence_short_circuits_before_any_llm_call`), `apps/api/tests/test_ask_router.py:327-336` |
| **내용이 같은 원문의 재컴파일** | `pass` | `packages/core/src/nexuswiki_core/router.py:86-99` (`decide_compile_route`에서 `has_existing_pages` 및 `fingerprint == previous_fingerprint`일 때 `CompileRoute.SKIP_UNCHANGED` 반환), `apps/worker/src/worker/handlers/compile.py:159-181, 256-288` (`_decide_route`에서 `latest_compile_fingerprint`와 `list_wiki_pages_for_source` 확인 후 `SKIP_UNCHANGED`이면 LLM 호출 없이 `link_sync`로 체이닝) | `packages/core/tests/test_router.py:82-109` (`test_compile_route`), `apps/worker/tests/test_handlers.py:851-866` (`test_unchanged_input_with_existing_pages_skips_llm_and_chains_to_link_sync`), `apps/worker/tests/test_controlled_ai_evidence.py:212-293` (`compile_unchanged_skip`) |
| **지문이 같아도 기존 위키 페이지가 없을 때** | `pass` | `packages/core/src/nexuswiki_core/router.py:94-102` (`has_existing_pages=False`일 때 `SKIP_UNCHANGED` 대신 `TRUNCATED` 또는 `STANDARD` 반환), `apps/worker/src/worker/handlers/compile.py:186-204, 276-288` (`list_wiki_pages_for_source`가 빈 목록이면 `has_existing_pages = False`로 LLM 컴파일 실행) | `packages/core/tests/test_router.py:87-88`, `apps/worker/tests/test_handlers.py:870-877` (`test_unchanged_input_without_existing_pages_still_runs_the_llm`) |

---

## 4. `ai-control-room` (`openspec/changes/archive/2026-11-03-ai-context-budget/specs/ai-control-room/spec.md`)

### Requirement: Control Room 추적 탭

| Scenario | 판정 | 코드 경로 (WHEN / THEN) | 검증 테스트 |
| --- | --- | --- | --- |
| **완료된 trace 상세** | `pass` | `apps/api/src/api/routers/control.py:241-303, 345-427` (`get_trace`에서 단계·호출·토큰·유효 비용 합계 반환, 정산 없는 호출은 원 `cost_micros` 사용), `apps/dashboard/components/ControlRoom.tsx:609-765` (`TraceDetailView` 렌더링) | `apps/api/tests/test_control_router.py:140-171` (`test_author_sees_own_ask_trace_with_totals_matching_usage`), `apps/dashboard/tests/ControlRoom.test.tsx:162-235` |
| **진행 중인 수집 trace** | `pass` | `apps/api/src/api/routers/control.py:203-238` (`_stages`에서 `completed`·`active`·`pending` 단계 생성), `apps/dashboard/components/ControlRoom.tsx:701-715` (`STATE_LABELS`로 `완료`·`진행 중`·`대기` 표시) | `apps/api/tests/test_control_router.py:329-365` (`test_running_ingest_reports_completed_active_and_pending_stages`), `apps/dashboard/tests/ControlRoom.test.tsx:254-288` |
| **데이터가 없는 워크스페이스** | `pass` | `apps/dashboard/components/ControlRoom.tsx:372-377` (`list.items.length === 0`일 때 빈 상태 안내 렌더링) | `apps/dashboard/tests/ControlRoom.test.tsx:151-160` (`빈 워크스페이스에서 첫 trace가 생기는 방법을 안내한다`) |
| **관측액과 정산액이 다르다** | `pass` | `apps/api/src/api/routers/control.py:254-255, 282-302, 402-410` (`ask_cost_trace_calls`와 `ask_cost_snapshot`으로 원 관측액 `observed_cost_micros`와 정산 반영액 `cost_micros` 구분 및 단일 호출 유지), `apps/dashboard/components/ControlRoom.tsx:729-731, 750-756` | `apps/api/tests/test_ask_cost_db.py:282-311`, `apps/dashboard/tests/ControlRoom.test.tsx:124-150` |

### Requirement: Control Room 예산 탭

| Scenario | 판정 | 코드 경로 (WHEN / THEN) | 검증 테스트 |
| --- | --- | --- | --- |
| **editor가 예산 탭을 연다** | `pass` | `supabase/migrations/0028_control_budget_tab.sql:15-258` (`public.control_budget_snapshot`에서 `v_can_view_ws = true`일 때 월간 예산·절감 집계·`by_call_path` 반환, 식별자/본문 미포함), `apps/api/src/api/routers/control.py:487-540` (`GET /workspaces/{workspace_id}/control/budget`), `apps/dashboard/components/ControlRoom.tsx:316-325, 341-349, 477-607` (`BudgetPanel`) | `supabase/tests/0028_control_budget_tab.sql:135-156`, `apps/api/tests/test_control_router.py:711-773` (`test_control_budget_separates_editor_and_viewer_scopes_and_denies_outsider`), `apps/api/tests/test_tenant_isolation_full_path.py:615-630`, `apps/dashboard/tests/ControlRoom.test.tsx:304-400` |
| **viewer가 예산 탭을 연다** | `pass` | `supabase/migrations/0028_control_budget_tab.sql:55, 81-93, 95-127, 233-255` (`v_can_view_ws = false`일 때 본인 Ask 절감 카운트만 집계하고 컴파일 절감 카운트는 `0`, `by_call_path`는 `'[]'::jsonb` 반환), `apps/api/src/api/routers/control.py:514, 532-539`, `apps/dashboard/components/ControlRoom.tsx:542-604` (컴파일 절감·호출 경로 표 숨김 및 안내 문구 표시) | `supabase/tests/0028_control_budget_tab.sql:116-133`, `apps/api/tests/test_control_router.py:758-780`, `apps/api/tests/test_tenant_isolation_full_path.py:631-637`, `apps/dashboard/tests/ControlRoom.test.tsx:402-450` |
| **비멤버가 예산 스냅샷을 요청한다** | `pass` | `supabase/migrations/0028_control_budget_tab.sql:50-53` (`has_workspace_role(p_workspace_id, 'viewer')` 미충족 시 `42501` 예외 발생), `apps/api/src/api/routers/control.py:496-501` (`WorkspaceForbidden` → HTTP 403 변환) | `supabase/tests/0028_control_budget_tab.sql:88-114`, `apps/api/tests/test_control_router.py:760-763`, `apps/api/tests/test_tenant_isolation_full_path.py:639-646` |

---

## 5. `ai-controls-showcase` (`openspec/changes/archive/2026-11-03-ai-context-budget/specs/ai-controls-showcase/spec.md`)

### Requirement: 재현 가능한 통제 전후 증거

| Scenario | 판정 | 코드 경로 (WHEN / THEN) | 검증 테스트 |
| --- | --- | --- | --- |
| **충돌 판정 비용 누락의 전후 비교** | `pass` | `apps/worker/tests/test_controlled_ai_evidence.py:104-141, 640-647`, `apps/dashboard/content/controlled-ai/step1.json:6-45`, `apps/dashboard/components/ControlledAiShowcase.tsx:91-170` | `apps/worker/tests/test_controlled_ai_evidence.py:822-849`, `apps/dashboard/tests/ControlledAiShowcase.test.tsx:38-51` |
| **Step 2 예산 및 단락 시나리오의 전후 비교** | `pass` | `apps/worker/tests/test_controlled_ai_evidence.py:212-366, 514-628, 678-721` (`compile_unchanged_skip`, `ask_context_budget_quota`, `structured_output_max_tokens`), `apps/dashboard/content/controlled-ai/step1.json:152-264`, `apps/dashboard/components/ControlledAiShowcase.tsx:75-77, 91-170` | `apps/worker/tests/test_controlled_ai_evidence.py:822-863`, `apps/dashboard/tests/ControlledAiShowcase.test.tsx:53-97` |
| **증거 파일의 내용 검사** | `pass` | `apps/dashboard/content/controlled-ai/step1.json:1-279` (`synthetic: true`, 합성 입력·관측값만 수록) | `apps/worker/tests/test_controlled_ai_evidence.py:873-906` (`test_evidence_contains_no_identifier_or_credential_shapes`, `test_forbidden_patterns_actually_match_their_shape`) |
| **아직 구현되지 않은 단계** | `pass` | `apps/worker/tests/test_controlled_ai_evidence.py:724-727` (`UPCOMING_STEPS`에 Step 3·4 정의), `apps/dashboard/content/controlled-ai/step1.json:266-277`, `apps/dashboard/components/ControlledAiShowcase.tsx:172-184` (`준비 중` 표시) | `apps/worker/tests/test_controlled_ai_evidence.py:866-870` (`test_upcoming_steps_carry_no_example_numbers`), `apps/dashboard/tests/ControlledAiShowcase.test.tsx:99-112` |
