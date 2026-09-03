# Spec Conformance 리뷰 — sources-redesign r2

- 판정: pass
- 대상: 워킹 트리 변경분 (base `0b26b55`, 브랜치 `feat/knowledge-grid-design-polish`)
- 일시: 2026-09-03T10:35:11+09:00
- 검토 파일: `apps/dashboard/components/SourcesList.tsx` · `apps/dashboard/app/w/[workspaceId]/sources/page.tsx` · `apps/dashboard/app/w/[workspaceId]/sources/loading.tsx` · `apps/dashboard/tests/SourcesList.test.tsx` · `apps/dashboard/tests/LoadingSkeletons.test.tsx` · `docs/design-systems/v2/nexuswiki-design-system.css`
- 판정 기준: `openspec/changes/sources-redesign/specs/source-management-wiki/spec.md` (MODIFIED 1건 + ADDED 3건, **시나리오 12개**)

## 시나리오 판정

### MODIFIED: Source library with MIME type filter tabs

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| `Member filters sources by MIME tab` | 충족 | 필터 계산 `SourcesList.tsx:208-212`, 탭 렌더 `:451-469` · 테스트 `SourcesList.test.tsx:82-118` |
| `Member reads how many sources a filter holds` | 충족 | 개수 산출 `SourcesList.tsx:219-220`, 탭 라벨 `전체 N`·`PDF N`·`텍스트/마크다운 N` `:252-256`. 전부 로드된 `sources`에서 파생 — 스펙의 "counts match the loaded workspace sources"와 일치. r1 대비 변경 없음 |
| `Assistive technology user selects a filter` | 충족 | `role="tablist"` `:448`, `role="tab"` `:455`, `aria-selected` `:456`, 접근 이름은 탭 라벨 `:467` · 테스트가 `getByRole("tab", …)`로 탭 시맨틱만 확인 `SourcesList.test.tsx:107,113` |
| 툴바 상하 모서리 일치 (요구사항 본문 SHALL) | 충족 | 탭 컨테이너·칩 `h-9`+`box-border` `:447,461`, 검색 래퍼 `h-9` `:474`, `.field.search` 36px 고정 `nexuswiki-design-system.css:1755-1768`. 900px 이하 툴바 세로 스택 `:1998` |

### ADDED: Source pipeline summary metrics

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| `Member opens a source library with processed sources` | **충족 (r1 미충족 → 해소)** | 총 등록 원문·포맷 분해 `SourcesList.tsx:291-310`, 청크 합계 `:313-335`, 인용 연결률 `:338-364`, 청킹 완료 상태 `:369-411`. 네 지표 모두 목록이 렌더하는 `sources` state에서 파생된다 — 청크 합계가 `sources.reduce(...(chunkStats[source.id]?.count ?? 0))` `:225-228`로 교체됐고, `Object.values(chunkStats)` 전량 합산은 코드에서 완전히 사라졌다(파일 내 유일한 등장은 금지 이유를 적은 주석 `:221`) · 테스트 `SourcesList.test.tsx:149-173`(네 지표 값 대조), `:175-193`(목록에 없는 `deleted-source`의 청크 99가 합계에 섞이지 않음 — r1 조치 1의 회귀 그물) |
| `Workspace has sources that no wiki page cites` | 충족 | `citedCount` `:238-240`, `orphanCount` `:241`, `citationRate` `:243-246`, 표시 `:349-361` · 테스트 `SourcesList.test.tsx:166-169`(`인용됨 (50%)` · `아직 인용되지 않은 소스 1개`) |
| `A summary aggregate query fails` (신규) | 충족 | 서버가 `error`를 빈 결과와 구분해 내려보냄 `page.tsx:82-93,137-138`, 인용 지표 칸이 단정 대신 `집계를 불러오지 못했습니다` `SourcesList.tsx:343-346`(문구 상수 `:61`), 모든 행의 인용 값이 `인용 정보를 불러오지 못했습니다` `:614-617`(`인용한 위키 없음` 단정보다 앞선 분기), 실패 집계에 의존하지 않는 총 등록 원문·포맷 분해 칸은 무조건 렌더 `:291-310` · 테스트 `SourcesList.test.tsx:204-227`(`고아 소스`·`인용됨 (` 부재 단언, 행 2개 모두 집계 불가 문구, 포맷 분해 유지) |
| `Workspace has no sources yet` | 충족 | 벤토 전체가 `sources.length > 0` 게이트 안 `:284`, 빈 상태 Dropzone 캔버스 `:493-520` · 테스트 `SourcesList.test.tsx:19-32`, `:195-202`(벤토 부재 명시 단언 신규) |
| 색만으로 전달하지 않을 것 (요구사항 본문 SHALL) | 충족 | 파이프라인 칸이 `전 소스 청킹 완료`/`청킹 진행 중`·`청킹 대기 N개`를 텍스트로 병기 `:392-408`. 아이콘 색은 보조 신호이며 `chunkStatsUnavailable`일 때 초록으로 새지 않도록 `!chunkStatsUnavailable &&` 가드가 걸려 있다 `:375` |
| 실패 집계 문단 — 청크 쪽 (요구사항 본문 SHALL) | 충족 (테스트 없음) | `chunkStatsUnavailable`이 의존 지표 전부를 덮는다: 생성된 청크 칸 `:318-321`, 파이프라인 상태 칸 `:382-385`, 행의 청크 값 `:645-648`. 스펙이 세운 시나리오는 wiki-citation 쪽뿐이고 그쪽은 검증됨 — 아래 「관찰 사항」 |

### ADDED: Uniform source list rows independent of citation count

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| `Member views a source cited by many wiki pages` | 충족 (r1 대비 검증 추가) | 상한 2개 `SourcesList.tsx:568-569`, 칩 렌더 `:624-633`, `+N개 더` `:634-638`, 한 줄 고정 `overflow-hidden whitespace-nowrap` `:623`, 행 높이 `md:h-[72px]` `:574`, 인용 0건 문구 `:618-621` · 테스트 `SourcesList.test.tsx:230-259`(인용 4건에서 칩 2개 렌더·3번째 부재·`+2개 더`) |
| `Member scans the list header against a row` | 충족 | 컬럼 정의를 컨테이너 CSS 변수 `--sources-cols`에 한 번만 선언 `:537-546`, 헤더가 참조 `:550`, 데이터 행이 참조 `:574`. 헤더 `청크 및 좌표`/`작업`의 `text-right` `:554,556`에 행의 `md:text-right` `:644`·`md:justify-end` `:676`가 대응 |
| `Member opens the source library on a narrow viewport` | 충족 | md 미만 `grid-cols-1` `:574`, 헤더 `hidden … md:grid` `:549`, 래퍼 `overflow-hidden` `:538`, 컬럼 트랙 전부 `minmax(0, …)` `:543` |

### ADDED: Source row identity and upload recency

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| `Member scans a source row for provenance` | 충족 | 포맷 배지 `:578-580`, 제목 링크 `:582-593`(`title`/`aria-label` 유지 `:587-588`), 크기 `:597-602`, 수집 유형 `:603`, 상대 시각 `:605`, 절대 일자 `:607` · 테스트 `SourcesList.test.tsx:34-60`(접근성 속성·상세 라우트·`2026년 8월 12일`) |
| `Source has no recorded size` | 충족 (r1 대비 검증 추가) | `formatBytes`가 `null` 반환 `:66-71`, 렌더가 `{size && …}` 조건부이며 구분점 `·`도 같은 블록 안 `:597-602` — 자리표시자 없이 생략 · 테스트 `SourcesList.test.tsx:261-288`(크기 있는 행의 `2.0 KB` 존재, 두 행 모두 절대 일자 노출) |

### r1에서 충족 판정한 항목의 비회귀 확인

| 항목 | 결과 | 증거 |
| --- | --- | --- |
| `data-od-id="source-table-section"` · `pipeline-stats` | 유지 | `:438`, `:288` |
| `JobStepper` 폴링 · `상세 보기` 링크 · `isOwner` 게이트 · 삭제 testid · 8개 페이지네이션 | 유지 | `:669-672`, `:677-682`, `:683-697`(`delete-source-btn-<id>` `:692`), `PAGE_SIZE = 8` `:127`, `Pagination` `:706-713` · 테스트 `SourcesList.test.tsx:62-80`, `:290-314` |
| 삭제 흐름의 페이지 보정 | 유지 | `:170-185` — `setSources` 후 `maxPage` 재계산 로직 그대로. 요약 산출식이 `sources`를 읽으므로 삭제 즉시 네 지표가 함께 줄어든다 |
| 로딩 스켈레톤 골격 | 유지 | `loading.tsx:7-8`(`aria-busy`·testid), `:26`(벤토 4칸), `:57-80`(같은 `--sources-cols` 5열) · 테스트 `LoadingSkeletons.test.tsx:37-51` |
| v2 CSS 주석 (task 4.3) | 유지 | `nexuswiki-design-system.css:1692-1720`·`:1724`·`:1737-1739` — 규칙 삭제 없음 |
| 검증 재실행 (task 4.2) | 이번 라운드에서 새로 실행 | `vitest run` **390 pass / 0 fail**(r1 384 → +6), `tsc --noEmit` 무오류, `next lint` Errors 0 / Warnings 0, `openspec validate sources-redesign --strict` valid |

## 조치가 필요한 항목

없다. r1의 지적 2건은 모두 해소됐다.

1. **조치 1(`totalChunks` 모순)** — 해소. `SourcesList.tsx:225-228`이 합계를 `sources`에서 파생시키고, `:221-224`에 왜 `Object.values` 전량 합산이면 안 되는지가 주석으로 남았다. 회귀 테스트가 `SourcesList.test.tsx:175-193`에 있다.
2. **조치 2(ADDED 3건 무검증)** — 해소. 네 지표 값 대조·합계 파생 원천·빈 워크스페이스 벤토 생략·집계 실패 시 단정 금지·인용 칩 상한·크기 생략까지 6건이 추가됐다.

## 관찰 사항 (판정에 반영하지 않음)

- **시나리오 개수 정정**: 호출자 메시지는 13개로 적었으나 delta spec의 `#### Scenario` 실제 개수는 **12개**다(MODIFIED 3 + `Source pipeline summary metrics` 4 + `Uniform source list rows` 3 + `Source row identity` 2). 12개 전부를 대조했다.
- **`tasks.md`에 집계 실패 대응 task가 없다**: 새로 들어온 `A summary aggregate query fails` 시나리오와 `page.tsx:82-93`·`SourcesList.tsx:61,318,343,382,614,645`의 구현을 가리키는 task 항목이 `tasks.md`에 없다. 동작 자체는 스펙과 테스트로 덮여 있으므로 스펙 준수 판정에는 영향이 없지만, task 4.4(sync·archive) 전에 §1이나 §3에 한 줄을 추가해 두면 원장이 구현과 어긋나지 않는다.
- **`chunkStatsUnavailable` 경로에 자동 검증이 없다**: 요구사항 본문은 "chunk **or** wiki-citation" 둘 다를 다루지만 시나리오는 wiki-citation만 세웠고, 테스트도 `citingPagesUnavailable`만 넣는다(`SourcesList.test.tsx:211`). 청크 쪽 세 분기(`:318`, `:382`, `:645`)는 코드 근거만 있다. 같은 fixture에 `chunkStatsUnavailable`을 켠 케이스 하나면 대칭이 맞는다.
- **크기 생략의 "자리표시자 없음"이 부정형으로 단언되지 않았다**: `SourcesList.test.tsx:261-288`은 크기 있는 행의 `2.0 KB` 존재와 두 행의 절대 일자만 본다. `getAllByText(/KB|MB|B$/)`가 1건인지 같은 부정 단언을 더하면 시나리오 문구와 정확히 겹친다. 구현(`:597-602`)은 조건부가 명확해 미충족으로 보지 않는다.
- **포맷 분해가 총계와 합이 맞지 않을 수 있다**: `isPdf`(`:75-80`)와 `isTextMd`(`:82-90`)는 상호배타가 아니라, `source_type="article"`이면서 제목이 `.pdf`로 끝나는 소스는 양쪽에 모두 계수된다. 스펙은 "format breakdown"만 요구하고 분할(partition)을 요구하지 않으며 task 1.1이 기존 판정 재사용을 명시했으므로 미충족은 아니다. 탭 개수도 r1부터 같은 성질이다.
- **r1의 잔여 관찰은 그대로다**: 탭 개수와 검색어의 상호작용, `목록 50건 상한`(`page.tsx:9,35`)과 `총 등록 원문` 표현의 간극, 320px 안팎에서 `h-9` + `flex-wrap` 칩이 두 줄로 감길 가능성(`:447`). 셋 다 어떤 시나리오도 깨지 않는다.
- **`tasks.md` 4.4(동기화·아카이브)는 미체크**다. 리뷰 게이트 이후 절차이므로 이번 판정 대상이 아니다.

## 판정 근거

delta spec의 12개 시나리오와 요구사항 본문의 SHALL 전부가 코드 근거를 가지며, r1에서 유일하게 미충족이던 "Each summary figure SHALL be derived from the same workspace data the list itself renders"가 산출식 교체로 해소됐다 — 네 지표가 모두 `sources` state를 원천으로 삼아 삭제 직후에도 아래 행들과 모순되지 않고, `Object.values(chunkStats)` 전량 합산은 코드에서 사라졌으며 목록 밖 청크가 합계에 섞이지 않는지 확인하는 회귀 테스트가 붙었다. r1의 두 번째 지적이던 ADDED 3개 요구사항의 무검증 상태도 6건의 단언 추가로 메워졌고, 벤토 수치·인용 칩 상한·빈 워크스페이스·집계 실패가 각각 그물에 걸린다. 이번 라운드에 delta spec이 확장됐지만(`A summary aggregate query fails`) 새 시나리오도 서버 props의 실패 플래그와 UI 분기로 충족되며, 실패 집계에 의존하지 않는 총 등록 원문·포맷 분해는 그대로 유지된다 — 스펙 밖 사용자 관찰 가능 동작이 남지 않았다는 뜻이다. MODIFIED 요구사항과 회귀 계약(셀렉터·권한 게이트·페이지네이션·스켈레톤·CSS 주석)도 r1 판정에서 깨진 곳이 없고, 전체 검증(테스트 390건·typecheck·lint·strict validate)을 이 리뷰에서 새로 실행해 통과를 확인했다. 남은 항목은 전부 검증 밀도나 원장 정리에 관한 권고이며 미충족 시나리오가 아니므로 `pass`다.
