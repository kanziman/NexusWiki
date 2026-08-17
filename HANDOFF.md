# 🤝 Handoff Document

- **작성 일시**: 2026-08-17T16:51 KST
- **브랜치**: `feat/source-management-wiki`
- **마지막 상태**: Phase 3: 소스 관리 & 위키 뷰어 (SRC-01 ~ SRC-03, WIKI-01 ~ WIKI-03) 100% 완료

## 🎯 1. 현재 상태

마일스톤 2의 **Phase 3: 소스 관리 & 위키 뷰어 화면 구현**이 완료되었으며, OpenSpec change `source-management-wiki` 제안·구현·스펙 동기화·아카이브가 완료되었습니다.

### Phase 3 구현 완료 내역

| ID | 카테고리 | 제목 | 핵심 내용 |
| --- | --- | --- | --- |
| `SRC-01` | Source Upload | 소스 드롭존 컴포넌트 | `Dropzone.tsx` 3종 포맷(PDF/MD/TXT, 최대 20MiB) 파일·텍스트·URL 업로드 및 202 응답 UX |
| `SRC-02` | Source Pipeline | 잡 상태 스테퍼 | `JobStepper.tsx` 5단계 파이프라인(parse, compile, link_sync, embed, conflict_check) 상태 실시간 추적 |
| `SRC-03` | Source List | 소스 목록 & MIME 필터 | `SourcesList.tsx` 3종 MIME 필터 탭(전체, PDF, 텍스트/마크다운) 및 `sources/page.tsx` 쿼리 연동 |
| `WIKI-01` | Wiki Viewer | 읽기 전용 위키 뷰어 | `WikiPageContent.tsx` 읽기 전용 배너, 검증/충돌 상태 콜아웃, 마크다운 렌더링 |
| `WIKI-02` | Wiki Navigation | WikiLink 상호 참조 & 레드링크 | `resolveWikiLinks`, `RedLinkCta.tsx` 클릭 이동 및 미해결 링크 소스 생성 유도 |
| `WIKI-03` | Wiki Citation | 이중 Citation & 원문 역추적 | `CitationMarker.tsx`, `CitationSidePanel.tsx`, `ContentViewer.tsx` 원문 청크 대조 서랍 연동 |

### 검증 상태

- **OpenSpec**:
  - `source-management-wiki` → spec sync & archive (`2026-08-17-source-management-wiki`)
  - Main Spec: `openspec/specs/source-management-wiki/spec.md` 동기화 완료
- **TypeScript**: `pnpm typecheck` 통과 (`tsc --noEmit`)
- **Unit Tests**: `pnpm test` (Vitest 41개 파일, 149개 테스트 전원 통과)
- **Lint**: `pnpm lint` (ESLint 0 errors)
- **Build**: `pnpm build` (Next.js 15 production build 성공)

## 📋 2. 다음 구현 순서 (Phase 4: 백로그 & 질문 응답)

1. **`BACKLOG-01`**: 레드링크 백로그 화면 (`apps/dashboard/app/w/[workspaceId]/backlog/page.tsx`, `BacklogList.tsx`)
2. **`BACKLOG-02`**: 백로그 정렬 & 필터 (참조 수 내림차순, 소스 보강 유도)
3. **`ASK-01`**: Ask SSE 스트리밍 응답 바인딩 (`AskConversation.tsx`)
4. **`ASK-02`**: 실시간 인용 마커 렌더링 & 원문 대조
