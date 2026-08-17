# 원문 소스 관리 PRD

> **문서 상태**: 리뷰 반영판 (2026-08-17). 이전 "확정(Validated)" 판의 지원 형식·필터 축·성능 계약을 실제 구현과 대조해 정정했다.
> **기능 영역**: 원본 소스 수집, 청킹·인덱싱 상태 추적, 청크 인스펙터
> **라우트**: `/w/[workspace_id]/sources`, `/w/[workspace_id]/sources/[id]`
> **연계 프로토타입**: [`nexuswiki-source-management.html`](nexuswiki-source-management.html)
> **상위 불변 규칙**: [`PRODUCT-INVARIANTS.md`](PRODUCT-INVARIANTS.md)
> **디자인 토큰**: [`nexuswiki-design-system.css`](nexuswiki-design-system.css)

이 문서의 SQL 은 `supabase/migrations/0001`~`0014` 에 실재하는 객체만 사용한다. 새 마이그레이션이 필요한 곳은 **[마이그레이션 필요]** 로 표시한다.

---

## 1. 목적과 데이터 계약

### 1.1 목적

어떤 원본이 등록되어 있고, 청킹·인덱싱이 정상 완료되었으며, 각 소스가 어떤 위키에 인용되고 있는지를 한 화면에서 관리한다.

### 1.2 불변 소스 파이프라인 — [구현됨]

`raw_sources` 와 `source_chunks` 는 Insert-only 다. 이는 관례가 아니라 **정책의 부재로 강제된다**:

| 테이블 | SELECT | INSERT | UPDATE | DELETE |
| --- | --- | --- | --- | --- |
| `raw_sources` | member | editor | **정책 없음** | owner |
| `source_chunks` | member | **정책 없음**(워커 `service_role` 전용) | **정책 없음** | 없음 |

근거: `0004_rls_policies.sql:213-221, 266`.

⚠️ 소스 화면은 **파이프라인 인덱싱 상태만** 추적한다. `verification_status` · `confidence` · `disputed` · `verified_by` 는 `wiki_pages` 에만 있는 사람의 판단이며 소스에는 존재하지 않는다.

### 1.3 5채널 하이브리드 인덱스 — [구현됨]

| 채널 | 근거 |
| --- | --- |
| ① `wiki_embeddings` HNSW | `wiki_embeddings_embedding_idx` |
| ② `source_chunks` HNSW | `source_chunks_embedding_idx` |
| ③ `wiki_pages.search_tsv` GIN | `wiki_pages_search_tsv_idx` |
| ④ `source_chunks.search_tsv` GIN | `source_chunks_search_tsv_idx` |
| ⑤ `wiki_links` 재귀 CTE 그래프 확장 | `0011_retrieval.sql:187`, `0012_ask_citation_and_graph.sql:85` |

외부 BM25 엔진이나 그래프 DB 없이 pgvector + tsvector + 재귀 CTE 로만 구동한다.

---

## 2. 지원 형식과 한도 — 구현과 일치시킬 것

⚠️ **이전 판이 실제 구현과 달랐다.** 아래가 실제 값이다.

| 항목 | 실제 구현 | 이전 판이 적었던 값 |
| --- | --- | --- |
| 업로드 허용 MIME | `application/pdf` · `text/plain` · `text/markdown` | `.sql .pdf .md .csv .json .zip` |
| URL 수집 허용 MIME | 위 3종 + `text/html` | — |
| 업로드 상한 | **20 MiB** (`MAX_UPLOAD_BYTES`) | 50 MB |
| 버킷 상한 | 50 MiB (`0005_storage.sql:48`) | — |

근거: [`settings.py:60-62`](../../../apps/api/src/api/settings.py) `ALLOWED_UPLOAD_MIME_TYPES`, [`extract.py:37-39`](../../../packages/core/src/nexuswiki_core/extract.py) `SUPPORTED_MIME_TYPES`.

* `.sql` · `.csv` · `.json` · `.zip` 은 **현재 업로드할 수 없다.** 화면에 이 형식들을 예시로 보여주면 안 된다.
* `.sql` 파일은 `text/plain` 으로 올라올 수는 있으나 그것은 확장자가 아니라 MIME 기준이다.
* 상한은 API 설정값(20 MiB)이 보이는 값이다. 버킷 상한(50 MiB)은 방어선이지 사용자에게 약속하는 수치가 아니다.
* 새 형식 추가에 마이그레이션이 필요 없도록 MIME 검증은 의도적으로 애플리케이션 계층에 있다(`0005_storage.sql:44-45` 주석).

---

## 3. 화면 요구사항

### 3.1 상단

* **브레드크럼**: `<워크스페이스 이름> / 원문 소스` — 2계층이다(불변식 §1). 프로젝트 경로를 넣지 않는다.
* **통계 3종**:

| 지표 | 산출 |
| --- | --- |
| 총 등록 소스 | `count(raw_sources)` |
| 생성된 청크 | `count(source_chunks)` |
| 인덱싱 상태 | 실패 잡이 없으면 정상. 4.2 참조 |

* **우측 액션**: `[소스 업로드]` primary 버튼 1개.

### 3.2 필터 축 — `mime_type` 으로 고정

⚠️ 이전 판은 탭을 `SQL · PDF · 마크다운 · CSV/JSON` 이라는 **파일 포맷** 축으로 잡았는데, 이 축은 스키마에 없다.

`raw_sources` 에는 두 개의 다른 축이 있다:

| 컬럼 | 값 | 성격 |
| --- | --- | --- |
| `source_type` | `article` `paper` `book` `transcript` `clipping` `file` `text` `url` | **수집 경로/성격**. 사용자가 고른다 |
| `mime_type` | 자유 텍스트 (CHECK 없음) | **파일 포맷**. 시스템이 채운다 |

**탭 필터는 `mime_type` 을 쓴다.** 이유는 탭이 답하는 질문이 "이게 무슨 파일인가"이기 때문이다. `source_type` 은 사용자가 고르는 값이라 포맷과 어긋날 수 있다(`url` 로 수집했는데 실체는 PDF).

지원 MIME 이 3종뿐이므로 탭도 3개다: `전체` · `PDF` · `텍스트/마크다운`. 형식이 늘면 탭이 는다.

* `source_type` 은 탭이 아니라 **행 안의 메타데이터**로 표시한다.
* 업로드 모달의 종류 선택은 `source_type` 을 쓴다. 두 축을 한 컨트롤에 섞지 않는다.

### 3.3 소스 목록 테이블

| 컬럼 | 내용 |
| --- | --- |
| 소스 파일 | `mime_type` 배지 + `title` + `byte_size` |
| 연결된 위키 문서 | 이 소스를 인용하는 `wiki_pages` 칩. **4.1 성능 조건 필수** |
| 청크 및 좌표 | `count(source_chunks)` + `char_start`–`char_end` 범위 |
| 파이프라인 상태 | `jobs` 상태에서 도출. 4.2 참조 |
| 업로드 | `created_at` 상대 시간 |
| 액션 | `[더보기]` → 원본 다운로드 · 영구 삭제 |

**상태 표기**는 토큰만 쓴다(불변식 §7). 이전 판의 `#10B981` · `#2563EB` · `#E11D48` 직접 지정은 폐기한다.

| 상태 | 표기 |
| --- | --- |
| 인덱싱 완료 | `.status` + `.dot` (`--good`) |
| 처리 중 | `.status.pending` |
| 인덱싱 실패 | `.status.failed` (`--danger`) |

* **원본 다운로드**는 `raw_sources.storage_path` 와 비공개 `sources` 버킷(`0005_storage.sql:47-48`)을 쓴다. 멤버십 정책이 걸려 있다.
* 900px 이하에서는 테이블 행을 카드로 전환한다. 열을 숨기지 않는다(불변식 §7.3).

### 3.4 청크 인스펙터

행 클릭 시 우측 슬라이드아웃. 소스 메타데이터, 청크 목록(`chunk_index` 순), 선택 청크의 본문과 `char_start`–`char_end`·토큰 수.

1600px 이상에서는 슬라이드아웃이 아니라 고정 3열로 상시 노출한다.

### 3.5 업로드 모달

* 드래그앤드롭 + 지원 형식 안내는 **§2 의 실제 값**을 쓴다: `PDF · 텍스트 · 마크다운, 최대 20MB`.
* `source_type` 선택 셀렉터 (8종).
* ⚠️ **프로젝트·위키 그룹 선택은 없다.** 2계층이므로 소스는 워크스페이스에 귀속된다(불변식 §1). 컬렉션이 도입되면 그때 선택지가 생긴다.
* 업로드 즉시 백그라운드 청킹·인덱싱 큐에 진입한다. 사용자가 누르는 시작 버튼은 없다(불변식 §2).

### 3.6 영구 삭제 확인 모달

* 인용 영향도: "현재 N개 위키 문서가 이 소스를 인용하고 있습니다" — **4.1 의 인덱스가 없으면 이 조회가 전체 스캔이다.**
* 사후 조치 안내: 삭제 시 해당 위키의 인용은 레드링크(작성 대기 백로그)로 전환되고 재컴파일 잡이 큐에 오른다.
* `[취소]` / `[영구 삭제]`(`.button.danger`).

### 3.7 삭제 시 자동 재컴파일

트리거는 **삭제 성공의 부수 효과**다. 사용자가 누르는 재컴파일 버튼은 없다(불변식 §2).

1. `raw_sources` 삭제 → `source_chunks` 는 복합 FK `on delete cascade` 로 함께 삭제된다(`0002_search_schema.sql:104-106`). 애플리케이션이 따로 지우지 않는다.
2. 삭제된 소스를 인용하던 `wiki_pages` 조회 — 4.1 참조.
3. 대상 위키별로 재컴파일 잡 인큐.
4. 완료 전까지 해당 위키 상단에 `JobStepper` 진행 배너.

⚠️ **중복 큐잉 방지는 DB 가 해주지 않는다.** `jobs` 테이블에는 unique 제약도 dedup 장치도 없다(`0003_jobs.sql`). 게다가 큐는 at-least-once 다. 따라서:

* 중복 제거는 **애플리케이션이 인큐 전에** `wiki_id` 기준으로 수행한다.
* 그럼에도 경합 시 중복 인큐가 발생할 수 있으므로 **컴파일 핸들러는 멱등이어야 한다.** `(workspace_id, slug)` upsert 키가 이를 위해 존재한다.
* 이전 판의 "중복 제거하여 1건만 인큐" 표현은 DB 가 보장하는 것처럼 읽혀 폐기한다.

---

## 4. 구현 전 결정·선행 작업

### 4.1 소스 → 위키 역인용 조회에 인덱스가 없다 — [마이그레이션 필요]

§3.3 두 번째 컬럼과 §3.6·§3.7 이 모두 **소스를 인용하는 위키 찾기**를 한다. 근거는 `wiki_pages.sources jsonb`(위키를 만든 `raw_source` id 배열)인데 여기에 인덱스가 없다.

실제 실행계획:

```text
explain select id from public.wiki_pages
where sources @> '["<raw_source_id>"]'::jsonb;

  Seq Scan on wiki_pages
    Filter: (sources @> '["..."]'::jsonb)
```

`wiki_pages` 인덱스 7개 중 `sources` 를 타는 것은 없다. 결과:

* 소스 목록 화면은 **행 수 × 전체 위키 스캔**
* 소스 삭제마다 전체 위키 스캔

**선행 마이그레이션** — 이 화면 구현 전에 적용한다:

```sql
-- 소스 → 위키 역인용 조회. jsonb 배열 포함 검사(@>)를 인덱스로 받는다.
create index wiki_pages_sources_idx
  on public.wiki_pages using gin (sources jsonb_path_ops);
```

`jsonb_path_ops` 를 쓰는 이유는 `@>` 만 필요하고 키 존재 검사는 필요 없어서다 — 기본 `jsonb_ops` 보다 인덱스가 작고 빠르다.

### 4.2 파이프라인 상태를 어디서 읽는가

§3.1 "인덱싱 상태"와 §3.3 "파이프라인 상태" 열의 근거가 정해지지 않았다. `jobs` 는 워크스페이스 단위이고 `payload` 로 대상을 가리키므로, 소스별 상태를 뽑으려면 `payload` 안의 `raw_source_id` 로 조회해야 한다.

결정 필요: `jobs.payload` 조회로 갈지, `raw_sources` 에 파생 상태 컬럼을 둘지. 전자는 인덱스가 또 필요하고 후자는 Insert-only 원칙(§1.2)과 충돌한다.

### 4.3 청크 좌표 표시 범위

§3.3 "청크 및 좌표"가 소스 전체의 `char_start`–`char_end` 범위를 보여주는지 청크별인지 불명확하다. 목록에서는 전체 범위, 인스펙터에서는 청크별로 정한다.

---

## 5. 데이터베이스 계약

### 5.1 소스 목록

```sql
select rs.id,
       rs.title,
       rs.source_type,
       rs.mime_type,
       rs.byte_size,
       rs.storage_path,
       rs.created_at,
       count(sc.id)      as chunk_count,
       min(sc.char_start) as char_start,
       max(sc.char_end)   as char_end
from public.raw_sources rs
left join public.source_chunks sc
       on sc.raw_source_id = rs.id
      and sc.workspace_id = rs.workspace_id
where rs.workspace_id = :workspace_id
  and (:mime_type is null or rs.mime_type = :mime_type)
group by rs.id
order by rs.created_at desc;
```

### 5.2 소스를 인용하는 위키 (4.1 인덱스 필요)

```sql
select wp.id, wp.slug, wp.title
from public.wiki_pages wp
where wp.workspace_id = :workspace_id
  and wp.sources @> jsonb_build_array(:raw_source_id::text)
order by wp.updated_at desc;
```

### 5.3 삭제

```sql
-- source_chunks 는 복합 FK on delete cascade 로 함께 지워진다.
-- wiki_embeddings 등 다른 자식은 이 소스를 참조하지 않는다.
delete from public.raw_sources
where id = :raw_source_id
  and workspace_id = :workspace_id;
```

⚠️ RLS 의 `USING` 이 막으면 **예외가 아니라 0행**이 돌아온다. 영향 행 수 0 → HTTP 403 으로 매핑한다.

---

## 6. 검증 계획

| 단계 | 항목 | 검증 기준 |
| --- | --- | --- |
| 1 | 선행 마이그레이션 | `wiki_pages_sources_idx` 적용 후 §5.2 가 `Bitmap Index Scan` 을 타는지 `EXPLAIN` 확인 |
| 2 | 업로드 | §2 의 3종 MIME 만 통과하고 20 MiB 초과가 거부되는지 |
| 3 | 필터 | 탭이 `mime_type` 으로 필터링되고, `source_type` 은 행 메타로만 보이는지 |
| 4 | 삭제 | `raw_sources` 삭제 시 `source_chunks` 가 cascade 로 사라지고, 인용 위키에 재컴파일 잡이 큐잉되는지 |
| 5 | 멱등성 | 같은 위키에 재컴파일 잡을 2건 인큐해도 결과가 1건 처리와 동일한지 |
| 6 | 반응형 | 900px 이하 카드 전환, 640px 이하 가로 스크롤 없음 |
