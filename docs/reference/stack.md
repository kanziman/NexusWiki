# 기술 스택 참조

`.claude/CLAUDE.md`가 필요할 때 읽어 들이는 상세 참조다. 항상 참인 규칙은 CLAUDE.md에 있고, 여기에는 **버전·개수·상태처럼 변하는 사실**만 둔다. 값이 바뀌면 이 파일만 고친다.

## 언어

| 언어 | 용도 | 위치 |
| --- | --- | --- |
| SQL (PostgreSQL 17) | 스키마 · RLS · 큐 함수 | `supabase/migrations/` |
| Python 3.12 | FastAPI API · 큐 워커 · 공유 코어 | `apps/api/` · `apps/worker/` · `packages/core/` |
| TypeScript (`strict`) | Next.js 15 dashboard | `apps/dashboard/` |
| TOML | 로컬 스택 설정 | `supabase/config.toml` |
| JSON | GSD 작업 · 결정의 역사적 스냅샷 | `checklists.json` · `checklists_v2.json` |

## 런타임

- **PostgreSQL 17** — `major_version = 17` (`supabase/config.toml`)
- **Supabase 로컬 스택** — Docker 컨테이너 `supabase_*_NexusWiki`
- **Supabase CLI 2.111.0**
- Python 패키지 매니저는 `uv`(루트 `pyproject.toml` + `uv.lock` 워크스페이스), dashboard는 `pnpm`(자체 `pnpm-lock.yaml`)
- dashboard는 uv 워크스페이스 멤버가 아닌 독립 앱이다

## 프레임워크

- **Supabase** — Postgres + PostgREST + GoTrue Auth + Storage + Realtime
- **PostgREST** — `public` · `graphql_public` 스키마 자동 노출, `max_rows = 1000`
- **FastAPI** + **Pydantic / pydantic-settings** — 설정 로딩과 LLM 구조화 출력 검증
- **Next.js 15 (App Router)** + **Tailwind CSS**
- **Cytoscape** — 지식 그래프 캔버스

## 테스트

- **Vitest + Testing Library** — dashboard. 테스트는 `apps/dashboard/tests/`
- **pytest** — Python API · worker · core
- 검증 명령: `pnpm test -- --run` · `pnpm typecheck` · `pnpm lint` · `ruff check apps packages`
- 마이그레이션 성능 검증은 `docs/ops/` 아래 기록으로 남긴다 (`hnsw-order-benchmark.md`, `reap-timeout-baseline.md` 등)

## 핵심 의존성

- **pgvector** (로컬 v0.8.0) — `extensions` 스키마에 설치. 모든 참조가 스키마 한정(`extensions.vector`, `extensions.vector_cosine_ops`)이라 실행 role의 `search_path`에 의존하지 않는다
- **pgcrypto / `gen_random_uuid()`** — 전 테이블 UUID 기본키
- **HNSW 인덱스** — `source_chunks_embedding_idx`, `wiki_embeddings_embedding_idx` (cosine)
- **GIN tsvector 인덱스** — `wiki_pages_search_tsv_idx`, `source_chunks_search_tsv_idx`. 앱이 생성한 bigram `tsvector('simple', …)` 대상
- `httpx` — OpenRouter + OpenAI 임베딩 클라이언트
- `pypdf` — PDF 텍스트 추출
- **DB 내 작업 큐** — `jobs` 테이블 + `claim_job` / `complete_job` / `fail_job` / `reap_stale_jobs` / `complete_job_and_chain` / `release_job` / `dead_letter_job` / `cancel_job`, `FOR UPDATE SKIP LOCKED` (`0003_jobs.sql` · `0007_search_and_queue_extensions.sql` · `0009_pipeline_ops.sql`). `EXECUTE`는 `anon` · `authenticated`에서 회수됨, `service_role` 전용

## 마이그레이션

`supabase/migrations/`에 `0001` ~ `0018`이 있다. **파일명 번호 순서가 곧 적용 순서다.** 번호 간격은 없다.

주요 지점만:

| 번호 | 내용 |
| --- | --- |
| `0001` | 코어 스키마 — workspaces · membership · raw_sources · wiki_pages · prompt_templates |
| `0002` | 검색 스키마 — source_chunks · wiki_embeddings · wiki_links · search_tsv · HNSW/GIN |
| `0003` | 작업 큐 — `jobs` + claim/완료/실패/reap 기본 함수 |
| `0004` | RLS 정책 + `SECURITY DEFINER` 멤버십 헬퍼 + owner 보호 트리거 |
| `0005` | Storage — 비공개 `sources` 버킷, 멤버십 기반 정책 |
| `0006` | 프롬프트 시드 — 전역 템플릿 (`workspace_id IS NULL`) |
| `0007` | 검색 RPC + 완료 후 체인 생성 · 실행 중 작업 release 함수 |
| `0009` | usage 회계 + dead-letter · cancel 함수 |
| `0016` | 공개 공유 사이드카 — `workspace_public_settings` · `wiki_page_publications` |
| `0017` | 사용자별 위키 즐겨찾기 — `user_wiki_bookmarks` |
| `0018` | Ask 대화 스레드 이력 — `ask_threads` `ask_messages` |

현재 테이블 15개: `workspaces` `workspace_members` `raw_sources` `wiki_pages` `source_chunks` `wiki_embeddings` `wiki_links` `prompt_templates` `jobs` `usage_events` `workspace_public_settings` `wiki_page_publications` `user_wiki_bookmarks` `ask_threads` `ask_messages`

## 설정

- `supabase/config.toml`은 시크릿을 값이 아니라 **참조로만** 읽는다 — `OPENAI_API_KEY`, `SUPABASE_AUTH_SMS_TWILIO_AUTH_TOKEN`, `SUPABASE_AUTH_EXTERNAL_APPLE_SECRET`, `S3_HOST` / `S3_REGION` / `S3_ACCESS_KEY` / `S3_SECRET_KEY`
- `.env.sample`이 필요한 키 목록을 담는다. `.gitignore`가 `.env`, `.env.*`, `supabase/.env`를 제외한다
- `.mcp.json`, `.codex/config.toml`은 gitignore 대상이며 저장소에 커밋된 적이 없다

로컬 포트는 **544xx 고정**이다. 같은 머신의 `zettlink` 스택이 543xx를 점유하므로 튜토리얼 기본값(`54321`/`54322`)을 쓰면 다른 프로젝트 DB에 붙는다.

| 서비스 | 주소 |
| --- | --- |
| API | `http://127.0.0.1:54421` |
| DB | `postgresql://…@127.0.0.1:54422/postgres` |
| Studio | `http://127.0.0.1:54423` |
| Inbucket | `http://127.0.0.1:54424` |
| Analytics | `54427` |
| Pooler (비활성) | `54429` |
| Shadow DB | `54420` |

## 배포

| 대상 | 상태 | 근거 |
| --- | --- | --- |
| **Supabase Cloud** | ACTIVE_HEALTHY, 리전 `ap-southeast-1`(싱가포르) | `docs/ops/cloud-bootstrap-record.md`, `docs/ops/migration-0007-record.md` |
| **Railway** | 서비스 2개 — `api`(web) + `worker`(상주). Hobby $5/mo는 워크스페이스 단위 과금 | `docs/ops/railway-deploy-record.md`, `docs/ops/railway-env-checklist.md` |
| **Vercel** | Production 배포됨 (2026-08-13, CLI 업로드 방식) | `docs/ops/vercel-deploy-record.md` |

⚠️ 리전은 프로젝트 생성 후 변경 불가다. Railway에 서울·도쿄 리전이 없어 교차 리전 왕복이 5채널마다 곱해진다 — `docs/ops/rtt-baseline.md` 참조.

검토 후 기각: Fly.io (~$6.5/mo), Render ($14/mo 고정)

## 호스트 요구사항

- Docker Desktop — Docker 엔진이 죽으면 HTTP 500 + `apiproxy: connection refused`가 뜬다. 조치는 Docker Desktop 재시작
- 로컬 `psql` 없음 — `docker exec -it supabase_db_NexusWiki psql -U postgres -d postgres`

## 알려진 스택 리스크

- OpenRouter 경유는 Anthropic 네이티브 프롬프트 캐싱과 `output_config.format`을 포기한다. 컴파일러 비용이 소스 수에 선형으로 늘어난다
- OpenRouter 자체의 `response_format: {type:"json_schema"}`는 엔드포인트별 지원이라 `require_parameters: true` + 능력 탐지를 전제로 **선택적 최적화**로만 쓸 수 있다. 프롬프트 + Pydantic + 3회 재시도는 그와 무관하게 필수 백스톱이다 — `docs/ops/openrouter-contract-record.md`
