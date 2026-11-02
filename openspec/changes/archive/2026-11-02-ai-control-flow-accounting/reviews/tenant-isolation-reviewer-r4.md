# Tenant Isolation 리뷰 — ai-control-flow-accounting r4 (확인 리뷰)

- 판정: **needs_fix**
- 대상: 커밋하지 않은 작업 트리 (HEAD = `66a2afd`). 범위는 r3 차단 사유 2건의 해소와 이번 수정이 만든 새 위험이다. 전체 재감사가 아니다.
- 일시: 2026-11-02T11:11:58Z

## 요약

r3 차단 사유 2건은 **해소됐다**. viewer의 직접 INSERT와 owner의 Ask trace 잡 생성이 모두 42501로 막히고, 상세는 403을 유지한다. 테넌트 경계를 넘는 경로와 불변 규칙 위반은 찾지 못했고, 트리거와 definer 검사가 새 존재 탐지 경로를 만들지도 않았다. 정상 경로도 막히지 않았다.

`pass`가 아닌 이유는 기록 두 건이 재현 결과와 다르기 때문이다.

1. 이번 수정의 전방 참조 때문에 `0023:8-9`의 "이 파일을 적용한 뒤에도 이전 버전 코드가 그대로 동작합니다"가 거짓이 됐다.
2. `design.md:167`의 "남은 경우" 목록에 빠진 경로가 있다. 잡 인큐로 상세가 403에서 200으로 바뀌는 경우와, 다른 멤버의 수집 trace 합계를 오염시키는 경우다.

둘 다 값이 새 나가는 결함이 아니며 문서 수정으로 해소된다. 1번은 함수 위치를 옮기면 근본적으로 없앨 수 있다.

## 검사 결과

r3에서 통과했고 이번 수정과 무관한 항목은 다시 실측하지 않았다.

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 이번 수정에 API 경로 변경 없음. 재현은 전부 요청자 JWT |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블 없음 |
| A-3 | `anon` 신규 GRANT·정책 | 통과 | 트리거 함수 `proacl`은 `{postgres=X/postgres}`뿐이다. anon 직접 INSERT는 401 `42501`, RPC는 404 `PGRST202` |
| A-4 | service_role 코드의 `workspace_id` | 통과 | 이번 수정에 service_role 코드 없음. definer 검사도 `m.workspace_id = p_workspace_id`로 한정(`0023:162`) |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 자식 테이블 없음 |
| B-6 | 0행 → 403 | 통과 | 상세의 0행 경로 403 유지(`control.py:386`) |
| B-7 | 42501 → 403 | 통과 | 트리거와 새 검사 모두 PostgREST에서 403 `42501` |
| C-8 | 핸들러 재실행 안전성 | 통과 | 재전달 200, 같은 trace, 사용량 1→2 |
| C-9 | `jobs` 직접 UPDATE 금지 | 통과 | 추가된 코드에 없음 |
| D-10 | `hnsw.iterative_scan` | 해당 없음 | 변경 없음 |
| D-11 | 토크나이저 일치 | 해당 없음 | 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트 `str.format` | 해당 없음 | 변경 없음 |
| D-14 | 인용 앵커 | 해당 없음 | 변경 없음 |
| E-15 | 마이그레이션 번호 | 통과 | 번호 추가 없음, 최대 `0026`. 클라우드 미적용은 기록(`migration-0023-0026-record.md:28`)에 따른 것이고 직접 확인하지 않았다. 번호와 별개인 전방 참조는 지적 1 |

## r3 차단 사유 해소 여부

| r3 | 결과 | 근거 |
| --- | --- | --- |
| 1. 직접 INSERT로 이미 쓰인 trace 턴 생성 | **해소** | 재현 1 |
| 1. `enqueue_source_job`의 같은 부류 경로 | **Ask 턴이 있는 값은 해소**, 그 밖의 값은 지적 2 | 재현 2, 재현 7 |
| 2. `design.md:161` 예산 문장 | **해소** | "최종 사용량 전이면 0으로 기록된다"로 정정. `:169`와 모순 없음 |
| 참고 2. 게이트웨이 단정 | 해소 | `errors.py:72-75`가 조건문이 됐고 기록 `:35`에 확인 절차가 있다. 로컬 위조 토큰 401, 임베딩 호출 0건 실측 |
| 참고 3. #170 문구 | 해소 | 제목과 Given이 "턴이 끝나기 전", "검색, 스트리밍, 종결 호출"로 바뀜 |
| 참고 4. 사후 대조의 소유자 | 해소 | `design.md:169`와 #170이 #172를 가리키고, #172는 OPEN |
| 참고 5. Langfuse 혼합 | 해소 | `design.md:167`의 (3)에 기록됨 |

## 조치가 필요한 항목

1. **`0023` 머리말이 이번 수정으로 거짓이 됐다** (심각도: 보통)
   - 위치: `supabase/migrations/0023_job_trace.sql:8-9`, `:158-164`
   - 깨지는 것: `:160`의 조건은 하나의 SQL 식으로 계획된다. `p_trace_id is not null`이 단락시켜 주지 않으므로 `ask_messages.trace_id`가 없으면 **`null`을 넘겨도** 호출할 때마다 `42703`이 난다. 그런데 머리말은 "이 파일을 적용한 뒤에도 이전 버전 코드가 그대로 동작합니다"라고 한다. `:158-159`도 "실행 시점에 해석"한다고만 적어 `null` 호출은 안전하다고 읽힌다.
   - 언제 일어나는가: 파일마다 자체 `begin`/`commit`이 있어(`0023:12`, `:225`) `0023` 커밋 뒤 `0025` 커밋 전에 창이 열린다. 보통은 짧지만 `0024`나 `0025`에서 적용이 멈추면 고칠 때까지 이어진다. 그동안 원문 등록은 500이 된다. `raw_sources` 행은 이미 만들어졌으므로 잡 없이 남는다(`sources.py:262-277`). 예외가 나므로 조용한 실패는 아니고, 테넌트 경계와도 무관하다.
   - 재현: 없는 컬럼을 참조하는 같은 모양의 `pg_temp` 함수를 롤백 트랜잭션에서 실행했다. 생성은 성공하고, `probe(null)`은 `ERROR: column m.no_such_column_yet does not exist`로 실패했다. 실제 스키마에서 컬럼을 지우는 실험은 지시에 따라 하지 않았다.
   - 조치: 둘 중 하나를 고른다.
     - 권장: 검사가 든 `enqueue_source_job`을 컬럼이 생긴 뒤인 `0025`에서 `create or replace`한다. 전방 참조와 창이 함께 사라지고 머리말도 다시 참이 된다.
     - 기록만: 머리말과 `:158-159`를 "`0025`까지 적용되기 전에는 `null` 호출도 42703으로 실패한다"로 고치고, `migration-0023-0026-record.md`의 적용 절차에 같은 내용과 중단 시 조치를 적는다.

2. **`design.md:167`의 "남은 경우" 목록에 빠진 경로가 있다** (심각도: 낮음)
   - 위치: `openspec/changes/ai-control-flow-accounting/design.md:167`, 관련 코드 `0023:160-164`, `control.py:369-384`
   - 깨지는 것: 이 항목은 잡 쪽 거부를 "Ask 턴의 값만"으로 설명한 뒤, 검사가 "표시 합계의 오염과 화면 계약을 지킨다"고 하고 남은 경우를 셋으로 닫는다. 그러나 `ask_messages`에 없는 값은 모두 통과하므로 목록 밖의 경우가 재현된다(재현 7).
     - **Ask 턴이 지워진 값**: 작성자가 스레드를 지우면 턴은 cascade로 사라지지만 사용량은 남는다. owner가 그 값으로 잡을 만들면 상세가 403에서 200이 되고, `calls`에 그 멤버의 호출이 나온다. 이 Ask trace 한정으로 `ai-control-room/spec.md:29-31`의 403이 성립하지 않는다.
     - **사용량에만 있는 값**: 다른 멤버의 `/retrieval` trace도 같다. 403에서 200이 된다. 정작 본인(viewer)은 403이다.
     - **다른 멤버의 수집 trace**: editor가 자기 잡을 얹으면 owner가 보는 상세의 `stages`와 `totals`가 늘어난다. 호출 1건, 비용 1에서 호출 2건, 비용 2가 됐다. 영상 배치를 허용하려면 값만으로 구분할 수 없어 생기는 결과다. 이것이 "표시 합계의 오염을 지킨다"는 문장의 범위 밖이라는 점이 적혀 있지 않다.
   - 영향 범위: 같은 워크스페이스의 editor 이상이 PostgREST를 직접 호출해야 한다. 돌아오는 `calls`는 이들이 RLS로 직접 읽을 수 있는 값이고 질문과 답변은 나가지 않는다. 월 상한 합계는 실제 사용량만 더한다. r3가 "`enqueue_source_job` 경로는 design에 적으면 충분하다"고 한 대로 코드를 고칠 필요는 없다.
   - 조치: `design.md:167`의 수용 목록에 (4)로 추가한다. "`enqueue_source_job`은 Ask 턴에 있는 값만 거부하므로, editor 이상은 턴이 지워진 값이나 사용량에만 있는 값, 다른 멤버의 수집 trace로 잡을 만들 수 있다. 상세가 200이 되거나 표시 합계가 섞이지만 돌아오는 값은 RLS로 읽을 수 있는 것뿐이다." 앞 문장의 "표시 합계의 오염과 화면 계약을 지킨다"도 "Ask 턴이 있는 trace에 한해"로 좁힌다.

## 판정 근거

A-1, A-3, A-4가 모두 통과했고 테넌트 경계를 넘는 경로를 찾지 못했으므로 `blocked` 조건은 아니다. 불변 규칙 위반도 없다. `needs_fix`인 이유는 지시된 사유 중 "기록이 사실과 다른 경우"에 해당하기 때문이다. 지적 2는 이번에 고친 항목 자체다. 지적 1의 머리말은 이번에 고친 문장이 아니지만, 이번 수정이 그 문장을 거짓으로 만들었고 같은 파일 안에 있으므로 같은 사유로 판단했다. 지적 1을 범위 밖으로 볼지는 호출자가 판단할 수 있으나, 지적 2만으로도 등급은 같다.

## 깐깐하게 본 지점의 결과

| 지점 | 결과 | 근거 |
| --- | --- | --- |
| 트리거 소유자·실행 권한 | 맞음 | 소유자 `postgres`, `prosecdef=f`, `search_path=public`. `authenticated` 실행 시 RLS 적용 |
| 비멤버가 trace 존재를 구분 | **불가** | 7개 경로에서 Ask, 수집, 부재 값의 상태·본문·헤더가 모두 동일(재현 3) |
| `revoke`가 정상 INSERT를 막는지 | 안 막음 | EXECUTE 없이 INSERT 201, RPC 턴 200 |
| RPC 직접 호출 | 불가 | authenticated, anon, service 모두 404 `PGRST202`. SQL 직접 호출도 `42501 permission denied for function` |
| definer 검사의 존재 탐지 | 다른 테넌트 값 탐지 불가, 수용 근거 일치 | 재현 2, 재현 6 |
| 턴 먼저 → 잡·사용량 | 막힘 | 심어 둔 값의 잡 인큐 403. 사용량은 service_role만 쓰고 인입 `X-Trace-Id`를 믿지 않는다(`packages/core/src/nexuswiki_core/trace.py:152`) |
| 잡 먼저 → 턴 | 막힘 | 403 `trace already in use` |
| `update` | 막힘 | PATCH `trace_id`, `client_turn_id` 모두 403 |
| `upsert` / `on conflict` | 막힘 | 재현 4 |
| 대량 INSERT | 막힘 | 둘째 행이 쓰인 값이면 전체 403 |
| `jobs`, `usage_events` 직접 쓰기 | 막힘 | owner와 viewer 모두 테이블 권한 없음으로 403 |

## 참고: 판정 사유가 아닌 것

1. **비멤버의 직접 INSERT는 RLS 오류가 아니다** (낮음, 기존 동작): 새 트리거가 통과시킨 뒤 `enforce_ask_source_references`(`0019`, definer)가 먼저 409 `23503`을 던진다. 값과 무관하게 동일하므로 존재 탐지는 아니다. 트리거 순서는 이름순이라 `reject_used_trace`가 먼저 돈다.
2. **멤버는 메시지 차이로 값을 구분한다** (낮음): 남의 스레드로 INSERT하면 쓰인 값은 `trace already in use`, 새 값은 RLS 메시지다. 멤버는 어차피 `usage_events`와 `jobs`를 읽으므로 새 정보가 아니다.
3. **design 수용 (3)의 범위** (낮음): 적힌 것은 턴뿐이지만 잡도 같다. B의 owner가 A의 Ask trace로 자기 소스의 잡을 만들 수 있다(200). Postgres 조회는 섞이지 않고 Langfuse 쪽 혼합도 같은 수준이다.
4. **design 수용 (2)의 "대부분"** (낮음): 사용량이 `query_embedding`뿐인 trace는 사용량만으로 Ask인지 `/retrieval`인지 구분되지 않지만 잡 인큐 응답으로는 구분된다. 드러나는 것은 턴의 존재뿐이다. "대부분"이라는 표현과 어긋나지 않는다.
5. **r1의 격리 스위트 간헐 실패**: 원인은 여전히 모른다. 지시에 따라 전체 스위트를 돌리지 않았으므로 해소되었다고 말할 수 없다.

## 재현 기록

실제 API 앱과 PostgREST를 쓰고 임베딩과 LLM만 스텁했다. 임베딩 스텁은 워커 기록을 흉내 내 현재 trace로 `usage_events`를 쓴다. 실제 클라이언트가 `trace_headers()`로 trace를 넘기는 것은 `services/retrieval.py:58`에서 코드로 확인했다. 로컬 함수 4개의 본문이 작업 트리의 마이그레이션 파일과 일치함을 비교했다.

### 재현 1: r3 viewer 경로

| 순서 | r3 | r4 |
| --- | --- | --- |
| 수집 trace 상세 | 403 | 403 |
| `ask_messages` 직접 INSERT, 그 값 | 201 | **403** `42501` `trace already in use` |
| 같은 상세 | 200 | **403** |
| 같은 `client_turn_id`로 `/ask` | 그 trace로 묶임, 사용량 1→2 | 200, **새 trace 발급, 수집 trace 사용량 1→1** |

### 재현 2: r3 owner 경로

| 호출 | 결과 |
| --- | --- |
| owner, viewer의 Ask trace로 인큐 | 403 `42501` `이 요청 식별자는 쓸 수 없습니다`, 잡 0건 |
| editor, 같은 값 | 같음 |
| viewer, 같은 값과 부재 값 | 둘 다 403 `워크스페이스에 대한 편집 권한이 없습니다` |
| owner와 editor의 상세 | 403 `{"detail":"forbidden"}` |
| viewer 본인의 상세 | 200 |

### 재현 3: 비멤버 응답 비교 (Ask, 수집, 부재 값)

| 경로 | 값끼리 동일 | 응답 |
| --- | --- | --- |
| 직접 INSERT, 자기 스레드 | 예 | 409 `23503` |
| 직접 INSERT, viewer 스레드 | 예 | 409 `23503` |
| upsert merge | 예 | 403 `permission denied` |
| upsert ignore | 예 | 409 `23503` |
| `start_ask_turn`, thread null | 예 | 403 `ask_threads` RLS |
| `start_ask_turn`, 자기 스레드 | 예 | 403 `ask thread not visible` |
| `enqueue_source_job` | 예 | 403 `편집 권한` |
| API 상세(실재와 부재) | 예 | 403 `{"detail":"forbidden"}` |

시간 차이는 측정하지 않았다. RLS가 행을 가리므로 값에 따른 분기가 없다.

### 재현 4: `on conflict` (롤백 트랜잭션, `authenticated`)

| 호출 | 결과 |
| --- | --- |
| 쓰인 값 + `do update set answer_text` | `42501 trace already in use` |
| 새 값 + `do update set answer_text` | 통과, 저장된 trace 불변 |
| `do update set trace_id` | `42501 permission denied` |
| 쓰인 값 + `do nothing` | `42501 trace already in use` |
| PostgREST merge-duplicates(쓰인 값, 새 값) | 둘 다 403 `permission denied` |
| PostgREST ignore-duplicates(기존 턴, 새 턴) | 둘 다 403 `trace already in use` |

### 재현 5: 정상 경로

| 호출 | 결과 |
| --- | --- |
| `/ask` 새 턴 | 200, `done`, 사용량 1 |
| 재전달 | 200, 같은 trace, 사용량 1→2 |
| 다른 턴 | 200, 다른 trace |
| 인입 `X-Trace-Id`에 쓰인 값 | 200, 무시되고 새 trace |
| `start_ask_turn`, 직접 INSERT, 인큐의 `null` | 200, 201, 200 |
| 영상 배치(사용량이 생긴 뒤 포함) | 200, 200, 잡 2건 |
| trace 없는 턴의 재전달, trace 없는 과거 사용량 | 200, 201 |
| `complete_job_and_chain`, Ask trace를 가진 잡 | 200, 후속 잡이 trace 승계 |

### 재현 6: design 수용 세 경우

| 경우 | 실측 | 일치 |
| --- | --- | --- |
| (1) 행이 아직 없는 값 | 값을 안다고 가정하면 201이지만 viewer는 자기 행만 읽고 질문은 나오지 않는다. editor가 읽는 `ask_messages`도 자기 행뿐이라 값을 얻을 경로가 없다 | 예 |
| (2) definer 판정 | owner와 editor만 판정 가능. viewer와 비멤버는 값과 무관하게 동일. 같은 워크스페이스 Ask만 거부되고, 다른 워크스페이스의 Ask 값은 부재 값처럼 200 | 예 |
| (3) 두 워크스페이스 | A의 trace로 B에 턴 201. B 상세 200에 `calls` 0건, A 상세는 403 유지. `observability.py:308`의 Langfuse ID는 trace 값만을 시드로 쓴다 | 예 |

### 재현 7: 기록에 없는 경우 (지적 2)

| 값 | 전 | owner 또는 editor 인큐 | 후 |
| --- | --- | --- | --- |
| 스레드를 지운 viewer의 Ask trace, 사용량 잔존 | owner 상세 403 | 200 | owner 상세 **200**, `calls`에 `query_embedding` |
| 같은 값으로 viewer가 다시 턴 | | | 403 (트리거는 유효) |
| viewer의 실제 `/retrieval` trace | owner 상세 403 | 200 | owner 상세 **200**, `calls` 1건. viewer 본인은 403 |
| owner의 수집 trace, editor의 잡 | `totals` 1건, 비용 1 | 200 | owner 상세 `totals` 2건, 비용 2, `stages` 5→6 (워커 처리는 사용량 삽입으로 가정) |

## 검증 범위

- 재현 스크립트:
  - `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/a44b5550-f4d4-4b96-b376-1e5e7a7a6cb1/scratchpad/r4_trace.py`
  - `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/a44b5550-f4d4-4b96-b376-1e5e7a7a6cb1/scratchpad/r4_trace2.py`
  - `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/a44b5550-f4d4-4b96-b376-1e5e7a7a6cb1/scratchpad/r4_sql.sql`
  - `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/a44b5550-f4d4-4b96-b376-1e5e7a7a6cb1/scratchpad/r4_cmp.py`
- 안내받은 `r3_trace.py` 등은 스크래치패드에 없었다. r3 보고서의 순서대로 새로 작성했으므로 스크립트 재실행이 아니라 절차 재현이다.
- 재현 데이터는 정리했다. 마지막 확인에서 `test-%` 사용자와 워크스페이스가 0건이다. SQL 실측은 전부 롤백했고 DB 객체와 작업 트리의 코드는 바꾸지 않았다.
- 전제로 받고 직접 확인하지 않은 것: 전체 pytest 809 passed 1 skipped, 임시 프로젝트의 0001~0026 전체 적용과 `0023_job_trace.sql`, 트리거를 끄면 회귀 테스트 4건이 실패한다는 것. `authenticated`에 EXECUTE가 없는 것은 로컬에서 직접 확인했다.
- 실행하지 않음: 전체 스위트, 클라우드 환경, 실제 공급자, 실제 Langfuse 서버, 실제 부분 적용(지적 1은 같은 모양의 임시 함수로 확인).
