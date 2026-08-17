# 작성 대기 백로그(레드링크) PRD

> **문서 상태**: 리뷰 반영판 (2026-08-17). 이전 "확정(Validated)" 판은 **화면의 절반이 스키마 없는 기능**이었다. `wiki_links` 에 존재하는 컬럼은 7개뿐인데 PRD 는 감지 경로·인용 문맥·해결 상태·수동 등록을 모두 기술했다. 실재하는 것만 남기고 나머지는 **[마이그레이션 필요]** 로 분리했다.
> **기능 영역**: 미해결 레드링크 집계, 영향도 정렬, 소스 보강 유도
> **라우트**: `/w/[workspace_id]/backlog` — **[미구현]** (라우트 자체가 없다)
> **연계 프로토타입**: **v2 시안 없음.** 상위 폴더의 `backlog-management-preview.html` 은 v1 이다
> **상위 불변 규칙**: [`PRODUCT-INVARIANTS.md`](PRODUCT-INVARIANTS.md)
> **디자인 토큰**: [`nexuswiki-design-system.css`](nexuswiki-design-system.css)

이 문서의 SQL·식별자는 `supabase/migrations/0001`~`0014` 와 `apps/` 에 실재하는 것만 쓴다. 미구현은 **[미구현]**, 새 마이그레이션이 필요하면 **[마이그레이션 필요]** 로 표시한다.

---

## 0. 이전 판에서 정정한 것

| # | 이전 판 주장 | 실제 | 근거 |
| --- | --- | --- | --- |
| 1 | `[+ 수동 백로그 등록]` 버튼 | **불가능하다.** `authenticated` 에게 `wiki_links` 는 **`grant select` 뿐**이고 정책도 `wiki_links_select_member` 하나다. INSERT 경로가 없다 | `0007:359` · `0004:274` |
| 2 | **감지 경로(Origin)** 컬럼 — `AI 컴파일 결손` / `소스 삭제 결손` | **그런 컬럼이 없다.** `wiki_links` 는 `id`·`workspace_id`·`from_wiki_id`·`target_slug`·`to_wiki_id`·`resolved`·`created_at` 7개가 전부 | `0002:163-195` |
| 3 | **인용 문맥 발췌문** — "컴파일러 LLM 이 본문에 남긴 실제 원문 컨텍스트" | **저장되지 않는다.** 링크는 `target_slug` 만 남기고 주변 문장을 보존하지 않는다 | 동일 |
| 4 | "소스가 삭제되면 인용하던 위키 부분이 자동으로 백로그로 전이" | **그런 경로가 없다.** `on delete set null (to_wiki_id)` 는 **위키 페이지**가 지워질 때 걸리고, `wiki_pages.sources` 는 jsonb 라 FK 조차 없다. 게다가 **소스 삭제 API 엔드포인트 자체가 없다**(`sources.py` 는 POST 3개뿐) | `0002:188-195` · `sources.py` |
| 5 | 필터 탭 `소스 삭제 결손 (1)` | 위 #4 로 성립하지 않는다 | — |
| 6 | "소스 업로드 시 **해당 백로그를** 즉시 해결 처리" | **특정 백로그에 소스를 붙이는 경로가 없다.** 레드링크는 `target_slug` 를 기다릴 뿐이고, 그 slug 의 위키를 만들지는 **컴파일러가 정한다** | §2.3 |
| 7 | 소스 형식 `.sql, .pdf, .md, .csv 등` | 지원은 **3종**(`application/pdf`·`text/plain`·`text/markdown`), 상한 20 MiB. `.sql`·`.csv` 는 검토 후 **제외 확정** | [`source-management-prd.md`](source-management-prd.md) §2.1–2.2 |
| 8 | `[✔ 해결 완료]` 상태 전환 | `resolved` 는 **생성 컬럼**(`to_wiki_id is not null`)이라 직접 쓸 수 없다. 그리고 해결된 링크는 백로그 목록에서 사라질 뿐 "완료" 상태로 남지 않는다 | `0002:174` |
| 9 | 이모지 `⭕` `🔗` `📊` `📘` `✔` | **§4.2 가 "Zero Emojis"라고 적어 놓고 §1·§3 에서 5종을 쓴다.** 문서가 자기 규칙을 위반한다 | **불변식 §7.2** |
| 10 | "로즈/레드 틴트 알약 칩" | **로즈는 금지 팔레트다.** 불변식이 `보라 · 파랑 · 로즈` 를 명시적으로 배제한다. 상태색은 `--good` · `--danger` 뿐 | **불변식 §7.1** |
| 11 | `#FFFFFF` · `#F8FAFC` · `#E2E8F0` 직접 지정 | 색은 토큰만 쓴다 | **불변식 §7.1** |
| 12 | 라우트 `/backlog` | 워크스페이스 스코프가 빠졌다. `/w/[workspace_id]/backlog` 이며 **아직 없다** | `app/w/[workspaceId]/` |
| 13 | 프로토타입 링크가 v1 절대경로(`file:///…`) | v2 시안이 없다. 절대경로 링크도 폐기 | — |
| 14 | 브레드크럼 `엔지니어링 코어 / 작성 대기 백로그` | 2계층이므로 형태는 맞다. `엔지니어링 코어` 가 워크스페이스 이름이라면 유지 | 불변식 §1 |

⚠️ **이 문서에서 사실이었던 것은 "레드링크가 존재하고 집계할 수 있다" 하나다.** 나머지 컬럼·상태·액션은 전부 없는 것을 있는 것처럼 적은 것이다.

---

## 1. 백로그의 실체 — [구현됨]

백로그는 별도 테이블이 아니다. **`wiki_links` 중 `to_wiki_id IS NULL` 인 행**이다.

```text
위키 본문의  [[캐시 계층 전략]]
        │
        ├─ 대상 slug 가 wiki_pages 에 있으면  → to_wiki_id 채워짐 → resolved = true
        └─ 없으면                            → to_wiki_id NULL   → resolved = false = 백로그
```

| 컬럼 | 의미 |
| --- | --- |
| `from_wiki_id` | 이 링크를 품은 위키 (= 영향받는 문서) |
| `target_slug` | 기다리는 대상 slug. **`to_wiki_id` 가 채워져도 보존된다** — 대상이 삭제되면 이 slug 로 다시 레드링크가 되어야 하므로 |
| `to_wiki_id` | 해결되면 채워진다. `NULL` 이 백로그 |
| `resolved` | **생성 컬럼**(`to_wiki_id is not null`). 직접 쓸 수 없다 |
| `created_at` | 링크 행 생성 시각 |

* **전용 인덱스가 이미 있다**: `wiki_links_unresolved_slug_idx on (workspace_id, target_slug) where to_wiki_id is null`. 백로그 조회는 이 부분 인덱스를 탄다.
* 유일성은 `(from_wiki_id, target_slug)` — 재컴파일 시 upsert 키다.

### 1.1 백로그는 어떻게 생기고 사라지는가 — [구현됨]

전부 [`link_sync.py`](../../../apps/worker/src/worker/handlers/link_sync.py) 가 소유한다. 사용자 액션이 아니다.

1. 컴파일된 본문에서 `[[...]]` 를 정규식으로 뽑아 `slugify` 한다.
2. 각 대상 slug 로 `wiki_pages` 를 찾아 있으면 `to_wiki_id`, 없으면 `NULL` 로 **업서트**한다.
3. ⚠️ **`delete_wiki_links_not_in` 으로 현재 본문에 없는 링크를 지운다.** 재컴파일로 본문에서 `[[캐시 계층 전략]]` 이 사라지면 **그 백로그 항목도 함께 사라진다.**
4. `resolve_red_links(target_slug = 이 페이지의 slug)` 로, 이 페이지를 기다리던 레드링크를 일괄 해소한다.

**따라서 백로그는 "할 일 목록"이 아니라 본문의 파생 상태다.** 사용자가 항목을 만들거나 지우거나 보류할 수 없고, 만들어도 다음 `link_sync` 가 지운다. 이것이 §2.1 수동 등록이 불가능한 이유이기도 하다.

### 1.2 이미 구현된 레드링크 표면 — [구현됨]

[`RedLinkCta.tsx`](../../../apps/dashboard/components/RedLinkCta.tsx) 가 위키 본문 안의 레드링크를 렌더한다. **백로그 화면을 새로 그리기 전에 이 계약을 따라야 한다.**

* 문구는 계약이다. **한 글자도 바꾸지 않는다**: `아직 작성되지 않음 · 지금 생성` / 아이콘 버튼 `aria-label`: `지금 생성`
* 클릭 동작: `/w/[workspaceId]/sources?prefillTitle=<제목>&tab=text` 로 이동.
  * ⚠️ **워크스페이스에 소스를 추가하는 화면으로 갈 뿐이다.** 이 백로그에 소스를 "연결"하는 것이 아니다. 컴포넌트 주석이 명시한다 — *"`wiki_pages` 행을 직접 만들거나 고치는 경로는 v1 에 없다. 실제 위키 페이지는 컴파일러가 이후 잡 체인에서 만든다."*
* 브래킷 노출 금지(`[[문서명]]`)는 이미 지켜지고 있다. 제목만 렌더하고 2줄 클램프한다.

---

## 2. 스키마가 없는 요구사항 — [마이그레이션 필요]

이전 판이 "확정"으로 적었던 것들이다. **하나같이 컬럼 한 줄 추가로 끝나지 않는다.**

### 2.1 수동 백로그 등록

* 막는 것은 UI 가 아니라 **권한이다.** `authenticated` 는 `wiki_links` 에 SELECT 만 갖는다.
* 권한을 열어도 §1.1-3 이 지운다. **사용자가 만든 행과 컴파일러가 만든 행을 구분할 방법이 없기 때문이다.**
* 하려면: `origin` 컬럼(`compiled` · `manual`) 추가 + `delete_wiki_links_not_in` 이 `manual` 을 건너뛰도록 워커 수정 + INSERT 정책(editor 이상) 추가.
* **권고: 이번 마일스톤에서 뺀다.** 백로그는 본문의 파생 상태라는 설계가 단순하고 정확하다. "쓸 예정인 문서"를 예약하는 기능은 컬렉션(불변식 §1)이 들어온 뒤에 다시 본다.

### 2.2 감지 경로(Origin)와 인용 문맥

* `origin` 은 §2.1 과 같은 컬럼을 공유한다.
* **인용 문맥은 더 비싸다.** 링크 주변 문장을 저장하려면 `link_sync` 가 본문에서 스니펫을 떠서 함께 업서트해야 하고, 재컴파일마다 갱신돼야 한다.
* **권고: 문맥은 저장하지 말고 조회 시점에 만든다.** `from_wiki_id` 로 본문을 읽어 `[[target]]` 주변을 잘라 보여주면 저장 없이 같은 값을 준다. 본문이 바뀌어도 자동으로 최신이다.

### 2.3 백로그에 소스를 붙여 해결하기

⚠️ **이건 컬럼 문제가 아니라 파이프라인 계약과의 충돌이다.** [`wiki-document-reader-prd.md`](wiki-document-reader-prd.md) §2.2 와 같은 오류다.

* `wiki_pages.sources` 는 **컴파일러가 쓰는 필드**다. 어느 위키가 무엇을 인용할지는 컴파일러가 정한다.
* 사용자가 "이 백로그에 이 소스"를 지정하는 API 도 스키마도 없다.
* 수동 연결을 허용하면 재컴파일을 유발할 수밖에 없어 **불변식 §2("수동 재컴파일 버튼 없음")** 와 부딪힌다.

**대신 실제로 일어나는 일**이 이미 충분하다: 소스를 워크스페이스에 추가하면 파이프라인이 돌고, 컴파일러가 그 slug 의 페이지를 만들면 `resolve_red_links` 가 기다리던 링크를 **일괄 해소**한다. 사용자는 "이 백로그를 해결한다"가 아니라 **"이 주제의 자료를 넣는다"** 를 한다. `RedLinkCta` 가 이미 그 동선이다(§1.2).

→ 화면은 `[+ 소스 연결]` 이 아니라 **`[소스 추가]`** 로 적고, `prefillTitle` 로 제목만 넘긴다.

### 2.4 소스 삭제로 인한 백로그

* §0-4 대로 경로가 없다. **소스 삭제 API 자체가 없다**(`sources.py` 는 POST 3개).
* source-management PRD §3.7 이 정의한 삭제 흐름은 "재컴파일 잡 인큐"이지 "레드링크 생성"이 아니다. 재컴파일 결과 본문에서 링크가 빠지면 §1.1-3 이 **링크를 지운다** — 백로그가 생기는 게 아니라 사라진다.
* **권고: 이 요구사항을 폐기한다.** 소스 삭제의 영향은 source-management PRD 가 소유한다. 두 문서에 같은 흐름을 적지 않는다.

---

## 3. 화면 요구사항 — 실현 가능한 범위

### 3.1 상단

* **브레드크럼**: `<워크스페이스 이름> / 작성 대기 백로그` — 2계층(불변식 §1).
* **통계 2종** (이전 판의 3종에서 축소):

| 지표 | 산출 | 상태 |
| --- | --- | --- |
| 미해결 백로그 | `count(distinct target_slug) where to_wiki_id is null` | **[구현됨]** |
| 영향받는 위키 | `count(distinct from_wiki_id) where to_wiki_id is null` | **[구현됨]** |
| ~~지식 완성 커버리지 %~~ | 정의가 없다 — §6-1 | **보류** |

* ⚠️ **`distinct target_slug` 로 세는 것이 중요하다.** `wiki_links` 는 (출발 문서 × 대상) 행이므로 5개 문서가 같은 주제를 가리키면 5행이다. 그대로 세면 "미해결 백로그 5건"이 되는데 실제 결손 주제는 1개다.
* **우측 액션 없음.** `[+ 수동 백로그 등록]` 은 §2.1 로 제거한다.

### 3.2 목록 테이블

정렬 기본값은 **인용 빈도 내림차순**이다 — 많이 참조될수록 먼저 쓸 가치가 있다.

| 컬럼 | 내용 | 상태 |
| --- | --- | --- |
| 백로그 주제 | `target_slug`. ⚠️ **표시용 제목이 없다** — §6-2 | [구현됨] |
| 인용 중인 위키 | `from_wiki_id` → `wiki_pages.title` 칩 N개 | [구현됨] |
| 인용 빈도 | `count(*) group by target_slug` | [구현됨] |
| 최초 감지 | `min(created_at)` 상대 시간 | [구현됨] |
| ~~감지 경로~~ | — | **[마이그레이션 필요]** §2.2 |
| 액션 | `[소스 추가]` → `sources?prefillTitle=…&tab=text` | [구현됨] §1.2 |

* **필터 탭은 `전체` 하나로 시작한다.** 이전 판의 `높은 인용 빈도` · `신규 감지` · `소스 삭제 결손` 중 앞 둘은 정렬로 충분하고 셋째는 §2.4 로 폐기된다. 축이 없는 탭을 만들지 않는다.
* 상태 표기는 토큰만 쓴다. 백로그는 미해결이 기본 상태이므로 `--danger` 를 남발하지 않는다 — **결손은 오류가 아니라 정상적인 작업 대기 상태다.**
* 900px 이하에서 행을 카드로 전환하고 열을 숨기지 않는다(불변식 §7.3).

### 3.3 상세 패널

행 클릭 시 우측 슬라이드아웃.

1. **주제와 최초 감지 시각.**
2. **인용 중인 위키 목록** — 클릭 시 해당 문서로 이동.
3. **인용 문맥** — **[미구현]** 저장하지 않는다. §2.2 권고대로 `from_wiki_id` 본문에서 조회 시점에 발췌한다.
4. **`[소스 추가]`** — §2.3. 드래그앤드롭 인제스천을 이 패널에 넣지 않는다. 소스 업로드는 `/sources` 가 소유한다.
   * 지원 형식 안내를 여기 복제하지 않는다. 복제하면 source-management PRD 와 어긋난다(이전 판이 `.sql`·`.csv` 를 적어 실제로 어긋나 있었다).

### 3.4 하지 않는 것

* **해결 완료 목록을 만들지 않는다.** 해결된 링크는 `resolved = true` 로 바뀌어 백로그에서 빠질 뿐이고, `created_at` 외에 "언제 해결됐는지"를 기록하지 않는다.
* **백로그 보류·무시·담당자 지정을 넣지 않는다.** 전부 §2.1 과 같은 벽에 부딪힌다.

---

## 4. 데이터베이스 계약

### 4.1 백로그 목록 (인용 빈도순)

```sql
select wl.target_slug,
       count(*)                     as impact,
       min(wl.created_at)           as first_detected_at,
       jsonb_agg(
         jsonb_build_object('id', wp.id, 'slug', wp.slug, 'title', wp.title)
         order by wp.title
       )                            as referencing_pages
from public.wiki_links wl
join public.wiki_pages wp
  on wp.id = wl.from_wiki_id
 and wp.workspace_id = wl.workspace_id
where wl.workspace_id = :workspace_id
  and wl.to_wiki_id is null
group by wl.target_slug
order by impact desc, first_detected_at asc;
```

**인덱스 실측** (로컬 `supabase_db_NexusWiki`):

| 데이터 형태 | 실행계획 |
| --- | --- |
| 20개 워크스페이스 · 링크 20,000행 중 미해결 1,000행(5%) | `Bitmap Index Scan on wiki_links_unresolved_slug_idx` ✅ |
| 단일 워크스페이스 · 링크 2,000행이 **전부** 미해결 | `Seq Scan` |

⚠️ **두 번째 줄은 성능 문제가 아니다.** 테이블의 모든 행이 부분 인덱스 조건에 맞으면 인덱스를 거치는 것이 손해라 플래너가 seq scan 을 고른다 — 올바른 선택이다. **`EXPLAIN` 에 `Seq Scan` 이 보인다고 인덱스를 추가하지 말 것.** 워크스페이스가 늘고 해결된 링크가 쌓이면 자동으로 인덱스 경로로 넘어간다(위 첫 줄이 그 상태다).

### 4.2 상단 통계

```sql
select count(distinct target_slug) as open_backlog,
       count(distinct from_wiki_id) as affected_pages
from public.wiki_links
where workspace_id = :workspace_id
  and to_wiki_id is null;
```

### 4.3 인용 문맥 — 조회 시점 발췌 (§2.2)

```sql
select wp.id, wp.slug, wp.title, wp.content
from public.wiki_links wl
join public.wiki_pages wp
  on wp.id = wl.from_wiki_id
 and wp.workspace_id = wl.workspace_id
where wl.workspace_id = :workspace_id
  and wl.target_slug = :target_slug
  and wl.to_wiki_id is null;
```

애플리케이션이 `content` 에서 해당 `[[...]]` 주변을 잘라 보여준다. **본문 전체를 클라이언트로 내려보내지 않는다** — 서버에서 발췌해 스니펫만 응답한다.

### 4.4 백로그는 쓰기 계약이 없다

`insert` · `update` · `delete` 계약을 **의도적으로 두지 않는다.** `authenticated` 에게 `wiki_links` 는 SELECT 뿐이고, 백로그는 `link_sync` 가 소유하는 파생 상태다(§1.1).

---

## 5. 선행 작업

| # | 작업 | 상태 |
| --- | --- | --- |
| 1 | `/w/[workspaceId]/backlog` 라우트 + 페이지 | **[미구현]** — 라우트 자체가 없다 |
| 2 | 백로그 조회 API | **[미구현]** — `apps/api` 는 `wiki_links` 를 **한 번도 참조하지 않는다.** 그래프 RPC(`wiki_graph_neighborhood`)만 간접 사용 |
| 3 | 상단 내비게이션 진입점 | `NavShell` 의 `ROUTES` 는 소스·질문하기·위키·설정 4개다. 백로그를 5번째로 넣을지 위키 화면의 탭으로 둘지 — §6-3 |
| 4 | v2 프로토타입 | 없다. 만들 경우 `RedLinkCta` 문구 계약(§1.2)을 그대로 따를 것 |

---

## 6. 미해결 결정

1. **"지식 완성 커버리지 %" 의 정의** — 이전 판의 `88.4%` 는 근거가 없다. 후보: (a) `미해결 레드링크가 0인 위키 / 전체 위키`, (b) `해결된 링크 / 전체 링크`. *권고: (a)*. 문서 단위라 사용자가 "어느 문서가 미완성인지"로 바로 이어갈 수 있다. 정의 확정 전까지 지표를 표시하지 않는다.
2. **백로그 표시 제목** — `target_slug` 는 slug 다(`캐시-계층-전략`). 원문 `[[캐시 계층 전략]]` 의 제목은 **저장되지 않는다** — `link_sync` 가 `slugify` 한 값만 넣는다. 후보: (a) slug 를 역변환해 보여준다(하이픈→공백, 부정확), (b) `wiki_links.target_title` 컬럼 추가 **[마이그레이션 필요]**, (c) `from_wiki_id` 본문에서 원문 표기를 찾아 쓴다. *권고: (c)* — §2.2·§4.3 의 발췌 조회와 같은 경로를 재사용하므로 컬럼이 늘지 않는다.
3. **진입 경로** — 최상위 내비게이션 5번째 항목 vs 위키 화면의 탭. *권고: 위키 화면의 탭.* 백로그는 위키의 파생 상태이고, 그래프가 `/ask?tab=graph` 로 통합된 선례가 있다.
4. **수동 백로그 등록** (§2.1) — 이번 마일스톤 제외 권고. 되살린다면 컬렉션 설계와 함께 본다.
5. **인용 문맥 저장 vs 조회 시점 발췌** (§2.2) — 발췌 권고.

---

## 7. 검증 계획

| # | 항목 | 검증 기준 |
| --- | --- | --- |
| 1 | 집계 정확성 | 5개 문서가 같은 주제를 가리킬 때 "미해결 백로그"가 **5 가 아니라 1** 로 세어지는지(§3.1) |
| 2 | 인덱스 | §4.1 이 `wiki_links_unresolved_slug_idx` 를 타는지 `EXPLAIN`. **단, 미해결이 테이블 대부분인 초기 상태의 `Seq Scan` 은 정상이다**(§4.1 실측표) |
| 3 | 자동 해소 | 백로그 주제와 같은 slug 의 위키가 컴파일되면 `resolve_red_links` 로 목록에서 사라지는지 |
| 4 | 자동 소멸 | 재컴파일로 본문에서 `[[...]]` 가 빠지면 해당 백로그도 사라지는지(§1.1-3) |
| 5 | 쓰기 차단 | `authenticated` JWT 로 `wiki_links` INSERT/UPDATE/DELETE 시도 시 전부 막히는지 |
| 6 | 문구 계약 | 레드링크 CTA 가 `아직 작성되지 않음 · 지금 생성` 을 글자 그대로 쓰는지 |
| 7 | 이동 경로 | `[소스 추가]` 가 `sources?prefillTitle=…&tab=text` 로 가고 제목이 채워지는지 |
| 8 | 브래킷 노출 | 목록·칩·발췌문 어디에도 `[[...]]` 원문이 보이지 않는지 |
| 9 | 반응형 | 900px 이하 카드 전환, 640px 이하 가로 스크롤 없음 |
| 10 | 토큰 · 이모지 | 이모지 0개, 로즈·보라·파랑 등 팔레트 밖 색 0개 |
