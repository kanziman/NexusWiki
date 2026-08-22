# Spec Conformance 리뷰 — redesign-dashboard-knowledge-surfaces r2

- 판정: **pass**
- 대상: r1 지적 수정, 추가된 운영 오류 시나리오, 아카이브된 delta spec과 현재 구현·테스트
- 일시: 2026-08-22T19:28:00+09:00

## r1 지적 종결 확인

| # | r1 지적 | 상태 | 증거 |
| --- | --- | --- | --- |
| 1 | 접힌 사이드바의 포커스 라벨·계정 설정 제어 미충족 | **닫힘** | 내비와 워크스페이스 스위처가 `:focus-visible`에서도 `aria-label` 기반 라벨을 표시하고, 계정 설정 링크도 접힌 상태에서 `inline-flex`로 유지된다(`nexuswiki-design-system.css:317-354`). `WorkspaceSidebar.test.tsx:136-159`가 접힌 상태에서 홈·설정·스위처를 실제 focus하고 설정 링크 목적지를 검증한다 |
| 2 | 목차 active/중첩/smooth scroll/fragment/no-heading 테스트 부재 | **닫힘** | `WikiPageContent.test.tsx:148-207`이 heading level별 들여쓰기, 최초 active, scroll 후 active 전환, `scrollIntoView({ behavior: "smooth" })`, `history.pushState(..., "#section-2")`를 검증한다. `:209-233`은 heading 없는 문서에 링크가 없음을 검증한다 |
| 3 | source detail mock이 workspace 격리를 증명하지 못함 | **닫힘** | mock이 세 테이블의 `workspace_id`와 chunk의 `raw_source_id` 호출을 기록·판정한다(`source-detail-route.test.tsx:38-88`). `:103-140`에서 전 쿼리 scope를 단언하고, `:143-154`에서 unknown id와 다른 workspace가 동일 not-found를 반환함을 검증한다 |

## 추가 계약 검토

### Source detail query fails

- **구현 충족**: source 조회는 `maybeSingle()`을 사용해 성공적 무행과 운영 오류를 분리한다. source 오류 또는 chunk/wiki 오류이면 관련 데이터를 빈 배열로 가장하지 않고 `role="alert"`의 일반 로드 실패 문구를 반환한다(`sources/[id]/page.tsx:27-79`). unknown/inaccessible source의 성공적 무행은 기존 일반 not-found를 유지한다.
- **테스트 충족**: `source-detail-route.test.tsx:156-176`이 source/chunks/wiki 세 오류 분기를 각각 주입하고 동일 일반 실패 문구 및 오류 기록을 검증한다.
- **정본 동기화 충족**: 아카이브 delta와 `openspec/specs/source-management-wiki/spec.md`에 같은 Requirement/Scenario가 반영되어 있다. 본문 대조 결과 차이는 선행 빈 줄 하나뿐이다.

## 전체 delta scenario 재판정

| Capability | 결과 | r2 핵심 증거 |
| --- | --- | --- |
| `dashboard-design-consistency` 3개 시나리오 | **전부 충족** | r1의 유일한 실제 위반이었던 collapsed focus/account 경로가 CSS와 키보드 테스트로 닫힘. Dropzone 파일/URL/텍스트·파일별 상태 테스트 유지 |
| `library-selection-layout` 3개 시나리오 | **전부 충족** | source identity/processing/full text/chunks/citing wiki, chunk 선택·좌표·복사, 각 빈 상태 구현과 컴포넌트 테스트 유지 |
| `source-management-wiki` 4개 시나리오 | **전부 충족** | 요청자 client와 세 쿼리 workspace scope, inaccessible=unknown not-found, 성공적 빈 collection, 운영 오류=load failure가 각각 분리됨 |
| `wiki-library-navigation` 5개 시나리오 | **전부 충족** | 표시/검색 공용 평문 발췌, 구조적 read-only markdown, WikiLink, unsafe URL 비활성화 구현·테스트 유지 |
| `wiki-page-routing` 3개 시나리오 | **전부 충족** | heading 위계·scroll active·smooth 이동·fragment·no-heading이 구현뿐 아니라 r2 테스트에서 직접 실행됨 |
| `backlog-ask` 5개 시나리오 | **전부 충족** | 백로그 검색/독립 row action, Ask 구조적 markdown·원위치 citation·placeholder·이중 범례·unsafe URL 테스트 유지 |

## 실행 검증

- `pnpm test -- ...` (`apps/dashboard`): **56개 테스트 파일, 262개 테스트 통과**
- `openspec validate --specs --strict`: **32개 spec 통과, 0개 실패**

## 조치가 필요한 항목

없음.

## 판정 근거

r1에서 확인한 실제 계약 위반 한 건과 회귀 증거 공백 두 건이 모두 사람의 추가 결정 없이 구현·테스트로 닫혔다. 접힌 사이드바는 포인터뿐 아니라 키보드 포커스에서도 전체 라벨을 제공하고 계정 설정 제어가 남는다. 목차의 세 Given/When/Then은 active 경계, 위계, smooth scroll, URL fragment, no-heading 상태까지 테스트가 실행한다. source detail은 모든 관련 쿼리의 workspace scope와 교차 workspace not-found를 mock 수준에서 증명한다.

r1 이후 추가된 operational error 시나리오도 성공적 무행과 오류를 `maybeSingle`/error 분기로 명시적으로 구분하고 세 쿼리 오류 테스트를 갖추었으며 main spec에 동기화됐다. 따라서 delta spec의 모든 시나리오가 실제 구현과 테스트에 대응하고 미충족 항목이 없어 **pass**로 판정한다.
