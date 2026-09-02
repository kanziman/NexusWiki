# 테넌트 격리 리뷰: 1라운드

## 최종 판정

**needs_fix**

## 지적 사항

### 1. 참조 검사와 삭제 사이의 경쟁 조건으로 근거가 조용히 유실될 수 있다

- 심각도: 높음
- 위치: `supabase/migrations/0021_source_deletion_integrity.sql:86`, `supabase/migrations/0021_source_deletion_integrity.sql:99`, `supabase/migrations/0021_source_deletion_integrity.sql:159`

`delete_raw_source`는 대상 `raw_sources` 행만 `for update`로 잠근 뒤 JSONB 참조와 활성 잡을 검사하고 원문을 삭제한다. 그러나 `wiki_pages.sources`, `wiki_page_publications.published_citations`, `ask_messages.citations`, `jobs.payload`를 쓰는 트랜잭션은 이 원문 행 잠금과 충돌하지 않으며, 참조 테이블에도 쓰기 방지 잠금이 없다.

공격 또는 실패 시나리오는 다음과 같다.

1. 워크스페이스 owner의 삭제 트랜잭션이 원문 행을 잠그고 참조 검사에서 0건을 확인한다.
2. 같은 워크스페이스의 editor가 `wiki_pages.sources`에 해당 원문 UUID를 추가하거나, Ask 인용 또는 공개본 인용을 저장하고 커밋한다. 일반적인 동시 요청에서도 같은 순서가 발생할 수 있다.
3. 삭제 트랜잭션은 참조를 다시 검사하지 않고 `raw_sources`를 삭제해 커밋한다.
4. 위키·공개본·Ask 이력에는 삭제된 원문을 가리키는 JSONB 참조가 남고, API는 202를 반환한다. 이 상태는 예외나 실패 잡으로 드러나지 않는다.

따라서 하나의 DB 트랜잭션으로 묶었다는 사실만으로 참조 검사와 삭제가 원자적이라고 볼 수 없다. 참조 생산자와 삭제 RPC가 같은 잠금 규약을 사용하게 하거나, 삭제 중 관련 참조 테이블의 쓰기를 막고 잠금 획득 후 참조를 검사해야 한다. 같은 경쟁 순서를 재현하는 회귀 테스트도 필요하다.

## 확인한 보호 장치

- API는 요청자 JWT로 `delete_raw_source`를 호출하고, 사용자 요청 경로에 `service_role`을 사용하지 않는다 (`apps/api/src/api/routers/sources.py:443`).
- RPC는 owner 역할을 먼저 확인하고, 대상이 없거나 다른 워크스페이스에 있으면 모두 SQLSTATE `42501`을 발생시킨다 (`supabase/migrations/0021_source_deletion_integrity.sql:82`, `supabase/migrations/0021_source_deletion_integrity.sql:93`). API의 단일 오류 처리 지점은 이를 동일한 403 본문으로 변환하므로 존재 여부가 응답으로 노출되지 않는다 (`apps/api/src/api/errors.py:188`).
- `delete_source_storage` worker는 BYPASSRLS인 service role을 사용하기 전에 잡의 `workspace_id`, `raw_source_id`, `storage_path` 세그먼트를 대조한다 (`apps/worker/src/worker/handlers/delete_source_storage.py:38`). 다른 테넌트 또는 다른 원문으로 변조된 payload는 Storage 호출 전에 거부된다.
- Storage DELETE의 404를 성공으로 처리하고 그 밖의 실패를 예외로 전파하므로, at-least-once 재실행은 멱등이고 일시적 장애가 성공으로 기록되지 않는다 (`apps/worker/src/worker/storage.py:58`).
- DB 행이 삭제된 뒤에도 객체가 남는 구간에서는 Storage SELECT 정책이 대응하는 `raw_sources` 행을 요구하므로 일반 멤버가 정리 대기 객체를 읽을 수 없다 (`supabase/migrations/0021_source_deletion_integrity.sql:41`).

## 실행한 검증

- `uv run --project apps/worker pytest -q apps/worker/tests/test_delete_source_storage.py apps/worker/tests/test_worker_storage.py apps/worker/tests/test_handlers.py`: 28개 통과
- `uv run --project apps/api pytest -q apps/api/tests/test_sources_router.py -k 'delete_source or cleanup_pending_storage_object'`: 9개 통과, 31개 제외

현재 테스트는 순차 실행 경로만 검증하므로 위 경쟁 조건을 탐지하지 못한다.
