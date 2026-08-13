## Context

`SourcesList.tsx`는 목록과 상세를 한 컴포넌트 안에서 `selectedId` state로 토글하는 아코디언이다 (`libraryHref="#sources-library"`라는 in-page anchor를 쓰는 것도 이 때문 — 실제 라우트가 없어서 임시로 anchor를 씀). 반대로 `WikiLibrary.tsx`는 이미 각 행이 `Link`로 `/wiki/[slug]` 실제 라우트로 이동하고, 그 라우트(`wiki/[slug]/page.tsx` → `WikiPageContent.tsx`)의 `DetailHeader`가 `libraryHref`로 실제 `/wiki` 목록을 가리킨다. See proposal.md - Why.

## Goals / Non-Goals

**Goals:**
- Sources 쪽을 Wiki 쪽과 같은 "행 → 실제 라우트 → DetailHeader의 실제 return 링크" 패턴으로 맞춘다.

**Non-Goals:**
- 리사이즈 가능한 split-pane, 새 의존성 추가 — 스펙이 요구하는 건 "같은 전환 방식"이지 특정 UI 패턴(패널 vs 라우트)이 아니다. Wiki 쪽이 이미 라우트 기반이고 `WikiPageContent`가 검증 배너·TOC·관련 문서까지 포함하는 긴 문서라 패널에 욱여넣는 것보다 Sources를 Wiki 패턴에 맞추는 쪽이 안전하다. (Ask↔Wiki 통합 스플릿 뷰는 별도 change(Change C)에서 다룬다 — 그건 이 스펙이 요구하는 것과 무관한, 사용자가 별도로 원한 상위 기능이다.)
- Dropzone/JobStepper 이동 — ingestion UI는 목록 페이지에 남는다.

## Decisions

- **새 라우트 `sources/[id]/page.tsx`를 Server Component로**: `wiki/[slug]/page.tsx`와 동일한 패턴(Supabase server client로 단일 행 조회, RLS가 워크스페이스 격리를 이미 강제) — 새 접근 제어 로직을 만들지 않는다.
- **`SourcesList.tsx`의 아코디언 관련 state(`selectedId`) 전체 제거**: 더 이상 인라인 확장이 없으므로 필요 없다. "상세 보기" 버튼은 `next/link`의 `Link`로 교체 — `WikiLibrary.tsx`가 이미 쓰는 것과 동일한 컴포넌트.
- **상세 콘텐츠(`유형`/`등록일` `<dl>`)를 그대로 새 라우트로 이동**: 새로 디자인하지 않는다 — 이번 change의 스코프는 "전환 방식 통일"이지 상세 콘텐츠 리치화가 아니다.

## Risks / Trade-offs

- [Risk] 상세 보기가 아코디언(같은 스크롤 위치 유지)에서 라우트 이동(스크롤 리셋, 새 페이지 로드)으로 바뀌어 체감 속도가 달라질 수 있음 → Mitigation: Server Component라 페이로드가 작고(단일 행), Next.js prefetch가 `Link`에 기본 적용된다.
