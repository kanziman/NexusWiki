# Tenant Isolation 리뷰 — wiki-advantage-eval r2

- 판정: pass
- 대상: `33a4476` 위의 미커밋 작업 트리(`git diff main...HEAD`는 빈 diff다). worktree 격리 훅이 git 호출을 막아 파일을 직접 읽고, 제품 코드는 메인 체크아웃과 `diff -rq`로 비교했다
- 일시: 2026-11-09T23:30:03Z

## 범위

- 변경: `scripts/ask_replay.py` · `scripts/model_evidence_eval.py` · `scripts/retrieval_ablation.py` · `scripts/ask_replay_serve.sh` · 테스트 2개 · `docs/ops/ask-sample-replay.md` · `scripts/fixtures/wiki_advantage.v1.json` · change 문서
- r1 이후 새로 생긴 것: `select_capped`(`ask_replay.py:945-956`), `typed_sample_warnings`(`ask_replay.py:1084-1096`), `build_ingestion`의 미완료 잡 검사 · `workspace_id` · `recovered_jobs`(`model_evidence_eval.py:264-338`), `cmd_retry_dead`(`model_evidence_eval.py:1665-1721`), `cmd_register`의 워크스페이스 대조(`:1797-1800`), `overall_verdict`의 측정 장애 규칙(`:1040-1051`)
- 바뀌지 않음(`diff -rq`, 출력 없음): `supabase/migrations/` · `apps/api/src/` · `apps/worker/src/`. 마이그레이션 최대 번호 `0036` 그대로
- 테스트: `apps/worker`에서 `uv run pytest -q tests/test_model_evidence_eval_script.py tests/test_ask_replay_script.py`를 새로 돌렸다. 146 passed

## r1 지적 처리

| r1 # | 지적 | 결과 | 근거 |
| --- | --- | --- | --- |
| 1 | `ingest-record`가 끝나지 않은 잡을 성공으로 기록 | 해결 | `build_ingestion`이 종료 상태 밖의 잡을 `pending`으로 세고 "끝나지 않은 잡 N개"를 `reasons`에 넣는다(`model_evidence_eval.py:281-291`). `failed`(자동 재시도 대기)는 `_FAILED_JOB_STATES`에 들어 실패로 막힌다. 어느 쪽이든 `ok: false`다. 회귀 테스트 `test_ingestion_with_pending_job_is_not_ok`(`test_model_evidence_eval_script.py:1001`). 재시도 이력은 `job-retries.jsonl` → `recovered_jobs`로 기록에 남는다(`:323-338`, `:1765`) |
| 2 | service_role 집계 조회의 1000행 절단 | 해결 | `select_capped`가 `POSTGREST_MAX_ROWS` 이상이면 멈춘다(`ask_replay.py:953-955`). 적용: `_wait_for_jobs`(`:965`), `_usage_total`(`:985`), `ingest-record`의 jobs · wiki_pages · raw_sources · usage_events 4건(`model_evidence_eval.py:1736-1753`), `retry-dead`의 drain(`:1682`). `supabase/config.toml:18` `max_rows = 1000`과 상수가 맞다. 테스트 `test_capped_select_refuses_truncated_aggregate`(`:1018`) |
| 3 | 예산 · 수집 기록이 워크스페이스에 묶이지 않음 | 해결 | `ingestion.json`에 `workspace_id`를 쓰고(`:302`, `:1764`), `register`가 state와 다르면 멈춘다(`:1798-1800`). `recorded is None`이면 통과하는데, 이는 고치기 전 코드로 만든 실측 기록 하나 때문이며 `verification.md:53`에 그 사실과 수동 확인(잡 174개 전부 `succeeded`)이 적혀 있다. 지금 코드의 `ingest-record`는 항상 값을 쓴다 |
| 참고 | 전체 판정과 측정 장애 | 해결 | `overall_verdict`가 `measurement_failure`면 지지 모델 수와 무관하게 `inconclusive`(`:1045-1046`). 호출부가 일관 줄만 모아 모델별 장애 합계로 넘긴다(`:1128-1142`). 테스트 `:1025` |

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 제품 요청 경로 변경 없음. 새 `retry-dead`의 재시도 호출은 `_login`으로 받은 요청자 JWT로 제품 API `POST /workspaces/{ws}/jobs/{id}/retry`를 부른다(`model_evidence_eval.py:1700-1705`). 라우터는 `_user_db`로 `retry_dead_job`을 부르고(`apps/api/src/api/routers/jobs.py:183-184`), 이 함수는 잡의 **실제** 워크스페이스에 대해 editor 역할을 검사한다(`0009_pipeline_ops.sql:425-430`). `authenticated`에만 실행 권한이 있다(`:553-557`) |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 마이그레이션 변경 없음 |
| A-3 | `anon` 신규 GRANT · 정책 | 해당 없음 | 마이그레이션 변경 없음 |
| A-4 | service_role 코드의 명시적 `workspace_id` 필터 | 통과 | 새 service_role 조회는 `retry-dead` drain 하나이며 `workspace_id=eq.{workspace}`를 건다(`:1686`). `select_capped`는 `_select`를 거치므로 필터 키가 없으면 `ValueError`다(`ask_replay.py:808-809`). 스택 URL과 API URL 둘 다 `assert_loopback`을 거친다(`:1674-1675`). 재시도할 잡 id는 이 필터된 조회에서만 나오고, 설령 state가 잘못돼도 제품 RPC의 editor 검사와 라우터의 워크스페이스 단언(`jobs.py:188`)이 다른 테넌트의 잡 재시도를 막는다 |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | API 변경 없음. 도구 쪽: `retry_dead_job`의 0행(dead 아님)은 라우터가 `JobNotRetryable`로 바꾸고, 도구는 상태 코드를 `job-retries.jsonl`에 남긴 뒤 최종 잡 상태로 판단한다. 재시도가 거부돼도 잡은 dead로 남아 `retry-dead`가 1을 돌려주고 `ingest-record`가 `ok: false`로 막으므로 조용히 성공으로 넘어가지 않는다 |
| B-7 | 42501 → 403 매핑 | 해당 없음 | API 변경 없음 |
| C-8 | 재실행 안전성 | 통과 | (a) 중복 재시도: `retry_dead_job`은 `status = 'dead'`인 행만 바꾸므로, 이미 `queued`로 되돌린 잡에 다시 불러도 attempts가 다시 초기화되거나 잡이 늘지 않는다(`0009:432-446`, 주석 `:453`). `retry-dead`를 두 번 돌리거나 동시에 돌려도 DB 상태는 같다. (b) 같은 대상의 살아 있는 잡이 있으면 `jobs_dedup_idx`가 23505로 막는다. 이 경우 소란스럽게 실패하고 그 결과도 기록된다. (c) 기록: `job-retries.jsonl`은 `append_line`(`open("a")`, 앞선 줄을 읽거나 고치지 않음, `:844-848`)이고, `ingestion.json` · `budget.json` · 등록은 `write_new`(`open("x")`)와 존재 검사로 덮어쓰지 않는다(`:134-141`, `:1650`, `:1728`, `:1775`). (d) 체인 잡은 `complete_job_and_chain` 한 트랜잭션에서 다음 단계를 넣으므로(`apps/worker/src/worker/db/service.py:833-854`), drain이 "전부 끝남"을 본 순간 다음 단계가 아직 안 들어간 틈은 없다 |
| C-9 | `jobs` 직접 UPDATE 금지 | 통과 | 스크립트에 jobs 쓰기 경로가 없다(`/rest/v1/jobs` 쓰기 · `.patch(` · `.delete(` · `update public.jobs` 검색 0건). 재시도는 제품 API → `retry_dead_job` RPC뿐이다 |
| D-10 | `hnsw.iterative_scan = strict_order` | 해당 없음 | 검색 질의 변경 없음. 도구는 제품 `RetrievalService`를 그대로 쓴다 |
| D-11 | 색인 · 질의 토크나이저 동일 | 해당 없음 | 토크나이저 · 색인 경로 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | 스키마 변경 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 템플릿 변경 없음 |
| D-14 | LLM 컨텍스트 인용 앵커 | 해당 없음 | 컨텍스트 조립은 제품 `AskService`를 그대로 쓴다 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션 없음(최대 `0036`) |
| 추가 | 조용한 실패: 재시도 중 잡을 성공으로 기록 | 통과 | `retry-dead` drain은 `failed`를 끝난 상태로 보지 않고 기다린다(`:1677`, `:1688`). 재시도 직후 잡은 `queued`이므로 drain이 다시 기다린다. 마지막에 성공이 아닌 잡이 남으면 1을 돌려준다(`:1719-1721`). 이를 무시하고 `ingest-record`를 돌려도 r1 1번 수정이 막는다 |
| 추가 | `typed_sample_warnings` | 해당 없음(격리 무관) | 경고 출력만 하고 반환 코드 · 기록에 영향이 없다(`ask_replay.py:1106-1107`). 시험지 구성은 spec-conformance 쪽에서 볼 사안이다 |
| 추가 | SQL 삽입(`_set_monthly_budget`) | 통과(r1과 같음) | UUID 정규화 · 0 이상 int만 받고, 리스트 인자 `subprocess.run`이라 셸을 거치지 않는다(`ask_replay.py:1122-1133`) |

## 조치가 필요한 항목

없음.

## 참고(판정에 반영하지 않음)

1. **`retry-dead`가 잡이 하나도 없을 때 성공으로 끝난다.** `all([])`이 참이라 drain이 바로 돌아오고 "남은 실패 잡 0개" · 반환 0이 된다(`model_evidence_eval.py:1688`, `:1719-1721`). state를 잘못 넘긴 경우 등에 해당한다. 다음 단계 `ingest-record`가 위키 0쪽으로 `ok: false`를 내므로 재생까지 새지는 않는다. `rows`가 비면 멈추게 하면 신호가 한 단계 앞당겨진다.
2. **`recovered_jobs`의 `retries`가 거부된 재시도 호출도 센다.** 상태 코드를 보지 않고 줄 수를 센다(`:330-333`). 동시 실행이나 중복 실행으로 0행 no-op(비-2xx)이 기록되면 재시도 횟수가 부풀려진다. 판정 관문에는 영향이 없고 기록의 정확도 문제다. 2xx만 세거나 상태 코드별로 나누면 된다.
3. **회귀 테스트가 비어 있는 두 경로.** `cmd_retry_dead`(dead만 재시도 · `failed` 대기 · 남은 실패 시 1)와 `cmd_register`의 워크스페이스 불일치 거부에는 테스트가 없다. 지금 코드는 읽어서 맞지만, 둘 다 조용한 실패를 막는 관문이니 테스트로 고정해 두길 권한다.
4. `_select`의 가드는 여전히 `workspace_id` 키가 있는지만 보고, 값이 `eq.`로 시작하는지는 보지 않는다(r1 참고 그대로). 지금 service_role 호출부는 모두 `eq.<uuid>`다.
5. 스펙(`specs/wiki-advantage-evaluation/spec.md:27`)의 "failed and was recovered through the product's retry path"에 워커 자동 재시도(`failed` → `succeeded`)도 들어가는지는 해석 문제다. `recovered_jobs`는 `job-retries.jsonl`에 있는 수동 재시도만 기록한다. `verification.md:56`도 자동 재시도로 복구된 `failed` 1개를 따로 적었다. spec-conformance 리뷰어 몫으로 남긴다.

## 판정 근거

r1의 세 지적(미완료 잡의 성공 기록, 1000행 절단, 워크스페이스에 묶이지 않은 수집 기록)과 전체 판정 규칙이 모두 코드와 회귀 테스트로 해결됐다. 새 `retry-dead` 경로는 service_role을 루프백 강제와 명시적 `workspace_id` 필터를 거친 잡 상태 읽기에만 쓴다. 재시도 자체는 요청자 JWT로 제품 API를 타며, 그 RPC가 잡의 실제 워크스페이스에 대해 editor 역할을 검사하므로 테넌트 경계를 넘을 수 없다. `jobs`는 직접 고치지 않는다. 중복 재시도는 RPC 수준에서 0행 no-op이고, 기록은 append-only다. 재시도가 실패하거나 거부돼도 최종 잡 상태로 판정되므로 조용히 성공으로 넘어가지 않는다. 제품 코드와 마이그레이션은 바뀌지 않았다. 남은 것은 신호를 앞당기거나 기록 정확도를 높이는 참고 사항뿐이라 pass로 판정한다.
