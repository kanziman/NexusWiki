# Spec Conformance 리뷰 — ask-evidence-research r1

- 판정: needs_fix
- 대상: 기준 HEAD `5dded7b` 위의 미커밋 작업 트리 (`/private/tmp/nexuswiki-evidence-research`, `git diff` + 신규 파일)
- 일시: 2026-11-09T00:23:12Z
- 참고 실행(이번 리뷰에서 새로 실행): 변경 관련 pytest 6개 파일 112 passed. `scripts/evidence_research_eval.py export /private/tmp/research-fix-20261109 …` 재생성 결과가 `apps/dashboard/content/evidence-research.json`과 완전히 같았음. 현재 작업 트리의 `execution_sha256()`가 측정 지문 `dfda4a4d…2d08`과 같았음(측정한 코드 = 리뷰한 코드)

## 시나리오 판정

### ask-evidence-research

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Bounded model-selected evidence research / Missing comparison target | 충족 | 판단 1회 `apps/api/src/api/services/ask.py:697-748`(`asyncio.timeout(15)`, `evidence_research=True`), 검색 최대 2회 `packages/core/src/nexuswiki_core/evidence_research.py:30-31,83-84`, 병합·재예산 `ask.py:1084-1111` · 테스트 `apps/api/tests/test_ask_router.py:209-316`(도구 호출 → 재검색 → 추가 청크가 `resolved`에 포함, SSE `meta,delta,citations,done`), `apps/api/tests/test_evidence_research.py:112-120` |
| 〃 / Sufficient evidence or disabled mode | 충족 | 도구 미선택 시 `status=sufficient`, 검색 없음 `ask.py:771` · 테스트 `test_evidence_research.py:157-161`. OFF는 `ask.py:1084` 분기로 판단 호출 자체가 없음, 기본값 `apps/api/src/api/settings.py:75` = False. OFF 테스트는 간접: 기존 테스트의 `_FakeLlmStream.stream`(`test_ask_router.py:105`)이 `evidence_research` 인자를 받지 않으므로 OFF에서 판단 호출이 생기면 기존 테스트가 깨짐 |
| 〃 / No initial evidence | 충족 | no-evidence 반환 `ask.py:1030-1061`이 재검색 분기(`ask.py:1084`)보다 앞섬 · 테스트 `test_ask_router.py:175-205`(ON/OFF 둘 다 LLM 호출 0) |
| Server-owned research authorization and validation / Invalid tool batch | 충족 | 배치 단위 검증 `evidence_research.py:28-48`, 스트림 단계 거부 `evidence_research.py:70-97`, 사유 기록 `ask.py:788-798`(`failure_reason`, `ask.research_failed`) · 테스트 `packages/core/tests/test_evidence_research.py:15-29`(알 수 없는 인자·빈 검색어·501자·비문자열·다른 도구·3개), `test_evidence_research.py:123-129,143-149` |
| 〃 / Cross-tenant request | 충족 | `workspace_id`/`jwt` 인자는 `set(arguments) != {"query"}`로 거부 `evidence_research.py:41-42`. 실행은 원 요청의 `workspace_id`·`user_db`만 사용 `ask.py:753-768`, 재검색 직전 멤버십 재확인 `ask.py:751-761` · 테스트 `packages/core/tests/test_evidence_research.py:18-19`, `test_evidence_research.py:112-115`(실행 인자가 원 workspace·db와 동일), `:152-154`(회수된 멤버십 → 검색 없이 거부) |
| Evidence budget and stream continuity / Duplicate evidence and oversized context | 충족 (테스트 부분) | `(kind, document_id)` 중복 제거 `evidence_research.py:51-59`, `select_dual_evidence` `ask.py:802`, 최종 예산 재적용 `ask.py:1099-1103`, 포함 근거만 별칭 `ask.py:1112`. 답변 스트림은 재검색 이후 시작 · 테스트 중복: `packages/core/tests/test_evidence_research.py:66-69`, `test_evidence_research.py:112-116`. **재검색 경로에서 예산 초과 본문이 잘리는지 보는 테스트는 없음**(예산 함수 재사용으로 판단) |
| Research failure and cost visibility / Timeout or malformed decision | 충족 | `TimeoutError` → `status=timeout` `ask.py:786-787`, 잘못된 판단 → `decision_or_search_failed`+`failure_reason` `ask.py:788-798`, 호출 수 `requested_calls`/`executed_calls` `ask.py:690,750,762`, 무효여도 스트림 끝까지 읽음 `ask.py:734-748`(D2 2026-11-09 결정) · 테스트 `test_evidence_research.py:132-149,170-173`. 실측: ON q28 `incomplete_decision`, `usage_incomplete=False`(`/private/tmp/research-fix-20261109/on-1.json`) |
| 〃 / Authorization or budget denied | 충족 (종료 경로 테스트 없음) | 워커 401/402/403 → `ResearchDenied` `ask.py:726-731`, 검색 경로 거부 전파 `apps/api/src/api/services/retrieval.py:22-31,76-82`, DB 거부 매핑 `ask.py:774-784`, 오류 턴 종료 `ask.py:1133-1138`(토큰 `budget_exceeded`/`forbidden`/`unauthorized`; 기존 답변 경로 402 처리 `ask.py:1179-1192`와 같은 `citations.error` + `status=error` 형태). 워크스페이스 예산은 워커 예약에서 HTTP 402로 헤더 전에 거부됨 `apps/worker/src/worker/ask_cost.py:92-94`, `llm_stream.py:136-142` · 테스트 `test_evidence_research.py:152-154,164-167`, `apps/api/tests/test_retrieval_service.py:44-60`. **`ResearchDenied`가 실제 SSE 오류 턴으로 끝나는지(`ask.py:1135`) 검증하는 테스트는 없음** |
| 〃 / Decision call consumed tokens without searching | 충족 | 판단 호출도 같은 `/internal/llm-chat` 예약·정산 경로 `apps/worker/src/worker/llm_stream.py:136-143,196-222`(`evidence_research` 플래그만 추가 `apps/worker/src/worker/__main__.py:175-187`). eval은 trace 단위로 모든 usage와 `metadata.incomplete`를 합산 `scripts/ask_replay.py:899-944`, 장애 판정 `scripts/evidence_research_eval.py:61-67` · 테스트 `test_evidence_research.py:132-140`(잘린 판단도 끝까지 소비). 실측: ON 입력 토큰 547,330 vs OFF 276,501로 판단 호출이 포함됨. 워커 단위에서 판단 호출 정산을 직접 검증하는 테스트는 없음 |

### ask-replay-scorecard

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Paired evidence research evaluation / Matched pair | 충족 | 조건(corpus·prompts·fixture·model·settings·policy·execution) `scripts/evidence_research_eval.py:83-100`, 실행별 revision `:160-162`, 품질·비용·토큰·총 지연·첫 토큰 p50/p95 `:200-219` · 테스트 `apps/worker/tests/test_evidence_research_eval.py:96-145`. 원본 두 기록의 `conditions` 7개 값이 전부 같음, fixture 다이제스트 `16251953…` |
| 〃 / Corpus or policy changed | 충족 | `conditions_match`/`valid`/`adopted` 차단 `evidence_research_eval.py:227-248,332-334`, 실행 중 스냅샷 변화 시 `aborted_reason` `:148-152` · 테스트 `test_evidence_research_eval.py:151-153` |
| 〃 / Decision implementation changed during resume | 충족 (재개 거부 테스트 없음) | 서버 manifest 지문 없음·불일치 시 시작 거부 `evidence_research_eval.py:80-82`, 재개 원본 조건 불일치 시 거부 `:102-109`, 지문 없는 기록은 유효 비교 아님 `:228-235` · 테스트: 지문이 프롬프트·상한 변경을 감지 `test_evidence_research_eval.py:23-36`, 지문 없는 기록 무효 `:147-150`. **`run()`의 재개 거부(`:80-82`, `:102-109`)는 테스트가 없음** |
| 〃 (요구사항 본문) 문항·판정 기준 사전 고정, 30+6+6 | 충족 | fixture `scripts/fixtures/evidence_research.v1.json`(base 30 + comparison 6 + mismatch 6). 첫 ON(`/private/tmp/nexuswiki-research-eval/on-1.json`, 2026-11-08T10:10) 이전 OFF부터 최종 쌍까지 모든 기록의 fixture 다이제스트가 `16251953…`로 같음 |
| Recovery scoring uses missing initial evidence / Missing target recovered | 충족 | 분모 `eligible` = 전용 문항 ∧ 장애 아님 ∧ 실제 초기 문맥에 기대 문서 전체 없음 `evidence_research_eval.py:275-281`, 근거·답변 복구 분리 `:280-281,355-360` · 테스트 `test_evidence_research_eval.py:143-145` |
| 〃 / No eligible initial failures | 충족 | `rate`는 분모 0이면 `None` `evidence_research_eval.py:359` · 테스트 `test_evidence_research_eval.py:17-21`. 공개 사본: `recovery = {eligible:0, evidence:0, answer:0, rate:null}`, 페이지는 "복구율은 미측정입니다" `apps/dashboard/components/EvidenceResearchShowcase.tsx:209-211` |

### retrieval-evaluation-showcase

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Public evidence research comparison page / Published matched evaluation | **미충족** | 페이지·조건 해시·문항 필터·다운로드는 있음: `apps/dashboard/app/showcase/evidence-research/page.tsx`, `results.json/route.ts`, 미들웨어 matcher에 `/showcase` 없음(`apps/dashboard/middleware.ts` `config.matcher`), controlled-ai 연결 `apps/dashboard/components/ControlledAiShowcase.tsx:86-90`. 그러나 **유효 결과의 OFF/ON 요약이 실제 표본·반복 횟수와 다르게 표시됨**: `EvidenceResearchShowcase.tsx:124-126` "기존 30문항 통과 · 3회 합계"·`/ 90`(실제는 1쌍, 30문항 중 28), `:215` 캡션 "42문항씩 3회", `:262` 실행 쌍 선택지 1~3차(2·3차는 빈 목록). 같은 페이지의 공지(`:180-182`)·`method`는 "한 쌍"이라 서로 모순. 유효 상태 렌더링을 검증하는 테스트도 없음(`apps/dashboard/tests/EvidenceResearchShowcase.test.tsx`는 `valid:false` 데이터만 사용) |
| 〃 / No valid result | 충족 | `valid=false`면 요약 표·복구 수치 숨김, 조건·장애 점검 항목만 표시 `EvidenceResearchShowcase.tsx:186-201,236-250` · 테스트 `EvidenceResearchShowcase.test.tsx:28-39`. 참고: 무효 상태에서도 문항 목록의 행별 "· 복구" 표시는 남음(`:302`) |
| Static allowlisted synthetic evaluation data / Offline result rendering | 충족 | 정적 JSON import + `force-static` `page.tsx:7,10`, `route.ts:1-3`. 공개 export 허용 필드 선택 `evidence_research_eval.py:222-368`. 공개 사본에 UUID·`gen-` 식별자·snapshot·답변 본문 없음(이번 리뷰에서 패턴 검사) · 테스트 `EvidenceResearchShowcase.test.tsx:79-91`, `test_evidence_research_eval.py:39-65` |
| 〃 / Untrusted result text | 충족 | React 텍스트 노드로만 렌더(`dangerouslySetInnerHTML` 없음) · 테스트 `EvidenceResearchShowcase.test.tsx:41-68` |

### 실측·공개 사본 대조

| 항목 | 결과 | 증거 |
| --- | --- | --- |
| 원본 무결성 | 일치 | 5개 파일 sha256이 `verification.md` 표와 같음 |
| 공개 사본 = 해당 쌍의 export | 일치 | `export /private/tmp/research-fix-20261109`를 다시 실행한 결과와 `content/evidence-research.json`이 같음 |
| 조건 일치 표시 | 스펙대로 | `conditions_match=true`, `valid=true`, `measurement_failures=0`, 측정 코드 지문 = 현재 작업 트리 지문 |
| 분모 0·미측정 | 스펙대로 | `recovery.rate=null`, 페이지 "미측정" 문구, `adopted=false`(미충족 3항목: answer_recovered·total_pass_improved·cost_within_limit) |
| 반복 횟수 표시 | **불일치** | 데이터·공지는 1쌍, 요약 표는 "3회"·`/ 90` (위 미충족 항목) |

## 조치가 필요한 항목

1. **공개 페이지가 반복 횟수와 회귀 분모를 틀리게 표시** — `EvidenceResearchShowcase.tsx:124-126`은 OFF/ON 기존 문항 통과를 "28 / 90"·"3회 합계"로 보여주고, `:215` 캡션은 "42문항씩 3회", `:262`은 1~3차 선택지를 둔다. 실제 데이터는 OFF/ON 1쌍(`runs` 2개, `EVALUATION_PAIRS=(1,)`)이고 기존 30문항 중 28개 통과다. 근거 Scenario: "Published matched evaluation — 조건 일치 여부와 OFF/ON 요약 … 을 확인할 수 있다", Requirement 본문 "표본·반복 횟수·판정 방법·한계를 표시". 3쌍 설계를 1쌍으로 줄이면서(D4 2026-11-08) 화면 문구가 따라오지 않은 범위 축소 흔적이다. 제안: 분모를 질문 수에서 계산하고(예: 회귀 문항 수 × 쌍 수), 캡션은 `data.runs`/쌍 수로 만들고, 실행 쌍 선택지는 `data.rows`에 실제로 있는 pair만 보여준다.
2. **유효 결과 렌더링 테스트 없음** — 컴포넌트 테스트 3개는 모두 `valid:false` 데이터를 쓴다. 그래서 1번 결함이 테스트를 통과했다. 근거 Scenario: "Published matched evaluation". 제안: `content/evidence-research.json`이나 같은 모양의 유효 픽스처로 렌더해 조건 일치 표시, OFF/ON 요약 값(28/30, 39/42), 복구율 "미측정", 반복 1쌍 문구, 채택 미달 제목을 검증한다.
3. **평가 재개 거부 경로 미검증** — `evidence_research_eval.py:80-82`(manifest 지문 없음·불일치)와 `:102-109`(재개 원본 조건 불일치)에 테스트가 없다. 근거 Scenario: "Decision implementation changed during resume — 재개를 거부하고 …". 제안: 네트워크 호출 전에 끝나는 분기이므로 `replay._login`/`snapshot`을 대역으로 바꾸고 `run()`이 `SystemExit`를 던지는지 검증한다(지문 없음, 지문 불일치, prior `conditions` 불일치 각 1건).
4. **권한·예산 거부의 오류 턴 종료 미검증** — `_research`가 `ResearchDenied`를 던지는지는 테스트됐지만(`test_evidence_research.py:152-167`), `ask.py:1133-1138`에서 `citations.error = budget_exceeded/forbidden`, `status=error`로 끝나는지 보는 Ask 제너레이터 수준 테스트가 없다. 근거 Scenario: "Authorization or budget denied — 거부를 일반 검색 실패로 삼키지 않고 기존 오류 계약으로 종료한다". 제안: `test_ask_router.py:209`과 같은 구성에서 판단 호출 상태 402와 멤버십 회수를 넣고, 마지막 `citations.error`와 `finalize_ask_turn`의 상태를 검증한다.

권고(판정에 영향 없음):

- 재검색 경로에서 예산보다 큰 추가 본문이 최종 상한으로 잘리고 별칭이 포함 근거에만 붙는지 직접 보는 테스트(`Duplicate evidence and oversized context`)를 추가하면 좋다.
- 워커 `__main__._stream_llm_chat`의 판단 출력 상한 `min(…, 256)`(`apps/worker/src/worker/__main__.py:180-184`)과 판단 호출 정산을 직접 검증하는 테스트가 없다.
- 무효 상태(`valid=false`)에서도 행별 "· 복구" 라벨이 보인다(`EvidenceResearchShowcase.tsx:302`). 스펙이 금지하는 것은 "요약"이지만, 조건이 다를 때는 행 라벨도 숨기는 편이 스펙 취지에 맞다.

## 범위 밖으로 합의된 공급자 402 문제에 대한 의견

결론: 이 change의 범위 안에서 스펙 "인증·권한·예산 오류는 기존 오류 계약을 따라야 한다"를 어긴다고 보지 않는다. 근거는 다음과 같다.

- 스펙과 D2의 "예산 거부"는 워크스페이스 월 상한이나 비용 예약 거부다. 이 거부는 워커가 **응답 헤더 전에** HTTP 402로 돌려준다(`apps/worker/src/worker/ask_cost.py:92-94`, `llm_stream.py:136-142`). 판단 호출에서는 이것이 `ResearchDenied("budget_exceeded")`(`ask.py:726-731`)로 바뀌고 오류 턴으로 끝난다(`ask.py:1135`). 검색 경로의 `NW402`/402도 같은 방식으로 전파된다(`ask.py:776-784`, `retrieval.py:22-31,76-82`).
- 공급자(OpenRouter) 크레딧 소진 402는 워커가 헤더를 보낸 뒤 제너레이터 안에서 `ProviderCreditExhausted`로 터진다(`apps/worker/src/worker/llm.py:236-242`). 그래서 API에는 연결 끊김으로 보인다. OFF 경로도 똑같아서 답변 스트림은 `llm_unavailable` 오류 턴으로 끝난다(`ask.py:1200-1215`). 이것이 기존 계약의 실제 동작이다.
- ON 경로에서는 판단 단계에서 이 끊김이 일반 실패(`decision_or_search_failed`, `failure_reason=RemoteProtocolError` 같은 예외 타입 이름)로 복구된다. 그다음 최종 답변 호출이 같은 이유로 끊겨 OFF와 같은 `llm_unavailable` 오류 턴으로 끝난다. 즉 최종 사용자 관찰 결과는 기존 계약과 같다. 공급자가 402로 거절한 호출은 과금되지 않으므로 추가 지출도 없다. 차이는 예약·정산 한 건이 늘고, 턴 보고서에 원인이 "예산"이 아니라 "판단 실패"로 남는다는 점뿐이다.
- 이 차이를 고치려면 워커가 헤더를 보내기 전에 공급자 응답 상태를 확인하도록 Ask 스트리밍 구조를 바꿔야 한다. 이는 OFF 경로에도 똑같이 있는 문제이므로 별도 이슈로 다루는 결정이 타당하다. 다만 그 이슈에서 판단 단계도 같이 고쳐야 한다(공급자 402 → `ResearchDenied("budget_exceeded")` 또는 별도 토큰).

## 판정 근거

Ask 재검색 흐름(9개 Scenario)과 평가 도구(5개 Scenario)는 모두 코드 경로와 실측 기록으로 충족된다. 공개 사본도 원본 쌍의 export와 정확히 같고, 측정한 코드 지문도 현재 작업 트리와 같다. 그러나 공개 페이지의 유효 결과 요약이 "3회 합계"·`/ 90`·"42문항씩 3회"로 표시되어, 실제 1쌍인 표본·반복 횟수와 회귀 분모를 틀리게 보여준다. 이는 "Published matched evaluation" Scenario와 "표본·반복 횟수 표시" 요구를 어기며, 같은 페이지의 공지와도 모순된다. 이 결함은 스펙 수정 없이 컴포넌트 코드만 고치면 해결된다. 같은 경로에 테스트가 없어서 생긴 결함이므로 유효 상태 렌더링 테스트도 함께 필요하다. 재개 거부와 거부 오류 턴 종료는 구현은 있으나 테스트가 없어 미검증 완료 주장에 해당한다. 모두 스펙 범위 안의 코드·테스트 보완이므로 `needs_fix`다.
