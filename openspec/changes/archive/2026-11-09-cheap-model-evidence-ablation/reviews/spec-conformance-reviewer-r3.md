# Spec Conformance 리뷰 — cheap-model-evidence-ablation r3

- 판정: pass
- 대상: `ceaa4ab` 위의 미커밋 작업 트리. `scripts/model_evidence_eval.py`(1703줄)와 `apps/worker/tests/test_model_evidence_eval_script.py`(테스트 36개)를 봤다. `scripts/model_evidence_run.sh`, `design.md` D6, `verification.md` 갱신도 함께 확인했다
- 일시: 2026-11-09T11:26:34Z
- 검증(이번 라운드에 새로 실행):
  - `uv run --package worker pytest -q apps/worker/tests/test_model_evidence_eval_script.py`: 36 passed
  - `ruff check`, `ruff format --check`(두 파일): 통과
  - `bash -n scripts/model_evidence_run.sh scripts/ask_replay_serve.sh`: 통과
  - `openspec validate cheap-model-evidence-ablation --strict`: valid
- 추가 확인:
  - 네트워크 없이 판정 경로를 직접 돌렸다. 대상은 정상 거절, 거절 문항에 답한 경우, 원문만 조건의 사실 포함, fallback, 답할 수 있는 문항의 채널 실패, 모델 불일치에 `error`가 겹친 경우, 턴 도중 예외 → `condition_entries` → `scoreboard_line` → `_complete`다.
  - 실측 원본의 `runs/*.json` 9개를 새 `judge`로 다시 채점했고, 같은 디렉터리에 `build_view`를 다시 적용했다. 읽은 파일은 `registration.json`, `plan.json`, `scoreboard.jsonl`, `runs/*.json`뿐이며 `state.json`은 열지 않았다.
- 참고: 이 세션에서도 훅 때문에 `git diff`를 쓸 수 없었다. 그래서 변경 파일 원본을 직접 읽고 대조했다.

## r2 이후 변경 확인

| 변경 | 결과 | 증거 |
| --- | --- | --- |
| `judge`: 장애를 문항 종류보다 먼저 거른다 | 스펙에 맞음 | `scripts/model_evidence_eval.py:393-414`<br>- 순서는 `not_run` → 측정 장애 → `failed_channels` → 상태가 `{resolved, fallback, no-evidence}` 밖인 경우 → 공용 `answer_verdict`다.<br>- 그래서 거절 문항 `q30`의 402 `error`와, 채널 실패 뒤의 `no-evidence`가 모두 `execution_failure`로 분류된다. 이는 스펙 "A turn ended by a channel failure, provider error … MUST be classified as an execution failure"를 문항 종류와 무관하게 지키는 것이다.<br>- 모델 불일치에 `error`가 겹치면 측정 장애가 우선한다(시뮬레이션). 그래서 "Served model" 요구도 흔들리지 않는다.<br>- 테스트 `tests/...:415-437`(두 경우를 파라미터로 고정) |
| 답할 수 있는 문항의 회귀 여부 | 회귀 없음 | 공용 `retrieval_ablation.answer_verdict`는 이미 같은 두 검사를 같은 순서로 하고 있었다(`scripts/retrieval_ablation.py:1114-1122`). 달라진 것은 `pass`가 `False`에서 `None`으로 바뀐 것뿐이다. `product_passed`는 참값만 세므로(`:451-453`) 수치는 같다 |
| `summarize_rows`: 거절 분모에서 장애 턴과 미실행 턴을 뺀다 | 스펙에 맞음 | `:432-438`, `:457-458`<br>- 장애는 `execution_failures`로 계속 세어 표시한다(`:454`). 스펙의 "excluded from … denominators while still being counted and shown"과 같은 처리다.<br>- 화면은 분모가 0이면 "—"로 표시한다(`_bar` `:957-959`).<br>- 테스트 `tests/...:435-437` |
| `run_condition_turns`: 턴 도중 예외가 나면 그 턴을 `interrupted`로 남기고 예외를 다시 던진다 | 스펙에 맞음 | `:502-521`<br>- 그 행은 판정이 `measurement_failure`라 사실 분모와 거절 분모에서 빠진다(`:421-425`, `:437`).<br>- `fill_not_run`은 이미 있는 ID를 건너뛰므로 중복 행이 생기지 않는다(`:553-554`).<br>- `cmd_run`의 `finally`가 기록과 두 줄을 쓴다(`:1477-1505`).<br>- 시뮬레이션 결과: `['resolved', 'interrupted', 'not_run']`, `asked 2`, `measurement_failures 1`, `_complete False`.<br>- 테스트 `tests/...:370-412` |
| 연속 실행 장애 중단 | 회귀 없음 | 카운터는 판정 분류를 그대로 쓴다(`:528-533`). 이제 장애가 난 `q30`도 연속 장애에 들어간다. 테스트 `tests/...:440-462` |
| 실측 기록 재채점 | `verification.md` 서술과 일치 | 9개 실행 × 2조건의 모든 턴에서 판정 변화는 0건이고, 요약 수치 차이도 0건이다.<br>- 모델별 거절: Haiku 0/6, Luna 0/6, DeepSeek 4/6.<br>- 다시 적용한 `build_view`: 완료 회차 [1, 2, 3], 부분 회차 [], 불일치 [], 깨진 줄 0, 세 모델 모두 위키 차이 [0, 0, 0]. 참조(Sonnet) 요약도 바뀌지 않았다 |
| 문서 | 일치 | `design.md:58`(D6)이 장애 우선 판정, 거절 분모 제외, `interrupted`를 기록한다. `verification.md:39`가 재채점 결과를 기록한다 |

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Fixed ingestion / Snapshot matches the reused retrieval record | 충족 | `Harness.__init__`의 고정 입력 대조 `:1211-1222`. 실행 기록은 `fixed_inputs`, `fixed_inputs_sha256`, `answer_prompt_sha256`을 싣는다 `:605-607`. 해시가 다른 실행은 합산에서 뺀다 `split_consistent` `:848-878`, `:884`. 테스트 `tests/...:102-104`, `:682-702` |
| Fixed ingestion / Stack was re-ingested | 충족 | 유료 호출 전에 다른 키를 지목하며 `SystemExit`한다 `:1220-1222`. probe와 run 모두 Harness를 먼저 만든다 `:1371`, `:1444`. 테스트 `tests/...:102-104` |
| Served model / Worker serves another model | 충족 | 분류는 `enrich_turn` `:366-375`에서 한다. `judge`가 측정 장애를 가장 먼저 거른다 `:396-401`. 첫 측정 장애에서 멈춘다 `:524-527`. 사실 분모와 통과 수에서는 빠진다 `:421-425`, `:451-453`. 테스트 `tests/...:116-133`, `:303-333` |
| Pre-registration / Registration edited after creation | 충족 | `check_registration` `:204-213`. 유료 호출 전에 `load_registration`을 부른다 `:1362`, `:1433`. 테스트 `tests/...:89-94` |
| Pre-registration / Run without a cap | 충족 | `:165-166`, `:211-213`. 테스트 `tests/...:97-99` |
| Probe / Probe costs fit three rounds | 충족 | `plan_rounds` `:276-330`. 테스트 `tests/...:222-226` |
| Probe / Probe is refused by the provider | 충족 (테스트는 변형만 있음) | `probe_ok` `:242-250`. 제외와 사유 기록 `:295-297`. `probe_ok`는 이번에 바뀌지 않았다. 테스트는 모델 불일치 변형만 있다 `tests/...:178-195` |
| Probe / Probe answer is truncated | 충족 | `:266`, `:383`. 테스트 `tests/...:198-203` |
| Round-major / Cap reached in round three | 충족 | 턴 직전 상한 검사와 남은 턴의 미실행 표시 `:491-501`. 남은 실행의 미실행 표시 `close_remaining` `:1511-1554`, `model_evidence_run.sh:81-83`. 멈춘 줄은 완료가 아니다 `_complete` `:748-754`. 모델 간 비교는 완료 회차만 쓴다 `:757-765`, `:901`. 테스트 `tests/...:260-300`, `:336-367`, `:465`~, `:584-619` |
| Round-major / A round is started out of order | 충족 | `check_run_order` `:338-346`. 테스트 `tests/...:240-248` |
| Per-turn verdicts / Answer ends as a fallback | 충족 | `:381-382`. `fallback` 상태는 새 장애 필터를 통과해 공용 판정으로 간다 `:412`. 시뮬레이션 결과는 `repair True`, `fallback True`, `fact_missing`(fallback 본문 기준)이다. 테스트 `tests/...:136-148` |
| Per-turn verdicts / Source-only answer | 충족 | 판정은 공용 판정의 `fact_included`, `dual_citation: None`이고, 진단 표시가 붙는다 `:444`, `:669`. 시뮬레이션에서도 같았다. 테스트 `tests/...:159-172` |
| JSONL / Run completes | 충족 | `append_line` `:681-685`, `cmd_run` `:1496-1504`. 줄에 본문은 넣지 않는다 `:651-678`. 테스트 `tests/...:558-568` |
| JSONL / Broken line in the scoreboard | 충족 | `read_lines` `:688-706`, 화면 안내. 테스트 `tests/...:578-581` |
| Scoreboard view / Non-loopback bind requested | 충족 | `assert_loopback_host` `:1130`을 `HTTPServer` 생성 `:1615`보다 먼저 부른다 `:1601`. 테스트 `tests/...:629-632` |
| Scoreboard view / Wiki always recovers a question | 충족 | `model_summary` `:790-840`(`always_recovered` `:837`). 테스트 `tests/...:584-619` |
| Product defaults / Experiment completes with a cheap model outperforming | 충족 | 변경 범위는 `scripts/`, `docs/ops/`, 테스트, change 디렉터리뿐이다. 공용 `retrieval_ablation.answer_verdict`도 손대지 않았다. 장애 필터는 이 실험의 `judge`에만 있다. 지출 조회에서 루프백을 다시 강제한다 `:1146` |

## 조치가 필요한 항목

없음.

## 관찰 (조치 필수는 아님)

1. **`interrupted`는 측정 장애로 분류된다**
   - 스펙은 "provider error"를 실행 장애로 요구한다. 다만 공급자 오류는 워커가 상태 `error`로 돌려주고, 그 경우는 `judge` `:412-413`에서 실행 장애가 된다.
   - `interrupted`는 하네스 자체의 예외다. 예를 들어 메시지 조회나 비용 조회가 실패한 경우다. 이 턴은 사용량을 확인하지 못했으므로 "Served model"의 측정 장애 규칙에 더 가깝다.
   - 어느 쪽으로 분류해도 사실 분모와 거절 분모에서 빠지고, 수로 세어 표시되며, 실행은 `stopped`가 되어 완료 회차에서 빠진다. 그래서 관찰 가능한 수치는 같다.
2. **장애 하나만 있는 거절 턴은 그 회차를 막지 않는다**
   - 중단되지 않은 실행에서 `q30`만 실행 장애로 끝났다고 하자. 그 줄은 `asked == planned`이고 측정 장애도 없으므로 `_complete`를 통과한다 `:748-754`.
   - 이때 거절은 0/0("—")으로, 실행 장애는 1로 표시된다. 모델 간 요약은 사실 포함만 쓰므로 수치가 오염되지 않는다.
   - 스펙의 "excluded … while still being counted and shown"과 일치한다.
3. **r2의 관찰 1~5는 그대로 유효하다**
   - 측정 장애도 실험을 닫는 보수적 선택, 실행 기록 `created_at`의 시각 미대조, 해시가 어긋난 줄만 있는 회차의 부분 회차 표시, 네트워크 배선의 단위 테스트 부재, run 단위 표현이 여기에 해당한다.
   - 이번 변경은 이 가운데 어느 것도 악화시키지 않았다.
   - 덧붙여, 예외로 끝난 `cmd_run`은 다시 던져 종료 코드 1이 되므로 실행기가 `close`를 부르지 않는다. 이 동작도 r2와 같다. 남은 계획 실행은 화면이 `missing_runs`로 표시하고 부분 회차로 처리한다 `:891-894`, `:922-928`.

## 판정 근거

r2 이후의 세 변경(`judge`의 장애 우선 분류, 거절 분모 제외, `interrupted` 행)은 모두 Requirement "Per-turn verdicts and failure signals" 범위 안에 있다. 특히 "채널 실패 · 공급자 오류로 끝난 턴은 실행 장애, 분모에서 빼되 센다"를 거절 문항에도 일관되게 적용하는 보강이다. 각 변경에는 대응 테스트가 있다(`tests/...:370-437`). 오프라인 시뮬레이션에서도 정상 거절, 답한 거절, 원문만 조건, fallback, 모델 불일치 경로가 의도대로 갈렸다. r2에서 충족이던 16개 시나리오를 바뀐 줄 번호로 다시 대조했고 회귀는 없었다. 실측 기록을 새 판정으로 재채점해도 판정 변화가 0건이라 `verification.md`의 수치가 유지된다. 모든 Scenario가 증거와 함께 충족되므로 `pass`로 판정한다.
