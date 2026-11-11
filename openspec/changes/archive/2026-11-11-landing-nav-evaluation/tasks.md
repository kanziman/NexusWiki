## 0. 추적

약식 change다. GitHub 이슈와 `/plan-feature` 게이트는 사용자 결정으로 생략했다. 작업 브랜치는 `feat/landing-nav-evaluation`이다.

## 1. 상단 메뉴에 평가 기록 링크를 추가한다

- [x] 1.1 `PublicLandingHeader`의 데스크톱·모바일 메뉴에서 `FAQ` 다음에 `/showcase/evaluation`으로 가는 「평가 기록」 `Link`(`prefetch={false}`, 섹션 링크와 같은 포커스·호버 스타일)를 추가한다. 모바일 링크는 선택 시 메뉴를 닫는다. 랜딩 테스트에 두 메뉴의 링크 대상과 모바일 닫힘을 추가한다.

AC:
Given: 미인증 방문자가 공개 랜딩을 연다.
When: 데스크톱 상단 메뉴를 보거나, 모바일 메뉴를 열고 「평가 기록」을 선택한다.
Then: 두 메뉴 모두 「FAQ」 다음에 「평가 기록」 링크가 있고 `href`는 `/showcase/evaluation`이며, 모바일 메뉴는 선택 후 닫힌다(`aria-expanded="false"`).

검증:
`cd apps/dashboard && npx vitest run tests/PublicLandingPage.test.tsx && npx tsc --noEmit && npx eslint components/public-landing/PublicLandingHeader.tsx tests/PublicLandingPage.test.tsx`
