# Spec Conformance 리뷰 — eval-reliability r1

- 판정: needs_fix
- 대상: `git diff main` + untracked 파일 (base `a8280fa`, 커밋 전 작업 트리 `feat/eval-reliability`)
- 일시: 2026-11-08T13:32:58Z
- 범위: delta spec `ask-replay-reliability` · `ask-replay-scorecard`, tasks 1~5절. 6절(#244 유료 실측 · 문서)은 사용자 결정으로 범위 밖이라 판정하지 않는다.
- 실행 확인: `uv run pytest apps/worker/tests/test_ask_replay_script.py apps/worker/tests/test_retrieval_ablation_script.py apps/worker/tests/test_ask_replay_reliability_script.py -q` → 174 passed. 실제 #232 기록(`.worktrees/ablation-evidence-20261108/answer.json` · `retrieve.json`)으로 `report`를 오프라인 실행해 q06이 "질문 모호성 (자동: 검색 미적중)", harness 28/29, 알려진 실패 1 · 예상 밖 0으로 나오는 것을 확인했다.

## 시나리오 판정

### ask-replay-scorecard

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Refusal performance / Run with one unanswerable question | 충족 | `scripts/ask_replay.py` `refusal_split` · `summarize`의 `**refusal_split(rows)` · 테스트 `test_ask_replay_script.py` `test_refusal_split_reports_three_figures_and_keeps_the_pass_rate` (28/29 · 1/1 · 0 · 29/30) |
| Refusal performance / Answerable question refused | 충족 | `ask_replay.py` `is_false_refusal`(resolved + `is_refusal`) · 테스트 `test_answerable_question_refused_by_the_model_is_a_false_refusal` |
| Refusal performance / Answerable question ends in no evidence | 충족 | `is_false_refusal`의 `status == "no-evidence"` · 테스트 `test_answerable_question_ending_in_no_evidence_is_a_false_refusal` |
| Refusal performance / No unanswerable question asked | 충족 | `refusal_split`의 `refusal_correct = None if not unanswerable` · 화면 JS `refusal()`이 `refusal_asked===0`이면 "없음 (거절 문항 0개)" · 테스트 `test_correct_refusal_is_absent_not_zero_without_unanswerable_questions` |
| Refusal performance / Older result file | 충족 | `scorecard_line`의 옛 요약 재계산, `read_scorecard`가 결과 파일 행으로 `refusal_split` 재계산, 결과 파일 없으면 "-" · 테스트 `test_scorecard_line_rederives_the_split_for_an_old_summary` · `test_report_rederives_the_split_for_an_old_line_with_its_result_file`(성적표 파일 불변 확인) · `test_report_without_result_file_leaves_the_split_unknown` |
| (요구 본문) 화면이 정확한 거절 옆에 거절 문항 수를 보인다 | 충족 | 화면 열 "정확한 거절 (거절 문항)"과 `frac(correct, asked)` |
| Fixed inputs / Replay on the preserved ingestion | 충족 (코드 경로 기준) | `ask_replay.py` `snapshot_tables` · `SNAPSHOT_COLUMNS` · `collect_fixed_inputs`가 `eval_fingerprint.snapshot_inputs` 사용, `retrieval_ablation.py`의 `load_corpus`가 같은 `replay.snapshot_tables` 호출 · 테스트 `test_retrieval_ablation_script.py` `test_moved_snapshot_hash_matches_the_value_before_the_move`(이동 전 값 고정) · `test_ablation_and_replay_share_one_fingerprint_definition`. 실제 보존 수집과 `65809ec4…` 대조는 6.1 몫(범위 밖) |
| Fixed inputs / Retrieval scoring on the same ingestion | 충족 | `cmd_retrieval_eval`의 `collect_fixed_inputs(..., with_prompt=False)` → `record["fixed_inputs"]` · 테스트 `test_ask_and_retrieval_eval_share_the_snapshot_fingerprint` |
| Fixed inputs / Prompt cannot be read | 충족 | `collect_fixed_inputs`의 `answer_prompt_sha256 = UNKNOWN` 폴백 · 테스트 `test_unreadable_prompt_is_recorded_as_unknown_and_the_run_is_kept` |
| (요구 본문) 추가형 필드 · 기존 의미 불변 | 충족 | 테스트 `test_new_fields_do_not_change_old_comparison_output`. HTTP 오류 행에 `doc` 추가는 거절 문항을 답할 수 있는 문항으로 잘못 세지 않게 하는 추가형 필드(`test_unanswerable_question_ending_in_http_error_stays_unanswerable`) |

### ask-replay-reliability

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Repetition series / Three runs with identical fixed inputs | 충족 | `scripts/ask_replay_reliability.py:66-73` `SERIES_KEYS`(revision 제외), `:194-214` `check_series`, `run_summary`의 `revision` · Markdown 표 revision 열 `:531` · 테스트 `test_ask_replay_reliability_script.py:89` |
| Repetition series / One run from a different ingestion | 충족 | `:208-213` 다른 키 이름 표시 · 테스트 `:96` (`match="snapshot_sha256"`) |
| Repetition series / Run written before fingerprints were recorded | 충족 | `:144` `fingerprint_missing`, `:200-202` "고정 입력 지문이 없다", `:203-205` 값이 unknown이면 거부 · 테스트 `:106` · `:113` |
| Per-question stability / Question that passes in some runs | 충족 | `:240-248` `stability` · 테스트 `:128` |
| Per-question stability / Spread across runs | 충족 | `:251-283` 회차별 통과 수 · 최소 · 최대 · 평균 · `wilson_interval` `:220-228`, 독립 표본 아님 문구 `:517` · `LIMITATIONS` · 테스트 `:149` · `:164` |
| Per-question stability / Run stopped early | 부분 충족 | 시나리오 그대로(한 회차만 20에서 멈춤, 나머지 회차 완료)는 `:441-447`로 충족, 테스트 `:138`. 그러나 harness 회차의 `not_run` 행과 모든 회차가 일찍 멈춘 경우에 요구 본문이 깨진다 → 조치 1 · 2 |
| Execution path / Ablation record joins a series | 충족 | `:148-191` `ablation_run`(path `harness`), `:482-494` `http_only` · `all` 분리, `spread`의 `paths` · 테스트 `:209` |
| Execution path / Diagnostic condition offered | 충족 | `:157-161` · 테스트 `:220` (`source_onlyxbody`) |
| Execution path / Title-header condition offered | 충족 | `:157-161` · 테스트 `:220` (`bothxtitle_body`) |
| (요구 본문) 다른 실험 기록 거부 | 충족 | `:152-156` · 테스트 `:226` |
| Spending cap / No cap given | 충족 | `:733` `required=True`(argparse가 요청 전에 종료) · 테스트 `:572` (`_forbid_network`) |
| Spending cap / Cap reached in the second run | 충족 | `:649-662` 시작 전 검사, `:664-703` partial · not_run · reason `spend_cap`, 회차별 `cost_micros` · 테스트 `:590` · `:641` |
| (요구 본문) 루프백 아닌 대상 거부 | 충족 (API는 테스트, DB는 코드만) | `:627` API, `:629` `stack_url` · 테스트 `:580`(API만) |
| First broken stage / Gold document absent from retrieval | 충족 (HTTP 회차) | `:391-405`, `:318-350` · 테스트 `:253` |
| First broken stage / Gold document retrieved but answer wrong | 충족 | 테스트 `:257` |
| First broken stage / Turn ended in an HTTP error | 충족 | `:398` · 테스트 `:261` |
| First broken stage / Retrieval record from a different ingestion | 충족 | `:353-372` `pick_evidence` · 테스트 `:283` |
| First broken stage / Unanswerable question answered | 충족 | `:400-401` · 테스트 `:292` |
| (요구 본문) 실패 채널을 보고한 턴은 실행 장애 | 미충족 (harness 회차) | `:398`이 `missing_channels`만 본다. #232 답변 행은 같은 정보를 `failed_channels`로 기록한다(`scripts/retrieval_ablation.py` `turn_row`) → 조치 3 |
| (요구 본문) 단계별 회차별 개수 · 별도 검색 호출 한계 문구 | 충족 | `:460` `stage_counts`, `LIMITATIONS` `:97-98` |
| Human cause labels / Labeled question fails | 충족 | `:457-459`, Markdown `:565-566` "(자동: …)" · 테스트 `:334` · 실제 기록 테스트 `:463` |
| Human cause labels / Label without evidence | 충족 | `:306-307`, `cmd_report`가 `:611`에서 라벨을 읽고 `:617`에서야 출력 파일을 연다 · 테스트 `:383`(`evidence="  "`) |
| Human cause labels / Label for an unknown question | 충족 | `:302-303` · 테스트 `:387` (`q99`) |
| (요구 본문) 저장소의 라벨 파일 · 답변 본문 금지 | 충족 | `scripts/fixtures/ask_replay_labels.v1.json`, 허용 필드 제한 `:76` · `:298-301` · 테스트 `:405` |
| Known failures / Only the known failure fails | 충족 (회차 단위) | `:461` · 테스트 `:334`(분모 유지 1/2, 알려진 1 · 예상 밖 0) |
| Known failures / Known failure passes | 충족 | `:453-454`, Markdown `:571-574` · 테스트 `:350` |
| (요구 본문) 묶음 전체의 알려진 · 예상 밖 실패 개수 | 미충족 | 회차별 목록만 있고 묶음 합계가 없다 → 조치 4 |
| Report record / Output path exists | 충족 | `:591-592`(입력 읽기 전), `:617` `"x"` 모드 · 테스트 `:428` |
| Report record / Offline report | 충족 | `cmd_report` `:588-620`에 네트워크 호출 없음 · 테스트 `:437` · 실제 #232 기록 오프라인 실행 확인 |
| (요구 본문) 기록에 본문 · 워크스페이스 id 없음 | 충족 | 테스트 `:437` (답변 · 질문 표식 · `ws-secret` 부재) |

## 조치가 필요한 항목

1. **harness 회차의 `not_run` 행이 실패로 세진다** — 근거 Scenario: "Run stopped early" 및 요구 본문 "A question that was not asked in a run because that run stopped early MUST NOT be counted as a failure in that run and MUST be reported as not run". `scripts/retrieval_ablation.py` `run_answers`는 상한에 닿으면 남은 턴을 `{"status": "not_run", "cost_micros": 0}` 행으로 기록한다. `scripts/ask_replay_reliability.py:169-172` `ablation_run`은 이 행을 그대로 회차 행으로 넣고, `:448`의 `replay.verdict`가 이를 실패로, `refusal_split`이 `answerable_asked`에 포함한다. 재현: `bothxbody` 조건에 통과 행 q01과 `not_run` 행 q02를 둔 기록 → q02 outcomes `['fail']`, `stable_fail`, `unexpected_failures == ['q02']`, `answerable_asked == 2`. 제안: `ablation_run`에서 `status == "not_run"` 행을 회차 행에서 빼(미실행으로 남기고) 회귀 테스트를 더한다. 실제 #232 기록은 30턴 모두 `resolved`라 지금 값에는 영향이 없다.

2. **모든 회차가 일찍 멈추면 남은 문항이 보고서에서 사라진다** — 근거: 같은 요구 본문 "MUST be reported as not run". `:231-237` `question_order`가 문항 목록을 회차 행에서만 모은다. 재현: planned 30 · asked 20인 HTTP 회차 2개 → `questions`가 20개뿐이고 q21~q30은 미실행으로도 나오지 않는다(`stability_counts.not_run == 0`). 이 상황은 비용 상한 경로에서 흔하다: 첫 회차에서 상한에 닿으면 1회차 partial, 2 · 3회차 not_run이고 보고서에는 1회차가 물은 문항만 남는다. 제안: 문항 목록을 계획 문항(질문 fixture · `select_questions`나 회차의 계획 목록) 기준으로 만들고, 어느 회차에서도 묻지 않은 문항은 모든 회차에 `not_run`으로 표시한다. 테스트를 더한다.

3. **harness 회차의 채널 장애가 실행 장애로 판정되지 않는다** — 근거: 요구 본문 "execution failure when the turn ... reported a failed retrieval channel". `:398`은 `row.get("missing_channels")`만 본다. #232 답변 행은 Ask `meta.missing_channels`를 `failed_channels` 키로 저장한다(`scripts/retrieval_ablation.py` `turn_row`). 재현: `failed_channels=["source_vector"]`인 실패 harness 행과 상위 8 미적중 검색 기록 → 자동 단계가 `execution_failure`가 아니라 `retrieval_miss`. 함께 `:100-101` 한계 문장("그 회차의 답변 기록에는 턴별 채널 장애 필드가 없다")도 사실과 다르다. 제안: `automatic_stage`가 `missing_channels`와 `failed_channels`를 모두 보게 하거나 `ablation_run`에서 `failed_channels`를 `missing_channels`로 옮기고, 한계 문장을 고치고, harness 행 테스트를 더한다.

4. **묶음 전체의 알려진 · 예상 밖 실패 개수가 없다** — 근거: 요구 본문 "The report SHALL count, per run and over the series, known failures and unexpected failures separately". `:477-481`은 회차별 `known_failures` · `unexpected_failures` 목록만 남기고, `:484-503` 보고서 최상위와 Markdown `:514-581`에는 묶음 합계가 없다. 제안: 묶음 단위 개수(예: 모든 회차 합계, 또는 한 번이라도 예상 밖으로 실패한 문항 수)를 기록과 Markdown에 더하고 테스트에서 확인한다. 어떤 집계로 할지는 구현 선택이며 스펙 변경은 필요 없다.

참고(판정에 반영하지 않음):

- 루프백 검사는 DB 대상(`stack_url`, `:629`)도 코드로 막지만 테스트는 API 주소만 있다. 5.1의 Given이 API만 적고 있어 미검증 완료로 보지 않았다. 테스트 하나를 더하면 좋다.
- 결과의 `fixed_inputs.policy_versions`는 관측값이 없으면 `"unknown"`이 아니라 빈 목록이다(`finalize_fixed_inputs`). 회차가 생략되지 않고 묶음에서는 unknown으로 거부되므로(`:129-131`) 스펙 의도는 지켜진다고 보았다.
- 보고서 `questions[].label_evidence`에 라벨 근거 문자열이 복사된다. 현재 q06 근거는 답변 내용을 한 구절로 요약하고 있다("반품 검수 48시간으로 답했다"). 답변 본문 그대로는 아니어서 지적하지 않았지만, 라벨 근거를 참조(#번호 · 문서 경로) 위주로 쓰는 편이 "답변 본문 금지"와 더 잘 맞는다.

## 판정 근거

scorecard 스펙의 시나리오 8개는 모두 증거와 테스트로 충족됐고, reliability 스펙도 HTTP 회차 경로에서는 시나리오 대부분이 충족된다. 다만 요구 본문 중 세 곳이 코드와 어긋난다. (1) harness 회차의 미실행 행과 (2) 모든 회차가 멈춘 경우의 미실행 문항이 "멈춘 회차의 미실행은 실패가 아니고 미실행으로 보고한다"를 어기고, (3) harness 회차의 채널 장애가 실행 장애로 판정되지 않는다. 또 (4) 묶음 단위의 알려진 · 예상 밖 실패 개수가 빠졌다. 네 항목 모두 스펙 문구가 분명하고 스펙 범위 안에서 `scripts/ask_replay_reliability.py`만 고치면 해결되므로 `blocked`가 아니라 `needs_fix`다.
