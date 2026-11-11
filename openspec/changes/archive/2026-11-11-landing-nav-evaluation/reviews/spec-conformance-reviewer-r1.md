# Spec Conformance 리뷰 — landing-nav-evaluation r1

- 판정: needs_fix
- 대상: 미커밋 작업 트리 `git diff` (기준 HEAD `a79617d`) — `apps/dashboard/components/public-landing/PublicLandingHeader.tsx`, `apps/dashboard/tests/PublicLandingPage.test.tsx`
- 일시: 2026-11-11T14:11:57Z

## 재실행한 검증

- `npx vitest run tests/PublicLandingPage.test.tsx` — 6 통과 / 0 실패
- 랜딩 관련 테스트 파일 전체(`PublicLandingPage`·`공개 랜딩` 참조 2개 파일) — 10 통과
- `npx tsc --noEmit` — 오류 없음
- `npx eslint components/public-landing/PublicLandingHeader.tsx tests/PublicLandingPage.test.tsx` — 문제 없음
- `openspec validate landing-nav-evaluation --strict` — valid

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 반응형 공개 랜딩 탐색과 전환 / 모바일 랜딩 탐색 | 충족 (레이아웃 실측은 확인 불가) | 모바일 메뉴는 세로 목록(`PublicLandingHeader.tsx:111` `flex-col`)에 링크 1개가 추가될 뿐이라 가로 넘침 요인이 없다. 데스크톱 `md` 경계 대응은 `:54` `gap-4 lg:gap-7`, `:60`·`:68` `whitespace-nowrap`. 768/1024px 줄바꿈·겹침 없음은 호출자의 브라우저 측정 보고에 의존하며 리뷰어가 재현하지 않았다. jsdom 테스트로는 검증할 수 없다 |
| 반응형 공개 랜딩 탐색과 전환 / 상단 메뉴의 평가 기록 링크 — 데스크톱 FAQ 다음 | 충족 | `PublicLandingHeader.tsx:56-71` (sectionLinks 뒤, 마지막 항목 FAQ `:15` 다음) · 테스트 `PublicLandingPage.test.tsx:38-44` (`slice(-2)` = `["FAQ","평가 기록"]`) |
| 〃 — 모바일 FAQ 다음 | 충족 (순서 테스트는 없음) | `PublicLandingHeader.tsx:112-129` · 테스트 `PublicLandingPage.test.tsx:49-55`는 링크 존재와 href만 확인하고 FAQ 다음이라는 **순서**는 확인하지 않는다 |
| 〃 — `/showcase/evaluation`으로 이동 | 충족 | `PublicLandingHeader.tsx:20-23`, `:66`, `:123` · 테스트 `PublicLandingPage.test.tsx:44-46`, `:56` |
| 〃 — 랜딩을 열었다는 이유만으로 대상 페이지를 미리 가져오지 않음 | 미검증 | 구현은 있음: `PublicLandingHeader.tsx:67`, `:124` `prefetch={false}`. 그러나 이를 확인하는 테스트가 없다. 같은 저장소는 동일 계약을 `tests/PublicLandingEvaluation.test.tsx:96-111`에서 소스 스캔으로 검증하는 선례가 있다 |
| 〃 — 모바일 메뉴에서 선택하면 메뉴가 닫힘 | 충족 | `PublicLandingHeader.tsx:125` `onClick={onCloseMobileMenu}` · 테스트 `PublicLandingPage.test.tsx:58-63` (`aria-expanded="false"`) |
| 반응형 공개 랜딩 탐색과 전환 / 키보드 탐색 | 충족 | 새 링크는 `next/link`가 렌더하는 `<a href>`라 키보드 포커스 가능하고, 기존 섹션 링크와 동일한 `nw-focus-ring` 클래스를 쓴다(`:68`, `:126`). 기존 시나리오 범위에서 회귀 없음 |
| 반응형 공개 랜딩 탐색과 전환 / 감소 모션 환경 | 충족 | 새 링크에는 `transition-colors`만 있고 반복·이동 애니메이션이 없다(`:68`, `:126`). 변경 없음 |

## 범위 점검

- **조용한 범위 축소**: 없음. 스펙이 요구하는 네 조건(양 메뉴 · FAQ 다음 · 대상 경로 · 무프리페치 · 모바일 닫힘)이 모두 코드에 있다.
- **미검증 완료 주장**: 부분적으로 있음. task 1.1이 `- [x]`인데, 스펙 THEN 절의 "미리 가져오지 않음"을 확인하는 테스트가 없다. task 1.1이 테스트 대상을 "링크 대상과 모바일 닫힘"으로 한정해 적었기 때문에 task 문면과는 어긋나지 않지만, 스펙 시나리오 기준으로는 검증 공백이다.
- **스펙 밖 동작**: 없음. `gap-4 lg:gap-7`·`whitespace-nowrap`은 사용자 관찰 동작이 아니라 요구사항의 "가로 넘침 없이"를 지키기 위한 레이아웃 조정이다. `design.md` Risks는 `gap-7` 유지 확인을 적었으나 실제로는 `md`에서 `gap-4`로 줄였다 — 결정 기록이 구현과 어긋나지만 스펙 위반은 아니다(아래 3번 참고).

## 조치가 필요한 항목

1. **평가 기록 링크의 무프리페치 계약 테스트 추가** — 근거 Scenario: 「상단 메뉴의 평가 기록 링크」 THEN "랜딩을 열었다는 이유만으로 대상 페이지를 미리 가져오지 않고". 제안: `tests/PublicLandingEvaluation.test.tsx:96-111`과 같은 방식으로 `components/public-landing/PublicLandingHeader.tsx` 소스에서 `href={evaluationLink.href}`를 가진 `<Link …>` 태그를 모두 찾아(데스크톱·모바일 2개) 각각 `prefetch={false}`를 포함하는지 단언한다. 헤더의 `/`·`/login` 링크는 이 계약 대상이 아니므로 전체 `<Link>` 일괄 단언은 쓰지 않는다.
2. **(권장) 모바일 메뉴 순서 단언** — 근거 Scenario: 같은 시나리오 THEN "두 메뉴 모두 FAQ 다음에". 데스크톱은 `slice(-2)`로 순서를 검증하지만 모바일은 존재만 확인한다. 모바일 nav의 링크 텍스트 목록에서 「FAQ」 바로 다음이 「평가 기록」인지 단언한다(모바일은 뒤에 「로그인」이 있으므로 `slice(-2)`가 아니라 인덱스 비교).
3. **(권장, 판정 영향 없음) `design.md` Risks 갱신** — "`gap-7`로 넘침이 없는지 확인"이라 적혀 있으나 실제 구현은 `md`에서 `gap-4`, `lg`부터 `gap-7`이고 `whitespace-nowrap`을 더했다. 실측 결과(768/1024px 줄바꿈·겹침 없음)와 함께 결정을 기록한다.

## 판정 근거

모든 시나리오의 동작은 코드에 존재하고 테스트·typecheck·lint·strict validate가 새로 실행해 통과한다. 다만 새 시나리오 THEN 절의 한 조건(무프리페치)은 대응 테스트가 없어 증거가 코드 한 줄뿐이고, 저장소에 동일 계약을 테스트로 고정하는 선례가 있다. 스펙은 명확하고 고칠 대상은 테스트 코드뿐이므로 `blocked`가 아니라 `needs_fix`다. 1번을 반영하면 `pass`로 판단할 수 있다.
