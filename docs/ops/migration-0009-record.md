# 마이그레이션 0009 적용 기록

`docs/ops/migration-0008-record.md`를 이어 쓴 문서다. `0008`은 기존 객체(임베딩 차원)를 옮기는 보정이었고,
`0009`는 그 기록이 `§한계 2`에 남긴 정정 한 줄을 실제로 집행하면서 Phase 3의 워커·API가 필요로 하는
**새 객체**를 한 번에 세운다 — 데드레터 원자 전이, 잡 취소, 인큐 시점 비용 상한, `usage_events`,
그리고 Python enum ↔ DB CHECK 대조용 카탈로그 읽기 함수.

## 적용 일시

- 로컬 `db reset`: 2026-08-08 (UTC 2026-08-08T06:4xZ). `0001`~`0009` 전체 재적용.
- 클라우드 `db push`: 2026-08-08 (UTC 2026-08-08T06:5xZ)
- 대상 커밋: `ede6dff` (마이그레이션 저술) · `4adcf5c` (계약 러너 한 쌍). 적용 시점 HEAD `4adcf5c`
- 대상 프로젝트: Supabase `dajhhwbkfdaqnuenulsb` / 리전 `ap-southeast-1`
- 도구: Supabase CLI 2.111.0
- ⚠️ `SUPABASE_ACCESS_TOKEN` 환경변수는 **설정되어 있지 않다**. CLI의 저장된 세션으로 `migration list`와
  `db push` 모두 비대화형으로 동작했으며, `0007`·`0008` 적용 때와 같은 조건이다.

## 무엇을 만들었나

| 객체 | 종류 | 요점 |
|---|---|---|
| `public.jobs.status` CHECK | 기존 제약 재정의 | `jobs_status_check`에 `'canceled'` 추가 (5값 → 6값) |
| `public.jobs.cancel_requested_at` | 신규 컬럼 | `timestamptz`. 협조적 취소의 신호 |
| `public.workspaces.monthly_budget_micros` | 신규 컬럼 | `bigint not null default 5000000` + `workspaces_budget_non_negative` |
| `public.usage_events` | 신규 테이블 | 12컬럼 + `usage_events_workspace_occurred_idx` + RLS + 정책 1종 |
| `public.dead_letter_job(uuid, text, text)` | 신규 함수 | service_role. 락 소유자 술어 3개 |
| `public.cancel_job(uuid, text)` | 신규 함수 | service_role. 같은 술어 3개, 체인 미연결 |
| `public.enqueue_source_job(uuid, uuid)` | 신규 함수 | definer / authenticated. 사용자 경로의 유일한 인큐 통로 |
| `public.request_job_cancel(uuid)` | 신규 함수 | definer / authenticated |
| `public.retry_dead_job(uuid)` | 신규 함수 | definer / authenticated |
| `public.enum_check_values(text, text)` | 신규 함수 | service_role. invoker (공개 카탈로그라 definer 불필요) |
| `public.search_chunks` ACL | **정정** | `service_role`의 EXECUTE 회수 — `0008` §한계 2가 남긴 한 줄 |

`jobs.status` CHECK 재정의는 유일한 "기존 객체 변경"이다. `03-CONTEXT.md > D-01`의 판별 기준에 걸리지
않는 이유는 `0009` 파일 헤더와 섹션 1 주석에 있다 — 되돌릴 수 없는 것은 파일 번호이지 객체가 아니다.

## 이 페이즈가 닫은 결정

**월 비용 상한 기본값 = `5000000` micro-dollar ($5.00/월/워크스페이스).**
`checklists.json > open_questions`의 "워크스페이스별 월 LLM 비용 상한값 — P4-OPS-01에서 확정" 항목을
Phase 3가 앞당겨 닫았다. `REQUIREMENTS.md:275`가 OPS-01을 첫 LLM 호출과 같은 페이즈에 둔 이유가 이것이다 —
상한이 없는 채로 첫 컴파일이 돌면 상한은 회고적 관측이 되지 단속이 되지 못한다.

단위를 토큰이 아니라 돈으로, 부동소수가 아니라 정수 micro로 둔 근거는 `03-02-PLAN.md > D-P2`에 있고
여기서 재서술하지 않는다. 값 $5.00의 근거는 PROJECT 예산 제약(Railway Hobby $5/mo 수준의 개인 프로젝트)이다.
값은 워크스페이스별 컬럼이므로 워크스페이스마다 다르게 둘 수 있다.

## 로컬

### 방법

- `supabase db reset`으로 `0001`~`0009`를 빈 DB에 순서대로 적용했다.
- 계약 러너 **3종**을 reset된 스키마 위에서 실행했다 — `verify_pipeline_ops.sh`(신규) ·
  `verify_queue_functions.sh`·`verify_search_contract.sh`(기존 회귀).
- 마이그레이션을 쓰는 동안에는 파일의 마지막 `commit;`을 `rollback;`으로 바꾼 사본을 psql에 흘려
  구문·의미를 부작용 없이 먼저 확인했다.

### 결과

- `supabase db reset`이 `0001` → … → `0009` 순서로 오류 없이 적용됐다. pass.
- `verify_pipeline_ops.sh` 종료 코드 `0`, 출력 `pipeline_ops: ok`. `do $t` 단언 블록 19개 전부 통과.
  테스트가 `rollback`으로 끝나므로 잔여 행 `0` (`jobs` 0행 · `usage_events` 0행 재확인). pass.
- `verify_queue_functions.sh` 종료 코드 `0` (`queue_functions: ok`) — 기존 큐 계약 회귀 없음. pass.
- `verify_search_contract.sh` 종료 코드 `0` (`search_contract: ok`) — `0008` 검색 계약 회귀 없음. pass.
- **러너가 red가 되는 것까지 확인했다.** T7 단언의 기대값을 일부러 틀리게 바꾼 사본은 종료 코드 `3`,
  `pipeline_ops: ok` 토큰 0회, 그리고 어느 단언이 깨졌는지를 이름과 실제값으로 인쇄했다. 통과가
  "조용한 통과"가 아님을 보인 것이다.
- `uv run pytest -rs` 147 passed. `pre-commit run --all-files` 통과. pass.

### 로컬 관측값

| 확인 항목 | 실제 반환값 | 판정 |
|---|---|---|
| `jobs_status_check` | 6값 (`queued`/`running`/`succeeded`/`failed`/`dead`/`canceled`) | pass |
| `jobs.cancel_requested_at` | `timestamp with time zone` | pass |
| `workspaces.monthly_budget_micros` | `bigint default 5000000` | pass |
| `usage_events` RLS | 활성 / 정책 1종 (`usage_events_select_member`) | pass |
| `has_function_privilege('service_role','search_chunks',…)` | `false` | pass (원래 로컬은 `false`였다 — §한계 2) |
| `enum_check_values('jobs','status')` | `canceled,dead,failed,queued,running,succeeded` | pass |
| `enum_check_values('wiki_pages','category')` | `concepts,entities,guides,maps` | pass |

## 클라우드

### 방법

- push **직전에** `supabase migration list --linked`로 원격 원장의 `0009` Remote 열이 비어 있음을 확인했다.
- `supabase db push --linked`로 적용한 뒤 같은 명령으로 다시 대조하고, 원격 카탈로그를
  `supabase db query --linked -f …`로 직접 조회했다.
- ⚠️ **권한은 반드시 원격에서 다시 물었다.** `0008` §한계 2가 보인 대로 로컬과 클라우드의
  `pg_default_acl`이 다르므로, 로컬 계약 테스트가 green인 것은 클라우드 권한에 대해 아무것도 말해주지 않는다.

### 결과

`supabase db push --linked` 출력:
`{"upToDate":false,"dryRun":false,"migrations":["0009_pipeline_ops.sql"],"seeds":[],"roles":[],"message":"Finished supabase db push."}`.
적용된 마이그레이션은 `0009` 하나뿐이며 부분 적용의 흔적은 없다 — 파일 전체가 단일 트랜잭션이므로
부분 적용이 애초에 불가능하다.

#### `migration list` 로컬/원격 대조표

| Local | Remote | 일치 |
|---|---|---|
| 0001 ~ 0008 | 0001 ~ 0008 | ✅ (변화 없음) |
| 0009 | 0009 | ✅ |

push 직전 표에서는 `0009` 행의 Remote 열만 비어 있었고, push 후 채워졌다.

#### 원격 스키마·제약 직접 조회

| 확인 항목 | 실제 반환값 | 판정 |
|---|---|---|
| `jobs_status_check` | `CHECK ((status = ANY (ARRAY['queued'::text, 'running'::text, 'succeeded'::text, 'failed'::text, 'dead'::text, 'canceled'::text])))` | pass |
| `jobs.cancel_requested_at` | `timestamp with time zone` | pass |
| `workspaces.monthly_budget_micros` | `bigint default 5000000` | pass |
| `usage_events` RLS / 정책 수 | `true` / `1` | pass |
| `enum_check_values('jobs','status')` (원격 실행) | `canceled,dead,failed,queued,running,succeeded` | pass |

#### 원격 `usage_events` 권한 — 3롤 × 5동작 전수

| 롤 | SELECT | INSERT | UPDATE | DELETE | TRUNCATE |
|---|---|---|---|---|---|
| `anon` | false | false | false | false | false |
| `authenticated` | **true** | false | false | false | false |
| `service_role` | **true** | **true** | false | false | false |

감사 기록이라는 설계대로다. 어느 롤에도 UPDATE/DELETE가 없고, RLS를 우회하는 TRUNCATE도 없다.

#### 원격 함수 EXECUTE — 3롤 × 7함수 전수

| 함수 | anon | authenticated | service_role |
|---|---|---|---|
| `dead_letter_job(uuid, text, text)` | false | false | **true** |
| `cancel_job(uuid, text)` | false | false | **true** |
| `enum_check_values(text, text)` | false | false | **true** |
| `enqueue_source_job(uuid, uuid)` | false | **true** | false |
| `request_job_cancel(uuid)` | false | **true** | false |
| `retry_dead_job(uuid)` | false | **true** | false |
| `search_chunks(uuid, extensions.vector, int)` | false | **true** | **false ← 정정됨** |

방향이 둘로 정확히 갈렸다. 워커 전용 3종은 `service_role`만, 사용자 RPC 3종은 `authenticated`만이며
`service_role`에는 주지 않았다(definer 함수의 멤버십 확인 기준이 `auth.uid()`라 BYPASSRLS 롤이 부르면
의미가 없다).

**`search_chunks`의 `service_role` EXECUTE가 `true` → `false`로 바뀌었다.** `0008` §한계 2가 연 항목이
닫혔고, `.planning/WINDOWS.md`의 열린 항목 5번이 이 관측으로 해소된다.

## 한계와 되돌리기

### 1. 이 적용은 one-way다 — `0009` 이하 번호는 더 이상 추가할 수 없다

원격 원장에 `0009`가 올라간 이상 `0009`보다 낮은 번호의 마이그레이션은 다시는 추가할 수 없다.
`0007`·`0008` 기록의 같은 항목과 같은 제약이며, 앞으로의 정정은 `0010`+로만 한다.

객체 자체는 뒤 마이그레이션에서 되돌릴 수 있다 — `jobs.status` CHECK는 `drop constraint` +
`add constraint`로, `usage_events`는 `drop table`로 돌아간다. **다만 `cost_micros`의 단위를 나중에 바꾸면
그 시점에 존재하는 모든 `usage_events` 행을 산술 변환해야 한다.** 지금은 `usage_events`가 0행이라
되돌리기 비용이 `0`이지만, 이 창은 Phase 3가 첫 LLM 호출을 기록하는 순간 닫힌다. `0008`의 임베딩 차원과
같은 구조의 창이다.

### 2. `monthly_budget_micros`를 바꾸는 사용자 경로가 없다

상한 값은 DB 컬럼으로만 존재하고 이를 바꾸는 API가 없다. `apps/api`의 `WorkspaceUpdateRequest`는
`extra="forbid"`에 `name` 하나만 허용하므로, 새 필드를 추가하지 않는 한 사용자는 자기 워크스페이스의
상한을 조회할 수는 있어도(`usage_events` SELECT + `workspaces` SELECT) **변경할 수 없다**.

즉 현재 상한 변경은 **DB 운영 작업**이다. 이것은 의도된 상태다 — 사용자가 스스로 상한을 올릴 수 있으면
상한은 상한이 아니라 확인 대화상자가 된다. 청구 주체와 상한 조정 권한을 어떻게 연결할지는 결제가 붙는
후속 페이즈의 몫이며, 그 전까지는 `update public.workspaces set monthly_budget_micros = … where id = …`이
유일한 경로다.

### 3. 협조적 취소는 이미 발생한 비용을 되돌리지 못한다

`request_job_cancel`은 `queued`/`failed` 잡을 즉시 `canceled`로 만들지만, `running` 잡에는
`cancel_requested_at`만 찍는다. 워커는 `jobs`를 직접 UPDATE하지 않는다는 계약(`0003`) 위에 서 있고,
COMP-04가 파이프라인을 `parse → compile → link_sync → embed` 넷으로 쪼갰으므로 **취소는 다음 체인 단계
경계에서 반영된다**. 02-CONTEXT.md > D-16이 하트비트 대신 잡 분할을 택한 것의 배당금이자 그 대가다.

따라오는 한계:

- 진행 중인 LLM 호출은 중단되지 않는다. 취소를 눌러도 그 호출의 토큰은 이미 소비됐고 **환불되지 않는다.**
  `usage_events`에는 그 비용이 그대로 기록되며 다음 인큐의 상한 판정에 포함된다.
- 취소 반영 지연의 상한은 **한 체인 단계의 지속 시간**이다. 그 값은 아직 실측되지 않았다 — 핸들러가
  존재하지 않기 때문이다. 같은 미지수가 reap 타임아웃 확정(02-CONTEXT.md > D-17)을 Phase 3 후반으로
  미룬 이유이며, 두 값은 같은 실측에서 함께 나온다.
- 위협 등록부의 `T-03-14`는 이 잔여 비용을 `accept`로 처분했다. 이 절이 그 처분의 기록이다.

### 4. 상한은 인큐 시점에만 걸린다 — 실행 중 초과는 막지 못한다

`enqueue_source_job`은 잡을 만들기 **전에** 이번 달 합을 본다. 그래서 "상한을 통과하지 않고 만들어진
잡은 없다"는 구조적으로 참이지만, **이미 큐에 있는 잡이 실행되면서 상한을 넘기는 것은 막지 않는다.**
한 소스의 컴파일이 상한을 통째로 넘길 만큼 비싸면 그 초과는 발생하고, 다음 인큐부터 거부된다.

이것은 D-P1이 선택한 형태의 논리적 귀결이다. 실행 중 차단을 하려면 워커가 매 LLM 호출 전에 상한을 다시
보고 잡을 중도 포기해야 하는데, 그러면 부분 완료된 컴파일 산출물의 처리가 새 문제로 들어온다. OPS-01이
요구한 것은 인큐 시점 상한이며, 실행 중 상한은 요구되지 않았다.

### 5. 자동 게이트는 여전히 클라우드 권한을 보지 못한다

`0008` §한계 4가 적은 사각이 그대로 남아 있다. CI(`search-contract` 잡)는 **소스**만 읽고, psql 계약
러너 3종은 **로컬 DB**만 본다. `usage_events`와 새 함수 6종의 클라우드 권한이 맞는지는 이 문서가 기록한
**push 후 원격 직접 조회**로만 확인되며, 그 절차는 사람이 실행한다.

`0009`는 이 사각을 없애지 못했지만 **좁혔다** — 모든 함수 revoke에 `service_role`을 명시적으로 넣어,
클라우드의 더 넓은 `pg_default_acl` 기본 부여가 무엇이든 결과 상태가 로컬과 같아지도록 했다.
앞으로 `public`에 함수를 만드는 마이그레이션은 `revoke all … from public, anon, authenticated, service_role`
후 필요한 롤에만 grant하는 이 형태를 따를 것.

### 6. 아직 확인되지 않은 것

- **원격에서 실제 요청자 JWT로 사용자 RPC 3종을 왕복시켜 본 적은 없다.** 확인한 것은 스키마·제약·권한이며,
  `enqueue_source_job`의 42501/53400이 PostgREST를 통해 어떤 HTTP 응답으로 렌더되는지는 인큐 라우터가
  서는 후속 플랜(ING-01)에서 처음 검증된다. 계약 테스트는 로컬에서 `set local role authenticated` +
  `request.jwt.claims`로 같은 컨텍스트를 흉내 냈을 뿐 PostgREST를 지나지 않았다.
- `enum_check_values`는 `ANY (ARRAY[` 형태의 CHECK만 본다. `check (x in ('a'))`처럼 값이 하나뿐인 열거는
  Postgres가 `= 'a'::text`로 렌더하므로 이 함수가 빈 배열을 돌려준다. 현재 스키마에 그런 컬럼은 없지만,
  워커 기동 가드를 쓰는 쪽은 "빈 배열 = 열거 없음"을 실패가 아니라 정보로 다뤄야 한다.
- 상한 판정의 월 경계는 **UTC 고정**이다. 워크스페이스별 시간대는 없다. 사용자가 KST로 생각하는 "이번 달"과
  최대 9시간 어긋나며, 그 차이가 문제가 되는 것은 월 경계 전후로 상한에 근접한 경우뿐이다.
