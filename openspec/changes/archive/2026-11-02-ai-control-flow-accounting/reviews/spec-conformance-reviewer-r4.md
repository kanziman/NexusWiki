# Spec Conformance 리뷰 — ai-control-flow-accounting r4 (범위 한정 확인 리뷰)

- 판정: pass
- 대상: 기준 커밋 `79b68fe` 대비 `66a2afd` + 커밋되지 않은 작업 트리. 범위는 r3 미충족 1건의 해소 여부와 이번 수정의 영향이다
- 일시: 2026-11-02T11:09:45Z

## 요약

r3의 미충족 1건은 해소됐다. 직접 INSERT가 `start_ask_turn`과 같이 `42501`로 거부되고, 상세 조회는 계속 403이다. 새 Scenario "editor가 다른 멤버의 Ask trace로 잡을 만들려 한다"도 충족한다. 정상 경로(새 턴, 사용량 뒤 재전달, 한 요청의 다중 인큐)는 실제 라우트에서 통과했다.

이번 수정과 관련해 미충족으로 판정한 Scenario는 없다. 다만 스펙 문구나 Risks 목록과 어긋나는 잔여 경우 3건을 실측하거나 판독했고 "참고"에 분리했다. 참고 1은 Scenario 문구를 어떻게 읽느냐에 따라 판정이 갈릴 수 있어, 내가 택한 해석을 함께 적었다.

r3에서 충족으로 판정한 다른 Scenario는 다시 감사하지 않았다.

## 직접 실행한 검증

| 항목 | 결과 |
| --- | --- |
| `apps/api/tests/test_control_router.py`, `apps/worker/tests/test_worker_main.py` | 35 통과 |
| `apps/api/tests/test_sources_router.py -k "youtube or enqueue"` | 5 통과 |
| `supabase/tests/0023_job_trace.sql` | `job_trace: ok`, 롤백 |
| `openspec validate ai-control-flow-accounting --strict` | valid |
| 로컬 DB 함수 본문과 파일 비교 (`ask_messages_reject_used_trace`, `enqueue_source_job`) | 둘 다 일치 |
| 트리거 상태와 함수 권한 | `ask_messages_reject_used_trace`가 `BEFORE INSERT`로 켜져 있다. 함수 ACL은 `postgres`만 남아 있다 |
| 스크래치 프로브 (실제 API를 ASGI로, 실제 PostgREST) | 7건 실행, 아래 "실측" |

전체 pytest, vitest, typecheck, lint, build, 임시 프로젝트의 0001~0026 전체 적용, 트리거를 끈 상태의 회귀 실패 4건은 호출자가 알린 결과를 인용하며 재실행하지 않았다.

프로브는 저장소 밖에 두었고 실행 뒤 지웠다. 실행 뒤 `ask_messages`, `auth.users`, `workspaces`, `jobs`, `usage_events`, `raw_sources`가 모두 0행이다.

## 실측

### r3 표 재실행

| 원본 trace | 요청자 | 상세(전) | `start_ask_turn` | 직접 `POST /rest/v1/ask_messages` | 상세(후) |
| --- | --- | --- | --- | --- | --- |
| 다른 멤버의 Ask 턴과 사용량 | viewer | 403 | 403 `42501` | **403 `42501`** (r3: 201) | **403** (r3: 200) |
| 다른 멤버의 Ask 턴과 사용량 | editor | 403 | 403 `42501` | 403 `42501` | 403 |
| 수집 잡 | viewer | 403 | 403 `42501` | **403 `42501`** (r3: 201) | **403** (r3: 200) |
| 수집 잡 | editor | 200 (권한 있음) | 403 `42501` | 403 `42501` | 200 (변화 없음) |

상세의 403 본문은 `{"detail":"forbidden"}`이다. 거부 전후로 해당 trace의 `ask_messages` 행 수가 변하지 않았다.

### 우회 시도

| 시도 | 결과 |
| --- | --- |
| 대량 INSERT (정상 행 + 이미 쓰인 trace 행) | 403 `42501`, 정상 행도 들어가지 않음 |
| upsert (`resolution=merge-duplicates`)로 내 턴의 trace 교체 | 403 `42501`, 값 유지 |
| `PATCH`로 내 턴의 trace 교체 | 403 `42501`, 값 유지 |
| trace 값을 대문자로 표기 | 403 `42501` |
| `/ask`에 `X-Trace-Id` 위조 | 200, 저장값은 서버 발급 값이며 위조값이 아님 |
| 비멤버의 직접 INSERT, 쓰인 trace와 없는 trace 비교 | 둘 다 409 `23503`, 같은 메시지. 존재 탐지가 생기지 않음 |
| 비멤버와 viewer의 `enqueue_source_job` | 403 `42501`, 역할 검사의 메시지. trace 검사에 닿지 않음 |

거부 시도 뒤 작성자의 상세는 200, `calls` 1건, 비용 합계 그대로다.

### 잡 인큐

| 경우 | 결과 |
| --- | --- |
| editor가 다른 멤버의 Ask trace로 인큐 (사용량 있음) | 403 `42501`, 그 trace의 잡 0건, 상세 403 |
| 같은 경우 (턴만 있고 사용량 없음) | 403 `42501`, 잡 0건, 상세 403 |
| 같은 대상 중복 인큐 | 200, 같은 잡, 기존 trace 유지 |
| trace 없는 인큐 | 200, 값 null |

### 정상 경로

| 경로 | 결과 |
| --- | --- |
| `/ask` 새 턴 (viewer) | 200, 1행. 응답 헤더, 저장값, 서비스가 본 컨텍스트의 trace가 모두 같음 |
| 사용량이 쌓인 뒤 같은 `client_turn_id`로 `/ask` 재전달 | 200, 1행. 저장값 유지, 저장된 trace로 다시 묶임. 작성자 상세 200 |
| 같은 스레드의 다음 턴 | 200 |
| `POST /sources/youtube-videos` 영상 3건 | 202, 3건 모두 `registered`. 한 요청 trace 아래 잡 3건, 상세 200 |
| `POST /sources/text` | 202, 잡 1건 |

`/ask`는 턴 저장과 trace 묶기까지 실제 경로로 지나고, 스트리밍 서비스만 대역으로 바꿨다.

## 시나리오 판정

### 이번 수정의 직접 대상

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| trace 식별자 고정 / 멤버가 이미 쓰인 trace로 새 턴을 만들려 한다 | 충족 (r3: 미충족) | 트리거 `supabase/migrations/0025_ask_trace.sql:51-76`, 권한 회수 `:79` · 테스트 `apps/api/tests/test_control_router.py:459`(함수), `:507`(직접 INSERT), 각각 사용량과 잡 매개변수 · 위 실측. 다른 워크스페이스의 값은 참고 1 |
| trace 식별자 고정 / editor가 다른 멤버의 Ask trace로 잡을 만들려 한다 | 충족 | `supabase/migrations/0023_job_trace.sql:160-167` · 테스트 `test_control_router.py:583`(거부), `:605`(다중 인큐 허용) · 위 실측. 테스트 공백은 참고 3 |
| 작성자와 역할 / editor가 다른 멤버의 Ask trace를 요청한다 | 충족 (r3의 우회 해소) | `apps/api/src/api/routers/control.py:332`, `:369`, `:386` · 테스트 `test_control_router.py:202` · 직접 INSERT와 인큐 모두 거부되어 요청자가 게이트를 만들 수 없음(위 실측). 스레드 삭제 뒤의 경우는 참고 2 |

### 이번 수정이 깨뜨릴 수 있는 Scenario

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| trace 식별자 고정 / 작성자가 턴의 trace를 바꾸려 한다 | 충족 | `0025_ask_trace.sql:39-41` · 테스트 `test_control_router.py:439` · upsert, `PATCH` 실측 |
| 작성자와 역할 / 작성자가 자신의 Ask trace를 본다 | 충족 | 테스트 `test_control_router.py:140` · 거부 시도 뒤와 재전달 뒤의 상세 200 실측. 재전달 `:629`, `apps/api/src/api/routers/ask.py:101`, `:109` |
| 잡 체인 / 수집 체인 완료 | 충족 | 인큐 `apps/api/src/api/routers/sources.py:268`, 라우트 `:588` · 테스트 `test_control_router.py:605` · 영상 3건, 텍스트 1건 실측 |
| 잡 체인 / 이미 큐에 있는 대상의 중복 인큐 | 충족 | `0023_job_trace.sql:196-205` · 테스트 `supabase/tests/0023_job_trace.sql` · 위 실측 |
| 잡 체인 / trace가 없던 기존 잡 | 충족 | `0023_job_trace.sql:160`의 null 조건 · 위 실측(새 인큐). 처리 경로는 변경 없음 |

### r3 참고 항목의 후속

`_serve_internal_listeners`의 기록 대기 연결은 이제 테스트가 고정한다. `apps/worker/tests/test_worker_main.py:222-249`가 실제 함수를 돌려 `apps/worker/src/worker/__main__.py:305`가 넘긴 값을 단언한다. 인자를 빼거나 비우면 실패한다(코드 판독, 변이 실행은 하지 않음).

### 문서 정정

`design.md:167`, `docs/ops/migration-0023-0026-record.md:9`, `:11`, `0025_ask_trace.sql:43-50`이 구현과 일치한다. #170과 #172는 `gh issue view`로 열린 상태와 제목, 완료 조건을 확인했다.

## 조치가 필요한 항목

없음.

## 참고 (차단 사유 아님)

1. **Scenario 문구와 Risks 수용의 간극.** Scenario의 WHEN은 "사용량이나 잡에 이미 있는 `trace_id`"이고 워크스페이스를 한정하지 않는다. 트리거는 같은 워크스페이스만 본다(`0025_ask_trace.sql:61`, `:65`). 두 워크스페이스의 멤버가 한쪽의 trace로 다른 쪽에 턴을 만들면 200이다(실측). 값을 가져온 쪽의 상세는 계속 403이므로 THEN의 뒷절은 성립하고, 앞절의 거부만 일어나지 않는다.
   - 내 해석: trace 조회가 전부 `workspace_id`로 갈리고 `design.md:167`의 (3)이 이 경우를 수용하므로, Scenario를 같은 워크스페이스에 대한 것으로 읽어 충족으로 판정했다.
   - 제안: 호출자가 알린 승인 범위에 이 수용이 들어 있는지는 내가 확인하지 못했다. 스펙 동기화 전에 WHEN에 "같은 워크스페이스의"를 넣으면 문구와 구현이 맞는다. 스펙 변경이므로 사람이 정할 일이다.

2. **작성자가 스레드를 지운 뒤에는 그 trace로 잡을 만들 수 있다.** 턴이 사라지면 `0023_job_trace.sql:160-167`의 검사에 걸리지 않는다. editor가 그 trace로 인큐하면 200이고, 상세가 403에서 200으로 바뀌어 사용량 `calls` 1건이 나온다(실측).
   - 미충족으로 보지 않은 이유: 게이트가 지키는 작성자 턴이 더 이상 없고, 돌아오는 값은 RLS로 이미 읽을 수 있다. viewer의 직접 INSERT는 사용량 행이 남아 있어 계속 거부된다(코드 판독).
   - 제안: `design.md:167`의 "남은 경우"는 세 가지만 적고 있으니 이 경우를 네 번째로 적는다.

3. **`test_control_router.py:583`은 "잡을 만들지 않는다"를 단언하지 않고, 다른 멤버의 trace도 쓰지 않는다.** owner가 자기 trace로 호출하며 상태 코드만 본다. 검사가 작성자를 가리지 않고 예외가 삽입 앞에서 나므로 동작은 같고, 다른 멤버의 경우와 잡 0건은 위 실측으로 확인했다. 잡 건수 단언을 더하면 Scenario의 THEN이 테스트로 고정된다.

4. **`0023`만 적용되고 `0025`가 아직인 구간에서는 모든 인큐가 실패한다.** `0023_job_trace.sql:160-164`가 `ask_messages.trace_id`를 읽는데 이 컬럼은 `0025`가 만든다. `p_trace_id`가 null이어도 식 전체를 먼저 해석하므로, 같은 모양의 식을 없는 컬럼으로 실행하면 `42703`이 났다(실측). 따라서 `0023:8-9`의 "이 파일을 적용한 뒤에도 이전 버전 코드가 그대로 동작합니다"는 이제 정확하지 않다. `:158-159`에 "네 파일은 함께 적용"이 적혀 있고 전체 적용은 통과하므로, 순차 적용 중의 짧은 구간이나 중간 파일 실패 때만 문제가 된다. 대응 Scenario는 없다. 머리 주석과 `design.md`의 Migration Plan 2항을 고치고, 클라우드 적용 절차에 중간 실패 시 대응을 적는 편이 낫다.

5. **`tasks.md`에 이번 수정이 드러나지 않는다.** 8.6의 Given은 "멤버가 이미 쓰인 trace로 턴을 만들거나"까지이고, 직접 INSERT 경로와 잡 인큐 거부를 적은 task가 없다. 구현과 테스트는 있으므로 범위 축소는 아니며, 추적 기록의 공백이다.

6. 결정대로 판정에서 뺀 것: task 7.3 미완료, `after.commit`의 `uncommitted`, `RESUME.md`.

## 판정 근거

`pass`다. r3의 미충족 1건은 Scenario의 THEN 두 절이 직접 INSERT 경로에서도 참이 됐고, 새 Scenario와 정상 경로도 실제 스택에서 확인했다. 참고 1과 2는 스펙 문구나 Risks 목록을 다듬을 사안이고, 다른 멤버의 턴이 살아 있는 동안 그 상세를 여는 경로는 찾지 못했다. 다른 테넌트의 값이 나오는 경로도 찾지 못했다.
