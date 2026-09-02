# Proposal: 개별 위키 문서(Wiki Page) 영구 삭제 기능 지원

## Why

- 사용자가 잘못 생성되었거나 불필요한 위키 문서를 정리하고자 할 때, 현재 개별 위키 문서를 삭제하는 기능이 없어 데이터 관리에 불편함이 있다.
- RLS 정책(`wiki_pages_delete_owner`)과 외래키 CASCADE(청크, 임베딩, 공개 발행, 북마크)가 이미 DB 수준에서 설계되어 있으므로, 백엔드 삭제 엔드포인트와 프론트엔드 UI(상세 뷰어 및 라이브러리)를 연동하여 완전한 수명주기 관리를 완성한다.

## What Changes

1. **백엔드 API**:
   - `DELETE /workspaces/{workspace_id}/wiki/{wiki_id}` 엔드포인트 추가 (소유자 권한 전용, DB delete_one 실행).
   - 권한 없는 사용자(에디터/뷰어)는 403 Forbidden 반환.
2. **프론트엔드 대시보드**:
   - `apps/dashboard/lib/wiki-publication.ts`에 `deleteWikiPage` 클라이언트 함수 추가.
   - `apps/dashboard/components/WikiPageContent.tsx` 상단 액션 바에 소유자 전용 `[위키 삭제]` 버튼 및 영구 삭제 확인 모달 연동 (삭제 후 `/w/[workspaceId]/wiki`로 리다이렉트).
   - `apps/dashboard/components/WikiLibrary.tsx` 목록 항목에 소유자 전용 삭제 옵션/버튼 연동.
   - `apps/dashboard/app/w/[workspaceId]/wiki/[slug]/page.tsx` 및 `wiki/page.tsx`에서 `isOwner` 권한 전달.

## Capabilities

### New Capabilities
- `DELETE /workspaces/{workspace_id}/wiki/{wiki_id}`를 통한 개별 위키 문서의 안전한 영구 삭제 및 연관 데이터 자동 정리.
- 대시보드 위키 리더 및 목록 화면에서 소유자가 확인 모달을 통해 문서를 삭제할 수 있는 UI 표면 제공.

### Modified Capabilities
- `wiki-page-routing`: 위키 상세 리더 화면에 소유자 전용 삭제 액션 표면 추가.

## Impact

- `apps/api/src/api/routers/wiki.py`
- `apps/api/tests/test_wiki_publication.py`
- `apps/dashboard/app/w/[workspaceId]/wiki/[slug]/page.tsx`
- `apps/dashboard/components/WikiPageContent.tsx`
- `apps/dashboard/components/WikiLibrary.tsx`
- `apps/dashboard/lib/wiki-publication.ts`
- `apps/dashboard/tests/WikiDeletion.test.tsx`
