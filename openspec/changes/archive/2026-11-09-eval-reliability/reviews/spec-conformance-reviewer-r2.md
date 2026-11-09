# Spec Conformance 리뷰 — eval-reliability r2

- 판정: needs_fix
- 대상: `git diff main` + untracked 파일 (base `a8280fa`, 커밋 전 작업 트리 `feat/eval-reliability`)
- 일시: 2026-11-08T13:38:04Z
- 범위: delta spec `ask-replay-reliability` · `ask-replay-scorecard`, tasks 1~5절. 6절(#244 유료 실측 · 문서)은 사용자 결정으로 범위 밖이다.
- 실행 확인:
  - `uv run pytest apps/worker/tests/test_ask_replay_script.py apps/worker/tests/test_retrieval_ablation_script.py apps/worker/tests/test_ask_replay_reliability_script.py -q` → 182 passed (r1 174 + 새 테스트 8)
  - `openspec validate eval-reliability --strict` → valid
  - 변경 파일 7개 대상 `ruff check` → 통과 (저장소 전체의 43건은 이번 변경과 무관한 `scripts/benchmark_retrieval.py` · `scripts/generate_retrieval_benchmark_corpus.py`)
  - 실제 #232 기록(`.worktrees/ablation-evidence-20261108/answer.json` · `retrieve.json`)으로 `report` 오프라인 실행 → harness 28/29, q06 "질문 모호성 (자동: 검색 미적중)", "묶음 전체 실패: 알려진 실패 1회 (q06) · 예상 밖 실패 0회 (-)", 미실행 0. r1 결과와 같고 묶음 합계 줄만 늘었다
  - 재현 스크립트 `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/6c51fee5-87d7-4363-97d4-934fc9ebfb8f/scratchpad/probe3.py`(CLI와 같게 `fixture_ids`를 넘김)

## r1 지적 사항 확인

| r1 항목 | 결과 | 증거 |
| --- | --- | --- |
| 1. harness 회차의 `not_run` 행이 실패로 세짐 | 해결 | `scripts/ask_replay_reliability.py:170-176`이 `status == "not_run"` 행을 회차 행에서 빼고 `:183` `planned = len(all_rows)`. 테스트 `apps/worker/tests/test_ask_replay_reliability_script.py:672` (q02 outcomes `["not_run"]`, `answerable_asked == 1`). probe3 A: `unexpected_failures == []` |
| 2. 모든 회차가 일찍 멈추면 남은 문항이 사라짐 | 부분 해결 | `:235-252` `question_order`가 fixture 순서로 `planned` 최대값까지 보태고, `cmd_report` `:657`이 fixture id를 넘긴다. 전체 수집(또는 `--limit` 접두 선택)에서는 맞다: 테스트 `:683`, probe3 B(30문항, 미실행 10). 그러나 계획 문항이 fixture의 접두가 아니면 틀린다 → 조치 1 |
| 3. harness 채널 장애가 실행 장애로 판정되지 않음 | 해결 | `:413-416`이 `missing_channels` 또는 `failed_channels`를 본다. 테스트 `:704`. 한계 문장 `:100-102`는 사실과 맞다: 실제 #232 `answer.json`의 `bothxbody` 30행에는 `failed_channels` 키가 없다(기록 revision `016ad7b`, 필드는 그 뒤 `a8280fa`의 `turn_row`에서 생김). probe3 D: `ablation_run`을 거친 harness 행 `failed_channels=["source_vector"]` → `execution_failure` |
| 4. 묶음 전체 알려진 · 예상 밖 실패 개수 없음 | 해결 | `:514-525` `series_failures`(회차 합 개수, 서로 다른 문항, 통과한 알려진 실패), Markdown `:579-585`. 테스트 `:710` (2회 · 1회, Markdown 문구까지 확인) |
| 참고: DB 루프백 거부 테스트 | 반영 | `:672` `cmd_repeat`의 `stack` 검사, 테스트 `:729` (`https://abc.supabase.co` → 요청 없이 "루프백") |
| 참고: 정책 버전 미관측 시 빈 목록 | 반영 | `scripts/ask_replay.py:1153-1165` `policies or UNKNOWN`, 테스트 `apps/worker/tests/test_ask_replay_script.py:1049`. 묶음에서는 `http_run` `:130-132`가 리스트가 아니므로 unknown → 거부, 테스트 `test_ask_replay_reliability_script.py:742` (`match="policy_version"`). 다른 소비처(`ask_replay.py:756`)는 retrieval 기록의 필드라 영향 없음 |
| 참고: 라벨 근거 문자열 | 미반영(의도) | 판정에 반영하지 않음. r1 의견 그대로 |

## 시나리오 판정

### ask-replay-scorecard

이번 라운드의 수정은 `ask_replay.py`에서 `finalize_fixed_inputs`의 미관측 정책 버전 표기만 바꿨다. 시나리오 전체를 다시 대조했고 r1 증거가 그대로 유효하다(관련 테스트 모두 통과).

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Refusal performance / Run with one unanswerable question | 충족 | `ask_replay.py` `refusal_split` · `summarize` · 테스트 `test_refusal_split_reports_three_figures_and_keeps_the_pass_rate` |
| Refusal performance / Answerable question refused | 충족 | `is_false_refusal` · 테스트 `test_answerable_question_refused_by_the_model_is_a_false_refusal` |
| Refusal performance / Answerable question ends in no evidence | 충족 | 테스트 `test_answerable_question_ending_in_no_evidence_is_a_false_refusal` |
| Refusal performance / No unanswerable question asked | 충족 | `refusal_correct = None` · 화면 "없음 (거절 문항 0개)" · 테스트 `test_correct_refusal_is_absent_not_zero_without_unanswerable_questions` |
| Refusal performance / Older result file | 충족 | 테스트 `test_scorecard_line_rederives_the_split_for_an_old_summary` · `test_report_rederives_the_split_for_an_old_line_with_its_result_file` · `test_report_without_result_file_leaves_the_split_unknown` |
| Fixed inputs / Replay on the preserved ingestion | 충족 (코드 경로 기준) | 공용 `eval_fingerprint.snapshot_inputs` · 테스트 `test_moved_snapshot_hash_matches_the_value_before_the_move` · `test_ablation_and_replay_share_one_fingerprint_definition`. 실제 `65809ec4…` 대조는 6.1 몫(범위 밖) |
| Fixed inputs / Retrieval scoring on the same ingestion | 충족 | 테스트 `test_ask_and_retrieval_eval_share_the_snapshot_fingerprint` |
| Fixed inputs / Prompt cannot be read | 충족 | 테스트 `test_unreadable_prompt_is_recorded_as_unknown_and_the_run_is_kept` |
| (요구 본문) 얻지 못한 값은 unknown | 충족 (r1보다 개선) | 정책 버전도 이제 `unknown` — `ask_replay.py:1164` · 테스트 `test_ask_replay_script.py:1049` |

### ask-replay-reliability

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Repetition series / Three runs with identical fixed inputs | 충족 | `ask_replay_reliability.py:66-73` `SERIES_KEYS`, `:198-218` `check_series`, Markdown revision 열 `:561` · 테스트 `:90` |
| Repetition series / One run from a different ingestion | 충족 | `:212-217` · 테스트 `:97` |
| Repetition series / Run written before fingerprints were recorded | 충족 | `:145` · `:204-205` · 테스트 `:107` · `:114` |
| Per-question stability / Question that passes in some runs | 충족 | `:255-263` · 테스트 `:129` |
| Per-question stability / Spread across runs | 충족 | `:266-298`, `:224-232`, 문구 `:547` · 테스트 `:150` · `:165` |
| Per-question stability / Run stopped early | 충족 (시나리오) · 요구 본문 일부 미충족 | 시나리오 그대로(한 회차만 멈춤)는 `:458-465` · 테스트 `:139`. harness 미실행 행(`:672`)과 모든 회차가 멈춘 전체 수집(`:683`)도 이제 맞다. 계획 문항이 fixture 접두가 아닌 수집에서 모든 회차가 멈추면 요구 본문이 깨진다 → 조치 1 |
| Execution path / Ablation record joins a series | 충족 | `:149-195`, `:500-512` · 테스트 `:210` |
| Execution path / Diagnostic condition offered | 충족 | `:158-162` · 테스트 `:222` |
| Execution path / Title-header condition offered | 충족 | `:158-162` · 테스트 `:222` |
| (요구 본문) 다른 실험 기록 거부 | 충족 | `:153-157` · 테스트 `:227` |
| Spending cap / No cap given | 충족 | `:776` `required=True` · 테스트 `:573` |
| Spending cap / Cap reached in the second run | 충족 | `:692-705`, `:707-746` · 테스트 `:591` · `:642` |
| (요구 본문) 루프백 아닌 API · DB 거부 | 충족 | `:670` · `:672` · 테스트 `:581` · `:729` |
| First broken stage / Gold document absent from retrieval | 충족 | `:406-422` · 테스트 `:254` |
| First broken stage / Gold document retrieved but answer wrong | 충족 | 테스트 `:258` |
| First broken stage / Turn ended in an HTTP error | 충족 | `:415` · 테스트 `:262` |
| First broken stage / Retrieval record from a different ingestion | 충족 | `:368-403` · 테스트 `:284` |
| First broken stage / Unanswerable question answered | 충족 | `:417-418` · 테스트 `:293` |
| (요구 본문) 실패 채널을 보고한 턴은 실행 장애 | 충족 | `:413-416` · 테스트 `:267`(HTTP) · `:704`(`failed_channels`) |
| (요구 본문) 단계별 회차별 개수 · 별도 검색 호출 한계 문구 | 충족 | `:478` · `:496`, `LIMITATIONS` `:97-98` |
| Human cause labels / Labeled question fails | 충족 | `:475-477`, Markdown `:602-603` · 테스트 `:335` · 실제 기록 테스트 `:464` |
| Human cause labels / Label without evidence | 충족 | `:321-322`, `cmd_report`가 `:648`에서 라벨을 읽고 `:660`에서야 출력 파일을 연다 · 테스트 `:394` |
| Human cause labels / Label for an unknown question | 충족 | `:317-318` · 테스트 `:394` |
| (요구 본문) 저장소 라벨 파일 · 답변 본문 금지 | 충족 | `scripts/fixtures/ask_replay_labels.v1.json`, `:76` · `:313-316` · 테스트 `:406` |
| Known failures / Only the known failure fails | 충족 | `:479` · 테스트 `:335` |
| Known failures / Known failure passes | 충족 | `:471-472`, `:522-524`, Markdown `:608-611` · 테스트 `:351` · `:710` |
| (요구 본문) 회차별 · 묶음 전체 알려진 · 예상 밖 실패 개수 | 충족 | 회차별 `:497-498`, 묶음 `:514-525`, Markdown `:565` · `:579-585` · 테스트 `:710` |
| Report record / Output path exists | 충족 | `:628-629`, `:660` `"x"` · 테스트 `:429` |
| Report record / Offline report | 충족 | `cmd_report` `:625-663`에 네트워크 호출 없음 · 테스트 `:438` · 실제 #232 기록 오프라인 실행 |
| (요구 본문) 기록에 본문 · 워크스페이스 id 없음 | 충족 | 테스트 `:438`. 새 `series_failures`는 문항 id만 담는다 |

## 조치가 필요한 항목

1. **계획 문항이 fixture 접두가 아니면 모든 회차가 멈췄을 때 미실행 문항이 바뀌어 보고된다** — r1 조치 2의 남은 부분. 근거: 요구 본문 "A question that was not asked in a run because that run stopped early MUST NOT be counted as a failure in that run and MUST be reported as not run".
   `question_order`(`scripts/ask_replay_reliability.py:235-252`)는 계획 문항 *개수*(`planned`)만 알고 *어떤 문항인지*는 모른 채 fixture 순서로 채운다. 그런데 계획 문항은 `select_questions`(`scripts/ask_replay.py:1103-1113`)가 수집하지 않은 문서의 질문을 빼서 만든다. `seed --limit-docs`(`scripts/ask_replay.py:956` · `:1458`)로 앞쪽 문서만 수집하면 계획 문항이 fixture의 접두가 아니게 된다. `cmd_repeat`에서는 첫 회차가 상한에 닿으면 남은 회차가 모두 미실행이 되므로, "모든 회차가 일찍 멈춘" 상황은 첫 회차 상한 도달과 같다.
   재현(probe3 C): 실제 fixture, `--limit-docs 4`(delivery · warehouse · safety · billing)의 계획 18문항 = q01~q15 · q27 · q28 · q30. 두 회차가 10문항에서 멈춤 → 보고된 문항은 q01~q18. **계획됐지만 묻지 못한 q27 · q28 · q30(거절 문항 포함)은 사라지고, 계획에 없던 q16~q18이 미실행으로 나온다.**
   테스트 `test_unseeded_fixture_questions_are_not_padded_beyond_the_plan`(`:698`)은 이름과 달리 개수 상한만 확인하고 이 경우는 다루지 않는다.
   제안: `build_result`(`scripts/ask_replay.py:1209-1231`)에 계획 문항 id 목록을 더한다(예: `planned_question_ids`. 추가형 필드라 scorecard 스펙의 "additive" 조건을 지킨다). `http_run`이 그 목록을 읽고, `ablation_run`은 `all_rows`의 id를 쓰고, `question_order`는 회차들의 계획 id를 우선한다. 지금의 fixture 채우기는 그 필드가 없는 옛 결과의 폴백으로만 남긴다. `--limit-docs`처럼 계획이 fixture 접두가 아닌 경우의 회귀 테스트를 더한다. 스펙은 바꿀 필요가 없다.

참고(판정에 반영하지 않음):

- `test_harness_failed_channel_is_an_execution_failure`(`:704`)는 `_stage` 헬퍼를 통해 `http_run` 경로로 돈다. `ablation_run`이 `verdict` · `condition`만 지우므로 `failed_channels`는 그대로 남고, probe3 D로 harness 경로에서도 `execution_failure`가 나오는 것을 확인했다. `ablation_run`을 거치는 테스트로 바꾸면 의도가 더 분명해진다.
- `build_report`의 `fixture_ids` 기본값이 `None`이라, 라이브러리로 직접 부르면서 이를 빼면 r1 조치 2의 증상(모든 회차가 멈추면 남은 문항이 사라짐)이 그대로 난다. 진입점 `cmd_report`는 항상 넘기므로(`:657`) 판정에는 반영하지 않았다. 조치 1의 계획 id 방식으로 고치면 함께 해결된다.

## 판정 근거

r1의 미충족 4건 중 3건(harness 미실행 행, harness 채널 장애, 묶음 합계)과 참고 2건은 코드와 테스트로 해결됐고, 수정 때문에 다른 시나리오가 깨지지는 않았다. scorecard 스펙 8개 시나리오와 reliability 스펙의 시나리오도 모두 충족된다. 남은 1건은 r1 조치 2가 일부만 해결된 것이다. 전체 수집이나 `--limit` 접두 선택에서는 맞지만, 지원하는 `seed --limit-docs` 수집에서 첫 회차가 상한에 닿으면 미실행으로 보고할 문항이 틀린다(계획 문항이 빠지고 계획 밖 문항이 들어간다). 스펙 문구는 분명하고, 결과에 계획 id를 추가형 필드로 남겨 보고서가 읽게 하면 스펙 범위 안에서 코드만으로 해결되므로 `blocked`가 아니라 `needs_fix`다. 리뷰 게이트 상한상 다음이 마지막 라운드(r3)다.
