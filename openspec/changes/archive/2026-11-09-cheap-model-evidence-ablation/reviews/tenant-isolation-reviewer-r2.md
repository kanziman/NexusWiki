# Tenant Isolation 리뷰 — cheap-model-evidence-ablation r2

- 판정: needs_fix
- 대상: 미커밋 작업 트리(`git diff` + 미추적 파일), 기준 `HEAD` = `ceaa4ab17b6020fa2cbd46baea669dfaf0c89974`
  - 수정: `scripts/ask_replay_serve.sh`, `docs/ops/ask-sample-replay.md`
  - 신규: `scripts/model_evidence_eval.py`, `scripts/model_evidence_run.sh`, `apps/worker/tests/test_model_evidence_eval_script.py`, `openspec/changes/cheap-model-evidence-ablation/`
- 일시: 2026-11-09T11:22:07Z
- 검증: `uv run --package worker pytest -q apps/worker/tests/test_model_evidence_eval_script.py` → 34 passed (새로 실행). 아래 1번은 `enrich_turn` → `judge` → `summarize_rows`를 직접 호출해 재현했다.

## r1 지적 반영 확인

| r1 # | 지적 | 결과 | 근거 |
| --- | --- | --- | --- |
| 1 | 예외로 끝난 조건의 과금된 턴 누락 | 해결(잔여 1건, 아래 2번) | `run_condition_turns`가 호출부 목록에 바로 쌓는다(`scripts/model_evidence_eval.py:462-469`, `:485`). `cmd_run`이 `started`를 넘기고(`:1415`, `:1430`) finally에서 `condition_entries`로 두 조건을 항상 기록한다. 시작 못 한 조건과 끊긴 조건의 남은 문항은 `not_run`이 되고 성적표 줄도 두 개 남는다(`:520-543`, `:1439-1466`). 고정 테스트 `test_exception_mid_condition_keeps_charged_turns` |
| 2 | 이전 워커가 안 내려가도 다음 모델로 진행 | 해결 | 종료 대기 30초 뒤에도 리스너가 살아 있으면 `exit 1`(`scripts/model_evidence_run.sh:66-77`). 시작 전 점유 검사(`:18-21`)와 합쳐, `wait_listener`가 성공하면 그 응답은 이번에 띄운 워커의 것이다. `ask_replay_serve.sh`의 WORKER_ONLY 경로는 EXIT/INT/TERM trap으로 워커를 내린다(`scripts/ask_replay_serve.sh:74-78`). 워커가 안 죽으면 조용히 넘어가지 않고 멈춘다 |
| 3 | 실행 장애만으로 채워진 실행이 완료 회차로 집계 | 해결(답할 수 있는 문항 한정, 아래 1번) | 실행 장애 3턴 연속이면 멈춘다(`:86`, `:490-495`). 멈춘 실행은 `stopped`가 있어 `_complete`에서 빠지고(`:710-716`), 종료 코드 2로 실행기가 `close`를 부른다(`model_evidence_run.sh:81-83`). 고정 테스트 `test_consecutive_execution_failures_stop_the_run` |
| 4 | `spent_since` 자체 루프백 검사 없음 | 해결 | 함수 첫 줄에서 `replay.assert_loopback(stack)`(`:1108`) |

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 제품 API·워커 코드 변경 없음. Ask 재생은 `UserDb(access_token=self.token)`(`scripts/model_evidence_eval.py:1212-1217`), 호출별 비용 조회 `ask_cost_trace_calls`는 anon `apikey` + 요청자 JWT(`:1125-1129`). service 키는 `sum_usage_events_since` 한 곳(`:1103-1116`)이며 `service_role` 전용 grant RPC다(`0027_ask_cost_accounting.sql`). 사용자 요청 경로가 아니다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블·마이그레이션 없음 |
| A-3 | `anon` 신규 GRANT·정책 | 해당 없음 | DDL 변경 없음 |
| A-4 | service_role 코드의 `workspace_id` 필터 | 통과 | `spent_since`가 `p_workspace_id`를 명시해 넘기고(`:1113`), 호출자 셋(`Harness.spent` `:1190`, `cmd_plan` `:1372`, `cmd_run` 경유) 모두 `state.json`의 재생 워크스페이스 ID를 쓴다. 루프백도 함수 안에서 강제한다(`:1108`) |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | API 경로 변경 없음. 스크립트는 UPDATE/DELETE를 하지 않는다 |
| B-7 | `42501` → 403 매핑 | 해당 없음 | API 경로 변경 없음. `ask_cost_trace_calls`의 거부는 `raise_for_status`로 예외가 되고(`:1130`), 이제 finally에서 부분 기록으로 남는다 |
| C-8 | 핸들러 재실행 안전성 | 해당 없음(핸들러 없음) · 기록 측 통과 | 작업 핸들러 없음. 실행·점검·계획·미실행 기록은 모두 `open("x")`로 덮어쓰기를 거부한다(`:133-140`). `close`는 기록이 없는 계획 실행만 채우므로(`:1491-1494`) 다시 불러도 중복 기록을 만들지 않는다. 다만 `close`가 성적표 줄을 `write_new` 뒤에 덧붙이므로, 기록 쓰기와 줄 덧붙이기 사이에서 죽으면 그 실행의 줄이 빠질 수 있다. 이는 `cmd_run`도 같은 구조이고 화면은 계획 실행에 줄이 없으면 부분 회차로 처리하므로(`test_planned_run_without_record_marks_round_partial`) 수치가 틀어지지 않는다 |
| C-9 | `jobs` 직접 UPDATE 금지 | 해당 없음 | `jobs` 접근 없음 |
| D-10 | `hnsw.iterative_scan = strict_order` | 해당 없음 | 새 벡터 질의 없음. 기존 `RetrievalService` 경로 |
| D-11 | 색인·질의 토크나이저 동일 | 해당 없음 | 토크나이저 변경 없음. 질의 벡터는 고정값이며 해시를 등록과 대조한다(`:1173-1184`) |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | DDL 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 신규 파일에 `.format(` 없음 |
| D-14 | 인용 앵커 동반 | 해당 없음 | 컨텍스트 조립 코드 변경 없음 |
| E-15 | 마이그레이션 번호 | 해당 없음 | 신규 마이그레이션 없음 |
| 추가 | 종료 코드 2 → `close` 연쇄 | 통과 | 2는 `cmd_run`의 `return 2`(`:1470`)에서만 의도적으로 나온다. 등록·계획·순서·런타임 검사의 `SystemExit("…")`는 종료 코드 1이라 `close`를 부르지 않는다. argparse·uv 오류로 2가 나와도 새 기록이 없으면 마지막 기록의 `stopped`가 비어 `close_remaining`이 거부한다(`:1487-1489`) |
| 추가 | 실행 장애가 다른 판정으로 세지는 경로 | 위반 | 거절 문항(`q30`, `doc == "none"`)의 실행 장애가 실행 장애로 분류되지 않는다. 아래 1번 |

## 조치가 필요한 항목

1. **거절 문항의 실행 장애가 '모델이 거절에 실패함'으로 조용히 집계된다** (심각도: 보통)
   - 위치: `scripts/model_evidence_eval.py:393-402` (`judge`가 측정 장애·미실행만 먼저 거르고 나머지를 `ablation.answer_verdict`에 넘긴다), `scripts/retrieval_ablation.py:1107-1113` (`doc == "none"`이면 상태·채널 실패를 보기 전에 거절 판정으로 간다), `scripts/ask_replay.py:181-186`
   - 깨지는 것: 재생 월 한도(`NW402`)나 워커 다운으로 `q30`이 상태 `error`로 끝나면 판정은 `refusal_wrong`, 사유는 "답하면 안 되는 질문에 답했다 (상태 error)"가 된다. 실행 장애 수는 0으로 남는다. 재현: `enrich_turn({'id':'q30','doc':'none','status':'error',…}, [])` → `judge` → `{'classification': 'refusal_wrong'}`, `summarize_rows` → `execution_failures 0, refusal_correct 0, refusal_total 1`. 반대로 검색 채널이 전부 실패해 `no-evidence`로 끝난 `q30`은 `refusal_correct`로 통과한다(`failed_channels=['vector','fts']`로 재현). 스펙은 "채널 실패·공급자 오류·사용량 없음으로 끝난 턴은 실행 장애로 분류하고 분모에서 빼되 센다"를 MUST로 요구하는데, 유일한 거절 문항에서 이 규칙이 빠진다. 그 실행은 `stopped`도 없고 `asked == planned`라 `_complete`를 통과해 완료 회차로 모델 비교에 들어간다. 성적표의 거절 결과가 인프라 장애를 그 모델의 행동으로 기록한다. `q30`은 각 조건의 마지막 문항(30번째)이라 연속 장애 카운터 이후에 오므로, 앞선 3턴 연속 장애 검사도 이 턴을 받쳐 주지 않는다.
   - 조치: `judge`에서 `ablation.answer_verdict`로 넘기기 전에, 상태가 `{resolved, fallback, no-evidence}` 밖이거나 `failed_channels`가 있는 턴을 문항 종류와 무관하게 `execution_failure`로 분류한다. 그러면 `summarize_rows`의 `refusals`에서도 빼야 한다(거절 분모는 실행된·장애 없는 거절 턴만). `doc == "none"`이고 `status == "error"`인 턴, `failed_channels`가 있는 `no-evidence` 턴 두 경우를 고정하는 테스트를 더한다. `retrieval_ablation.answer_verdict` 자체는 #237 기록 재채점에 쓰이므로 이 실험의 `judge`에서 막는 편이 범위가 좁다.

2. **예외가 난 그 턴은 과금됐어도 `not_run`(비용 0)으로 기록된다** (심각도: 낮음, 권장)
   - 위치: `scripts/model_evidence_eval.py:483` (`run_turn`이 예외를 던지면 행이 없다), `:1258-1263` (LLM 호출이 끝난 뒤의 `_turn_message`·`trace_calls`에서 예외가 날 수 있다), `:511-517` (`fill_not_run`)
   - 깨지는 것: 답변 호출은 끝났는데 메시지 조회나 비용 조회가 실패하면, 그 문항은 "돌지 않은 턴"으로 비용 0과 함께 남는다. 실제 지출은 `spent_delta_micros`에 잡히므로 상한 집행과 기록 전체의 지출은 맞고, 그 실행은 `stopped`가 있어 모델 간 수치에서도 빠진다. 다만 줄의 `cost_micros`·`asked`가 실제보다 한 턴 적고, 사유가 "not_run"이라 "물었지만 결과를 못 읽었다"와 구분되지 않는다.
   - 조치(권장): `run_condition_turns`가 `run_turn` 직전에 진행 중 문항 ID를 남기고, 예외 시 그 문항만 `status="interrupted"`(판정 `execution_failure`, 사유 예외 이름)로 채운다. 또는 최소한 기록에 `interrupted_question` 필드를 둔다. 재리뷰 통과 조건은 아니다.

## 판정 근거

테넌트 경계를 넘는 경로는 없다. service_role은 루프백 스택의 `service_role` 전용 집계 RPC 하나에만 쓰이고 함수 안에서 루프백과 `workspace_id`를 모두 강제하며, Ask 재생과 호출별 비용 조회는 요청자 JWT를 쓴다. 제품 API·워커·마이그레이션은 바뀌지 않았다. 그래서 `blocked`가 아니다. r1의 두 `needs_fix` 항목(과금된 턴 누락, 겹친 워커로 인한 오귀속)과 권장 두 항목은 모두 코드와 테스트로 해결됐다. 그러나 이번 라운드에서 같은 "조용한 실패" 범주의 결함을 하나 새로 찾았다. 유일한 거절 문항 `q30`에서는 실행 장애가 실행 장애로 분류되지 않아, 인프라 장애가 그 모델의 거절 실패로 집계되고 그 회차는 완료 회차로 비교에 들어간다(1번, 스펙 MUST 위반). 수정 범위는 `judge` 한 함수와 요약의 거절 분모, 테스트 둘이다. 그래서 `needs_fix`로 판정한다. 2번은 권장 사항이다.
