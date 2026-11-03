# Spec Conformance 리뷰 — ai-control-risk-policy r3

- 판정: pass
- 대상: `git diff origin/main...HEAD` (`fb34a5e`)와 r2 이후 Step 4 작업 트리 수정
- 일시: 2026-11-03T08:58:57+09:00
- 범위: 이 change의 전체 delta spec 및 r2 지적. 별도 Storage change는 해당 change의 r1 보고서에서 판정했다.

## r2 지적 재확인

본문 변경과 승인 보류 판정이 분리됐다. `apps/worker/src/worker/handlers/compile.py:439`의 `decision.changed`는 보호 페이지의 메타데이터 변경을 계속 보류한다. 개정 삽입은 `:459`에서 기존·신규 본문이 다를 때만 실행한다. 승인 적용도 `apps/worker/src/worker/handlers/wiki_proposal_apply.py:75`에서 같은 본문 비교를 수행한다. 따라서 메타데이터만 바뀐 `shadow` 쓰기와 승인 적용은 개정 없이 진행하고, 본문이 바뀐 쓰기는 이전 본문을 먼저 기록한다.

대응 회귀 테스트 `apps/worker/tests/test_risk_policy.py:489`, `:499`는 개정 0건과 실제 메타데이터 반영을 확인한다. 승인 적용 테스트는 `applied` 전이·어휘 색인·후속 체인도 유지되는지 검사한다. 보호 페이지 메타데이터 변경의 `enforce` 보류 테스트 `:473`과 본문 변경 개정 테스트 `:324`, `:401`, `:514`도 유지돼 조용한 범위 축소를 찾지 못했다.

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 공통 LLM 정책 / 사용자 템플릿에 인용 규칙이 없다 | 충족 | 요청 앞 정책 `apps/worker/src/worker/llm.py:203`, 사용량 버전 `apps/worker/src/worker/llm_gateway.py:94`, `:206` · `apps/worker/tests/test_risk_policy.py:121`, `:141` |
| 공통 LLM 정책 / 원문이 지시를 담고 있다 | 충족 | 자료 경계 `packages/core/src/nexuswiki_core/llm_policy.py:28`, 주입 `apps/worker/src/worker/llm.py:383` · `apps/worker/tests/test_risk_policy.py:80` |
| 데이터 수집 거부 / 구조화 출력 지원이 없는 경로 | 충족 | `apps/worker/src/worker/llm.py:386` · 재요청 검사 `apps/worker/tests/test_risk_policy.py:100` |
| 데이터 수집 거부 / 스트리밍 답변 | 충족 | `apps/worker/src/worker/llm.py:206` · `apps/worker/tests/test_risk_policy.py:121` |
| 쓰기 분류와 개정 이력 / 새 페이지 | 충족 | `packages/core/src/nexuswiki_core/wiki_write_policy.py:45`, `apps/worker/src/worker/handlers/compile.py:424` · 분류 `apps/worker/tests/test_risk_policy.py:208`, 저장 `:361` |
| 쓰기 분류와 개정 이력 / 다른 원문이 만든 페이지 갱신 | 충족 | `packages/core/src/nexuswiki_core/wiki_write_policy.py:58`, `apps/worker/src/worker/handlers/compile.py:459` · `apps/worker/tests/test_risk_policy.py:514` |
| 쓰기 분류와 개정 이력 / 재실행 | 충족 | 고유 키 `supabase/migrations/0033_wiki_write_control.sql:30`, 중복 무시 `apps/worker/src/worker/db/service.py:467` · 실제 DB 중복 삽입·멤버 읽기 `apps/api/tests/test_wiki_proposals.py:286` |
| 승인 보류 / 검증된 페이지 재컴파일 | 충족 | `apps/worker/src/worker/handlers/compile.py:440` · `apps/worker/tests/test_risk_policy.py:312` |
| 승인 보류 / 두 번 재컴파일 | 충족 | 대기 제안 키·업서트 `supabase/migrations/0033_wiki_write_control.sql:82`, `:130` · `apps/api/tests/test_wiki_proposals.py:172` |
| 승인 보류 / editor가 승인한다 | 충족 | 적용·색인 경로 `apps/worker/src/worker/handlers/wiki_proposal_apply.py:74`, `:106`, `:119`, 체인 뒤 임베딩 `apps/worker/src/worker/handlers/embed.py:73` · `apps/api/tests/test_wiki_proposals.py:217`, `apps/worker/tests/test_risk_policy.py:401`, `:581` |
| 승인 보류 / viewer나 비멤버가 승인을 시도한다 | 충족 | `supabase/migrations/0033_wiki_write_control.sql:156` · `apps/api/tests/test_wiki_proposals.py:100` |
| 승인 보류 / 거부한다 | 충족 | 상태 변경 `supabase/migrations/0033_wiki_write_control.sql:163` · `apps/api/tests/test_wiki_proposals.py:197` |
| 분쟁 근거 표시 / 분쟁 페이지가 근거에 있다 | 충족 | `apps/api/src/api/services/ask.py:463`, `:1068`, 경고 `apps/dashboard/components/AskConversation.tsx:630` · `apps/api/tests/test_ask_router.py:1178`, `apps/dashboard/tests/AskConversation.test.tsx:282` |
| 분쟁 근거 표시 / 분쟁 페이지가 없다 | 충족 | 분쟁일 때만 표시 `apps/api/src/api/services/ask.py:463`, `:1069`, `apps/dashboard/components/AskConversation.tsx:630` · API의 표시·별칭 없음 `apps/api/tests/test_ask_router.py:1202` |
| 리스크 탭 / editor가 대기 제안을 처리한다 | 충족 | 처리 후 재조회 `apps/dashboard/components/ControlRoom.tsx:318` · 목록 제거 검사 `apps/dashboard/tests/ControlRoom.test.tsx:586` |
| 리스크 탭 / viewer가 리스크 탭을 연다 | 충족 | 본문 조회 분기 `apps/api/src/api/routers/control.py:624`, UI 분기 `apps/dashboard/components/ControlRoom.tsx:651` · `apps/api/tests/test_wiki_proposals.py:128`, `apps/dashboard/tests/ControlRoom.test.tsx:675` |
| 리스크 탭 / 비멤버의 요청 | 충족 | 역할 검사 `supabase/migrations/0034_control_risk_tab.sql:37` · `apps/api/tests/test_wiki_proposals.py:146` |
| 통제 전후 증거 / 충돌 판정 비용 누락의 전후 비교 | 충족 | `apps/dashboard/content/controlled-ai/step1.json:11`, 표시 `apps/dashboard/components/ControlledAiShowcase.tsx:149` · `apps/dashboard/tests/ControlledAiShowcase.test.tsx:38` |
| 통제 전후 증거 / Step 2 예산 및 단락 시나리오의 전후 비교 | 충족 | 생성값 대조 `apps/worker/tests/test_controlled_ai_evidence.py:1114`, 시나리오·양쪽 커밋 표시 `apps/dashboard/components/ControlledAiShowcase.tsx:149`, `:155`, `:161` · `apps/dashboard/tests/ControlledAiShowcase.test.tsx:53`, `:75` |
| 통제 전후 증거 / Step 3 출력 계약 시나리오의 전후 비교 | 충족 | 생성값 대조 `apps/worker/tests/test_controlled_ai_evidence.py:1114`, 커밋 검사 `:1131` · 전체 항목 표시 `apps/dashboard/tests/ControlledAiShowcase.test.tsx:53` |
| 통제 전후 증거 / Step 4 정책 시나리오의 전후 비교 | 충족 | 세 시나리오 `apps/worker/tests/test_controlled_ai_evidence.py:988`, `:999`, `:1007`, 생성값 대조 `:1114` · `apps/dashboard/tests/ControlledAiShowcase.test.tsx:53` |
| 통제 전후 증거 / 증거 파일의 내용 검사 | 충족 | 식별자·자격 증명 검사 `apps/worker/tests/test_controlled_ai_evidence.py:1175`, 금지 패턴 자체 검사 `:1195` |
| 통제 전후 증거 / 아직 구현되지 않은 단계 | 충족 | 조건부 영역 `apps/dashboard/components/ControlledAiShowcase.tsx:173` · 예시 수치 부재 `apps/worker/tests/test_controlled_ai_evidence.py:1157`, 영역 없음 `apps/dashboard/tests/ControlledAiShowcase.test.tsx:99` |

## Requirement 본문 재확인

- 본문 동일 개정 생략은 위 두 경로와 회귀 테스트로 해소됐다. `enforce`의 메타데이터 보류는 유지된다.
- `off` 예외와 위험 등급별 **개정** 건수는 현재 delta spec의 명시 계약이며, 이를 넘어선 동작을 추가하지 않았다.
- 정책 버전은 과거 사용량과 분리해 현재 `LLM_POLICY_VERSION`을 반환한다(`apps/api/src/api/routers/control.py:663`).
- 개정은 멤버 읽기·워커 쓰기다(`supabase/migrations/0033_wiki_write_control.sql:41`). viewer는 제안 본문을 받지 않는다(`apps/api/tests/test_wiki_proposals.py:128`).
- 적용된 제안의 재실행은 본문을 다시 쓰지 않고 후속 체인을 복구한다(`apps/worker/src/worker/handlers/wiki_proposal_apply.py:57`, 테스트 `apps/worker/tests/test_risk_policy.py:432`). 변경된 위키 청크는 같은 번호여도 재임베딩한다(`apps/worker/src/worker/handlers/embed.py:73`, 테스트 `apps/worker/tests/test_risk_policy.py:581`).
- API·worker 쓰기 모드 동시 설정과 불일치 자동 탐지 부재를 `.env.sample:95`, `docs/reference/stack.md:52`에 안내한다. 기본값 `shadow`는 유지된다(`apps/worker/src/worker/settings.py:126`).
- 4c는 비목표로 유지되고 구현 범위에 추가되지 않았다.

## 조치가 필요한 항목

없음.

## 검증과 남은 워크플로우

- 부모가 수정 후 새로 실행한 결과: 전체 pytest **1,092 passed / 1 skipped**(438.22초), Vitest **473 passed**, TypeScript·ESLint·최신 Ruff·양 change strict validation 통과, `supabase/tests/wiki_write_control.sql` 로컬 통과.
- skip 1건은 측정 대상 코드가 미커밋인 동안의 증거 커밋 신선도 검사다. 사용자 순서에 따른 최종 `measure → write after`와 커밋 후 해당 검사 재실행이 남아 있다. 이 결과를 skip 없는 전체 통과로 표현하지 않는다.
- 리뷰어는 r2 이후 수정과 전체 계약의 구현·테스트 근거를 대조했고, 요청에 따라 DB·큐 테스트를 추가 실행하지 않았다.
- 최종 증거 갱신·스펙 동기화·strict validation·아카이브·커밋 및 PR 사전 승인은 부모의 후속 작업이다. 이 보고서는 해당 작업이나 운영 마이그레이션 적용 완료를 주장하지 않는다.

## 판정 근거

r2의 유일한 미충족 항목은 코드와 두 회귀 테스트로 해결됐다. 모든 Scenario 및 Requirement 본문에 대응하는 구현·검증 근거를 다시 확인했고 추가 미충족이나 범위 밖 사용자 동작을 찾지 못했다. 세 번째 라운드의 최종 스펙 준수 판정은 `pass`다.
