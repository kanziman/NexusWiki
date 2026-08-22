# Spec Conformance 리뷰 — redesign-dashboard-knowledge-surfaces r1

- 판정: **needs_fix**
- 대상: 아카이브된 proposal/specs/design/tasks와 현재 워킹 트리의 dashboard 구현·테스트
- 일시: 2026-08-22T19:20:00+09:00

## 시나리오 판정

| Requirement / Scenario | 결과 | 핵심 증거 |
| --- | --- | --- |
| Compact accessible knowledge-surface controls / Member operates compact controls with a keyboard | 충족 | 공통 `:focus-visible` 처리와 입력 테두리/링(`nexuswiki-design-system.css:79-97`), 각 내비·검색·탭·모달 제어의 접근 가능한 이름. `Dropzone.test.tsx`와 사이드바 기존 테스트 통과 |
| Compact accessible knowledge-surface controls / Member uses the collapsed sidebar | **미충족** | 접힌 상태의 전체 라벨은 `:hover::after`에만 생성되고(`nexuswiki-design-system.css:317-334`) `:focus-visible`/`:focus-within` 대응이 없다. 더구나 계정 프로필의 유일한 설정 링크(`WorkspaceSidebar.tsx:228-235`)는 접힌 상태에서 `display:none` 처리된다(`nexuswiki-design-system.css:344`). 따라서 키보드 포커스로 라벨을 식별할 수 없고 계정 제어가 접힌 상태에서 운용되지 않는다 |
| Compact accessible knowledge-surface controls / Member opens source ingestion | 충족 | Radix Tabs의 파일/URL/텍스트 상태, 필수 필드, 제출 비활성화, 파일별 대기·성공·중복·실패가 구현되어 있고 `Dropzone.test.tsx`가 탭·필드·혼합 결과를 검증 |
| Source detail knowledge trace / Member opens a source from the library | 충족 | 제목과 상세 액션이 동일한 workspace-scoped 경로를 사용하고, 상세는 메타·파이프라인·원문·청크·인용 위키를 제공. `SourcesList.test.tsx`, `SourceDetailContent.test.tsx` 통과 |
| Source detail knowledge trace / Member inspects a source chunk | 충족 | 청크 선택, ordinal/문자 좌표, 본문과 복사 동작이 `SourceDetailContent.tsx`에 구현됨. 선택·좌표는 컴포넌트 테스트로 검증 |
| Source detail knowledge trace / Source has no extracted content or citations | 충족(테스트 보강 필요) | 청크·원문·인용 위키별 명시적 빈 상태가 구현됨. 현재 테스트는 청크와 인용 빈 상태만 단언하고 전체 원문 탭의 빈 상태는 직접 단언하지 않음 |
| Tenant-scoped source detail composition / Member views a source in the active workspace | 충족 | 요청자 `createClient()`로 `raw_sources`, `source_chunks`, `wiki_pages`를 각각 `workspace_id`에 스코프해 병렬 조회(`sources/[id]/page.tsx:24-45`) |
| Tenant-scoped source detail composition / Member requests an inaccessible source | 충족(테스트 미흡) | source 조회가 오류/무행이면 관련 데이터를 렌더하지 않고 고정 not-found를 반환. 다만 라우트 테스트 mock은 `workspace_id` 값을 기록하거나 판정하지 않아 다른 워크스페이스 fixture를 실제로 검증하지 못함(`source-detail-route.test.tsx:36-65,103-114`) |
| Tenant-scoped source detail composition / Related data is partially unavailable | 충족 | source가 보이면 chunk/wiki 오류·무행을 각각 빈 배열로 처리하고 상세를 유지(`sources/[id]/page.tsx:56-78`) |
| Clean wiki library previews / Library page contains rich markdown | 충족 | `cleanExcerpt`가 heading/강조/code/list/table/WikiLink 문법을 평문화하고 160자로 제한. 테스트 fixture로 표시 문구 검증 |
| Clean wiki library previews / Member searches cleaned content | 충족 | 표시와 검색이 같은 `cleanExcerpt` 함수를 사용(`WikiLibrary.tsx:41-58,90-96`), 회귀 테스트 통과 |
| Structured read-only wiki markdown / Member reads a structured wiki page | 충족 | heading, 단락, 순서/비순서 목록, 표, 인용, fenced/inline code, 강조가 의미 요소로 렌더됨. 구조 테스트 통과 |
| Structured read-only wiki markdown / Wiki content contains internal links | 충족 | 기존 `resolveWikiLinks` 결과를 resolved workspace 링크 또는 `RedLinkCta`로 렌더 |
| Structured read-only wiki markdown / Wiki content contains an unsafe markdown link | 충족 | 공통 `safeMarkdownHref`가 실행/미지원 프로토콜을 거부하고 라벨만 남김. 안전/위험 URL 테스트 통과 |
| Active wiki section navigation / Member reads through document sections | 충족(회귀 테스트 없음) | 본문과 목차가 같은 줄 인덱스 id를 쓰고 스크롤 위치상 마지막 heading을 active로 지정하며 level별 들여쓰기를 유지. 그러나 테스트는 목차 문구 존재만 확인하고 스크롤 경계·active 클래스·중첩 level을 검증하지 않음 |
| Active wiki section navigation / Member selects a table-of-contents entry | 충족(회귀 테스트 없음) | 클릭 시 `scrollIntoView({ behavior: "smooth" })`, `history.pushState(...#id)`, active 상태 갱신이 구현됨(`WikiPageContent.tsx:269-281`). 해당 세 동작을 실행하는 테스트가 없음 |
| Active wiki section navigation / Document has no supported headings | 충족(회귀 테스트 없음) | 빈 목차 링크와 active 표시 없이 안내 문구만 렌더. 무-heading fixture 테스트가 없음 |
| Consistent backlog document hierarchy / Member scans and filters backlog topics | 충족 | 주제·raw slug·참조 문서 검색과 impact/최초 감지 행 위계가 구현되고 기존 `BacklogList.test.tsx`가 검색·정렬·표시를 검증 |
| Consistent backlog document hierarchy / Member operates a backlog row | 충족 | 주제 버튼, 위키 링크, 소스 추가 링크가 별도 상호작용 요소이며 행 전체 클릭 핸들러가 없음. 상세 패널·각 링크 목적지 테스트 통과 |
| Structured Ask answers with dual-citation legend / Resolved answer contains markdown and citations | 충족 | `MarkdownAnswer`가 마커 React 노드를 원위치에 보존하며 구조화 마크다운을 렌더하고 Ask 헤더가 원문/위키 범례를 제공. `MarkdownAnswer.test.tsx`와 기존 Ask 인용 클릭 테스트 통과 |
| Structured Ask answers with dual-citation legend / Answer is still streaming | 충족 | 해소 전 `CitationMarker`는 비상호작용 `<span>` placeholder이고 주변 마크다운은 계속 렌더. `CitationMarker.test.tsx` 및 Ask 상태 기계 테스트 통과 |
| Structured Ask answers with dual-citation legend / Answer contains an unsafe markdown link | 충족 | 공통 URL 허용 목록을 사용하고 위험 링크 라벨만 남김. 안전/위험 URL 테스트 통과 |

## 조치가 필요한 항목

1. **접힌 사이드바의 키보드/계정 제어를 계약대로 복구해야 한다.** `.nav-item`, `.switcher`, 계정 제어가 포커스를 받을 때도 `aria-label`의 전체 라벨이 가시적으로 표시되어야 한다. 현재는 hover에만 의존하며, `.profile .icon-btn`은 접힌 상태에서 완전히 숨겨져 설정 링크가 운용 불가능하다. 포커스 상태와 설정 링크 운용을 실제 키보드 상호작용 테스트로 고정해야 한다.
2. **tasks 3.4가 완료됐다고 볼 수 있도록 목차 회귀 테스트를 추가해야 한다.** 여러 level heading fixture에서 스크롤에 따른 active 항목과 중첩 단서, 항목 클릭의 smooth scroll 및 URL fragment 갱신, heading 없는 문서의 빈 링크/active 부재를 직접 검증해야 한다. 현재 `WikiPageContent.test.tsx:11-40`은 목차에 `개요` 텍스트가 있다는 사실만 확인한다.
3. **source detail 라우트의 격리 회귀 테스트를 강화해야 한다.** 다른 workspace의 같은/유효 source id가 active workspace에서는 일반 not-found가 되고 chunk/wiki 데이터가 전달되지 않는 fixture를 만들고, mock이 모든 `workspace_id` 필터를 기록·검증해야 한다. 현재 mock은 source id만 판정하므로 task 2.3의 “보이지 않는 소스 fixture”를 충족하지 못한다.

## 실행 검증

- `pnpm test -- ...` (`apps/dashboard`): **56개 테스트 파일, 255개 테스트 통과**
- 저장소 루트에는 `package.json`이 없어 최초 `pnpm --filter ...` 시도는 실행되지 않았고, dashboard 패키지 디렉터리에서 다시 실행해 통과 결과를 확인함

## 판정 근거

대부분의 문서 표면, 소스 추적, 안전 URL, WikiLink, Ask 이중 인용, 백로그 독립 액션은 delta spec과 일치한다. 그러나 접힌 사이드바 시나리오는 실제 구현이 키보드 포커스 라벨을 제공하지 않고 계정 설정 링크를 숨기므로 명시적인 사용자 동작을 위반한다. 또한 완료 처리된 목차 및 격리 회귀 task에는 핵심 Given/When/Then을 실행하는 테스트가 없다. 세 항목 모두 사람의 추가 결정 없이 코드·테스트 수정으로 닫을 수 있으므로 `blocked`가 아닌 **needs_fix**로 판정한다.
