# NexusWiki — 세션 핸드오프

**최종 갱신:** 2026-08-01
**단계:** Phase 1 (데이터 계층) 진행 중 · 32개 태스크 중 1개 완료
**다음 작업:** `P1-DB-02` 검색 스키마

---

## 0. 30초 요약

Cairni 스타일 Living Wiki SaaS를 그린필드로 짓는 중입니다. 원시 소스(PDF/URL/텍스트)를 넣으면 LLM이 위키로 컴파일하고, 하이브리드 검색으로 **원문 + 위키 이중 출처**를 단 답변을 제공합니다.

이전 세션에서 한 일은 두 가지입니다. **(1)** 원래 계획서 기반 체크리스트를 리뷰해 핵심 기능 3개가 데이터 모델에 대응물이 없다는 걸 찾아내고, 인터뷰로 9개 결정을 확정한 뒤 체크리스트를 전면 재작성(19 → 32 태스크). **(2)** 로컬 Supabase 스택을 띄우고 코어 스키마(`0001`)를 적용·검증.

> ⚠️ **이 프로젝트는 아직 git 저장소가 아닙니다.** 지금까지의 작업물이 전부 버전 관리되지 않고 있습니다. 다음 세션 시작 시 `git init` + 최초 커밋을 먼저 하세요.

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
[~] P0-INIT-00 Supabase 셋업        — 로컬만 완료, 클라우드 미생성
[ ] P0-INIT-01 monorepo 구조        — 건너뜀 (마이그레이션은 이에 의존 안 함)
[ ] P1-DB-02   검색 스키마          ← 다음
[ ] P1-DB-03   jobs 테이블
[ ] P1-SEC-01  RLS 정책             ← Phase 2 전체의 병목
```

RLS까지 남은 추정: **3.5일**

### 디스크상의 파일

```
checklists.json                        32개 태스크 + decisions + open_questions
supabase/config.toml                   포트를 544xx로 수정함 (§4 참조)
supabase/migrations/0001_core_schema.sql
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

## 3. 다음 작업: `P1-DB-02` 검색 스키마

`supabase/migrations/0002_search_schema.sql` 작성.

**만들 것**
- `create extension if not exists vector`
- `source_chunks(id, raw_source_id, workspace_id, chunk_index, content, char_start, char_end, embedding vector(1536), search_tsv tsvector)` — **이중 Citation의 원문 측 데이터.** 원안에 아예 없어서 핵심 기능이 구현 불가였던 부분
- `wiki_embeddings(id, wiki_id, workspace_id, chunk_content, embedding vector(1536))`
- `wiki_links(id, workspace_id, from_wiki_id, target_slug, to_wiki_id nullable, resolved boolean)` — `to_wiki_id IS NULL`이 미해결 링크(red link)
- HNSW 인덱스 2개 (`vector_cosine_ops`), GIN 인덱스 2개 (`search_tsv`), `wiki_links` 양방향 조회 인덱스
- 네 테이블 모두 `enable row level security` (정책은 `0004`)

**⚠️ 가장 중요한 함정**

`search_tsv`를 **generated column으로 만들면 안 됩니다.** DB가 `to_tsvector`를 직접 돌리면 한국어가 공백 단위로만 쪼개져서 검색이 사실상 무용해집니다. 애플리케이션(`P2-BE-02` 토크나이저)이 bigram으로 쪼갠 문자열을 `to_tsvector('simple', ...)`에 넣어 채우는 **일반 컬럼**이어야 합니다.

**검증 기준**
- `EXPLAIN ANALYZE`로 벡터 쿼리가 HNSW를, tsvector 쿼리가 GIN을 타는지 확인
- `wiki_links`에 `to_wiki_id IS NULL` 행이 삽입 가능한지
- `source_chunks.char_start/char_end`로 `raw_sources.content`를 슬라이스하면 `chunk.content`와 정확히 일치 (이건 `P2-ING-02`에서 실제 검증)

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

**RLS 무한 재귀 (`P1-SEC-01`)**
`workspace_members`의 RLS 정책이 "내가 이 워크스페이스 멤버인가"를 확인하려고 `workspace_members`를 다시 조회하면 무한 재귀 에러가 납니다. `SECURITY DEFINER` 함수로 감싸서 끊어야 합니다. `stable`과 `set search_path = public`을 빠뜨리면 각각 성능 문제와 보안 취약점이 됩니다.

```sql
create function public.is_workspace_member(ws_id uuid)
returns boolean language sql
security definer stable set search_path = public
as $$ select exists (select 1 from workspace_members
                     where workspace_id = ws_id and user_id = auth.uid()); $$;
```

**bigram 토크나이저 버전 불일치 (`P2-BE-02`)**
색인 시와 질의 시 **반드시 동일한 토크나이저 함수**를 타야 합니다. 어긋나면 검색이 에러 없이 조용히 안 맞습니다 — 디버깅이 가장 고약한 종류입니다. 버전 상수를 두고, 토크나이저를 바꾸면 전체 재색인이 필요하다는 걸 명시하세요.

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
git init && git add -A && git commit -m "chore: initial checklist and core schema"   # ← 아직 안 됨
docker ps --filter name=NexusWiki | head -3   # 스택 살아있나
supabase start                                 # 없으면 기동
supabase db reset                              # 0001 재적용 확인
```

그다음 `checklists.json`의 `decisions` 블록을 읽고 `P1-DB-02`부터 이어가면 됩니다. 결정 사항은 근거와 함께 기록돼 있으니 재논의하지 마세요.
