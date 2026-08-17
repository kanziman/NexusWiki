# Proposal: source-management-wiki

## Why

NexusWiki의 핵심 가치는 원문 소스를 수집하여 위키 문서를 컴파일하고, 위키 문서를 읽으며 언제든 원문 출처를 역추적(이중 Citation)할 수 있도록 하는 것이다.
Phase 3에서는 다음을 완결한다:
1. 소스 관리 화면(`/w/[workspaceId]/sources`): PDF/MD/TXT 3종 포맷 업로드, 잡 상태 실시간 모니터링, MIME 타입 기반 3종 필터 탭(`전체`, `PDF`, `텍스트/마크다운`).
2. 위키 리더 화면(`/w/[workspaceId]/wiki/[slug]` 및 `/ask`): 읽기 전용 위키 마크다운 렌더링, 검증 상태 뱃지, `[[WikiLink]]` 상호 연결 및 미해결 레드링크 CTA, 이중 Citation 인라인 칩 및 원문 대조 서랍.

## What Changes

1. **소스 드롭존 & 파이프라인 스테퍼 (`SRC-01`, `SRC-02`)**:
   - `Dropzone.tsx`: 3종 포맷(PDF/MD/TXT, 최대 20MiB) 파일/텍스트/URL 업로드
   - `JobStepper.tsx`: 5단계 파이프라인 진행 상태 실시간 표시 및 실패 잡 재시도 안내
2. **소스 목록 & MIME 필터 탭 (`SRC-03`)**:
   - `SourcesList.tsx`: 3종 MIME 필터 탭(`전체`, `PDF`, `텍스트/마크다운`) 제공 및 선택 시 목록 필터링
   - `sources/page.tsx`: `mime_type` 컬럼 선택 및 RLS 스코프 데이터 패칭
3. **읽기 전용 위키 문서 뷰어 & 검증 상태 (`WIKI-01`)**:
   - `WikiPageContent.tsx`: 읽기 전용 배너, 검증/충돌 상태 콜아웃, 마크다운 렌더링
   - `wiki/[slug]/page.tsx`: 존재 확인 및 통합 뷰어 라우팅
4. **WikiLink 상호 연결 & 레드링크 CTA (`WIKI-02`)**:
   - `resolveWikiLinks`, `RedLinkCta`: `[[WikiLink]]` 파싱, 해소된 링크 페이지 이동 및 미해결 링크 백로그 생성 유도
5. **이중 Citation 하이라이트 & 원문 역추적 (`WIKI-03`)**:
   - `CitationMarker.tsx`, `CitationSidePanel.tsx`, `ContentViewer.tsx`: `[[wiki:wN]]`, `[[src:sN]]` 앵커 파싱, 원문 청크 대조 패널

## Validation Plan

- 단위 테스트: `SourcesList.test.tsx`, `Dropzone.test.tsx`, `JobStepper.test.tsx`, `WikiPageContent.test.tsx`, `ContentViewer.test.tsx`, `RedLinkCta.test.tsx`, `CitationMarker.test.tsx`
- TypeScript typecheck, ESLint, Next.js build 전체 통과
- GitHub Issue #29 연결
