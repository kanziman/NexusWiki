# Spec Conformance 리뷰 — cheap-model-evidence-ablation r1

- 판정: needs_fix
- 대상: `ceaa4ab` 위 미커밋 작업 트리 (`scripts/model_evidence_eval.py` · `scripts/model_evidence_run.sh` 신규, `scripts/ask_replay_serve.sh` · `docs/ops/ask-sample-replay.md` 수정, `apps/worker/tests/test_model_evidence_eval_script.py` 신규)
- 일시: 2026-11-09T11:15:00Z
- 검증: `uv run pytest apps/worker/tests/test_model_evidence_eval_script.py -q` → 27 passed (새로 실행)
- 참고: 이 세션에서는 훅 때문에 `git diff`를 쓸 수 없어서 변경 파일 원본을 직접 읽어 대조했다. 실측 원본 `.worktrees/model-evidence-20261109/`에서는 `scoreboard.jsonl`과 `runs/*.json`만 읽었고 `state.json`은 열지 않았다.

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Fixed ingestion / Snapshot matches the reused retrieval record | 충족 (테스트 간접) | `Harness.__init__`가 실제 스냅샷 · 청크 경계 · fixture · 질의 벡터 해시를 등록값과 대조한다 `scripts/model_evidence_eval.py:1061-1072`. 실행 기록이 `fixed_inputs` · `fixed_inputs_sha256` · `answer_prompt_sha256`을 싣는다 `:516-518`. 테스트는 비교 함수만 본다 `tests/...:102-104`. 실측 9개 실행 기록의 (프롬프트, 고정 입력, 등록) 해시 조합은 하나뿐이었다 |
| Fixed ingestion / Stack was re-ingested | 충족 (테스트 간접) | 불일치하면 `run_turn`이 호출되기 전에 `SystemExit`로 다른 키 이름을 낸다 `:1070-1072`. probe와 run 모두 Harness를 먼저 만든다 `:1221`, `:1294`. 테스트 `tests/...:102-104` |
| Served model / Worker serves another model | 부분 충족 | 분류와 중단은 된다: `enrich_turn` `:366-373`, `run_condition_turns` `:489-491`, 테스트 `tests/...:116-133`, `:303-329`. 다만 중단 뒤 남은 행에 `verdict`가 없어서 `summarize_rows`가 `KeyError`를 던진다(조치 1). 그러면 측정 장애 턴이 든 조건 전체가 실행 기록과 성적표에서 빠진다. 아래 「관찰」 2도 본다 |
| Pre-registration / Registration edited after creation | 충족 | `check_registration` `:202-208`. `cmd_probe` `:1212`과 `cmd_run` `:1283`이 유료 호출 전에 검사한다. 테스트 `tests/...:89-94` |
| Pre-registration / Run without a cap | 충족 | 등록 거부 `:163-164`, 로드 때도 거부 `:209-211`. 테스트 `tests/...:97-99` |
| Probe / Probe costs fit three rounds | 충족 | `plan_rounds` `:274-328`. 테스트 `tests/...:222-226` |
| Probe / Probe is refused by the provider | 충족 (테스트는 변형만) | 상태가 `resolved` · `fallback`이 아니면 제외한다 `:245-247`. 제외 사유를 적고 남은 모델로 계획한다 `:293-301`. 테스트는 모델 불일치 변형만 있다 `tests/...:178-195`. 실행 장애 상태(`error`)를 직접 다루는 테스트는 없다 |
| Probe / Probe answer is truncated | 충족 | `build_probe_record` `:264`, 계획에 남는지 `tests/...:198-203` |
| Round-major / Cap reached in round three | **미충족** | 턴 직전 상한 검사와 `not_run` 표시는 `:466-485`에 있다(테스트 `tests/...:260-300`). 그러나 (a) `not_run` 행에 `verdict`가 없어 `summarize_rows` `:407`, `:421`, `:431`이 `KeyError`를 던진다. 직접 재현했다: `rows = run_condition_turns(...)` → `summarize_rows(rows, "both")`에서 `KeyError 'verdict'`. 결과적으로 멈춘 조건의 행과 줄이 기록되지 않는다. (b) 아직 시작하지 않은 실행(같은 회차의 남은 모델 · 다음 회차)은 어디에도 `not_run`으로 남지 않는다. `model_evidence_run.sh:69-73`은 그냥 종료한다. 모델 간 비교에서 부분 회차를 빼는 규칙은 맞다 `:666-674`, 테스트 `tests/...:414-449` |
| Round-major / A round is started out of order | 충족 | `check_run_order` `:336-344`. 테스트 `tests/...:240-248` |
| Per-turn verdicts / Answer ends as a fallback | 충족 | `repair_attempted` · `fallback` `:379-380`. 사실 포함은 `citations.text`를 우선하는 `answer_text` 본문의 `keyword_hit`로 판정하고(`scripts/ask_replay.py:109-118`), `counts_for_fact` `:403-411`가 분모에 넣는다. 테스트 `tests/...:136-148` |
| Per-turn verdicts / Source-only answer | 충족 | `answer_verdict` `scripts/retrieval_ablation.py:1141-1147`(`dual_citation: None`). 진단 표시 `:423`, `:1322`. 테스트 `tests/...:159-172` |
| JSONL / Run completes | 충족 | `append_line` 덧붙이기 모드 `:590-594`, `cmd_run` `:1352-1360`. 본문 제외 `:562-587`. 테스트 `tests/...:388-398`. 단위는 (회차, 모델, 조건) 30문항당 한 줄이다. 「관찰」 1을 본다 |
| JSONL / Broken line in the scoreboard | 충족 | `read_lines` `:597-615`, 화면 안내 `:957-961`. 테스트 `tests/...:408-411`. 화면 문구를 확인하는 테스트는 없다 |
| Scoreboard view / Non-loopback bind requested | 충족 | `assert_loopback_host` `:984-987`를 `HTTPServer` 생성 `:1413`보다 먼저 부른다 `:1399`. 테스트 `tests/...:459-462` |
| Scoreboard view / Wiki always recovers a question | 충족 | `model_summary` `:726-730`. 테스트 `tests/...:414-449` |
| Product defaults / Experiment completes with a cheap model outperforming | 충족 | 제품 코드(`apps/`, `supabase/`)와 `.env`는 바뀌지 않았다. 작업 트리 변경은 `scripts/`, `docs/ops/`, 테스트, change 디렉터리뿐이다. 서버 스크립트는 `.env`를 읽기만 한다 `scripts/ask_replay_serve.sh:25`, `:33`. 대상은 루프백으로 제한된다 `:1050-1051`, `:1257` |

## 조치가 필요한 항목

1. **`not_run` 행에 판정이 없어서 중단 경로가 기록을 잃는다** — `run_condition_turns` `:476-484`가 만든 `not_run` 행에는 `verdict`가 없다. 그런데 `summarize_rows`는 모든 행에서 `r["verdict"]`를 읽는다(`counts_for_fact` `:407`, `classes` `:421`, `product_passed` `:431`). 그래서 상한에 걸리거나 측정 장애로 멈추면 `KeyError`가 난다. `cmd_run`은 그 조건을 `conditions`에 넣지 못한 채 기록을 쓰고, 성적표 줄도 쓰지 않은 채 `KeyError`를 다시 던진다 `:1328-1363`. 멈춘 조건의 `not_run` 턴과 측정 장애 턴이 기록에서 사라진다. 근거 Scenario: "Cap reached in round three — records the remaining turns as not run", "Worker serves another model — that turn is a measurement failure, the run stops". Requirement 문장: "Each completed or stopped run SHALL append exactly one line", "still being counted and shown". 제안: `not_run` 행에도 `judge(row, scope)`를 붙인다. `run_condition_turns`에 scope를 넘기거나 `cmd_run`에서 요약 전에 채운다. `run_condition_turns` → `summarize_rows` → `scoreboard_line`을 상한 중단과 측정 장애 중단 두 경우로 잇는 테스트도 더한다. 기존 테스트 `tests/...:260-329`는 요약 단계를 거치지 않아 이 결함을 놓쳤다.

2. **아직 시작하지 않은 실행이 `not_run`으로 남지 않는다** — Requirement "Round-major execution under the total cap"은 "marking the remaining turns **and runs** as not run with the cap as the reason"을 요구한다. 지금은 상한으로 멈추면 `model_evidence_run.sh:69-73`이 종료할 뿐이다. 남은 (회차, 모델) 실행은 기록에도 화면에도 사유가 없다. `build_view`의 `partial_rounds` `:787-793`도 줄이 있는 회차만 보므로, 한 턴도 시작하지 않은 회차는 부분 회차로도 보이지 않는다. 근거 Scenario: "Cap reached in round three — the experiment stops, records the remaining turns as not run". 제안: 상한으로 멈출 때 계획상 남은 실행마다 `not_run` 기록과 줄(사유 = 상한)을 남긴다. 또는 화면이 `plan.json`의 실행 순서와 기존 기록을 비교해 남은 실행을 "미실행(상한)"으로 표시한다. 둘 중 하나를 고르고 테스트를 붙인다.

3. **해시가 다른 실행을 함께 집계하지 않는다는 규칙을 집행하지 않는다** — Requirement "Fixed ingestion…"은 "runs whose hashes differ MUST NOT be aggregated together"를 요구한다. Requirement "Pre-registration…"은 등록 시각 이전 기록이나 해시가 맞지 않는 등록의 기록을 거부하라고 요구한다. 그런데 집계하는 쪽(`complete_rounds` `:666-674`, `build_view` `:751-801`, `check_run_order` `:340-344`)은 줄이나 실행 기록의 `fixed_inputs_sha256` · `answer_prompt_sha256` · `registration_sha256` · `created_at`을 확인하지 않는다. 성적표 줄에는 `answer_prompt_sha256`과 `registration_sha256`도 없다 `:574-587`. 실측 기록은 해시 조합이 하나뿐이라 결과에는 영향이 없다. 하지만 같은 디렉터리에 다른 프롬프트나 다른 등록의 실행이 섞여도 조용히 합산된다. 제안: 줄에 `answer_prompt_sha256`과 `registration_sha256`을 더한다(새 키 추가라 옛 줄과 호환된다). `build_view`는 현재 등록과 맞지 않는 줄이나 프롬프트 해시가 다수와 다른 줄을 비교에서 빼고 표시한다. 이를 확인하는 테스트를 더한다.

4. **(경미) 문항 안정성 수가 화면에 일부만 나온다** — Requirement "Local scoreboard view"는 "per-question stability counts"를 요구한다. `model_summary`는 `stable_pass` · `stable_fail` · `flaky`를 계산한다 `:714-725`. 그러나 `_summary_row`는 흔들림 수만 그린다 `:896`, `:905`. 제안: 두 조건의 안정 통과 · 안정 실패 · 흔들림을 모두 표시한다.

## 관찰 (조치 필수는 아님)

1. **"run" 단위가 모호하다** — Requirement "Append-only JSONL scoreboard"는 실행마다 정확히 한 줄을 쓰라고 하면서 줄에 `condition`을 넣으라고 한다. Scenario는 "a run finishes all 30 questions"이다. 구현은 CLI 실행 하나(60턴)가 조건별로 두 줄을 쓴다. 30문항 = 한 줄로 읽으면 일관되므로 미충족으로 보지 않았다. 다음 스펙 동기화 때 "run = (회차, 모델, 조건)"을 명시하면 좋다.
2. **응답 모델 확인이 간접적이다** — `ask_cost_trace_calls`의 `model`은 `ask_cost_calls.model`이다(`supabase/migrations/0027_ask_cost_accounting.sql:233`). 워커는 `usage_events.model`도 요청 모델로 덮어쓴다(`apps/worker/src/worker/ask_cost.py:135`). 그래서 "recorded usage names a different model"은 기록상 생길 수 없다. 실제 불일치는 정산이 `unresolved`로 남는 경로(`ask_cost.py:144-147`)를 거쳐 `cost_unresolved` 측정 장애로 잡힌다 `:372-373`. 이 경로는 테스트됐다 `tests/...:126-133`. 실효성은 있다. 다만 공급자 사용량에 `model` 키가 없으면 워커가 일치로 간주한다(`ask_cost.py:144`). 이 부분은 제품 코드라 이 change 범위 밖이다.
3. `check_run_order`는 앞선 실행 기록이 **있는지만** 보고 그 실행이 완료됐는지는 보지 않는다. Scenario 문구("has no record")는 충족한다. 측정 장애로 멈춘 1회차 실행이 있어도 2회차를 수동으로 시작할 수는 있다. 실행기는 0이 아닌 종료 코드에서 멈추므로 정상 경로는 막힌다.
4. `Harness`의 고정 입력 대조 자체(실제 스냅샷 계산 경로)는 네트워크가 필요해서 단위 테스트가 없다. 비교 함수 테스트와 실측 기록으로만 뒷받침된다.

## 판정 근거

스펙 범위는 바뀌지 않았다. 범위 밖 사용자 관찰 동작도 없다. 따라서 `blocked`가 아니다. 그러나 task 2.1 · 2.2 · 2.3이 `- [x]`로 완료 주장된 상한 중단 · 측정 장애 중단 경로가 실제로는 `KeyError`로 기록을 잃는다(조치 1). 단위 테스트가 요약 단계를 거치지 않아 이것을 잡지 못했다. 미검증 완료 주장이다. 남은 실행의 `not_run` 표시(조치 2)와 해시가 다른 실행의 집계 금지(조치 3)는 스펙 MUST인데 구현이 없다. 실측에서는 상한 · 장애 · 해시 불일치가 하나도 일어나지 않아 결과 수치에는 영향이 없다. 네 항목 모두 스펙을 고치지 않고 코드와 테스트만으로 해결된다. 그래서 `needs_fix`로 판정한다.
