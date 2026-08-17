## 1. 사이드카 마이그레이션 DDL & RLS 정책 작성 (PUB-01)

- [x] 1.1 `supabase/migrations/0016_public_sharing.sql` 작성 (사이드카 테이블 2개, 트리거 3개, RLS 정책 및 GRANT)

## 2. 공개 위키 라우트 및 뷰어 컴포넌트 구현 (PUB-02)

- [x] 2.1 `apps/dashboard/app/p/[slug]/[page]/page.tsx` 공개 위키 뷰어 라우트 작성 (anon 클라이언트, 킬스위치 404)

## 3. 공개 공유 설정 UI 및 워크스페이스 설정 연동 (PUB-03)

- [x] 3.1 `apps/dashboard/components/PublicSharingSettings.tsx` 작성 (킬스위치 토글, 공개 표시명/설명, owner RBAC)
- [x] 3.2 `WorkspaceGeneralSettings.tsx` 및 `SettingsMembersPanel.tsx`에 연동
- [x] 3.3 단위 테스트 작성 및 TypeScript, Vitest, ESLint, Next.js build 전체 검증
