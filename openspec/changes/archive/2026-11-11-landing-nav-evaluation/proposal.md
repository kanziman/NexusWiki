## Why

공개 평가 페이지(`/showcase/evaluation`)는 랜딩 평가 소개 섹션의 카드로만 닿을 수 있다. 방문자가 스크롤하지 않고도 상단 메뉴에서 평가 기록으로 바로 갈 수 있어야 제품의 검증 근거가 첫 화면에서 드러난다.

## What Changes

- 공개 랜딩 상단 메뉴(데스크톱 · 모바일)의 `FAQ` 오른쪽에 「평가 기록」 링크를 추가한다. 대상은 `/showcase/evaluation`이다.
- 이 링크만 섹션 앵커가 아니라 페이지 이동이며, 랜딩을 열었다는 이유만으로 대상 페이지를 미리 가져오지 않는다.
- GitHub 이슈와 `/plan-feature` 게이트는 사용자 결정으로 생략한 약식 change다.

## Capabilities

### New Capabilities

(없음)

### Modified Capabilities

- `public-marketing-landing`: 「반응형 공개 랜딩 탐색과 전환」 요구사항에 상단 메뉴의 평가 기록 링크를 추가한다.

## Impact

- `apps/dashboard/components/public-landing/PublicLandingHeader.tsx`
- `apps/dashboard/tests/PublicLandingPage.test.tsx`
- API · DB · 인증 경로 변경 없음
