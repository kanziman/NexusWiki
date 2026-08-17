## Why

한글이 포함된 위키 슬러그는 인증된 사용자가 정상 URL로 접근해도 상세 페이지에서 찾을 수 없는 것으로 표시된다. 업로드한 한글 제목이 생성하는 위키 페이지까지 접근 불가하게 만들며, 계획된 다중 파일 업로드의 선행 결함이기도 하다.

## What Changes

- 위키 상세 라우트가 percent-encoded 및 이미 디코드된 슬러그를 모두 동일한 저장 슬러그로 조회하도록 한다.
- 잘못된 percent encoding은 서버 오류 없이 기존의 안전한 "페이지를 찾을 수 없습니다" 상태로 처리한다.
- ASCII, 한글, 혼합 슬러그 및 잘못된 인코딩에 대한 회귀 검증을 추가한다.

## Capabilities

### New Capabilities

- `wiki-page-routing`: 인증된 워크스페이스 멤버가 URL 슬러그 형식과 무관하게 자신이 접근 가능한 위키 상세 페이지를 안전하게 조회하는 동작을 정의한다.

### Modified Capabilities

- 없음.

## Impact

- 영향 코드: `apps/dashboard/app/w/[workspaceId]/wiki/[slug]/page.tsx` 및 해당 라우트 테스트.
- API, 데이터베이스 스키마, RLS 정책 및 저장된 슬러그 형식은 변경하지 않는다.
