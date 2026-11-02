# Spec Conformance 리뷰 — ai-control-risk-policy r1

- 판정: needs_fix
- 대상: `git diff feat/ai-control-output-contract..HEAD` (`993c9d9`)
- 일시: 2026-11-02T23:09:06Z

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 공통 LLM 정책 / 사용자 템플릿에 인용 규칙이 없다 | 충족 | `apps/worker/src/worker/llm.py:203` · `apps/worker/src/worker/llm_gateway.py:206` · 테스트 `apps/worker/tests/test_risk_policy.py:120`, `:140` |
| 공통 LLM 정책 / 원문이 지시를 담고 있다 | 충족 | `packages/core/src/nexuswiki_core/llm_policy.py:28-34` · `llm.py:203`, `:383` · 테스트 `test_risk_policy.py:79`, `:120` |
| 데이터 수집 거부 / 구조화 출력 지원이 없는 경로 | 충족 | `llm.py:386` · 테스트 `test_risk_policy.py:99` |
| 데이터 수집 거부 / 스트리밍 답변 | 충족 | `llm.py:206` · 테스트 `test_risk_policy.py:120` |
| 쓰기 분류와 개정 이력 / 새 페이지 | 충족 | `packages/core/src/nexuswiki_core/wiki_write_policy.py:37` · 테스트 `test_risk_policy.py:162`, `:352` |
| 쓰기 분류와 개정 이력 / 다른 원문이 만든 페이지 갱신 | 충족, 테스트 부족 | `wiki_write_policy.py:60` · `apps/worker/src/worker/handlers/compile.py:454-465` · 등급만 `test_risk_policy.py:182`에서 검증. `medium`의 개정 기록을 확인하는 테스트 없음 |
| 쓰기 분류와 개정 이력 / 재실행 | 충족, 테스트 없음 | 키 `supabase/migrations/0033_wiki_write_control.sql`의 `wiki_page_revisions_job_key` · `apps/worker/src/worker/db/service.py`의 `insert_wiki_page_revision`. 실제 DB로 같은 호출을 두 번 보내 1건을 직접 확인함. 저장소 테스트는 이 경로를 두 번 타지 않음(`apps/api/tests/test_wiki_proposals.py:245`의 두 번째 실행은 상태 검사에서 끝남) |
| 승인 보류 / 검증된 페이지 재컴파일 | 충족 | `compile.py:434-452` · 테스트 `test_risk_policy.py:311` |
| 승인 보류 / 두 번 재컴파일 | 충족 | `0033`의 `wiki_write_proposals_pending_key`, `upsert_wiki_write_proposal` · 테스트 `test_wiki_proposals.py:172` |
| 승인 보류 / editor가 승인한다 | 충족 | `apps/worker/src/worker/handlers/wiki_proposal_apply.py:67`, `:98`, `:110` · 테스트 `test_wiki_proposals.py:217`, `test_risk_policy.py:392` |
| 승인 보류 / viewer나 비멤버가 승인을 시도한다 | 충족 | `0033`의 `decide_wiki_write_proposal` 권한 검사 · 테스트 `test_wiki_proposals.py:100` |
| 승인 보류 / 거부한다 | 충족 | `apps/api/src/api/routers/wiki.py:465` · 테스트 `test_wiki_proposals.py:197` |
| 분쟁 근거 표시 / 분쟁 페이지가 근거에 있다 | 충족 | `apps/api/src/api/services/ask.py:463`, `:1068-1070` · `apps/dashboard/components/AskConversation.tsx:136`, `:429`, `:630` · 테스트 `apps/api/tests/test_ask_router.py:1178`, `apps/dashboard/tests/AskConversation.test.tsx:263` |
| 분쟁 근거 표시 / 분쟁 페이지가 없다 | 충족 | `ask.py:463`, `:1069` · `AskConversation.tsx:630` · 테스트 `test_ask_router.py:1202`. 화면에 경고가 없음을 직접 확인하는 테스트는 없음 |
| 리스크 탭 / editor가 대기 제안을 처리한다 | 충족, THEN 미검증 | `apps/dashboard/components/ControlRoom.tsx:312-326` · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:585`는 POST 호출까지만 보고, 제안이 사라지거나 집계가 바뀌는지 확인하지 않음 |
| 리스크 탭 / viewer가 리스크 탭을 연다 | 충족 | `apps/api/src/api/routers/control.py:605` · `ControlRoom.tsx:643` · 테스트 `test_wiki_proposals.py:128`, `ControlRoom.test.tsx:646` |
| 리스크 탭 / 비멤버의 요청 | 충족 | `0034_control_risk_tab.sql`의 권한 검사 · 테스트 `test_wiki_proposals.py:146` |
| 통제 전후 증거 / Step 4 정책 시나리오의 전후 비교 | 충족 | `apps/dashboard/content/controlled-ai/step1.json` 마지막 세 항목(`79b68fe` → `3696506`) · 테스트 `apps/worker/tests/test_controlled_ai_evidence.py:1114`, `:1131`, `apps/dashboard/tests/ControlledAiShowcase.test.tsx:53` |
| 통제 전후 증거 / 증거 파일의 내용 검사 | 충족 | 테스트 `test_controlled_ai_evidence.py:1175` |
| 통제 전후 증거 / 아직 구현되지 않은 단계 | 충족 | `apps/dashboard/components/ControlledAiShowcase.tsx`의 `evidence.upcoming.length > 0` 분기 · 테스트 `ControlledAiShowcase.test.tsx:99` |
| 통제 전후 증거 / 충돌 비용, Step 2, Step 3 비교 | 충족 | 이번 change로 동작이 바뀌지 않음 · 테스트 `ControlledAiShowcase.test.tsx:53` |

Requirement 본문의 요구는 시나리오에 없어도 함께 대조했다. 아래 1~5번은 그 대조에서 나온 항목이다.

`design.md` D1~D6과 어긋나는 구현은 찾지 못했다. Non-Goals 항목은 지적하지 않았다.

## 조치가 필요한 항목

1. **검증·공개 페이지의 본문 외 변경이 보류되지 않는다** — 본문이 같으면 `changed=False`가 되어(`wiki_write_policy.py:48`) `enforce`에서도 `compile.py:471`의 업서트가 그대로 실행된다. 검증된 페이지의 `category`, `aliases`, `confidence`, `sources`와 슬러그가 같은 범위의 `title`이 승인도 이력도 없이 바뀐다. 테스트 `test_risk_policy.py:343`은 제목이 다른 검증 페이지에서 업서트 1회를 기대해 이 동작을 고정한다. 근거: "검증 완료 또는 공개 페이지의 변경은 `high`다", "`high` 쓰기는 페이지를 바꾸지 않고". 제안: `enforce`에서 검증·공개 페이지의 본문이 같으면 메타데이터를 쓰지 않거나, 메타데이터 차이도 제안으로 보류한다. 개정을 남기지 않는 규칙은 유지한다.

2. **`AI_CONTROL_RISK_MODE=off`가 개정 이력 의무를 끈다** — 스펙에는 `enforce`와 `shadow`만 있고 개정 이력은 무조건 MUST다. 그런데 `off`는 분류와 개정을 모두 건너뛰고(`compile.py:424`) 테스트 `test_risk_policy.py:334`가 이를 고정한다. 화면에도 "꺼짐" 라벨이 있다(`ControlRoom.tsx`의 `RISK_MODE_LABELS`). 근거: "기존 본문을 바꾸는 쓰기는 이전 본문을 개정 이력으로 MUST 남긴다". 제안: 워커·API 설정의 `Literal`, `.env.sample`, 라벨에서 `off`를 제거한다. `_upsert_page`의 기본값 `risk_mode="off"`도 함께 정리한다.

3. **리스크 탭의 등급별 건수에 새 페이지가 빠진다** — 집계가 `wiki_page_revisions`만 센다(`0034_control_risk_tab.sql`). 새 페이지는 개정이 없어 "낮음"에 잡히지 않고, 컴파일에서 분류도 호출되지 않는다(`compile.py:424`). 새 페이지 10개를 만들어도 화면은 "낮음 0건"이다. 근거: "위험 등급별 쓰기 건수". 제안: 기간 내 새 페이지 수를 `low`에 더하고 테스트를 추가한다.

4. **"적용 중인 정책 버전"이 아니라 과거 사용량의 버전을 보여준다** — `control_risk_snapshot`은 최근 `usage_events`의 값만 모은다. 사용량이 없는 워크스페이스의 owner로 실행하면 `policy_versions`가 `[]`이고(롤백 트랜잭션에서 확인) 화면에 정책 줄이 사라진다(`ControlRoom.tsx:629`). 버전을 올린 뒤에는 옛 버전도 함께 "적용된 LLM 정책"으로 표시된다. 실제 사용량에서 이 값을 확인하는 API 테스트도 없다. 근거: "적용 중인 정책 버전". 제안: API가 `LLM_POLICY_VERSION`을 현재 버전으로 돌려주고, 사용량 기록 값은 필요하면 별도 필드로 둔다.

5. **승인 잡 재실행에서 벡터 색인 갱신이 사라질 수 있다** — `applied` 전이(`wiki_proposal_apply.py:110`)와 체인 등록(`:113`)은 한 트랜잭션이 아니다. 그 사이에 워커가 죽으면 재실행은 상태 검사(`:53`)에서 다음 잡 없이 끝난다(`:55`). `link_sync` → `embed`가 돌지 않아 벡터 채널에 이전 본문이 남고, 실패 기록도 없다. 테스트 `test_risk_policy.py:412`는 `applied`에서 체인 없음을 기대한다. 근거: "승인하면 이전 본문을 개정으로 남기고 검색 색인까지 갱신한다". 제안: 재실행에서 상태가 `applied`이면 `link_sync` 체인을 등록하며 완료하고, `rejected`나 `pending`은 지금처럼 끝낸다. 테스트 기대값도 나눈다.

6. **완료로 표시된 시나리오의 테스트가 비어 있다** — 코드 변경 없이 테스트만 추가하면 된다.
   - "재실행": 실제 DB에서 같은 `job_id`로 개정 쓰기를 두 번 호출하거나 컴파일을 두 번 실행해 1건을 확인한다.
   - "editor가 대기 제안을 처리한다": 승인 뒤 재조회 응답을 바꿔 제안이 사라지고 집계가 줄어드는지 확인한다.
   - "다른 원문이 만든 페이지 갱신": `run_compile`에서 `medium` 등급과 이전 본문의 기록을 확인한다.
   - Requirement의 "개정 이력은 멤버만 읽고": 비멤버 0행, owner 1행을 롤백 트랜잭션으로 확인했으나 저장소 테스트가 없다.

참고로 `tasks.md`의 4번 검증 명령 `test_control_router.py`에는 리스크 탭 테스트가 없고, 2번 명령의 `test_tenant_isolation_full_path.py`에도 새 테이블 검증이 없다. 실제 테스트는 `apps/api/tests/test_wiki_proposals.py`에 있으므로 명령을 맞추는 편이 좋다. `supabase/tests/wiki_write_control.sql`은 직접 실행해 통과했지만 이를 돌리는 스크립트나 CI 연결은 찾지 못했다.

## 실행한 검증

- `uv run pytest apps/worker/tests/test_risk_policy.py apps/api/tests/test_wiki_proposals.py apps/worker/tests/test_controlled_ai_evidence.py`: 66 passed
- `uv run pytest apps/api/tests/test_ask_router.py -k disputed`: 2 passed
- `pnpm vitest run tests/ControlRoom.test.tsx tests/AskConversation.test.tsx tests/ControlledAiShowcase.test.tsx`: 통과
- `supabase/tests/wiki_write_control.sql`: 통과
- `openspec validate ai-control-risk-policy --strict`: 통과
- 로컬 DB: `0032` 적용 후 전역 Ask 템플릿 4개에 낡은 지시가 없음을 확인
- 로컬 DB 직접 확인: 개정 중복 삽입, 제안 업서트, `is_wiki_page_published`, 개정 RLS, `control_risk_snapshot`. 만든 행은 삭제하거나 롤백했다.

전체 스위트는 다시 돌리지 않았다. pytest 1,067건과 vitest 473건 통과는 호출자가 전달한 결과다. 동시 실행으로 인한 실패는 없었다.

## 판정 근거

스펙의 모든 Scenario에 구현 경로는 있다. 그러나 Requirement 본문의 요구 중 1, 3, 4, 5번이 충족되지 않았고, 2번은 무조건 MUST인 개정 이력을 스펙에 없는 모드로 끌 수 있게 한다. 6번은 완료로 표시된 task의 시나리오를 테스트가 확인하지 못하는 경우다. 전부 스펙을 바꾸지 않고 코드와 테스트로 해결할 수 있어 `blocked`가 아니라 `needs_fix`로 판정한다. 3번을 "개정 건수"로 좁히거나 2번의 `off`를 유지하려면 코드 대신 스펙을 `/opsx:update`로 고쳐야 하며, 그 선택은 사람의 결정이다.
