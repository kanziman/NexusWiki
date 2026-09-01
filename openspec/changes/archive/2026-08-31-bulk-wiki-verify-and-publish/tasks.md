## 1. 백엔드 API 구현

- [x] 1.1 `apps/api/src/api/routers/wiki.py`에 `POST /workspaces/{workspace_id}/wiki/bulk-verify` 엔드포인트 구현
- [x] 1.2 `apps/api/src/api/routers/wiki.py`에 `POST /workspaces/{workspace_id}/wiki/bulk-publish` 엔드포인트 구현
- [x] 1.3 `apps/api/tests/test_wiki_publication.py`에 일괄 검증 및 일괄 발행 백엔드 테스트 추가

## 2. 프론트엔드 UI 연동

- [x] 2.1 `apps/dashboard/lib/wiki-publication.ts`에 `bulkVerifyWikiPages` 및 `bulkPublishWikiPages` 클라이언트 함수 추가
- [x] 2.2 `apps/dashboard/components/WikiLibrary.tsx`에 다중 선택 체크박스, 선택 상태 관리, 일괄 검증/발행 툴바 액션 UI 추가
- [x] 2.3 `apps/dashboard/app/w/[workspaceId]/wiki/page.tsx`에서 사용자 역할(`canVerify`) 조회 후 `WikiLibrary`로 전달
- [x] 2.4 프론트엔드 컴포넌트 테스트 추가 및 검증 (`pnpm test`, `pnpm lint`)

## 3. 검증 및 스펙 아카이브

- [x] 3.1 `openspec validate bulk-wiki-verify-and-publish --strict` 검증 및 delta spec 반영 후 아카이브
