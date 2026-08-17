# 위키 문서 리더 PRD

> **문서 상태**: 리뷰 반영판 (2026-08-17). 이전 "확정(Validated)" 판의 소스 연결 의미·아카이브 계약·단계 수·유사도 표기를 실제 구현과 대조해 정정했다.
> **기능 영역**: 컴파일된 위키 문서 읽기, 원문 출처 역추적, 지식 연결망
> **라우트**: `/w/[workspace_id]/wiki/[slug]`
> **연계 프로토타입**: [`nexuswiki-wiki-document-reader.html`](nexuswiki-wiki-document-reader.html)
> **상위 불변 규칙**: [`PRODUCT-INVARIANTS.md`](PRODUCT-INVARIANTS.md)
> **디자인 토큰**: [`nexuswiki-design-system.css`](nexuswiki-design-system.css)

이 문서의 SQL·식별자는 `supabase/migrations/0001`~`0014` 와 `apps/` 에 실재하는 것만 쓴다. 미구현은 **[미구현]**, 새 마이그레이션이 필요하면 **[마이그레이션 필요]** 로 표시한다.

---

## 1. 목적

컴파일된 위키를 읽으면서 **"이 내용이 원본 어디에 근거하는가"**를 그 자리에서 역추적할 수 있어야 한다. 이중 Citation 의 위키 쪽 절반이 이 화면이다 — 여기서 원문으로 내려가는 경로가 끊기면 이 제품은 그냥 또 하나의 RAG 챗봇이 된다.

---

## 2. 화면 요구사항

### 2.1 문서 헤더

* **브레드크럼**: `<워크스페이스 이름> / <문서 제목>` — 2계층이다(불변식 §1). 이전 판의 `엔지니어링 코어 / 데이터베이스 & RLS / 문서명` 3계층은 폐기한다.
* **제목** + 즐겨찾기 토글.
  * ⚠️ **[미구현]** 즐겨찾기 저장소가 없다. workspace-home PRD §4.1 과 같은 항목이며 함께 결정한다.
* **검증 뱃지**: `verification_status = 'verified'` 일 때만 `.badge.verified` 로 표기한다.
  * 허용값은 `verified` · `partial` · `unverified` · `disputed` 4종이다. **`stale` 은 존재하지 않는다**(불변식 §3).
  * 색은 토큰만 쓴다. 이전 판의 `#ECFDF5` · `#059669` 직접 지정은 폐기한다(불변식 §7).
* **메타 통계 3종**:

| 지표 | 산출 |
| --- | --- |
| 인용된 원문 소스 | `jsonb_array_length(wiki_pages.sources)` |
| 최종 컴파일 시점 | `wiki_pages.updated_at` 상대 시간 |
| 인용 중인 백링크 | `wiki_links` 중 `to_wiki_id = <현재 문서>` 인 행 수 |

### 2.2 상단 액션

* `[소스 추가]` — ⚠️ **이 버튼은 워크스페이스에 원문을 추가한다. "이 문서에 소스를 연결"하는 것이 아니다.**

  이전 판은 "새로운 원본 문서나 청크를 **이 위키 문서에 연결**"이라고 적었으나 그런 경로는 없다. `wiki_pages.sources` 는 컴파일러가 쓰는 필드이고(`0001` 주석: "이 위키를 만든 raw_source id 배열"), 어느 위키가 무엇을 인용할지는 **컴파일러가 정한다.** 사용자가 특정 위키에 소스를 붙이는 API 도 스키마도 없다.

  게다가 수동 연결을 허용하면 재컴파일을 유발할 수밖에 없어 불변식 §2("수동 재컴파일 버튼 없음")와 부딪힌다. 소스를 추가하면 파이프라인이 알아서 이 문서를 갱신한다 — 그것이 이 제품의 계약이다.

* `[더보기]` 드롭다운:
  1. **문서 링크 복사** — 현재 URL 을 클립보드로.
  2. **마크다운으로 내보내기** — 본문을 `.md` 로 다운로드.
  3. **위키 문서 아카이브** — ⚠️ **[마이그레이션 필요]**. 2.6 참조.

### 2.3 본문 캔버스

* 본문 폭 780–840px(디자인 시스템 §레이아웃).
* **이중 Citation 인라인 칩** — 원문의 앵커를 렌더링한 것이다.

  앵커 규약은 [`citations.py`](../../../packages/core/src/nexuswiki_core/citations.py) 가 소유한다:

  | 패턴 | 형태 | 용도 |
  | --- | --- | --- |
  | `ISSUED_ANCHOR_PATTERN` | `[[wiki:w1]]` · `[[src:s1]]` | Ask 응답에서 서버가 실제 발급한 앵커. 좁게 매치 |
  | `BROAD_ANCHOR_PATTERN` | `[[wiki:...]]` · `[[src:...]]` | 수집 시점. 관대하게 매치 |

  * **위키 참조 칩**(`wiki:`): 클릭 시 해당 문서로 이동.
  * **원문 소스 칩**(`src:`): 클릭 시 출처 대조 서랍 오픈.
  * **브래킷 노출 금지**: 렌더링된 본문에 `[[wiki:w1]]` 원문이 그대로 보이면 안 된다. 알약형 칩으로 치환한다.
  * ⚠️ 이전 판은 이 문법을 `[[문서명]]` 으로 적었으나 실제는 `[[wiki:wN]]` · `[[src:sN]]` 이다. 발급되지 않은 앵커는 `strip_forged_anchors` 로 제거된다 — LLM 이 지어낸 인용을 막는 장치이므로 렌더러가 임의 복원해서는 안 된다.

### 2.4 우측 패널 — 목차 · 연결된 지식

* 접기/펼치기 가능. 닫으면 본문이 넓어진다.
* **목차**: 스크롤 위치에 따라 활성 섹션 표시.
* **연결된 지식 그래프**: `[인용 위키] → [현재 문서] → [참조 위키]` 흐름.

  근거는 **[구현됨]** [`wiki_graph_neighborhood(p_workspace_id, p_seed_wiki_id, p_fanout, p_total_limit)`](../../../supabase/migrations/0012_ask_citation_and_graph.sql) 이다. `(from_wiki_id, to_wiki_id, depth)` 를 돌려주며 `authenticated` 에게 EXECUTE 가 부여되어 있어 사용자 경로에서 호출 가능하다.

  * `p_fanout` 은 1–20 만 허용된다. 화면이 이 범위를 넘겨 호출하지 않는다.
  * 미해결 링크(`resolved = false`)는 레드링크로 구분 표기한다 — 클릭하면 문서가 아니라 작성 대기 백로그로 간다.

### 2.5 출처 대조 서랍

원문 소스 칩 클릭 시 열린다. 표시 항목:

* 해당 `source_chunks` 의 본문
* `char_start`–`char_end` 좌표
* 원본 파일명(`raw_sources.title`)과 형식

⚠️ **유사도 점수는 표기하지 않는다.** 이전 판은 "유사도 0.91"을 적었으나 근거가 없다. `similarity` 를 돌려주는 것은 [`find_similar_wiki_pages`](../../../supabase/migrations/0012_ask_citation_and_graph.sql) 하나뿐인데,

* **위키↔위키** 유사도지 위키↔원문 청크가 아니고,
* 주석이 명시하듯 *"호출자는 워커의 충돌 감지 잡뿐(사용자 요청 경로 아님)"* 이라 `EXECUTE` 가 `service_role` 에게만 부여되어 있다.

사용자에게 필요한 것은 점수가 아니라 **원문 그 자체**다. 서랍은 청크 본문과 좌표만 보여준다.

### 2.6 아카이브 — [마이그레이션 필요]

이전 판은 아카이브를 "`archived_at` 타임스탬프 소프트 삭제"로 정의했으나 **`archived_at` 은 마이그레이션·API·워커 어디에도 없다.** 메뉴에 한 줄 더하는 일이 아니다:

1. `wiki_pages.archived_at timestamptz` 컬럼 추가
2. **5채널 전부에 제외 필터** — `wiki_pages` 벡터·FTS 두 채널과 `wiki_links` 그래프 확장이 아카이브 문서를 타지 않아야 한다
3. `wiki_embeddings` 를 지울지 남길지 결정 — 남기면 벡터 채널에서 계속 잡히고, 지우면 복원 시 재임베딩 비용이 든다
4. 복원 경로 정의

**이번 마일스톤 범위에서 뺄 것을 권한다.** 삭제는 이미 `wiki_links` 레드링크 메커니즘이 안전하게 받아준다(대상 삭제 시 `on delete set null (to_wiki_id)` 로 링크가 레드링크로 되돌아간다). 아카이브가 주는 추가 가치가 위 4단계 비용을 넘지 않는다.

### 2.7 자동 재컴파일 진행 배너

원문 변경으로 컴파일 잡이 도는 동안 헤더 아래 `JobStepper` 배너를 노출한다. 사용자가 누르는 재컴파일 버튼은 없다(불변식 §2).

⚠️ **단계 수를 문서에 하드코딩하지 않는다.** 이전 판은 "3/4 단계"라고 적었으나 실제 값은 두 곳이 다르다:

| 소유자 | 값 |
| --- | --- |
| 서버 `CHAIN_ORDER` ([`jobs.py:29`](../../../apps/api/src/api/routers/jobs.py)) | `parse` · `compile` · `link_sync` · `embed` · `conflict_check` — **5단계** |
| 대시보드 `STAGE_TYPES` ([`JobStepper.tsx`](../../../apps/dashboard/components/JobStepper.tsx)) | 위 4개 (`conflict_check` 제외) |

API 가 `chain_position` 과 `chain_total` 을 내려주므로 화면은 그 값을 그대로 쓴다. 단계 라벨도 서버의 `STEP_LABELS` 가 소유한다(`원문 파싱` · `위키 컴파일` · `링크 동기화` · `임베딩` · `지식 충돌 검사`).

> **미해결**: 서버 5단계와 대시보드 4단계 중 어느 쪽이 사용자에게 보이는 총계인지 정해야 한다. `conflict_check` 를 진행 표시에 포함할지가 쟁점이다.

### 2.8 웹에 공개

`[웹에 공개]` 버튼과 스니펫 승인 모달, 재발행 수명주기는 **[`public-sharing-prd.md`](public-sharing-prd.md) 가 소유한다.** 이 문서는 진입점만 정의하고 계약을 복제하지 않는다 — 같은 규칙을 두 곳에 적으면 한쪽만 고쳐질 때 어긋난다.

이 화면이 지켜야 할 것만 적는다:

* 사전 게이트는 `verification_status = 'verified'` 다. 나머지 3종은 버튼을 비활성화한다(`stale` 은 존재하지 않는 값이므로 조건에 쓰지 않는다).
* 발행 이후 갱신 판정은 `wiki_pages.updated_at > wiki_page_publications.published_at` 비교로만 한다. 새 컬럼이나 enum 값을 만들지 않는다(불변식 §3).
* **[미구현]** `wiki_page_publications` · `workspace_public_settings` 둘 다 마이그레이션이 없다.

---

## 3. 데이터베이스 계약

### 3.1 문서 조회

```sql
select wp.id, wp.slug, wp.title, wp.category, wp.content,
       wp.verification_status, wp.confidence, wp.disputed,
       wp.sources, wp.updated_at
from public.wiki_pages wp
where wp.workspace_id = :workspace_id
  and wp.slug = :slug;
```

`(workspace_id, slug)` UNIQUE 인덱스를 탄다.

### 3.2 인용된 원문 소스

```sql
-- wiki_pages.sources 는 raw_source id 배열이다.
select rs.id, rs.title, rs.mime_type, rs.storage_path
from public.raw_sources rs
where rs.workspace_id = :workspace_id
  and rs.id = any (
    select (jsonb_array_elements_text(:sources::jsonb))::uuid
  );
```

### 3.3 백링크 (이 문서를 인용하는 위키)

```sql
select wp.id, wp.slug, wp.title
from public.wiki_links wl
join public.wiki_pages wp
  on wp.id = wl.from_wiki_id
 and wp.workspace_id = wl.workspace_id
where wl.workspace_id = :workspace_id
  and wl.to_wiki_id = :wiki_id;
```

### 3.4 연결된 지식 그래프

```sql
select * from public.wiki_graph_neighborhood(
  :workspace_id, :wiki_id, p_fanout => 10, p_total_limit => 100
);
```

`p_fanout` 은 1–20 범위를 벗어나면 함수가 거부한다.

---

## 4. 검증 계획

| 단계 | 항목 | 검증 기준 |
| --- | --- | --- |
| 1 | 인용 칩 | 렌더링된 본문에 `[[wiki:wN]]`·`[[src:sN]]` 원문이 노출되지 않는지. 발급되지 않은 앵커가 복원되지 않는지 |
| 2 | 출처 대조 서랍 | 청크 본문과 `char_start`–`char_end` 가 원문과 일치하는지. 유사도 점수가 표기되지 않는지 |
| 3 | 검증 뱃지 | `verified` 에서만 표시. `partial`·`unverified`·`disputed` 에서 미표시 |
| 4 | 그래프 | `wiki_graph_neighborhood` 호출이 `p_fanout` 1–20 을 지키는지. 레드링크가 구분 표기되는지 |
| 5 | 진행 배너 | 단계 총계가 API 의 `chain_total` 을 따르는지(하드코딩 없음) |
| 6 | 반응형 | 본문 폭 780–840px 유지, 640px 이하 가로 스크롤 없음 |
