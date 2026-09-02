## 1. 백엔드 삭제 엔드포인트 및 테스트

- [x] 1.1 `apps/api/src/api/routers/wiki.py`에 `DELETE /workspaces/{workspace_id}/wiki/{wiki_id}` 엔드포인트 구현
- [x] 1.2 `apps/api/tests/test_wiki_publication.py`에 소유자 삭제 성공 및 에디터/뷰어 403 차단 테스트 추가

## 2. 프론트엔드 UI 연동

- [x] 2.1 `apps/dashboard/lib/wiki-publication.ts`에 `deleteWikiPage` 클라이언트 함수 추가
- [x] 2.2 `apps/dashboard/components/WikiPageContent.tsx`에 소유자 전용 [위키 삭제] 버튼 및 삭제 확인 모달 연동
- [x] 2.3 `apps/dashboard/app/w/[workspaceId]/wiki/[slug]/page.tsx` 및 `WikiLibrary.tsx`에 `isOwner` 역할 조회/전달
- [x] 2.4 `apps/dashboard/tests/WikiDeletion.test.tsx` 단위/컴포넌트 테스트 작성

## 3. 검증 및 스펙 아카이브

- [x] 3.1 `openspec validate individual-wiki-deletion --strict` 검증 및 spec 동기화 후 아카이브
