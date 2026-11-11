# Spec Conformance 리뷰 — landing-evaluation-intro r1

- 판정: pass
- 대상: 커밋 전 작업 트리 (`git diff` + 미추적 파일, 기준 HEAD `8b0fde4`, 브랜치 `feat/landing-evaluation-intro`)
- 일시: 2026-11-11T13:26:02Z

## 직접 재실행한 검증

- `npx vitest run tests/PublicLandingEvaluation.test.tsx tests/experiments.test.ts tests/public-wiki-page-route.test.tsx tests/PublicLandingPage.test.tsx` → 24 통과 · 0 실패
- `npx tsc --noEmit -p .` → 오류 없음
- 변경 파일 7개 `eslint` → 문제 없음
- `openspec validate landing-evaluation-intro --strict` → valid
- 브라우저 확인(1280 · 375 폭 가로 넘침 0px)은 호출자가 보고한 결과다. 이 리뷰에서 독립 재현하지 않았다.

## 시나리오 판정

### public-marketing-landing / 기록된 평가 판정의 랜딩 소개

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 대표 실험 판정 표시 — 제목 · 결정 | 충족 | `apps/dashboard/components/public-landing/PublicLandingEvaluation.tsx:92`(제목), `:97`(`decisionLabels`) · 선택 규칙 `apps/dashboard/lib/experiments.ts:129-143` · 테스트 `apps/dashboard/tests/PublicLandingEvaluation.test.tsx:15,27` |
| 대표 실험 판정 표시 — 원래 기준 충족 수/전체 수 | 충족 | `PublicLandingEvaluation.tsx:73,104`(스냅샷 `met` 플래그로 계산) · 테스트 `PublicLandingEvaluation.test.tsx:28-31`(스냅샷 계산값과 리터럴 「6개 중 3개」 둘 다 대조) |
| 대표 실험 판정 표시 — 미충족 조건별 실제값 · 허용값 | 충족 | `PublicLandingEvaluation.tsx:74,122-129`(문자열을 해석 없이 그대로 출력) · 테스트 `PublicLandingEvaluation.test.tsx:32-38`(미충족 3개 전부 + 충족 조건 미혼입) |
| 대표 실험 판정 표시 — 같은 블록의 합성 시나리오 표기 | 충족 | `PublicLandingEvaluation.tsx:82-84`(`article` 첫 줄), `:172`(`snapshot.synthetic === true`일 때만) · `lib/experiments.ts:88` · 테스트 `PublicLandingEvaluation.test.tsx:26`, 비합성 반례 `:83-90` |
| 대표 실험 판정 표시 — 재검색 실험 페이지 링크 | 충족 | `PublicLandingEvaluation.tsx:17-19,75,106-113` · 테스트 `PublicLandingEvaluation.test.tsx:39-41` |
| 대표 실험을 찾을 수 없음 — 결정 기록 없음 | 충족 | `lib/experiments.ts:132-137` · 테스트 `tests/experiments.test.ts:42-44`, `PublicLandingEvaluation.test.tsx:75-81` |
| 대표 실험을 찾을 수 없음 — 기준 세트 · 정책 참조 끊김 | 충족 | `lib/experiments.ts:110,141` · 테스트 기준 세트 `PublicLandingEvaluation.test.tsx:60-73`, 정책 `tests/experiments.test.ts:38-40` |
| 대표 실험을 찾을 수 없음 — 소개 문구와 평가 페이지 링크만 표시 | 충족 | `PublicLandingEvaluation.tsx:155-167`(소개는 항상), `:169-174`(블록 생략), `:176-194`(카드 링크) · 테스트 `PublicLandingEvaluation.test.tsx:65-72`(article 없음, 「미채택」·「충족」·「+66.4%」 없음, 링크 3개) |
| 대표 실험을 찾을 수 없음 — 랜딩의 나머지 섹션 그대로 렌더링 | 충족(구조 근거) | 대체 경로는 예외 없이 `null`만 반환(`PublicLandingEvaluation.tsx:169-174`), 랜딩은 형제 섹션으로 배치(`apps/dashboard/components/PublicLandingPage.tsx:329`). 끊긴 스냅샷으로 전체 랜딩을 렌더링하는 테스트는 없다(`PublicLandingPage`가 스냅샷을 주입받지 않음) |
| 평가 페이지 카드 연결 — 세 페이지로 이동 | 충족 | `PublicLandingEvaluation.tsx:27-43,177-193` · 테스트 `PublicLandingEvaluation.test.tsx:44-58` |
| 평가 페이지 카드 연결 — 포커스 상태 | 충족 | `PublicLandingEvaluation.tsx:109,182`(`nw-focus-ring`) · 규칙 `apps/dashboard/app/globals.css:102-107`. 클래스 부착을 단언하는 테스트는 없다 |
| 평가 페이지 카드 연결 — 미리 가져오지 않음 | 충족 | `PublicLandingEvaluation.tsx:108,181`(`prefetch={false}`) · 테스트 `PublicLandingEvaluation.test.tsx:92-106`(소스의 모든 `<Link>`에 `prefetch={false}`) |
| 모바일 평가 소개 | 충족(수동 확인 근거) | `PublicLandingEvaluation.tsx:85`(`grid-cols-1` → `md:` 2열), `:176`(`grid-cols-1 md:grid-cols-3`), `min-w-0`·`break-words`(`:80,86,123,125`). 자동 테스트 없음. 375px 넘침 0px은 호출자 브라우저 확인에 의존 |
| Requirement 본문 — 스냅샷에 없는 판정 · 수치 금지 | 충족 | 블록의 수치는 전부 스냅샷 필드(`conditions.length`, `met`, `actual`, `limit`)에서 나옴. 카드 문구(`:31,36,41`)와 소개 문단(`:163-165`)에 수치 없음 |

### public-sharing / Public viewer returns to the public home

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Visitor returns to the landing from a published page | 충족 | `apps/dashboard/app/p/[slug]/[page]/page.tsx:124-131`(`Link href="/"`, `aria-label="NexusWiki 홈"`) · 테스트 `apps/dashboard/tests/public-wiki-page-route.test.tsx:274-277`. `/`의 미인증 랜딩은 기존 동작 `apps/dashboard/app/page.tsx:18` |
| Opening a published page does not prefetch the home route | 충족 | `page.tsx:126`(`prefetch={false}`) · 테스트 `public-wiki-page-route.test.tsx:330-341`(`href="/"` Link가 정확히 1개이고 `prefetch={false}`) · `/w/` 없음 `:197`, `:326` |
| Requirement 본문 — 키보드 포커스 · 보이는 포커스 상태 | 충족 | `<a>`로 렌더링되어 기본 포커스 가능, `page.tsx:127`의 `nw-focus-ring` · `globals.css:102-107` |
| Requirement 본문 — 헤더 3열 정렬 불변 | 충족(구조 근거) | 같은 클래스 `.public-brand-logo` 유지(`page.tsx:127`), 규칙이 요소 종류와 무관한 `display:flex; flex:none; width/height 28px`(`docs/design-systems/v2/nexuswiki-design-system.css:3207-3217`). 테스트는 `.public-header-grid` 존재만 확인(`public-wiki-page-route.test.tsx:268`). 넓은 화면의 실제 정렬은 로컬 DB 문제로 브라우저 확인 안 됨 |

### 기존 메인 스펙과의 충돌

| 대상 | 결과 | 근거 |
| --- | --- | --- |
| `public-marketing-landing` / 실제 제품 계약에 맞는 마케팅 표현(확인되지 않은 수치 금지) | 충돌 없음 | 새 섹션의 수치는 커밋된 스냅샷 값만 쓰고, 합성 표기와 미채택 결정을 함께 보인다. 처리 시간 · 용량 · 무료 범위 · 모델 학습 정책 표현은 추가되지 않았다 |
| `public-marketing-landing` / 반응형 · 키보드 탐색 | 충돌 없음 | 새 링크 전부 `nw-focus-ring`, 모바일 1열 |
| `public-sharing` / `/w/` 링크 금지 | 충돌 없음 | 추가 링크는 `/` 하나. `/w/` 부재 테스트 유지(`public-wiki-page-route.test.tsx:197,326`) |
| `public-sharing` / 3열 셸 정렬 | 충돌 없음(구조 근거) | 위 표 참조 |
| `public-sharing` / 공개 라우트 테이블 조회 금지 | 영향 없음 | 헤더 변경은 마크업만 바꾸고 질의를 추가하지 않는다 |

### task 완료 주장 대조

- 1.1 `- [x]`: 구현(`page.tsx:124-131`)과 테스트(`public-wiki-page-route.test.tsx:274-277,330-341`) 모두 있음. 축소 없음
- 2.1 `- [x]`: `featuredAdoption`·`synthetic`·컴포넌트·대체 표시·카드 3개·`prefetch={false}`·랜딩 교체(`PublicLandingPage.tsx:329`) 전부 존재하고 각각 테스트가 있음. 축소 없음
- 3.1 `- [ ]`: 리뷰 게이트 진행 중이라 미완료가 맞다

### 스펙 밖 동작

- 대표 실험 블록에 실험 질문(`experiment.question`, `PublicLandingEvaluation.tsx:101`)이 보인다. delta spec의 표시 목록에는 없지만 `design.md` D2에 명시돼 있고, 스냅샷 문자열이며 판정 · 수치가 아니므로 금지 조항에 걸리지 않는다
- 그 밖에 스펙에 없는 사용자 관찰 가능 동작은 찾지 못했다

## 조치가 필요한 항목

필수 조치 없음. 아래는 판정에 영향을 주지 않는 관찰이다.

1. **실행 출처 중복 시 대표 실험이 사라질 수 있음** — `lib/experiments.ts:138-139`는 `experimentFor(run_source)`가 같은 id를 돌려주지 않으면 `undefined`를 반환한다. 같은 `run_source`를 쓰는 실험이 앞에 하나 더 등록되면 결정과 참조가 온전한 도입 실험이 있어도 랜딩이 대체 표시로 떨어진다. 지금 스냅샷(`content/experiments.json`)에서는 출처가 1:1이라 일어나지 않고, 상세 페이지와 다른 실험을 가리키지 않게 막는 의도로 보인다. 제안: 출처당 실험 하나라는 전제를 주석으로 남기거나 스냅샷 테스트로 고정한다.
2. **자동 테스트가 없는 시나리오 조건** — 「랜딩 나머지 섹션 그대로」, 카드 포커스 링 클래스, 모바일 1열 배치는 구조 근거와 호출자 수동 확인에 기대고 있다. 제안(선택): 카드 링크에 `nw-focus-ring` 클래스가 붙는지 단언 한 줄을 추가한다.

## 판정 근거

delta spec 두 개의 Requirement 2개와 Scenario 6개가 모두 코드 경로로 충족되고, 핵심 THEN(스냅샷 값 그대로 표시, 합성 표기, 끊긴 참조 대체, 카드 대상, `prefetch={false}`, 홈 링크 대상과 접근 이름, `/w/` 부재)은 테스트가 직접 확인한다. 기존 메인 스펙의 확인되지 않은 수치 금지 · `/w/` 링크 금지 · 3열 정렬과도 충돌하지 않는다. 남은 공백은 레이아웃 수준의 수동 확인 항목뿐이라 `pass`로 판정한다.
