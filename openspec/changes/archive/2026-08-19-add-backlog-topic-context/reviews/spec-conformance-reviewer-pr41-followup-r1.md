# Spec Conformance 리뷰 — PR #41 후속분(4283cc6..86d16d9) r1

- 판정: pass
- 대상: `git diff 4283cc6..86d16d9`(3커밋: `bb15cfa`, `d3fa9ab`, `86d16d9`)
- 대조 스펙: `openspec/specs/wiki-library-navigation/spec.md`, `openspec/specs/dashboard-design-consistency/spec.md`, `openspec/specs/source-management-wiki/spec.md`
- 참고: 이 3커밋에 대응하는 OpenSpec change는 없다(순수 육안 QA 픽스). `HANDOFF.md`(2026-08-19)가 "4283cc6 이후 리뷰 게이트 재실행 안 함"을 명시적으로 남겨 이번 리뷰 필요성을 스스로 확인하고 있다.
- 검증 실행: `cd apps/dashboard && pnpm typecheck && pnpm lint && pnpm test` — 전부 통과(typecheck 0 error · lint 0 issue · vitest 46 files / 188 tests pass)
- 일시: 2026-08-19T14:04:06Z

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| wiki-library-navigation / Searchable wiki library — "Search has no matching pages" | 충족 | `apps/dashboard/components/WikiLibrary.tsx:171-179`에서 `isEmpty`(전체 0건)와 필터 결과 0건을 분기해 `NO_MATCH_BODY`("조건에 맞는 위키 문서가 없습니다.")만 쓰는 경로가 "위키 페이지가 없다"를 암시하지 않음. 테스트 `apps/dashboard/tests/WikiLibrary.test.tsx:69-`("shows a distinct no-results state") 통과 |
| dashboard-design-consistency / Consistent workspace page structure — "Member moves between workspace destinations" | 충족 | `/wiki` 라우트가 `pages.length === 0`을 가로채 v1 마크업(제목·프레임 없음)을 반환하던 경로를 제거하고 `WikiLibrary`에 위임(`apps/dashboard/app/w/[workspaceId]/wiki/page.tsx:27-32`). 빈 상태에서도 `<h1>위키</h1>` 제목·`.content.library` 프레임이 유지됨을 회귀 테스트로 고정(`apps/dashboard/tests/WikiLibrary.test.tsx:46-67`, 특히 59-61의 `heading level:1 name:"위키"` 단언). CSS `--topbar-h`/`--shell-footer-h` 토큰화(`docs/design-systems/v2/nexuswiki-design-system.css:29-40`)로 상단바·LNB·리더 목차·Ask 인풋 4곳이 같은 기준선을 공유해 목적지 전환 시 셸 프레임이 흔들리지 않음 |
| dashboard-design-consistency / Shared state and control language — "Member encounters a non-default state" | 충족 | `JobStepper.tsx`가 Tailwind ad-hoc 유틸리티(색을 컴포넌트가 직접 지정)에서 이미 앱 전역에 존재하던 v2 상태 표기 계약 `.status`/`.status.pending`/`.status.failed`/`.dot`으로 교체(`apps/dashboard/components/JobStepper.tsx:209-223`, CSS 정의는 사전 존재: `docs/design-systems/v2/nexuswiki-design-system.css:483-494`). 상태 텍스트(`statusText`)는 그대로 유지돼 "색상만이 아니라 텍스트로" 요구를 계속 충족. 신설 규칙 `.pipe-line .status`(같은 CSS 파일 1668행)는 이 계약을 셀 폭 안에서 줄바꿈만 허용하도록 좁힌 것으로 계약 자체를 바꾸지 않음 |
| source-management-wiki / Real-time source job pipeline tracking — "Member views processing source" | 충족 | 활성 단계·진행률·취소/재시도 액션이 마크업 변경 후에도 동일한 텍스트·`aria-label`로 렌더됨. `apps/dashboard/tests/JobStepper.test.tsx` 5개 테스트가 `role`/텍스트 기준으로 조회하며 클래스명에 의존하지 않아 리팩터 후에도 그대로 통과(직접 실행 확인: `pnpm vitest run tests/JobStepper.test.tsx` → PASS) |
| source-management-wiki / Read-only compiled wiki document reader — "Member views verified wiki page" | 충족 | 요구사항 문구는 "read-only banner, verified status badge, structured markdown content" 표시만 요구하며 검증자 식별 표시를 요구하지 않음. `VerificationCallout`이 `검증됨 · {date}`만 렌더하도록 `verifiedBy`를 제거(`apps/dashboard/components/WikiPageContent.tsx:319-339`)해도 배지·날짜는 유지되어 시나리오 충족. 단, 삭제 전 코드 주석이 인용하던 "UI-SPEC Copywriting Contract 'Verified callout'"(원본은 `.planning/phases/06-dashboard/06-UI-SPEC.md:174`, `검증됨 · {verifier} · {verified_at 날짜}` verbatim 고정)은 `3e6bcef`(v1.0 phase 디렉터리 정리) 커밋에서 이미 저장소에서 삭제됐고, 후속 v2 문서(`docs/design-systems/dashboard-ui-spec.md`, e215b3c 도입)에는 이 verbatim 계약이 없음 — 현재 유효한 openspec/specs 어디에도 verifier 노출을 요구하는 근거가 없어 이번 삭제는 스펙 위반이 아님(아래 "판정 근거" 참조) |
| source-management-wiki / Source library with MIME type filter tabs | 영향 없음(비대상) | 이번 델타의 `SourcesList.tsx` 변경은 `<colgroup>` 폭 재분배뿐(`apps/dashboard/components/SourcesList.tsx:226-233`)이며 MIME 탭 로직·`.status`/`.dot` 렌더링 자체는 손대지 않음. `apps/dashboard/tests/SourcesList.test.tsx` 그대로 통과 |

## 조치가 필요한 항목

없음. 미충족 Scenario를 발견하지 못했다.

## 판정 근거

세 커밋은 전부 UI/CSS 레이어에 한정되고(파일 목록 확인, 마이그레이션·API·워커 변경 없음), 대조한 3개 스펙의 관련 Requirement/Scenario를 모두 코드 경로와 테스트로 확인했다. 특히 우려했던 두 지점을 직접 근거로 판정했다:

1. **`WikiPageContent.tsx`의 `verified_by` 제거** — 코드 주석이 스스로 인용하던 원래의 verbatim 카피 계약은 `.planning/phases/06-dashboard/06-UI-SPEC.md`(커밋 `2c1d383`에서 생성, `3e6bcef`에서 v1.0 phase 정리 중 삭제)에만 있었고, 이 문서는 지금 저장소에 존재하지 않는다. v2로 넘어오며 만들어진 대체 문서(`docs/design-systems/dashboard-ui-spec.md`)와 이번 리뷰가 판정 기준으로 삼은 `openspec/specs/source-management-wiki/spec.md` 어디에도 "verified_by/verifier를 표시해야 한다"는 요구가 없다. 따라서 이 변경은 이미 폐기된 문서를 근거로 남아 있던 죽은 주석을 실제로 정리한 것이며, 살아있는 스펙 기준으로는 위반이 아니다. (다만 지운 이전 주석이 인용하던 "UI-SPEC Copywriting Contract"라는 표현이 코드 여기저기(`RedLinkCta.tsx`, `Dropzone.tsx`, `InviteForm.tsx` 등)에 여전히 살아 있고 그 원본 문서가 사라진 상태라, 향후 다른 컴포넌트에서 같은 혼란이 재발할 수 있다는 점은 코드 정합성 이슈이지 스펙 준수 이슈는 아니므로 `/code-review` 소관으로 남겨둔다.)
2. **`JobStepper.tsx`의 Tailwind → `.status`/`.pipe-*` 전환** — `.status`/`.status.pending`/`.status.failed`/`.dot`은 이번에 새로 만든 관용구가 아니라 `docs/design-systems/v2/nexuswiki-design-system.css`에 이미 정의돼 있던 앱 전역 상태 표기 계약이며, `SourcesList.tsx`를 포함한 다른 화면이 이미 쓰고 있었다(원장상 `PRD §3.3` 인용). 이번 변경은 JobStepper만 이 계약에서 벗어나 있던 것을 맞춘 것이다. `apps/dashboard/tests/JobStepper.test.tsx`는 `screen.findByText`/`getByRole` 기준으로만 단언해 클래스명이나 DOM 구조에 의존하지 않으며, 실제로 리팩터 이후에도 5개 테스트 모두 그대로 통과했다(직접 실행 확인).

`WikiLibrary.tsx`의 빈 상태 이동(`bb15cfa`)은 `wiki-library-navigation`과 `dashboard-design-consistency` 양쪽의 "일관된 페이지 프레임" 요구를 회귀 테스트(`apps/dashboard/tests/WikiLibrary.test.tsx:46-67`)로 직접 고정했고, `SourcesList.tsx`의 열 폭 조정은 상태 표기 계약 자체를 건드리지 않았다.

`pnpm typecheck`/`pnpm lint`/`pnpm test`를 이 세션에서 새로 실행해 전부 통과했으며(46 files / 188 tests), 스펙 밖 사용자 관찰 가능 동작 추가나 조용한 범위 축소도 발견되지 않았다.
