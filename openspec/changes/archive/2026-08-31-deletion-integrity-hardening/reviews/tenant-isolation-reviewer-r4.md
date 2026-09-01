# 테넌트 격리 리뷰: 4라운드

- 판정: **pass**
- 대상: `git diff main...HEAD` (`431b2332d70518894d99034ebce37754d416f91f`)
- 일시: 2026-09-01T10:18:33Z

⚠️ 프로젝트 규칙상 리뷰 라운드 상한은 3이지만, 사용자가 이번 건에 한해 4라운드를 명시적으로 승인했다. 라운드 번호 자체는 판정에 반영하지 않았다.

## 재검증 방법

r3의 두 지적 사항이 코드 수준에서 실제로 해소됐는지, 그리고 회귀 테스트가 실제로 그 취약점을 재현·차단하는지를 다음 방법으로 확인했다.

1. `supabase/migrations/0021_source_deletion_integrity.sql`의 함수 본문을 직접 읽고 이전 판(r3 검토 시점)과 대조했다.
2. 4개 신규 테스트를 로컬 스택(포트 54421)에 대해 직접 실행해 통과를 확인했다.
3. **회귀 테스트가 허위로 통과하지 않는지** 검증하기 위해, `assert_raw_source_reference`와 `enforce_ask_source_references`를 r3 시점의 버그 있는 구현으로 라이브 DB에 임시로 되돌린 뒤 같은 테스트를 다시 돌려 실제로 실패하는지 확인했다(정상 회귀 확인 후 `supabase db reset --local`로 원상 복구).
4. `supabase db lint --local`, `apps/api` 전체 pytest(221 passed), `apps/worker` 전체 pytest(154 passed)를 재실행했다.
5. `auth.uid()`와 `is_workspace_member()`의 실제 함수 본문을 `\df+`로 조회해 `service_role` JWT(로컬 `admin_key`, `sub` claim 없음)에서 `auth.uid()`가 정말 `null`을 반환하는지 확인했다.
6. `information_schema.role_table_grants`로 `wiki_pages`/`ask_messages`에 대한 `anon` 권한에 변화가 없는지 확인했다.

## r3 지적 1 — security definer 트리거의 존재 여부 노출 재검증

### 수정 내용 확인

`assert_raw_source_reference`(`supabase/migrations/0021_source_deletion_integrity.sql:82-112`)와 `enforce_ask_source_references`(`supabase/migrations/0021_source_deletion_integrity.sql:173-189`) 모두 원문/청크 조회보다 **앞서** 다음 게이트를 추가했다.

```sql
if (select auth.uid()) is not null
  and not public.is_workspace_member(p_workspace_id) then
  raise exception '참조할 원문이 존재하지 않는다' using errcode = '23503';
end if;
```

- `auth.uid()`가 `null`이 아닌 경우(사용자 요청 경로)에만 멤버십을 먼저 확인한다. 공격자가 자신이 속하지 않은 워크스페이스 UUID를 `p_workspace_id`(= `new.workspace_id`)로 넣으면, 대상 원문/청크가 존재하든 안 하든 **항상 같은 지점에서 같은 `23503`**을 반환한다 — 원문 존재 여부에 도달하기 전에 걸린다.
- 공격자가 **자신의** 워크스페이스에 다른 워크스페이스 소속 원문 UUID를 참조시키면, 멤버십 검사는 통과(자기 워크스페이스이므로)하지만 이어지는 `where r.workspace_id = p_workspace_id and r.id::text = p_source_id` 조회가 `p_workspace_id`(공격자 자신의 워크스페이스)로 필터링돼 있어 다른 워크스페이스의 원문은 보이지 않는다. 결과는 여전히 동일한 `23503`이다.
- `enforce_wiki_source_references`(위키)와 `enforce_publication_source_references`(발행본)는 모두 `assert_raw_source_reference`를 호출하므로 같은 보호를 물려받는다.
- `enforce_job_source_reference`(`jobs` INSERT)도 동일 함수를 호출하지만, `jobs` INSERT는 `authenticated`에 권한이 없고 `delete_raw_source` RPC 내부(이미 owner 검증을 마친 뒤, 삭제 전 시점이라 원문이 아직 존재)에서만 발생하므로 실사용 경로에서 이 게이트에 걸릴 일이 없다.
- **worker(`service_role`) 경로**: `auth.uid()`는 로컬 `admin_key`(service_role JWT, `sub` claim 없음)에서 `null`을 반환함을 `\df+ auth.uid`로 직접 확인했다 — `coalesce(request.jwt.claim.sub, request.jwt.claims->>'sub')::uuid`이며 둘 다 없으면 `null`이다. 따라서 `if (select auth.uid()) is not null` 분기 자체가 평가되지 않고 워커는 기존과 동일하게 잠금+존재 확인 경로로 직행한다. **BYPASSRLS 워커 경로는 이 변경으로 막히지 않는다.**

### 신규 회귀 테스트 검증

- `test_wiki_reference_guard_hides_cross_tenant_source_existence` (`apps/api/tests/test_sources_router.py:677`)와 `test_ask_reference_guard_hides_cross_tenant_chunk_existence` (`apps/api/tests/test_sources_router.py:724`)는 공격자 JWT로 **PostgREST에 직접** `wiki_pages`/`ask_messages` INSERT를 보내 존재하지 않는 UUID와 피해자 워크스페이스의 실제 UUID를 각각 참조시키고, 반환된 `(code, message)`가 완전히 동일한지 검증한다. r3가 지적한 정확한 공격 시나리오(피해 워크스페이스 UUID + 후보 원문 UUID를 직접 PostgREST에 투척)를 그대로 재현한다.
- `test_service_role_keeps_reference_guard_bypass_for_worker_jobs` (`apps/api/tests/test_sources_router.py:774`)는 `admin_key`로 `jobs` INSERT가 여전히 201을 반환하는지 확인해, 새 게이트가 워커 경로를 막지 않음을 증명한다.
- **허위 통과 여부 검증**: 위 세 함수를 r3 시점의 버그 있는 버전(멤버십 선행 검사 없음, 단일 snapshot 재검증)으로 라이브 DB에 되돌려 같은 4개 테스트를 실행한 결과, `test_wiki_reference_guard_hides_cross_tenant_source_existence`·`test_ask_reference_guard_hides_cross_tenant_chunk_existence`·`test_ask_reference_writer_revalidates_after_concurrent_delete_commits` 3건이 정확히 예상대로 실패했다(`test_service_role_...`은 원래도 이 버그와 무관하므로 그대로 통과). 이는 이 테스트들이 실제로 결함을 검출하는 능력이 있음을 뜻하며, 수정 전 코드에서는 통과하지 않는다는 것을 직접 확인했다. 이후 `supabase db reset --local`로 수정된 마이그레이션을 재적용해 4건 모두 다시 통과함을 재확인했다.

## r3 지적 2 — Ask 트리거의 snapshot 경쟁 재검증

### 수정 내용 확인

`enforce_ask_source_references`(`supabase/migrations/0021_source_deletion_integrity.sql:173-261`)는 이제 다음 순서로 동작한다.

1. 첫 SQL(191-213행)에서 `citations.resolved`의 `source` 청크를 조회해 `v_missing_chunk`와 함께 **그 시점 snapshot에서 확인된 `raw_source_id` 집합을 `v_source_ids` 배열에 보존**한다.
2. `foreach v_source_id in array v_source_ids`(222-225행)로 그 **보존된 배열**을 순회하며 `lock_raw_source_reference`로 advisory lock을 잡는다. r3가 지적한 버그는 이 단계에서 배열을 다시 조회해 만들었다는 점이었는데, 지금은 1단계에서 이미 확보한 배열을 그대로 쓴다.
3. 잠금 획득 후(230-253행) **새 snapshot**에서 청크·`raw_source_id`·원문(`raw_sources`) 존재를 모두 다시 확인하고, 청크 누락·원문 미존재·`raw_source_id`가 잠근 집합(`v_source_ids`)에 없는 경우를 모두 `v_missing_chunk`로 묶어 `23503`을 던진다.

이 구조는 "잠그기 전 확인한 대상을 잠그고, 잠근 뒤 다시 확인한다"는 표준 패턴이며, 1단계와 2단계 사이의 snapshot 불일치로 잠금 대상이 사라지는 r3의 실패 시나리오(빈 배열 → 반복문 0회 실행 → 잠금·재검증 모두 생략)를 원천적으로 막는다.

### 신규 회귀 테스트 검증

`test_ask_reference_writer_revalidates_after_concurrent_delete_commits` (`apps/api/tests/test_sources_router.py:1124`)는 `docker exec`로 실제 두 개의 독립 psql 세션을 띄워 경쟁을 재현한다.

- 세션 A("blocker")가 advisory lock을 먼저 잡고 `pg_sleep(3)` 뒤 원문을 삭제·커밋한다.
- 세션 B("writer")는 blocker가 잠금을 잡은 뒤(즉 아직 삭제되지 않은 시점)에 `ask_messages` INSERT를 시작해, 트리거의 1단계 조회는 청크가 **존재하는 상태**로 통과하고, 2단계 잠금 획득에서 blocker가 쥔 락을 기다리며 블로킹된다(`pg_stat_activity.wait_event_type = 'Lock'`으로 실측 확인).
- blocker가 커밋(삭제 확정)한 뒤 writer가 잠금을 획득하면, 재검증 단계가 새 snapshot에서 청크·원문이 사라졌음을 감지해 `23503`으로 INSERT 전체를 실패시킨다. 테스트는 `writer.returncode != 0`과 오류 메시지, 그리고 `ask_messages`에 해당 행이 남지 않았음을 모두 확인한다.

이 테스트는 목(mock)이 아니라 실제 두 트랜잭션의 lock 대기 상태를 `pg_stat_activity`로 폴링해 확인하므로, 우연히 타이밍이 맞아 통과하는 구조가 아니다. 위 "허위 통과 여부 검증" 절차에서 버그 버전으로는 이 테스트가 실패(즉 writer가 조용히 성공)함을 직접 확인했으므로, 이 테스트가 실제로 경쟁 조건을 검출한다.

## 새로운 격리 문제 발생 여부

- **A-1 (service_role의 사용자 경로 사용)**: 해당 없음. 이번 diff는 사용자 요청 경로에 `service_role`을 새로 도입하지 않았다.
- **A-4 (워커 workspace_id 명시적 필터)**: `apps/worker/src/worker/handlers/delete_source_storage.py`는 `payload["workspace_id"]`/`payload["raw_source_id"]`를 명시적으로 사용해 storage 경로를 재구성하고 검증한다(`apps/worker/tests/test_delete_source_storage.py`로 확인). 이번 라운드에서 새로 추가된 `is_workspace_member` 선행 검사는 `auth.uid() is not null`로 게이트돼 있어 `service_role`(auth.uid() = null) 경로를 건드리지 않는다 — 코드 읽기와 `test_service_role_keeps_reference_guard_bypass_for_worker_jobs`로 이중 확인했다.
- **정상 사용자 흐름 회귀**: `is_workspace_member`는 "멤버인가"만 확인하는 넓은 게이트이고, 그 뒤에 오는 기존 RLS `with check`(`wiki_pages_insert_editor`는 `has_workspace_role(..., 'editor')`)가 역할별 세부 권한을 그대로 담당한다. 즉 이번 추가 검사가 기존보다 더 엄격한 조건을 앞세우지 않으므로 정상 owner/editor 흐름을 추가로 막지 않는다. `apps/api` 전체 스위트(221 passed) 및 `apps/worker` 전체 스위트(154 passed) 재실행으로 확인했다.
- **anon 권한**: `information_schema.role_table_grants`로 `wiki_pages`/`ask_messages`의 `anon` 권한을 조회한 결과 `TRUNCATE`/`REFERENCES`/`TRIGGER`뿐이며(Postgres 기본 스키마 권한), `INSERT`/`SELECT`/`UPDATE`/`DELETE`는 없다. 이번 diff는 `anon`에 새 GRANT를 추가하지 않았다.
- **마이그레이션 번호(E-15)**: `0021`이 `supabase/migrations/` 내 최고 번호이며, 상단 주석은 병렬 진행 중인 `0020`(BYOK) 변경과의 충돌을 이미 인지하고 있다. 이번 라운드의 diff는 새 마이그레이션 파일을 추가하지 않았다(기존 `0021` 파일 내부만 수정).

## 이번 diff의 나머지 검사 항목

이번 라운드는 r3의 두 `blocked` 항목 재검증에 집중하도록 범위가 지정됐다. 그 외 항목은 r1~r3에서 이미 통과 판정을 받았고 이번 diff(431b233)에서 관련 코드가 추가로 바뀌지 않았으므로 재확인만 하고 새 지적을 추가하지 않는다.

- B-6/B-7: `apps/api/src/api/errors.py`의 `_render_isolation_failure`가 `WorkspaceForbidden`(영향 행 0)과 SQLSTATE `42501`을 동일하게 403/`FORBIDDEN_BODY`로 매핑하는 단일 등록 지점 구조는 이번 diff로 바뀌지 않았다. `SourceInUse`(SQLSTATE `NW409` → 409)도 동일한 단일 등록 지점 패턴을 따른다.
- C-8/C-9: `delete_raw_source`는 삭제와 정리 잡 INSERT를 한 트랜잭션에서 처리하고 `on conflict do nothing`으로 정리 잡 재실행에 대비한다. `jobs` 직접 UPDATE는 이 diff에 없다.
- D-10~D-14: 이번 diff는 벡터 검색·토크나이저·프롬프트 템플릿·LLM 컨텍스트를 건드리지 않는다. 해당 없음.

## 실행한 검증 (이번 라운드)

- `uv run --project apps/api pytest -q apps/api/tests/test_sources_router.py -k 'hides_cross_tenant or keeps_reference_guard_bypass or revalidates_after_concurrent_delete'`: 4 passed
- 위 4개 테스트를 r3 버그 버전으로 되돌린 DB에서 재실행: 3 failed(예상대로), 1 passed(예상대로) — 회귀 테스트의 검출력 확인
- `supabase db reset --local` 후 재실행: 4 passed (수정판 복원 확인)
- `uv run --project apps/api pytest -q apps/api/tests/test_sources_router.py`: 47 passed
- `uv run --project apps/api pytest -q apps/api/tests/`: 221 passed
- `uv run --project apps/worker pytest -q apps/worker/tests/`: 154 passed
- `supabase db lint --local`: 스키마 오류 없음
- `\df+ auth.uid`, `\df+ public.is_workspace_member`, `information_schema.role_table_grants`(wiki_pages/ask_messages, anon/authenticated/service_role) 직접 조회로 함수 본문·권한 실측 확인

## 판정 근거

r3가 `blocked`로 지적한 두 항목 모두 코드 수준에서 실제로 해소됐음을 함수 본문 대조로 확인했고, 신규 회귀 테스트 4건이 수정 전 코드에서는 실제로 실패하고(직접 재현) 수정 후 코드에서는 통과함을 라이브 스택에서 왕복 검증했다. `is_workspace_member` 선행 검사는 `auth.uid() is not null` 가드로 `service_role`(worker) 경로를 건드리지 않으며, 정상 워크스페이스 멤버의 기존 삽입·수정 흐름도 뒤따르는 RLS `with check`가 그대로 세부 권한을 판정하므로 추가로 막히지 않는다. anon 권한 확대, 신규 마이그레이션 번호 역전, 사용자 경로의 service_role 사용 등 다른 `blocked`급 패턴도 발견되지 않았다. 따라서 `pass`로 판정한다.
