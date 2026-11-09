# Spec Conformance 리뷰 — eval-reliability r3

- 판정: pass
- 대상: `git diff main` + untracked 파일 (base `a8280fa`, 커밋 전 작업 트리 `feat/eval-reliability`)
- 일시: 2026-11-08T13:41:55Z
- 범위: delta spec `ask-replay-reliability` · `ask-replay-scorecard`, tasks 1~5절. 6절(#244 유료 실측 · 문서)은 범위 밖이다.
- r2 이후 바뀐 파일: `scripts/ask_replay.py` · `scripts/ask_replay_reliability.py` · `apps/worker/tests/test_ask_replay_reliability_script.py` (수정 시각 기준. 스펙 · tasks · 나머지 스크립트는 r2 때와 같다)
- 실행 확인 (모두 이번 라운드에 새로 실행):
  - `uv run pytest apps/worker/tests/test_ask_replay_script.py apps/worker/tests/test_retrieval_ablation_script.py apps/worker/tests/test_ask_replay_reliability_script.py -q` → 184 passed (r2 182 + 새 테스트 2)
  - `openspec validate eval-reliability --strict` → valid
  - 변경 파일 7개 대상 `ruff check` → 통과, 수정된 3개 `ruff format --check` → 통과
  - 실제 #232 기록(`.worktrees/ablation-evidence-20261108/answer.json` · `retrieve.json`) + 라벨 파일로 `report` 오프라인 실행 → q06 "질문 모호성 (자동: 검색 미적중)", "묶음 전체 실패: 알려진 실패 1회 (q06) · 예상 밖 실패 0회 (-)", 안정 통과 29 · 안정 실패 1 · 미실행 0. r2와 같다
  - 종단 재현 `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/6c51fee5-87d7-4363-97d4-934fc9ebfb8f/scratchpad/probe_r3.py` — 손으로 필드를 넣지 않고 실제 `replay.select_questions`(앞 4개 문서만 수집한 state) → `replay.build_result` → 결과 파일 → `report` CLI 경로를 탄다

## r2 지적 사항 확인

| r2 항목 | 결과 | 증거 |
| --- | --- | --- |
| 1. 계획 문항이 fixture 접두가 아니면 모든 회차가 멈췄을 때 미실행 문항이 바뀌어 보고됨 | 해결 | `scripts/ask_replay.py:1229` `build_result`가 `planned_question_ids`를 남긴다(계획 문항 = `select_questions` 결과, `cmd_ask` `:1253` · `cmd_repeat` `ask_replay_reliability.py:689`). `ask_replay_reliability.py:142` `http_run`이 이를 `planned_ids`로 읽고, `:185` `ablation_run`은 `not_run` 행을 포함한 전체 행 id를 쓴다. `:237-256` `question_order`가 회차의 `planned_ids`를 먼저 쓰고, fixture 채우기는 `planned_ids`가 없는 회차(`:249` `legacy`)의 계획 개수까지만 한다. 테스트 `test_ask_replay_reliability_script.py:751`(계획 q01·q02·q05·q27·q28·q30, 3문항에서 멈춤 → 보고 문항 = 계획, 미실행 = q27·q28·q30) · `:771`(`build_result`가 id 목록을 남김). probe_r3: 계획 18문항(q01~q15·q27·q28·q30)과 보고 문항이 정확히 일치, 미실행 q11~q15·q27·q28·q30, 예상 밖 실패 0. 하네스 부분 실행(5문항 실행 · 13문항 `not_run`)도 보고 문항 = 계획 |
| 참고: `build_report`를 `fixture_ids` 없이 부르면 남은 문항이 사라짐 | 해결 | 새 형식 결과와 #232 기록은 `planned_ids`를 갖고 있어 `fixture_ids` 없이도 계획 문항 전체가 나온다(`:246`) |
| 참고: `failed_channels` 테스트가 `http_run` 경로로 돎 | 미반영(판정 무관) | r2 probe3 D로 `ablation_run` 경로 동작은 이미 확인했다 |

### 옛 결과의 대체 경로가 스펙 위반인가

호출자가 물은 점이다. 결론: **판정에 반영할 위반이 아니다.**

- 대체 경로(fixture 순서로 계획 개수까지 채우기)는 `planned_question_ids`가 없는 HTTP 결과에서만 탄다. 그런데 `fixed_inputs`가 없는 결과는 `check_series`(`:200-213`)가 "고정 입력 지문이 없다"로 묶음에서 거부한다 — 스펙 시나리오 "Run written before fingerprints were recorded"가 요구하는 동작이다.
- `main`의 `scripts/ask_replay.py`는 `fixed_inputs`를 쓰지 않는다(`git show main:scripts/ask_replay.py`에 해당 키 없음). 이 브랜치는 아직 커밋도 없다. 따라서 "`fixed_inputs`는 있고 `planned_question_ids`는 없는" 결과는 출시된 어떤 버전도 만들지 않으며, 이 브랜치의 r2 이전 작업 트리 산출물이나 손으로 만든 파일(r2 probe3 C)뿐이다. #232 하네스 기록은 항상 `ablation_run` `:185`로 `planned_ids`를 갖는다.
- 그 좁은 경우에도 대체 경로는 미실행 문항을 **실패로 세지는 않는다**(행이 없는 문항은 `:464-469`에서 `not_run`). 어긋날 수 있는 것은 "어느 문항이 미실행인가"의 이름뿐이며, 그 한계는 docstring `:240-242`에 적혀 있다.
- 즉 스펙이 다루는 입력(지문이 있는 새 결과 · #232 기록)에서는 요구 본문 "A question that was not asked in a run because that run stopped early MUST NOT be counted as a failure ... and MUST be reported as not run"이 충족되고, 대체 경로는 스펙이 이미 거부하는 옛 결과와 미출시 중간 산출물에만 남는다.

## 시나리오 판정

### ask-replay-scorecard

r2 이후 `ask_replay.py`의 변경은 `build_result`에 `planned_question_ids` 한 필드를 더한 것뿐이다. 추가형 필드이며 기존 필드의 의미를 바꾸지 않는다(요구 본문 "additive and MUST NOT change the meaning of existing result fields"). `scorecard_line`(`:360`)은 이 필드를 읽지 않으므로 성적표 줄도 그대로다. 시나리오 전체를 다시 대조했고 관련 테스트가 모두 통과한다.

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Refusal performance / Run with one unanswerable question | 충족 | `refusal_split` · `summarize` · 테스트 `test_refusal_split_reports_three_figures_and_keeps_the_pass_rate` |
| Refusal performance / Answerable question refused | 충족 | `is_false_refusal` · 테스트 `test_answerable_question_refused_by_the_model_is_a_false_refusal` |
| Refusal performance / Answerable question ends in no evidence | 충족 | 테스트 `test_answerable_question_ending_in_no_evidence_is_a_false_refusal` |
| Refusal performance / No unanswerable question asked | 충족 | `refusal_correct = None`, 화면 "없음 (거절 문항 0개)" · 테스트 `test_correct_refusal_is_absent_not_zero_without_unanswerable_questions` |
| Refusal performance / Older result file | 충족 | 테스트 `test_scorecard_line_rederives_the_split_for_an_old_summary` · `test_report_rederives_the_split_for_an_old_line_with_its_result_file` · `test_report_without_result_file_leaves_the_split_unknown` |
| Fixed inputs / Replay on the preserved ingestion | 충족 (코드 경로 기준) | 공용 `scripts/eval_fingerprint.py` `snapshot_inputs` · 테스트 `test_moved_snapshot_hash_matches_the_value_before_the_move` · `test_ablation_and_replay_share_one_fingerprint_definition`. 실제 `65809ec4…` 대조는 6.1 몫(범위 밖) |
| Fixed inputs / Retrieval scoring on the same ingestion | 충족 | 테스트 `test_ask_and_retrieval_eval_share_the_snapshot_fingerprint` |
| Fixed inputs / Prompt cannot be read | 충족 | 테스트 `test_unreadable_prompt_is_recorded_as_unknown_and_the_run_is_kept` |
| (요구 본문) 얻지 못한 값은 unknown · 추가형 필드 | 충족 | 정책 버전 `policies or UNKNOWN` · 테스트 `test_ask_replay_script.py:1049`. 새 `planned_question_ids`도 추가형 · 테스트 `test_ask_replay_reliability_script.py:771` |

### ask-replay-reliability

줄 번호는 `scripts/ask_replay_reliability.py`, 테스트는 `apps/worker/tests/test_ask_replay_reliability_script.py` 기준이다.

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Repetition series / Three runs with identical fixed inputs | 충족 | `check_series` `:200-220`, Markdown revision 열 `:565` · 테스트 `:90` |
| Repetition series / One run from a different ingestion | 충족 | `:214-219` · 테스트 `:97` |
| Repetition series / Run written before fingerprints were recorded | 충족 | `:146` `fingerprint_missing` · `:206-207` · 테스트 `:107` · `:114` |
| Per-question stability / Question that passes in some runs | 충족 | `stability` `:259-267` · 테스트 `:129` |
| Per-question stability / Spread across runs | 충족 | `spread` `:291`, `wilson_interval` `:226-234`, 문구 `:551` · 테스트 `:150` · `:165` |
| Per-question stability / Run stopped early | 충족 | 한 회차만 멈춤 `:464-469` · 테스트 `:139`. 하네스 `not_run` 행 `:173-177` · 테스트 `:672`. 모든 회차가 멈춘 전체 수집 · 테스트 `:683`. 일부 문서 수집에서 모든 회차가 멈춤 `:237-256` · 테스트 `:751` · probe_r3 |
| Execution path / Ablation record joins a series | 충족 | `ablation_run` `:150-197`, `spread` http_only `:512-516` · 테스트 `:210` |
| Execution path / Diagnostic condition offered | 충족 | `:159-163` · 테스트 `:222` |
| Execution path / Title-header condition offered | 충족 | `:159-163` · 테스트 `:222` |
| (요구 본문) 다른 실험 기록 거부 | 충족 | `:154-158` · 테스트 `:227` |
| Spending cap / No cap given | 충족 | `:780` `required=True` · 테스트 `:573` |
| Spending cap / Cap reached in the second run | 충족 | `before` `:696-709`, 회차 루프 `:711-750` · 테스트 `:591` · `:642` |
| (요구 본문) 루프백 아닌 API · DB 거부 | 충족 | `:674` · `:676` · 테스트 `:581` · `:729` |
| First broken stage / Gold document absent from retrieval | 충족 | `automatic_stage` `:410-429` · 테스트 `:254` |
| First broken stage / Gold document retrieved but answer wrong | 충족 | 테스트 `:258` |
| First broken stage / Turn ended in an HTTP error | 충족 | 테스트 `:262` |
| First broken stage / Retrieval record from a different ingestion | 충족 | `pick_evidence` `:372` · 테스트 `:284` |
| First broken stage / Unanswerable question answered | 충족 | 테스트 `:293` |
| (요구 본문) 실패 채널을 보고한 턴은 실행 장애 | 충족 | `:417-418` (`missing_channels` 또는 `failed_channels`) · 테스트 `:267` · `:704` |
| (요구 본문) 단계별 회차별 개수 · 별도 검색 호출 한계 문구 | 충족 | `:482` · `:500`, `LIMITATIONS` `:97-98` |
| Human cause labels / Labeled question fails | 충족 | `:478-481`, Markdown `:606-607` · 테스트 `:335` · 실제 기록 테스트 `:464` · 실제 #232 오프라인 실행 |
| Human cause labels / Label without evidence | 충족 | `load_labels` `:308`, `cmd_report`가 `:652`에서 라벨을 읽고 `:664`에서야 출력 파일을 연다 · 테스트 `:394` |
| Human cause labels / Label for an unknown question | 충족 | `load_labels` · 테스트 `:394` |
| (요구 본문) 저장소 라벨 파일 · 답변 본문 금지 | 충족 | `scripts/fixtures/ask_replay_labels.v1.json` · 테스트 `:406` |
| Known failures / Only the known failure fails | 충족 | `:483` · 테스트 `:335` |
| Known failures / Known failure passes | 충족 | `:475-476`, `:526-528`, Markdown `:612-615` · 테스트 `:351` · `:710` |
| (요구 본문) 회차별 · 묶음 전체 알려진 · 예상 밖 실패 개수 | 충족 | 회차별 `:501-502`, 묶음 `:519-529`, Markdown `:569` · `:583-589` · 테스트 `:710` |
| Report record / Output path exists | 충족 | `:632-633`, `:664` `"x"` · 테스트 `:429` |
| Report record / Offline report | 충족 | `cmd_report` `:629-667`에 네트워크 호출 없음 · 테스트 `:438` · 실제 #232 오프라인 실행 |
| (요구 본문) 기록에 본문 · 워크스페이스 id 없음 | 충족 | 테스트 `:438`. `planned_question_ids`는 HTTP 결과 파일의 필드이고 보고서 기록에는 문항 id만 들어간다 |

## 조치가 필요한 항목

없음.

참고(판정에 반영하지 않음):

- 같은 고정 입력이지만 `--limit`이 다른 결과 파일을 한 묶음에 넣으면, 한 회차의 계획에만 있는 문항이 다른 회차에서 `not_run`으로 나온다(그 회차는 일찍 멈춘 것이 아니라 애초에 계획하지 않았다). 실패로 세지 않으므로 스펙 위반은 아니며 r2에도 있던 동작이다. 묶음 키에 계획 문항 집합을 넣을지는 6절 실측 후 판단할 일이다.
- `planned_question_ids`가 없는 결과에 대한 fixture 채우기는 스펙이 거부하는 옛 결과와 미출시 중간 산출물에서만 닿는 경로다(위 「옛 결과의 대체 경로」). 지우려면 `planned_ids`가 없으면 행 id만 쓰도록 단순화할 수 있으나 필수는 아니다.

## 판정 근거

r2의 남은 1건(일부 문서만 수집한 계획에서 모든 회차가 멈추면 엉뚱한 미실행 문항을 보고함)은 결과 파일에 계획 문항 id를 추가형 필드로 남기고 보고서가 그것을 우선하도록 고쳐 해결됐다. 수정은 실제 `select_questions` → `build_result` → `report` 경로에서도 계획 문항과 보고 문항이 일치함을 종단 재현으로 확인했다. 옛 결과의 대체 경로는 스펙이 이미 묶음에서 거부하는 입력(지문 없는 결과)과 출시되지 않은 중간 산출물에만 남고, 그 경우에도 미실행 문항을 실패로 세지 않으므로 위반으로 보지 않았다. 두 delta spec의 모든 Scenario와 요구 본문을 다시 대조했고 회귀는 없으며, tasks 1~5절의 `- [x]`는 대응 코드와 테스트를 갖는다. 따라서 `pass`다.
