# NexusWiki — 세션 핸드오프

**최종 갱신:** 2026-08-01
**단계:** Phase 1 (데이터 계층) — 스키마 레이어 완료 · 32개 태스크 중 4개 완료
**다음 작업:** `P1-SEED-01` 프롬프트 템플릿 시드, 그다음 Phase 2 (`P0-INIT-01/02` → `P2-*`)

---

## 0. 30초 요약

Cairni 스타일 Living Wiki SaaS를 그린필드로 짓는 중입니다. 원시 소스(PDF/URL/텍스트)를 넣으면 LLM이 위키로 컴파일하고, 하이브리드 검색으로 **원문 + 위키 이중 출처**를 단 답변을 제공합니다.

이전 세션에서 한 일은 두 가지입니다. **(1)** 원래 계획서 기반 체크리스트를 리뷰해 핵심 기능 3개가 데이터 모델에 대응물이 없다는 걸 찾아내고, 인터뷰로 9개 결정을 확정한 뒤 체크리스트를 전면 재작성(19 → 32 태스크). **(2)** 로컬 Supabase 스택을 띄우고 코어 스키마(`0001`)를 적용·검증.

이번 세션에서는 `git init` + 최초 커밋을 하고, 검색 스키마(`0002`) · 잡 큐(`0003`) · RLS 정책(`0004`)을 작성·적용·검증했습니다. **Phase 2의 병목이던 스키마 레이어가 전부 끝났습니다.** 9개 테이블에 정책이 붙었고 38개 격리 케이스가 통과합니다. 이제 백엔드 코드를 붙일 차례입니다.

---

## 1. 확정된 결정 (재논의 불필요)

전부 사용자 인터뷰로 확정했고, 근거는 `checklists.json`의 `decisions` 블록에 있습니다.

| 항목 | 결정 | 핵심 이유 |
|---|---|---|
| 테넌시 | **팀 우선** | `workspace_members` + 역할 기반 RLS 필수, `disputed` 기능이 의미를 가짐 |
| 그래프 DB | **Neo4j 제외** | 고유 가치인 GDS는 Aura 기본 티어에 없음. 이 규모에선 순회 성능 이점 없음. 팀 모드에선 Neo4j에 RLS가 없어 보안 부담까지 추가. `wiki_links` + recursive CTE로 대체 |
| 한국어 검색 | **앱 레이어 bigram + tsvector** | Postgres 기본 FTS는 한국어 형태소 분석기 없음. pg_bigm/pgroonga는 Supabase 미제공. bigram은 의존성 0이고 사내 약어·신조어 누락 없음 |
| 렌즈 필터 | **`wiki_pages.category` 재사용** | 렌즈 라벨을 `[전체]/[개념]/[엔티티]/[가이드]/[맵]`으로. 스키마 변경 0 |
| 원본 파일 | **Supabase Storage 보관** | "불변 원본 보존" 약속 이행 + 파서 개선 시 재처리 경로 |
| LLM | **OpenRouter 경유, 모델은 env `LLM_MODEL`** (기본 `claude-sonnet-4-6`) | 모델 교체 자유도 |
| 구조화 출력 | **프롬프트 + Pydantic 검증 + 재시도(3회)** | OpenRouter로는 Anthropic 네이티브 `output_config.format`을 못 씀 |
| 잡 큐 | **Postgres `jobs` 테이블 + `FOR UPDATE SKIP LOCKED` 워커 폴링** | 새 인프라 0, 잡 상태를 그대로 프론트에 노출 |
| DB 접근 | **하이브리드** — 사용자 요청은 요청자 JWT, 워커/마이그레이션만 `service_role` | `service_role`은 RLS를 완전 우회. 사용자 경로에 JWT를 쓰면 DB가 격리를 강제해 코드 실수를 막아줌 |
| 배포 | **Railway** (api + worker 두 서비스) | Hobby $5/월은 **워크스페이스 단위** 구독(서비스 단위 아님). CPU 실사용분 과금이 LLM 대기 워커에 유리 |

### "5-Way" 검색 채널의 정의

계획서에 정의가 없던 항목입니다. Neo4j 없이도 5개가 성립합니다.

1. `wiki_embeddings` 벡터 유사도 (pgvector HNSW)
2. `source_chunks` 벡터 유사도 (pgvector HNSW)
3. `wiki_pages` bigram tsvector 어휘 검색
4. `source_chunks` bigram tsvector 어휘 검색
5. `wiki_links` N-hop 그래프 확장 (recursive CTE)

---

## 2. 현재 진척

```
[x] P1-DB-01   코어 스키마          — 적용·검증 완료
[x] P1-DB-02   검색 스키마          — 적용·검증 완료 (EXPLAIN 5채널 전부 인덱스 사용 확인)
[x] P1-DB-03   jobs 테이블 + 큐 함수 — 적용·검증 완료 (8워커 400잡 동시성 통과)
[x] P1-SEC-01  RLS 정책            — 적용·검증 완료 (38/38 격리 케이스 통과)
[~] P0-INIT-00 Supabase 셋업        — 로컬만 완료, 클라우드 미생성
[ ] P1-SEED-01 프롬프트 템플릿 시드   ← 다음 (0006, 스키마 의존 없음)
[ ] P0-INIT-01 monorepo 구조        ← 그다음. 여기서부터 코드
[ ] P0-INIT-02 FastAPI 스캐폴딩
```

**스키마 레이어는 끝났습니다.** 남은 Phase 1 작업은 시드 하나뿐이고, 이후는 전부 애플리케이션 코드입니다.

### 디스크상의 파일

```
checklists.json                        32개 태스크 + decisions + open_questions
supabase/config.toml                   포트를 544xx로 수정함 (§4 참조)
supabase/migrations/0001_core_schema.sql
supabase/migrations/0002_search_schema.sql
supabase/migrations/0003_jobs.sql
supabase/migrations/0004_rls_policies.sql
HANDOFF.md                             이 문서
```

### `0001`에서 원안 DDL을 바꾼 것 (근거는 `checklists.json` → `P1-DB-01.deviations_from_plan`)

- `text` PK → **`uuid` PK + `gen_random_uuid()`**
- `wiki_pages.related_wikis jsonb` **제거** → `0002`의 `wiki_links`로 정규화 (jsonb 배열은 인덱스/조인 불가 → 5번 채널에 못 씀)
- `workspaces.owner_id` **추가** (원안에 소유자 개념 부재 → RLS 기준점 없었음)
- **소유자 자동 멤버 등록 트리거** 추가 — 멤버 0명 워크스페이스는 RLS 하에서 영구 접근 불가가 되므로 DB가 보장
- **RLS를 `0001`에서 선행 활성화** (정책 없음 = 전면 거부) — 정책 붙이기 전 노출 창 제거
- `source_type`에 `'url'` 추가, `prompt_templates.is_default` 유일성을 partial unique index로 강제

---

## 3. 방금 끝난 것 (1): `P1-DB-02` 검색 스키마

`supabase/migrations/0002_search_schema.sql`. 2000행을 시드해 `EXPLAIN ANALYZE` 13종으로 검증했습니다. 5-Way 채널 5개가 전부 인덱스를 탑니다.

| 채널 | 확인된 플랜 |
|---|---|
| 1 `wiki_embeddings` 벡터 | `Index Scan using wiki_embeddings_embedding_idx` (HNSW) |
| 2 `source_chunks` 벡터 | `Index Scan using source_chunks_embedding_idx` (HNSW) |
| 3 `wiki_pages` 어휘 | `Bitmap Index Scan on wiki_pages_search_tsv_idx` (GIN) |
| 4 `source_chunks` 어휘 | `Bitmap Index Scan on source_chunks_search_tsv_idx` (GIN) |
| 5 `wiki_links` 3-hop CTE | `Index Scan using wiki_links_from_idx` |

red link 삽입/해소/복귀, 교차 테넌트 차단, 슬라이스 정합성 2000/2000, 제약 6종 거부, 신규 3테이블 RLS 전면 거부까지 전부 통과.

### 원안에서 바꾼 것 (근거는 `checklists.json` → `P1-DB-02.deviations_from_plan`)

- **`wiki_pages.search_tsv` 추가** — 채널 3의 물리 컬럼이 `0001` 어디에도 없었습니다. 채널이 아예 성립 불가였음
- **`raw_sources`/`wiki_pages`에 `(id, workspace_id)` 복합 UNIQUE 추가** → 자식 테이블이 복합 FK를 겁니다. 워커는 `service_role`이라 RLS를 우회하므로(§5) 테넌트 경계를 지켜줄 장치가 이것뿐입니다. 잘못된 `workspace_id` 삽입이 FK 위반으로 거부되는 것까지 확인
- **`wiki_embeddings.chunk_index` 추가** — 순번이 없으면 재임베딩 시 멱등 upsert 키가 없어 중복 행이 쌓입니다
- **`wiki_links.resolved`를 generated column으로** — `to_wiki_id`와 따로 관리하면 어긋납니다. (한국어 토크나이징과 무관하므로 generated가 안전한 자리)
- **`to_wiki_id` FK를 `on delete set null (to_wiki_id)`** (PG15+ 컬럼 지정) — 대상 삭제 시 red link로 복귀. 컬럼을 지정하지 않으면 `workspace_id`까지 NULL이 되어 NOT NULL 위반
- **`tsv_tokenizer_version smallint`** 를 `source_chunks`/`wiki_pages`에 — 토크나이저 교체 시 재색인 대상을 전수 재처리 없이 골라내기 위함 (§5의 함정)
- **pgvector는 `extensions` 스키마**, 마이그레이션 내에서는 `extensions.vector` / `extensions.vector_cosine_ops`로 수식 — 실행 롤의 `search_path`에 의존하지 않기 위함

---

## 3b. 방금 끝난 것 (2): `P1-DB-03` 잡 큐

`supabase/migrations/0003_jobs.sql`. 테이블 + 큐 조작 함수 4종.

### 상태 전이

```text
  queued ──claim──> running ──complete──> succeeded
    ^                  │
    │                  ├──fail (attempts < max)──> failed ──run_after 경과──┐
    │                  └──fail (attempts >= max)──> dead                    │
    └────────────────────────── reap (락 타임아웃) ───────────────────────────┘
```

`failed`는 종착점이 아니라 **"직전 시도 실패, 백오프 후 재시도 예정"** 입니다. 사람이 손대야 하는 종착점은 `dead` 하나뿐. 둘을 나눠 두면 프론트가 "3번 중 2번째 실패, 4분 후 재시도"를 그대로 보여줄 수 있습니다.

### 워커(`P2-JOB-01`)가 쓸 인터페이스

```sql
claim_job(worker_id, types[])                  -- 점유. SKIP LOCKED. 없으면 0행
complete_job(job_id)                           -- succeeded
fail_job(job_id, error, backoff, max_backoff)  -- 재시도 여지 있으면 failed+백오프, 없으면 dead
reap_stale_jobs(timeout)                       -- 락 타임아웃 잡을 queued로 회수
```

⚠️ **`jobs`를 직접 UPDATE하지 마세요.** 락 일관성 CHECK와 `attempts` 회계가 함수 안에 있습니다. 네 함수 모두 `service_role` 전용이며 `anon`/`authenticated`의 EXECUTE는 회수해 뒀습니다.

### 검증

5000행 시드 후 폴링 쿼리가 `jobs_poll_idx` 부분 인덱스를 타는 것 확인. 기능 10종(백오프 재예약, `max_attempts` 소진 → dead, 락 회수, 제약 4종, 권한) 통과.

동시성 — 이게 이 태스크의 핵심 합격 기준이었습니다.

- 잡 2개 / 워커 2개 → 서로 다른 잡 점유
- 잡 1개 / 워커 2개 → 두 번째 워커가 **172ms 만에 빈손 반환** (첫 워커의 5초 락에 블로킹되지 않음)
- **8워커 × 400잡 → `sum(attempts) = 400`.** 모든 잡이 정확히 1회씩 점유됨. 잔여 락 0행, 중복 처리 0건

### 원안에서 바꾼 것 (근거는 `checklists.json` → `P1-DB-03.deviations_from_plan`)

- **`run_after` 추가** — 백오프 없이 재시도하면 워커가 LLM/임베딩 API를 타이트 루프로 때립니다. 기본값이 `now()`라 신규 잡은 즉시 대상이자 FIFO
- **`attempts`를 fail이 아니라 claim 시점에 증가** — 워커를 죽이는 독약 잡이 무한 루프를 돌지 않습니다 (죽어도 reap 후 재시도에서 소진)
- **`jobs_lock_consistency` CHECK** — `running`이면 락 필수, 아니면 NULL 필수. 완료/회수가 락을 안 지우고 빠져나가는 버그를 DB가 막습니다
- **`type`에 CHECK 열거를 걸지 않음** — `0001`/`0002`의 하우스 스타일과 유일하게 다른 지점입니다. 계획서가 명시하는 잡 종류는 `compile` 하나뿐이고 Phase 2에서 계속 바뀝니다. 대신 워커가 미등록 type을 즉시 `dead` + `last_error`로 보내야 합니다
- **큐 함수의 `anon`/`authenticated` EXECUTE 회수** — Supabase는 public 스키마 함수에 기본 실행 권한을 줍니다. 놔두면 PostgREST `/rpc/`로 남의 잡을 점유·종료할 수 있습니다

---

## 3c. 방금 끝난 것 (3): `P1-SEC-01` RLS 정책

`supabase/migrations/0004_rls_policies.sql`. **9개 테이블 전부에 정책이 붙었습니다.** 워크스페이스 A(owner/editor/viewer) + B(owner) + 외부인/비멤버 픽스처로 **38개 케이스 전부 통과**.

### 권한 모델

| | SELECT | INSERT | UPDATE | DELETE |
|---|---|---|---|---|
| `workspaces` | 멤버 | 본인 소유로만 | **owner** | owner |
| `workspace_members` | 멤버 | **owner** | **owner** | **owner** |
| `raw_sources` | 멤버 | editor | **없음(불변)** | owner |
| `wiki_pages` | 멤버 | editor | editor | owner |
| `source_chunks` / `wiki_embeddings` / `wiki_links` | 멤버 | **없음** | **없음** | **없음** |
| `prompt_templates` | 멤버 + 전역 | editor | editor | owner |
| `jobs` | 멤버 | **없음** | **없음** | **없음** |

굵은 칸이 "멤버=SELECT / editor=INSERT·UPDATE / owner=DELETE" 기본 규칙에서 벗어난 곳이고, 이유는 각각 마이그레이션 주석과 `checklists.json` → `P1-SEC-01.deviations_from_plan`에 있습니다. 요약하면:

- **`workspaces` UPDATE = owner** — 이 UPDATE는 곧 `owner_id` 이전(소유권 양도)입니다. editor에게 열면 editor가 스스로를 소유자로 만듭니다
- **`workspace_members` 쓰기 = owner** — editor에게 INSERT를 열면 자신을 `owner` 역할 행으로 추가해 즉시 권한 상승이 됩니다
- **파생 3종 읽기 전용** — 워커가 만드는 데이터입니다. 특히 `source_chunks` INSERT를 열면 editor가 원문에 없는 청크를 심어 **이중 Citation의 원문 측 인용을 위조**할 수 있습니다. 워커는 `service_role`(BYPASSRLS)이라 무영향
- **`raw_sources` UPDATE 정책 없음** — "불변 원본 보존" 약속을 DB가 강제. 재처리는 워커 경로

### 별도로 추가한 것

- **`protect_owner_membership` 트리거** — 소유자가 자기 멤버십 행을 지우거나 역할을 낮추거나 `user_id`를 바꾸는 걸 차단합니다. `0001`이 "멤버 0명 워크스페이스"를 자동 등록 트리거로 막았는데, **등록된 뒤 지우면 같은 상태로 되돌아갑니다** (`owner_id`는 그대로인데 정작 그 사람이 관리 불가)
- **`workspaces` SELECT에 `owner_id = auth.uid()` 조건** — `insert ... returning *`의 RETURNING은 SELECT 정책을 통과해야 하는데, 소유자를 멤버로 넣는 `0001`의 트리거는 **AFTER 트리거라 그 시점엔 멤버십 행이 없습니다.** 멤버십만으로 판정하면 워크스페이스 생성 자체가 실패합니다

### API 계층이 알아야 할 것

**`USING`에 걸리면 에러가 아니라 조용히 0행입니다.** viewer가 `update wiki_pages`를 하면 예외가 아니라 `rows=0`이 돌아옵니다(검증 12·13·23·27·37번). API는 **영향 행 0 = 403**으로 매핑해야 합니다. 반대로 `WITH CHECK` 위반은 `42501` 예외로 옵니다.

---

## 3d. 다음 작업: `P1-SEED-01` 프롬프트 템플릿 시드

`supabase/migrations/0006_seed_prompts.sql`. 전역 기본 템플릿(`workspace_id IS NULL`) 5종 — `target_type='ask'` 4개(Technical Deep-Dive, Executive Summary, Action Items Extractor, FAQ & Guide Generator) + `target_type='compile'` 1개.

`0001`의 partial unique index가 `is_default=true`를 `target_type`당 1개로 이미 강제하므로, 시드가 규칙을 어기면 마이그레이션이 실패합니다. `0004`가 전역 템플릿을 모든 로그인 사용자에게 읽히도록 해 뒀습니다.

그 뒤로는 스키마 작업이 없습니다. `P0-INIT-01`(monorepo) → `P0-INIT-02`(FastAPI 스캐폴딩)부터 코드입니다.

---

## 4. 로컬 환경 — 반드시 읽을 것

### 포트가 기본값이 아닙니다

같은 머신에 **`zettlink` 프로젝트의 Supabase 스택이 상시 실행 중**이고 기본 포트(54321~54324, 54327)를 점유합니다. 충돌을 피하려고 NexusWiki를 544xx 대역으로 옮겼습니다. 두 스택이 동시에 돌아갑니다.

```
API      http://127.0.0.1:54421
Studio   http://127.0.0.1:54423
DB       postgresql://postgres:postgres@127.0.0.1:54422/postgres
Inbucket http://127.0.0.1:54424      Analytics 54427   Pooler 54429   Shadow DB 54420
```

문서나 튜토리얼의 `54321`/`54322`를 그대로 쓰면 **엉뚱하게 `zettlink` DB에 연결됩니다.** 주의하세요.

### 자주 쓸 명령

```bash
supabase start                    # 스택 기동
supabase db reset                 # 마이그레이션 전체 재적용 — RLS 개발 중 계속 반복
supabase stop                     # 내리기 (zettlink는 영향 없음)

# psql이 로컬에 없으므로 컨테이너로 접속
docker exec -it supabase_db_NexusWiki psql -U postgres -d postgres
```

### 환경 이슈 이력

- **Docker 엔진이 한 번 죽었습니다.** 앱과 VM은 살아 있는데 VM 안의 `dockerd`만 죽어서 모든 API 호출이 500을 반환했습니다(`apiproxy: connection refused`). Docker Desktop 재시작으로 해결. 또 발생하면 같은 방법으로.
- **디스크 94% (여유 26GB).** `Docker.raw` 61GB. `docker system df` 기준 빌드 캐시 2.57GB가 100% 회수 가능합니다. `docker builder prune`은 이미지·볼륨을 건드리지 않지만 **다른 프로젝트의 캐시도 지우므로** 사용자 확인 후 실행하세요.
- **Supabase CLI 2.33.2** (최신 2.111.0). 업그레이드하면 `config.toml` 스키마가 바뀔 수 있으니 **Phase 1 완료 후**에 하세요.
- **클라우드 Supabase 프로젝트 미생성.** Phase 1 전체를 로컬만으로 끝낼 수 있어 미뤘습니다. 배포(`P0-INIT-04`) 전까지 필요 없습니다. 만들 때 리전은 **Northeast Asia (Seoul)** 권장.

---

## 5. 나중에 반드시 물릴 함정들

**RLS 무한 재귀 (`P1-SEC-01`)** — ✅ `0004`에서 해결했습니다. 아래는 왜 그렇게 했는지의 기록입니다.
`workspace_members`의 RLS 정책이 "내가 이 워크스페이스 멤버인가"를 확인하려고 `workspace_members`를 다시 조회하면 무한 재귀 에러가 납니다. `SECURITY DEFINER` 함수로 감싸서 끊어야 합니다. `stable`과 `set search_path = public`을 빠뜨리면 각각 성능 문제와 보안 취약점이 됩니다.

```sql
create function public.is_workspace_member(ws_id uuid)
returns boolean language sql
security definer stable set search_path = public
as $$ select exists (select 1 from workspace_members
                     where workspace_id = ws_id and user_id = auth.uid()); $$;
```

**bigram 토크나이저 버전 불일치 (`P2-BE-02`)**
색인 시와 질의 시 **반드시 동일한 토크나이저 함수**를 타야 합니다. 어긋나면 검색이 에러 없이 조용히 안 맞습니다 — 디버깅이 가장 고약한 종류입니다. 버전 상수를 두고(`0002`가 `tsv_tokenizer_version` 컬럼을 준비해 뒀습니다), 토크나이저를 바꾸면 재색인이 필요하다는 걸 명시하세요.

**질의 측 tsquery 생성 (`P2-BE-02`)** — `0002` 검증 중 실제로 밟은 지뢰입니다.
bigram 문자열을 `to_tsquery`에 그대로 넣으면 `"한국 국어"`처럼 공백으로 이어져 **syntax error**가 납니다. `phraseto_tsquery('simple', bigram(q))`를 쓰세요. bigram들이 `<->`로 묶여 인접성까지 검사하므로 부분 문자열 매칭 의미가 정확히 보존됩니다. `plainto_tsquery`는 `&`로 묶여 순서가 뒤바뀐 오탐이 섞입니다.

**벡터 검색의 사후 필터링 (`P2-BE-01`)** — `0004` 검증에서 플랜으로 확인했습니다.
`where workspace_id = $1 order by embedding <=> $2 limit k`는 HNSW가 먼저 k개를 뽑고 그다음 워크스페이스를 거르므로 **결과가 k개보다 적게 나올 수 있습니다.**

더 고약한 건 **RLS 정책 자체가 같은 사후 필터로 동작한다**는 점입니다. 앱이 `workspace_id` 조건을 빼먹어도 격리는 되지만, 플랜은 이렇게 됩니다.

```text
Index Scan using source_chunks_embedding_idx
  Order By: (embedding <=> ...)
  Filter: is_workspace_member(workspace_id)
  Rows Removed by Filter: 5      ← HNSW가 뽑은 후보의 절반이 여기서 증발
```

검색 쿼리는 **(1)** `where workspace_id = $1`을 명시하고 **(2)** `set local hnsw.iterative_scan = strict_order`를 켜세요 (로컬 pgvector 0.8.0 확인됨).

**정책 위반이 에러가 아닐 때가 있습니다 (`P2-API-01`, `P2-QC-01`)**
`USING`에 걸린 UPDATE/DELETE는 예외가 아니라 **조용히 0행**을 반환합니다. viewer가 위키를 수정하려 하면 에러 없이 "성공했는데 아무것도 안 바뀜"이 됩니다. API는 **영향 행 0 = 403**으로 매핑해야 합니다. `WITH CHECK` 위반(남의 워크스페이스로 쓰기)만 `42501` 예외로 옵니다.

**잡은 at-least-once입니다 (`P2-JOB-01`, `P2-LLM-01`)**
`reap_stale_jobs`의 타임아웃(기본 15분)이 정상 잡의 최장 실행 시간보다 짧으면, 살아 있는 워커의 잡을 뺏어 **같은 잡이 두 번 처리됩니다.** LLM 컴파일은 수 분이 걸릴 수 있습니다. 타임아웃을 넉넉히 두되, 그와 별개로 **모든 핸들러는 멱등해야 합니다** — 위키는 `(workspace_id, slug)` upsert, 청크는 `(raw_source_id, chunk_index)` upsert, 임베딩은 `(wiki_id, chunk_index)` upsert. 이 세 유니크 키가 `0002`에 있는 이유입니다.

**워커의 `service_role` 우회 (`P1-SEC-01`, `P4-SEC-01`)**
사용자 요청 경로는 JWT라 RLS가 지켜주지만, **워커는 `service_role`이라 RLS를 우회합니다.** 워커 코드에는 `workspace_id` 필터를 반드시 명시해야 합니다.

**OpenRouter 비용 (`P2-LLM-01`, `P4-OPS-01`)**
Anthropic 프롬프트 캐싱을 못 씁니다. 컴파일러 시스템 프롬프트는 길고 매 소스마다 반복되므로 소스가 늘면 비용이 선형으로 붙습니다. `P4-OPS-01`에서 실측 후 Anthropic 직결 전환을 재검토하세요.

**멱등성의 정의**
"LLM 출력 텍스트가 같다"가 아니라 **"동일 `content_hash` 재수집 시 행이 늘지 않고, `(workspace_id, slug)` upsert로 중복 위키가 없다"** 입니다. LLM은 비결정적이라 전자는 애초에 달성 불가능합니다.

---

## 6. 미결 사항

`checklists.json`의 `open_questions`에도 있습니다. 넷 다 착수를 막지는 않습니다.

1. **OpenRouter 모델 슬러그 실제 값** — `P2-LLM-01` 착수 전 확인 (`anthropic/claude-sonnet-4.6` 형태로 추정하나 미검증)
2. **Supabase 리전 / Railway 리전 조합**의 왕복 지연 측정
3. **청킹 파라미터**(토큰 수·오버랩) 초기값 — `P2-ING-02`에서 실측 후 확정
4. **워크스페이스별 월 LLM 비용 상한** — `P4-OPS-01`에서 확정

---

## 7. 다음 세션 시작 시 체크리스트

```bash
cd /Users/zorba/projects/NexusWiki
git log --oneline | head -3                   # 저장소는 이미 초기화됨
docker ps --filter name=NexusWiki | head -3   # 스택 살아있나
supabase start                                 # 없으면 기동
supabase db reset                              # 0001~0004 재적용 확인
```

그다음 `checklists.json`의 `decisions` 블록을 읽고 `P1-SEED-01`부터 이어가면 됩니다. 결정 사항은 근거와 함께 기록돼 있으니 재논의하지 마세요.
