# Spec Conformance 리뷰 — wiki-advantage-eval r3

- 판정: pass
- 대상: `33a4476` 위 미커밋 작업 트리. 이 세션에서도 훅이 git을 막아 파일을 직접 읽었다. 대상은 `scripts/model_evidence_eval.py` · `scripts/ask_replay.py` · 테스트 두 파일 · delta spec 세 개 · `design.md` · `tasks.md` · `verification.md`다. 실측 원본의 `state.json`은 열지 않았다
- 일시: 2026-11-09T23:36:15Z

## 새로 실행한 검증

| 명령 | 결과 |
| --- | --- |
| `uv run pytest apps/worker/tests/test_ask_replay_script.py apps/worker/tests/test_model_evidence_eval_script.py apps/worker/tests/test_retrieval_ablation_script.py apps/worker/tests/test_eval_regression_gate.py -q` | 218 passed (r2는 216개였고 새 테스트 2개가 늘었다) |
| `uv run python scripts/check_eval_regression.py` | "합성 답변 30문항의 고정 판정 일치" |
| `openspec validate wiki-advantage-eval --strict` | valid |
| `uv run python scripts/ask_replay.py check-sample --sample scripts/fixtures/wiki_advantage.v1.json` | exit 0, 경고 1건(m09 / l_email), 유형별 10 · 10 · 10 · 10 · 4, 문서 29 |
| 시험지 정규 해시 `fingerprint.fixture_sha256` | `43713409…`, r2와 같다(시험지는 바뀌지 않았다) |
| `ruff check`(바뀐 5파일) · `ruff format --check scripts apps/worker/tests` | 통과 |
| `ruff check scripts apps/worker/tests`(전체) | 43건이지만 모두 이 change가 건드리지 않은 `scripts/benchmark_retrieval.py`(13) · `scripts/generate_retrieval_benchmark_corpus.py`(30)에서 나온다 |
| 판별력 점검(스크래치 테스트, 저장소 밖) | `test_type_table_shows_wiki_difference_column`의 두 단언은 유형별 표 밖(전체 요약 표)에서도 각각 한 번씩 성립한다. 아래 r2 조치 3 참고 |

## r2 조치 항목 해결 여부

| r2 항목 | 상태 | 증거 |
| --- | --- | --- |
| 1. 워커 자동 재시도 복구 누락 · 409가 재시도 수에 섞임 | 해결 | `recovered_jobs`(`scripts/model_evidence_eval.py:322-351`)가 이제 두 경로를 센다. (a) `job-retries.jsonl`에서는 2xx만 `api_retries`로 센다(`:334-340`). (b) 최종 상태가 `succeeded`이고 `attempts > 1`인 잡은 `worker_attempts`로 센다(`:341-346`). `ingest-record`의 잡 조회에 `attempts`가 들어갔다(`:1753`). `attempts`는 claim에서만 늘고(`supabase/migrations/0023_job_trace.sql:54`), `retry_dead_job`만 0으로 되돌린다(`0009_pipeline_ops.sql:434`). 그래서 이 판별은 DB 의미와 맞는다. 테스트 `test_recovered_jobs_listed_and_do_not_block`(`apps/worker/tests/test_model_evidence_eval_script.py:1032-1068`)은 409 제외(`api_retries: 2`), 자동 재시도 복구(`j3`, `worker_attempts: 2`), 최종 `dead` 제외(`j2`), `ok: true`를 확인한다 |
| 2. `failed`를 실패로 분류 | 해결 | `build_ingestion`은 `FINAL_FAILURE_STATES = {dead, canceled}`(`:319`)만 실패로 보고(`:282`), `failed`는 미완료로 센다(`:283`, `:289`). 테스트 `test_failed_status_waiting_for_auto_retry_is_unfinished_not_failed`(`:1071-1082`)가 `failed_jobs == []`와 `reasons == ["끝나지 않은 잡 1개"]`를 확인한다. `dead` 경로는 `test_ingestion_with_failed_job_blocks_registration_cap`(`:755`)이 그대로 지킨다 |
| 3. 유형별 위키 차이 열 테스트 | 테스트는 추가됐지만 판별력이 없다(권고) | 코드는 맞다. `_TYPE_HEAD`(`:1343`)에 "위키 차이"가 있고, 회차별 `both − source`가 `:1370-1377`에 있다. 스크래치 점검에서 이 값이 유형별 구역 안에 실제로 그려지는 것도 확인했다. 그런데 새 테스트 `test_type_table_shows_wiki_difference_column`(`:1085-1106`)은 `"<th>위키 차이</th>" in page`와 `"<b>+1 · +1</b>" in page`를 페이지 전체에서 찾는다. 전체 요약 표 머리(`_SUMMARY_HEAD`, `:1241`)에도 같은 열이 있다. 게다가 이 테스트 데이터는 `conflict` 문항만 쓰므로 요약 행의 위키 차이(`:1283`, `:1293`)도 `+1 · +1`이 된다. 그래서 유형별 열을 지워도 이 테스트는 통과한다(아래 권고 1) |
| 4(a). multi_doc 첫 Scenario WHEN 문구 | 해결 | `specs/wiki-advantage-evaluation/spec.md:11`이 "in a single one of the documents the question names as evidence"로 바뀌어, 경고 Scenario(`:14-16`)와 더 이상 겹치지 않는다 |
| 4(b). 설계 D7 전체 판정의 측정 장애 규칙 | 해결 | `design.md:85`가 "어느 모델이든 측정 장애가 있으면 `inconclusive`"로 시작하고, 스펙 `spec.md:61` · 코드 `overall_verdict`와 같다 |
| (추가) 스펙 실패 정의 · 자동 재시도 Scenario | 반영 | Requirement 본문이 실패를 `dead` · `canceled`로 정의하고 자동 재시도 대기를 미완료로 둔다(`spec.md:27`). 새 Scenario "Job recovered by the worker's automatic retry"(`:41-43`)가 들어갔다. 이는 사용자 결정 2("최종 상태 기준")를 문구로 옮긴 것이라 범위 이탈이 아니다 |

## 시나리오 판정

### wiki-advantage-evaluation

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Typed question set / Multi-document fact stated in one document | 충족 | `scripts/ask_replay.py:1035-1040`(근거 문서만 검사) · 테스트 `apps/worker/tests/test_ask_replay_script.py:1180` |
| Typed question set / Multi-document fact coincides in an unrelated document | 충족 | `ask_replay.py:1084-1107` · 테스트 `:1250`, `:1259`. 실측 시험지 경고 1건(m09 / l_email)을 다시 확인했다 |
| Typed question set / Conflict question without the old value forbidden | 충족 | `ask_replay.py:1051-1052` · 테스트 `:1187` |
| Typed question set / Question without a type | 충족 | `ask_replay.py:1016-1018`, `seed`의 사전 검사 `:1141-1144` · 테스트 `:1201`, `:1219` |
| (본문) 유형별 최소 개수 · 4,000자 · 형제 문서 · 해시 고정 | 충족 | `ask_replay.py:1056-1080` · 테스트 `:1209`, `:1239`. 정규 해시 `43713409…`가 r2와 같다 |
| Fixed cheap compile model / Compile model equals an answer model | 충족 | 테스트 `test_model_evidence_eval_script.py:745`, `:750` |
| Fixed cheap compile model / One compile job failed | 충족 | `build_ingestion` `model_evidence_eval.py:282`, `:286-287`, `replay_cap` `:356-359` · 테스트 `:755` |
| Fixed cheap compile model / Job recovered by the product retry | 충족 | `cmd_retry_dead` `:1709-1729`(요청자 JWT, 제품 API), `recovered_jobs` `:333-340`(2xx만 셈) · 테스트 `:1032`(`api_retries: 2`, 409 제외, `ok: true`) |
| Fixed cheap compile model / Job recovered by the worker's automatic retry | 충족 | 복구 기록 `:341-346`(`worker_attempts`), 대기 중 미완료 `:283`, `:289` · 테스트 `:1045-1056`, `:1071-1082` |
| Fixed cheap compile model / Job still running when the record is written | 충족 | `:283`, `:288-289` · 테스트 `:1001` |
| Total budget / Ingestion spent part of the budget | 충족 | `replay_cap` `:354-363` · 테스트 `:783`, `:948` |
| Total budget / Remaining budget too small | 충족(r2와 같다) | 기존 `plan_rounds` · 실측 `plan.void-cost.json` |
| Pre-registered effect criterion / Wiki recovers enough questions | 충족 | `model_verdict` · `overall_verdict` `:1049-1050` 부근 · 테스트 `:825`, `:896` |
| Pre-registered effect criterion / Wiki shows no difference | 충족 | 테스트 `:825` |
| Pre-registered effect criterion / Too few complete rounds | 충족 | `MIN_ROUNDS_FOR_VERDICT` · 테스트 `:825` |
| (본문) 어느 모델이든 측정 장애 → 전체 `inconclusive` | 충족 | 테스트 `:1025` · `design.md:85`와 일치 |
| Per-type report / Wiki helps only on conflicts | 충족 | `model_summary.by_type` · 렌더 `:1359-1381` · 테스트 `:896-938` |
| Per-type report / Refusal question differs between conditions | 충족 | 거절 구역 `:1382-1411` · 테스트 `:896-938` |
| (본문) 유형별 위키 차이 | 충족(코드). 테스트의 판별력이 약하다 | `:1343`, `:1370-1377` · 테스트 `:1085`. 권고 1 |

### ask-replay-scorecard

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Per-question pass verdict / 13개 Scenario 전체 | 충족(r2 이후 바뀌지 않았다) | `verdict` `ask_replay.py:203-240` · 테스트 `test_ask_replay_script.py:1070`(금지 사실), `:1079`(필드 없음), 거절 계열 `:376-410`. 회귀 관문도 일치한다 |

### model-evidence-ablation

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Answer ends as a fallback · Source-only answer | 충족(기존) | 기존 테스트 |
| Answer lists the old and the new value | 충족 | 테스트 `test_conflict_turn_with_old_value_is_not_fact_correct`(`test_model_evidence_eval_script.py:793`) |
| Existing sample without types or forbidden facts | 충족 | 테스트 `test_old_rows_without_forbidden_keep_fact_result`(`:811`) |

## 새 회귀 점검

- `build_ingestion`의 분류 변경은 이 change 안의 함수에만 영향을 준다. 기존 재생의 `seed` 대기(`ask_replay._wait_for_jobs`, `ask_replay.py:959-981`)는 여전히 `_FAILED_JOB_STATES`(`:81`, `failed` 포함)를 쓴다. 그래서 이전 실험 흐름은 바뀌지 않았다.
- 기존 30문항 판정은 회귀 관문과 일치한다. 효과 구역은 등록에 `effect_criterion`이 있을 때만 그려지므로 이전 성적표도 그대로다(`test_view_without_criterion_has_no_effect_section` `:941`).
- `recovered_jobs`의 출력 형식이 r2의 `retries` 키에서 `api_retries`/`worker_attempts`로 바뀌었다. 이 필드는 r2에서 새로 생겼고, 실측 `ingestion.json`은 이 필드 이전 코드로 만들어졌다(`verification.md:56`). 그래서 읽는 쪽 회귀는 없다.

## 조치가 필요한 항목

없음. 아래는 판정을 바꾸지 않는 권고다.

1. **(권고) 유형별 위키 차이 테스트의 판별력** — `test_type_table_shows_wiki_difference_column`(`test_model_evidence_eval_script.py:1104-1106`)은 페이지 전체에서 문자열을 찾는다. 요약 표에도 같은 머리와 같은 값(`+1 · +1`)이 나오므로, 유형별 열을 지워도 이 테스트는 통과한다. 스크래치 점검 결과 유형별 구역 밖에서도 두 문자열이 각각 1회씩 나왔다. 제안: 단언 범위를 `page.index("유형별 위키 차이")`부터 `page.index("거절 문항 (효과")`까지로 좁힌다. 또는 두 유형을 섞어 유형별 값과 전체 값이 달라지게 한다(예: `conflict` +1, `multi_doc` 0 → 전체 +1, 유형별 `+1` / `+0`). 근거 Requirement: "Per-type wiki difference report … the wiki difference … broken down by question type". 코드는 맞게 구현돼 있어 스펙 미충족은 아니다.
2. **(관찰) `attempts > 1`에는 락 타임아웃으로 회수된 잡도 든다** — `reap_stale_jobs`는 `attempts`를 유지한 채 잡을 다시 큐에 넣는다(`0009_pipeline_ops.sql:21`). 그래서 한 번도 `failed`가 되지 않고 회수된 뒤 성공한 잡도 `worker_attempts`로 기록된다. 스펙 Scenario는 "failed once"를 말한다. 그렇지만 이렇게 더 기록되는 잡은 재생을 막지 않고 기록에만 남으므로, 스펙이 금지하는 동작은 아니다. 필요하면 docstring에 한 줄 적어 둔다.
3. **(관찰) 문서 흐름** — `tasks.md:55`(4.1)의 실행 순서에 `retry-dead`가 없다. `seed`는 `failed`를 보는 순간 "잡이 실패했다"로 멈춘다(`ask_replay.py:972-974`). 이는 기존 동작이고 재생을 막는다는 결과는 스펙과 같다. 다만 실측 절차를 다시 따라 할 사람을 위해 `seed` → (`retry-dead`) → `ingest-record` 순서를 적어 두면 좋다. 또 tasks.md 검증 명령의 `ruff check scripts apps/worker/tests`는 이 change와 무관한 두 파일 때문에 실패한다.

## 판정 근거

r2의 needs_fix 4건은 모두 코드 · 스펙 · 설계에서 닫혔다. 핵심이던 조치 1(워커 자동 재시도 복구 기록과 2xx만 세기)과 조치 2(`failed` → 미완료)는 구현과 테스트가 함께 들어갔다. DB 쪽 `attempts` 의미(claim에서 증가, `retry_dead_job`만 초기화)와도 맞는다. 스펙 문구 변경(실패 정의, 자동 재시도 Scenario, multi_doc WHEN)은 이미 내린 사용자 결정 1 · 2를 옮긴 것이라 범위 이탈이 아니다. 세 delta spec의 모든 Scenario는 코드 경로와 대응 테스트를 갖췄고, 검증 명령도 모두 새로 통과했다. 남은 것은 조치 3 테스트의 판별력이 약하다는 점 하나다. 해당 동작은 코드로 구현돼 있고 스크래치 점검으로도 확인했으며, 판정 단위인 Scenario가 아니라 Requirement 본문의 한 구절이다. r2도 이 항목만으로는 needs_fix로 보지 않았다. 그래서 `pass`로 판정하고, PR 전에 단언 범위를 좁히는 수정을 권한다.
