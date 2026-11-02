# Tasks — ai-control-output-contract

- Umbrella Issue: https://github.com/kanziman/NexusWiki/issues/188

## 1. 구조화 출력 계약: 펜스, 의미 검증, 호출 상한, 쌍 격리 (https://github.com/kanziman/NexusWiki/issues/189)

- [x] 1.1 `apps/worker/src/worker/llm.py`에 `parse_json_only`와 예외 없는 응답 분류를 추가하고 시도를 2회로 줄이며 재시도 재주입을 제한하고, 펜스 제거와 위반 코드를 사용량 메타데이터에 기록한다.
- [x] 1.2 `LlmSchemaError`를 `NON_RETRYABLE_ERRORS`에 넣고 `CompiledPage`에 공백·placeholder 검증을 추가한다.
- [x] 1.3 `conflict.py`에서 한 쌍의 스키마 소진을 격리한다.

Given 펜스 응답·placeholder 페이지·계속 깨지는 응답·한 쌍만 깨지는 충돌 판정, When 각 핸들러를 실행하면, Then 호출은 2회 이하이고 비용이 모두 기록되며 잘못된 페이지는 저장되지 않는다.
검증: `uv run pytest apps/worker/tests/test_llm.py apps/worker/tests/test_llm_gateway.py apps/worker/tests/test_handlers.py`

## 2. Ask 인용 계약, 수리, Fallback (https://github.com/kanziman/NexusWiki/issues/190)

- [x] 2.1 `supabase/migrations/0029_ask_fallback_status.sql`로 `fallback` 상태를 허용한다.
- [x] 2.2 `packages/core`에 인용 계약 판정 순수 함수를 두고 `services/ask.py`에 수리, Fallback, `AI_CONTROL_QUALITY_MODE`, 통제 보고서를 연결한다.
- [x] 2.3 대시보드 Ask 화면과 기록 복원에서 `fallback`을 표시한다.

Given 인용 없는 답변, When Ask가 끝나면, Then 수리되어 `resolved`이거나 발급 앵커만 쓴 `fallback`이고 호출은 2회 이하다.
검증: `uv run pytest apps/api/tests/test_ask_router.py apps/api/tests/test_ask_citations.py packages/core/tests/test_answer_contract.py` · `cd apps/dashboard && pnpm test AskConversation`

## 3. 컴파일 페이지 근거 청크 (https://github.com/kanziman/NexusWiki/issues/191)

- [x] 3.1 `0030_wiki_page_evidence.sql`에 테이블, RLS, 교체 RPC, 컴파일 템플릿 갱신을 추가하고 `supabase/tests/wiki_page_evidence.sql`로 검증한다.
- [x] 3.2 `compile.py`에서 청크에 앵커를 발급하고 `evidence`를 대조해 저장한다.

Given 발급 앵커와 지어낸 앵커가 섞인 페이지, When 컴파일을 두 번 실행하면, Then 발급 앵커만 한 벌 저장되고 비멤버는 0행을 받는다.
검증: `uv run pytest apps/worker/tests/test_handlers.py apps/api/tests/test_tenant_isolation_full_path.py` · `supabase test db`

## 4. Control Room 품질 탭 (https://github.com/kanziman/NexusWiki/issues/192)

- [x] 4.1 `0031_control_quality_tab.sql`에 `control_quality_snapshot`을 추가하고 `GET /workspaces/{workspace_id}/control/quality`를 연결한다.
- [x] 4.2 `ControlRoom.tsx`에서 품질 탭을 활성화한다.

Given editor, viewer, 비멤버, When 품질 탭을 요청하면, Then 전체 집계, 본인 Ask 집계, 403을 각각 받고 본문은 없다.
검증: `uv run pytest apps/api/tests/test_control_router.py apps/api/tests/test_tenant_isolation_full_path.py` · `cd apps/dashboard && pnpm test ControlRoom`

## 5. 전후 증거와 문서 (https://github.com/kanziman/NexusWiki/issues/193)

- [x] 5.1 `test_controlled_ai_evidence.py`에 `compile_fence_retry`, `compile_placeholder_page`, `ask_no_citation_terminal`을 추가하고 증거 파일과 쇼케이스를 갱신한다.
- [x] 5.2 합성 샘플 재생으로 위반율과 수리 결과를 측정해 기본 모드를 정하고, `docs/reference/stack.md`와 `docs/ops/`에 기록한다.

Given 기준 커밋과 현재 코드, When 시나리오와 샘플을 재생하면, Then 전후 값이 합성 증거로 기록되고 쇼케이스가 Step 4만 준비 중으로 표시한다.
검증: `uv run pytest apps/worker/tests/test_controlled_ai_evidence.py` · `cd apps/dashboard && pnpm test ControlledAiShowcase`
