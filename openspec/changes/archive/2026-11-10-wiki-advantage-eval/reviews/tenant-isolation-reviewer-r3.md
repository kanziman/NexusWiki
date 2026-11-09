# Tenant Isolation 리뷰 — wiki-advantage-eval r3

- 판정: pass
- 대상: `33a4476` 위의 미커밋 작업 트리(`git diff main...HEAD`는 빈 diff다). worktree 격리 훅이 git 호출을 막아 파일을 직접 읽었다. 제품 코드는 메인 체크아웃과 `diff -rq`로 비교했다
- 일시: 2026-11-09T23:34:18Z

## 범위

- r2 이후 바뀐 것(스펙 리뷰 r2 반영): `scripts/model_evidence_eval.py`
  - `build_ingestion`이 `FINAL_FAILURE_STATES = {dead, canceled}`만 실패로 세고, `failed`는 미완료(`pending`)로 센다(`:280-289`, `:319`)
  - `recovered_jobs`가 2xx 재시도 호출만 세고, `attempts > 1`로 끝난 성공 잡(워커 자동 재시도)을 함께 남긴다(`:322-351`)
  - `ingest-record`의 jobs 조회에 `attempts` 열을 넣었다(`:1749-1754`)
  - 테스트: `test_recovered_jobs_listed_and_do_not_block`(`apps/worker/tests/test_model_evidence_eval_script.py:1032`), `test_failed_status_waiting_for_auto_retry_is_unfinished_not_failed`(`:1071`)
- 바뀌지 않은 것: `supabase/migrations/` · `apps/api/src/` · `apps/worker/src/`. `diff -rq` 출력이 없다. 마이그레이션 최대 번호는 그대로 `0036`이다
- 테스트: `apps/worker`에서 `uv run pytest -q tests/test_model_evidence_eval_script.py tests/test_ask_replay_script.py`를 새로 돌려 148개가 통과했다

## 이번 변경의 핵심 질문: `failed`를 미완료로 바꾼 뒤에도 재생 차단이 유지되는가

유지된다. 분류는 이름만 바뀌었고, 닫힌 쪽으로 실패하는(fail-closed) 성질은 그대로다.

- `failed`(`0003_jobs.sql:17`: "종착점이 아니라 백오프 후 재시도 예정")는 이제 `pending`에 들어가 `reasons`에 "끝나지 않은 잡 N개"를 남긴다. `reasons`가 비어 있지 않으면 `ok: false`다(`model_evidence_eval.py:288-289`, `:313`). 그러면 `replay_cap`이 `SystemExit`로 멈추고(`:356-359`), `cmd_ingest_record`는 1을 돌려준다(`:1782`). 이 경로는 테스트로 고정됐다(`test_model_evidence_eval_script.py:1071-1082`)
- `pending`은 허용 목록이 아니라 여집합으로 정의된다(`not in FINAL_FAILURE_STATES | {"succeeded"}`, `:283`). 그래서 `queued` · `running` · `failed`뿐 아니라 스키마 밖의 값이나 `status`가 없는 행까지 전부 막힌다. 열린 쪽으로 새는 상태값은 없다. 허용되는 값은 `0009_pipeline_ops.sql:71`의 CHECK 6종이다
- `ok: true`가 되려면 모든 잡이 `succeeded`여야 한다. 이 조건은 r2와 같다
- `failed_jobs`(기록 필드)에는 이제 `failed`가 빠진다. 하지만 `failed_jobs`를 읽어 판정하는 곳이 없다. 판정은 `ok` 하나로만 한다(`:356`). 그래서 이 필드 변화가 관문을 열지는 않는다
- `cmd_retry_dead`의 drain은 원래부터 `failed`를 끝난 상태로 보지 않았다(`done = {succeeded, dead, canceled}`, `:1690`). 이번 분류는 그 drain과 같은 쪽으로 맞춰진 것이다

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 제품 요청 경로는 바뀌지 않았다. 이번 변경은 평가 스크립트의 service_role 읽기 조회에 열 하나를 더한 것뿐이다. 재시도 경로(요청자 JWT → `POST /workspaces/{ws}/jobs/{id}/retry`, `:1713-1718`)도 r2와 같다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 마이그레이션 변경 없음 |
| A-3 | `anon` 신규 GRANT · 정책 | 해당 없음 | 마이그레이션 변경 없음 |
| A-4 | service_role 코드의 명시적 `workspace_id` 필터 | 통과 | `ingest-record`의 jobs 조회는 `attempts`를 더한 뒤에도 `workspace_id=eq.{workspace}` 필터와 `select_capped`를 그대로 거친다(`:1749-1754`). `select_capped`는 `_select`를 거치므로 필터 키가 없으면 거부된다. 스택 URL은 `assert_loopback`을 거친다(`:1744`). 또 `recovered_jobs`는 결과를 이 필터된 `jobs`에 있는 id로만 내놓는다(`if job_id in final`, `:350`). 그래서 `job-retries.jsonl`에 다른 state나 다른 워크스페이스의 잡 id가 섞여도 기록에 들어가지 않는다 |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | API 변경 없음. 도구 쪽에서 `retry_dead_job`의 0행 no-op은 비-2xx 응답이 된다. 이 응답은 이제 `api_retries`에 세지 않는다(`:334-335`). 이 수정으로 r2 참고 2번이 해결됐다 |
| B-7 | 42501 → 403 매핑 | 해당 없음 | API 변경 없음 |
| C-8 | 재실행 안전성 | 통과 | `recovered_jobs`는 순수 함수다. 같은 입력이면 같은 결과를 낸다. `job-retries.jsonl`은 계속 append-only이고, `ingestion.json`은 계속 `write_new`와 존재 검사로 덮어쓰지 않는다(`:1740-1742`, `:1780`). 같은 잡의 2xx 줄이 여러 개여도 `setdefault`로 한 항목에 모인다. 잡이 중복으로 생기지 않는다 |
| C-9 | `jobs` 직접 UPDATE 금지 | 통과 | 이번 변경은 `jobs`를 읽기만 한다(`select` 열 추가). 쓰기 경로는 새로 생기지 않았다 |
| D-10 | `hnsw.iterative_scan = strict_order` | 해당 없음 | 검색 질의 변경 없음 |
| D-11 | 색인 · 질의 토크나이저 동일 | 해당 없음 | 토크나이저 · 색인 경로 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | 스키마 변경 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 템플릿 변경 없음 |
| D-14 | LLM 컨텍스트 인용 앵커 | 해당 없음 | 컨텍스트 조립 변경 없음 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션 없음(최대 `0036`) |
| 추가 | 조용한 실패: `failed` 재분류로 재생 차단이 새는가 | 통과 | 위 「핵심 질문」 절 참고. `failed`는 `ok: false`로 계속 막히고, 여집합 정의라 모르는 상태값도 막힌다 |
| 추가 | 조용한 실패: 복구 기록이 판정을 바꾸는가 | 통과 | `recovered`는 기록 필드일 뿐이다. `reasons`나 `ok` 계산에 들어가지 않는다(`:285-293`). 복구 잡이 있어도 관문이 열리거나 닫히지 않는다. 테스트 `:1058-1068`이 이를 확인한다 |

## 조치가 필요한 항목

없음.

## 참고(판정에 반영하지 않음)

1. **`worker_attempts`에는 실패가 아닌 재획득도 섞인다.** `claim_job`은 잡을 잡을 때 `attempts`를 올린다(`0003_jobs.sql:116`, `0023_job_trace.sql:54`). `reap_stale_jobs`는 이 값을 되돌리지 않는다(`0009_pipeline_ops.sql:21` "attempts 유지"). 그래서 락 타임아웃으로 회수됐다가 다시 잡혀 성공한 잡도 `attempts = 2`가 되어 `recovered_jobs`에 "워커 자동 재시도"로 남는다(`model_evidence_eval.py:342-346`). 이 잡은 실제로 `failed`를 거치지 않았다. 기록의 정확도 문제일 뿐 관문이나 격리에는 영향이 없다. `verification.md`나 docstring(`:329`)에 "reap 뒤 재획득 포함"이라고 적어 두면 해석이 틀어지지 않는다.
2. **`ask_replay.py`의 `_FAILED_JOB_STATES`에는 아직 `failed`가 들어 있다**(`scripts/ask_replay.py:81`, `:972`). 그래서 `ask_replay`의 시드 대기는 `failed`를 보면 곧바로 실패로 끝내고, `model_evidence_eval`은 기다린다. 두 도구의 분류가 다르다. 하지만 `ask_replay` 쪽이 더 보수적이라(닫힌 쪽으로 실패) 데이터가 새지는 않는다. 일관성이 필요하면 spec-conformance 쪽에서 판단할 사안이다.
3. r2 참고 1번(`retry-dead`가 잡이 0개여도 0을 돌려줌)과 3번(`cmd_retry_dead` · `cmd_register` 워크스페이스 불일치 테스트 없음)은 그대로 남아 있다. 둘 다 다음 단계 `ingest-record`가 막으므로 재생까지 새지 않는다.

## 판정 근거

이번 변경은 평가 스크립트 하나에서 잡의 분류와 기록만 바꾼다. service_role 조회는 열 하나가 늘었을 뿐이고, 명시적 `workspace_id` 필터 · 1000행 절단 거부 · 루프백 강제가 그대로 걸려 있다. 복구 기록은 이 필터된 잡 집합에 묶여 있어서, 다른 워크스페이스의 재시도 기록이 섞일 수 없다. `failed`를 실패에서 미완료로 옮겼어도 재생 관문은 열리지 않는다. 관문은 "모든 잡이 `succeeded`"라는 여집합 조건으로 판정하고, 미완료 역시 `ok: false`이기 때문이다. 이 경로는 회귀 테스트로 고정됐다. 제품 코드와 마이그레이션은 바뀌지 않았다. 새로 나온 것은 기록 정확도에 관한 참고 사항뿐이라 pass로 판정한다.
