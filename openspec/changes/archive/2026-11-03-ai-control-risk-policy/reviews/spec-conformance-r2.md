# Spec Conformance 리뷰 — ai-control-risk-policy r2

- 판정: needs_fix
- 대상: `git diff origin/main...HEAD` (`fb34a5e`), r1 지적 반영 포함
- 일시: 2026-11-03T08:50:00+09:00
- 기준: 현재 change의 delta spec 전체 Requirement와 Scenario. 로컬 `main`이 오래되어 최신 `origin/main`을 기준으로 삼았다.

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 공통 LLM 정책 / 사용자 템플릿에 인용 규칙이 없다 | 충족 | `apps/worker/src/worker/llm.py:203`, `apps/worker/src/worker/llm_gateway.py:94`, `:206` · `apps/worker/tests/test_risk_policy.py:121`, `:141` |
| 공통 LLM 정책 / 원문이 지시를 담고 있다 | 충족 | `packages/core/src/nexuswiki_core/llm_policy.py:28`, `apps/worker/src/worker/llm.py:383` · `apps/worker/tests/test_risk_policy.py:80` |
| 데이터 수집 거부 / 구조화 출력 지원이 없는 경로 | 충족 | `apps/worker/src/worker/llm.py:386` · `apps/worker/tests/test_risk_policy.py:100` |
| 데이터 수집 거부 / 스트리밍 답변 | 충족 | `apps/worker/src/worker/llm.py:206` · `apps/worker/tests/test_risk_policy.py:121` |
| 쓰기 분류와 개정 이력 / 새 페이지 | 충족 | `packages/core/src/nexuswiki_core/wiki_write_policy.py:45`, `apps/worker/src/worker/handlers/compile.py:424` · 분류 `apps/worker/tests/test_risk_policy.py:208`, 저장 `:361` |
| 쓰기 분류와 개정 이력 / 다른 원문이 만든 페이지 갱신 | 충족 | `packages/core/src/nexuswiki_core/wiki_write_policy.py:58`, `apps/worker/src/worker/handlers/compile.py:460` · `apps/worker/tests/test_risk_policy.py:489` |
| 쓰기 분류와 개정 이력 / 재실행 | 충족 | `supabase/migrations/0033_wiki_write_control.sql:30`, `apps/worker/src/worker/db/service.py:467` · 실제 DB 중복 삽입·멤버 읽기 `apps/api/tests/test_wiki_proposals.py:286` |
| 승인 보류 / 검증된 페이지 재컴파일 | 충족 | `apps/worker/src/worker/handlers/compile.py:440` · `apps/worker/tests/test_risk_policy.py:312` |
| 승인 보류 / 두 번 재컴파일 | 충족 | `supabase/migrations/0033_wiki_write_control.sql:82`, `:130` · `apps/api/tests/test_wiki_proposals.py:172` |
| 승인 보류 / editor가 승인한다 | 충족 | `apps/worker/src/worker/handlers/wiki_proposal_apply.py:74`, `:105`, `:118`, `:121`, `apps/worker/src/worker/handlers/embed.py:73` · `apps/api/tests/test_wiki_proposals.py:217`, `apps/worker/tests/test_risk_policy.py:401`, `:432`, `:556` |
| 승인 보류 / viewer나 비멤버가 승인을 시도한다 | 충족 | `supabase/migrations/0033_wiki_write_control.sql:156` · `apps/api/tests/test_wiki_proposals.py:100` |
| 승인 보류 / 거부한다 | 충족 | `supabase/migrations/0033_wiki_write_control.sql:176` · `apps/api/tests/test_wiki_proposals.py:197` |
| 분쟁 근거 표시 / 분쟁 페이지가 근거에 있다 | 충족 | `apps/api/src/api/services/ask.py:463`, `:1068`, `apps/dashboard/components/AskConversation.tsx:630` · `apps/api/tests/test_ask_router.py:1178`, `apps/dashboard/tests/AskConversation.test.tsx:282` |
| 분쟁 근거 표시 / 분쟁 페이지가 없다 | 충족 | `apps/api/src/api/services/ask.py:463`, `:1069`, `apps/dashboard/components/AskConversation.tsx:630` · API의 표시·별칭 없음 `apps/api/tests/test_ask_router.py:1202`, UI는 별칭이 있는 경우에만 경고하는 분기 확인 |
| 리스크 탭 / editor가 대기 제안을 처리한다 | 충족 | `apps/dashboard/components/ControlRoom.tsx:318` · 승인 후 재조회로 목록 제거 `apps/dashboard/tests/ControlRoom.test.tsx:586` |
| 리스크 탭 / viewer가 리스크 탭을 연다 | 충족 | `apps/api/src/api/routers/control.py:624`, `apps/dashboard/components/ControlRoom.tsx:651` · `apps/api/tests/test_wiki_proposals.py:128`, `apps/dashboard/tests/ControlRoom.test.tsx:675` |
| 리스크 탭 / 비멤버의 요청 | 충족 | `supabase/migrations/0034_control_risk_tab.sql:38` · `apps/api/tests/test_wiki_proposals.py:146` |
| 통제 전후 증거 / 충돌 판정 비용 누락의 전후 비교 | 충족 | `apps/dashboard/content/controlled-ai/step1.json:11`, `apps/dashboard/components/ControlledAiShowcase.tsx:149` · `apps/dashboard/tests/ControlledAiShowcase.test.tsx:38` |
| 통제 전후 증거 / Step 2 예산 및 단락 시나리오의 전후 비교 | 충족 | 증거 정의 `apps/worker/tests/test_controlled_ai_evidence.py:1025`의 시나리오 매핑 · 생성값 대조 `:1114`, 표시 `apps/dashboard/tests/ControlledAiShowcase.test.tsx:53`, `:75` |
| 통제 전후 증거 / Step 3 출력 계약 시나리오의 전후 비교 | 충족 | 생성값 대조 `apps/worker/tests/test_controlled_ai_evidence.py:1114`, 양쪽 커밋 `:1131` · 전체 항목 표시 `apps/dashboard/tests/ControlledAiShowcase.test.tsx:53` |
| 통제 전후 증거 / Step 4 정책 시나리오의 전후 비교 | 충족 | 세 시나리오 정의 `apps/worker/tests/test_controlled_ai_evidence.py:988`, `:999`, `:1007`, 실제 코드 대조 `:1114` · `apps/dashboard/tests/ControlledAiShowcase.test.tsx:53` |
| 통제 전후 증거 / 증거 파일의 내용 검사 | 충족 | `apps/worker/tests/test_controlled_ai_evidence.py:1175`, 금지 패턴 자체 검사 `:1195` |
| 통제 전후 증거 / 아직 구현되지 않은 단계 | 충족 | `apps/dashboard/components/ControlledAiShowcase.tsx:173`의 `evidence.upcoming.length > 0` 분기 · `apps/worker/tests/test_controlled_ai_evidence.py:1157`, `apps/dashboard/tests/ControlledAiShowcase.test.tsx:99` |

## Requirement 본문 및 r1 조치 확인

- r1의 메타데이터 승인 우회는 `metadata_changed` 비교와 `high` 제안 저장으로 막혔다(`compile.py:433`, 테스트 `test_risk_policy.py:473`). 다만 그 수정으로 아래의 본문 동일 개정 이력 위반이 생겼다.
- `off` 복구 모드와 위험 등급별 **개정** 건수는 현재 delta spec에 명시되어 있어, 현재 계약을 기준으로 r1의 두 항목은 해소됐다. 이 리뷰는 해당 스펙 변경의 사용자 승인 이력을 새로 판정하지 않는다.
- 현재 정책 버전은 API의 `LLM_POLICY_VERSION`으로 제공하고(`control.py:663`), 사용량의 과거 버전과 분리한다. 리스크 탭은 승인 후 반영 중인 건수도 표시한다(`ControlRoom.tsx:646`).
- 개정 테이블은 멤버 SELECT와 워커 INSERT만 허용한다(`0033_wiki_write_control.sql:39`). 실제 DB 테스트가 멤버 1건·비멤버 0건을 확인한다(`test_wiki_proposals.py:286`).
- `applied` 재실행은 본문을 다시 쓰지 않고 체인을 복구하며(`wiki_proposal_apply.py:57`), 바뀐 청크는 같은 번호여도 다시 임베딩한다(`embed.py:73`). 대응 회귀 테스트는 `test_risk_policy.py:432`, `:556`이다.
- `AI_CONTROL_RISK_MODE` 기본값은 `shadow`이고 4c 구현은 범위에 추가되지 않았다.

## 조치가 필요한 항목

1. **본문이 같은 메타데이터 변경도 개정을 남긴다.** `wiki_write_policy.py:51`의 보호 페이지 메타데이터 변경은 `changed=True`다. `compile.py:439`는 이를 개정 저장 조건으로도 사용하므로 `shadow`에서 본문은 같고 분류만 바뀌어도 `:460`에서 개정 1건을 남긴다. `enforce`에서 만들어진 메타데이터 전용 제안을 승인해도 `wiki_proposal_apply.py:75`가 본문 비교 없이 개정을 남긴다. 근거 Requirement: "본문이 같으면 개정을 남기지 않는다." 기존 테스트 더블로 두 경로를 단발 실행해 각각 `revisions=1`, `previous_content == upsert.content`임을 확인했다. 제안: 승인 보류 여부에 쓰는 변경 판정과 개정 삽입에 쓰는 **본문 변경** 판정을 나누고, 컴파일·승인 적용 양쪽에서 본문이 같은 경우 개정 삽입을 생략한다. 메타데이터 전용 `shadow`와 승인 적용의 개정 0건 회귀 테스트를 추가한다.

## 검증과 한계

- 부모가 이번 세션에서 새로 실행한 결과: Python 전체 1,074 passed / 1 failed, Vitest 79 files / 473 passed(워커 2개), TypeScript·ESLint·Ruff·OpenSpec strict 통과.
- Python의 실패 1건은 변경 범위 밖 기존 Storage RLS 거부 응답의 오류 매핑이다. 이 change의 스펙 판정과 분리했으며, 전체 검증 통과로 보고하지 않는다.
- 리뷰어는 DB·공유 큐 테스트를 추가 실행하지 않았다. 부모와 조율하여 DB 없는 기존 테스트 더블로 위 지적의 두 경로만 직접 실행했다.
- 쇼케이스의 `measure → write after` 갱신은 사용자가 지정한 리뷰 통과 후 단계로 남아 있다. 현재 생성값 일치 테스트 결과와 생성 코드·표시 경로를 검토했다.

## 판정 근거

모든 명시 Scenario에 구현과 검증 근거가 있지만, Requirement 본문의 본문 동일 시 개정 생략 규칙이 두 쓰기 경로에서 충족되지 않는다. 승인 보류를 유지하면서 본문 변경 여부로 개정 삽입만 제한하면 해결되므로 스펙 변경이 필요한 `blocked`가 아니라 `needs_fix`다. 지적 1건을 수정하고 마지막 허용 라운드인 r3에서 재검토한다.
