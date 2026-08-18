# 아키텍처 참조

`.claude/CLAUDE.md`가 필요할 때 읽어 들이는 상세 참조다. 어기면 조용히 깨지는 불변 규칙은 CLAUDE.md에 있고, 여기에는 **구조와 책임 분담**을 둔다.

## 구성 요소

| 구성 요소 | 책임 | 위치 |
| --- | --- | --- |
| 코어 스키마 | workspaces · membership · raw_sources · wiki_pages · prompt_templates. 테이블 생성과 동시에 RLS 활성화 | `supabase/migrations/0001_core_schema.sql` |
| 검색 스키마 | source_chunks · wiki_embeddings · wiki_links · `wiki_pages.search_tsv`, HNSW + GIN | `supabase/migrations/0002_search_schema.sql` |
| 작업 큐 | `jobs` + `claim_job`/`complete_job`/`fail_job`/`reap_stale_jobs` (SKIP LOCKED) | `supabase/migrations/0003_jobs.sql` |
| 테넌트 격리 | 전 테이블 RLS 정책 + `SECURITY DEFINER` 멤버십 헬퍼 + owner 보호 트리거 | `supabase/migrations/0004_rls_policies.sql` |
| Storage 버킷 | 비공개 `sources` 버킷, 멤버십 기반 정책 | `supabase/migrations/0005_storage.sql` |
| 프롬프트 시드 | 전역 템플릿 (`workspace_id IS NULL`) | `supabase/migrations/0006_seed_prompts.sql` |
| 공개 공유 사이드카 | `workspace_public_settings` · `wiki_page_publications`, 킬스위치 RLS | `supabase/migrations/0016_public_sharing.sql` |
| API 서비스 | JWT 인증 · 워크스페이스 컨텍스트 · 읽기 API · ask · ingest | `apps/api/` |
| Worker 서비스 | 큐 폴링 · 파싱/청킹 · LLM 컴파일 · 임베딩 · 링크 동기화 | `apps/worker/` |
| 공유 코어 | 구조화 로깅 등 API·worker 공용 모듈 | `packages/core/` |
| Dashboard | 인증 · 업로드 · ask UI · 그래프 캔버스 · 위키 뷰어 · 공개 뷰어 | `apps/dashboard/` |
| 작업 원장 | 작업 · 결정 · 검증 기록 | `checklists.json` · `checklists_v2.json` |
| 세션 인계 | 현재 상태 · 이탈 사항 · 함정 | `HANDOFF.md` |
| 운영 기록 | 배포 · 벤치마크 · 마이그레이션 검증 기록 | `docs/ops/` |

## 지배적 패턴

- **격리는 앱이 아니라 DB에 산다.** RLS는 각 테이블을 만드는 바로 그 마이그레이션에서 활성화된다 — 정책이 없는 상태로 열려 있는 창이 존재하지 않는다.
- **하이브리드 DB 접근.** 사용자 요청 경로는 요청자 JWT를 쓰고 RLS가 격리를 강제한다. `service_role`은 워커와 마이그레이션 전용이다.
- **복합 FK가 테넌트를 나른다.** `raw_sources`와 `wiki_pages`는 `(id, workspace_id)` UNIQUE를 가지므로 자식 테이블이 복합 FK를 쓴다. RLS를 우회하는 워커도 테넌트를 넘을 수 없다.
- **한국어 어휘 검색은 애플리케이션 책임이다.** `search_tsv`는 의도적으로 생성 컬럼이 아니다. 앱이 bigram 토큰화한 `to_tsvector('simple', …)`를 쓰고, `tsv_tokenizer_version`이 어느 토크나이저가 만든 행인지 기록한다.
- **큐 상태 전이는 함수를 통해서만.** `jobs`를 직접 UPDATE하면 안 된다. 시도 회계와 lock 일관성 CHECK가 네 개 함수 안에 있다.

## 계층

### 1. 원문 계층
- 목적: 원자료를 그대로 보존 — 이중 Citation의 "원문" 절반
- 위치: `public.raw_sources`, `public.source_chunks`
- 내용: 추출된 평문, `content_hash` 멱등 키, `storage_path`, `char_start`/`char_end` 청크 구간
- 소비: 검색 채널 2·4, 이중 Citation 페이로드
- ⚠️ 제약: **UPDATE 정책이 존재하지 않는다.** 불변성은 관례가 아니라 정책 부재로 강제된다

### 2. 위키 계층
- 목적: LLM이 컴파일한, 사람이 검증 가능한 지식 페이지
- 위치: `public.wiki_pages`, `public.wiki_embeddings`, `public.wiki_links`
- 내용: slug/title/category/content, 품질 플래그(`explored`·`confidence`·`verification_status`·`disputed`), 소스 역참조
- 소비: 검색 채널 1·3·5, 위키 뷰어와 캔버스

### 3. 작업 계층
- 목적: 수집 요청과 장시간 LLM 작업을 분리
- 위치: `public.jobs` + 네 함수
- 생산자는 ingest API, 소비자는 worker

### 4. 격리 계층
- 위치: `supabase/migrations/0004_rls_policies.sql`
- 내용: `is_workspace_member(uuid)`, `workspace_role(uuid)`, `has_workspace_role(uuid, text)`, `protect_owner_membership()` 트리거, 정책 다수

## 핵심 추상

### 워크스페이스
- 테넌시의 뿌리. 모든 도메인 테이블이 `workspace_id`를 가진다
- `workspaces.owner_id` + `workspace_members(workspace_id, user_id, role)`
- AFTER INSERT 트리거가 owner를 멤버로 자동 등록한다 — 멤버 0명(영구히 보이지 않는) 워크스페이스가 생길 수 없다

### 멤버십 헬퍼
- 목적: `workspace_members`에서 RLS 무한 재귀(`42P17`)를 끊는다
- `security definer stable set search_path = public`. `auth.uid()`가 함수 안에 고정되어 호출자 자신의 멤버십만 돌려주므로 `authenticated`에 부여해도 안전하다

### 큐 함수
- `jobs`를 바꾸는 유일한 정식 경로
- `claim_job(worker_id, types[])` · `complete_job(job_id)` · `fail_job(job_id, error, backoff, max_backoff)` · `reap_stale_jobs(timeout)`
- 전부 `service_role` 전용

### 레드 링크 (`wiki_links`)
- 아직 존재하지 않는 페이지로 향하는 링크. "다음에 쓸 페이지" 백로그를 겸한다
- `to_wiki_id IS NULL`, `resolved`는 저장된 생성 컬럼
- 대상 삭제는 `on delete set null (to_wiki_id)` — 링크가 `workspace_id`를 잃지 않고 빨간 링크로 되돌아간다

### 프롬프트 템플릿
- 전역(`workspace_id IS NULL`) 또는 워크스페이스별 교체 가능
- `{{variable}}` 이중 중괄호 자리표시자. `target_type`당 기본값이 정확히 하나임을 부분 유니크 인덱스가 강제한다

## 진입점

| 진입점 | 트리거 |
| --- | --- |
| `supabase/migrations/` | `supabase db reset` / `supabase db push` — 파일명 번호 순서가 적용 순서 |
| `supabase/config.toml` | `supabase start` — 포트는 544xx 고정 |
| `apps/api/` | HTTP 요청 |
| `apps/worker/` | 큐 폴링 (상주 프로세스) |
| `apps/dashboard/` | 브라우저 |

## 상태

- 모든 지속 상태는 Postgres다. 캐시·큐 브로커·그래프 저장소가 따로 없다
- 작업 진행 상황은 프론트엔드가 `jobs`를 직접 읽어 표시한다 (멤버는 SELECT만 가능)
- 코드에는 전역 가변 상태가 없다
