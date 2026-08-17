# 🤝 Handoff Document

- **작성 일시**: 2026-08-17T17:04 KST
- **브랜치**: `feat/public-sharing`
- **마지막 상태**: Phase 5: 공개 공유 (PUB-01 ~ PUB-03) 100% 완료 / v2 마일스톤 2 전 Phase 구현 완료

## 🎯 1. 현재 상태

마일스톤 2의 **Phase 5: 공개 위키 공유 화면 및 사이드카 구현**이 완료되었으며, OpenSpec change `public-sharing` 제안·구현·스펙 동기화·아카이브가 완료되었습니다.

### Phase 5 구현 완료 내역

| ID | 카테고리 | 제목 | 핵심 내용 |
| --- | --- | --- | --- |
| `PUB-01` | DB Migration | 사이드카 테이블 DDL | `0016_public_sharing.sql` `workspace_public_settings`, `wiki_page_publications`, 킬스위치 RLS 정책, `enforce_publication_verified` 트리거, anon GRANT |
| `PUB-02` | Public Route | 공개 위키 라우트 | `/p/[slug]/[page]` 비로그인(anon) 사용자용 읽기 전용 뷰어, 킬스위치 OFF 시 404 차단, 승인된 인용 스니펫 목록 렌더링 |
| `PUB-03` | Settings | 공개 공유 킬스위치 설정 | `PublicSharingSettings.tsx` 마스터 킬스위치(ON/OFF) 토글, 공개 표시명/설명 수정, owner RBAC 게이트, `WorkspaceGeneralSettings` 연동 |

### 검증 상태

- **OpenSpec**:
  - `public-sharing` → spec sync & archive (`2026-08-17-public-sharing`)
  - Main Spec: `openspec/specs/public-sharing/spec.md` 동기화 완료
- **TypeScript**: `pnpm typecheck` 통과 (`tsc --noEmit`)
- **Unit Tests**: `pnpm test` (Vitest 44개 파일, 157개 테스트 전원 통과)
- **Lint**: `pnpm lint` (ESLint 0 errors)
- **Build**: `pnpm build` (Next.js 15 production build 성공, `/p/[slug]/[page]` 라우트 포함)

## 🏆 v2 마일스톤 2 전체 완료 현황

- **Phase 1: 홈 대시보드 (`HOME-01` ~ `HOME-06`)** ✅ (PR #26 머지 완료)
- **Phase 2: 워크스페이스 설정 & 멤버 관리 (`SETTINGS-01` ~ `SETTINGS-04`)** ✅ (PR #28 머지 완료)
- **Phase 3: 소스 관리 & 위키 뷰어 (`SRC-01` ~ `SRC-03`, `WIKI-01` ~ `WIKI-03`)** ✅ (PR #30 머지 완료)
- **Phase 4: 백로그 & 질문 응답 (`BACKLOG-01`, `BACKLOG-02`, `ASK-01`, `ASK-02`)** ✅ (PR #32 머지 완료)
- **Phase 5: 공개 공유 (`PUB-01` ~ `PUB-03`)** ✅ (PR 생성 대기)
