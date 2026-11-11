# Spec Conformance 리뷰 — landing-nav-evaluation r2

- 판정: pass
- 대상: 미커밋 작업 트리 `git diff` (기준 HEAD `a79617d`) — `apps/dashboard/components/public-landing/PublicLandingHeader.tsx`, `apps/dashboard/tests/PublicLandingPage.test.tsx`, `openspec/changes/landing-nav-evaluation/design.md`
- 일시: 2026-11-11T14:14:06Z

## 재실행한 검증

- `npx vitest run` (dashboard 전체) — 579 통과 / 0 실패
- `npx tsc --noEmit` — 종료 코드 0
- `npx eslint components/public-landing/PublicLandingHeader.tsx tests/PublicLandingPage.test.tsx` — 종료 코드 0
- `openspec validate landing-nav-evaluation --strict` — valid
- 변이 확인: 헤더 소스에서 모바일 평가 기록 링크의 `prefetch={false}` 한 줄(`:124`)을 지운 사본을 scratchpad에 만들고 새 테스트의 정규식·필터를 그대로 적용했다. 대상 링크 2개가 잡히고 "모두 prefetch={false}" 조건이 false가 되었으므로, 새 테스트는 이 회귀를 잡아낸다

## r1 지적 반영 대조

| r1 항목 | 반영 | 증거 |
| --- | --- | --- |
| 1. 무프리페치 계약 테스트 추가 (필수) | 반영 | `tests/PublicLandingPage.test.tsx:74-91` — `href={evaluationLink.href}`인 `<Link>`만 골라 개수 2를 확인하고 각각 `prefetch={false}`를 단언. 홈·로그인 링크는 대상에서 빠진다(`:82-85`). 위 변이 확인으로 실제로 실패를 일으킴을 확인 |
| 2. 모바일 메뉴 순서 단언 (권장) | 반영 | `tests/PublicLandingPage.test.tsx:60-64` — 모바일 링크 텍스트 목록에서 `indexOf("FAQ") + 1` 자리가 「평가 기록」인지 단언 |
| 3. `design.md` Risks 갱신 (권장) | 반영 | `design.md` Risks — `gap-7`의 `md` 줄바꿈 원인, `gap-4 lg:gap-7` · `whitespace-nowrap` 조치, 768px·1024px iframe 측정 결과 기록 |

구현 파일 `PublicLandingHeader.tsx`는 r1 이후 바뀌지 않았다(`:66-67`, `:123-124` 그대로).

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 반응형 공개 랜딩 탐색과 전환 / 모바일 랜딩 탐색 | 충족 (레이아웃 실측은 리뷰어가 재현하지 않음) | 모바일 메뉴 세로 목록 `PublicLandingHeader.tsx:111`, 데스크톱 `md` 대응 `:54`·`:60`·`:68`. 768/1024px 측정은 `design.md` Risks에 기록된 호출자 측정에 의존 |
| 〃 / 상단 메뉴의 평가 기록 링크 — 데스크톱 FAQ 다음 | 충족 | `PublicLandingHeader.tsx:56-71` · 테스트 `PublicLandingPage.test.tsx:41-47` |
| 〃 — 모바일 FAQ 다음 | 충족 | `PublicLandingHeader.tsx:112-129` · 테스트 `PublicLandingPage.test.tsx:60-64` |
| 〃 — `/showcase/evaluation`으로 이동 | 충족 | `PublicLandingHeader.tsx:20-23`, `:66`, `:123` · 테스트 `PublicLandingPage.test.tsx:48-50`, `:59` |
| 〃 — 대상 페이지를 미리 가져오지 않음 | 충족 | `PublicLandingHeader.tsx:67`, `:124` · 테스트 `PublicLandingPage.test.tsx:74-91` |
| 〃 — 모바일 메뉴에서 선택하면 닫힘 | 충족 | `PublicLandingHeader.tsx:125` · 테스트 `PublicLandingPage.test.tsx:66-71` |
| 〃 / 키보드 탐색 | 충족 | 새 링크는 `<a href>`로 렌더되며 `nw-focus-ring` 사용(`:68`, `:126`). 회귀 없음 |
| 〃 / 감소 모션 환경 | 충족 | 새 링크에는 `transition-colors`만 있음(`:68`, `:126`). 회귀 없음 |

## 범위 점검

- 조용한 범위 축소: 없음
- 미검증 완료 주장: 없음. r1에서 비어 있던 무프리페치 조건이 테스트로 고정됨
- 스펙 밖 동작: 없음. 간격·`whitespace-nowrap` 조정은 "가로 넘침 없이" 요구를 위한 레이아웃 조정이며 `design.md`에 기록됨

## 조치가 필요한 항목

없음.

## 판정 근거

delta spec의 모든 시나리오가 코드 경로와 테스트 증거를 함께 갖췄다. r1의 필수 지적과 권장 지적 두 건이 모두 반영됐고, 새 테스트가 실제 회귀를 잡는지도 변이로 확인했다. 남은 한계는 768/1024px 레이아웃 실측을 리뷰어가 재현하지 않았다는 점 하나다. jsdom으로는 검증할 수 없는 항목이고 측정 결과가 `design.md`에 기록돼 있어 판정을 막지 않는다.
