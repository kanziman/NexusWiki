# Spec Conformance 리뷰 — retrieval-evidence-ablation r1

- 판정: needs_fix
- 대상: 커밋되지 않은 작업 트리 (`git diff` + 미추적 파일, 기준 `016ad7b18ad131ce28997df1c297acae8cddfb6c`, 브랜치 `feat/retrieval-evidence-ablation`)
- 일시: 2026-11-08T12:44:10Z
- 새로 실행한 검증: `uv run pytest packages/core/tests/test_retrieval_golden.py apps/api/tests/test_retrieval_service.py apps/worker/tests/test_retrieval_ablation_script.py` → 82 passed, `openspec validate retrieval-evidence-ablation --strict` → valid
- 실험 원본 기록 대조: `.worktrees/ablation-evidence-20261108/`의 `registration.json` · `retrieve.json` · `answer.json` · `query-vectors.json` · `query-vectors.failed-502.json`의 sha256이 `verification.md` 표와 모두 일치. 두 기록의 `fixed_inputs`가 완전히 같고, `experiment: "retrieval-evidence-ablation"`, 단일 근거 조건의 `diagnostic: true`, 사전 등록 12:14:01Z < 검색 기록 12:18:06Z를 확인했다. `publishable`에는 fixture 질문 원문 0건, 답변 본문 0건, 워크스페이스 id·UUID 0건, 토큰 패턴 0건이다(기록 전체에도 워크스페이스 id와 JWT가 없다).

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Six-condition matrix / All six conditions share fixed inputs | 충족 | 조건 행렬 `scripts/retrieval_ablation.py:80-88`, 6조건 루프 `:1736-1749`, 기록 단위 `fixed_inputs` `:196-220` · `:396`. 고정 입력 결정성 테스트 `apps/worker/tests/test_retrieval_ablation_script.py:224`. 실기록 `retrieve.json`·`answer.json`의 `fixed_inputs` 동일 확인 |
| Six-condition matrix / A condition was produced from different inputs | 부분 충족 | 거부와 항목 명시 `scripts/retrieval_ablation.py:933-963`, 테스트 `test_retrieval_ablation_script.py:534`(질의 벡터). 단, 요구 본문이 고정 입력으로 열거한 **답변 프롬프트 버전**은 `fixed_inputs` 밖(`:1376`)에 있어 비교 거부 대상이 아니다 → 조치 2 |
| Title header / Source chunk with a real title | 충족 | `embedding_text` `scripts/retrieval_ablation.py:105-117`, 실제 제목 사용 `:693-704`. 저장 본문·좌표 불변: 실험 SQL이 `public.source_chunks.content`를 그대로 돌려줌 `:505`, 어휘 채널은 운영 RPC `:882-884`. 테스트 `test_retrieval_ablation_script.py:334` · `:352` · `:459` |
| Title header / Section is not available | 충족 | 섹션 입력 경로 자체가 없음. 입력 형식은 `title_body-v1` 하나 `scripts/retrieval_ablation.py:88`. 전용 테스트는 없으나 부재가 곧 증거 |
| Distinguishable vectors / Title changes while body stays the same | 충족 | 5항목 PK `scripts/retrieval_ablation.py:470-482`, 재사용 판정 `:784`, 검색 시 현재 텍스트 해시 일치 행만 사용 `:515-519` · `:550-554`. 테스트 `test_retrieval_ablation_script.py:415` |
| Distinguishable vectors / Product request runs during an experiment | 충족 (구조적 증거만) | `apps/`·`packages/`·`supabase/` 소스 어디에도 `ablation` 참조 없음(grep), 스키마 권한 회수 `scripts/retrieval_ablation.py:468`, 마이그레이션 미추가. 자동 테스트는 없다(task 2 Given/When/Then 마지막 줄도 테스트 없이 `[x]`) |
| Evidence scope / Wiki-only scope | 충족 | `apps/api/src/api/services/retrieval.py:109-147`, 정책 필드 `packages/core/src/nexuswiki_core/retrieval_policy.py:45` · `:61-65`, 범위 매핑 `scripts/retrieval_ablation.py:80-84` · `:120-123`. 테스트 `apps/api/tests/test_retrieval_service.py:137` · `:154` · `:171`, `test_retrieval_ablation_script.py:111` · `:122` |
| Evidence scope / A channel fails during a condition | 부분 충족 | 검색 단계는 충족: `classify` `scripts/retrieval_ablation.py:282-293`, 테스트 `test_retrieval_ablation_script.py:153` · `:161`. **답변 단계 조건 기록은 채널 상태를 남기지 않고**(`turn_row` `:1244-1272`가 `meta.missing_channels`를 버림), 채널 장애를 실행 장애로 분류하지 못한다(`answer_verdict` `:1138-1177`) → 조치 1 |
| Retrieval-first / Retrieval phase completes | 충족 | `cmd_retrieve` `scripts/retrieval_ablation.py:1598-1781`는 LLM 클라이언트를 만들지 않음, 기록 `answer_micros: 0` `:1776`. 실기록 `retrieve.json` cost `answer_micros: 0` |
| Retrieval-first / Selection rule recorded after results | 충족 | `check_registration` `scripts/retrieval_ablation.py:1086-1101`, 호출 `:1875`. 테스트 `test_retrieval_ablation_script.py:587` · `:595` |
| Retrieval-first / Spending cap reached | 충족 | `run_answers` `scripts/retrieval_ablation.py:1210-1241`, 미실행 판정 `:1142-1143`, 임베딩 상한 `:721-768`. 테스트 `test_retrieval_ablation_script.py:635` · `:431` · `:445` |
| Diagnostic verdicts / Source-only answer without wiki citation | 충족 | `answer_verdict` 단일 근거 분기 `scripts/retrieval_ablation.py:1159-1177`. 테스트 `test_retrieval_ablation_script.py:668` |
| Diagnostic verdicts / Gold document absent from evidence | 충족 | `classify` `scripts/retrieval_ablation.py:288-293`. 테스트 `test_retrieval_ablation_script.py:171` |
| Diagnostic verdicts / Diagnostic result next to product scorecard | 부분 충족 | 진단 표시는 있음: 헤더 `(진단)` `scripts/retrieval_ablation.py:1004-1005`, `verdict_rule` `:1201`, 문서 `docs/ops/ask-sample-replay.md:124`. 그러나 답변 표의 `통과율`/`통과` 한 행에 단일 근거 진단 수치와 `both`의 이중 인용 통과율을 나란히 놓는다(`scripts/retrieval_ablation.py:991` · `:1023-1025`, `docs/ops/ask-sample-replay.md:131`) → 조치 3 |
| Append-only record / Output path already exists | 충족 | 요청 전 검사 `scripts/retrieval_ablation.py:1601-1602` · `:1868-1869` · `:1786-1787`, `"x"` 모드 `:1397-1405`. 테스트 `test_retrieval_ablation_script.py:258` · `:274` |
| Append-only record / Question recovers under another condition | 충족 | `transitions` `scripts/retrieval_ablation.py:412-455`. 테스트 `test_retrieval_ablation_script.py:511`. 실기록 `retrieve.json` transitions 7쌍 |
| Append-only record / Publication reads the record | 충족 | `publishable` `scripts/retrieval_ablation.py:1275-1329`, 다른 실험 거부 `:954-958`. 테스트 `test_retrieval_ablation_script.py:734` · `:746` · `:546`. 실기록 publishable 검사 결과 위 머리말 참조 |
| Product defaults / Experiment completes | 충족 | 워커 임베딩 코드 변경 없음(diff에 `apps/worker/src` 없음), 기본 정책 해시 보존 `scripts/benchmark_retrieval.py:100-103`, 테스트 `packages/core/tests/test_retrieval_golden.py:235` · `:249` |
| Product defaults / Non-loopback target | 충족 | `assert_loopback` 호출 `scripts/retrieval_ablation.py:1604-1605` · `:1871-1872`(모든 네트워크 요청 이전). 테스트 `test_retrieval_ablation_script.py:292` · `:311`. `answer`의 루프백 거부 테스트는 없음(코드 경로는 `retrieve`와 같은 함수) |

## 조치가 필요한 항목

1. **답변 재생 단계의 채널 장애가 기록·분류되지 않는다** — `answer`는 `AskService`가 조건별 `RetrievalService`로 검색을 다시 수행하는데, 그 검색의 채널 상태를 조건 기록에 남기지 않는다. `AskService`는 `meta` 이벤트에 `missing_channels`를 싣지만(`apps/api/src/api/services/ask.py:945-953`) `turn_row`(`scripts/retrieval_ablation.py:1244-1272`)가 이를 읽지 않고, `answer_verdict`(`:1138-1177`)는 상태가 `resolved`이면 채널이 실패했어도 `pass`/`fact_missing`으로 판정한다. 답변 조건 기록에는 `enabled_channels`도 없다(`:1357-1366`). 근거 Scenario: "WHEN a vector channel fails under the `both` scope THEN the record marks that channel as failed and the affected question is classified as an execution failure", 요구 본문 "Each condition record MUST list which channels were active by design, which succeeded, and which failed." 제안: `turn_row`가 `meta` 이벤트의 `missing_channels`를 `failed_channels`로 저장하고, `answer_verdict`가 이 값이 비어 있지 않으면 범위와 무관하게 `execution_failure`로 분류하게 한다. 답변 조건 기록에 `enabled_channels`를 넣고, 해당 테스트를 추가한다.

2. **답변 프롬프트 버전이 비교 거부 대상이 아니다** — 요구는 답변 프롬프트 버전을 고정 입력으로 열거하고 "fixed-input hashes가 다르면 비교·집계를 거부"하라고 한다. 구현은 `answer_prompt_sha256`을 `fixed_inputs` 밖(`scripts/retrieval_ablation.py:1376`)에 두고, `merge_records`(`:945-973`)는 `fixed_inputs`만 대조한다. 따라서 프롬프트가 다른 두 답변 기록의 조건이 조용히 한 표로 합쳐진다. `:1374`의 주석("비교 명령은 이 값을 대조한다")도 실제 동작과 다르다. 근거: Requirement "Six-condition matrix over a fixed ingestion" 본문. 제안: 답변 단계 기록끼리 비교할 때 `answer_prompt_sha256`이 다르면 거부하고 항목 이름을 보이게 한다. 예를 들어 답변 기록의 비교용 키에 넣거나 `merge_records(phase="answer")`에서 별도로 대조한다. 거부 테스트를 추가한다.

3. **진단 답변 수치가 제품 이중 인용 통과율과 같은 행에 놓인다** — 요구는 단일 근거 결과를 "MUST NOT be reported as or compared with the product scorecard's dual-citation pass rate"라고 한다. `compare_markdown`의 답변 표는 `통과율` 한 행에 `source_onlyxbody (진단)`의 사실 기준 통과율과 `both`의 제품 규칙 통과율을 나란히 출력한다(`scripts/retrieval_ablation.py:991` · `:1023-1025`). 운영 문서도 `| 통과 | 28/29 (사실 기준) | 28/29 (제품 규칙) | …`로 같은 행에 놓는다(`docs/ops/ask-sample-replay.md:131`). 같은 문서의 검색 표는 `이중 적중@8`에서 단일 근거 칸을 `진단`으로 비워 두므로(`:124`) 답변 표만 일관되지 않다. task 4의 Given/When/Then("이중 인용 통과율과 나란히 비교되지 않는다")에도 걸린다. 제안: 답변 표에서 `both`의 제품 규칙 통과율 행과 단일 근거의 진단 통과 행을 분리하고, 해당 칸이 아닌 곳은 `진단`/`-`로 비운다. 문서 표도 같은 방식으로 고친다. 기대 사실 포함 행은 그대로 비교해도 요구에 어긋나지 않는다.

4. **기록의 측정 비용이 실험 전체가 아니라 마지막 실행분만 담는다** — 요구는 기록에 "measured cost"를 포함하라고 한다. `retrieve.json`의 `cost`(그리고 `publishable.cost`)는 `embedding_calls: 1, embedding_micros: 3`이다. 실제 실험의 임베딩은 67회 134 micros였다(`verification.md`). 질의 벡터 30개와 제목 벡터 35개는 앞선 실행에서 만들어 재사용됐고, 그 비용은 어느 기록에도 들어가지 않는다(`EmbedBudget`은 실행 단위 `scripts/retrieval_ablation.py:728-768`, 기록 `:1772-1777`). #230이 `publishable`만 읽으면 임베딩 비용을 과소 보고하게 된다. 제안: 질의 벡터 파일 생성 시 사용액·호출 수를 그 파일에 기록하고, 제목 벡터 준비 비용은 `ablation` 행이나 별도 원장에 남긴다. 검색 기록은 재사용한 산출물의 비용을 합산하거나 "이전 실행분 별도"임을 필드로 명시한다. 이미 쓴 기록은 append-only라 고치지 않고, `verification.md`의 합계가 정본임을 문서에 적는 것으로 충분하다.

5. **조건 기록에 "성공한 채널"이 명시되지 않는다** (경미) — 요구는 활성·성공·실패 채널을 모두 나열하라고 한다. 검색 조건은 `enabled_channels`(`scripts/retrieval_ablation.py:372`)와 행별 `failed_channels`·`disabled_channels`(`:360-361`)를 두고, 성공 채널은 차집합으로만 알 수 있다. 제안: 행별 `succeeded_channels`(meta의 `status == "ok"`)를 명시한다. 조치 1과 함께 답변 조건에도 적용한다.

## 판정 근거

18개 Scenario 중 14개는 코드 경로와 테스트(또는 실험 원본 기록)로 충족된다. 고정 입력 해시, 진단 표시, `publishable`의 금지 필드 부재, append-only, 실험 식별자는 실기록에서도 확인했다. 미충족 4건은 모두 스펙 범위 안에서 코드나 문서를 고치면 해결된다. 답변 단계 채널 장애 분류, 프롬프트 해시 비교 거부, 진단 수치의 행 분리, 비용 집계가 그것이다. 스펙 자체를 바꿀 필요는 없으므로 `needs_fix`다.

참고(판정에 반영하지 않음):

- 답변 단계 분류에는 스펙의 세 분류(검색 미적중 · 실행 장애 · 의도된 단일 근거) 밖의 값이 있다(`fact_missing` · `fail` · `measurement_failure` · `refusal_*`). 검색에서 정답을 찾았는데 답이 틀린 경우(실기록 `source_onlyxbody`의 q06)는 세 분류 어디에도 맞지 않는다. 요구 문장을 "검색 판정에서 통과하지 못한 문항"으로 읽으면 구현이 충족하며, `/opsx:sync` 때 본 스펙에 답변 단계 분류를 명시하기를 권한다.
- "Product request runs during an experiment"는 자동 테스트가 없고 구조적 증거(참조 부재·권한 회수)에만 기댄다. 실험 전 운영 임베딩 해시를 남기지 않은 이탈은 `verification.md`에 기록돼 있다.
- 실기록의 `git_sha`는 `016ad7b`(dirty 표기 없음)로 찍혔다. 이 점은 `verification.md`와 운영 문서에 공개됐고, 이후 `+dirty` 표기로 고쳐졌다(`scripts/retrieval_ablation.py:1441-1459`).
- 이번 라운드는 사용자 지시로 tenant-isolation 리뷰를 생략했다.
