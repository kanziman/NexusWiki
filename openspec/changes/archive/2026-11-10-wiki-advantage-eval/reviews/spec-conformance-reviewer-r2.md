# Spec Conformance 리뷰 — wiki-advantage-eval r2

- 판정: needs_fix
- 대상: `33a4476` 위 미커밋 작업 트리. 이 세션에서는 훅이 git을 막아 파일을 직접 읽었다. 대상은 `scripts/ask_replay.py` · `scripts/model_evidence_eval.py` · `scripts/retrieval_ablation.py` · 테스트 두 파일 · `docs/ops/ask-sample-replay.md` · change 산출물이고, 실측 원본 `.worktrees/wiki-advantage-20261110/`도 봤다(`state.json`은 열지 않았다)
- 일시: 2026-11-09T23:30:17Z

## 새로 실행한 검증

| 명령 | 결과 |
| --- | --- |
| `uv run pytest apps/worker/tests/test_ask_replay_script.py apps/worker/tests/test_model_evidence_eval_script.py apps/worker/tests/test_retrieval_ablation_script.py apps/worker/tests/test_eval_regression_gate.py -q` | 216 passed (r1은 210개였고 6개가 늘었다) |
| `uv run python scripts/check_eval_regression.py` | "합성 답변 30문항의 고정 판정 일치" |
| `openspec validate wiki-advantage-eval --strict` | valid |
| `uv run python scripts/ask_replay.py check-sample --sample scripts/fixtures/wiki_advantage.v1.json` | exit 0, 경고 1건 "m09: 기대 사실이 근거 밖 문서(l_email)에 있다", 유형별 10 · 10 · 10 · 10 · 4, 문서 29 |
| 시험지 해시 | `43713409…`, `budget.json`의 `fixture_sha256`과 같다(시험지는 바뀌지 않았다) |
| `ruff check`(바뀐 5파일) · `ruff format --check scripts apps/worker/tests` | 통과 |
| 실측 `scoreboard.html` sha256 | `ba918615…`. `verification.md`에 적은 값과 같고, 표 머리에 "위키 차이" 열이 있다 |

## 사용자 결정 반영 확인

### 결정 1: multi_doc 검사 범위("스펙을 좁히고 경고")

- 스펙: Requirement 본문이 "MUST NOT be stated in any single one of the source documents the question names as its evidence"로 좁혀졌다. 근거 밖에서 우연히 겹치면 "MUST be reported as a warning, not a failure"다. 새 Scenario "Multi-document fact coincides in an unrelated document"도 들어갔다(`specs/wiki-advantage-evaluation/spec.md:8`, `:14-16`).
- 구현: 실패 검사는 근거 문서만 본다(`scripts/ask_replay.py:1035-1040`). 경고는 `typed_sample_warnings`가 근거 밖 문서 전체를 본다(`:1084-1096`). `cmd_check_sample`은 경고를 출력하지만 exit code는 위반에만 따른다(`:1103-1110`).
- 테스트: `test_multi_doc_fact_in_unrelated_document_is_warning_only`(`apps/worker/tests/test_ask_replay_script.py:1250`), `test_wiki_advantage_fixture_reports_m09_coincidence`(`:1259`, 경고가 정확히 m09/l_email 한 건).
- 기록: `design.md:55`, `verification.md:55`.
- **반영됐다.** 남은 것은 문구 하나다. 기존 Scenario "Multi-document fact stated in one document"의 WHEN은 여전히 "in a single source document"라는 무조건 표현이다(`spec.md:11`). 글자 그대로 읽으면 근거 밖 문서의 경우가 새 Scenario와 겹치고, 두 Scenario의 THEN이 정반대(실패 / 통과)가 된다. 본문과 새 Scenario가 뜻을 정해 주므로 새 결정이 필요한 문제는 아니다. 이미 내린 결정을 문구에 마저 옮기는 정리다(조치 4).

### 결정 2: 재시도로 복구한 잡("최종 상태 기준")

- 스펙: "A job is failed when its final state is a failure state; a job that is not yet in a final state MUST also block replay … Recovered jobs MUST NOT block replay but MUST be listed in the ingestion record."(`spec.md:27`). 새 Scenario는 "Job recovered by the product retry"(`:37-39`)와 "Job still running when the record is written"(`:41-43`)다.
- 구현: `build_ingestion`(`scripts/model_evidence_eval.py:264-317`)은 미완료를 막고(`:281-291`), `workspace_id`(`:302`)와 `recovered_jobs`(`:313`)를 기록한다. `recovered_jobs`(`:323-338`)는 `job-retries.jsonl`과 최종 상태를 맞춰 본다. `retry-dead`(`:1665-1721`)는 제품 API `POST /workspaces/{ws}/jobs/{id}/retry`(`apps/api/src/api/routers/jobs.py:176`)를 요청자 JWT로 부르고, `jobs`를 직접 UPDATE하지 않는다. `ingest-record`가 이 함수들을 잇는다(`:1757-1766`).
- 테스트: `test_recovered_jobs_listed_and_do_not_block`(`test_model_evidence_eval_script.py:1032`), `test_ingestion_with_pending_job_is_not_ok`(`:1001`).
- **대부분 반영됐지만 한 갈래가 빠졌다(조치 1).** 워커 자동 재시도(`fail_job` → `failed` → 다시 claim)로 복구한 잡은 기록에 남지 않는다. 이 change의 `verification.md:56`도 "복구 잡은 임베딩 4개(`dead` 3개는 재시도 API, `failed` 1개는 자동 재시도)"라고 그 잡을 복구로 센다.

## r1 조치 항목 해결 여부

| r1 항목 | 상태 | 증거 |
| --- | --- | --- |
| 1. multi_doc 범위 (blocked) | 사용자 결정으로 해소. 문구 정리만 남았다 | 위 결정 1 |
| 2. 복구 잡 기록 (blocked) | 사용자 결정으로 해소. 구현 한 갈래가 빠졌다 | 위 결정 2, 조치 1 |
| 3. 유형별 표의 위키 차이 열 | 코드 해결, 테스트 없음 | `_TYPE_HEAD`에 "위키 차이" 열(`model_evidence_eval.py:1330`)과 회차별 `both − source` 값(`:1357-1364`)이 있고, 실측 `scoreboard.html`도 다시 그렸다. `test_effect_view_by_type_and_refusal_excluded`(`:896-938`)는 이 열과 값을 확인하지 않는다(조치 3) |
| 4. 문서 판정 순서에 금지 사실 | 해결 | `docs/ops/ask-sample-replay.md:32`가 "… 기대 사실 … · 금지 사실(`expect_none`)을 말하지 않음(정의된 질문만, 기존 30문항에는 없다) · … 인용"을 넣었고, 순서가 `verdict`(`ask_replay.py:216-223`) 및 docstring(`:188`)과 같다 |
| 5. 측정 장애 범위 | 스펙 · 코드 해결, 설계가 뒤처졌다 | 스펙 "a model's verdict is `inconclusive` when … a measurement failure of its own, and the overall verdict is `inconclusive` when any model has a measurement failure"(`spec.md:57`). `overall_verdict(measurement_failure=…)`는 `model_evidence_eval.py:1040-1051`이고 `build_view`가 `:1142`에서 넘긴다 · 테스트 `:1025`. 설계 D7의 전체 판정 규칙(`design.md:85`)에는 이 조건이 없다(조치 4) |
| (격리 r1) `select_capped` · `workspace_id` | 해결 | `ask_replay.py:945-956`, `ingest-record`(`model_evidence_eval.py:1736-1753`), 등록의 워크스페이스 대조(`:1797-1800`) · 테스트 `:1018`, `:1015` |

## 시나리오 판정

### wiki-advantage-evaluation

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Typed question set / Multi-document fact stated in one document | 충족(근거 문서 기준) | `ask_replay.py:1035-1040` · 테스트 `test_ask_replay_script.py:1180`. WHEN 문구 정리는 조치 4 |
| Typed question set / Multi-document fact coincides in an unrelated document | 충족 | `ask_replay.py:1084-1107` · 테스트 `:1250`, `:1259` |
| Typed question set / Conflict question without the old value forbidden | 충족 | `ask_replay.py:1051-1052` · 테스트 `:1187` |
| Typed question set / Question without a type | 충족 | `ask_replay.py:1016-1018` · 테스트 `:1201`, `:1219`(네트워크 전에 거부) |
| (본문) 유형별 최소 개수 · 4,000자 · 형제 문서 · 해시 고정 | 충족 | `ask_replay.py:1056-1080` · 테스트 `:1209`, `:1239`. 해시는 `budget.json`과 같다 |
| Fixed cheap compile model / Compile model equals an answer model | 충족 | 테스트 `test_model_evidence_eval_script.py:745`, `:750` |
| Fixed cheap compile model / One compile job failed | 충족 | `build_ingestion` `:280`, `:288-289`, `replay_cap` `:343-346` · 테스트 `:755` |
| Fixed cheap compile model / Job recovered by the product retry | 충족(이 Scenario의 `dead` → 재시도 API 경로) | `retry-dead` `:1696-1718`, `recovered_jobs` `:323-338` · 테스트 `:1032`(재시도 2회, `ok: true`) |
| Fixed cheap compile model / Job still running when the record is written | 충족 | `:281-291` · 테스트 `:1001` |
| (본문) "any job that failed and was recovered through the product's retry path" | **부분 충족** | 워커 자동 재시도로 복구한 잡이 기록되지 않는다(조치 1) |
| Total budget / Ingestion spent part of the budget | 충족 | `replay_cap` `:341-350` · 테스트 `:783`, `:948` |
| Total budget / Remaining budget too small | 충족(r1과 같다) | 기존 `plan_rounds` · 실측 `plan.void-cost.json` |
| Pre-registered effect criterion / Wiki recovers enough questions | 충족 | `model_verdict` `:1030-1037`, `overall_verdict` `:1040-1051` · 테스트 `:825`, `:896` |
| Pre-registered effect criterion / Wiki shows no difference | 충족 | 테스트 `:825` |
| Pre-registered effect criterion / Too few complete rounds | 충족 | `MIN_ROUNDS_FOR_VERDICT` `:1027` · 테스트 `:825` |
| (본문) 어느 모델이든 측정 장애 → 전체 `inconclusive` | 충족 | `:1045-1046`, `:1142` · 테스트 `:1025` |
| Per-type report / Wiki helps only on conflicts | 충족 | `model_summary.by_type` `:1003-1013` · 테스트 `:930-931` |
| Per-type report / Refusal question differs between conditions | 충족 | 테스트 `:929`, `:932`, `:937-938` |
| (본문) 유형별 위키 차이 | 충족(코드), 테스트 없음 | `:1330`, `:1357-1364`, 실측 html. 조치 3 |

### ask-replay-scorecard

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Per-question pass verdict / Answerable question meets every criterion | 충족 | `ask_replay.py:214-240` |
| / Question fails on one criterion | 충족 | 기존 테스트 |
| / Several criteria fail at once | 충족 | 코드 `:216-223`와 문서 `docs/ops/ask-sample-replay.md:32`의 순서가 같다 · 테스트 `test_ask_replay_script.py:194` |
| / No expected fact defined | 충족 | `:219` |
| / Answer states a forbidden fact | 충족 | `:221-223` · 테스트 `:1070` |
| / No forbidden facts defined | 충족 | 테스트 `:1079` · 회귀 관문 일치 |
| / 거절 6개 · Turn did not reach the model | 충족(이번에 바뀌지 않았다) | `:203-216` · 기존 테스트 |

### model-evidence-ablation

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Per-turn verdicts / Answer ends as a fallback · Source-only answer | 충족(기존) | 기존 테스트 |
| / Answer lists the old and the new value | 충족 | 테스트 `test_model_evidence_eval_script.py:793` |
| / Existing sample without types or forbidden facts | 충족 | 테스트 `:811` |

## 새 회귀 점검

- 기존 30문항 판정: 회귀 관문이 일치한다. `overall_verdict`의 새 인자는 등록에 `effect_criterion`이 있을 때만 쓰이므로(`:1127`, `:1145`) 이전 실험의 성적표는 바뀌지 않는다(`test_view_without_criterion_has_no_effect_section` `:941`).
- `_wait_for_jobs` · `_usage_total`이 `select_capped`로 바뀌었다(`ask_replay.py:965`, `:985`). 행이 1000개 이상이면 멈추는 동작이 추가됐지만, 이는 실험 도구의 안전 장치이고 제품의 사용자 동작이 아니다. 기존 시험지의 잡 · 사용량 행 수는 1000에 한참 못 미친다.
- 실측 판정은 바뀌지 않았다. r1에서 다시 계산한 `not_supported`에 측정 장애 0건이라, 측정 장애 규칙이 바뀌어도 값이 같다. `verification.md:53`도 이를 적었다.

## 조치가 필요한 항목

1. **워커 자동 재시도로 복구한 잡이 `recovered_jobs`에 빠진다** — `recovered_jobs`는 `retry-dead`가 남긴 `job-retries.jsonl`만 근거로 쓴다(`model_evidence_eval.py:329-338`). 잡 조회도 `id,type,status,last_error`뿐이다(`:1740`). 그래서 `fail_job`이 `failed`로 돌린 뒤 워커가 다시 잡아 성공한 잡은 기록에 남지 않는다. DB에는 흔적이 있다. `complete_job`은 `attempts`를 건드리지 않고(`supabase/migrations/0023_job_trace.sql:88-93`), 초기화는 `retry_dead_job`만 한다(`0009_pipeline_ops.sql:432-435`). 그래서 `attempts > 1`인 `succeeded` 잡이 바로 그 경우다. 이번 실측에도 이런 잡이 실제로 있었다(`drain-retry.log:1`의 `embed:failed 1`, `verification.md:56`). 근거: Requirement "MUST record … any job that failed and was recovered through the product's retry path". `0003_jobs.sql:17`에 따르면 `failed`는 백오프 뒤 재시도할 상태이므로 제품 재시도 경로에 든다. 제안: `ingest-record`의 잡 조회에 `attempts`를 더한다. `recovered_jobs`는 `job-retries.jsonl`에 없더라도 `status = succeeded`이고 `attempts > 1`인 잡을 `retries = attempts − 1`, `via: worker`로 넣는다. 테스트도 하나 더한다. 덧붙여 `retry-dead`는 응답 코드와 상관없이 한 줄을 남기므로(`:1706-1715`), 409처럼 재시도가 안 된 호출도 `retries`에 섞인다(실측 `drain-retry.log:5-9`). 이 수는 `status_code == 200`만 세는 편이 맞다.
2. **(경미) 자동 재시도 대기인 `failed`가 "실패한 잡"으로 분류된다** — `build_ingestion`은 `replay._FAILED_JOB_STATES`(`ask_replay.py:81`, `failed` 포함)로 실패를 판정한다(`model_evidence_eval.py:280`). 하지만 `failed`는 최종 상태가 아니다(`0003_jobs.sql:17`). 재생을 막는다는 결과는 같다. 다만 사용자 결정("실패는 최종 상태 기준, 미완료는 미완료로 차단")에 맞추려면 `failed`를 `pending` 쪽으로 옮겨야 한다. 그래야 이유가 "끝나지 않은 잡"으로 적힌다. `retry-dead`의 `done` 집합(`:1677`)은 이미 그렇게 나눈다. 근거 Scenario: "Job still running when the record is written".
3. **유형별 위키 차이 열을 확인하는 테스트가 없다** — 코드와 실측 html에는 열이 있다. 그런데 `test_effect_view_by_type_and_refusal_excluded`(`test_model_evidence_eval_script.py:896-938`)는 "위키 차이" 머리나 `conflict`의 `+2 · +2` 값을 확인하지 않는다. 근거 Requirement "Per-type wiki difference report … the wiki difference … broken down by question type". 제안: 그 테스트에 `"위키 차이" in page`와 `conflict` 행의 `+2` 단언을 더한다.
4. **(문서) 결정을 문구에 마저 옮긴다** — (a) Scenario "Multi-document fact stated in one document"의 WHEN(`spec.md:11`)을 "appears verbatim in one of the documents the question names as its evidence"로 바꿔 새 경고 Scenario와 겹치지 않게 한다. (b) `design.md:85` D7 전체 판정에 "어느 모델이든 측정 장애가 있으면 `inconclusive`"를 넣어 스펙 · 코드와 맞춘다. 둘 다 사용자가 이미 내린 결정을 문구에 옮기는 일이라, 새로 사람의 결정이 필요하지 않다.

## 판정 근거

r1의 blocked 두 건은 사용자 결정으로 스펙에 정확히 들어갔다. multi_doc 결정은 구현 · 테스트 · 기록까지 빠짐없이 반영됐다. r1 조치 3 · 4 · 5와 격리 리뷰 반영도 코드와 문서에서 확인했다. 검증 명령은 모두 통과했고, 기존 30문항 판정과 실측 판정에는 회귀가 없다. 남은 것은 모두 스펙 범위 안에서 코드 · 테스트 · 문구를 고치면 닫힌다. 그중 조치 1은 스펙 본문 "recovered through the product's retry path"가 요구하는 기록 하나(워커 자동 재시도 복구)를 빠뜨렸다. 이 change의 `verification.md`도 그 잡을 복구로 세므로, 해석 문제가 아니라 구현 누락이다. 그래서 `pass`가 아니라 `needs_fix`다. 실측 결과와 사전 등록 판정에는 영향이 없다. 실측 `ingestion.json`은 이 필드 이전 코드로 만들었고, `verification.md`가 복구 4건을 대신 기록한다.
