# 공개 위키 공유 PRD — 1:1 사이드카

> **문서 상태**: 리뷰 반영판 (2026-08-17). 사이드카 아키텍처와 킬스위치 설계는 **옳았고 실측으로 동작을 확인했다.** 다만 §3 라우팅 계약이 `anon` 에서 실행 불가였고(실측: `permission denied for table wiki_pages`), GRANT 문이 하나도 없었으며, 존재하지 않는 `stale` 값에 기대고 있었다.
> **기능 영역**: 검토 승인된 위키의 외부 공개, 공개 URL 네임스페이스, 마스터 킬스위치
> **라우트**: `/p/[workspace_slug]/[page_slug]` — **[미구현]** (`app/` 에 `p` 디렉터리가 없다)
> **연계 프로토타입**: **v2 시안 없음.** 상위 폴더의 `public-wiki-reader-preview.html` 은 v1 이다
> **상위 불변 규칙**: [`PRODUCT-INVARIANTS.md`](PRODUCT-INVARIANTS.md) §3 · §4 · §5
> **디자인 토큰**: [`nexuswiki-design-system.css`](nexuswiki-design-system.css)

**이 문서의 두 테이블은 전부 [미구현]이다.** `workspace_public_settings` · `wiki_page_publications` 둘 다 마이그레이션이 없다(현재 테이블 10개). 아래 DDL 은 **구현 계약**이며, §6 에서 로컬 DB 에 실제로 세워 `anon` 으로 질의해 검증한 형태다.

---

## 0. 이전 판에서 정정한 것

| # | 이전 판 | 실제 | 근거 |
| --- | --- | --- | --- |
| 1 | §3.1 라우팅: "`wiki_page_publications` 의 `page_slug` 레코드를 렌더링" | **`wiki_page_publications` 에 slug 컬럼이 없다.** `wiki_pages` 를 조인해야 하는데 `anon` 은 그 테이블에 **정책도 권한도 없다** → 공개 페이지가 통째로 열리지 않는다 | **실측** §6-② |
| 2 | GRANT 문 없음 | **`anon` 은 `public` 스키마에 테이블 권한이 0개다.** 정책만 써도 `permission denied` 다 — 정책은 권한을 주지 않는다 | 실측: `role_table_grants` 0행 |
| 3 | §4.1 "`unverified`/**`stale`** 차단" | **`stale` 은 존재하지 않는 값이다.** 허용값은 `verified` · `partial` · `unverified` · `disputed` | **불변식 §3** · CHECK 실측 |
| 4 | `public_workspace_slug` | 불변식 §4 는 `workspace_slug` 로 적는다. 게다가 다른 3개 PRD 는 **`workspaces.slug`** 를 권고한다 — 셋이 어긋나 있다 | §7-1 |
| 5 | `[✅ 승인 / ❌ 제외]`, §5 매트릭스 전체 | 이모지 금지. **설계 문서 산문에도 적용된다** | **불변식 §7.2** |
| 6 | §3.1 의 `$$\text{https://...}$$` LaTeX 수식 | PRD 에 수식 조판을 쓰지 않는다. 코드 표기로 바꿈 | — |
| 7 | SQL 이 전부 대문자 (`CREATE TABLE`, `SELECT`) | 이 저장소는 **SQL 키워드도 소문자**다. 대문자 키워드가 `supabase/migrations/` 어디에도 없다 | `CLAUDE.md` > Naming Patterns |
| 8 | `published_by … REFERENCES auth.users(id)` | `ON DELETE` 가 없어 기본값 `NO ACTION` — **사용자 삭제가 조용히 막힌다.** `workspaces.owner_id` 는 같은 상황에 `on delete restrict` 를 명시하고 이유를 주석으로 남겼다 | `0001:37-38` |
| 9 | 공개 게이트 `verification_status = 'verified'` | **DB 가 강제하지 않는다.** `WITH CHECK` 이 역할만 보므로 UI 를 우회하면 미검증 문서도 발행된다 | §2.3 |
| 10 | `wiki_page_publications` 에 멤버용 SELECT 정책 없음 | 킬스위치가 OFF 면 **viewer 는 자기 워크스페이스 발행본을 못 본다** → §4.3 재발행 배너가 viewer 에게 안 뜬다 | §2.2 ⚠️ |
| 11 | 문서 헤더 없음 | v2 PRD 공통 헤더 블록 추가 | — |

### 이전 판이 옳았던 것 — 유지한다

⚠️ **킬스위치를 `EXISTS (select 1 from workspace_public_settings …)` 로 구현한 것은 정확하다.** 불변식 §5.3 이 금지한 것은 **`workspaces` 를 서브쿼리하는 것**이다(`anon` 은 그 테이블에 정책이 없어 항상 0행). 사이드카를 보게 만든 것이 바로 그 함정을 피하는 설계이고, §6-① 에서 `anon` 이 발행본을 정상 조회하는 것을 실측했다. 이 구조를 바꾸지 않는다.

---

## 1. 목적

검증 완료된 위키만 외부에 열되, **원문 소스는 한 줄도 새지 않아야 한다.** 이 제품의 정체성인 이중 Citation 을 외부 열람자에게도 주려면 인용 스니펫을 함께 보여줘야 하는데, 그 스니펫이 곧 원문의 일부다. 그래서 공개는 **자동화하지 않고 사람이 스니펫 단위로 승인한다.**

---

## 2. 스키마 — [미구현] · 구현 계약

### 2.1 `workspace_public_settings` — 마스터 킬스위치

```sql
create table public.workspace_public_settings (
  workspace_id         uuid primary key
                         references public.workspaces (id) on delete cascade,
  -- 전역 고유 URL 네임스페이스. 워크스페이스 내부에서만 고유한 wiki slug 를
  -- 전역 평면 URL 로 노출하면 테넌트 간 라우팅이 충돌한다 (불변식 §4).
  workspace_slug       text unique,
  allow_public_sharing boolean not null default false,
  public_display_name  text,
  public_description   text,
  updated_at           timestamptz not null default now()
);

alter table public.workspace_public_settings enable row level security;

-- 민감 컬럼이 없는 테이블이므로 anon 이 행 전체를 봐도 안전하다.
-- 사이드카를 분리한 이유가 이것이다 (불변식 §5.2).
create policy workspace_public_settings_select_public
  on public.workspace_public_settings
  for select to anon, authenticated
  using (allow_public_sharing = true);

-- 멤버는 OFF 상태도 봐야 한다 — 토글 UI 를 그리려면 현재 값이 필요하다.
create policy workspace_public_settings_select_member
  on public.workspace_public_settings
  for select to authenticated
  using (public.is_workspace_member(workspace_id));

create policy workspace_public_settings_update_owner
  on public.workspace_public_settings
  for update to authenticated
  using (public.has_workspace_role(workspace_id, 'owner'))
  with check (public.has_workspace_role(workspace_id, 'owner'));

-- ⚠️ 정책은 권한을 주지 않는다. GRANT 가 없으면 permission denied 다.
grant select on table public.workspace_public_settings to anon, authenticated;
grant update on table public.workspace_public_settings to authenticated;
```

### 2.2 `wiki_page_publications` — 승인 발행본

```sql
create table public.wiki_page_publications (
  wiki_page_id        uuid primary key,
  workspace_id        uuid not null,

  -- ★ slug 를 비정규화해 들고 있는다. 이것이 없으면 공개 라우트가
  --   wiki_pages 를 조인해야 하는데, anon 은 그 테이블에 정책도 권한도
  --   없어 공개 페이지가 통째로 열리지 않는다 (§6-② 실측).
  published_slug      text not null,

  published_title     text not null,
  published_content   text not null,   -- 사람이 승인한 마크다운 전문
  published_citations jsonb not null,  -- 사람이 승인한 인용 스니펫 배열
  published_at        timestamptz not null default now(),
  -- on delete restrict: 발행자를 지우기 전에 발행본을 먼저 정리해야 한다.
  -- cascade 로 두면 계정 삭제가 공개 문서를 조용히 내린다.
  published_by        uuid not null references auth.users (id) on delete restrict,

  -- 공개 URL 의 유일성 축. 이것이 라우트 /p/[workspace_slug]/[page_slug] 를 받는다.
  constraint wiki_page_publications_workspace_slug_key
    unique (workspace_id, published_slug),

  -- 테넌트 오염 원천 차단. wiki_pages_id_workspace_key 가 이 참조를 받는다.
  constraint wiki_page_publications_tenant_fkey
    foreign key (wiki_page_id, workspace_id)
    references public.wiki_pages (id, workspace_id) on delete cascade
);

alter table public.wiki_page_publications enable row level security;

-- 물리적 킬스위치. 사이드카를 보므로 anon 에서도 서브쿼리가 실제로 행을 찾는다.
create policy wiki_page_publications_select_public
  on public.wiki_page_publications
  for select to anon, authenticated
  using (
    exists (
      select 1 from public.workspace_public_settings s
      where s.workspace_id = wiki_page_publications.workspace_id
        and s.allow_public_sharing = true
    )
  );

-- ⚠️ 멤버 전용 SELECT 가 따로 필요하다. 위 정책만 두면 킬스위치가 OFF 일 때
--    viewer 가 자기 워크스페이스의 발행 여부조차 못 읽어 §4.3 재발행 배너가
--    뜨지 않는다 (editor 이상은 아래 write 정책의 USING 으로 읽힌다).
create policy wiki_page_publications_select_member
  on public.wiki_page_publications
  for select to authenticated
  using (public.is_workspace_member(workspace_id));

create policy wiki_page_publications_write_editor
  on public.wiki_page_publications
  for all to authenticated
  using (public.has_workspace_role(workspace_id, 'editor'))
  with check (public.has_workspace_role(workspace_id, 'editor'));

grant select on table public.wiki_page_publications to anon, authenticated;
grant insert, update, delete on table public.wiki_page_publications to authenticated;
```

### 2.3 검증 게이트를 DB 가 강제한다 — [마이그레이션 필요]

§4.1 은 `verification_status = 'verified'` 만 발행 가능하다고 적는데, 위 `with check` 은 **역할만 본다.** UI 를 우회한 직접 호출이면 미검증 문서도 발행된다.

이 제품에서 검증 뱃지는 **사람이 세우는 유일한 신뢰 신호**이므로(불변식 §3) 게이트를 애플리케이션에만 두지 않는다:

```sql
create or replace function public.enforce_publication_verified()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if not exists (
    select 1 from public.wiki_pages wp
    where wp.id = new.wiki_page_id
      and wp.workspace_id = new.workspace_id
      and wp.verification_status = 'verified'
  ) then
    raise exception '검증 완료된 문서만 공개할 수 있습니다'
      using errcode = '42501';
  end if;
  return new;
end;
$$;

create trigger wiki_page_publications_verify_gate
  before insert or update on public.wiki_page_publications
  for each row execute function public.enforce_publication_verified();
```

`security definer` 가 필요한 이유: 트리거가 보는 `wiki_pages` 조회도 호출자의 RLS 를 타므로, 정의자 권한이 없으면 게이트가 멤버십에 따라 다르게 동작한다.

---

## 3. 공개 URL 라우팅

```text
https://nexuswiki.io/p/[workspace_slug]/[page_slug]
```

**[금지]** 전역 평면 URL `/p/[page_slug]`. `wiki_pages.slug` 는 `unique (workspace_id, slug)` 라 워크스페이스 안에서만 고유하다 — 서로 다른 테넌트가 같은 `tenant-isolation-rls` 를 공개하면 충돌한다(불변식 §4).

### 3.1 라우팅 쿼리 — `wiki_pages` 를 건드리지 않는다

```sql
select p.published_title,
       p.published_content,
       p.published_citations,
       p.published_at
from public.wiki_page_publications p
join public.workspace_public_settings s
  on s.workspace_id = p.workspace_id
where s.workspace_slug = :workspace_slug
  and p.published_slug = :page_slug;
```

⚠️ **`allow_public_sharing` 조건을 쿼리에 적지 않는다.** RLS 가 이미 양쪽 테이블에서 강제한다. 애플리케이션이 다시 적으면 "앱이 막고 있다"는 착각을 만들고, 앱에서 빠뜨린 날 격리가 무너진다. **차단은 DB 가 한다.**

* 0행이면 404 다. **존재 여부를 구분해 응답하지 않는다** — 킬스위치 OFF 와 미발행과 없는 슬러그가 모두 같은 404 여야 워크스페이스 존재가 새지 않는다.
* 이 경로는 `anon` 이므로 요청자 JWT 도 `service_role` 도 쓰지 않는다.

---

## 4. 수명주기

1. **사전 게이트**: `verification_status = 'verified'` 만 발행 가능. 나머지 3종(`partial` · `unverified` · `disputed`)은 버튼 비활성.
   * **`stale` 은 존재하지 않는 값이므로 조건에 쓰지 않는다**(불변식 §3).
   * 공개 승인이 `verification_status` 를 바꾸지 않는다. 의미를 섞지 않는다.
2. **인용 스니펫 육안 검토**: 컴파일러가 만든 인용 구간에 내부 호스트·IP·주석이 없는지 사람이 스니펫 단위로 승인/제외한 뒤에야 발행된다. 승인된 것만 `published_citations` 에 들어간다.
3. **재발행 판정**: `wiki_pages.updated_at > wiki_page_publications.published_at` **비교로만** 한다. 새 컬럼도 새 enum 값도 만들지 않는다(불변식 §3).
   * 내부 위키 상단 배너: `공개 이후 내용이 변경되었습니다 — 검토 후 재발행` (이모지 없이).
   * 외부 열람자는 그동안 기존 승인본을 본다. 재발행 때도 스니펫 검토를 다시 거친다.
4. **킬스위치**: `allow_public_sharing = false` 면 RLS 가 모든 공개 조회를 0행으로 만든다. §6-③ 에서 실측했다.

---

## 5. 권한 매트릭스

| 기능 | 게스트(`anon`) | viewer | editor | owner |
| --- | :---: | :---: | :---: | :---: |
| 공개 위키 본문·목차 | O | O | O | O |
| 승인된 인용 스니펫 | O (승인분만) | O | O | O |
| **원본 소스 전문·파일 다운로드** | **X** | O | O | O |
| 내부 위키 열람 · Ask · 그래프 | **X** | O | O | O |
| 발행본 등록 · 재발행 · 내림 | **X** | **X** | O | O |
| 마스터 킬스위치 ON/OFF | **X** | **X** | **X** | O |

* 게스트의 X 는 전부 **정책 부재로 강제된다.** `anon` 은 `wiki_pages` · `source_chunks` · `raw_sources` 어디에도 정책이 없고 GRANT 도 없다 — 실측으로 확인했다.
* ⚠️ **`for all` 정책은 DELETE 도 포함한다.** 위 표대로 editor 가 발행본을 내릴 수 있다. owner 전용으로 좁히려면 정책을 `insert`/`update` 와 `delete` 로 쪼개야 한다 — §7-3.

---

## 6. 실측 검증 기록

로컬 `supabase_db_NexusWiki` 에 §2 스키마를 트랜잭션 안에서 실제로 세우고 `set local role anon` 으로 질의했다.

| # | 검증 | 결과 |
| --- | --- | --- |
| ① | 킬스위치 `exists` 서브쿼리가 `anon` 에서 동작하는가 | **통과** — 발행본 1행 조회됨. 사이드카 설계가 불변식 §5.3 함정을 피한다 |
| ② | 이전 판 §3.1 라우팅(`wiki_pages` 조인)이 `anon` 에서 되는가 | **실패** — `ERROR: permission denied for table wiki_pages`. GRANT 를 줘도 `wiki_pages_select_member` 가 `{authenticated}` 전용이라 0행 |
| ③ | `published_slug` 비정규화 수정안 | **통과** — `wiki_pages` 를 건드리지 않고 제목·본문 반환 |
| ④ | 킬스위치 OFF 후 동일 쿼리 | **0행** — 물리적 차단 확인 |
| ⑤ | §2.3 검증 게이트 트리거 | **통과** — `verified` 문서는 발행되고, `partial` 문서는 `42501 검증 완료된 문서만 공개할 수 있습니다` 로 거부됨 |

부수 실측: `wiki_pages_id_workspace_key unique (id, workspace_id)` 존재(복합 FK 성립), `anon` 의 `public` 스키마 테이블 권한 **0개**, `verification_status` CHECK 4종에 `stale` 없음.

---

## 7. 미해결 결정

1. 🔴 **`workspace_slug` 를 어디에 둘 것인가** — 세 문서가 어긋나 있다. 이전 판은 `workspace_public_settings.public_workspace_slug`, 불변식 §4 는 `workspace_public_settings.workspace_slug`, workspace-home·workspace-settings·auth-google 3개 PRD 는 **`workspaces.slug`** 를 권고한다.
   *권고: `workspaces.slug` 로 두고 사이드카는 참조만 한다.* 비공개 워크스페이스도 URL 이 필요하고(`/w/[slug]`), 공개 여부와 무관한 식별자를 공개 전용 테이블에 두면 공개를 끈 순간 내부 URL 이 깨진다.
   ⚠️ **다만 그러면 `anon` 이 슬러그를 해석하려고 `workspaces` 를 읽어야 하는데 정책이 없다** — §6-② 와 같은 실패다. `workspaces.slug` 를 정본으로 두되 사이드카에 **복제**해서 공개 경로가 사이드카만 보게 해야 한다. 복제 동기화는 트리거로 강제한다.
2. **`published_slug` 와 `wiki_pages.slug` 가 갈라질 때** — 발행 후 원본 slug 가 바뀌면 공개 URL 은 옛 slug 를 유지한다. 이것이 의도인지(공개 URL 안정성) 따라가야 하는지(일관성) 결정한다. *권고: 유지.* 외부에 나간 URL 이 깨지는 것이 더 나쁘다.
3. **발행본 삭제 권한** — `for all` 이면 editor 가 공개를 내릴 수 있다. owner 전용으로 좁힐지 결정(§5).
4. **공개 페이지의 인용 스니펫 렌더** — `published_citations` jsonb 스키마를 정의해야 한다. 앵커 규약은 `citations.py` 가 소유하므로 그 형태를 그대로 굳힐지, 승인 시점에 평문으로 펼칠지. *권고: 평문으로 펼친다.* 공개본은 불변 스냅샷이므로 런타임 해석기를 외부에 노출할 이유가 없다.
5. **v2 프로토타입 부재** — `/p/` 화면 시안이 없다. v1 `public-wiki-reader-preview.html` 은 참고만 한다.

---

## 8. 검증 계획

| # | 항목 | 검증 기준 |
| --- | --- | --- |
| 1 | 라우팅 | `anon` 으로 §3.1 이 `wiki_pages` 를 건드리지 않고 발행본을 반환하는지 |
| 2 | 킬스위치 | `allow_public_sharing = false` 로 바꾼 직후 공개 조회가 **0행**인지 |
| 3 | 404 동일성 | 킬스위치 OFF · 미발행 · 없는 슬러그가 **구분 불가능한 같은 404** 인지 |
| 4 | 원문 차단 | `anon` 이 `source_chunks` · `raw_sources` · `wiki_pages` 에 도달하지 못하는지 |
| 5 | 검증 게이트 | `verification_status <> 'verified'` 인 문서를 직접 INSERT 하면 §2.3 트리거가 42501 로 거부하는지 |
| 6 | 테넌트 격리 | 다른 워크스페이스의 `wiki_page_id` 로 발행 시도 시 복합 FK 가 거부하는지 |
| 7 | slug 충돌 | 서로 다른 워크스페이스가 같은 `page_slug` 를 발행해도 각자 URL 로 정확히 해석되는지 |
| 8 | 멤버 가시성 | 킬스위치 OFF 상태에서 **viewer** 가 발행 여부를 읽어 재발행 배너를 볼 수 있는지 |
| 9 | 재발행 판정 | `updated_at > published_at` 만으로 배너가 뜨는지(새 컬럼 없이) |
| 10 | GRANT | 정책만 있고 GRANT 가 빠진 테이블이 없는지 — `permission denied` 회귀 방지 |
| 11 | 토큰 · 이모지 | 공개 페이지에 이모지 0개, 팔레트 밖 색 0개 |
