# Spec Conformance 리뷰 — ai-control-output-contract r1

- 판정: needs_fix
- 대상: `git diff feat/ai-context-budget..HEAD` (`33ff943abc8901a78c368cf4ef16b9d0ca6d916d`, 스택된 브랜치라 main이 아니라 이 범위로 봤다. merge-base가 `feat/ai-context-budget` 끝과 같음을 확인했다)
- 일시: 2026-11-03T01:20:00+09:00

## 요약

Scenario 27개 중 충족 22개, 부분 충족 3개, 미충족 2개다. 핵심 경로(수리, Fallback, 펜스, 2회 상한, 근거 저장, 쌍 격리)는 구현과 테스트가 있다. 남은 지적은 경계 입력에서 계약이 뚫리는 곳과, 스펙 문구와 다른 응답·화면이다. 전부 스펙을 고치지 않고 해결할 수 있다.

## 시나리오 판정

### grounded-answering

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Ask 인용 계약과 수리 / 인용이 하나도 없는 답변을 수리한다 | 충족 | `apps/api/src/api/services/ask.py:982-1004`, `:1019-1029` · 테스트 `apps/api/tests/test_ask_router.py:1061` |
| Ask 인용 계약과 수리 / 근거 부족을 밝힌 답변 | 충족 (반대 방향의 과대 일치는 조치 항목 3) | `packages/core/src/nexuswiki_core/answer_contract.py:42-44`, `:57` · 테스트 `test_ask_router.py:1084`, `packages/core/tests/test_answer_contract.py:59` |
| Ask 인용 계약과 수리 / 정상 답변 | 충족 | `answer_contract.py:55-59` · 테스트 `test_ask_router.py:1046`, `test_answer_contract.py:69` |
| 결정론적 Ask Fallback / 수리도 실패한다 | 충족 | `ask.py:1005-1011`, `answer_contract.py:90-122` · 테스트 `test_ask_router.py:1095` (`repair_invalid`) |
| 결정론적 Ask Fallback / 수리 호출 자체가 실패한다 | 충족 | `ask.py:628-637` · 테스트 `test_ask_router.py:1095` (`repair_call_failed`, 502만). 전송 예외와 깨진 프레임 경로는 코드로만 확인했다 (`ask.py:455`, `:636`) |
| 결정론적 Ask Fallback / 근거 본문에 앵커 문법이 들어 있다 | 충족 | `answer_contract.py:84` · 테스트 `test_answer_contract.py:80` |
| 결정론적 Ask Fallback / 기록을 다시 연다 | 충족 | `apps/dashboard/components/AskConversation.tsx:122-133`, `:689-690`, `:700`, `supabase/migrations/0029_ask_fallback_status.sql:19-21`, `:44` · 테스트 `apps/dashboard/tests/AskThreadHistoryRestore.test.tsx:182` (안내 라벨만 단언하고 근거 목록 본문은 단언하지 않는다) |
| 품질 통제 모드 / shadow 모드의 위반 | 충족 | `ask.py:973-982`, `:1012-1018` · 테스트 `test_ask_router.py:1119` |
| 품질 통제 모드 / off 모드 | 충족 | `ask.py:972-973` · 테스트 `test_ask_router.py:1127` |

### wiki-compilation

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 코드 펜스와 의미 검증 / 펜스로 감싼 정상 JSON | 충족 | `apps/worker/src/worker/llm.py:70`, `:113-122`, `:514-530`, `apps/worker/src/worker/llm_gateway.py:94-95` · 테스트 `apps/worker/tests/test_output_contract.py:109`, `apps/worker/tests/test_controlled_ai_evidence.py:294` |
| 코드 펜스와 의미 검증 / placeholder 페이지 | 부분 충족 | 단독 값은 거부된다 (`apps/worker/src/worker/handlers/compile.py:59-69`, `:95`, 테스트 `test_output_contract.py:173`, `test_controlled_ai_evidence.py:302`). 앵커와 결합하면 통과해 공백·placeholder가 저장된다 (조치 항목 2) |
| 코드 펜스와 의미 검증 / 본문이 템플릿 문법을 설명한다 | 충족 | `compile.py:57-62` (전체 일치) · 테스트 `test_output_contract.py:185` |
| 호출 상한 / 어떤 입력에도 호출은 2회를 넘지 않는다 | 미충족 | 파싱 실패 경로만 2회로 끝난다 (`llm.py:64`, `apps/worker/src/worker/errors.py:173-180`, 테스트 `test_output_contract.py:123`, `:138`). `content: null`과 빈 `choices`는 큐가 재시도한다 (조치 항목 1) |
| 호출 상한 / 파싱할 수 없는 출력의 재시도 | 충족 | `llm.py:335-339`, `:533-541` · 테스트 `test_output_contract.py:143`, `:154` |
| 페이지 근거 청크 / 발급되지 않은 앵커 | 부분 충족 | 저장 대조와 로그 구현은 있다 (`compile.py:164-168`, `:271-285`, `:424-435`, 테스트 `test_output_contract.py:341`). 로그 단언 테스트가 없다 (조치 항목 6) |
| 페이지 근거 청크 / 재컴파일 | 충족 | `supabase/migrations/0030_wiki_page_evidence.sql:68-80` · 테스트 `supabase/tests/wiki_page_evidence.sql` (RPC 2회 호출, 직접 실행 통과). 핸들러를 두 번 도는 테스트는 없다 |
| 페이지 근거 청크 / 다른 워크스페이스 사용자의 조회 | 충족 | `0030_wiki_page_evidence.sql:43-48` · 테스트 `supabase/tests/wiki_page_evidence.sql:69-70` (시드 있음, 직접 실행 통과). `apps/api/tests/test_tenant_isolation_full_path.py:679`는 시드 행이 없어 이 Scenario의 증거가 되지 못한다 |
| 충돌 판정 쌍 격리 / 한 쌍만 스키마를 어긴다 | 충족 | `apps/worker/src/worker/handlers/conflict.py:122-136`, `:143-148` · 테스트 `test_output_contract.py:240` |

### ai-control-room

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 품질 탭 / editor가 품질 탭을 연다 | 충족 | `apps/api/src/api/routers/control.py:542-587`, `supabase/migrations/0031_control_quality_tab.sql:14-128`, `apps/dashboard/components/ControlRoom.tsx:549-614` · 테스트 `apps/api/tests/test_control_router.py:814`, `apps/dashboard/tests/ControlRoom.test.tsx:452` |
| 품질 탭 / viewer가 품질 탭을 연다 | 부분 충족 | 본인 Ask만 집계하고 실제 수집 수치는 노출하지 않는다 (`0031:74`, `:96`, `:108`). 응답에는 수집 필드가 0으로 남는다 (조치 항목 5) |
| 품질 탭 / 비멤버의 요청 | 충족 | `0031:47-50`, `control.py:555-556` · 테스트 `test_control_router.py:814`, `test_tenant_isolation_full_path.py:649` |
| 품질 탭 / 집계할 데이터가 없다 | 미충족 | 기간과 무관한 `pages_total`이 빈 상태를 막는다 (`ControlRoom.tsx:551-554`, `0031:101-110`). 조치 항목 4 |

### ai-controls-showcase

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 전후 증거 / 충돌 판정 비용 누락의 전후 비교 | 충족 | `apps/dashboard/components/ControlledAiShowcase.tsx:92`, `:148-163` · 테스트 `test_controlled_ai_evidence.py:979`, `apps/dashboard/tests/ControlledAiShowcase.test.tsx:56` |
| 전후 증거 / Step 2 예산 및 단락 시나리오의 전후 비교 | 충족 | 같은 렌더 경로, `apps/dashboard/content/controlled-ai/step1.json` · 테스트 `test_controlled_ai_evidence.py:979` |
| 전후 증거 / Step 3 출력 계약 시나리오의 전후 비교 | 충족 | `test_controlled_ai_evidence.py:294`, `:302`, `:621`, `:848-875`. 기준 커밋 `79b68fe`에서 다시 측정해 10개 시나리오의 `before` 값이 모두 일치함을 확인했다. `after` 커밋 `1f52a6e`는 이 브랜치 이력에 있다 |
| 전후 증거 / 증거 파일의 내용 검사 | 충족 | 테스트 `test_controlled_ai_evidence.py:1040` |
| 전후 증거 / 아직 구현되지 않은 단계 | 충족 | `test_controlled_ai_evidence.py:878-880`, `:1022` · 테스트 `ControlledAiShowcase.test.tsx:99-111` |

## 조치가 필요한 항목

1. **`content: null`과 빈 `choices`가 호출 상한을 넘긴다** — `_read_content`의 `ProviderError`(`llm.py:288-290`, `:314-315`)는 `NON_RETRYABLE_ERRORS`에 없어 큐가 `fail_job`으로 다시 돌린다 (`apps/worker/src/worker/queue.py:304-310`, `max_attempts` 기본 3). 실측: 첫 응답 `null`은 1회 호출 후 `ProviderError`, 첫 응답이 깨지고 둘째가 `null`이면 2회 호출 후 `ProviderError`로 `non_retryable=False`다. 따라서 공급자가 이런 응답을 계속 돌려주면 잡 하나가 최대 6회 호출된다. 기존 테스트 `apps/worker/tests/test_llm_gateway.py:270`은 기록만 보고 이 분류를 그대로 굳힌다. 근거 Scenario: "어떤 입력에도 호출은 2회를 넘지 않는다 ... 잡은 재시도 없이 안전하게 종결된다". 제안: 내용 없는 응답을 위반 시도로 세고(되먹임에 원문 없음) 소진 시 `LlmSchemaError`로 끝낸다. D1의 "기록 뒤에 다시 던진다"는 그대로 지켜진다. 충돌 판정의 쌍 격리도 함께 적용된다. 큐 재시도까지 포함한 호출 수를 단언하는 테스트를 추가한다.

2. **앵커가 붙은 공백·placeholder 페이지가 저장된다** — 검증은 앵커 제거 전(`compile.py:95`)이고 제거는 검증 후(`compile.py:394`)다. 실측: 본문 `[[src:s1]]`은 `''`로, `TODO [[src:s1]]`은 `'TODO '`로, `{{title}} [[src:s1]]`은 `'{{title}} '`로 저장된다. 이번 변경이 입력 청크에 앵커를 붙이면서 생긴 경로다. 근거: "컴파일 페이지의 제목이나 본문이 공백이거나 전체가 placeholder ... MUST 거부", Scenario "placeholder 페이지 ... 잘못된 페이지는 저장되지 않는다". 제안: `_reject_blank_or_placeholder`가 앵커를 지운 값으로 판정하게 해 `semantic_invalid` 재시도로 보낸다. 제목에도 같은 제거를 적용한다(제목은 현재 지우지 않는다). 테스트를 추가한다.

3. **근거 부족 표현이 부분 일치라 인용 없는 일반 답변이 `resolved`로 저장된다** — `_ABSTENTION`(`answer_contract.py:42-44`)은 문장 어디든 일치한다. 실측: "이 시스템은 원인을 알 수 없는 오류가 나면 3회 재시도합니다.", "파일을 찾을 수 없으면 관리자에게 문의합니다."가 인용 없이 위반 `()`로 통과한다. D5는 표현을 놓치는 방향만 다뤘고, 이 방향은 수리 비용이 아니라 인용 없는 답변의 저장으로 이어진다. 근거: "답변이 있는데 해소된 인용이 하나도 없으면 위반이다", design Goals "인용 없는 답변의 `resolved` 저장 차단". 제안: 자료·근거 부족을 밝히는 문맥으로 패턴을 좁히고(`자료로는 ... 알 수 없`, `자료에 없` 등) 위 두 문장을 음성 사례로 테스트에 넣는다.

4. **데이터가 없는데 품질 탭이 0을 표시한다** — `hasIngest`가 `evidence.pages_total > 0`을 포함하는데(`ControlRoom.tsx:551-553`) `pages` 집계에는 기간 조건이 없다(`0031:101-110`). 위키 페이지가 있는 워크스페이스에서 기간 안에 턴과 호출이 없으면 빈 상태 대신 "답변 턴 0건", "구조화 호출 0건" 지표가 그려진다. 코드로 확인했고 렌더링 실행은 하지 않았다. 기존 테스트 `ControlRoom.test.tsx:537`은 `pages_total: 0`만 본다. 근거 Scenario: "기간 안에 턴과 호출이 없다 → 0을 정상 수치처럼 꾸미지 않고 빈 상태를 표시한다". 제안: 빈 상태 판정에서 `pages_total`을 빼고, `pages_total > 0`인 경우의 테스트를 추가한다.

5. **viewer 응답에 수집 경로 필드가 0으로 반환된다** — `control.py:575-586`이 viewer에게도 `structured`와 `evidence`를 0으로 돌려주고, 테스트가 이를 정상으로 고정한다(`test_control_router.py:912-913`, `test_tenant_isolation_full_path.py:667`). 실제 수치 유출은 없고 화면도 숨기지만(`ControlRoom.tsx`의 `can_view_workspace` 분기), 응답만 보면 "수집 호출 0건"과 구분되지 않는다. 근거 Scenario: "본인 Ask 집계만 표시되고 수집 경로 집계는 반환되지 않는다". 제안: `can_view_workspace`가 거짓이면 두 필드를 `null`로 내리거나 빼고, 프런트 타입과 두 테스트를 고친다.

6. **THEN 일부를 확인하는 테스트가 없다** — `worker.compile_fabricated_evidence`(`compile.py:281`)와 `worker.conflict_pairs_unjudged`(`conflict.py:143-148`)를 단언하는 테스트가 `apps/worker/tests`에 없다. 근거 Scenario: "지어낸 앵커 수가 구조화 로그에 남는다", Requirement "그 쌍을 판정하지 않은 것으로 SHALL 기록". 제안: 두 로그의 존재와 개수를 단언한다.

7. **task 5.2가 완료인데 기본 모드 결정이 기록되어 있지 않다** — task는 "기본 모드를 정하고 `docs/reference/stack.md`와 `docs/ops/`에 기록한다"이고 design Risks도 "샘플 재생으로 위반율을 확인한 뒤 기본값을 정한다"이다. `AI_CONTROL_QUALITY_MODE`는 `docs/` 어디에도 없다. `stack.md`의 변경은 마이그레이션 표뿐이다. 또 `docs/ops/ask-sample-replay.md`의 Step 3 열이 인용한 `314a855`는 HEAD의 조상이 아니어서 이 브랜치로 재현할 수 없다. 제안: 기본값 `enforce`와 그 근거(위반 0/30이라 수리 경로는 재생에서 돌지 않았다는 한계 포함), 되돌리는 방법을 두 문서에 적고, 커밋 표기를 실제 이력(`1f52a6e`)으로 고치되 그 커밋의 재생이 아니면 그 사실을 명시한다.

## 설계 결정 대조

| 결정 | 결과 | 비고 |
| --- | --- | --- |
| D1 기록 후 판정, 예외 없는 분류 | 일치 | `llm.py:282-315`, `:514-530` |
| D2 펜스 한 겹 | 일치 | `llm.py:70`, `:113-122` |
| D3 placeholder 전체 일치 | 일치 | 다만 판정 시점이 앵커 제거 전이다 (항목 2) |
| D4 2회와 비재시도 | 부분 일치 | 스키마 소진은 일치, 내용 없는 응답이 빠졌다 (항목 1) |
| D5 두 코드 | 일치 | 코드는 둘이다. 표현 판정은 항목 3 |
| D6 사후 수리와 2,000토큰 초안 | 일치 | `ask.py:81`, `:617-626`, `:987-994` |
| D7 `fallback` 상태와 본문 정리 | 일치 | `0029`, `answer_contract.py:84` |
| D8 근거 테이블과 범위 교체 | 일치 | `0030:19-34`, `:54-85`, `apps/worker/src/worker/db/service.py:430` |
| D9 품질 집계 형태와 타입 확인 | 일치 | `0031:56-67`. 잘못된 문자열을 검사가 먼저 걸러 거짓이 되는 것을 DB에서 확인했다 |

## 검증 실행

- `uv run pytest` (worker 6개, core 1개, api 4개 파일): 275 passed, 1 error. 오류는 `test_requester_jwt_update_matrix...[wiki_links]`의 준비 단계 `LookupError`다. 단독 재실행은 통과했다. 원인은 확정하지 못했다.
- `pnpm exec vitest run` (`ControlRoom`, `ControlledAiShowcase`, `AskThreadHistoryRestore`): 27 passed.
- `supabase/tests/wiki_page_evidence.sql`을 `docker exec psql`로 실행: 오류 없이 ROLLBACK까지 진행.
- `openspec validate ai-control-output-contract --strict`: valid.
- 로컬 스택(`supabase_db_NexusWiki`, 54422)은 0031이 아니라 **0034까지** 적용되어 있었다. 0032~0034는 이 브랜치에 없고 `feat/ai-control-risk-policy` worktree에 있다. 그 세 파일은 `finalize_ask_turn`, `control_quality_snapshot`, `replace_wiki_page_evidence`, `ask_messages_status_check`를 건드리지 않음을 확인했지만, 0031만 적용된 깨끗한 스택에서의 결과는 확인하지 못했다.
- 위 "실측"은 이 브랜치 코드에 합성 입력을 넣어 재현한 것이다. 큐 재시도 횟수(최대 6회)는 실제 큐를 돌린 값이 아니라 분류 결과와 `max_attempts` 기본값으로 계산한 값이다.

## 참고 (판정에 넣지 않음)

- `repair` 구간(`ask.py:985`)이 `_SPAN_LABELS`(`control.py:73-78`)에 없어 Control Room 추적에서 빠진다. 수리 시간이 화면에 보이지 않는다. 스펙 요구는 아니다.
- Fallback은 제목의 앵커를 지우지 않는다(`answer_contract.py:108`). 제목에 `[[wiki:w9]]`가 있으면 답변에서는 지워지지만 `fabricated_anchor_count`가 1이 된다. 스펙 문구는 "근거 본문"이라 판정에 넣지 않았고, 항목 2에서 제목을 정리하면 대부분 해소된다.
- 수리 호출 비용은 같은 `stream` 경계를 지나 호출마다 새 `p_call_id`로 예약된다(`ask.py:615`, `apps/worker/src/worker/llm_stream.py:139`, `apps/worker/src/worker/ask_cost.py:80`). 코드 경로로 확인했고, 수리 호출을 실제 경계까지 통과시키는 테스트는 없다.
- `_post_chat`의 능력 탐지 재전송(`llm.py:404-421`)은 4xx 거절 뒤 HTTP 요청을 하나 더 만든다. 기존 동작이고 거절된 요청이라 호출 상한 위반으로 세지 않았다. 5xx와 전송 실패의 큐 재시도도 스펙의 "잘못된 응답"이 아니라고 보고 세지 않았다.
- `scripts/benchmark_retrieval.py`, `scripts/generate_retrieval_benchmark_corpus.py`의 변경은 proposal Impact에 없다. 함수·클래스 AST가 기준과 같아 포맷 변경으로 보이며 사용자 관찰 동작은 없다.

## 판정 근거

미충족 Scenario 2개(호출 상한, 빈 상태)와 부분 충족 3개(placeholder, viewer 응답, 지어낸 앵커 로그 테스트), 그리고 Requirement 문구를 어기는 근거 부족 과대 일치와 task 5.2의 기록 누락이 남아 있어 `pass`가 아니다. 어느 것도 스펙 해석이나 사람의 결정을 요구하지 않고 스펙 범위 안에서 코드·테스트·문서를 고치면 해결되므로 `needs_fix`다.
