# 🤝 Handoff Document

- **작성 일시**: 2026-08-17T16:58 KST
- **브랜치**: `feat/backlog-ask`
- **마지막 상태**: Phase 4: 백로그 & 질문 응답 (BACKLOG-01, BACKLOG-02, ASK-01, ASK-02) 100% 완료

## 🎯 1. 현재 상태

마일스톤 2의 **Phase 4: 백로그 & 질문 응답 화면 구현**이 완료되었으며, OpenSpec change `backlog-ask` 제안·구현·스펙 동기화·아카이브가 완료되었습니다.

### Phase 4 구현 완료 내역

| ID | 카테고리 | 제목 | 핵심 내용 |
| --- | --- | --- | --- |
| `BACKLOG-01` | Backlog | 레드링크 백로그 화면 | `BacklogList.tsx`, `backlog/page.tsx` 미해결 레드링크 주제별 집계, 상단 통계(미해결 백로그 주제 수, 영향받는 위키 문서 수), 인용 문서 칩 |
| `BACKLOG-02` | Backlog | 백로그 정렬 & 소스 보강 | 인용 빈도(`impact`) 내림차순 정렬, 검색 필터, `[소스 추가]` CTA (`prefillTitle` & `tab=text` 연동) |
| `ASK-01` | Ask | Ask SSE 스트리밍 응답 바인딩 | `AskConversation.tsx` SSE 스트림(`meta` -> `delta*` -> `citations` -> `done`), 프롬프트 템플릿 로드, 에러 복구 |
| `ASK-02` | Ask | 인용 마커 & 원문 대조 | `CitationMarker.tsx`, `ContentViewer.tsx` 실시간 앵커 파싱, 승격 및 원문 서랍 연동 |

### 검증 상태

- **OpenSpec**:
  - `backlog-ask` → spec sync & archive (`2026-08-17-backlog-ask`)
  - Main Spec: `openspec/specs/backlog-ask/spec.md` 동기화 완료
- **TypeScript**: `pnpm typecheck` 통과 (`tsc --noEmit`)
- **Unit Tests**: `pnpm test` (Vitest 42개 파일, 152개 테스트 전원 통과)
- **Lint**: `pnpm lint` (ESLint 0 errors)
- **Build**: `pnpm build` (Next.js 15 production build 성공, `/w/[workspaceId]/backlog` 라우트 포함)

## 📋 2. 다음 구현 순서 (Phase 5: 공개 공유)

1. **`PUB-01`**: 사이드카 테이블 DDL (`workspace_public_settings` + `wiki_page_publications`) 및 anon RLS 정책
2. **`PUB-02`**: `/p/[slug]/[page]` 공개 위키 뷰어 라우트
3. **`PUB-03`**: 공개 공유 킬스위치 설정 UI (`PublicSharingSettings.tsx`)
