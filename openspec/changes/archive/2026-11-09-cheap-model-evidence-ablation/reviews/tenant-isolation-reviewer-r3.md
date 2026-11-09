# Tenant Isolation 리뷰 — cheap-model-evidence-ablation r3

- 판정: pass
- 대상: 미커밋 작업 트리(`git diff` + 미추적 파일), 기준 `HEAD` = `ceaa4ab17b6020fa2cbd46baea669dfaf0c89974`
  - 수정: `scripts/ask_replay_serve.sh`, `docs/ops/ask-sample-replay.md`
  - 신규: `scripts/model_evidence_eval.py`, `scripts/model_evidence_run.sh`, `apps/worker/tests/test_model_evidence_eval_script.py`, `openspec/changes/cheap-model-evidence-ablation/`
- 일시: 2026-11-09T11:26:02Z
- 검증(새로 실행):
  - `uv run --package worker pytest -q apps/worker/tests/test_model_evidence_eval_script.py` → 36 passed
  - `uv run ruff check scripts/model_evidence_eval.py apps/worker/tests/test_model_evidence_eval_script.py` → 통과
  - r2 재현 시나리오를 `enrich_turn` → `judge` → `summarize_rows`로 직접 다시 돌렸다(아래 표)

## r2 지적 반영 확인

| r2 # | 지적 | 결과 | 근거 |
| --- | --- | --- | --- |
| 1 | 거절 문항(`q30`)의 실행 장애가 거절 판정으로 집계됨 | 해결 | `judge`가 `ablation.answer_verdict`로 넘기기 전에 `failed_channels`(`scripts/model_evidence_eval.py:406-411`)와 상태 `{resolved, fallback, no-evidence}` 밖(`:412-413`)을 문항 종류와 무관하게 `execution_failure`로 거른다. `summarize_rows`의 거절 분모가 `not_run`·`measurement_failure`·`execution_failure`를 뺀다(`:432-438`). 재현 결과: `q30` `error`(호출 없음 / 정산된 호출 있음), `q30` `unknown`, `q30` `no-evidence`+채널 실패는 모두 `execution_failure`이고 `refusal_total`에 들지 않는다. 장애 없는 `q30` `no-evidence`는 그대로 `refusal_correct`다. 고정 테스트 `test_refusal_question_failure_is_execution_failure`(두 경우 매개변수화) |
| 2 | 예외가 난 그 턴이 `not_run`(비용 0)으로 기록됨 (권장) | 해결 | `run_condition_turns`가 `run_turn` 예외 시 그 문항을 `status="interrupted"`, `measurement_failure="interrupted"`로 호출부 목록에 남기고 다시 던진다(`:502-521`). `fill_not_run`은 이미 있는 ID를 건너뛰므로(`:553-554`) 그 행을 덮지 않는다. 측정 장애가 1이 되어 `_complete`에서 빠지고(`:748-754`), `cmd_run`의 `stopped`도 채워진다(`:1474-1476`). `spent()` 조회 예외는 `try` 밖이라 호출이 없었던 턴은 그대로 `not_run`이 된다. 맞는 구분이다. 고정 테스트 `test_exception_mid_condition_keeps_charged_turns`의 상태 열 단언 |

### 재현 결과 (`judge(…, "both")`)

| 입력 | measurement_failure | 판정 |
| --- | --- | --- |
| `q30` · `error` · 호출 없음 | 없음 | `execution_failure` |
| `q30` · `error` · 정산된 호출 1 | 없음 | `execution_failure` |
| `q30` · `unknown` | 없음 | `execution_failure` |
| `q30` · `no-evidence` · `failed_channels=['fts']` | 없음 | `execution_failure` |
| `q30` · `no-evidence` · 장애 없음 | 없음 | `refusal_correct` |
| `q01` · `error` | 없음 | `execution_failure` |
| `q01` · `resolved` · `failed_channels=['fts']` | 없음 | `execution_failure` |

요약: `execution_failures 6`, `refusal_total 1`, `refusal_correct 1`, `fact_denominator 0`, `product_passed 0`.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 제품 API·워커 코드 변경 없음. Ask 재생은 `UserDb(access_token=self.token)`(`scripts/model_evidence_eval.py:1250-1255`), 호출별 비용 조회 `ask_cost_trace_calls`는 anon `apikey` + 요청자 JWT(`:1163-1167`). service 키는 `spent_since`의 `sum_usage_events_since` 한 곳(`:1141-1154`)이고, 이 RPC는 `service_role` 전용 grant 집계다. 사용자 요청 경로가 아니다. 이번 라운드 수정은 판정·요약 로직뿐이라 클라이언트 사용처는 r2와 같다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블·마이그레이션 없음 |
| A-3 | `anon` 신규 GRANT·정책 | 해당 없음 | DDL 변경 없음 |
| A-4 | service_role 코드의 `workspace_id` 필터 | 통과 | `spent_since`가 함수 첫 줄에서 `replay.assert_loopback`(`:1146`)을 하고 `p_workspace_id`를 명시해 넘긴다(`:1151`). 호출자(`Harness.spent` `:1227-1228`, `cmd_probe` `:1377`, `cmd_plan` `:1410`, `cmd_run` `:1450`·`:1479`)는 모두 `state.json`의 재생 워크스페이스 ID를 쓴다 |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | API 경로 변경 없음. 스크립트는 UPDATE/DELETE를 하지 않는다 |
| B-7 | `42501` → 403 매핑 | 해당 없음 | API 경로 변경 없음. `ask_cost_trace_calls` 거부는 `raise_for_status` 예외(`:1168`)가 되고, 이제 그 턴은 `interrupted` 측정 장애로 남는다 |
| C-8 | 핸들러 재실행 안전성 | 해당 없음(핸들러 없음) · 기록 측 통과 | 작업 핸들러 없음. 실행·점검·계획·미실행 기록은 모두 `open("x")`로 덮어쓰기를 거부한다(`:133-140`). `close`는 기록이 없는 계획 실행만 채운다(`:1529-1532`). r2와 같다 |
| C-9 | `jobs` 직접 UPDATE 금지 | 해당 없음 | `jobs` 접근 없음 |
| D-10 | `hnsw.iterative_scan = strict_order` | 해당 없음 | 새 벡터 질의 없음. 기존 `RetrievalService` 경로 |
| D-11 | 색인·질의 토크나이저 동일 | 해당 없음 | 토크나이저 변경 없음. 질의 벡터는 고정값이고 해시를 등록과 대조한다(`:1211-1222`) |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | DDL 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 신규 파일에 `.format(` 없음 |
| D-14 | 인용 앵커 동반 | 해당 없음 | 컨텍스트 조립 코드 변경 없음 |
| E-15 | 마이그레이션 번호 | 해당 없음 | 신규 마이그레이션 없음(최대 번호 `0036` 그대로) |
| 추가 | 판정 순서 변경이 답할 수 있는 문항에 주는 영향 | 통과 | 공용 `answer_verdict`는 답할 수 있는 문항의 상태·채널 장애를 이미 `execution_failure`로 분류했다(`scripts/retrieval_ablation.py:1114-1122`). 앞으로 당긴 검사의 분류는 같고, `pass`만 `False`에서 `None`으로 바뀐다. `product_passed`는 참인 `pass`만 세고(`:451-453`) 사실 분모는 분류로 거르므로(`:417-425`) 수치는 바뀌지 않는다. `#237` 참조 기록 재채점(`reference_conditions`, `:709-740`)도 같은 `judge`를 쓴다. 그래서 참조 줄과 이번 실행 줄의 거절 판정 기준이 같다 |
| 추가 | 거절 분모 0의 표시 | 통과(참고) | `q30`이 장애로 빠지면 성적표 칸은 `0/0`이 되고(`:1074`), 같은 줄의 실행 장애 칸이 1로 보인다(`:1063-1065`). 조용히 사라지지 않는다. 이 실행은 `stopped`가 없고 `asked == planned`라 완료 회차에 들어간다. 이것은 스펙의 "분모에서 빼되 센다" 규칙 그대로이며, 모델 간 비교는 사실 포함 짝 비교(`counts_for_fact`)라 장애 턴이 결과를 기울이지 않는다 |

## 조치가 필요한 항목

없음.

## 판정 근거

테넌트 경계를 넘는 경로는 없다. service_role은 루프백 스택의 `service_role` 전용 집계 RPC 하나에만 쓰이고 함수 안에서 루프백과 `workspace_id`를 모두 강제하며, Ask 재생과 호출별 비용 조회는 요청자 JWT를 쓴다. 제품 API·워커·마이그레이션은 바뀌지 않았다. r2의 `needs_fix` 항목(거절 문항의 장애가 거절 판정으로 새는 조용한 실패)은 `judge`의 사전 필터와 거절 분모 정리로 해결됐다. r2가 지적한 두 입력(`error`, 채널 실패 뒤 `no-evidence`)과 `unknown`, 정산된 호출이 있는 `error`까지 직접 재현했고, 모두 `execution_failure`로 분류되며 거절 분모에서 빠졌다. 권장 항목(예외 턴의 `interrupted` 기록)도 반영됐다. 이번 수정 때문에 새로 생긴 격리·오류 매핑·멱등성·조용한 실패 위험은 찾지 못했다. 그래서 `pass`로 판정한다.
