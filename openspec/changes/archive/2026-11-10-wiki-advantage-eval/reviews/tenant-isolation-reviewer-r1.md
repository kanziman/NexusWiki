# Tenant Isolation 리뷰 — wiki-advantage-eval r1

- 판정: needs_fix
- 대상: `33a4476` 위의 미커밋 작업 트리(`git diff main...HEAD`는 빈 diff다). worktree 격리 훅이 git 호출을 막아서, 메인 체크아웃 파일과 `diff`로 범위를 확인하고 파일을 직접 읽었다
- 일시: 2026-11-09T16:44:03Z

## 범위

- 변경: `scripts/ask_replay.py` · `scripts/model_evidence_eval.py` · `scripts/retrieval_ablation.py`(금지 사실 판정 2곳) · `scripts/ask_replay_serve.sh` · 테스트 2개 · `docs/ops/ask-sample-replay.md` · 신규 `scripts/fixtures/wiki_advantage.v1.json` · change 문서
- 바뀌지 않음(`diff -rq`로 확인): `supabase/migrations/` · `apps/api/src/` · `apps/worker/src/`
- 실측 중 재시도에 쓴 스크래치 스크립트는 커밋 대상이 아니어서 코드로는 확인하지 못했다. 경로가 제품 API `POST /workspaces/{ws}/jobs/{id}/retry`라는 사실만 확인했다(`apps/api/src/api/routers/jobs.py:176` → `retry_dead_job`, 요청자 JWT, editor 검사 후 42501)

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 제품 요청 경로는 바뀌지 않았다. 도구 안의 Ask 턴은 요청자 JWT(`UserDb(access_token=self.token)`, `model_evidence_eval.py:1512`)로 돈다. service_role은 로컬 재생 스택 집계 조회(`ask_replay.py:795` `_select`, `model_evidence_eval.py:1403` `spent_since`)에만 쓰고, 둘 다 `assert_loopback`을 거친다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 마이그레이션 변경 없음 |
| A-3 | `anon` 신규 GRANT·정책 | 해당 없음 | 마이그레이션 변경 없음 |
| A-4 | service_role 코드의 명시적 `workspace_id` 필터 | 통과 | `ingest-record`의 jobs · wiki_pages · raw_sources · usage_events 조회(`model_evidence_eval.py:1622-1639`) 모두 `eq.{workspace}`. `_select`가 필터 키 없는 조회를 거부한다(`ask_replay.py:808`). `sum_usage_events_since`는 함수 본문이 `e.workspace_id = p_workspace_id`로 거른다(`0027_ask_cost_accounting.sql:76-77`). psql UPDATE도 `where id = '<uuid>'` 한 행이다. 다만 아래 5번 참고: 필터 값의 모양은 검사하지 않는다 |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | API 변경 없음. 도구 쪽 psql UPDATE는 `returning`의 첫 줄이 설정값과 같지 않으면(0행 포함) 멈춘다(`ask_replay.py:1102-1103`). 잘못된 컨테이너를 줘도 그 DB에는 이 워크스페이스가 없어 0행 → 중단이므로 조용히 넘어가지 않는다 |
| B-7 | 42501 → 403 매핑 | 해당 없음 | API 변경 없음 |
| C-8 | 핸들러 재실행 안전성 | 통과 | 새 잡 핸들러 없음. 도구 기록은 append-only다: `write_new`가 `open("x")`로 덮어쓰기를 막고(`model_evidence_eval.py:134-141`), `budget-open`/`ingest-record`/`register`가 각각 기존 파일이 있으면 멈춘다(1596, 1615, 1659) |
| C-9 | `jobs` 직접 UPDATE 금지 | 통과 | 스크립트에 jobs 쓰기 경로 없음(PATCH/DELETE/`update` 검색 결과는 `workspaces` UPDATE 1건뿐). dead 잡 복구는 `retry_dead_job` RPC를 쓰는 제품 API로 했다 |
| D-10 | `hnsw.iterative_scan = strict_order` | 해당 없음 | 검색 질의 변경 없음. 도구는 제품 `RetrievalService`를 그대로 쓴다 |
| D-11 | 색인/질의 토크나이저 동일 | 해당 없음 | 토크나이저 · 색인 경로 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | 스키마 변경 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 템플릿 변경 없음 |
| D-14 | LLM 컨텍스트 인용 앵커 | 해당 없음 | 컨텍스트 조립은 제품 `AskService`를 그대로 쓴다 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션 없음(최대 `0036`) |
| 추가 | SQL 삽입(`_set_monthly_budget`) | 통과 | 워크스페이스는 `str(UUID(...))`로 정규화하고 금액은 `int`(argparse `type=int`) · 0 이상만 받는다(`ask_replay.py:1091-1093`). 문자열에 들어갈 수 있는 값이 UUID 문자와 숫자뿐이다. `subprocess.run`은 리스트 인자라 셸을 거치지 않는다 |
| 추가 | 조용한 실패 — 잡 실패가 성공으로 셈 | **위반** | `build_ingestion`이 끝나지 않은 잡을 실패로 보지 않는다(아래 1번) |
| 추가 | 조용한 실패 — PostgREST 1000행 절단 | 주의 | service_role 집계 조회에 행 수 상한 검사가 없다(아래 2번) |
| 추가 | 지출 집계 | 통과(주의 1건) | `spent_since`는 RPC 합계라 절단되지 않고, 미정산 예약은 예약액으로 센다. 다만 예산 기록이 워크스페이스에 묶여 있지 않다(아래 3번) |
| 추가 | `ASK_REPLAY_RESERVE_MICROS` | 통과 | 검증 없이 JSON에 삽입되지만(`ask_replay_serve.sh:46-47`), 숫자가 아니면 설정 파싱이 기동 시 실패하므로 조용히 넘어가지 않는다. 로컬 546xx 스택에만 붙는다 |

## 조치가 필요한 항목

1. **`ingest-record`가 끝나지 않은 잡을 성공으로 기록한다** (심각도: 보통)
   - 위치: `scripts/model_evidence_eval.py:274-299`(`build_ingestion`), 호출부 `:1611-1653`
   - 깨지는 것: `failed`는 `dead`·`failed`·`canceled`만 센다. 그래서 `queued`나 `running` 잡이 남아 있어도 `ok: true`가 기록된다. 이번 실측이 바로 그런 흐름이었다. `seed`의 `_wait_for_jobs`는 dead 잡을 만나면 바로 `SystemExit`로 끝나고(`ask_replay.py:958-960`), 그 뒤 제품 API로 재시도했다. 재시도한 잡이 끝났는지 기다리는 장치는 도구에 없다. `retry_dead_job`은 같은 행을 `queued`로 되돌리고 `last_error`를 지운다(`0009_pipeline_ops.sql:432-442`). 이 상태에서 `ingest-record`를 돌리면 잡은 아직 queued인데 `ok: true`가 된다. 그 잡이 나중에 다시 dead가 되면 임베딩이 빠진 수집 위에서 재생이 계획되고, 스펙 "MUST NOT start answer replay when any ingestion job failed"가 아무 경고 없이 무너진다. 이 과정은 append-only라 다시 판정되지도 않는다. 재수집 뒤라면 스냅샷 지문 불일치로 드러나지만, 잡이 dead로 끝나면 스냅샷이 바뀌지 않아 지문으로도 잡히지 않는다.
   - 조치: `build_ingestion`에서 `status not in replay._TERMINAL_JOB_STATES`인 잡을 따로 세고, 하나라도 있으면 `reasons`에 "끝나지 않은 잡 N개"를 넣는다(`ok: false`). 회귀 테스트 1건(queued 잡 → `ok` false)을 추가한다. 재시도된 잡은 `last_error`가 지워져 기록에 남지 않으므로, 가능하면 `attempts`도 함께 읽어 기록하거나 verification에 재시도 사실을 남긴다(지금은 verification.md:51 서술에만 있다).

2. **service_role 집계 조회가 1000행에서 조용히 잘릴 수 있다** (심각도: 보통 · 지금 데이터에서는 미발현)
   - 위치: `scripts/ask_replay.py:795-817`(`_select`), 사용처 `:951`(`_wait_for_jobs`), `:971`(`_usage_total`), `model_evidence_eval.py:1622-1639`(`ingest-record`)
   - 깨지는 것: `select_all`에는 `POSTGREST_MAX_ROWS` 검사가 있지만(`ask_replay.py:855`), `_select`를 직접 부르는 집계 경로에는 없다. 행이 1000개를 넘으면 PostgREST가 오류 없이 자르고, 순서 지정도 없어 어느 행이 빠질지 모른다. 그러면 세 가지가 조용히 틀린다. (a) 잘린 바깥의 dead 잡을 보지 못해 `seed`와 `ingest-record`가 성공한다. (b) 다른 컴파일 모델의 usage 행이 빠져 `compile_models_used` 검사를 통과한다. (c) `_usage_total`이 지출을 적게 센다. 이번 시도는 잡 174, 사용량 행 576이라 발현하지 않았지만, 시험지를 두 배로 키우면 닿는다.
   - 조치: `_select`(적어도 token 없는 service_role 경로)에서 `len(rows) >= POSTGREST_MAX_ROWS`이면 멈추게 하거나, `Prefer: count=exact`로 받은 총수와 비교한다.

3. **예산 · 수집 기록이 워크스페이스에 묶여 있지 않다** (심각도: 낮음)
   - 위치: `scripts/model_evidence_eval.py:235-300`(`build_budget` · `build_ingestion`), `:1681-1685`(`cmd_register`)
   - 깨지는 것: `ingestion.json`에는 `workspace_id`가 없다. `register`는 `--state`로 받은 워크스페이스로 `spent_since(EPOCH)`를 다시 잰다. 수집과 다른 state 파일을 넘기면 다른 워크스페이스의 지출(새 워크스페이스라면 0)로 재생 상한을 계산하므로 총 상한이 부풀어도 아무 신호가 없다. 제품 월 한도는 psql로 한도를 낮춘 그 워크스페이스에만 걸리므로 이 경우에는 막아 주지 않는다.
   - 조치: `ingestion.json`에 `workspace_id`(그리고 `monthly_budget_micros` 설정값)를 기록하고, `register`에서 state의 워크스페이스와 다르면 멈춘다.

## 참고(판정에 반영하지 않음)

- `_select`의 가드는 `"workspace_id" in params`처럼 키가 있는지만 본다(`ask_replay.py:808`). 지금 service_role 호출부는 모두 `eq.<uuid>`를 쓰지만 `is.null`이나 `neq.`를 넘겨도 통과한다. token이 없는 경로에서는 값이 `eq.`로 시작하는지까지 확인하는 편이 안전하다.
- `design.md:68`에는 아직 "로컬 service_role, `workspace_id` 필터"로 한도를 낮춘다고 적혀 있다. 이는 같은 파일 `:71`과 verification.md:48(psql로 변경)과 어긋난다. 근거 문서 정합 문제라 spec-conformance 쪽에서 볼 사안이다.
- `overall_verdict`는 한 모델에 측정 장애가 있어도 다른 모델들이 `min_models`를 채우면 `supported`를 낸다(`model_evidence_eval.py:1002-1008`). 스펙의 "when any model has a measurement failure" 문구를 전체 판정에도 걸리게 읽으면 어긋난다. 해석 문제이므로 spec-conformance 리뷰어에게 넘긴다. 이번 실측 결과(`not_supported`)는 바뀌지 않는다.

## 판정 근거

테넌트 경계를 넘는 경로는 없다. 제품 API · 워커 · 마이그레이션이 바뀌지 않았고, 도구의 service_role 사용은 모두 루프백 강제와 명시적 `workspace_id` 필터 아래에 있다. psql 직접 쓰기도 UUID · 정수만 받는 단일 행 UPDATE이며, 0행이면 멈춘다. jobs는 제품 RPC로만 건드렸다. 그래서 blocked는 아니다. 그러나 1번은 호출자가 지정한 검사 대상인 "잡 실패가 성공으로 세지는 경로"에 그대로 해당한다. 이번 실측이 정확히 그 흐름(dead → 수동 재시도 → 종료 대기 없이 ingest-record)을 밟았고, 기록은 append-only라 사후에 바로잡히지 않는다. 2번도 같은 종류의 조용한 실패이며, 둘 다 몇 줄의 코드 수정과 테스트로 해결된다. 따라서 needs_fix로 판정한다.
