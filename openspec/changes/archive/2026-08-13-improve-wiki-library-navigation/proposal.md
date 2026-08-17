## Why

현재 위키 목록은 제목만 나열해 문서의 주제와 검증 상태를 비교하거나 원하는 문서를 빠르게 찾기 어렵다. 위키 상세도 긴 본문을 읽기 전에 문서 상태와 연결 문서를 파악할 수 있는 탐색 구조가 필요하다.

## What Changes

- 위키 목록을 문서 수, 텍스트 검색, 카테고리 필터, 문서별 카테고리·검증 상태·본문 미리보기를 갖춘 탐색 가능한 라이브러리로 바꾼다.
- 위키 상세에 breadcrumb, 문서 메타데이터, 상태 영역, 본문 목차, 관련 문서 탐색을 추가한다.
- 좁은 화면에서도 목록의 필터와 상세의 목차·메타데이터가 접근 가능하고 읽기 흐름을 방해하지 않게 만든다.

## Capabilities

### New Capabilities

- `wiki-library-navigation`: 워크스페이스 위키 목록의 탐색·필터링과 위키 상세의 문서 맥락·연결 탐색 계약

### Modified Capabilities

- 없음.

## Impact

- 영향 코드: `apps/dashboard/app/w/[workspaceId]/wiki/page.tsx`, `apps/dashboard/app/w/[workspaceId]/wiki/[slug]/page.tsx`, `apps/dashboard/components/WikiPageContent.tsx`, 새 목록·상세 UI 컴포넌트와 테스트
- API·DB 스키마 변경 없음. 기존 RLS 기반 Supabase 조회와 위키 링크 데이터를 재사용한다.
