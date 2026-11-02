# Tenant Isolation 리뷰 — ai-control-flow-accounting r5 (재확인 리뷰)

- 판정: **needs_fix**
- 대상: 커밋하지 않은 작업 트리 (HEAD = `66a2afd`). 범위는 r4 조치 2건의 해소와 이번 수정이 만든 새 위험이다. 전체 재감사가 아니다.
- 일시: 2026-11-02T12:01:49Z

## 요약

코드 수정은 문제없다. `0025`의 `enqueue_source_job`은 `0023` 본문에 검사 블록만 더한 것이고, 역할 검사, raw_source 소유권, 예산, 중복 인큐 처리, definer, `search_path`, 권한, 설명이 그대로다. `0023` 머리말도 다시 참이다. 테넌트 경계를 넘는 경로와 불변 규칙 위반은 찾지 못했다.

`pass`가 아닌 이유는 하나다. 이번에 고친 `design.md:167`의 수용 (4) 끝 문장이 실제 동작과 다르다. "월 상한 합계도 변하지 않는다"는 같은 문장이 설명하는 경우에서 거짓이다. 표시 합계가 늘어나는 것은 그 잡의 실제 사용량이 생겼기 때문이고, 월 상한 합계도 같은 값만큼 늘어난다. 문장 하나만 고치면 되며 코드와 스키마는 바꿀 필요가 없다.

## r4 조치 항목 해소 여부

| r4 | 결과 | 근거 |
| --- | --- | --- |
| 1. `0023` 머리말이 거짓 | **해소** | 재현 1. `ask_messages.trace_id`가 없는 상태에서 null, 이름 있는 2인자, trace 값 호출이 모두 성공한다. `0023`에 `ask_messages` 참조가 없다 |
| 2. `design.md:167` 목록의 누락 | **경로 누락은 해소, 끝 문장은 지적 1** | 재현 3. 빠졌던 세 경로가 적혔고 403→200과 표시 합계 증가가 실측과 맞는다 |

## 검사 결과

r4까지 통과했고 이번 수정과 무관한 항목은 다시 실측하지 않았다.

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 이번 수정에 API 경로 변경 없음. 인큐는 요청자 JWT로 호출 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블 없음 |
| A-3 | `anon` 신규 GRANT·정책 | 통과 | 세 상태 모두 `proacl = {postgres=X/postgres,authenticated=X/postgres}`. `set role anon` 호출은 `permission denied` |
| A-4 | service_role 코드의 `workspace_id` | 통과 | service_role 코드 변경 없음. definer 검사는 `m.workspace_id = p_workspace_id`로 한정(`0025:130`) |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 자식 테이블 없음 |
| B-6 | 0행 → 403 | 통과 | 상세의 0행 경로 변경 없음(`control.py:386`). 재현 3에서 403 유지 |
| B-7 | 42501 → 403 | 통과 | 새 위치의 검사도 PostgREST에서 403 `42501` |
| C-8 | 핸들러 재실행 안전성 | 통과 | 중복 인큐는 같은 잡을 돌려주고 기존 trace를 바꾸지 않는다(재현 2) |
| C-9 | `jobs` 직접 UPDATE 금지 | 통과 | 함수의 `insert ... on conflict do nothing`은 기존과 같고 UPDATE 없음 |
| D-10 | `hnsw.iterative_scan` | 해당 없음 | 변경 없음 |
| D-11 | 토크나이저 일치 | 해당 없음 | 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트 `str.format` | 해당 없음 | 변경 없음 |
| D-14 | 인용 앵커 | 해당 없음 | 변경 없음 |
| E-15 | 마이그레이션 번호 | 통과 | 번호 추가 없음, 최대 `0026`. 클라우드 미적용은 기록(`migration-0023-0026-record.md:28`)에 따른 것이고 직접 확인하지 않았다 |

## 조치가 필요한 항목

1. **수용 (4)의 "월 상한 합계도 변하지 않는다"가 실제와 다르다** (심각도: 낮음)
   - 위치: `openspec/changes/ai-control-flow-accounting/design.md:167` 끝 문장, 관련 코드 `supabase/migrations/0025_ask_trace.sql:137-140`, `apps/worker/src/worker/queue.py:245`, `apps/worker/src/worker/llm_gateway.py:194`
   - 깨지는 것: 바로 앞 문장은 다른 사람의 수집 trace에 잡을 얹으면 "표시되는 호출 수와 합계가 늘어난다"고 한다. 그 증가는 워커가 그 잡의 trace로 쓴 사용량 행에서 나온다. 월 상한 합계는 trace와 무관하게 이번 달 `usage_events`를 전부 더하므로 같은 행이 함께 더해진다. 재현 3에서 표시 합계가 1→2로 늘 때 월 합계도 3→4로 늘었다. 인큐 직후에는 둘 다 그대로다. 즉 "표시는 늘고 월 합계는 그대로"인 시점은 없다.
   - 영향: 상한 집행은 정상이고 경계를 넘지 않는다. trace를 재사용한다고 비용이 더 붙지도 않는다. 문장의 의도는 이것이었겠지만 적힌 내용은 다르다. 이 문장은 잡이 만드는 비용이 없다고 읽히므로, 나중에 수용 근거로 인용하면 틀린 전제가 된다.
   - 같은 문장의 작은 부정확: "돌아오는 값은 ... 사용량뿐"이지만 응답의 `stages`는 잡 행에서 나온다(`control.py:370-382`, 재현 3에서 5→6). 잡도 멤버가 RLS로 읽을 수 있어(`0004_rls_policies.sql:312`) 결론은 같다.
   - 조치: 끝 문장을 다음처럼 고친다. "돌아오는 값은 RLS로 이미 읽을 수 있는 사용량과 잡 단계뿐이고 본문은 나가지 않는다. 월 상한 합계에는 그 잡이 실제로 쓴 비용만 더해지며, trace를 재사용한다고 더 늘지는 않는다."

## 판정 근거

A-1, A-3, A-4가 모두 통과했고 테넌트 경계를 넘는 경로가 없으므로 `blocked` 조건이 아니다. 이번 수정이 만든 불변 규칙 위반(사유 a)도 없다. `needs_fix`인 이유는 사유 (b), 이번에 고친 기록이 실제 동작과 다른 경우에 해당하기 때문이다. 심각도는 낮고 문장 하나의 수정이다. 코드와 마이그레이션은 건드릴 이유가 없으므로 이 수정만이라면 DB 재현을 반복할 내용은 없다. 프로젝트의 3라운드 상한을 이미 넘은 재확인이므로, 재리뷰 여부는 사람이 정할 일이다.

## 지시된 확인 항목의 결과

### `0025`의 `enqueue_source_job`

| 확인 | 결과 | 근거 |
| --- | --- | --- |
| 본문이 `0023`에 검사만 더한 것 | 맞음 | 두 정의의 diff는 `create` → `create or replace` 한 줄과 `0025:124-135`의 블록뿐이다 |
| 역할 검사 | 유지 | viewer와 비멤버는 Ask 값, 부재 값 모두 동일한 403 `편집 권한`. 존재 탐지 경로 없음 |
| raw_source 소유권 | 유지 | 다른 워크스페이스의 소스는 403 `편집 권한` |
| 예산 | 유지 | 상한 0에서 null trace는 `NW402`. 검사가 예산보다 앞이라 Ask 값은 `42501` |
| 중복 인큐 | 유지 | 같은 잡을 돌려주고 trace 불변. 단 Ask 값이면 중복 대상이어도 먼저 403 |
| definer, `search_path` | 유지 | `prosecdef=t`, `{search_path=public}`, 소유자 `postgres` |
| 권한, 설명 | 유지 | `0023` 적용 뒤와 `0025` 적용 뒤의 `proacl`과 설명 md5가 같다. 오버로드 1개 |
| `notify pgrst` | 있음 | `0025:350`. 같은 트랜잭션 안 |
| `0023` 머리말 | 다시 참 | 재현 1 |

### 기록 대조

| 기록 | 결과 | 근거 |
| --- | --- | --- |
| `design.md:167` 첫 부분과 "Ask 턴이 있는 trace에 한해" | 맞음 | 재현 2 |
| `design.md:167` 수용 (4)의 경로 세 가지와 그 결과 | 맞음 | 재현 3 |
| `design.md:167` 수용 (4)의 끝 문장 | **다름** | 지적 1 |
| `design.md:179` Migration Plan 2항 | 맞음 | 재현 1 |
| `migration-0023-0026-record.md:11` | 맞음 | `0025`의 내용과 일치 |
| `migration-0023-0026-record.md:21` | 동작과 무관, 참고 1 | |
| `specs/ai-control-room/spec.md:61` 스레드를 지운 trace | 맞음 | 재현 3. 삭제 뒤 인큐하면 owner 상세 200 |
| `specs/ai-control-room/spec.md:64` 같은 워크스페이스 한정 | 맞음 | 트리거가 `new.workspace_id`로 조회(`0025:61`, `:65`). r4 재현 6 |
| `specs/ai-control-room/spec.md:68` 같은 워크스페이스 한정 | 맞음 | 재현 2. 다른 워크스페이스의 Ask 값은 200 |
| `tasks.md:143-147` 8.7 | 동작은 맞음, 참고 4 | Then의 "실제 동작대로 적혀 있다"는 지적 1을 고쳐야 완전히 참이 된다 |

### 테스트 `test_editor_cannot_enqueue_a_job_under_an_ask_trace`

단언(`apps/api/tests/test_control_router.py:603-608`)은 유효하다. 관리자 키로 `workspace_id`와 `trace_id`를 걸어 조회하므로 RLS에 가려 빈 결과가 나오는 경우가 아니다. 조회가 실패하면 본문이 `[]`가 아니어서 테스트가 실패한다.

## 참고: 판정 사유가 아닌 것

1. **`migration-0023-0026-record.md:21`의 `0023`** (낮음): `0023`을 직접 수정했다고 적혀 있지만, 이번 이동으로 `git diff HEAD -- supabase/migrations/0023_job_trace.sql`은 0줄이다. 로컬 `schema_migrations`에 기록된 `0023`에도 검사가 없고, `design.md:192`는 `0025`, `0026`만 말한다. 넣었다 뺀 이력이므로 사실이 아니라고 할 수는 없다. "다시 만들어야 한다"는 결론도 `0025` 때문에 여전히 맞다. 지적 1을 고칠 때 `0023`을 함께 빼면 기록이 맞춰진다.
2. **`0023:202`의 함수 설명** (낮음): 설명은 유지되지만 `0025` 적용 뒤의 동작인 Ask trace 거부를 말하지 않는다. `0025`에 `comment on function`이 없다.
3. **`0025:8-9` 머리말** (낮음): "추가 전용", "두 함수"라고 하지만 이 파일은 이제 `enqueue_source_job`도 바꾸고 UPDATE 권한도 좁힌다. 이전 코드는 trace를 넘기지 않아 영향이 없으므로(재현 1의 null 호출, 재현 2) 동작은 문제없다.
4. **8.7의 검증 명령** (낮음): `tasks.md:146`의 명령은 전부 적용된 DB에서 돌아 "앞선 파일만 적용된 구간"을 재현하지 않는다. 그 근거인 호출자의 0001~0024 임시 프로젝트 실행은 `migration-0023-0026-record.md`, `design.md`, `tasks.md`에 적혀 있지 않다.
5. **턴이 사라지는 다른 경로** (낮음): `spec.md:61`과 수용 (4)는 "작성자가 스레드를 지운" 경우만 적었다. `ask_threads_user_id_fkey`도 `on delete cascade`이므로 계정 삭제로도 턴이 사라진다. FK만 확인했고 이 경로를 실행하지는 않았다.
6. **r4 재현 스크립트** (저장소 밖): `r4_cmp.py`는 `enqueue_source_job`을 `0023`의 `create function`에서 찾으므로 이제 틀린 본문과 비교한다. 이번에는 `0025`와 직접 비교했다.
7. **r1의 격리 스위트 간헐 실패**: 지시에 따라 판정 사유로 삼지 않았다. 전체 스위트를 돌리지 않았으므로 해소되었다고 말할 수 없다.

## 재현 기록

### 재현 1: 부분 적용 구간 (롤백 트랜잭션)

`0025`, `0026`이 만든 객체와 `ask_messages.trace_id`, `control_report`를 지워 0024까지의 상태를 흉내 내고, `0023` 4절의 파일 내용을 그대로 실행했다(첫 `drop`의 대상만 3인자로 바꿈). 호출은 `authenticated`로 했다.

| 단계 | 결과 |
| --- | --- |
| `ask_messages.trace_id` 컬럼 수 | 0 |
| 인큐, null trace | 성공, `queued` |
| 인큐, 이름 있는 2인자(이전 코드 형태) | 성공, `queued` |
| 인큐, trace 값 | 성공, 값 저장 |
| 이어서 컬럼 추가와 `0025` 1-1절 실행 | 성공. `prosecdef`, `proconfig`, 소유자, `proacl`, 설명 md5 동일, 오버로드 1개 |
| 그 함수 본문과 파일 | 일치 |

임의의 Ask 값이 존재할 수 없는 구간이므로 검사가 없어도 구멍이 없다. 배포 순서상 trace를 넘기는 새 코드도 아직 없다.

### 재현 2: 수정 함수의 동작 (실제 API, PostgREST)

| 호출 | 결과 |
| --- | --- |
| owner, viewer의 Ask trace | 403 `42501` `이 요청 식별자는 쓸 수 없습니다`, 잡 0건 |
| editor, 같은 값 | 같음 |
| viewer, Ask 값과 부재 값 | 둘 다 403 `편집 권한` |
| 비멤버, Ask 값과 부재 값 | 둘 다 403 `편집 권한` |
| 남의 raw_source | 403 `편집 권한` |
| null trace | 200 |
| 같은 대상, 다른 trace | 200, 같은 잡, trace 불변 |
| 같은 대상, Ask 값 | 403 `42501` |
| 영상 배치(같은 trace 2건) | 200, 200 |
| 다른 워크스페이스의 Ask 값 | 200 (`spec.md:68`의 한정과 일치) |
| 상한 0, null trace (롤백 SQL) | `NW402` |
| 상한 0, Ask 값 (롤백 SQL) | `42501` |
| anon, service_role (롤백 SQL) | `permission denied for function` |

### 재현 3: 수용 (4)

처리 후 수치의 사용량은 스크립트가 넣었다. 워커는 잡의 trace를 묶어 사용량을 쓰지만(`queue.py:245`, `llm_gateway.py:194`) 실제 워커를 돌리지는 않았다.

| 경우 | 전 | 인큐 | 후 |
| --- | --- | --- | --- |
| 스레드를 지운 viewer의 Ask trace | owner 상세 403, 사용량 잔존 | 200 | owner 상세 200, 질문 본문 없음 |
| viewer의 실제 `/retrieval` trace | owner 상세 403 | 200 | owner 상세 200, `calls` 1건. viewer 본인은 403 |
| owner의 수집 trace, editor의 잡 | `totals` 1건, 비용 1, 단계 5, 월 합계 3 | 200 | 아래 표 |

| 시점 | 표시 호출 수 | 표시 비용 | 단계 | 월 합계 |
| --- | --- | --- | --- | --- |
| 인큐 전 | 1 | 1 | 5 | 3 |
| 인큐 직후 | 1 | 1 | 6 | 3 |
| 처리 후 | 2 | 2 | 6 | **4** |

### 다시 실행한 검증

- `supabase/tests/0023_job_trace.sql`: `job_trace: ok`, 롤백
- `uv run pytest apps/api/tests/test_control_router.py`: 23 passed
- `openspec validate ai-control-flow-accounting --strict`: valid
- 로컬 `enqueue_source_job` 본문과 `0025` 파일: 일치

## 검증 범위

- 재현 스크립트:
  - `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/a44b5550-f4d4-4b96-b376-1e5e7a7a6cb1/scratchpad/r5_window.py`
  - `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/a44b5550-f4d4-4b96-b376-1e5e7a7a6cb1/scratchpad/r5_trace.py`
  - `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/a44b5550-f4d4-4b96-b376-1e5e7a7a6cb1/scratchpad/r5_budget.sql`
  - `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/a44b5550-f4d4-4b96-b376-1e5e7a7a6cb1/scratchpad/r4_trace2.py` (`/retrieval`과 수집 trace 경로)
- 재현 데이터는 정리했다. 마지막 확인에서 `auth.users`, `workspaces`, `jobs`, `usage_events`가 모두 0건이다. SQL 실측은 전부 롤백했고 DB 객체는 바꾸지 않았다. 보고서 외에 작업 트리를 바꾸지 않았다.
- 재현 1은 흉내 낸 상태다. 0024까지 실제로 적용한 것은 호출자의 임시 프로젝트 실행이며, 직접 재실행하지 않았다.
- 전제로 받고 직접 확인하지 않은 것: 전체 pytest 809 passed 1 skipped, vitest 463 passed, `pnpm typecheck`, `pnpm build`, 임시 프로젝트의 단계별 적용.
- 실행하지 않음: 전체 스위트, 실제 워커, 클라우드 환경, 시간 차이 측정.
