## Context

동기는 [`proposal.md`](proposal.md)의 Why를, 표시 계약은 [`specs/source-management-wiki/spec.md`](specs/source-management-wiki/spec.md)를 따른다. 근거 계획서는 `docs/design-systems/sources-redesign-plan.md`다.

현재 상태 중 설계를 제약하는 것들:

- `apps/dashboard/app/w/[workspaceId]/sources/page.tsx`는 이미 `chunkStats`(소스별 청크 수·char 구간)와 `citingPages`(소스별 인용 위키 목록)를 N+1 없이 집계해 `SourcesList`에 내려준다. 벤토가 필요로 하는 네 지표는 전부 이 두 props와 `initialSources`에서 나온다 — 새 조회가 필요 없다.
- `SourcesList`는 `sources` 로컬 state를 업로드·삭제 시 갱신하지만 `chunkStats`·`citingPages`는 서버 props 그대로다. 방금 업로드한 소스는 청크 통계가 아직 없다.
- 목록 시각은 `docs/design-systems/v2/nexuswiki-design-system.css`의 `.content.sources` 스코프에 산다: `.stats`는 3열 그리드로 하드코딩, `.table`/`.table-wrap`은 `<table>` 전제, `.field.search`는 `height/min-height/max-height: 36px`로 못박혀 있고 `padding`에 `!important`가 걸려 있다.
- 반면 직전에 머지된 위키 라이브러리 리디자인(`WikiLibrary.tsx`)은 공용 CSS를 늘리지 않고 **Tailwind 유틸리티 + v2 `var()` 토큰**을 인라인으로 쓰는 방식으로 갔다.
- `.format`(포맷 배지), `.doc-chip`(인용 위키 칩)은 이미 v2에 있고 이 화면 전용이다.
- 테스트가 잡고 있는 것: `data-od-id="source-table-section"`, `data-testid="empty-sources-dropzone-container"`, `data-testid="delete-source-btn-<id>"`, `role="tab"`(`/PDF/`·`/텍스트\/마크다운/` 이름), 제목의 `title`/`aria-label`, `상세 보기` 링크 이름, `2026년 8월 12일`(절대 일자), 페이지당 8개 페이지네이션. `<table>`/`row`/`cell` role에 의존하는 단언은 없다.

## Goals / Non-Goals

**Goals:**

- 벤토·툴바·목록을 계획서 Phase 1~3의 위계로 맞추되, 위키 라이브러리가 세운 구현 관용구(유틸리티 + 토큰)를 따라 두 화면이 서로 다른 방식으로 만들어지지 않게 한다.
- 헤더와 데이터 행이 하나의 컬럼 정의를 공유해 축이 어긋날 수 없는 구조로 만든다.
- 기존 테스트 셀렉터·권한 게이트·페이지네이션·`JobStepper` 폴링을 그대로 보존한다.

**Non-Goals:**

- 소스 상세 라우트(`/sources/[id]`), 청크 인스펙터, `Dropzone` 내부는 이 change에서 바꾸지 않는다.
- `/` 키 검색 포커스 단축키를 신설하지 않는다(계획서 §2에 힌트가 있으나 위키 라이브러리에서 이미 배제한 결정을 뒤집지 않는다).
- 다크 모드, `prefers-color-scheme`, Tailwind `dark:` 변형을 도입하지 않는다.
- API·워커·마이그레이션·RLS를 바꾸지 않는다.

## Decisions

### D-1. 새 시각은 Tailwind 유틸리티 + v2 토큰으로 쓴다. 공용 CSS는 늘리지 않는다

계획서 §3은 `.metrics-grid`·`.sources-table-container`·`.source-row-item` 같은 새 클래스명을 제안한다. 그대로 가면 v2 CSS에 이 화면 전용 규칙이 한 블록 더 쌓이고, 바로 옆 위키 라이브러리는 유틸리티로 같은 모양을 만드는 이원 상태가 된다.

대신 `WikiLibrary.tsx`와 같이 인라인 유틸리티로 쓰고 색·반경·간격은 `var(--border)`·`var(--surface)`·`var(--muted)` 등 기존 토큰만 참조한다. 임의 hex를 새로 도입하지 않는다. 계획서 콘셉트 코드의 `status-pill good` 같은 미정의 클래스는 위키 라이브러리가 이미 쓰는 `bg-[var(--good)]/12 text-[var(--good)]` 패턴으로 치환한다.

이미 존재하고 이 화면 전용인 `.format`·`.doc-chip`·`.doc-chips`는 그대로 재사용한다 — 잘 도는 것을 유틸리티로 옮겨 적을 이유가 없다.

대안: v2 CSS에 새 섹션을 추가한다. → 위 이원화 때문에 채택하지 않는다.

### D-2. 툴바 높이는 38px가 아니라 기존 `.field.search`의 36px에 맞춘다

계획서 §2는 세그먼트 바와 검색창을 38px로 통일하라고 한다. 그런데 `.field.search`는 `.content.sources` 스코프가 아니라 전역이며, 위키 라이브러리 검색창도 같은 클래스를 쓴다. 38px로 올리면 이 change의 범위 밖인 위키 라이브러리 툴바가 함께 2px 밀린다.

따라서 목표 높이를 **36px**로 잡고, 필터 탭 쪽을 `h-9`(36px) + `box-border`로 맞춘다. 공유 CSS는 건드리지 않는다. 스펙이 요구하는 것은 "두 컨트롤의 위아래 모서리가 일치할 것"이지 특정 픽셀 값이 아니다.

### D-3. 필터 탭은 시각만 세그먼트 칩으로 바꾸고 `role="tablist"`/`aria-selected`는 유지한다

위키 라이브러리는 `chip` + `aria-pressed`를 쓰지만, 소스 필터는 상호배타적 단일 선택이라 tab 시맨틱이 더 맞고 `SourcesList.test.tsx`가 `getByRole("tab", …)`으로 잡고 있다. 시맨틱을 바꾸면 스펙상 이득 없이 테스트만 깨진다.

탭 이름에 개수를 계속 실어(`전체 12`·`PDF 0`·`텍스트/마크다운 12`) 기존 정규식 단언(`/PDF/`)과도 계속 맞물린다.

### D-4. 벤토 네 지표는 전부 이미 내려오는 props에서 계산한다

| 지표 | 산출 |
| --- | --- |
| 총 등록 원문 | `sources.length` + 포맷별 분해(`isPdf`/`isTextMd` 재사용) |
| 생성된 청크 | `chunkStats` 값들의 `count` 합 |
| 위키 인용 연결률 | `citingPages[id]`가 비지 않은 소스 수 / `sources.length` |
| 파이프라인 상태 | 청크가 1개 이상인 소스 수(`indexedCount`) / `sources.length` |

계획서가 말하는 "파이프라인 건강도(5/5단계)"를 워크스페이스 단위로 정확히 계산하려면 `jobs` 테이블을 새로 읽어야 한다. 이 change는 새 조회를 만들지 않기로 했으므로, 이미 있는 신호인 **청킹 완료 소스 비율**로 지표를 정의한다. 스펙도 그 표현("whether every registered source has completed chunking")으로 적었다 — 화면이 데이터보다 더 아는 척하지 않게 하기 위해서다. 행 단위 5단계 진행은 지금처럼 `JobStepper`가 계속 담당한다.

⚠️ `chunkStats`·`citingPages`는 서버 props라 업로드 직후 새 소스에는 값이 없다. 이때 분모(`sources.length`)만 늘고 분자는 그대로여서 연결률이 잠깐 내려간다. 이는 실제 상태를 반영한 것이므로(방금 올린 소스는 아직 청킹·인용 전이다) 보정하지 않는다.

### D-5. 헤더와 행은 하나의 `grid-template-columns` 값을 공유한다

계획서가 지적한 "헤더 '작업'과 삭제 아이콘의 축 어긋남"은 헤더와 행이 각자 폭을 선언할 때 생긴다. 컨테이너에 CSS 변수로 컬럼 정의를 한 번만 쓰고 헤더 행·데이터 행이 모두 그것을 참조하게 해, 한쪽만 고쳐서 어긋나는 상태를 구조적으로 불가능하게 만든다.

`<table>`을 버리므로 `table-layout: fixed` + `<colgroup>`은 사라진다. 테스트가 table/row/cell role에 의존하지 않는 것은 확인했다.

### D-6. 인용 위키 칩은 2개 + 나머지 개수로 자른다

행 높이가 인용 수에 따라 달라지는 것이 지금 목록 리듬이 깨지는 직접 원인이다. `.doc-chips`의 `flex-wrap: wrap` 대신 이 화면에서는 줄바꿈을 막고 최대 2개만 렌더한 뒤 `+N개 더`를 붙인다. 나머지 인용은 소스 상세에서 전부 볼 수 있으므로 정보가 사라지지 않는다.

인용이 0건인 소스의 `인용한 위키 없음` 문구는 유지한다 — 고아 소스를 식별하는 유일한 행 단위 신호다.

### D-7. 업로드 열은 없애지 않고 제목 아래 메타 라인으로 접는다

6열 → 5열은 `업로드` 열을 메타 라인으로 옮겨서 만든다. 계획서 §3.2 예시는 상대 시각(`2일 전`)만 보여주지만, 절대 일자를 잃으면 정확한 출처 시점을 행에서 되짚을 수 없고 `SourcesList.test.tsx`의 `2026년 8월 12일` 단언도 깨진다. 둘 다 남긴다(`formatRelativeTime` 표시 + `formatDate` 병기). 스펙의 "Source row identity and upload recency" 요구사항이 이 결정의 계약이다.

## Risks / Trade-offs

- [Risk] `<table>` → CSS Grid 전환으로 스크린리더의 표 탐색(행/열 헤더 연관)이 사라진다. → 목록이 원래 셀 단위 비교표가 아니라 카드 행이었고, 각 값이 자기 라벨을 텍스트로 들고 있게 만든다. 헤더 행은 시각 라벨로 남기되 행 안의 값이 라벨 없이 숫자만 남지 않도록 한다(`5 청크`, `5/5단계`).
- [Risk] 72px 고정 행 높이는 긴 한국어 제목에서 말줄임을 늘린다. → 제목에 `title`/`aria-label`을 계속 달아 전체 문자열을 보조기술과 툴팁에 남긴다(기존 계약).
- [Risk] `.content.sources .stats`(3열 그리드)와 `.table`/`.table-wrap`이 새 마크업에서 안 쓰이면서 죽은 규칙이 된다. → 이 change에서 해당 규칙을 지우지는 않는다(백로그 리디자인이 같은 블록을 건드릴 예정이라 두 change가 같은 파일에서 충돌한다). 사용처가 사라진 사실을 v2 CSS 주석으로 남긴다.
- [Risk] 계획서가 명시한 38px를 36px로 내리는 결정(D-2)이 계획서와 어긋난다. → 계획서는 근거 문서이지 계약이 아니다. 계약은 delta spec이고, 스펙은 픽셀이 아니라 정렬을 요구한다. 이 이탈을 여기 기록한다.
- [Trade-off] 파이프라인 지표를 청킹 완료율로 정의하면 embed·conflict_check 단계에서 멈춘 소스를 "정상"으로 셀 수 있다. → 새 조회 없이 얻을 수 있는 최선이며, 행 단위 `JobStepper`가 실제 단계를 계속 보여준다. 워크스페이스 단위 5단계 집계는 별도 change로 남긴다.
- [Trade-off] `sources/page.tsx`의 `PAGE_SIZE = 50` 때문에 벤토는 **로드된 창** 기준이다. 소스가 50개를 넘으면 "전 소스 청킹 완료"가 51번째 이후를 포함하지 않는다. → 종전 3칸 통계 바도 같은 창을 썼으므로 이 change가 만든 결함은 아니다. 정확히 세려면 워크스페이스 전체 집계 조회가 필요한데 이 change는 새 조회를 만들지 않기로 했다(D-4). 창 밖까지 정확한 집계는 별도 change로 남긴다.

## Migration Plan

1. `SourcesList` UI만 배포한다. 데이터베이스 마이그레이션도 API 변경도 없다.
2. `pnpm test`(`SourcesList`·`SourceDeletion`·`source-detail-route` 포함)·`pnpm typecheck`·`pnpm lint`·`openspec validate sources-redesign --strict`로 회귀를 확인한다.
3. 문제가 있으면 이 change의 UI 커밋만 되돌린다. 서버 조회와 삭제 API 계약을 바꾸지 않으므로 데이터 롤백은 필요 없다.
