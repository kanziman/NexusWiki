# Spec Conformance 리뷰 — workspace-home-redesign + wiki-library-redesign r1

- 판정: pass
- 대상 change (2건, 하나의 PR로 함께 나감)
  - `openspec/changes/archive/2026-09-02-workspace-home-redesign/` — delta spec `specs/workspace-home-dashboard/spec.md`
  - `openspec/changes/archive/2026-09-02-wiki-library-redesign/` — delta spec `specs/wiki-library-navigation/spec.md`
- 대상 코드: 워킹트리 변경분 (`git diff` + untracked, base 커밋 `2f64376`)
- 일시: 2026-09-02T06:38:20Z
- 새로 실행한 검증
  - `npx vitest run` (apps/dashboard): 366 passed / 0 failed
  - `npx tsc --noEmit` (apps/dashboard): No errors found
  - `npx eslint .` (apps/dashboard): No issues found
  - `npx openspec validate --specs --strict`: 34 passed / 0 failed (동기화된 정본 `workspace-home-dashboard`, `wiki-library-navigation` 포함)

## 시나리오 판정 — workspace-home-dashboard (MODIFIED)

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Workspace-scoped home overview / Returning member opens home | 충족 | `h1` 고정 문자열 `홈 대시보드` — `apps/dashboard/app/w/[workspaceId]/page.tsx:291` · 테스트 `apps/dashboard/tests/workspace-home.test.tsx:90`. URL 스코프 액션: 소스 추가 `apps/dashboard/components/KnowledgeGrid.tsx:210-216`·`:228-235`, 위키 탐색 `KnowledgeGrid.tsx:81-87`, 질문 `apps/dashboard/components/AskHero.tsx:80` (`${base}/ask`). 모든 조회는 `workspace_id` 스코프 — `page.tsx:125-156` |
| 〃 (`workspaces` 조회 금지 조항) | 충족 | `Promise.all` 안에 `raw_sources`·`wiki_pages`·`wiki_links`·`source_chunks` 넷뿐이고 `workspaces` 조회 없음 — `page.tsx:125-156`, 이유 주석 `page.tsx:122-124` |
| 〃 (지식 완결도 지표 + 요약 문장) | 충족 | 완결도 뱃지 `page.tsx:292-297`(값은 `isVerified` 기반 `page.tsx:271-276`), 요약 문장 `page.tsx:299-302` · 테스트 `workspace-home.test.tsx:91-95`, `:145` |
| Workspace-scoped home overview / Member reads knowledge-health metrics | 충족 | 벤토 4칸 — 컴파일된 위키+검증률 `page.tsx:313-321`, 원문 수+인덱싱 청크 `page.tsx:322-330`(청크 조회 `page.tsx:152-155`, 집계 `page.tsx:269`), 백로그 `page.tsx:331-341`, 최종 업데이트(서버 렌더 스냅샷) `page.tsx:342-346`. "라이브" 표현 없음 — 주석 `page.tsx:306-307` · 테스트 `workspace-home.test.tsx:96-101`(`queryByText(/라이브/)`가 null), `:139-142`, `chunkWorkspaceId === "ws-1"` 단언 `:107`·`:144` |
| Ask hero canvas / User enters question via chips | 충족 | 칩 클릭이 입력을 채우고 포커스까지 옮김 — `AskHero.tsx:61-67`, 렌더 `AskHero.tsx:166-177` · 테스트 `apps/dashboard/tests/AskHero.test.tsx`("populates textarea and focuses it when a starter chip is clicked", `toHaveFocus` 포함) |
| Ask hero canvas / User submits question with scope | 충족 | `AskHero.tsx:69-81`(scope가 기본값이 아니면 `scope` 파라미터 부가), `⌘/Ctrl+Enter` `AskHero.tsx:83-88` · 테스트 `AskHero.test.tsx` "submits question and navigates to /ask route" + 신규 "⌘/Ctrl + Enter 로 질문을 제출한다" |
| Ask hero canvas / Chips reflect the active workspace | 충족 | 서버에서 `sources` 배열 길이로 상위 4개 산출 — `page.tsx:31-48`(`SUGGESTED_CHIP_LIMIT = 4`), 인용 수 계산 `page.tsx:181`, 주입 `page.tsx:350` · 테스트 `workspace-home.test.tsx` "추천 칩은 인용 빈도 상위 4개 위키 제목이며 하드코딩 질문을 쓰지 않는다"(5위 제외, 하드코딩 칩 부재 단언) |
| Ask hero canvas / Workspace has no wiki pages to suggest | 충족 | `DEFAULT_CHIPS` 제거, 기본값 `defaultChips = []` — `AskHero.tsx:32-34`; 입력·스코프·제출은 칩과 무관하게 렌더 `AskHero.tsx:99-163` · 테스트 `AskHero.test.tsx:19-33`(하드코딩 칩 3종 부재), `workspace-home.test.tsx:104-107`(빈 워크스페이스). 코드베이스 전체에 `DEFAULT_CHIPS` 잔존 없음(grep: 테스트 픽스처 문자열만 존재) |
| Two-column knowledge grid / Populated wiki and backlog display | 충족 | 비대칭 그리드 `docs/design-systems/v2/nexuswiki-design-system.css:996-1002` (`minmax(0,1.4fr) minmax(0,1fr)`, `apps/dashboard/app/globals.css:3`에서 임포트되어 앱에 실제 적용). 상한 `KnowledgeGrid.tsx:53-54`·`:69-70`, 카테고리·검증·인용 뱃지 `KnowledgeGrid.tsx:133-143`, 백로그 인용 수 `KnowledgeGrid.tsx:206-208` · 테스트 `apps/dashboard/tests/KnowledgeGrid.test.tsx:137-173`(10/8 상한), `:41-47` |
| 〃 (카테고리 라벨 매핑) | 충족 | `KnowledgeGrid.tsx:46-51` (`entities: "엔티티"`) · 테스트 `KnowledgeGrid.test.tsx:41` |
| Two-column knowledge grid / Empty state display | 충족 | `KnowledgeGrid.tsx:91-96`, `:176-179`, 소스 연결 콜아웃 `:223-236` · 테스트 `KnowledgeGrid.test.tsx:124` |
| Two-column knowledge grid / Member follows a backlog source-connection CTA | 충족 | `KnowledgeGrid.tsx:210-216` — `${base}/sources?prefillTitle=<encoded>&tab=text`, 라벨 `소스 추가`(design.md D-6/Resolved Q2 준수) · 테스트 `KnowledgeGrid.test.tsx:50-56`, `:97-107`(모달 경로), `workspace-home.test.tsx:146-149` |

## 시나리오 판정 — wiki-library-navigation (ADDED + MODIFIED)

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Floating bulk action bar / Authorized member selects library pages | 충족 | 플로팅 바 `apps/dashboard/components/WikiLibrary.tsx:722-771` (`fixed bottom-6 left-1/2 z-40`, `data-testid="bulk-action-bar"`), 노출 조건 `WikiLibrary.tsx:374`. `fixed`라 문서 흐름 밖이므로 목록을 아래로 밀지 않고, 하단 가림 방지는 `.content.library.has-floating-bulk { padding-bottom: 120px }` — `nexuswiki-design-system.css:3488`, `:3543`, `:3549` (적용 `WikiLibrary.tsx:378`). `bulk-verify-btn` `:748`, `bulk-publish-btn` `:762` · 테스트 `apps/dashboard/tests/WikiBulkActions.test.tsx`(바 안에 두 버튼이 있고 `select-all-checkbox`는 없음을 `not.toContainElement`로 단언) |
| 〃 (전체 선택은 리스트 컨트롤 행에 잔류) | 충족 | 전체 선택 체크박스가 카드 리스트(`:588`) 위 서브 컨트롤 행 `WikiLibrary.tsx:558-586`에 남음, `data-testid="select-all-checkbox"` `:573` · 테스트 `WikiBulkActions.test.tsx`의 `expect(bulkBar).not.toContainElement(selectAllCheckbox)`, `WikiDeletion.test.tsx:111`(존재 확인) |
| Floating bulk action bar / Member without verification permission views the library | 충족 | 전체 선택 게이트 `WikiLibrary.tsx:558`, 행 체크박스 게이트 `WikiLibrary.tsx:604-620`, 플로팅 바 게이트 `WikiLibrary.tsx:374`(`canVerify && selectedIds.size > 0`) · 테스트 `WikiBulkActions.test.tsx:37-48`(select-all·행 체크박스 2종·바·검증/발행 버튼 모두 부재 단언) |
| 〃 (오너 전용 삭제 게이트) | 충족 | 삭제 버튼 `WikiLibrary.tsx:664-680`(`isOwner &&`), 핸들러 재확인 `WikiLibrary.tsx:113`(`if (!deleteTarget \|\| deleting \|\| !isOwner) return`) · 테스트 `apps/dashboard/tests/WikiDeletion.test.tsx` |
| Floating bulk action bar / Member clears the current selection | 충족 | `선택 해제` 버튼 `WikiLibrary.tsx:732-738`(`setSelectedIds(new Set())` → `showFloatingBulk` false) · 테스트 `WikiBulkActions.test.tsx` "선택 해제를 누르면 선택이 비고 플로팅 바가 사라진다" |
| Searchable wiki library / Member finds a page by title or preview text | 충족 | 대소문자 무시 필터 `WikiLibrary.tsx:219-229`(제목 + `cleanExcerpt` 본문, `toLocaleLowerCase`), 검색 입력 `:528-537`, 지우기 `:538-550`, 상세 링크 유지 `:622-626` · 테스트 `apps/dashboard/tests/WikiLibrary.test.tsx:30-50`, `:85-111` |
| Searchable wiki library / Member filters the library by category | 충족 | 칩에 개수 표시 + `aria-pressed` — `WikiLibrary.tsx:491-519` · 테스트 `WikiLibrary.test.tsx:40-50`(`{ name: "개념 1" }`, `aria-pressed="true"`) |
| Searchable wiki library / Search has no matching pages | 충족 | `NO_MATCH_BODY` `WikiLibrary.tsx:52`, 렌더 분기 `:705-716`(빈 워크스페이스 문구와 구분) · 테스트 `WikiLibrary.test.tsx:75` |
| Searchable wiki library / Member reads library knowledge-health counts | 충족 | 총 문서 수 뱃지 `WikiLibrary.tsx:317-319`, 검증률(`isVerified`만 사용) `:240-241` + 벤토 `:334-425`, 카테고리별 수 `:244-257`·`:427-457` · 테스트 `WikiLibrary.test.tsx:139-157`(50%, 1/2 검증됨, 전체·4카테고리 개수), `:201-`(충돌·만료를 검증으로 세지 않음) |
| Searchable wiki library / Member filters from the category summary | 충족 | 벤토 카테고리 칸이 칩과 동일한 `applyCategoryFilter`를 호출 — `WikiLibrary.tsx:431-455`, 공유 상태 `:263-266` · 테스트 `WikiLibrary.test.tsx:159-173`(벤토 클릭 후 칩 `aria-pressed=true`) |
| 〃 (카테고리 라벨 홈과 통일) | 충족 | `WikiLibrary.tsx:60-65` — `entities: "엔티티"`(기존 `"항목"` 제거), 근거 주석 `:58-59`. CSS 주석도 `엔티티`로 갱신 `nexuswiki-design-system.css:3496` · 테스트 `WikiLibrary.test.tsx:175-199`(행 텍스트에 `엔티티` 포함, `항목` 미포함) |
| 〃 (행별 인용 수) | 충족 | 인덱스 조회 컬럼에 `sources` 추가 — `apps/dashboard/app/w/[workspaceId]/wiki/page.tsx:37-38`(즐겨찾기 분기와 전체 조회가 같은 `pageColumns` 사용 `:66`, `:75`), 길이 계산 `WikiLibrary.tsx:100-102`, 행 표시 `:648-651` · 테스트 `apps/dashboard/tests/wiki-index-route.test.tsx`(select 문자열에 `sources`·`expires_at` 포함 단언), `WikiLibrary.test.tsx:175-199`(`인용 3개`) |
| Clean wiki library previews / Library page contains rich markdown | 충족 | `cleanExcerpt` `WikiLibrary.tsx:81-98`(WikiLink·코드·헤딩·강조·리스트·테이블 제거 후 160자 절단) · 테스트 `WikiLibrary.test.tsx:85-111`(`[[` 미노출) |
| Clean wiki library previews / Member searches cleaned content | 충족 | 검색 대상이 같은 `cleanExcerpt` 결과 — `WikiLibrary.tsx:219-229` · 테스트 `WikiLibrary.test.tsx:102-111` |
| Clean wiki library previews / Library excerpt stays readable on a wide viewport | 충족 | 카드 표면 `WikiLibrary.tsx:596-603`, 발췌 `:658` — `line-clamp-2 max-w-3xl` · 테스트 `WikiLibrary.test.tsx:96-101`(`toHaveClass("line-clamp-2", "max-w-3xl")`) |

## 부수 task 판정 (tasks.md 완료 주장 대조)

| Task | 결과 | 증거 |
| --- | --- | --- |
| home 2.1 `--warning` 토큰 + "안 그러면 뭐가 깨지는지" 주석 | 충족 | `nexuswiki-design-system.css:56-60`(주석 + `--warning: oklch(.68 .15 75)`), 사용처 `:1062-1067`(백로그 좌측 보더), `page.tsx:53`·`:59`. 레거시 `--color-warning-text` 재사용 없음 |
| home 5.1 홈 로딩 스켈레톤 정합 | 충족 | `apps/dashboard/app/w/[workspaceId]/loading.tsx:29-52`(벤토 4칸), `:72-131`(`.sections` 2열), 이유 주석 `:10-12`·`:27-28`·`:70-71` · 테스트 `apps/dashboard/tests/LoadingSkeletons.test.tsx`("홈 스켈레톤은 벤토 메트릭 4칸과 비대칭 지식 그리드 골격을 쓴다", 옛 `.stats` 부재 단언) |
| home 5.2 `PreviewWorkspace`의 `.sections` 공유 | 충족 | `apps/dashboard/components/PreviewWorkspace.tsx:244-250`(공유 유지 이유 주석, 클래스 포크 없음) · 테스트 `apps/dashboard/tests/PreviewWorkspace.test.tsx`("미리보기 홈은 실제 홈과 같은 .sections 그리드를 공유한다") |
| library (파급) 위키 라이브러리 로딩 스켈레톤 | 충족 | `apps/dashboard/app/w/[workspaceId]/wiki/loading.tsx:28-43`(벤토 5칸), `:62-83`(`.wiki-card` 카드 행) · 테스트 `LoadingSkeletons.test.tsx`("위키 라이브러리 스켈레톤은 벤토 5칸과 카드 행 골격을 쓴다") |
| 양 change 검증·아카이브 task | 충족 | 정본 동기화 반영됨 — `openspec/specs/workspace-home-dashboard/spec.md`, `openspec/specs/wiki-library-navigation/spec.md` 갱신분이 delta spec 문장과 일치. `openspec validate --specs --strict` 34/34 통과 |

## 조치가 필요한 항목

미충족 시나리오는 없다. 아래는 **커밋 범위**에 관한 확인 요청이며, 그대로 PR에 실리면 두 change의 선언 범위를 벗어난다.

1. **`apps/dashboard/public/`에 리디자인 프리뷰 HTML 2종이 untracked로 존재** — `apps/dashboard/public/redesign-preview.html`, `apps/dashboard/public/wiki-library-preview.html`. 두 proposal의 Impact 목록에 없고, 이 저장소의 프로토타입은 모두 `docs/design-systems/*.html`에 있다(현재 `docs/design-systems/dashboard-redesign-preview.html`은 95바이트 포인터 주석뿐이다). `public/`에 두면 `/redesign-preview.html`·`/wiki-library-preview.html`이 인증 없이 서비스되는 **스펙에 없는 사용자 관찰 가능 표면**이 된다. 게다가 두 파일 모두 `<html class="dark">`로, 두 change design.md의 D-1(단일 테마)과 방향이 반대다. 제안: PR 커밋에서 제외하거나 `docs/design-systems/`로 옮긴다.
2. **`supabase/migrations/0020_workspace_byok_api_key.sql`가 untracked** — 이미 커밋된 `0021_source_deletion_integrity.sql`보다 앞선 번호다. 두 proposal 모두 "마이그레이션 변경 없음"을 선언했고, 이 파일은 두 delta spec 어디에도 대응 요구사항이 없다. 그대로 커밋되면 CLAUDE.md의 마이그레이션 번호 순서 규칙(로컬·클라우드 적용 순서 불일치)까지 함께 걸린다. 제안: 이 PR의 커밋 범위에서 제외하고 별도 change로 다룬다.

## 관찰 (판정에 영향 없음)

- **인용 수 0인 위키는 칩 후보에서 아예 제외된다** — `page.tsx:40`의 `filter(citation_count > 0)`. 스펙은 "citation frequency로 랭크"만 요구하고 칩 존재를 보장하지 않으며, 인용 원문이 없는 문서를 추천하면 이중 Citation이 비는 답이 나오므로 합리적 좁힘으로 본다. 다만 "위키는 있는데 `sources`가 비어 있는 워크스페이스"는 어느 시나리오도 다루지 않는다 — 다음 스펙 개정에서 문장 하나로 못 박아 두면 좋다.
- **"browse wiki content" 링크에 직접 단언하는 테스트가 없다** — 코드는 `KnowledgeGrid.tsx:81-87`(`${base}/wiki`)에 있고 시나리오는 충족되지만, `소스 추가`/`소스 연결`과 달리 href 단언이 없다. 회귀 방지 관점에서만 아쉬운 지점이다.
- 플로팅 바의 "목록을 밀어내지 않는다"는 jsdom에서 레이아웃으로 검증할 수 없어 `fixed` 클래스와 `has-floating-bulk` 패딩 선언을 증거로 삼았다. 테스트는 구조(바 안에 전체 선택 체크박스가 없음)로 대리 검증한다.

## 판정 근거

두 delta spec의 모든 Requirement와 그 아래 시나리오가 파일·행 단위 증거와 대응 테스트를 갖췄다. 특히 논쟁 지점 5종 — (1) `h1` 고정 `홈 대시보드`와 `workspaces` 조회 부재 및 시스템 수준의 URL 스코프 링크 3종, (2) `DEFAULT_CHIPS` 제거와 `sources` 길이 기준 상위 4개 칩 및 위키 없는 경우, (3) `entities → 엔티티` 통일과 백로그 CTA의 `prefillTitle`+`tab=text`, (4) 플로팅 바의 비밀림·전체 선택 잔류·`canVerify` 미보유 멤버의 선택 컨트롤 부재·`isOwner` 삭제 게이트, (5) 검증률·카테고리별 수·인용 수 표시와 2줄 클램프(`line-clamp-2 max-w-3xl`) — 이 전부가 구현과 테스트 양쪽에서 확인된다. 조용한 범위 축소나 미검증 완료 주장은 발견되지 않았고, 테스트·타입체크·린트·strict spec validation을 이 리뷰에서 새로 실행해 모두 통과했다. 따라서 `pass`다. 다만 위 「조치가 필요한 항목」 2건은 스펙 밖 산출물이므로, 그대로 커밋에 포함된다면 판정은 `needs_fix`로 바뀐다.
