## Context

대시보드 전반의 품질 및 인터랙션 고도화 작업입니다. (자세한 동기는 proposal.md 참조)

## Goals / Non-Goals

**Goals:**
- 워크스페이스 유형(personal/team) 전환 시 Supabase 클라이언트에서 잔여 멤버 수를 확인하고 안전하게 차단/저장
- Next.js App Router의 `router.refresh()`를 통해 워크스페이스 유형 변경을 LNB와 전체 레이아웃에 실시간 반영
- `AskConversation`에서 URL 쿼리 파라미터(`q`)를 감지하여 1회 자동 실행(`autoSubmittedRef`)함으로써 홈 대시보드 질문 입력과의 원활한 연동 보장
- 마크다운 본문 파싱 시 정규식을 통해 본문 끝 중복 `## 관련 문서` 텍스트를 제거하고, 전용 2열 카드 그리드 UI로 일원화

**Non-Goals:**
- DB 스키마 마이그레이션(기존 `workspaces.kind` 및 `workspace_members` 테이블 구조 유지)
- 백엔드 SSE 프로토콜 자체의 변경

## Decisions

### 1. 팀 -> 개인 전환 시 멤버 수 사전 검증
- **결정**: `WorkspaceGeneralSettings`의 `handleSubmit`에서 `kind === "personal"`로 저장 시도 시 `workspace_members`의 카운트를 조회하여 본인 외 멤버(`count > 1`)가 있으면 에러 메시지와 함께 저장을 차단한다.
- **대안**: DB RLS 또는 트리거에서 에러 발생시키기 -> 프론트엔드에서 명확하고 친절한 한국어 안내 문구를 즉시 제공하기 위해 UI 레벨에서 사전 검증 수행.

### 2. URL 쿼리 파라미터 기반 질문 자동 실행
- **결정**: `AskConversation`에서 `useSearchParams()`의 `q` 값을 `autoSubmittedRef` 플래그로 1회 안전하게 트리거한다.
- **대안**: 로컬스토리지 또는 글로벌 상태 공유 -> URL 기반 딥링크 지원 및 뒤로가기/새로고침 호환성을 위해 표준 SearchParams 채택.

### 3. 마크다운 본문 중복 '관련 문서' 정제
- **결정**: `cleanWikiContent` 함수를 두어 본문 끝에 위치한 `## 관련 문서` 섹션을 제거한 뒤 `extractHeadings` 및 `DocumentBody`에 전달한다.
- **대안**: 컴파일러 프롬프트만 수정 -> 기존에 이미 DB에 저장되어 컴파일 완료된 기존 문서들에도 즉시 깨끗하게 적용되도록 뷰어 렌더링 단계에서 필터링.

## Risks / Trade-offs

- [Risk] `router.refresh()` 호출 시 서버 컴포넌트 재조회 비용 → Mitigation: 가벼운 메타데이터 쿼리이므로 성능 영향 미미.
