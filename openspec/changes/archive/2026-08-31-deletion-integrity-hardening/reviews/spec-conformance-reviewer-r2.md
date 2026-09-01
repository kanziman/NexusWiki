# Spec Conformance 리뷰 — deletion-integrity-hardening r2

## 판정

**pass**

## 검토 범위

- r1 이후 변경된 `delete_raw_source`의 참조 검사 원자성
- tenant isolation r1에서 지적한 동시 참조 writer 경쟁 조건의 해소 여부
- `source-management-wiki`와 `unified-workspace-viewer` delta spec의 전체 시나리오 회귀 여부

## r1 이후 수정 사항 확인

tenant isolation r1에서 지적한 경쟁 조건은 해소됐다. `delete_raw_source`는 대상 원문 행을 `for update`로 잠근 뒤, JSONB 참조와 활성 파이프라인 잡을 보유한 `wiki_pages`, `wiki_page_publications`, `ask_messages`, `jobs` 테이블을 모두 `share` 모드로 잠근다. 이 잠금은 참조 writer의 `row exclusive` 잠금과 충돌하므로, 먼저 시작한 writer가 있으면 커밋을 기다린 후 참조 검사를 실행한다. 참조가 발견되면 Storage 정리 잡 생성과 원문 삭제 이전에 `NW409`를 발생시킨다 (`supabase/migrations/0021_source_deletion_integrity.sql:86-104,108-175`).

추가된 회귀 테스트는 editor가 `wiki_pages.sources` 참조를 삽입한 트랜잭션을 열린 상태로 유지한 뒤 owner의 삭제 요청을 실행한다. 삭제 요청은 writer가 커밋될 때까지 대기하고, 이후 409 `source_in_use`로 끝나는 것을 확인한다 (`apps/api/tests/test_sources_router.py:747-843`). 리뷰 과정에서 이 테스트를 다시 실행했으며 1개 테스트가 통과했다.

## delta 시나리오 대조

| Requirement / Scenario | 결과 | r2 근거 |
| --- | --- | --- |
| Owner-only raw source permanent deletion / Owner deletes raw source | 충족 | 참조 테이블 잠금 이후 검사·정리 잡 삽입·원문 삭제가 같은 RPC 트랜잭션에서 실행되므로, 참조가 없는 삭제의 판정과 데이터 변경 사이에 먼저 시작된 writer가 끼어들 수 없다 (`0021_source_deletion_integrity.sql:97-104,108-175`). 기존 202·cascade·정리 잡 계약에는 변경이 없다. |
| Owner-only raw source permanent deletion / Storage cleanup is retried | 충족 | worker의 404 멱등 성공, 일시 오류 전파, 큐의 `fail_job` 재시도 경로는 변경되지 않았다 (`apps/worker/src/worker/storage.py:58-63`, `apps/worker/src/worker/queue.py:266-283`). |
| Owner-only raw source permanent deletion / Owner requests deletion of a referenced raw source | 충족 | 네 참조 테이블을 잠근 뒤 위키·공개본·Ask·활성 잡을 검사하고 `NW409`를 발생시킨다 (`0021_source_deletion_integrity.sql:97-152`). 순차 참조 네 경로와 실제 동시 wiki writer 경로가 모두 409로 검증된다 (`apps/api/tests/test_sources_router.py:707-843,846-950`). |
| Owner-only raw source permanent deletion / Non-owner member attempts to delete raw source | 충족 | owner 검사는 참조 테이블 잠금보다 먼저 실행되며, 비소유자는 데이터 변경 없이 42501 → 403으로 끝난다 (`0021_source_deletion_integrity.sql:82-95`, `apps/api/tests/test_sources_router.py:665-689`). |
| Owner-only raw source permanent deletion / Deleting non-existent or foreign workspace source | 충족 | `(id, workspace_id)` 원문을 잠그지 못하면 참조 테이블 잠금 전에 동일한 42501을 반환하므로 존재 여부를 노출하지 않는다 (`0021_source_deletion_integrity.sql:86-95`, `apps/api/tests/test_sources_router.py:645-662,692-704`). |
| Citation click integrates with the viewer / Member clicks a wiki citation marker | 충족 | Ask의 workspace-scoped wiki 조회와 같은 화면의 wiki 탭 라우팅은 변경되지 않았다 (`apps/dashboard/components/AskConversation.tsx:457-474`). |
| Citation click integrates with the viewer / Member clicks a source citation marker | 충족 | source 마커의 `chunkId`·`tab=source` 라우팅과 `SourceChunkView` ready 상태는 변경되지 않았다 (`apps/dashboard/components/AskConversation.tsx:477`, `apps/dashboard/components/ContentViewer.tsx:334-398`). |
| Citation click integrates with the viewer / Member clicks an unavailable wiki citation marker | 충족 | 조회 실패 시 `missingCitation=wiki`로 이동하고 명시적 unavailable 상태를 표시하는 경로는 유지됐다 (`apps/dashboard/components/AskConversation.tsx:461-473`, `apps/dashboard/components/ContentViewer.tsx:203-283`). |
| Citation click integrates with the viewer / Member clicks an unavailable source citation marker | 충족 | source chunk 조회의 오류·0행은 로딩이 아니라 unavailable 상태로 종료된다 (`apps/dashboard/components/ContentViewer.tsx:334-375`). |

## 지적 사항

없음.

## 검증 증적

- 리뷰어 재실행: `uv run pytest apps/api/tests/test_sources_router.py::test_delete_waits_for_a_concurrent_reference_writer_then_returns_409 -q -rs` — 1개 통과
- 전체 구현 검증 기록: Python 테스트 489개 통과, dashboard 테스트 356개 통과
- `git diff --check`: 통과

tenant isolation r1이 제시한 “참조 검사 직후 writer가 커밋하고 삭제가 202로 끝나는” 위반 시나리오는 잠금 순서와 동시성 회귀 테스트로 닫혔다. 나머지 delta spec 시나리오에도 회귀가 없어 최종 판정을 `pass`로 확정한다.
