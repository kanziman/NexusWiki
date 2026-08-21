## 1. 본문 폭 통일

- [x] 1.1 `.content`의 `width`를 `min(1280px, 100%)`로 올린다 (`nexuswiki-design-system.css`). 폭이 이제 목적지 간 단일값이라는 근거를 주석으로 남기고, "통일할 근거가 없어 그대로 둔다"는 기존 주석을 걷어낸다
- [x] 1.2 `.content.settings` · `.content.sources` · `.content.backlog` · `.content.library`에서 `width` 선언만 제거한다. 각 규칙의 패딩·그리드·탭 등 나머지 선언은 유지한다
- [x] 1.3 좁은 뷰포트 미디어 쿼리(`.content { padding: 30px 20px }` · `25px 14px`)가 여전히 유효한지 확인한다 — 폭 상한이 올랐을 뿐 `min(…, 100%)`이라 좁은 화면 동작은 그대로여야 한다

## 2. 타이포 스케일

> ⚠️ 구현 중 범위를 좁혔다. 기본 규칙이 약 180곳이고 폰트 크기 토큰이 없어 전면 +1px은 회귀 위험이 크고 Vitest가 잡지 못한다. 델타 스펙이 요구하는 상태 텍스트 가독성 + 본문 기본값만 올린다 — 근거는 design.md Decision 4.

- [x] 2.1 `body`의 기본 크기를 14px → 15px로 올린다
- [x] 2.2 상태 텍스트군을 12px로 통일한다 — `.status`(11px) · `.tag`(10px) · `.verified`(9px) · `.inspect .tag`(9px) · `.inspect .kicker`(9px) · `.public-badge`(9px) · `.public-stamp`(10px) · `.backlog .doc-title:before`("작성 대기", 9px)
- [x] 2.3 `.badge`를 `600 10px var(--font-mono)` → 12px로 올린다. 상태 텍스트는 장식이 아니라 신뢰 정보를 나른다(design.md Decision 4)
- [x] 2.4 `.status`가 들어가는 파이프라인 표 셀에 상향의 영향을 주석으로 남긴다 — 그 자리는 문구가 한 글자씩 세로로 접혔던 전례가 있다
- [x] 2.5 11·12·13px 본문·메타를 손대지 않았음을 확인한다. 전면 스케일 조정은 토큰 도입을 수반하는 별도 사안이다

## 3. 상태 어휘 단일화

- [x] 3.1 `verification_status` 값 → 라벨 매핑을 공유 모듈 하나로 만든다. `verified` → "검증됨", `partial` → "부분 검증", 나머지 → 기존 표기 유지
- [x] 3.2 `WikiLibrary.tsx`가 자체 문자열 대신 그 모듈을 쓰도록 바꾼다
- [x] 3.3 `KnowledgeGrid.tsx`의 "검증 완료"를 그 모듈에서 파생한 "검증됨"으로 바꾼다
- [x] 3.4 `workspace-home.test.tsx:102` · `KnowledgeGrid.test.tsx:43`의 `"검증 완료"` 단언을 "검증됨"으로 고친다
- [x] 3.5 두 목적지가 같은 라벨을 쓰는지 검증하는 테스트를 추가한다 (델타 스펙의 `Member sees the same underlying status on two destinations` 시나리오)

## 4. eyebrow 감축

- [x] 4.1 `AskConversation.tsx`의 `ASK · DUAL CITATION`을 제거한다
- [x] 4.2 `BacklogList.tsx`의 `BACKLOG · RED LINKS`를 제거한다
- [x] 4.3 `SourcesList.tsx`의 `SOURCE PIPELINE · DATABASE & RLS`를 제거한다
- [x] 4.4 `WikiLibrary.tsx`의 `COMPILED KNOWLEDGE`를 제거한다
- [x] 4.5 `settings/page.tsx`의 `WORKSPACE CONTROL · RBAC`를 제거한다
- [x] 4.6 `WikiPageContent.tsx`의 브레드크럼(`위키 / {category}`)은 **유지**하되, 한국어에 맞지 않는 `text-transform: uppercase` · 넓은 `letter-spacing` · 모노스페이스를 벗긴 읽기용 처리를 준다
- [x] 4.7 eyebrow를 제거한 화면에서 제목 아래 설명문이 h1과 같은 말을 반복하면 문구를 정리한다 (design.md Decision 5의 "최소 개입" 범위)

## 5. 프리뷰 동기화

- [x] 5.1 `PreviewWorkspace.tsx`의 eyebrow 11곳에 4번과 같은 기준을 적용한다
- [x] 5.2 `PreviewWorkspace.tsx`의 상태 문구("검증됨" · "부분 검증")가 3.1 모듈의 어휘와 일치하는지 확인한다
- [x] 5.3 프리뷰가 제거된 eyebrow에 의존하는 테스트(`PreviewWorkspace.test.tsx` · `preview-layout.test.tsx`)를 확인하고 필요하면 고친다

## 6. 검증

- [x] 6.1 `pnpm typecheck` · `pnpm lint` · `pnpm test` · `pnpm build`를 새로 실행해 전부 통과시킨다
- [x] 6.2 `openspec validate dashboard-layout-density --strict`를 통과시킨다
- [x] 6.3 **육안 확인**: `/preview`를 넓은 뷰포트에서 열어 홈 · 소스 · 위키 · 백로그 · 설정의 좌우 경계선이 같은지, 배지·메타가 읽히는지 확인한다. ⚠️ 폭과 크기는 시각 속성이라 Vitest가 잡지 못한다(design.md Risks)
- [x] 6.4 좁은 뷰포트(900px 이하 · 650px 이하)에서 가로 오버플로가 없는지 확인한다
- [x] 6.5 리뷰 게이트: `spec-conformance-reviewer` · `tenant-isolation-reviewer`를 병렬로 돌리고 판정을 사용자에게 중계한다

## 7. 리뷰 게이트 r1 대응

> `spec-conformance-reviewer` r1 = blocked · `tenant-isolation-reviewer` r1 = needs_fix.
> 스펙 수정 3건은 사용자 결정으로 확정했다(폭 요구사항 범위 축소 · 리듬 요구사항 제거 · 리더 어휘 통일).

- [x] 7.1 델타 스펙의 폭 요구사항을 "공유 콘텐츠 캔버스를 쓰는 목적지"로 좁히고, Ask(사용자가 폭을 직접 조절)·리더(읽기 measure)를 사유와 함께 예외로 명시한다. 대응 시나리오도 둘로 나눈다
- [x] 7.2 "각 목적지가 주 작업 대상에 시각적 비중을 준다" 요구사항을 델타에서 제거한다 — design.md Decision 5가 후속 change로 미룬 항목이라, 남기면 archive 시 baseline이 구현되지 않은 동작을 단정한다
- [x] 7.3 하한 아래 남은 상태 텍스트 2곳을 12px로 올린다 — `.metric small`(9px, "대기·실행 중·실패", danger 색 동반) · `.share-state`(10px, "ON/OFF", 색으로 상태 구분)
- [x] 7.4 앱 홈의 eyebrow(`워크스페이스`)를 제거한다. design.md Decision 3 표가 홈 라우트를 누락했다
- [x] 7.5 `.eyebrow` 주석을 사실대로 고친다 — 앱·프리뷰 양쪽 다 사용처가 없다(이전 주석은 둘 다 반대로 적었다)
- [x] 7.6 홈 대시보드 쿼리에 `disputed`를 추가하고 `WikiPageSummary`에 필드를 넣는다. 빠져 있어 충돌 우선순위가 홈에서만 도달 불가능했다
- [x] 7.7 위키 리더의 `"부분 검증됨"`을 모듈에서 파생한 `"부분 검증"`으로 맞춘다. 뒤따르는 안내 문구는 이 화면 고유 확장이라 유지하고, UI-SPEC 계약이 보호하는 충돌 콜아웃은 건드리지 않는다
- [x] 7.8 홈이 충돌 문서에도 배지를 띄우게 한다 — 검증만 띄우면 충돌 문서가 홈에서 아무 표식 없이 지나간다(회귀 테스트가 잡은 잔여 결함)
- [x] 7.9 회귀 테스트 2건 추가 — 충돌 문서의 두 목적지 라벨 일치, topbar 전역 지식 액션 2개 제한

## 8. 리뷰 게이트 r2 대응

> `spec-conformance-reviewer` r2 = needs_fix (blocked 해소) · `tenant-isolation-reviewer` r2 = needs_fix.
> ⚠️ r1 때 보고서 요약만 보고 대응해 r1-2(라이브러리 통계 이중 어휘)를 놓쳤다. r2부터는 보고서 본문을 직접 읽는다.

- [x] 8.1 `expires_at`을 신뢰 상태 판정에 편입한다 — 모듈이 `verified && 만료` → "검증 만료됨"을 내고 `isVerified`가 만료를 제외한다. 홈·위키 라이브러리 select와 타입에 컬럼 추가. `0007_search_and_queue_extensions.sql` §5가 "만료된 검증을 검증으로 세면 오래된 위키가 영원히 verified로 남습니다"라고 명시적으로 금지한 상태였다
- [x] 8.2 홈이 만료 문서도 배지로 띄우게 한다. `.badge.verified`는 살아있는 검증에만 붙이고 충돌·만료는 중립 `.badge`로 그린다 — `workspace-home-prd.md` §3.3의 `.badge.verified` 규칙을 지키면서 무표시 통과를 막는다
- [x] 8.3 (r1-2 미조치분) `WikiLibrary` 통계의 라벨을 "검증됨"으로, 술어를 `isVerified`로 바꾼다. 없애려던 이중 어휘가 목적지 간에서 사라지고 한 화면 안에 남아 있었고, 카운트가 `disputed` 행을 검증으로 세고 있었다
- [x] 8.4 리더의 충돌 콜아웃도 모듈에서 상태명을 파생한다. "UI-SPEC 계약 보호 대상"이라던 7.7의 근거가 틀렸다 — `grep -rl "Copywriting Contract" docs/` 가 0건이라 그 계약 문서는 리포지토리에 없다
- [x] 8.5 홈 테스트 모의가 `select()` 인자를 기록하게 하고, 신뢰 판정 컬럼 3종을 단언한다. 예전 모의는 인자를 버려 컬럼을 빼도 전부 통과했다 — 가드가 실제로 실패하는지 `expires_at`을 일시 제거해 확인했다
- [x] 8.6 topbar 회귀 테스트가 `<button>`으로 추가되는 지식 액션도 잡게 한다
- [x] 8.7 `proposal.md`에서 7.2로 제거한 리듬 요구사항 약속을 걷어낸다
- [x] 8.8 `design.md`를 구현과 맞춘다 — Decision 3 표에 홈 추가, Decision 4 표에 `.metric small`·`.share-state` 추가, Decision 5를 "스펙 요구사항이 아니다"로 다시 쓴다
- [x] 8.9 델타 스펙의 예외 열거를 `specifically` → `for example` 로 바꾼다. 원문 소스 상세(`max-w-4xl`)가 캔버스도 열거된 예외도 아니라 닫힌 목록이 사실과 어긋났다

## 9. 리뷰 게이트 r3 대응 (권고, 판정 불변)

> `spec-conformance-reviewer` r3 = **pass** · `tenant-isolation-reviewer` r3 = **pass**. 둘 다 치명 항목 없이 통과했다. 아래는 두 보고서의 비차단 권고를 반영한 것 — 판정을 바꾸지 않지만 이번 change가 두 번 물린 "주석·문서가 현실과 어긋난다" 부류라 남겨두지 않는다.

- [x] 9.1 리더의 남은 리터럴("검증됨"·"검증 만료됨")을 모듈에서 파생시킨다 — 홈·라이브러리와 같은 상태명을 쓰는지 이제 세 목적지 전부 한 함수가 보장한다
- [x] 9.2 홈 테스트에 충돌·만료 문서의 렌더 결과를 단언하는 케이스를 추가한다. select→props 매핑(`disputed: p.disputed`)을 지워 가드가 실제로 실패하는 것을 확인했다 — select 문자열만 지키는 8.5로는 이 겹을 못 덮었다
- [x] 9.3 design.md Decision 2에 라운드별로 넓어진 이력(disputed → expires_at → 카운트 술어)과 PRD §3.3 둘째 절과의 불일치를 기록한다. 되돌릴지 PRD를 고칠지는 사람의 결정 사안으로 남긴다
- [x] 9.4 `KnowledgeGrid.tsx` 주석에 PRD §3.3 판정 결과(첫 절 충족·둘째 절 문자 그대로 불일치)까지 적는다
- [x] 9.5 design.md의 "6개 목적지"를 "5개"로 정정한다 — Ask·리더는 애초에 `.content`를 쓰지 않는다
- [x] 9.6 CSS 주석이 인용하는 스펙 문장을 7.1로 정정된 실제 문장("Destinations that render on the shared content canvas SHALL …")으로 맞춘다
