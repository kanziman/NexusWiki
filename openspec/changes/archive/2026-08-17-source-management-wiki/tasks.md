## 1. 소스 관리 및 MIME 타입 필터링 구현 (SRC-01, SRC-02, SRC-03)

- [x] 1.1 `apps/dashboard/components/SourcesList.tsx`에 3종 MIME 필터 탭(`전체`, `PDF`, `텍스트/마크다운`) 추가 및 필터링 구현
- [x] 1.2 `apps/dashboard/app/w/[workspaceId]/sources/page.tsx` 쿼리에 `mime_type` 컬럼 추가

## 2. 위키 문서 뷰어 & WikiLink/Citation 연동 확인 (WIKI-01, WIKI-02, WIKI-03)

- [x] 2.1 `WikiPageContent.tsx`, `WikiLibrary.tsx`, `ContentViewer.tsx` v2 디자인 시스템 스타일링 및 인터랙션 점검
- [x] 2.2 단위 테스트 작성 및 TypeScript, Vitest, ESLint, Next.js build 전체 검증
