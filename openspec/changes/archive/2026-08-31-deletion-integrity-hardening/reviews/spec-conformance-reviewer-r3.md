# Spec Conformance 리뷰 — deletion-integrity-hardening r3

## 판정

**pass**

## 검토 범위

- 최대 3라운드 중 최종 라운드
- tenant isolation r2의 delete-first 경쟁 조건과 전역 `share` 잠금 deadlock 지적
- 아카이브된 `source-management-wiki`와 `unified-workspace-viewer` delta spec 전체

## r2 이후 수정 사항 확인

### 원문별 참조 직렬화

전역 테이블 잠금은 제거됐다. 삭제 RPC와 참조 생산자는 `(workspace_id, source_id)`를 `hashtextextended`한 같은 키로 transaction-level advisory lock을 획득한다 (`supabase/migrations/0021_source_deletion_integrity.sql:58-103,267-300`).

참조 생산자에는 다음 검증 트리거가 연결됐다.

- `wiki_pages.sources`: 원문 ID를 정렬해 잠근 뒤 원문 존재를 확인한다 (`0021_source_deletion_integrity.sql:105-131`).
- `wiki_page_publications.published_citations`: 인용 anchor를 정렬해 잠근 뒤 원문 존재를 확인한다 (`0021_source_deletion_integrity.sql:133-162`).
- `ask_messages.citations`: source chunk의 workspace 소유권과 존재를 확인하고, 연결된 원문 ID를 정렬해 같은 잠금을 획득한다 (`0021_source_deletion_integrity.sql:164-222`).
- `jobs.payload.raw_source_id`: 잡 INSERT 전에 같은 잠금과 원문 존재 검사를 수행한다 (`0021_source_deletion_integrity.sql:224-244`).

따라서 참조 writer가 먼저 잠그면 삭제 RPC가 기다린 뒤 커밋된 참조를 발견해 409를 반환한다. 삭제 RPC가 먼저 잠그면 원문 삭제가 커밋된 뒤 writer의 존재 재검사가 23503으로 실패한다. 이 양방향 경계가 실제 PostgreSQL 동시성 테스트로 검증된다 (`apps/api/tests/test_sources_router.py:747-987`).

### 전역 잠금 deadlock 제거

잠금 키가 원문별이므로 서로 다른 원문은 같은 참조 테이블이나 `jobs`에 쓰더라도 advisory lock을 공유하지 않는다. Storage 경로가 있는 서로 다른 원문 두 건을 동시에 삭제해 두 응답이 모두 202인지 확인하는 회귀 테스트가 추가됐다 (`apps/api/tests/test_sources_router.py:1143-1178`). 전역 `lock table ... in share mode` 구문은 현재 마이그레이션에 남아 있지 않다.

## delta 시나리오 대조

| Requirement / Scenario | 결과 | 최종 근거 |
| --- | --- | --- |
| Owner-only raw source permanent deletion / Owner deletes raw source | 충족 | 삭제 RPC는 원문별 advisory lock과 대상 행 잠금을 얻은 뒤 참조를 검사하고, 정리 잡 삽입과 원문 삭제를 같은 트랜잭션에서 수행한다 (`0021_source_deletion_integrity.sql:285-379`). 미참조 원문의 202와 Storage 정리 잡 생성은 통합 테스트로 확인되며 (`apps/api/tests/test_sources_router.py:623-642,1097-1140`), 서로 다른 두 원문의 동시 삭제도 모두 202로 끝난다 (`apps/api/tests/test_sources_router.py:1143-1178`). |
| Owner-only raw source permanent deletion / Storage cleanup is retried | 충족 | Storage DELETE는 404를 멱등 성공으로 처리하고 다른 오류를 전파한다. 큐는 전파된 일시 오류를 `fail_job`으로 재예약하며 성공 또는 404 이전에는 `complete_job`을 호출하지 않는다 (`apps/worker/src/worker/storage.py:58-63`, `apps/worker/src/worker/queue.py:266-283`). |
| Owner-only raw source permanent deletion / Owner requests deletion of a referenced raw source | 충족 | 위키·공개본·Ask·활성 잡 순차 참조는 모두 `NW409` 전에 보존되고 (`0021_source_deletion_integrity.sql:302-348`, `apps/api/tests/test_sources_router.py:707-744,990-1094`), writer-first 경쟁에서도 삭제가 기다린 뒤 409 `source_in_use`를 반환한다 (`apps/api/tests/test_sources_router.py:747-843`). delete-first에서는 대기하던 writer가 23503으로 실패해 끊어진 참조가 저장되지 않는다 (`apps/api/tests/test_sources_router.py:846-987`). |
| Owner-only raw source permanent deletion / Non-owner member attempts to delete raw source | 충족 | owner 역할 검사는 advisory lock보다 먼저 실행되며, 비소유자는 데이터 변경 없이 42501에서 고정 본문의 403으로 매핑된다 (`0021_source_deletion_integrity.sql:285-289`, `apps/api/tests/test_sources_router.py:665-689`). |
| Owner-only raw source permanent deletion / Deleting non-existent or foreign workspace source | 충족 | owner 확인 이후에도 `(id, workspace_id)` 원문 행을 찾지 못하면 동일한 42501을 반환하므로 존재 여부를 구분하지 않는다 (`0021_source_deletion_integrity.sql:289-300`, `apps/api/tests/test_sources_router.py:645-662,692-704`). |
| Citation click integrates with the viewer / Member clicks a wiki citation marker | 충족 | workspace-scoped wiki 조회 후 같은 Ask 화면의 wiki 탭으로 전환하는 경로가 유지됐다 (`apps/dashboard/components/AskConversation.tsx:457-474`, `apps/dashboard/tests/AskConversation.test.tsx:344-374`). |
| Citation click integrates with the viewer / Member clicks a source citation marker | 충족 | source 마커는 `chunkId`와 `tab=source`로 라우팅되고 `SourceChunkView`의 ready 상태가 원문과 좌표를 표시한다 (`apps/dashboard/components/AskConversation.tsx:477`, `apps/dashboard/components/ContentViewer.tsx:334-398`). |
| Citation click integrates with the viewer / Member clicks an unavailable wiki citation marker | 충족 | wiki 조회 실패는 `missingCitation=wiki`로 전환되고 콘텐츠 뷰어의 명시적 unavailable 상태에서 끝난다 (`apps/dashboard/components/AskConversation.tsx:461-473`, `apps/dashboard/components/ContentViewer.tsx:203-283`). |
| Citation click integrates with the viewer / Member clicks an unavailable source citation marker | 충족 | source chunk 오류·0행은 `unavailable` 상태로 전환되어 무한 로딩 없이 안내를 표시한다 (`apps/dashboard/components/ContentViewer.tsx:334-375`). |

## 지적 사항

없음.

## 검증 증적

- 리뷰어 재실행: writer-first, delete-first, 서로 다른 파일 원문 동시 삭제 테스트 3개 통과
- 리뷰어 재실행: `openspec validate --specs --strict` — 34개 spec 통과
- 리뷰어 재실행: `git diff --check` — 통과
- 전체 구현 검증 기록: Python 테스트 491개, dashboard 테스트 356개, typecheck, lint, Ruff, DB lint, strict OpenSpec validation 통과

2라운드에서 남았던 반대 잠금 순서의 끊어진 참조와 전역 잠금의 동시 삭제 deadlock이 모두 원문별 공통 잠금 규약과 양방향 회귀 테스트로 해소됐다. delta spec의 9개 시나리오에 미충족 항목이 없으므로 마지막 라운드의 최종 판정을 `pass`로 확정한다.
