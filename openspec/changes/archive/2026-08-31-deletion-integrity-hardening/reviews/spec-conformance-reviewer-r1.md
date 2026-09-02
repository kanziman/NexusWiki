# Spec Conformance 리뷰 — deletion-integrity-hardening r1

## 판정

**pass**

## 검토 범위

- delta spec: `source-management-wiki`의 `Owner-only raw source permanent deletion`
- delta spec: `unified-workspace-viewer`의 `Citation click integrates with the viewer`
- 구현: 원문 삭제 RPC·API 오류 매핑·Storage 정리 worker·Ask 콘텐츠 뷰어
- 검증: API 통합 테스트, worker 테스트, dashboard 테스트

## 시나리오 대조

| Requirement / Scenario | 결과 | 구현 및 테스트 근거 |
| --- | --- | --- |
| Owner-only raw source permanent deletion / Owner deletes raw source | 충족 | `delete_raw_source`는 owner와 대상 소유권을 확인하고 원문 행을 잠근 뒤, Storage 경로가 있으면 정리 잡을 삽입하고 원문을 삭제한다. 함수 호출 자체가 한 DB 트랜잭션이므로 잡 삽입과 삭제가 함께 확정되며, `source_chunks`와 그 안의 검색 임베딩은 FK cascade로 삭제된다 (`supabase/migrations/0021_source_deletion_integrity.sql:82-95,145-169`, `supabase/migrations/0002_search_schema.sql:58-105`). API는 RPC 결과가 정확히 1행일 때 202를 반환한다 (`apps/api/src/api/routers/sources.py:443-466`). 통합 테스트는 202와 원문 행 삭제를 확인한다 (`apps/api/tests/test_sources_router.py:623-642`). |
| Owner-only raw source permanent deletion / Storage cleanup is retried | 충족 | Storage DELETE의 404는 멱등 성공으로 끝나고 다른 오류는 전파된다 (`apps/worker/src/worker/storage.py:58-63`). 전파된 `HTTPStatusError`는 재시도 불가 오류에 포함되지 않으므로 큐가 `fail_job`으로 넘기며, 객체 삭제 또는 404 이전에는 `complete_job`에 도달하지 않는다 (`apps/worker/src/worker/queue.py:266-283`, `apps/worker/src/worker/errors.py:141-147`). 테스트는 200·204·404 성공과 503 예외 전파를 확인한다 (`apps/worker/tests/test_worker_storage.py:47-74`). |
| Owner-only raw source permanent deletion / Owner requests deletion of a referenced raw source | 충족 | RPC는 `wiki_pages.sources`, 공개본 `published_citations`, 저장된 Ask의 source chunk 인용, queued/running/failed 파이프라인 잡을 모두 검사하고 하나라도 있으면 삭제·잡 생성 전에 `NW409`를 발생시킨다 (`supabase/migrations/0021_source_deletion_integrity.sql:97-143`). API 단일 오류 매핑은 이를 409 `source_in_use`로 변환한다 (`apps/api/src/api/routers/sources.py:454-462`, `apps/api/src/api/errors.py:241-248,337-350`). 통합 테스트는 위키·공개본·Ask·활성 잡 네 경로의 409를 확인하며, 위키 경로에서는 원문과 참조가 모두 보존되는 것도 확인한다 (`apps/api/tests/test_sources_router.py:705-849`). |
| Owner-only raw source permanent deletion / Non-owner member attempts to delete raw source | 충족 | RPC의 첫 권한 검사는 owner가 아니면 SQLSTATE 42501을 반환하며 데이터 변경문에 도달하지 않는다 (`supabase/migrations/0021_source_deletion_integrity.sql:82-95`). API의 격리 오류 렌더러는 이를 고정 본문의 403으로 변환한다 (`apps/api/src/api/errors.py:188-218`). editor가 삭제를 시도했을 때 403과 원문 행 보존을 확인하는 통합 테스트가 있다 (`apps/api/tests/test_sources_router.py:665-689`). |
| Owner-only raw source permanent deletion / Deleting non-existent or foreign workspace source | 충족 | owner 확인 뒤에도 `(id, workspace_id)`로 잠글 원문이 없으면 동일한 42501을 발생시켜 존재 여부를 구분하지 않는다 (`supabase/migrations/0021_source_deletion_integrity.sql:86-95`). 타 테넌트와 존재하지 않는 ID는 모두 고정 본문의 403으로 검증된다 (`apps/api/tests/test_sources_router.py:645-662,692-702`). |
| Citation click integrates with the viewer / Member clicks a wiki citation marker | 충족 | Ask 마커는 요청자의 workspace로 위키 ID를 조회해 slug를 얻은 뒤 같은 Ask 화면의 `tab=wiki`로 이동하고, `ContentViewer`는 해당 slug의 위키를 렌더링한다 (`apps/dashboard/components/AskConversation.tsx:457-474`, `apps/dashboard/components/ContentViewer.tsx:138-144,203-267`). 테스트는 workspace와 ID 스코프 및 최종 URL을 확인한다 (`apps/dashboard/tests/AskConversation.test.tsx:344-374`). |
| Citation click integrates with the viewer / Member clicks a source citation marker | 충족 | source 마커는 별도 패널을 열지 않고 `chunkId`와 `tab=source`를 같은 Ask URL에 설정하며, `SourceChunkView`는 그 청크를 조회해 ready 상태에서 본문과 좌표를 표시한다 (`apps/dashboard/components/AskConversation.tsx:477`, `apps/dashboard/components/ContentViewer.tsx:315-325,334-398`). 라우팅 테스트가 source 탭과 청크 ID를 확인한다 (`apps/dashboard/tests/AskConversation.test.tsx:313-342`). |
| Citation click integrates with the viewer / Member clicks an unavailable wiki citation marker | 충족 | workspace-scoped 위키 조회 결과가 없으면 Ask 화면은 `missingCitation=wiki`와 wiki 탭으로 이동한다. 콘텐츠 뷰어는 이를 `not-found`로 초기화해 명시적인 접근 불가 안내를 표시한다 (`apps/dashboard/components/AskConversation.tsx:461-473`, `apps/dashboard/components/ContentViewer.tsx:203-228,277-283`). 마커 라우팅과 최종 안내 상태를 각각 테스트한다 (`apps/dashboard/tests/AskConversation.test.tsx:376-402`, `apps/dashboard/tests/ContentViewer.test.tsx:97-104`). |
| Citation click integrates with the viewer / Member clicks an unavailable source citation marker | 충족 | source chunk 조회가 오류 또는 0행이면 `unavailable` 상태로 전환하고 명시적 안내를 렌더링하므로 로딩 상태에 머물지 않는다 (`apps/dashboard/components/ContentViewer.tsx:334-375`). 테스트는 접근 불가 문구가 표시되고 로딩 `status`가 사라지는 것을 확인한다 (`apps/dashboard/tests/ContentViewer.test.tsx:106-114`). |

## 지적 사항

없음.

## 검증 증적

- `uv run pytest apps/api/tests/test_sources_router.py -q -rs`: 40개 통과
- `uv run pytest tests/test_delete_source_storage.py tests/test_worker_storage.py tests/test_handlers.py -q` (`apps/worker`): 28개 통과
- `pnpm test -- --run tests/AskConversation.test.tsx tests/ContentViewer.test.tsx tests/SourceDeletion.test.tsx` (`apps/dashboard`): 72개 파일, 356개 테스트 통과

실행 중 Vite 설정과 Node localStorage 관련 경고가 있었지만 테스트 실패나 시나리오 미충족은 없었다. delta spec의 모든 Given/When/Then 결과가 현재 작업 트리의 실제 사용자 경로에 연결되어 있다.
