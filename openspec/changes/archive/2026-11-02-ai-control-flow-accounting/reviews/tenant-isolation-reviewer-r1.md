# Tenant Isolation 리뷰 — ai-control-flow-accounting r1

- 판정: **blocked**
- 대상: `git diff 79b68fe` + 추적되지 않은 신규 파일 (HEAD = `79b68fe`, 변경 전부 미커밋 작업 트리)
- 일시: 2026-11-02T08:05:56Z

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `apps/api/src`에 `service_client`·`service_role` 사용 없음(주석 1건뿐). `control.py`는 전부 `UserDb` |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블 없음. `0023`~`0026`은 컬럼·함수 추가뿐 |
| A-3 | `anon` 신규 GRANT·정책 | 통과 | 신규 함수 4개 모두 anon EXECUTE 없음(`has_function_privilege` 실측 f). anon 직접 호출·조회 42501 실측. 새 컬럼의 anon 권한은 기존 테이블 권한에서 파생된 `REFERENCES`뿐 |
| A-4 | service_role 코드의 `workspace_id` | **위반** | 필터 자체는 있으나 값이 **검증되지 않은 경로 파라미터**다. 지적 1 |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 자식 테이블 없음 |
| B-6 | 0행 → 403 | 통과 | 신규 쓰기 API 없음. `get_trace`의 0행은 `control.py:386`에서 명시적으로 403 |
| B-7 | 42501 → 403 | 통과 | `ask_trace_aggregate` 위반은 `errors.py:244-246`을 지나 403. 비멤버 42501 실측 |
| C-8 | 핸들러 재실행 안전성 | 통과 | upsert 키 변경 없음. 사용량은 호출마다 새 행이 스펙 계약이고, 저장 경로에 덮어쓰기 없음 |
| C-9 | `jobs` 직접 UPDATE 금지 | 통과 | `claim_job`, `complete_job_and_chain` 함수 내부 변경뿐. 워커 코드에 직접 UPDATE 없음 |
| D-10 | `hnsw.iterative_scan` | 해당 없음 | 벡터 RPC 변경 없음(`0011`, `0012` 설정 유지) |
| D-11 | 토크나이저 일치 | 해당 없음 | 색인·질의 토크나이저 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트 `str.format` | 통과 | 소스 추가분에 없음(테스트의 URL 포맷 3건만) |
| D-14 | 인용 앵커 | 통과 | 컨텍스트 조립 경로 변경 없음. 지표 계산만 `rendered_text`로 변경 |
| E-15 | 마이그레이션 번호 | 통과 | `0023`~`0026`은 저장소 최대 `0022` 다음. 클라우드 미적용이며 push 전 확인 절차가 `docs/ops/migration-0023-0026-record.md`에 있음 |

### 요청하신 지점별 결과

| 지점 | 결과 | 근거 |
| --- | --- | --- |
| 재생성 함수 권한 | 통과 | 로컬 `pg_proc` 실측. `enqueue_source_job`과 `ask_trace_aggregate`는 definer이며 `search_path=public`, `start_ask_turn`과 `finalize_ask_turn`은 invoker이며 EXECUTE는 authenticated와 postgres뿐. `claim_job`과 `complete_job_and_chain`은 invoker에 service_role 전용으로 유지 |
| 함수 본문 회귀 | 통과 | `0003`, `0007`, `0010`, `0019`의 직전 정의와 대조. 추가된 것은 trace 인자·컬럼과 `last_claimed_at`, `control_report`뿐 |
| `ask_trace_aggregate` 역할 확인 | 통과 | 첫 문장에서 editor 확인. viewer와 비멤버 42501 실측 |
| 집계의 사용자 식별 정보 | 통과, 일부 지적 | 반환 컬럼에 사용자·스레드·trace 없음. 결정 키는 허용 목록(`0026:60-61`). 단 지적 2, 9 |
| `control.py` 접근 순서 | 통과 | Ask(RLS) → editor → jobs → 403, `usage_events`는 게이트 뒤(`:333`, `:376`). RLS가 작성자와 현재 멤버십을 함께 요구(`0018:98-108`)하므로 비작성자와 멤버십 상실 작성자 모두 403. `test_control_router.py`로 확인 |
| 응답 허용 목록 | 통과 | 전 필드를 명시적으로 조립. `last_error`는 분류 문자열로만 변환(`:106-112`) |
| 질의 임베딩 비용 귀속 | **위반** | 지적 1 |
| 그 외 service_role 쓰기 | 통과 | `insert_usage_event`, `latest_compile_fingerprint` 모두 `workspace_id` 명시. Ask 경로는 `start_ask_turn` 게이트(`routers/ask.py:124`)를 먼저 통과 |
| `queue.py` trace·사용량 멱등성 | 통과, 일부 지적 | 재시도·회수·반납·dead 재시도에서 trace 유지(`supabase/tests/0023_job_trace.sql` 재실행 ok). `clear_job_context`가 trace까지 지워 다음 잡으로 새지 않음. 시도별 사용량 행은 실제 호출 수와 일치. 단 지적 8 |
| 외부 전송 본문 누출 | 통과 | `input`·`output` 미전달, 메타데이터 허용 목록(`observability.py:70-80`), SDK가 metadata에도 `mask` 적용(`langfuse/_client/span.py:159`), 기본 span 필터가 외부 span 차단. `test_observability_e2e.py` 통과 |
| 워크스페이스 해시 | 통과 | SHA-256(`:303-307`). 솔트가 없어 후보 UUID를 아는 사람은 대조할 수 있다. 익명화가 아니라 가명 처리로 이해해야 한다 |
| 비밀 키 마스킹 | 통과 | `langfuse_secret_key`가 `REDACTED_KEYS`에 있고 커플링 테스트가 있음. 전송 실패 실측에서 stderr에 키 없음 |
| 예외 삼킴 | 일부 지적 | 동기 경로는 `_warn_failure`로 경고가 남음. 백그라운드 전송 실패는 그렇지 않음(지적 7) |
| `LANGFUSE_SECRET_KEY`와 SEC-01 구분 | **근거 수정 필요** | 지적 3 |
| 공개 쇼케이스 | 통과 | `force-static`, 컴포넌트의 import는 `Link`와 CSS뿐, 루트 레이아웃은 세션을 읽지 않음, `/showcase`는 미들웨어 matcher 밖, 증거 JSON에 UUID·`@`·자격 증명 패턴 없음. 테넌트 데이터로 이어지는 경로 없음 |

## 조치가 필요한 항목

1. **로그인 없이 다른 테넌트의 `usage_events`에 비용을 기록할 수 있다** (심각도: 치명)
   - 위치: `apps/api/src/api/routers/retrieval.py:74-77`(게이트 없음), `apps/api/src/api/services/retrieval.py:57`, `:108`, `apps/worker/src/worker/query_embedding.py:135-139`, `apps/worker/src/worker/__main__.py:78-90`
   - 깨지는 것: `/retrieval`은 JWT를 검증하지 않고 멤버십도 확인하지 않은 채 **RLS가 평가되는 첫 RPC보다 먼저** 임베딩을 호출한다. 경로의 워크스페이스 ID가 `X-Workspace-Id`로 워커에 전달되고, 내부 토큰을 신뢰한 워커가 `service_role`로 그 워크스페이스에 행을 쓴다. 응답은 200과 빈 근거라 호출자도 피해자도 오류를 보지 못한다.
   - 이 변경에서 생긴 문제다. `79b68fe`에서도 같은 요청이 임베딩을 호출했지만 어느 테넌트에도 기록하지 않았다.
   - 재현 조건과 관측(로컬 스택, 실제 PostgREST와 service_role 쓰기, 임베딩 공급자만 스텁):
     ```text
     POST /workspaces/{피해자}/retrieval
     Authorization: Bearer not-a-jwt
     {"query":"아무 질의"}
     → 200, evidence=[]
     → 호출 순서: POST /internal/query-embedding (X-Workspace-Id: 피해자) → 그 뒤 RPC
     → 피해자 usage_events: kind=embedding, cost_micros=123, metadata={"call":"query_embedding"}
     ```
     다른 사용자의 유효한 JWT로도 같은 결과였다.
   - 피해: 이 합계는 호출 종류를 가리지 않고 월 상한 판정에 들어간다(`0023:155-167`, `__main__.py:155`). 상한에 닿으면 피해 워크스페이스의 수집이 `NW402`로 거부되고 Ask 예산 판정도 실패한다. Control Room에도 출처 없는 비용이 표시된다.
   - 대상 찾기: `allow_public_sharing=true`인 워크스페이스의 `workspace_id`는 `workspace_public_settings`로 anon이 읽을 수 있다(`0016:63-66`, 컬럼 권한 실측). 전 멤버와 URL을 본 사람도 UUID를 안다.
   - 규모(추정): 기본 상한 $5, 워커 제한 1건/초, 1만 자 질의, bge-m3 $0.01/백만 토큰, 건당 약 2,500토큰을 가정하면 약 56시간에 소진한다. 단가와 토큰 수는 실측이 아니므로 자릿수만 보아야 한다.
   - 조치: `retrieve`에서 `service.retrieve` 호출 전에 `has_workspace_role(viewer)`를 확인하고 실패하면 `WorkspaceForbidden`을 던진다. Ask는 이미 게이트가 있으므로 라우터에 두는 편이 왕복을 늘리지 않는다. 위조 토큰은 게이트에서 PostgREST 오류가 되어 현재 매핑상 500으로 끝나지만(`errors.py:248-252`) 임베딩에는 닿지 않는다.
   - 회귀 테스트: 비멤버와 위조 토큰 각각에 대해 임베딩 클라이언트 호출 0회, 피해 워크스페이스 `usage_events` 0행을 단언해 `test_tenant_isolation_full_path.py`에 추가한다. 현재 이 스위트에는 `/retrieval` 행이 없어 32건 통과와 이 결함이 공존한다. delta spec에 비멤버 질의 시나리오도 추가한다.

2. **viewer 한 명이 워크스페이스 전체의 Ask 집계를 500으로 만들 수 있다** (심각도: 보통)
   - 위치: `supabase/migrations/0026_ask_trace_aggregate.sql:52-54`, `:79-80`
   - 깨지는 것: 타입이 `number`인지만 확인하므로 범위를 벗어난 값이 `::int`에서 22003으로 실패한다. `0026:50-51`의 주석이 막으려던 바로 그 실패가 숫자로 재현된다. 값이 기간 안에 남아 있는 동안 모든 editor의 집계가 실패하고, RLS 때문에 다른 멤버는 그 행을 고칠 수 없다.
   - 재현 조건: 작성자(viewer 가능)가 자신의 완료된 턴에 `PATCH /rest/v1/ask_messages` `{"control_report":{"total_ms":1e20}}`을 보낸 뒤 owner가 `ask_trace_aggregate`를 호출한다. 롤백 트랜잭션에서 `22003 integer out of range`를 관측했다. 22003은 42501이 아니므로 API는 500을 돌려준다(이 응답은 코드 판독). `test_forged_report_values_do_not_break_the_aggregate`는 문자열만 검사한다.
   - 조치: `durations` CTE에 `total_ms between 0 and 86400000` 같은 범위 조건을 넣고, 큰 수와 음수 사례를 테스트에 더한다. 이미 적용한 로컬 외에 클라우드는 미적용이지만, 번호 규칙에 따라 `0027`로 고치거나 push 전에 `0026`을 수정할지 정한다.

3. **SEC-01 구분은 위험 범위 면에서 방어할 수 있지만, 주석의 근거가 사실이 아니다** (심각도: 보통)
   - 위치: `apps/api/src/api/settings.py:96-101`, `:1`, `:17`, `packages/core/tests/test_settings.py`의 `NON_SECRET_API_FIELDS` 추가분, `docs/ops/railway-env-checklist.md`
   - 판단: 구분 자체는 타당하다. 이 키로는 RLS를 우회해 고객 원문에 닿을 수 없고 공급자 비용도 쓸 수 없으며, Langfuse에는 본문이 없다. API는 이미 공급자 비용을 쓸 수 있는 내부 호출 토큰도 갖고 있다.
   - 깨지는 것: "이 키로는 관측 프로젝트에 쓰는 일만 할 수 있어"는 틀렸다. 같은 키 쌍으로 SDK의 공개 API 클라이언트가 trace `get`, `list`, `delete`를 노출한다(`langfuse/_client/resource_manager.py:355-356`, `langfuse/api/trace/client.py:37`, `:83`, `:124`). 실제 서버 호출은 하지 않았고, SDK에서 쓰기 전용 키 옵션은 찾지 못했다. 서버 측 범위는 Langfuse 문서로 한 번 더 확인하는 것이 좋다.
   - 결과: API가 침해되면 RLS 바깥에서 **전 테넌트의** trace ID, 워크스페이스 해시, 호출 종류, 모델, 비용, 시각을 읽고 삭제할 수 있다. 이것은 API에 처음 생기는 교차 테넌트 읽기 능력이며, 후속 Step이 메타데이터를 늘리면 범위도 함께 늘어난다. 또한 파일 머리말은 "secret을 담을 필드가 존재하지 않는다", 클래스 설명은 "secret이 아닌 운영 토글만"이라고 하고, 비밀 키가 `NON_SECRET_API_FIELDS`에 들어 있어 "격리는 필드 부재로만 성립한다"는 규칙과 문장 단위로 충돌한다.
   - 조치: 다음 중 하나를 사람이 결정한다.
     - (가) 유지: 주석, 머리말, 테스트 목록 이름을 "읽기·삭제도 가능하며 비본문 메타데이터의 교차 테넌트 노출을 감수한다"로 고치고, 키 회전 절차를 체크리스트에 추가한다.
     - (나) 제거: `export_ask_turn`을 기존 내부 토큰으로 워커에 위임해 API에서 키를 없앤다. SEC-01의 단순한 형태가 유지되는 대신 내부 라우트가 하나 늘어난다.

4. **헤더 없는 질의 임베딩이 `bootstrap` 워크스페이스로 기록을 시도한다** (심각도: 보통)
   - 위치: `apps/worker/src/worker/__main__.py:87`, `:322`, `:384`, `apps/worker/src/worker/query_embedding.py:135-137`
   - 깨지는 것: `_embed_query`가 주변 structlog 컨텍스트에서 워크스페이스를 읽는다. `main`이 `workspace_id="bootstrap"`을 묶은 뒤 리스너 태스크를 만들므로 리스너는 그 값을 물려받는다. design D5의 "기록을 건너뛰고 경고"는 운영 경로에서 실행되지 않고, 이전 버전 API의 호출이나 형식이 틀린 헤더는 DB 22P02 오류로 끝나며 Langfuse에 리터럴 `bootstrap`의 해시가 나간다. `test_worker_main.py`는 이 바인딩 없이 돌아 잡아내지 못한다. 지금은 UUID가 아니라서 실패할 뿐이지만, 귀속 값을 주변 컨텍스트에서 읽는 구조는 나중에 진짜 ID가 묶이면 다른 테넌트로 조용히 귀속된다.
   - 재현 조건: `main`과 같은 순서로 `bind_job_context(workspace_id="bootstrap")` 후 uvicorn 리스너를 띄우고 `X-Workspace-Id` 없이 호출한다. 응답 200, sink 인자 `workspace_id=bootstrap`, 로그 `worker.query_embedding_usage_failed`를 관측했다.
   - 조치: 라우트에서 검증한 값을 전용 `ContextVar`나 함수 인자로 전달해 주변 컨텍스트 의존을 없앤다. 회귀 테스트는 bootstrap 바인딩 뒤의 리스너를 대상으로 쓴다.

5. **작성자가 `ask_messages.trace_id`를 임의의 값으로 바꿀 수 있다** (심각도: 보통)
   - 위치: `supabase/migrations/0019_ask_streaming_turns.sql:42`(테이블 단위 UPDATE), `0025_ask_trace.sql:125`, `apps/api/src/api/routers/ask.py:102-104`, `apps/api/src/api/routers/control.py:326-333`
   - 깨지는 것: `0025`의 주석은 `control_report` 위조만 다룬다. 같은 턴에서 다른 멤버의 trace로 값을 바꾸면 그 trace가 게이트 1단계를 통과하고, 같은 `client_turn_id`를 재전달하면 위조한 사람의 새 사용량이 피해자 trace로 묶여 상세 합계를 부풀린다. 워크스페이스 안의 데이터 오염이며 테넌트 경계는 넘지 않는다. 멤버는 `usage_events`를 직접 읽을 수 있고 design이 이를 범위 밖으로 승인했으므로 새로 노출되는 값은 없다. 다만 그 때문에 `control.py:20-21`의 "순서가 바뀌면 조회할 수 있다"는 경고는 경계가 아니라 화면 수준의 순서만 보장한다.
   - 재현 조건: viewer 권한의 작성자로 `update ask_messages set trace_id=<타인 trace>`가 성공함을 롤백 트랜잭션에서 관측했다. 이후의 게이트 통과와 재전달 오염은 코드 판독이며 E2E로 실행하지 않았다.
   - 조치: 작성자 UPDATE를 `answer_text`, `citations`, `status`, `control_report` 컬럼으로 좁혀 `trace_id`를 고정하고, `start_ask_turn`에서 워크스페이스에 이미 있는 trace 값을 거부할지 결정한다. 후자를 하지 않으면 design Risks에 수용 사실로 적는다.

6. **종료 시 대기 중인 질의 임베딩 사용량이 로그 없이 사라진다** (심각도: 낮음)
   - 위치: `apps/worker/src/worker/__main__.py:56`, `:74-83`
   - 깨지는 것: `_pending_usage_writes`를 기다리는 코드가 없다. SIGTERM 뒤 `asyncio.run`이 남은 태스크를 취소하는데 `CancelledError`는 `except Exception`에 걸리지 않으므로 기록도 로그도 남지 않는다. 배포마다 진행 중이던 몇 건의 비용이 상한에서 빠진다. 코드 판독 결과이며 실행으로 재현하지는 않았다.
   - 조치: 리스너 종료 뒤 제한 시간을 두고 남은 태스크를 `gather`하고, 남은 건수를 로그로 남긴다. `WORKER_GRACE_SECONDS` 예산을 함께 확인한다.

7. **Langfuse 백그라운드 전송 실패는 구조화 로그에 남지 않는다** (심각도: 낮음)
   - 위치: `packages/core/src/nexuswiki_core/observability.py:134`, `:239-267`
   - 깨지는 것: `base_url=http://127.0.0.1:9`로 실행하자 `observability.enabled`가 찍히고 `flush_observability()`는 `True`를 돌려줬다. 실패 흔적은 stderr의 평문 한 줄 `Failed to export spans batch ...`뿐이고 `observability.export_failed`는 나오지 않았다. 잘못된 리전이나 키로 배포해도 켜진 것처럼 보인다. 예산의 원천은 Postgres이므로 제품 영향은 없다.
   - 조치: 체크리스트에 "Langfuse UI에서 첫 trace 수신 확인"을 넣고, `flush`의 `True`가 전송 성공을 뜻하지 않는다고 docstring을 고친다.

8. **`outcome="succeeded"`가 전이 없이도 내보내진다** (심각도: 낮음)
   - 위치: `apps/worker/src/worker/queue.py:233`, `:310-311`
   - 깨지는 것: `complete_job`은 0행이어도 `None`을 돌려줄 뿐이라, 회수된 뒤 뒤늦게 끝난 워커도 성공으로 내보낸다. "상태 전이가 성공한 뒤에만 채운다"는 주석과 다르다. 영향은 개발자용 Langfuse 사본에 한정되며 DB 상태는 변하지 않는다. 코드 판독 결과다.
   - 조치: 주석을 실제 동작에 맞추거나, 핸들러가 이미 체인 완료한 경우와 구분해 0행 결과를 반영한다.

9. **`p_since`를 직접 지정하면 개별 턴의 값을 분리할 수 있다** (심각도: 낮음)
   - 위치: `supabase/migrations/0026_ask_trace_aggregate.sql:46`, `:92`
   - 깨지는 것: 라우터는 일 단위로 제한하지만(`control.py:394`) RPC는 authenticated가 직접 부를 수 있다. editor가 `p_since`를 조금씩 옮기며 차이를 보면 턴 하나의 시각, 상태, 결정, 지연을 얻는다. 멤버가 둘뿐이면 사실상 작성자가 특정된다. 질문 본문과 식별자는 나오지 않으며 시각과 비용은 이미 `usage_events`로 보인다. 코드 판독 결과다.
   - 조치: 함수 안에서 `p_since`를 UTC 일 단위로 내림하거나, 현재 소규모 운영에서 수용한다고 design Risks에 적는다.

10. **코드 설명과 실제 동작의 사소한 불일치** (심각도: 낮음)
    - `control.py:23`은 원시 오류를 "읽지도" 않는다고 하지만 `_JOB_COLUMNS`(`:47-49`)가 `last_error`를 읽는다. 응답에는 나가지 않으므로 누출은 아니다.
    - `observability.py:7`은 공개 함수가 예외를 던지지 않는다고 하지만 `export_ask_turn`의 필드 추출(`:180-201`)은 `try` 밖에 있다. 현재 입력은 서버가 조립한 값뿐이라 도달하지 않는다.

## 판정 근거

지적 1은 A-4 위반이다. 이 변경이 들어가면 인증되지 않은 호출자가 워커의 `service_role`을 통해 임의 테넌트의 `usage_events`에 행을 만들고, 그 합계로 해당 테넌트의 수집과 Ask를 멈출 수 있으며, 모든 응답이 200이라 아무 신호도 남지 않는다. 데이터를 읽어 가는 경로는 아니지만 테넌트 경계를 넘는 쓰기이자 조용한 손상이므로 `blocked`로 판정한다. 코드 수정 자체는 작지만, 비멤버 `/retrieval`의 응답을 200에서 403으로 바꾸는 계약 변경과 지적 3의 선택지에는 사람의 결정이 필요하다. 코드와 마이그레이션이 아직 클라우드에 없으므로 운영에서 발생한 일은 아니다.

나머지 경계는 실측에서 유지됐다. RLS 작성자·멤버십 조건, 함수 권한, 응답 허용 목록, Langfuse 본문 차단, 공개 쇼케이스에서는 격리 위반을 찾지 못했다.

## 검증 범위

- 실행: 관련 pytest 11개 파일 142건 통과, `supabase/tests/0023_job_trace.sql` ok, 롤백 트랜잭션의 SQL 실측, 로컬 스택 재현 스크립트(재현 데이터 정리 후 잔여 0건 확인).
- `test_tenant_isolation_full_path.py`: 이번 전체 실행에서 31건 통과, `test_requester_jwt_delete_matrix_blocks_both_foreign_directions[raw_sources]` 1건 ERROR. 해당 테스트 함수만 다시 돌리자 9건 전부 통과했다. 간헐적 현상으로 보이지만 원인은 확인하지 못했다.
- 실행하지 않음: 클라우드 환경, 실제 임베딩 공급자, 실제 Langfuse 서버 호출, 대시보드 테스트 재실행. `test_cross_tenant_ingest_is_forbidden_with_a_fixed_body[file]`의 502는 조사 중이라는 전달에 따라 이번 판정에 넣지 않았다.

## 범위 밖 참고

이번 변경에서 생긴 것이 아니며 판정에 반영하지 않았다.

- `anon`과 `authenticated`에 `ask_messages`, `ask_threads`의 `TRUNCATE`, `TRIGGER`, `REFERENCES`가 남아 있다. PostgREST로는 도달할 수 없다.
- 로컬 DB에 이번 리뷰 이전의 `test-%` 잔여가 있다(사용자 36명, 워크스페이스 3개, 최신 07:02Z). 어느 실행에서 남았는지는 확인하지 않았고, 지우지 않았다.
