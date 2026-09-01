# 테넌트 격리 리뷰: 3라운드

## 최종 판정

**blocked**

3라운드는 최대 리뷰 라운드다. 아래 테넌트 존재 정보 노출과 Ask 인용 경쟁 조건이 남아 있으므로, 프로젝트 규칙에 따라 추가 자동 수정 라운드로 진행하지 않고 사람의 판단이 필요한 `blocked`로 확정한다.

## 2라운드 수정 확인

- 전역 테이블 `share` 잠금은 제거되었다. 삭제 RPC와 참조 생산자가 `(workspace_id, source_id)`에서 유도한 원문별 advisory transaction lock을 공유하므로 다른 테넌트와 다른 원문의 쓰기를 전역으로 막지 않는다 (`supabase/migrations/0021_source_deletion_integrity.sql:65`, `supabase/migrations/0021_source_deletion_integrity.sql:289`).
- 위키 writer가 먼저 잠그면 삭제가 커밋을 기다린 뒤 409를 반환하고, 삭제가 먼저 잠그면 위키 writer가 기다린 뒤 23503으로 거부되는 양방향 회귀 테스트가 추가되었다 (`apps/api/tests/test_sources_router.py:748`, `apps/api/tests/test_sources_router.py:847`).
- 서로 다른 Storage 원문 삭제 두 건이 모두 202를 반환하는 테스트가 추가되어, 2라운드의 `jobs` lock upgrade 교착은 해소되었다 (`apps/api/tests/test_sources_router.py:1144`).

## 지적 사항

### 1. `security definer` BEFORE trigger가 RLS보다 먼저 외부 테넌트 원문 존재 여부를 노출한다

- 심각도: 치명적
- 위치: `supabase/migrations/0021_source_deletion_integrity.sql:82`, `supabase/migrations/0021_source_deletion_integrity.sql:105`, `supabase/migrations/0021_source_deletion_integrity.sql:128`
- 관련 권한과 정책: `supabase/migrations/0007_search_and_queue_extensions.sql:356`, `supabase/migrations/0004_rls_policies.sql:236`

`enforce_wiki_source_references`와 `assert_raw_source_reference`는 모두 `security definer`다. PostgreSQL은 INSERT의 BEFORE ROW trigger를 RLS `with check`보다 먼저 실행한다. 따라서 trigger가 호출자의 RLS를 우회하여 `raw_sources`를 조회한 뒤에야 `wiki_pages_insert_editor` 정책이 외부 워크스페이스 쓰기를 거부한다.

공격 시나리오는 다음과 같다.

1. 인증된 공격자가 피해 워크스페이스 UUID와 확인하려는 원문 UUID를 넣어 `wiki_pages` INSERT를 PostgREST에 직접 보낸다. `authenticated`에는 이 테이블의 INSERT 권한이 있다.
2. 확인하려는 원문이 없으면 definer trigger의 `assert_raw_source_reference`가 RLS 검사 전에 SQLSTATE `23503`과 "참조할 원문이 존재하지 않는다"를 반환한다.
3. 같은 UUID의 원문이 피해 워크스페이스에 실제로 있으면 definer trigger는 통과하고, 이후 `wiki_pages_insert_editor`의 `with check`가 SQLSTATE `42501`로 거부한다.
4. 공격자는 `23503`과 `42501`의 차이로 자신이 속하지 않은 워크스페이스의 원문 존재 여부를 구분할 수 있다.

Ask trigger도 같은 방식으로 외부 워크스페이스의 source chunk 존재 여부를 먼저 확인하므로 청크 UUID 열거 경로가 된다 (`supabase/migrations/0021_source_deletion_integrity.sql:164`). trigger 본문과 참조 조회를 `security invoker`로 실행해 요청자의 RLS가 먼저 데이터 가시성을 제한하도록 하거나, definer 조회 전에 호출자의 워크스페이스 권한을 확인하여 외부·없는 대상을 동일한 오류로 거부해야 한다. worker의 `service_role`은 invoker 방식에서도 BYPASSRLS를 유지하므로 별도 우회가 필요하지 않다.

### 2. Ask trigger가 청크 확인과 원문 잠금 사이에 청크를 다시 조회하여 삭제를 놓칠 수 있다

- 심각도: 높음
- 위치: `supabase/migrations/0021_source_deletion_integrity.sql:174`, `supabase/migrations/0021_source_deletion_integrity.sql:198`, `supabase/migrations/0021_source_deletion_integrity.sql:213`

`enforce_ask_source_references`는 첫 SQL 문장에서 source citation의 청크 존재를 확인한 뒤, 별도의 두 번째 SQL 문장에서 같은 청크를 다시 조회해 `raw_source_id`를 얻고 advisory lock을 잡는다. 이 trigger는 volatile 함수이므로 READ COMMITTED에서 두 내부 SQL 문장은 서로 다른 snapshot을 볼 수 있다.

실패 시나리오는 다음과 같다.

1. Ask INSERT trigger의 첫 청크 검사에서 대상 source chunk가 존재해 `v_missing_chunk = false`가 된다.
2. 첫 검사 직후 삭제 RPC가 원문별 advisory lock을 획득하고 원문과 source chunk를 cascade 삭제하여 커밋한다. Ask trigger는 아직 해당 advisory lock을 요청하지 않았다.
3. Ask trigger의 두 번째 쿼리는 새 snapshot에서 이미 삭제된 청크를 보지 못하므로 `for v_source_id` 반복문을 한 번도 실행하지 않는다.
4. 원문 잠금과 존재 재검증이 모두 생략된 채 Ask 메시지가 커밋되고, 삭제된 청크를 가리키는 JSONB 인용이 조용히 남는다.

첫 청크 조회에서 확인한 `raw_source_id` 집합을 함수 변수에 보존한 다음 정렬된 advisory lock을 획득하고, 잠금 뒤 청크와 원문 존재를 다시 검증해야 한다. writer-first와 delete-first 테스트도 위키뿐 아니라 청크 ID를 원문 ID로 변환하는 Ask 경로를 포함해야 한다.

## 유지된 보호 장치

- 삭제 API는 요청자 JWT를 사용하고 RPC는 owner 역할을 먼저 검사한다. 없는 원문과 외부 원문은 동일한 403 본문으로 매핑된다.
- advisory lock 키는 workspace와 source를 함께 포함하므로 서로 다른 테넌트가 같은 source UUID를 사용해도 잠금 범위가 합쳐지지 않는다.
- Storage 경로는 RPC와 worker 양쪽에서 workspace 및 source UUID를 검증한다.
- Storage DELETE는 404를 성공으로 처리하고 다른 실패를 예외로 전파하므로 at-least-once 재실행이 멱등이며 일시적 장애를 성공으로 기록하지 않는다.
- cleanup job과 원문 삭제는 같은 트랜잭션에 남아 있으며, DB 행 삭제 직후 Storage SELECT 정책이 정리 대기 객체의 사용자 읽기를 차단한다.

## 실행한 검증

- `uv run --project apps/api pytest -q apps/api/tests/test_sources_router.py -k 'concurrent_reference_writer or source_lock_first or two_storage_source_deletions'`: 3개 통과, 40개 제외
- `uv run --project apps/worker pytest -q apps/worker/tests/test_delete_source_storage.py apps/worker/tests/test_worker_storage.py`: 11개 통과

통과한 회귀 테스트는 위키의 양방향 잠금 순서와 동시 삭제를 검증하지만, 외부 테넌트 trigger 오류의 동일성 및 Ask trigger 내부 두 snapshot 사이의 삭제 경쟁은 검증하지 않는다.
