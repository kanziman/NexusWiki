# Proposal: public-sharing

## Why

검증 완료된 위키 문서를 외부 비로그인 사용자(`anon`)에게 안전하게 공개하고, 원문 소스 누출 없이 사람이 승인한 스니펫만 열람할 수 있도록 지원한다.
Phase 5에서는 다음을 완결한다:
1. 사이드카 스키마(`0016_public_sharing.sql`): `workspace_public_settings`(마스터 킬스위치), `wiki_page_publications`(승인 발행본) 및 anon/member RLS 정책, `enforce_publication_verified` 트리거 게이트.
2. 공개 위키 뷰어 라우트(`/p/[slug]/[page]`): 비로그인 사용자가 킬스위치가 켜진 워크스페이스의 승인된 공개 위키 문서를 열람하고, 이중 Citation 인용 스니펫을 안전하게 확인.
3. 공개 공유 설정 UI(`PublicSharingSettings.tsx`): 워크스페이스 소유자가 마스터 킬스위치(ON/OFF) 및 공개 워크스페이스 표시명을 제어.

## What Changes

1. **사이드카 DDL & RLS (`PUB-01`)**:
   - `supabase/migrations/0016_public_sharing.sql`: `workspace_public_settings`, `wiki_page_publications`, 트리거, GRANT, RLS 정책 정의
2. **공개 위키 라우트 (`PUB-02`)**:
   - `apps/dashboard/app/p/[slug]/[page]/page.tsx`: anon 접근 가능한 읽기 전용 뷰어, 킬스위치 OFF 시 404
3. **공개 공유 설정 UI (`PUB-03`)**:
   - `apps/dashboard/components/PublicSharingSettings.tsx`: 킬스위치 토글, 공개 표시명/설명 수정, owner RBAC 게이트
   - `WorkspaceGeneralSettings.tsx` / `SettingsMembersPanel.tsx` 연동

## Validation Plan

- 단위 테스트: `PublicSharingSettings.test.tsx`, `public-wiki-page-route.test.tsx`
- TypeScript typecheck, ESLint, Next.js build 전체 통과
- GitHub Issue #33 연결
