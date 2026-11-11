## 0. 추적

추적: umbrella https://github.com/kanziman/NexusWiki/issues/282. Gate 4 승인으로 작업 분해 확정. 하위 이슈: 1절 #283, 2절 #284, 3절 #285. GitHub sub-issue 연결 응답 확인 완료. 작업 브랜치는 `feat/landing-evaluation-intro`다.

## 1. 공개 위키 문서 헤더에서 공개 홈으로 돌아간다

이슈: https://github.com/kanziman/NexusWiki/issues/283

- [x] 1.1 공개 위키 뷰어 헤더의 브랜드 마크를 `/` 링크(접근 이름 「NexusWiki 홈」, `prefetch={false}`, 포커스 링)로 바꾸고, 라우트 테스트에 홈 링크 대상을 추가한다.

AC:
Given: 같은 워크스페이스에 공개 문서가 있다.
When: 방문자가 공개 문서를 열고 헤더 브랜드 마크를 선택한다.
Then: `/`로 이동하고, 링크는 접근 이름 「NexusWiki 홈」으로 식별되며, 페이지에 `/w/` 링크가 없고, 헤더 3열 셸이 그대로다.

검증:
`cd apps/dashboard && npx vitest run tests/public-wiki-page-route.test.tsx`

## 2. 랜딩 평가 소개에 대표 실험 판정과 평가 페이지 카드를 보인다

이슈: https://github.com/kanziman/NexusWiki/issues/284

- [x] 2.1 `featuredAdoption`(결정 기록 있는 첫 도입 실험, 기준·정책·결정 중 하나라도 없으면 없음)과 스냅샷 `synthetic` 노출, `PublicLandingEvaluation`(대표 실험 블록·합성 표기·결정·기준 충족 수·미충족 조건 실제값/허용값·상세 링크, 카드 3개, 대체 표시)을 만들고 랜딩의 기존 평가 섹션을 교체한다. 모든 링크는 `prefetch={false}`다.

AC:
Given: 커밋된 실험 스냅샷에 재검색 도입 실험과 미채택 결정, 원래 기준 6개가 있다.
When: 방문자가 공개 랜딩의 평가 소개 섹션을 본다.
Then: 「합성 시나리오 기준」, 「재검색 도입」, 「미채택」, 「원래 기준 6개 중 3개 충족」과 미충족 조건 3개의 실제값·허용값(예: 비용 +66.4% · 허용 +50%)이 스냅샷 값 그대로 보이고, 상세 링크는 `/showcase/evidence-research`다. 카드 3개는 `/showcase/evaluation`·`/showcase/controlled-ai`·`/showcase/regression`으로 연결된다. 기준 세트 참조를 지운 가짜 스냅샷에서는 판정·수치가 사라지고 소개 문구와 링크, 카드만 남는다. 합성이 아닌 가짜 스냅샷에서는 합성 표기가 없다.

검증:
`cd apps/dashboard && npx vitest run tests/PublicLandingPage.test.tsx tests/PublicLandingEvaluation.test.tsx tests/experiments.test.ts`

## 3. 검증·리뷰·스펙 동기화

이슈: https://github.com/kanziman/NexusWiki/issues/285

- [x] 3.1 대시보드 테스트·typecheck·lint·prettier와 `openspec validate landing-evaluation-intro --strict`를 새로 실행하고, 데스크톱·모바일 폭에서 랜딩 평가 섹션과 공개 위키 헤더를 확인한다. `spec-conformance-reviewer`·`tenant-isolation-reviewer`를 병렬로 돌려 pass를 받은 뒤 스펙 동기화와 아카이브를 브랜치에서 커밋한다.

AC:
Given: 1·2절이 끝났다.
When: 검증 명령과 리뷰 게이트를 실행한다.
Then: 모든 검증이 새 실행 결과로 통과하고 두 리뷰어가 pass이며, `openspec/specs/public-marketing-landing`·`openspec/specs/public-sharing`에 요구사항이 반영되고 change가 아카이브된다.

검증:
`cd apps/dashboard && pnpm test && pnpm typecheck && pnpm lint && cd ../.. && openspec validate landing-evaluation-intro --strict`

기록:
- 리뷰 r1은 두 리뷰어 모두 pass다. spec-conformance 리뷰의 비차단 지적(같은 실행 출처의 실험이 앞에 있으면 대표 실험이 사라짐)을 받아 `featuredAdoption`이 실행 출처 대신 실험 id로 기준·정책·결정을 붙이게 고치고 회귀 테스트를 추가했다. 수정 뒤 전체 검증을 다시 실행했다.
- 공개 위키 헤더의 브라우저 확인은 Docker 장애로 로컬 DB를 띄울 수 없어, 사이드카 두 테이블만 흉내 내는 가짜 PostgREST에 개발 서버를 붙여 1280·375 폭에서 했다. 비밀값은 쓰지 않았다.
