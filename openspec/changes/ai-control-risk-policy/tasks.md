# Tasks — ai-control-risk-policy

- Umbrella Issue: https://github.com/kanziman/NexusWiki/issues/196

## 1. 공통 정책 주입과 데이터 수집 거부 (https://github.com/kanziman/NexusWiki/issues/197)

- [x] 1.1 `packages/core`에 정책 문구와 버전을 두고 워커 요청 조립에서 주입하며 사용량에 `policy_version`을 기록한다.
- [x] 1.2 모든 채팅 요청에 `data_collection: deny`를 강제한다.
- [x] 1.3 `0032_prompt_policy_cleanup.sql`로 전역 Ask 템플릿의 낡은 인용 지시를 제거한다.

Given 인용 규칙을 뺀 템플릿, When LLM을 호출하면, Then 요청에 공통 정책과 데이터 수집 거부가 있고 정책 버전이 기록된다.
검증: `uv run pytest apps/worker/tests/test_risk_policy.py apps/worker/tests/test_llm.py`

## 2. 위험한 쓰기 분류, 개정 이력, 승인 보류 (https://github.com/kanziman/NexusWiki/issues/198)

- [x] 2.1 `0033_wiki_write_control.sql`에 개정·제안 테이블, RLS, 승인·거부 RPC를 추가하고 `supabase/tests/wiki_write_control.sql`로 검증한다.
- [x] 2.2 `classify_wiki_write`와 `compile.py` 쓰기 분기, `AI_CONTROL_RISK_MODE`를 구현한다.
- [x] 2.3 승인 적용 잡 `wiki_proposal_apply`와 승인·거부 API를 구현한다.

Given 검증된 페이지, When `enforce`에서 재컴파일하면, Then 본문은 그대로이고 대기 제안이 하나 생기며 editor 승인 뒤에만 반영된다.
검증: `uv run pytest apps/worker/tests/test_risk_policy.py apps/api/tests/test_wiki_proposals.py apps/api/tests/test_tenant_isolation_full_path.py`

## 3. 분쟁 근거 표시 (https://github.com/kanziman/NexusWiki/issues/199)

- [x] 3.1 Ask 컨텍스트와 `citations.disputed_aliases`, 답변 화면 경고를 구현한다.

Given 분쟁 페이지가 근거에 있을 때, When Ask가 끝나면, Then 프롬프트와 화면에 분쟁 표시가 있다.
검증: `uv run pytest apps/api/tests/test_ask_router.py` · `cd apps/dashboard && pnpm test AskConversation`

## 4. Control Room 리스크 탭 (https://github.com/kanziman/NexusWiki/issues/200)

- [x] 4.1 `0034_control_risk_tab.sql`과 `GET /workspaces/{workspace_id}/control/risk`를 구현한다.
- [x] 4.2 `ControlRoom.tsx`에 리스크 탭과 승인·거부 UI를 구현한다.

Given editor, viewer, 비멤버, When 리스크 탭을 열면, Then 대기 제안과 처리 버튼, 집계만, 403을 각각 받는다.
검증: `uv run pytest apps/api/tests/test_control_router.py` · `cd apps/dashboard && pnpm test ControlRoom`

## 5. 전후 증거와 문서 (https://github.com/kanziman/NexusWiki/issues/201)

- [x] 5.1 `verified_page_overwrite`, `chat_data_collection`, `template_policy_bypass` 시나리오를 추가하고 증거 파일과 쇼케이스를 갱신한다.
- [x] 5.2 합성 샘플 재생으로 정책 주입 뒤 이중 인용률과 공급자 동작을 확인하고 문서를 갱신한다.

검증: `uv run pytest apps/worker/tests/test_controlled_ai_evidence.py` · `cd apps/dashboard && pnpm test ControlledAiShowcase`
