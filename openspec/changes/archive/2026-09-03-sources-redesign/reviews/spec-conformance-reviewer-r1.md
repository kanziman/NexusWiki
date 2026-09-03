# Spec Conformance 리뷰 — sources-redesign r1

- 판정: needs_fix
- 대상: 워킹 트리 변경분 (`git diff`, base `0b26b55`, 브랜치 `feat/knowledge-grid-design-polish`)
- 일시: 2026-09-03T00:00:00+09:00
- 검토 파일: `apps/dashboard/components/SourcesList.tsx` · `apps/dashboard/app/w/[workspaceId]/sources/loading.tsx` · `apps/dashboard/tests/LoadingSkeletons.test.tsx` · `docs/design-systems/v2/nexuswiki-design-system.css`

## 시나리오 판정

### MODIFIED: Source library with MIME type filter tabs

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| MIME 탭 필터링 (`Member filters sources by MIME tab`) | 충족 | 필터 계산 `apps/dashboard/components/SourcesList.tsx:190-195`, 탭 렌더 `:406-433` · 테스트 `apps/dashboard/tests/SourcesList.test.tsx:82-118` |
| 탭에 실린 개수 (`Member reads how many sources a filter holds`) | 충족 (단서 있음) | `SourcesList.tsx:202-203`(pdfCount·textMdCount), `:238-242`(`전체 N`·`PDF N`·`텍스트/마크다운 N`). 전부 로드된 `sources`에서 산출 — 스펙의 "counts match the loaded workspace sources"와 일치. 자동 단언은 없음(테스트는 `/PDF/` 정규식으로 이름만 확인) |
| 보조기술 노출 (`Assistive technology user selects a filter`) | 충족 | `role="tablist"` `SourcesList.tsx:408`, `role="tab"` `:415`, `aria-selected` `:416`, 접근 이름은 탭 라벨 텍스트 `:429`. 테스트는 `getByRole("tab", …)`까지만 확인(`SourcesList.test.tsx:107,113`), `aria-selected` 단언은 없음 |
| 툴바 상하 모서리 일치 (요구사항 본문의 SHALL) | 충족 | 탭 컨테이너·각 칩 `h-9`+`box-border` `SourcesList.tsx:407,421`, 검색 래퍼 `h-9` `:434`, `.field.search`가 `height/min-height/max-height: 36px` 고정 `docs/design-systems/v2/nexuswiki-design-system.css:1755-1768`. 900px 이하에서는 `.content.sources .toolbar { flex-direction: column }`(`:1998`)으로 세로 스택 |

### ADDED: Source pipeline summary metrics

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 요약 지표 전반 (`Member opens a source library with processed sources`) | 부분 미충족 | 총 등록 원문·포맷 분해 `SourcesList.tsx:276-295`, 청크 합계 `:298-312`, 인용 연결률 `:315-331`, 청킹 완료 상태 `:334-371`. ⚠️ 청크 합계만 `Object.values(chunkStats)` 전량 합산(`:211-214`)이라 목록 상태(`sources`)와 분리된다 — 아래 「조치 1」 |
| 인용 0건 소스 존재 (`Workspace has sources that no wiki page cites`) | 충족 | `citedCount` `:224-226`, `citationRate` `:229-232`, 표시 `:322-330`(`N/M`, `인용됨 (P%)`, `아직 인용되지 않은 소스 N개`). 인용이 없는 소스가 있으면 분자가 분모보다 작아 100% 미만이 된다 |
| 소스 0건 (`Workspace has no sources yet`) | 충족 | 벤토 전체가 `sources.length > 0` 게이트 안 `:270`, 빈 상태 Dropzone 캔버스 `:457-489` · 테스트 `apps/dashboard/tests/SourcesList.test.tsx:19-32` |
| 색만으로 전달하지 않을 것 (요구사항 본문의 SHALL) | 충족 | 파이프라인 칸이 `전 소스 청킹 완료` / `청킹 진행 중` 문구와 `청킹 대기 N개`를 함께 둔다 `:356-371`. 아이콘 색은 보조 신호일 뿐 `:342-350` |

### ADDED: Uniform source list rows independent of citation count

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 인용 다수 행의 상한과 잔여 표시 (`Member views a source cited by many wiki pages`) | 충족 | 상한 2개 `SourcesList.tsx:528-529`, 칩 렌더 `:580-589`, `+N개 더` `:590-594`, 한 줄 고정 `overflow-hidden whitespace-nowrap` `:579`, 행 높이 고정 `md:h-[72px]` `:534`. 인용 0건 문구 `:574-577`. 자동 단언 없음 |
| 헤더-값 컬럼 축 일치 (`Member scans the list header against a row`) | 충족 | 컬럼 정의를 컨테이너 CSS 변수 `--sources-cols`에 한 번만 선언 `:496-505`, 헤더가 참조 `:510`, 데이터 행이 참조 `:534`. 헤더 `청크 및 좌표`/`작업`의 `text-right`(`:513,516`)에 행의 `md:text-right`(`:600`)·`md:justify-end`(`:628`)가 대응 |
| 좁은 뷰포트 리플로 (`Member opens the source library on a narrow viewport`) | 충족 | md 미만 `grid-cols-1` `:534`(md 이상에서만 5열), 헤더는 `hidden … md:grid` `:508`, 래퍼 `overflow-hidden` `:497`, 컬럼 트랙 전부 `minmax(0, …)` `:502-503`이라 콘텐츠가 트랙을 밀지 못한다. 900px 이하 CSS는 툴바를 세로로 스택 `nexuswiki-design-system.css:1998` |

### ADDED: Source row identity and upload recency

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 행의 출처 정보 (`Member scans a source row for provenance`) | 충족 | 포맷 배지 `SourcesList.tsx:538-540`(`.format` 규칙 `nexuswiki-design-system.css:1798-1835`), 제목 링크 `:542-554`(`title`/`aria-label` 유지), 크기 `:557-562`, 수집 유형 `:563`, 상대 시각 `:565`, 절대 일자 `:567` · 테스트 `SourcesList.test.tsx:52-59`(제목 접근성·상세 라우트·`2026년 8월 12일`) |
| 크기 미기록 (`Source has no recorded size`) | 충족 | `formatBytes`가 `null` 반환 `:58-60`, 렌더는 `{size && …}` 조건부이며 구분점 `·`도 조건 블록 안 `:557-562` — 자리표시자 없이 생략되고 나머지 필드는 유지 |

### 회귀 보존 확인 (tasks 3.4 · 3.5 · 4.x)

| 항목 | 결과 | 증거 |
| --- | --- | --- |
| `data-od-id="source-table-section"` · `pipeline-stats` | 유지 | `:398`, `:274` |
| `JobStepper` 폴링 · `상세 보기` 링크 · `isOwner` 게이트 · 삭제 testid · 8개 페이지네이션 | 유지 | `:621-624`, `:629-636`, `:637-650`(`delete-source-btn-<id>` `:644`), `:768`, `PAGE_SIZE = 8` `:174` |
| 로딩 스켈레톤 골격 | 충족 | `loading.tsx:23-38`(벤토 4칸), `:55-117`(같은 `--sources-cols` 5열), `data-testid="sources-loading-skeleton"`·`aria-busy` 유지 `:5-9` · 테스트 `tests/LoadingSkeletons.test.tsx:37-51` |
| v2 CSS 주석 (task 4.3) | 충족 | `nexuswiki-design-system.css:1692-1720`(사용처 현황·미삭제 사유), `:1724`, `:1737-1739` — 규칙 삭제 없음 |
| 검증 재실행 (task 4.2) | 재현 확인 | `vitest run` 384 pass / 0 fail, `tsc --noEmit` 무오류, `eslint .`(next lint) 무경고, `openspec validate sources-redesign --strict` valid |

## 조치가 필요한 항목

1. **`생성된 청크` 지표가 목록과 어긋날 수 있다** — `totalChunks`가 `Object.values(chunkStats)`를 전량 합산한다(`apps/dashboard/components/SourcesList.tsx:211-214`). `chunkStats`는 서버 props로 고정인 반면 목록은 `sources` 로컬 state를 렌더하고, 삭제 성공 시 `setSources`로 행만 제거된다(`:147-160`). 그래서 소스를 삭제하면 `총 등록 원문`·`위키 인용 연결률`·`N/M 소스 청킹 완료`는 줄어드는데 `생성된 청크`만 삭제된 소스의 청크를 계속 포함한 값으로 남아, 새로고침 전까지 아래 행들과 모순된다.
   근거 Scenario/SHALL: "Each summary figure SHALL be derived from the same workspace data the list itself renders, so that a figure never contradicts the rows below it."
   제안: 합계를 목록과 같은 원천에서 뽑는다 — `sources.reduce((sum, s) => sum + (chunkStats[s.id]?.count ?? 0), 0)`. 다른 세 지표(`indexedCount` `:215-217`, `citedCount` `:224-226`)는 이미 `sources`를 순회하므로 이 한 곳만 맞추면 된다. `design.md` D-4가 인정한 "업로드 직후 새 소스는 분자에 없다"는 별개의 의도된 동작이며 이 수정과 충돌하지 않는다.

2. **ADDED 3개 요구사항의 시나리오가 자동 검증 없이 `- [x]`로 완료 주장됐다** — `tasks.md` 1.1·1.2·3.2·3.3이 각각 Given/When/Then을 달고 체크됐지만, `apps/dashboard/tests/SourcesList.test.tsx`는 `chunkStats`·`citingPages`를 한 번도 넘기지 않고(`:20,38-49,63-75,83-100,121-128`) 벤토 수치·인용 칩 상한·`+N개 더`·크기 생략을 단언하지 않는다. 이번 라운드에 추가된 단언은 로딩 스켈레톤 골격뿐이다(`tests/LoadingSkeletons.test.tsx:37-51`). task 4.1이 테스트 범위를 "깨진 단언만 최소 범위로 수정"으로 잡았더라도, 새로 추가된 요구사항의 관찰 가능한 동작은 회귀 그물 없이 남는다 — 실제로 조치 1의 모순은 벤토 수치 테스트가 있었다면 잡혔을 종류다.
   근거 Scenario: "Workspace has sources that no wiki page cites → the citation summary reports a proportion below full", "Member views a source cited by many wiki pages → the row shows a bounded number of citation links plus a remainder indicator", "Source has no recorded byte size → the row omits the size without displaying a placeholder value".
   제안: `SourcesList.test.tsx`에 (a) 소스 3건 중 1건만 인용된 fixture로 `3` 중 인용 `1/3`·연결률 33%·`아직 인용되지 않은 소스 2개`가 나오는지, (b) 인용 5건 소스에서 칩 2개 + `+3개 더`가 나오는지, (c) `byte_size` 없는 행에 `KB`/`MB`/자리표시자가 없는지 세 케이스를 추가한다. (a)를 삭제 흐름과 엮으면 조치 1의 회귀도 함께 막힌다.

## 관찰 사항 (판정에 반영하지 않음)

- **탭 개수와 검색어의 상호작용**: 탭 라벨의 개수는 `sources` 전체에서 산출하므로(`:238-242`), 검색어가 걸린 상태에서 `전체 12`를 보면서 실제로는 2행만 보이는 조합이 가능하다. 스펙의 두 번째 절("counts match the loaded workspace sources")을 정본으로 읽으면 현재 구현이 맞고, 첫 절("the number of sources that filter would display")만 읽으면 어긋난다. 다음 스펙 개정에서 문구를 하나로 좁히면 좋다.
- **`목록 50건 상한`**: `page.tsx:9,35`가 소스를 50건으로 자르므로, 51건 이상인 워크스페이스에서 `총 등록 원문`은 등록 총량이 아니라 로드된 건수를 보고한다. 스펙이 "the same workspace data the list itself renders"로 못박았으므로 현재 구현과 모순되지 않지만, 표현("총 등록 원문")과 실제 의미의 간극은 남는다.
- **아주 좁은 폭에서 탭 줄바꿈**: 필터 nav가 `h-9`(고정 높이) + `flex-wrap`이다(`:407`). 새 마크업은 `.content.sources .tabs`를 쓰지 않으므로 640px 이하에서 `flex-wrap: nowrap; overflow-x: auto`로 보호하던 옛 규칙(`nexuswiki-design-system.css:2049-2055`)이 더 이상 걸리지 않는다. 폭 320px 안팎에서 칩이 두 줄로 감기면 36px 상자 밖으로 넘쳐 아래 검색창과 겹칠 수 있다. 가로 스크롤을 만들지는 않아 스펙 시나리오를 깨지는 않지만, `h-9` 대신 `min-h-9`(정렬은 `md:h-9`로 유지)로 두면 안전하다.
- **`tasks.md` 4.4(동기화·아카이브)는 미체크 상태**다. 리뷰 게이트 이후 절차이므로 이번 판정 대상이 아니다.

## 판정 근거

delta spec의 11개 시나리오/SHALL 중 10개는 코드에 근거가 명확하고, 회귀 셀렉터·권한 게이트·페이지네이션·스켈레톤 계약도 모두 보존됐으며 전체 검증(테스트 384건·typecheck·lint·strict validate)을 이 리뷰에서 새로 돌려 통과를 확인했다. 다만 "Source pipeline summary metrics"가 요구한 "요약 수치가 아래 행들과 결코 모순되지 않을 것"이 삭제 경로에서 깨진다 — 청크 합계만 목록 state가 아닌 서버 props 맵 전체에서 나오기 때문이다. 이는 스펙을 고칠 필요 없이 한 줄짜리 산출식 교체로 해결되는 코드 문제이고, 같은 요구사항에 대한 자동 검증이 하나도 없어 이 종류의 어긋남이 다시 들어와도 그물에 걸리지 않는다. 스펙 자체는 모호하지 않고 구현도 스펙 범위를 벗어나지 않으므로 `blocked`이 아니라 `needs_fix`다.
