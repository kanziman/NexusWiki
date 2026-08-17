# 넥서스위키(NexusWiki) 제품 핵심 불변식 (Product Invariants)

> 이 문서는 모든 화면 설계(PRD), 데이터베이스 DDL, 비동기 파이프라인, UI 프로토타입이 **위반할 수 없는 단일 진실 공급원**입니다. PRD 와 이 문서가 어긋나면 이 문서가 이깁니다.

## 이 문서를 읽는 법

각 항목에는 구현 상태가 붙어 있습니다. **[구현됨]** 은 `supabase/migrations/` 에 실재하는 객체를 가리키고, **[미구현]** 은 아직 마이그레이션이 없는 설계입니다.

⚠️ **PRD 에서 [미구현] 객체를 SQL 계약으로 적을 때는 반드시 그 표시를 함께 적습니다.** 지금까지 반복된 실패가 정확히 이것입니다 — PRD 가 존재하지 않는 테이블·컬럼을 "확정(Validated)" 딱지와 함께 기술해 두면, 읽는 사람이 구현된 것으로 믿고 그 위에 다음 설계를 쌓습니다.

현재 마이그레이션은 `0001`~`0014`, RLS 정책 27개입니다.

---

## 1. 정보구조 불변식 (Information Architecture) — 2계층

### [금지] 워크스페이스와 위키 페이지 사이에 중간 계층을 두지 않음

* **원칙**: 넥서스위키의 정보구조는 **`워크스페이스 > 위키 페이지` 2계층**이다. `프로젝트`, `지식 그룹`, 폴더, 컬렉션 같은 중간 계층은 **스키마에도 UI 에도 존재하지 않는다.**
* **[구현됨]** `wiki_pages` 는 `workspace_id` 만 가지며 `UNIQUE (workspace_id, slug)` 로 고유하다. `projects` · `wiki_groups` 테이블도, `wiki_pages.project_id` · `group_id` 컬럼도 없다.
* **[금지]** 라우트에 중간 계층을 넣지 않는다. `/w/[workspace_slug]/[project_slug]/[group_slug]` 형태는 금지.

### 계층 대신 쓰는 것 — 전부 [구현됨]

| 목적 | 수단 | 근거 |
| --- | --- | --- |
| 분류 | `wiki_pages.category` — `concepts` · `entities` · `guides` · `maps` **4종 고정** | `0001_core_schema.sql` CHECK 제약 + `wiki_pages_workspace_category_idx` |
| 문서 간 구조 | `wiki_links` — `to_wiki_id IS NULL` 이면 레드링크(작성 대기), `resolved` 는 생성 컬럼 | `0002_search_schema.sql` |
| 동의어 | `wiki_pages.aliases jsonb` | `0001_core_schema.sql` |
| 신뢰도 | `confidence` · `verification_status` · `explored` · `disputed` | `0001_core_schema.sql` |

* **[금지]** 위 `category` 4종 외의 값을 UI 에 쓰지 않는다. `ARCHITECTURE`, `성능 튜닝`, `GUIDE` 같은 임의 렌즈 이름은 CHECK 제약에 걸려 INSERT 가 거부된다. 화면에 한국어 레이블이 필요하면 4종에 대한 표시명 매핑으로 처리하고, 종류를 늘리지 않는다.

### 왜 계층을 두지 않는가

1. **검색이 계층을 대체하는 제품이다.** 5채널 하이브리드 검색과 Ask 가 존재 이유인데, 그 위에 폴더 트리를 얹으면 없애려던 탐색 방식을 되살리는 셈이다.
2. **컴파일러에 분류 부담을 주지 않는다.** 위키 페이지는 LLM 이 자동 생성한다. 그룹 계층이 있으면 컴파일러가 페이지마다 소속을 정해야 하고, 오분류를 사람이 손으로 고쳐야 하는데 이는 §2 "수동 재컴파일 버튼 없음"과도 부딪힌다.
3. **워크스페이스가 이미 그 역할을 한다 — 더 강하게.** 지식 영역이 정말 갈리면 답은 별도 워크스페이스다. 워크스페이스는 RLS 로 물리 격리되고 `workspace_members` 역할도 따로 간다. 중간 계층은 그 일을 격리 보장 없이 흉내낸다.
4. **테넌트 경계를 늘리는 건 가장 비싼 변경이다.** 격리는 앱이 아니라 DB 에 산다. 테이블이 늘면 복합 FK `(id, workspace_id)` 와 RLS 정책이 함께 늘고, 틀릴 자리가 늘어난다.

### Ask 스코프는 계층 없이 좁힌다

스코프 셀렉터는 `현재 문서 주변(wiki_links 이웃)` · `카테고리` · `워크스페이스 전체` 로 구성한다. 검색 정밀도 이득은 유지되고 스키마는 그대로다.

### 다시 볼 시점

한 워크스페이스가 수백 문서를 넘거나 영역별 권한 분리 요구가 나올 때. 그때도 우선 검토할 답은 "워크스페이스를 나눈다" 이다.

---

## 2. 컴파일 & 재컴파일 불변식 (Compiler & Jobs)

### [금지] "사용자 수동 재컴파일 트리거" 버튼은 존재하지 않음

* **원칙**: 위키 생성과 갱신은 **원본 소스가 변경·추가·삭제될 때 백그라운드 워커가 자동 실행하는 비동기 파이프라인**이다.
* 사용자가 누르는 "위키 수동 재컴파일" 버튼은 UI 어디에도 없다.
* **유일한 사용자 액션**:
  1. `[+ 소스 추가]` / 소스 파일 업로드 또는 삭제 → 백그라운드 파이프라인 자동 실행
  2. 비동기 잡이 실패했을 때 `JobStepper` 의 `[재시도]` 버튼

---

## 3. 인간 검증(`verification_status`) 보존 불변식

* **[구현됨]** `wiki_pages.verification_status` 의 허용값은 정확히 **`'verified'` · `'partial'` · `'unverified'` · `'disputed'` 4종**이며 기본값은 `'unverified'` 다 (`0001_core_schema.sql` CHECK 제약).
  * ⚠️ **`'stale'` 은 존재하지 않는다.** 이전 판이 `('unverified','verified','stale')` 로 잘못 적어 두었고, 그 값에 기대어 설계된 PRD 가 있다면 함께 고쳐야 한다.
  * `disputed` 는 같은 이름의 boolean 컬럼 `wiki_pages.disputed` 와 별개다. 둘을 혼동하지 않는다.
* 신뢰도는 별도 컬럼 `confidence`(`high` · `medium` · `low`)로 관리하며 `verification_status` 와 섞지 않는다.
* 백그라운드 AI 컴파일러(`_upsert_page`)는 `verification_status` 를 절대 덮어쓰지 않는다. **사람이 세우는 뱃지**다.
* **공개 및 재발행 수명주기**:
  1. `verification_status = 'verified'` 인 문서만 공개 신청 가능.
  2. 공개 이후 내용이 바뀌었는지는 `wiki_pages.updated_at > wiki_page_publications.published_at` 타임스탬프 비교로만 판정한다. 새 enum 값을 만들지 않는다.

---

## 4. 공개 위키 URL 네임스페이스 및 충돌 방지 불변식 (Public Routing)

### [금지] 전역 플랫 URL `/p/[page_slug]` 사용 금지

* **원칙**: 위키 슬러그는 워크스페이스 안에서만 고유하다(`UNIQUE (workspace_id, slug)`). 서로 다른 워크스페이스가 같은 `tenant-isolation-rls` 슬러그를 공개할 수 있으므로 전역 평면 URL 은 라우팅 충돌을 일으킨다.
* **공개 URL 표준 규격**: `https://nexuswiki.io/p/[workspace_slug]/[page_slug]`
* **동작 계약**:
  1. **[미구현]** `workspace_public_settings.workspace_slug` 가 전역 고유 식별자 역할을 한다.
  2. 라우터는 해당 워크스페이스의 마스터 스위치가 ON 이고 발행본(**[미구현]** `wiki_page_publications`)이 있을 때만 렌더링한다.
* 로그인 사용자용 내부 라우트는 `/w/[workspace_slug]/...` 로 공개 경로와 분리한다.

---

## 5. 1:1 사이드카 테넌트 격리 & 물리적 킬스위치 불변식

1. **테넌트 격리 복합 FK — [구현됨] 관행**: 모든 자식·사이드카 테이블은 `FOREIGN KEY (parent_id, workspace_id) REFERENCES parent_table (id, workspace_id)` 를 강제해, RLS 를 우회하는 `service_role` 경로에서도 테넌트 교차를 원천 차단한다.
2. **사이드카 테이블 분리 — 둘 다 [미구현]**:
   * `workspace_public_settings`: 워크스페이스 공개 마스터 스위치와 공개 메타데이터. 민감 컬럼과 물리적으로 분리해 `anon` 이 이 테이블 전체를 봐도 안전하게 만든다.
   * `wiki_page_publications`: 사람이 검토 승인한 공개 발행본 1건 (본문 전문 + 승인된 인용 스니펫 JSONB).
3. **물리적 킬스위치**: `workspace_public_settings.allow_public_sharing` 이 `false` 면 RLS 엔진 레벨에서 모든 공개 조회가 0건(404)으로 일괄 차단된다.
   * ⚠️ 킬스위치를 `EXISTS (SELECT 1 FROM workspaces ...)` 서브쿼리로 구현하면 안 된다. `anon` 은 `workspaces` 에 정책이 없어 서브쿼리가 **항상 0행**을 반환한다. 사이드카 테이블을 분리한 이유가 이것이다.

---

## 6. 워크스페이스 생성 계약

* **[구현됨]** `workspaces.owner_id` 는 `NOT NULL` 이다. INSERT 에서 빠지면 실패한다.
* **[구현됨]** `workspaces_add_owner_member` AFTER INSERT 트리거가 생성자를 `role='owner'` 로 `workspace_members` 에 자동 등록한다(`ON CONFLICT DO UPDATE`).
  * ⚠️ PRD 나 애플리케이션 코드가 `INSERT INTO workspace_members ... 'owner'` 를 **다시 적지 않는다.** 계약이 두 곳에 중복되면 한쪽만 고쳐질 때 어긋난다.
* **[구현됨]** `workspaces.kind` 는 `'personal'` · `'team'` 2종이다.

---

## 7. 디자인 시스템 룩앤필 불변식

1. **색은 토큰이 정본이다.** [`nexuswiki-design-system.css`](nexuswiki-design-system.css) 의 `:root` 토큰 외의 색을 쓰지 않는다. PRD 에 hex 를 직접 적지 않는다.
   * 강조는 `--accent`(청록) 하나. 상태는 `--good` · `--danger` 뿐이다.
   * **[금지]** 보라 · 파랑 · 로즈 같은 팔레트 밖 색으로 뱃지나 렌즈를 칠하지 않는다.
2. **Zero Emojis**: 렌더링되는 UI 에 이모지를 쓰지 않고 2.0~2.2px 단색 SVG 라인 아이콘만 쓴다. **이 문서를 포함한 설계 문서 산문에도 같은 규칙을 적용한다** — 지금까지 PRD 프로즈에서 반복적으로 깨진 항목이다.
3. **가로 스크롤 금지**: 640px 이하에서 페이지 전체가 가로로 스크롤되지 않는다. 표는 카드로 전환하되 열을 임의로 숨기지 않는다.
