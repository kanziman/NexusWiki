# Tenant Isolation 리뷰 — cheap-model-evidence-ablation r1

- 판정: needs_fix
- 대상: 미커밋 작업 트리(`git diff` + 미추적 파일), 기준 `HEAD` = `ceaa4ab17b6020fa2cbd46baea669dfaf0c89974`
  - 수정: `scripts/ask_replay_serve.sh`, `docs/ops/ask-sample-replay.md`
  - 신규: `scripts/model_evidence_eval.py`, `scripts/model_evidence_run.sh`, `apps/worker/tests/test_model_evidence_eval_script.py`, `openspec/changes/cheap-model-evidence-ablation/`
- 일시: 2026-11-09T11:14:53Z
- 검증: `uv run --package worker pytest -q apps/worker/tests/test_model_evidence_eval_script.py` → 27 passed (새로 실행)

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 제품 API·워커 코드 변경 없음. 스크립트의 Ask 재생은 `UserDb(access_token=self.token)`(`scripts/model_evidence_eval.py:1100-1105`)와 요청자 JWT로 부른 `ask_cost_trace_calls`(`:1013-1017`)를 쓴다. service 키는 `sum_usage_events_since` 집계 한 곳(`:997-1004`)뿐이고, 이 RPC는 `service_role` 전용 grant다(`0027_ask_cost_accounting.sql:79-81`). 사용자 요청 경로가 아니다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블·마이그레이션 없음 |
| A-3 | `anon` 신규 GRANT·정책 | 해당 없음 | DDL 변경 없음. `apikey`에 로컬 anon 데모 키를 싣는 것은 PostgREST 규약이고, 권한 판정은 `Authorization`의 사용자 JWT로 한다 |
| A-4 | service_role 코드의 `workspace_id` 필터 | 통과 | `spent_since`가 `p_workspace_id`를 명시해 넘기고(`:1001`), 함수 본문이 `e.workspace_id = p_workspace_id`로 거른다(`0027:76-77`). 호출자 두 곳 모두 `state.json`의 재생 워크스페이스 ID를 넘긴다(`:1078`, `:1260`) |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | API 경로 변경 없음. 스크립트는 UPDATE/DELETE를 하지 않는다 |
| B-7 | `42501` → 403 매핑 | 해당 없음 | API 경로 변경 없음. 스크립트에서 `ask_cost_trace_calls`의 `42501`은 `raise_for_status`로 예외가 되어 실행을 멈춘다(`:1018`) |
| C-8 | 핸들러 재실행 안전성 | 해당 없음(핸들러 없음) · 기록 측 확인 | 작업 핸들러를 추가하지 않았다. 실험 기록은 `open("x")`로 덮어쓰기를 거부하고(`:131-138`), 등록·점검·계획·실행 모두 기존 경로를 먼저 검사한다. 재실행 시 재생 DB에는 턴마다 새 스레드가 쌓이지만(`thread_id=None`, `uuid4()`) 지출은 DB 기준이라 상한이 이중 집계로 뚫리지 않는다. 단, 예외 시 부분 기록이 빠지는 문제는 아래 1번 |
| C-9 | `jobs` 직접 UPDATE 금지 | 해당 없음 | `jobs` 접근 없음 |
| D-10 | `hnsw.iterative_scan = strict_order` | 해당 없음 | 새 벡터 질의 없음. 기존 `RetrievalService` 경로를 그대로 쓴다 |
| D-11 | 색인·질의 토크나이저 동일 | 해당 없음 | 토크나이저 변경 없음. 질의 벡터만 고정값(`FixedQueryEmbeddingClient`)으로 대체하고 그 해시를 등록과 대조한다(`:1061-1072`) |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | DDL 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 신규 파일에 `.format(` 없음. 프롬프트 조립은 기존 `AskService` 경로 |
| D-14 | 인용 앵커 동반 | 해당 없음 | 컨텍스트 조립 코드 변경 없음 |
| E-15 | 마이그레이션 번호 | 해당 없음 | 신규 마이그레이션 없음 |
| 추가 | 루프백 강제 | 통과(보강 권장) | 스택·워커 URL은 `replay.assert_loopback`(`:1050-1051`, `:1257`), 성적표 바인드는 `assert_loopback_host`(`:984-987`)로 막는다. service 키는 Supabase CLI 공개 데모 키(`scripts/ask_replay.py:73-77`)라 클라우드에서 통하지 않는다. `spent_since` 자체에는 검사가 없다(아래 4번) |
| 추가 | 지출 누락 | 통과 | 상한 집행은 기록 합이 아니라 `effective_usage.budget_micros` 합이고, 미정산 호출은 `greatest(reserve_micros, 관측액)`으로 잡힌다(`0027:65-67`). 실행이 죽어도 지출은 DB에 남는다 |
| 추가 | 측정 장애가 성공으로 세지는 경로 | 부분 위반 | 모델 불일치·미정산·사용량 없음은 측정 장애로 분류되고 실행을 멈춘다(`:366-373`, `:489-491`). 정산은 공급자 응답 모델이 호출 모델과 같을 때만 일어나므로(`apps/worker/src/worker/ask_cost.py:144`) `settled` 요구가 served-model 검사를 실제로 받친다. 다만 아래 2·3번 경로가 있다 |

## 조치가 필요한 항목

1. **예외로 끝난 조건의 이미 돈 턴이 실행 기록에서 사라진다** (심각도: 보통)
   - 위치: `scripts/model_evidence_eval.py:465` (`rows`가 `run_condition_turns` 지역 변수), `:1307-1326` (`conditions.append`는 조건이 정상 반환한 뒤에만), `:1334-1360` (finally)
   - 깨지는 것: 조건 도중 `trace_calls`의 `raise_for_status`, `spent_since` 조회 실패, 워커 연결 오류 등으로 예외가 나면 그 조건에서 이미 실행·과금된 턴의 행이 통째로 버려진다. 실행 기록에는 `stopped="exception …"`만 남고, 성적표 줄은 그 조건에 대해 아예 쓰이지 않는다. 첫 조건에서 죽으면 그 실행은 성적표에 한 줄도 남지 않아 화면에서 보이지 않는다. 지출 자체는 `spent_delta_micros`로 잡히므로 상한은 지켜지지만, 줄의 `cost_micros`·토큰·턴 판정이 실제보다 적게 남는다. 설계 D5("예외로 죽어도 `finally`에서 부분 기록과 성적표 줄을 남긴다")와도 어긋난다.
   - 조치: `run_condition_turns`가 바깥에서 받은 리스트에 행을 바로 덧붙이게 하거나, `work`가 조건 진입 시 빈 조건 항목을 먼저 `conditions`에 넣고 행을 그 안에 쌓는다. finally에서 미완 조건도 `summarize_rows`로 요약하고 남은 문항을 `not_run`(사유: 예외)으로 채워 기록·줄을 쓴다. 이를 고정하는 테스트(조건 중간 예외 → 기록에 앞선 턴 존재, 줄 기록)를 더한다.

2. **이전 워커가 안 내려가도 다음 모델로 진행해, 인프라 장애가 영구 '모델 제외' 결과로 굳는다** (심각도: 보통)
   - 위치: `scripts/model_evidence_run.sh:64-68`, 연쇄 `:48` (`wait_listener`), `scripts/model_evidence_eval.py:1236-1242` (점검은 `ok=False`여도 종료 코드 0)
   - 깨지는 것: 30초 안에 8081이 닫히지 않으면 루프가 그냥 빠져나간다. 다음 모델의 워커는 포트를 못 잡고, `wait_listener`는 **이전 모델 워커**의 응답으로 즉시 성공한다. runtime manifest는 새 모델로 쓰였으므로 `read_runtime` 검사도 통과한다. 첫 턴에서 `model_mismatch`로 측정 장애가 잡히는 것은 맞지만, 점검 단계라면 그 기록이 `ok=False, failure_reason="측정 장애 model_mismatch:<이전 모델>"`로 **append-only로 굳어** 다시 점검할 수 없고(`:1217-1218`), 점검 명령이 0을 돌려주므로 실행기가 멈추지 않고 남은 모델도 같은 이유로 연달아 제외된다. 실제 원인은 포트 점유인데 기록은 "그 모델이 다른 모델을 서빙했다"로 남는다.
   - 조치: 종료 대기 루프 뒤에도 리스너가 살아 있으면 `exit 1`로 멈춘다. 가능하면 각 단계 시작 전 리스너가 새로 띄운 워커의 것인지(예: 워커 로그의 기동 표시나 프로세스 생존) 확인한다.

3. **실행 장애만으로 채워진 실행이 '완료 회차'로 집계되고 종료 코드 0이다** (심각도: 낮음)
   - 위치: `scripts/model_evidence_eval.py:366` (상태 `error`는 사용량 없음 검사에서 빠짐), `:489-491` (측정 장애일 때만 멈춤), `:657-663` (`_complete`가 `execution_failures`를 보지 않음), `:1364`
   - 깨지는 것: 실행 도중 재생 월 한도가 차서(`NW402` → 상태 `error`, 예약 행 없음) 또는 워커가 죽어서(`llm_unavailable` → `error`) 남은 턴이 전부 실행 장애가 되어도 실행은 멈추지 않고 0으로 끝난다. 그 회차는 `_complete`를 통과해 모델 간 비교에 들어가고, 모델 요약의 분모(`shared`)만 조용히 줄어든다. 실행별 행에 경고색으로 표시되고 스펙("실행 장애는 분모에서 빼되 세고 보인다")에는 맞으므로 위반은 아니지만, 이번 기록처럼 재생 월 한도가 이미 찬 상태에서 첫 호출부터 402가 나는 상황이 실제로 있었다(`docs/ops/ask-sample-replay.md` 해당 절). 이번 9개 실행은 실행 장애 0건이라 결과에는 영향이 없다.
   - 조치(권장): 연속 N턴 실행 장애, 또는 예약 없이 `error`로 끝난 턴(비용 0·호출 0)이 나오면 측정 장애처럼 실행을 멈추거나, 최소한 `_complete`가 실행 장애 비율 상한을 보게 한다.

4. **`spent_since`가 자체 루프백 검사 없이 service 키를 보낸다** (심각도: 낮음)
   - 위치: `scripts/model_evidence_eval.py:995-1004`
   - 깨지는 것: 현재 두 호출자는 모두 `assert_loopback`을 거친 URL을 넘기므로 실제 경로는 안전하다. 키도 공개 데모 키다. 다만 함수가 모듈 수준 공개 함수라, 이후 다른 호출자가 검사 없이 부르면 service_role 헤더가 임의 호스트로 나간다.
   - 조치(권장): 함수 첫 줄에서 `replay.assert_loopback(stack)`을 다시 건다.

## 판정 근거

테넌트 경계를 넘는 경로는 없다. service_role 사용은 로컬 루프백 스택의 `service_role` 전용 집계 RPC 하나뿐이고 `workspace_id`를 명시해 거르며, Ask 재생과 호출별 비용 조회는 요청자 JWT로 RLS·함수 내 권한 검사를 그대로 받는다. 제품 API·워커·마이그레이션은 바뀌지 않았다. 그래서 `blocked`는 아니다. 그러나 요청받은 "조용한 실패" 범위에서 코드 수정으로 고칠 결함이 두 개 있다. 예외로 끝난 조건의 과금된 턴이 기록과 성적표에서 사라지는 경로(1번, 설계 D5 위반)와, 포트를 못 비운 이전 워커가 다음 모델을 대신 서빙해 인프라 장애가 되돌릴 수 없는 '모델 제외' 결과로 굳는 경로(2번)다. 두 경로 모두 이번 9개 실행 결과에는 영향이 없었지만(장애·측정 장애 0건), 재실행이나 다른 표본에서는 증거 기록이 조용히 틀어진다. 그래서 `needs_fix`로 판정한다. 3·4번은 권장 사항이며 재리뷰 통과 조건은 아니다.
