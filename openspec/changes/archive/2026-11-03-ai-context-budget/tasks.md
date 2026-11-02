# Tasks — ai-context-budget

- Umbrella Issue: https://github.com/kanziman/NexusWiki/issues/183

## 1. Ask 컨텍스트 토큰 예산·이중 근거 쿼터 및 RRF 메타데이터 병합 (https://github.com/kanziman/NexusWiki/issues/184)

- [x] 1.1 `packages/core/src/nexuswiki_core/rrf.py`의 `fuse_ranked_hits`에서 다중 채널 병합 시 선행 채널 키 우선순위를 유지하며 후행 채널의 `metadata`(`slug`, `title`)를 병합하도록 수정하고 `packages/core/tests/test_rrf.py`에 회귀 테스트를 추가한다.
- [x] 1.2 `packages/core/src/nexuswiki_core/context_budget.py`에 `allocate_ask_context_budget` 및 `AskContextBudgetResult`를 구현하여 `max_context_tokens` 상한 내에서 위키 근거(`[[wiki:...]]`)와 원문 청크 근거(`[[src:...]]`)가 모두 존재할 때 각 최소 1개 블록을 보장하고 요약 메타데이터를 산출한다.
- [x] 1.3 `apps/api/src/api/settings.py`에 `ASK_MAX_CONTEXT_TOKENS: int = 6000`을 추가(`packages/core/tests/test_settings.py` 허용 목록 동기화)하고, `apps/api/src/api/services/ask.py`에서 `_fetch_evidence_content`가 `wiki_pages`의 `slug`·`title`을 보강한 뒤 `allocate_ask_context_budget` 결과를 `control_report["budget"]`에 기록하도록 연결하며 `apps/api/tests/test_ask_router.py` 및 `apps/api/tests/test_ask_citations.py`로 검증한다.

## 2. 구조화 출력 max_tokens·입력 상한 및 Compile SKIP_UNCHANGED 단락 실행 (https://github.com/kanziman/NexusWiki/issues/185)

- [x] 2.1 `apps/worker/src/worker/settings.py`에 `COMPILE_MAX_OUTPUT_TOKENS: int = 4096`, `COMPILE_MAX_EXISTING_SLUGS: int = 200`, `CONFLICT_MAX_INPUT_TOKENS: int = 4000`, `CONFLICT_MAX_OUTPUT_TOKENS: int = 512`를 추가하고 `worker.llm.complete_structured` 및 `LlmGateway.complete_structured`가 `max_tokens`를 OpenRouter 요청 본문과 `usage_events.metadata`에 전달·기록하도록 구현한다.
- [x] 2.2 `packages/core/src/nexuswiki_core/router.py`의 `decide_compile_route`에 `has_existing_pages: bool = True` 조건을 추가하고, `apps/worker/src/worker/handlers/compile.py`에서 `existing_slugs` 상한·`max_tokens` 적용 및 `SKIP_UNCHANGED`일 때 LLM 호출을 생략하고 `compile_route: "SKIP_UNCHANGED"`로 `link_sync`에 체이닝하도록 수정한다.
- [x] 2.3 `apps/worker/src/worker/handlers/conflict.py`에서 페이지 본문 쌍을 `CONFLICT_MAX_INPUT_TOKENS` 예산 내로 절단하고 `max_tokens=settings.CONFLICT_MAX_OUTPUT_TOKENS` 및 `truncated_input` 메타데이터를 기록하도록 구현하며 `packages/core/tests/test_router.py`, `apps/worker/tests/test_llm.py`, `apps/worker/tests/test_llm_gateway.py`, `apps/worker/tests/test_handlers.py`로 검증한다.

## 3. Control Room [예산] 탭 집계 RPC·API 및 대시보드 UI 활성화 (https://github.com/kanziman/NexusWiki/issues/186)

- [x] 3.1 `supabase/migrations/0028_control_budget_tab.sql`에 요청자 JWT 전용 `public.control_budget_snapshot(p_workspace_id uuid, p_since timestamptz)` 함수를 작성하고 로컬 DB에 적용한 뒤 `supabase/tests/0028_control_budget_tab.sql`로 `viewer`/`editor`/비소속 사용자 권한 분기를 검증한다.
- [x] 3.2 `apps/api/src/api/routers/control.py`에 `GET /workspaces/{workspace_id}/control/budget` 엔드포인트를 추가하여 월 예산 상한·원장 정산 상태·활성 토큰 예산 정책·절감 카운트·역할별 호출 경로 내역을 반환하고 `apps/api/tests/test_control_router.py` 및 `apps/api/tests/test_tenant_isolation_full_path.py`로 검증한다.
- [x] 3.3 `apps/dashboard/components/ControlRoom.tsx`에서 `budget` 탭을 활성화하여 예산 현황·정책·절감 카운트·호출 경로별 내역 UI를 렌더링하고(`quality`·`risk` 탭만 예정 상태 유지) `apps/dashboard/tests/ControlRoom.test.tsx`로 검증한다.

## 4. 공개 쇼케이스(/showcase/controlled-ai) Step 2 전/후 합성 증거 및 문서 갱신 (https://github.com/kanziman/NexusWiki/issues/187)

- [x] 4.1 `apps/worker/tests/test_controlled_ai_evidence.py`에 Step 2 전/후 합성 시나리오 3종(`compile_unchanged_skip`, `ask_context_budget_quota`, `structured_output_max_tokens`)을 추가하고 `79b68fe` 대비 현재 코드의 실측 결과로 `apps/dashboard/content/controlled-ai/step1.json` 및 `ControlledAiShowcase.tsx`를 갱신한다.
- [x] 4.2 `docs/reference/stack.md` 등 관련 레퍼런스 문서를 최신 상태로 동기화하고 `uv run pytest apps/worker/tests/test_controlled_ai_evidence.py` 및 `cd apps/dashboard && pnpm test ControlledAiShowcase.test.tsx`를 통과시킨다.
