# Spec Conformance 리뷰 — cheap-model-evidence-ablation r2

- 판정: pass
- 대상: `ceaa4ab` 위 미커밋 작업 트리. `scripts/model_evidence_eval.py`(1665줄) · `scripts/model_evidence_run.sh` · `apps/worker/tests/test_model_evidence_eval_script.py`(34개)를 보고, `design.md` D5 · `verification.md` 갱신을 함께 확인했다
- 일시: 2026-11-09T11:21:42Z
- 검증(새로 실행):
  - `uv run pytest apps/worker/tests/test_model_evidence_eval_script.py -q`: 34 passed
  - `ruff check` · `ruff format --check`(두 파일): 통과
  - `bash -n scripts/model_evidence_run.sh scripts/ask_replay_serve.sh`: 통과
  - `openspec validate cheap-model-evidence-ablation --strict`: valid
- 추가 확인:
  - 네트워크 없는 종단 시뮬레이션을 직접 돌렸다(`run_condition_turns` → `condition_entries` → `build_run_record` → `scoreboard_line` → `close_remaining` → `build_view` → `render_html`). 상한 중단 경로와 측정 장애 중단 경로를 각각 확인했다.
  - 실측 디렉터리에 새 `build_view`를 다시 적용했다. 이때 `registration.json` · `plan.json` · `scoreboard.jsonl` · `runs/*.json`만 읽었고 `state.json`은 열지 않았다.
- 참고: 이 세션에서는 훅 때문에 `git diff`를 쓸 수 없었다. 그래서 변경 파일 원본을 직접 읽고 대조했다.

## r1 조치 항목 해결 여부

| r1 항목 | 결과 | 증거 |
| --- | --- | --- |
| 1. `not_run` 행에 판정이 없어 `KeyError` | 해결 | `not_run_row`가 `verdict`를 붙인다 `scripts/model_evidence_eval.py:499-508`. 상한 중단 경로 `:480-482`와 예외 채움 `fill_not_run` `:511-517`이 이 함수를 같이 쓴다. `condition_entries` `:520-543`는 시작 못 한 조건까지 두 조건을 모두 요약한다. `cmd_run`은 `started` 목록에 턴을 바로 쌓고 `:1415`, `:1430`, `finally`에서 기록과 두 줄을 쓴다 `:1439-1467`. 테스트는 `tests/...:303-333`(측정 장애 → 요약), `:336-367`(상한 → 요약 → 성적표 줄), `:370-404`(예외 → 과금 턴 보존). 시뮬레이션에서도 두 경로 모두 `KeyError` 없이 줄 18개가 남았다 |
| 2. 시작 못 한 실행이 `not_run`으로 남지 않음 | 해결 | `close_remaining` `:1473-1516`이 계획상 남은 (회차, 모델)마다 미실행 기록과 두 줄을 쓴다. 사유는 멈춘 실행의 `stopped`이고 `not started:` 접두가 붙는다. 실행기는 종료 코드 2일 때 `close`를 부른다 `scripts/model_evidence_run.sh:78-84`. 화면은 기록 없는 계획 실행을 `missing_runs`로 표시하고, 그 회차를 부분 회차에 넣는다 `:853-856`, `:884-890`, `:1060-1062`. 테스트 `tests/...:432-454`, `:672-681` |
| 3. 해시가 다른 실행을 함께 집계 | 해결 | 성적표 줄에 `registration_sha256` · `answer_prompt_sha256`을 더했다 `:635-637`. `split_consistent` `:810-839`는 실행 기록의 등록 · 고정 입력 · 프롬프트 해시를 기준과 비교한다. 다른 줄은 `complete_rounds`와 모델 요약 입력에서 빠진다 `:846`, `:852`, `:860`. 실행별 표에는 남고 `:893`, 뺀 개수를 표시한다 `:1063-1064`. 테스트 `tests/...:649-669`. 실측 기록에서는 불일치 0, 깨진 줄 0, 완료 회차 1·2·3이다. 옛 줄에 해시 필드가 없어도 실행 기록에서 읽으므로 호환된다 |
| 4. 안정성 수 일부만 표시 | 해결 | `_summary_row`가 두 조건의 안정 통과·안정 실패·흔들림을 모두 그린다 `:996-999`, `:1008`. 헤더는 `:956`. 테스트 `tests/...:684-691` |

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Fixed ingestion / Snapshot matches the reused retrieval record | 충족 | `Harness.__init__` 고정 입력 대조 `:1173-1184`. 실행 기록은 `fixed_inputs` · `fixed_inputs_sha256` · `answer_prompt_sha256`을 싣는다 `:567-569`. 해시가 다른 실행은 합산에서 뺀다 `:810-839`. 테스트 `tests/...:102-104`, `:649-669` |
| Fixed ingestion / Stack was re-ingested | 충족 | `run_turn`보다 먼저 `SystemExit`로 다른 키를 지목한다 `:1182-1184`. probe와 run 모두 Harness를 먼저 만든다 `:1333`, `:1406`. 테스트 `tests/...:102-104` |
| Served model / Worker serves another model | 충족 | 분류 `enrich_turn` `:370-375`. 첫 측정 장애에서 멈춘다 `:486-489`. 장애 턴은 사실 분모에서 빠지고 `:405-413` 통과로도 세지 않는다(`pass: None`, `:396-401`, `:433`). 조건과 줄은 이제 기록에 남는다. 테스트 `tests/...:116-133`, `:303-333` |
| Pre-registration / Registration edited after creation | 충족 | `check_registration` `:204-213`. 유료 호출 전에 `load_registration`을 부른다 `:1324`, `:1395`. 테스트 `tests/...:89-94` |
| Pre-registration / Run without a cap | 충족 | `:165-166`, `:211-213`. 테스트 `tests/...:97-99` |
| Probe / Probe costs fit three rounds | 충족 | `plan_rounds` `:276-330`. 테스트 `tests/...:222-226` |
| Probe / Probe is refused by the provider | 충족 (테스트는 변형만) | `probe_ok` `:242-250`. 제외와 사유 `:295-297`. 테스트는 모델 불일치 변형만 있다 `tests/...:178-195` |
| Probe / Probe answer is truncated | 충족 | `:266`. 테스트 `tests/...:198-203` |
| Round-major / Cap reached in round three | 충족 | 턴 직전 상한 검사와 남은 턴 미실행 `:473-482`. 남은 실행 미실행 `:1473-1516` · `model_evidence_run.sh:81-83`. 멈춘 줄은 완료가 아니다 `_complete` `:710-716`. 모델 간 비교는 완료 회차만 쓴다 `:719-727`, `:863`. 시뮬레이션(3회차 두 번째 모델 도중 상한)에서 완료 [1, 2] · 부분 [3] · 누락 [] · 모델 요약 회차 [1, 2]가 나왔다. 테스트 `tests/...:260-300`, `:336-367`, `:432-454`, `:551-586` |
| Round-major / A round is started out of order | 충족 | `check_run_order` `:338-346`. 테스트 `tests/...:240-248` |
| Per-turn verdicts / Answer ends as a fallback | 충족 | `:381-382`. 테스트 `tests/...:136-148` |
| Per-turn verdicts / Source-only answer | 충족 | `ablation.answer_verdict`(`dual_citation: None`). 진단 표시 `:425`, `:631`. 테스트 `tests/...:159-172` |
| JSONL / Run completes | 충족 | `append_line` `:643-647`, `cmd_run` `:1458-1466`. 본문은 넣지 않는다 `:613-640`. 테스트 `tests/...:525-535` |
| JSONL / Broken line in the scoreboard | 충족 | `read_lines` `:650-668`, 화면 안내 `:1065-1069`. 테스트 `tests/...:545-548` |
| Scoreboard view / Non-loopback bind requested | 충족 | `assert_loopback_host` `:1092-1095`를 `HTTPServer` 생성 `:1577`보다 먼저 부른다 `:1563`. 테스트 `tests/...:596-599` |
| Scoreboard view / Wiki always recovers a question | 충족 | `model_summary` `:779-783`. 테스트 `tests/...:551-586`, `:649-669` |
| Product defaults / Experiment completes with a cheap model outperforming | 충족 | 변경은 `scripts/` · `docs/ops/` · 테스트 · change 디렉터리뿐이다. 제품 코드와 `.env`는 바뀌지 않았다. 지출 조회에서 루프백을 다시 강제한다 `:1108` |

## 조치가 필요한 항목

없음.

## 관찰 (조치 필수는 아님)

1. **측정 장애 · 연속 실행 장애도 실험 전체를 닫는다**
   - 실행기는 종료 코드 2면 사유와 무관하게 `close`를 부르고 끝낸다 `model_evidence_run.sh:81-83`. 2는 상한 · 측정 장애 · 실행 장애 3연속 · 예외를 모두 뜻한다.
   - 그러면 남은 계획 실행이 덮어쓸 수 없는 미실행 기록으로 확정된다. `write_new`와 `check_run_order` 때문에 재시도할 수 없다.
   - 스펙이 남은 실행의 미실행 표시를 요구하는 것은 상한 경우뿐이다. 측정 장애에 대해서는 "the run MUST stop"만 요구한다. 그래서 이 동작은 스펙 위반이 아니라 더 보수적인 선택이다.
   - `design.md` D5에 "실행이 멈추면 실행기가 `close`로…"라고 기록돼 있다. 일시 장애 뒤 재개가 필요해지면 그때 결정할 일이다.
2. **실행 기록의 `created_at`은 등록 시각과 비교하지 않는다**
   - Requirement "Pre-registration"의 "run record created at or before the registration time … MUST be refused"는 점검 기록 쪽에서만 명시적으로 집행된다 `:294`.
   - 실행 기록은 `load_registration` 뒤에 `_now()`로 만들어지므로 정상 경로에서는 등록보다 늦다. 다만 `split_consistent`는 등록 해시만 보고 시각은 보지 않는다.
   - 시계가 거꾸로 가거나 손으로 만든 기록이 아니면 생길 수 없는 경우라 미충족으로 보지 않았다.
3. **해시가 어긋난 줄만 있는 회차는 부분 회차로도 표시되지 않는다**
   - 어떤 회차의 줄이 전부 `split_consistent`에서 빠지면, 그 회차는 `partial_rounds`에 들지 않는다 `:884-890`.
   - 대신 "해시가 달라 합산에서 뺀 줄 N개"가 표시되고 합산에서는 빠진다. 스펙의 "MUST NOT be aggregated"는 지켜진다.
4. **네트워크가 필요한 배선은 단위 테스트가 없다**
   - `cmd_run`의 `finally` 배선과 `model_evidence_run.sh`의 `close` 호출이 여기에 해당한다. 구성 함수는 각각 테스트됐다.
   - 이번 리뷰의 종단 시뮬레이션은 이 구성 함수들을 실제 순서대로 엮어 확인했다.
5. **"run" 단위 표현은 r1과 같다**
   - 한 CLI 실행은 (회차, 모델, 조건)마다 한 줄, 즉 두 줄을 쓴다. 다음 스펙 동기화 때 "run = (회차, 모델, 조건)"을 명시하면 좋다.

## 판정 근거

r1의 조치 4건은 모두 코드와 테스트로 해결됐다. 각 해결은 위 표의 줄 번호와 대응 테스트로 확인했다. 특히 r1에서 미검증 완료 주장으로 지적한 상한 · 측정 장애 중단 경로가 이제 성적표 줄까지 이어진다. 이것은 요약 단계를 거치는 테스트(`tests/...:303-367`)와 종단 시뮬레이션 둘 다로 확인했다.

새 동작인 `close` 명령, 연속 실행 장애 중단, 리스너 미종료 시 중단은 스펙 범위 안이다. 각각 남은 실행의 미실행 표시와 부분 회차 제외를 보강하며, `design.md` D5에 기록돼 있다. 회귀는 찾지 못했다. 실측 기록을 새 화면 로직으로 다시 집계해도 완료 회차 1·2·3, 위키 차이 0, 불일치 0으로 `verification.md`의 서술과 같다.

모든 Scenario가 증거와 함께 충족되므로 `pass`로 판정한다.
