# 워크스페이스 홈 PRD

> **문서 상태**: 리뷰 반영판 (2026-08-17). 이전 "확정(Validated)" 판은 존재하지 않는 스키마 위에 쓰여 있어 전면 재작성했다.
> **기능 영역**: 워크스페이스 홈 대시보드, 신규 사용자 온보딩
> **라우트**: `/w/[workspace_slug]` (홈), `/` (소속 워크스페이스 0개일 때 온보딩)
> **연계 프로토타입**: [`nexuswiki-workspace-home.html`](nexuswiki-workspace-home.html)
> **상위 불변 규칙**: [`PRODUCT-INVARIANTS.md`](PRODUCT-INVARIANTS.md)
> **디자인 토큰**: [`nexuswiki-design-system.css`](nexuswiki-design-system.css)

이 문서의 SQL 은 `supabase/migrations/0001`~`0014` 에 실재하는 객체만 사용한다. 미구현 객체를 쓰는 곳은 **[미구현]** 으로 표시한다.

---

## 1. 목적

* 워크스페이스 홈은 **질문을 시작하는 자리**다. 문서를 뒤지는 자리가 아니다.
* 팀이 지금 무엇을 알고 있고(컴파일된 위키), 무엇이 비어 있는지(레드링크 백로그)를 한 화면에서 보여준다.
* 소속 워크스페이스가 없는 신규 사용자에게는 이름 하나로 시작하는 최소 개설 경험을 준다.

### 성공 기준

1. 진입 후 첫 질문까지 클릭 2회 이내(질문창 포커스 → 전송, 또는 추천 칩 1회 → 전송).
2. 레드링크 백로그가 홈에서 바로 보이고, 각 항목에서 소스 연결로 넘어갈 수 있다.
3. 신규 사용자가 워크스페이스 이름만 입력하고 홈에 도달한다.

---

## 2. 정보구조 (불변식 §1 준수)

**워크스페이스 > 위키 페이지 2계층이다.** 프로젝트·지식 그룹 중간 계층은 없다.

이전 판은 `/w/[workspace_slug]/[project_slug]/[group_slug]` 3계층을 전제했으나 `projects`·`wiki_groups` 테이블도 `wiki_pages.project_id`·`group_id` 컬럼도 실재하지 않는다. 분류는 `category` 4종이 담당한다.

### 카테고리 표시명 매핑

`wiki_pages.category` 의 CHECK 값은 4종 고정이며 늘리지 않는다. 화면에는 표시명만 입힌다.

| `category` 값 | 화면 표시명 |
| --- | --- |
| `concepts` | 개념 |
| `entities` | 엔티티 |
| `guides` | 가이드 |
| `maps` | 맵 |

뱃지 색은 쓰지 않는다. 카테고리는 중립 `.badge` 로만 표기한다 (불변식 §7 — 강조색은 `--accent` 하나).

---

## 3. 화면 요구사항

### 3.1 좌측 내비게이션 (LNB)

* **워크스페이스 스위처** (`.switcher`): 현재 워크스페이스 이름 + 이니셜 마크. 클릭 시 팝오버 — 소속 워크스페이스 목록(현재 항목 체크) + `[새 워크스페이스 생성]`.
  * 소속 목록은 `workspace_members` 로 조회한다. `workspaces.kind` 가 `personal` 인 것과 `team` 인 것을 구분해 표기한다.
* **시스템 뷰** — 각 항목은 실재하는 질의에 대응한다:

| 항목 | 근거 | 카운트 |
| --- | --- | --- |
| 즐겨찾기 | **[미구현]** 즐겨찾기 저장소 없음 — 4.1 참조 | 표시 보류 |
| 최근 본 위키 | **[미구현]** 열람 이력 없음 — 4.1 참조 | 없음 |
| 미완성 백로그 | `wiki_links` 중 `resolved = false` 인 `target_slug` distinct 수 | 있음 |
| 원문 소스 | `raw_sources` 행 수 | 있음 |

* **카테고리 렌즈**: `개념` · `엔티티` · `가이드` · `맵` 4개 **필터**. 선택 시 본문 위키 목록이 해당 `category` 로 필터링된다.
  * 표시명은 이미 구현된 [`GraphLensFilter.tsx`](../../../apps/dashboard/components/GraphLensFilter.tsx) 와 일치시킨다. 코드가 먼저 있었으므로 문서를 코드에 맞춘다.
  * ⚠️ **이것은 3계층 트리의 대체물이 아니다.** 카테고리는 컴파일러가 배정하는 필터라 사용자가 만들 수 없다. 사용자가 이름 붙여 만드는 묶음은 **컬렉션**이며 별도 항목이다 — 불변식 §1 참조.
* **컬렉션** — **[미구현, 마일스톤2 예정]**. 사용자가 `[+]` 로 만들고 문서를 넣는 평면 묶음. 스키마·UI 설계 전까지 LNB 에 그리지 않는다.
* **팀 관리**: `팀원 & 역할 관리` — `workspace_members_list()` (`0014`) 사용.
* **하단 프로필** (`.profile`): 이름 + 역할, 설정 트리거.

> LNB 에 `[템플릿 관리]` 를 두지 않는다. `prompt_templates` 는 실재하지만 Supabase Studio 로 충분하다는 판단이 선행 리뷰에서 나왔다.

### 3.2 상단 바

* **브레드크럼**: `<워크스페이스 이름>` 단일 레벨. 3계층 경로를 표시하지 않는다.
* **우측 액션**: `[소스 추가]`(기본 버튼), `[질문 시작]`(primary, 화면당 1개 — 질문창으로 포커스 이동).
* 640px 이하에서는 `[메뉴]` 버튼이 LNB 서랍을 연다.

> 이전 판의 "시뮬레이션 모드 스위처(개발/데모용)"와 `[로그인]` 버튼은 삭제한다. 앞의 것은 프로토타입 조작 장치이고, 뒤의 것은 이미 로그인한 화면에 로그인 버튼을 두는 모순이다.

### 3.3 본문

**히어로**: 워크스페이스 이름(`h1`) + 즐겨찾기 토글 + 한 줄 설명.

**현황 통계** (`.stats`) — 4개 전부 실재 질의로 산출:

| 지표 | 산출 |
| --- | --- |
| 컴파일된 문서 | `count(wiki_pages)` |
| 연결된 원문 소스 | `count(raw_sources)` |
| 작성 대기 항목 | `count(distinct wiki_links.target_slug where resolved = false)` |
| 최종 업데이트 | `max(wiki_pages.updated_at)` |

⚠️ 이전 판은 LNB 백로그 카운트(7)와 본문 백로그 카운트(3)를 다른 값으로 적었다. **같은 질의에서 나오는 같은 수치여야 한다.**

**중앙 질문창** (`.ask`): 다중 라인 자동 리사이즈. 스코프 셀렉터는 불변식 §1 에 따라 3단계:

1. `현재 문서 주변` — 선택된 문서가 있을 때만. `wiki_links` 1-hop 이웃으로 한정
2. `<카테고리>` — LNB 렌즈 선택 시 해당 `category`
3. `워크스페이스 전체` — 기본값

`[질문하기]` 클릭 시 `/w/[workspace_slug]/ask` 로 전환하며 질문과 스코프를 넘긴다.

**추천 질문 칩** (`.chip`): 클릭 시 질문창을 채우고 포커스. 문구는 하드코딩이며, 워크스페이스 내용 기반 생성은 이번 마일스톤 범위 밖이다.

**2열 지식 영역**:

* **컴파일된 위키 문서** — 행 구성: 제목 / `<카테고리 표시명> · 인용 원문 N개 · <검증 뱃지>`. 클릭 시 `/w/[workspace_slug]/wiki/[slug]`.
  * 검증 뱃지는 `verification_status = 'verified'` 일 때만 `.badge.verified` 로 표기한다. 나머지 3종(`partial` · `unverified` · `disputed`)은 뱃지를 달지 않는다. 불변식 §3 참조 — `'stale'` 값은 존재하지 않는다.
* **작성 대기 백로그** — `wiki_links` 의 미해결 링크. 행 구성: `target_slug` / `위키 N곳에서 인용됨`. `[소스 연결]` 클릭 시 소스 추가 모달.

### 3.4 신규 사용자 온보딩

* **노출 조건**: `workspace_members` 에 행이 0개인 사용자가 `/` 진입.
* **폼**: `워크스페이스 이름` (필수) + `URL 슬러그` (이름에서 자동 생성, 수정 가능) + `[시작하기]`.
* 템플릿 팩이나 프리셋을 강요하지 않는다. 생성 즉시 홈으로 진입한다.
* ⚠️ **[미구현]** URL 슬러그를 저장할 곳이 없다. 4.2 참조.

---

## 4. 미해결 항목 (구현 전 결정 필요)

### 4.1 즐겨찾기 · 최근 본 위키 — 저장소 없음

두 기능 모두 사용자별 상태가 필요한데 해당 테이블이 없다. 선택지:

1. **이번 마일스톤에서 제외** — LNB 에서 두 항목을 뺀다. 가장 싸다.
2. `user_wiki_bookmarks (user_id, wiki_page_id, workspace_id, created_at)` 마이그레이션 1개 추가. 복합 FK `(wiki_page_id, workspace_id)` 와 RLS 정책 필요.
3. 최근 본 위키만 클라이언트 `localStorage` 로 처리 — 기기 간 동기화 없음.

프로토타입은 현재 두 항목을 모두 그리고 있다. **결정 전까지 카운트 뱃지를 표시하지 않는다.**

### 4.2 워크스페이스 URL 슬러그 — 결정 완료, 컬럼은 [마이그레이션 필요]

**2026-08-17 결정: `workspaces.slug` 가 정본이고 `workspace_public_settings.workspace_slug` 는 트리거로 파생되는 읽기 전용 복제본이다** (`checklists.json > decisions.workspace_slug`). 계약 전문은 [`public-sharing-prd.md`](public-sharing-prd.md) §2.0.

둘 중 하나만으로는 안 되는 이유가 각각 있다:

* **사이드카에만 두면** 비공개 워크스페이스가 URL 을 갖지 못한다.
* **정본에만 두면** 공개 경로가 `workspaces` 를 조인해야 하는데 `anon` 은 정책도 GRANT 도 없어 공개 페이지가 통째로 열리지 않는다(public-sharing 리뷰에서 `permission denied` 실측).

⚠️ **컬럼은 아직 없다.** 그리고 **이 결정은 슬러그 도입이지 라우트 전환이 아니다** — 내부 라우트는 이번 마일스톤에서 `/w/[workspace_id]`(UUID) 를 유지한다. 공개 URL 은 `/p/` 라 내부 라우트와 독립이므로 슬러그의 목적은 라우트를 바꾸지 않아도 달성된다. 이 문서의 `/w/[workspace_slug]` 표기는 슬러그 라우트 전환 이후를 가리킨다.

### 4.3 `wiki_pages` 설명 필드 없음

히어로의 "한 줄 설명"에 해당하는 컬럼이 `workspaces` 에 없다(`name` · `kind` · `owner_id` 뿐). 설명을 넣으려면 컬럼 추가가 필요하다. 없이 가도 화면은 성립한다.

---

## 5. 데이터베이스 계약

### 5.1 온보딩 워크스페이스 생성

```sql
-- owner_id 는 NOT NULL 이다. 빠지면 INSERT 가 실패한다.
-- workspace_members INSERT 를 여기에 적지 않는다 —
-- workspaces_add_owner_member AFTER INSERT 트리거가 이미 수행한다 (불변식 §6).
-- slug 는 [마이그레이션 필요] 다. 값은 서버가 slugify(title, taken) 로 만들며
-- taken 에는 기존 workspaces.slug 전체를 넘긴다 (전역 UNIQUE 이므로).
insert into public.workspaces (name, kind, owner_id, slug)
values (:workspace_name, 'team', auth.uid(), :slug)
returning id, slug;
```

⚠️ 이 화면의 온보딩은 셀프서브 가입 경로와 같은 흐름이다 — 계약이 갈리지 않도록 [`auth-google-prd.md`](auth-google-prd.md) §5·§6.2 와 함께 고친다.

### 5.2 홈 위키 목록

```sql
-- RLS 가 workspace_id 를 강제하지만, service_role 경로 대비로 조건을 명시한다.
select wp.id,
       wp.slug,
       wp.title,
       wp.category,
       wp.verification_status,
       wp.updated_at,
       jsonb_array_length(wp.sources) as cited_sources_count
from public.wiki_pages wp
where wp.workspace_id = :workspace_id
  and (:category is null or wp.category = :category)
order by wp.updated_at desc
limit 20;
```

* 인용 원문 수는 `wiki_pages.sources jsonb` 의 길이로 센다. `wiki_page_citations` 테이블은 존재하지 않는다.
* `archived_at` 컬럼이 없으므로 아카이브 필터는 걸지 않는다. 아카이브 기능은 이 마일스톤 범위 밖이다.
* 카테고리 렌즈 필터는 `wiki_pages_workspace_category_idx` 를 탄다.

### 5.3 작성 대기 백로그

```sql
-- 미해결 위키 링크 = 레드링크. resolved 는 to_wiki_id IS NULL 로부터 나오는 생성 컬럼이다.
select wl.target_slug,
       count(*) as cited_by_count
from public.wiki_links wl
where wl.workspace_id = :workspace_id
  and wl.resolved = false
group by wl.target_slug
order by cited_by_count desc
limit 20;
```

### 5.4 현황 통계

```sql
select (select count(*) from public.wiki_pages  where workspace_id = :workspace_id) as compiled_pages,
       (select count(*) from public.raw_sources where workspace_id = :workspace_id) as linked_sources,
       (select count(distinct target_slug) from public.wiki_links
         where workspace_id = :workspace_id and resolved = false)                   as backlog_items,
       (select max(updated_at) from public.wiki_pages where workspace_id = :workspace_id) as last_updated;
```

`backlog_items` 는 5.3 과 같은 정의를 쓴다 — LNB 와 본문이 다른 수를 보이면 안 된다.

---

## 6. 검증 계획

| 단계 | 항목 | 검증 기준 |
| --- | --- | --- |
| 1 | LNB · 스위처 | 카테고리 렌즈 4개가 `category` CHECK 값과 1:1 대응. 렌즈 선택 시 본문 목록 필터링 |
| 2 | 질문창 · 스코프 | 칩 클릭 시 질문창 자동 채움. 스코프 3종이 각각 다른 검색 범위를 실제로 전달 |
| 3 | 위키 · 백로그 2열 | 검증 뱃지가 `verification_status = 'verified'` 에서만 표시. LNB 백로그 수 == 본문 백로그 수 |
| 4 | 온보딩 | 워크스페이스 생성 후 `workspace_members` 에 owner 행이 **1개만** 생성됨(트리거 중복 없음) |
| 5 | 반응형 | 390 · 640 · 900 · 1280 · 1680px 에서 `scrollWidth == clientWidth` |
