# 테넌트 격리 리뷰: 2라운드

## 최종 판정

**needs_fix**

## 1라운드 수정 확인

`delete_raw_source`가 네 참조 테이블을 `share` 모드로 잠근 다음 참조를 검사하므로, 참조 writer가 먼저 `row exclusive` 잠금을 획득한 경우에는 삭제 요청이 writer의 커밋을 기다린다. 추가된 동시성 테스트도 이 순서를 재현하며, 커밋된 위키 참조를 확인한 삭제 RPC가 409를 반환하는 것을 검증한다.

그러나 잠금 획득 순서가 반대인 경우와 전역 테이블 잠금의 lock upgrade는 아직 안전하지 않다.

## 지적 사항

### 1. 삭제 RPC가 먼저 잠근 뒤 시작한 참조 writer는 삭제 후 끊어진 참조를 저장할 수 있다

- 심각도: 높음
- 위치: `supabase/migrations/0021_source_deletion_integrity.sql:97`, `supabase/migrations/0021_source_deletion_integrity.sql:108`, `supabase/migrations/0021_source_deletion_integrity.sql:173`
- 관련 테스트: `apps/api/tests/test_sources_router.py:748`

테이블 `share` 잠금은 삭제 트랜잭션이 진행되는 동안 writer를 대기시킬 뿐, 삭제 커밋 뒤에 writer가 끊어진 JSONB 참조를 저장하는 일은 막지 않는다. 참조 writer 쪽에는 `raw_sources` 존재를 강제하는 FK·트리거·공통 잠금 규약이 없다.

공격 또는 실패 시나리오는 다음과 같다.

1. owner의 삭제 트랜잭션이 `wiki_pages`를 포함한 네 테이블의 `share` 잠금을 먼저 획득한다.
2. 같은 워크스페이스의 editor가 해당 원문 UUID를 `wiki_pages.sources`에 넣는 INSERT 또는 UPDATE를 시작한다. 이 writer는 `row exclusive` 잠금을 얻지 못해 대기한다.
3. 삭제 RPC는 참조를 0건으로 확인하고 원문과 청크를 삭제한 뒤 202를 반환하며 커밋한다.
4. 대기하던 editor writer가 잠금을 얻고 JSONB 참조를 그대로 커밋한다. DB에는 이미 존재하지 않는 원문을 가리키는 위키 참조가 남지만, writer를 거부하는 제약이 없어 오류가 발생하지 않는다.

같은 문제가 공개본과 Ask JSONB 인용에도 적용된다. 활성 잡 경로도 완전히 닫히지 않는다. `enqueue_source_job`은 `raw_sources` 존재를 일반 SELECT로 확인한 뒤 나중에 `jobs` INSERT를 시도하므로, 삭제 트랜잭션의 미커밋 삭제 이전 버전을 읽고 `jobs` 잠금에서 대기했다가 삭제 커밋 후 고아 parse 잡을 삽입할 수 있다 (`supabase/migrations/0010_budget_error_sqlstate.sql:34`, `supabase/migrations/0010_budget_error_sqlstate.sql:57`).

현재 동시성 테스트는 writer가 먼저 잠금을 잡고 삭제가 나중에 기다리는 순서만 검증한다. 삭제가 먼저 잠근 상태에서 writer를 시작하는 반대 순서도 검증해야 한다. 두 연산 중 삭제가 먼저 확정되면 이후 참조 생성이 실패해야 하므로, 참조 생산자가 같은 원문 단위 잠금을 사용하고 잠금 획득 뒤 원문 존재를 확인하거나 FK가 있는 참조 원장을 사용해야 한다.

### 2. 전역 `share` 잠금 뒤 `jobs` INSERT를 수행하면 동시 삭제끼리 deadlock이 발생할 수 있다

- 심각도: 중간
- 위치: `supabase/migrations/0021_source_deletion_integrity.sql:101`, `supabase/migrations/0021_source_deletion_integrity.sql:104`, `supabase/migrations/0021_source_deletion_integrity.sql:160`

`share` 잠금은 다른 `share` 잠금과 호환되지만, INSERT가 요구하는 `row exclusive` 잠금과는 충돌한다. 서로 다른 워크스페이스에서 Storage 원문 삭제 두 건이 동시에 실행되면 두 트랜잭션이 모두 `jobs`의 `share` 잠금을 획득한 다음, 각각 정리 잡을 INSERT하려고 `row exclusive`로 lock upgrade를 시도한다. 각 트랜잭션이 상대방의 `share` 잠금을 기다리므로 PostgreSQL이 하나를 deadlock으로 중단하며, API는 이를 500으로 반환한다.

잠금 범위가 원문이나 워크스페이스가 아니라 테이블 전체이기 때문에 한 테넌트의 반복 삭제가 다른 테넌트의 wiki·Ask·잡 쓰기까지 지연시키는 가용성 격리 문제도 생긴다. 전역 테이블 잠금 대신 원문별 advisory lock 또는 참조 행/FK 기반 잠금처럼 테넌트와 원문에 한정된 직렬화 수단이 필요하다.

## 유지된 보호 장치

- 사용자 요청은 요청자 JWT로 RPC를 호출하고, `service_role`은 worker Storage 정리에만 사용한다.
- owner가 아닌 사용자, 존재하지 않는 원문, 다른 워크스페이스 원문은 모두 고정된 403 응답으로 매핑되어 존재 여부가 노출되지 않는다.
- Storage 경로는 RPC와 worker 양쪽에서 workspace 및 source UUID를 확인한다.
- Storage DELETE는 404를 성공으로 취급하고 일시적 오류를 예외로 전파하므로 재실행이 멱등이며 실패가 성공으로 기록되지 않는다.

## 실행한 검증

- `uv run --project apps/api pytest -q apps/api/tests/test_sources_router.py -k 'concurrent_reference_writer or cross_tenant_is_forbidden or editor_is_forbidden'`: 3개 통과, 38개 제외
- `uv run --project apps/worker pytest -q apps/worker/tests/test_delete_source_storage.py apps/worker/tests/test_worker_storage.py`: 11개 통과

통과한 동시성 테스트는 첫 번째 지적 사항의 반대 잠금 순서를 다루지 않는다.
