# NexusWiki

## What This Is

원시 소스(PDF · URL · 텍스트)를 넣으면 LLM이 상호 링크된 위키로 컴파일하고, 5채널 하이브리드 검색으로 **원문과 위키 양쪽을 함께 인용한 답변**을 돌려주는 Cairni 스타일 Living Wiki SaaS입니다. 팀 단위 워크스페이스가 기본 단위이며, 테넌트 격리는 애플리케이션이 아니라 Postgres RLS가 강제합니다. 사용 대상은 흩어진 문서를 하나의 검증 가능한 지식 베이스로 만들고 싶은 소규모 팀입니다.

## Core Value

질문에 대한 답이 **원문 청크와 컴파일된 위키 페이지 양쪽으로 추적 가능해야 한다** — 이중 Citation이 무너지면 이 제품은 그냥 또 하나의 RAG 챗봇입니다.

## Requirements

### Validated

<!-- 코드로 존재하고 검증까지 끝난 것. supabase/migrations/0001~0004, 0006 -->

- ✓ 워크스페이스 기반 팀 멀티테넌시 — `workspaces` + `workspace_members`, 역할 owner(3) > editor(2) > viewer(1), 소유자 자동 등록 트리거 (`0001`)
- ✓ 9개 테이블 전체 RLS 격리 — 정책 20+개, `SECURITY DEFINER` 멤버십 헬퍼로 재귀(42P17) 회피, 38/38 격리 케이스 통과 (`0004`)
- ✓ 불변 원시 소스 계층 — `raw_sources`(UPDATE 정책 부재로 불변성 강제) + `content_hash` 기반 재수집 멱등성 (`0001`)
- ✓ 5채널 검색 스키마 — `wiki_embeddings`/`source_chunks` pgvector HNSW, `wiki_pages`/`source_chunks` bigram GIN, `wiki_links` recursive CTE. EXPLAIN으로 5채널 전부 인덱스 사용 확인 (`0002`)
- ✓ 복합 FK 테넌트 전파 — `(id, workspace_id)` UNIQUE + 자식 테이블 복합 FK로 RLS를 우회하는 워커조차 테넌트를 넘을 수 없음 (`0002`)
- ✓ Postgres 네이티브 잡 큐 — `jobs` + `claim_job`/`complete_job`/`fail_job`/`reap_stale_jobs`, `FOR UPDATE SKIP LOCKED`, 8워커 400잡 동시성 통과 (`0003`)
- ✓ 레드 링크 모델 — `wiki_links.to_wiki_id IS NULL`이 곧 "다음에 쓸 페이지" 백로그 (`0002`)
- ✓ 상황별 프롬프트 템플릿 — 전역 템플릿 5종(compile 1 + ask 4), `{{variable}}` 치환, `target_type`당 기본값 1개를 부분 유니크 인덱스로 강제 (`0001`, `0006`)
- ✓ 로컬 Supabase 개발 스택 — Postgres 17, 포트 544xx (zettlink와 충돌 회피) (`supabase/config.toml`)
- ✓ Phase 1 bootstrap — Storage 정책, uv monorepo, 공용 구조화 로깅/재귀 redaction, Next.js 15 스캐폴드, Railway api/worker 배포, Auth hardening, Singapore RTT baseline 검증 완료

### Active

<!-- v1 범위. checklists.json Phase 0~4 전체 (32 태스크)에 대응. -->

- [ ] JWT 인증과 워크스페이스 컨텍스트 — 요청자 토큰으로 RLS를 태우는 경로
- [ ] 한국어 bigram 토크나이저 — 색인/질의 공용 모듈, `tsv_tokenizer_version` 기록
- [ ] 소스 수집 API — 파일/URL/텍스트 → Storage 업로드 → `raw_sources` → 잡 인큐
- [ ] 문서 파서와 청킹 파이프라인 — PDF 텍스트 추출, `(raw_source_id, chunk_index)` 업서트
- [ ] 잡 워커 프로세스 — 폴링, 지수 백오프 재시도, 데드레터, SIGTERM graceful shutdown
- [ ] 위키 컴파일러 — OpenRouter LLM + Pydantic 검증 + 3회 재시도, `(workspace_id, slug)` 업서트
- [ ] `[[WikiLink]]` 파싱과 링크 동기화 — slug 정규화, `wiki_links` 업서트, 미해결 타깃은 레드 링크로 유지
- [ ] 임베딩 파이프라인 — 위키 청크 + 원문 청크 양쪽 벡터화
- [ ] 5-Way 하이브리드 검색 — 5채널 병렬 + RRF 융합 + Citation 앵커(`[[wiki:slug]]`/`[[src:chunk_id]]`) 기반 이중 Citation 응답
- [ ] 읽기 API — 위키/소스/그래프/잡 상태 조회
- [ ] 지식 충돌 감지와 검증 상태 전이 API — `disputed`, `verification_status`, `confidence`
- [ ] 인증·워크스페이스 전환·멤버 초대 UI
- [ ] 소스 드롭존과 잡 진행 상태 표시
- [ ] Ask UI — 상황별 프롬프트 칩 + 이중 Citation 카드
- [ ] Cytoscape 지식 캔버스 — 렌즈 필터(`wiki_pages.category` 재사용)
- [ ] 위키 뷰어 — WikiLink 네비게이션, 레드 링크, 상태 콜아웃
- [ ] E2E 시나리오 검증 — 수집 → 컴파일 → 임베딩 → 검색
- [ ] 재수집 멱등성 검증 — 동일 `content_hash` 재투입 시 행 증가 0
- [ ] 워크스페이스 격리 검증 — 애플리케이션 경로에서의 교차 테넌트 시도 전수
- [ ] 검색 품질·지연 기준선 수립
- [ ] LLM/임베딩 비용 가드레일과 관측

### Out of Scope

- **Neo4j 등 별도 그래프 DB** — 고유 가치인 GDS가 Aura 기본 티어에 없고, 이 규모에서는 순회 성능 이점이 없음. 팀 모드에서는 Neo4j에 RLS가 없어 보안 부담만 추가됨. `wiki_links` + recursive CTE로 대체
- **pg_bigm / pgroonga** — Supabase가 제공하지 않음. 앱 레이어 bigram + `tsvector('simple', …)`로 대체
- **Postgres 기본 FTS 형태소 분석** — 한국어 분석기가 없어 공백 분리만 됨. `search_tsv`를 생성 컬럼으로 만들면 안 되는 이유
- **Anthropic 네이티브 structured output(`output_config.format`)** — OpenRouter 경유라 사용 불가. 프롬프트 + Pydantic 검증 + 3회 재시도로 대체
- **개인 전용(싱글 유저) 모드** — 팀 우선으로 확정. `disputed` 같은 기능은 다중 사용자 전제에서만 의미가 있음
- **외부 큐 브로커 / 캐시 계층** — Postgres 하나로 충분하고, 잡 상태를 프론트에 그대로 노출할 수 있음
- **모바일 네이티브 앱** — 웹 우선
- **Fly.io / Render 배포** — 각 ~$6.5/mo, $14/mo 고정으로 Railway Hobby($5/mo, 워크스페이스 단위) 대비 불리

## Context

- **기존 계획 자산.** `checklists.json`에 32개 태스크 · 10개 확정 결정 · 4개 미해결 질문이 정리되어 있고, `HANDOFF.md`에 세션 핸드오프가 있습니다. 이번 GSD 초기화는 **스코프를 다시 짜는 것이 아니라 그 계획을 GSD 구조(REQUIREMENTS/ROADMAP/PHASES)로 옮기는 작업**입니다.
- **코드베이스 맵.** `.planning/codebase/` 7개 문서(2026-08-01 기준)가 이미 존재합니다. 계획 에이전트는 이걸 먼저 읽어야 합니다.
- **진척.** 32개 중 5개 완료. DB 레이어는 끝났고 남은 스키마 작업은 Storage(`0005`) 하나. 여기서부터 애플리케이션 코드입니다.
- **RLS 위반은 에러가 아닐 수 있음.** `USING`에 막힌 UPDATE/DELETE는 예외 없이 0행을 반환합니다. API는 *affected rows = 0*을 403으로 매핑해야 합니다. `WITH CHECK` 위반만 `42501`을 던집니다.
- **잡은 at-least-once.** `reap_stale_jobs` 기본 타임아웃 15분. 모든 핸들러는 멱등이어야 하고, 3개 업서트 키가 정확히 이 목적으로 존재합니다.
- **수익 모델 미정.** SaaS를 지향하지만 가격/과금은 아직 결정된 바 없습니다. 워크스페이스별 월 LLM 비용 상한만 P4에서 확정 예정.
- **미해결 질문 4건** (`checklists.json > open_questions`): OpenRouter 모델 슬러그, Supabase/Railway 리전 조합 왕복 지연(→ 싱가포르 양쪽으로 결정, P0에서 실측), 청킹 파라미터 초기값, 워크스페이스별 LLM 비용 상한.
- **"Cairni"는 검색되지 않는 제품이다.** 리서치가 확인한 바로는 실존 레퍼런스가 아니며, 실질적 조상은 Karpathy의 LLM Wiki 패턴(ingest / query / **maintain**)이다. 현재 스키마가 거의 1:1로 대응하되 `maintain` 워크플로우와 컴파일 로그가 비어 있다 — 둘 다 v2로 추적 중. 요구사항을 "Cairni 스타일"에 앵커하지 말 것.

## Constraints

- **Tech stack**: Supabase(Postgres 17 + Auth + Storage) · FastAPI · Next.js 15 App Router · pgvector — 데이터 계층이 이미 이 전제로 구현·검증 완료됨
- **Tech stack**: LLM은 OpenRouter 경유, 모델은 env `LLM_MODEL`(기본 `claude-sonnet-4-6`) — 모델 교체 자유도 확보. 대신 Anthropic 네이티브 프롬프트 캐싱과 네이티브 `output_config.format`을 포기. (OpenRouter 자체의 `response_format: {type:"json_schema"}`는 엔드포인트별로 지원되므로 `require_parameters: true`와 능력 탐지를 전제로 선택적 최적화로 쓸 수 있음 — 프롬프트+Pydantic+3회 재시도는 그와 무관하게 필수 백스톱)
- **Deployment**: Supabase 리전 `ap-southeast-1`(싱가포르) + Railway `asia-southeast1` — Railway에 서울·도쿄 리전이 없어 교차 리전 왕복이 5채널마다 곱해짐. **리전은 프로젝트 생성 후 변경 불가**
- **Security**: Next.js는 15.2.3 이상 필수 — CVE-2025-29927은 `x-middleware-subrequest` 헤더 위조로 미들웨어를 건너뛰는데, 이 앱의 테넌트 게이트가 미들웨어임
- **Security**: 사용자 요청 경로는 요청자 JWT(`user_client`), `service_role`은 워커와 마이그레이션 전용 — `service_role`은 BYPASSRLS라 사용자 경로에 쓰는 순간 38개 격리 정책이 전부 장식이 됨
- **Compatibility**: 마이그레이션 `0005`(Storage)는 클라우드 첫 `db push` **이전에** 반드시 적용 — 이후에 넣으면 로컬/클라우드 순서가 어긋남
- **Dependencies**: 로컬 포트는 544xx 고정 — 같은 머신의 `zettlink` 스택이 543xx를 점유. 튜토리얼의 `54321`/`54322`를 쓰면 다른 프로젝트 DB에 붙음
- **Dependencies**: 로컬 `psql` 없음 — `docker exec -it supabase_db_NexusWiki psql -U postgres -d postgres` 사용
- **Performance**: 벡터 검색은 post-filter — `set local hnsw.iterative_scan = strict_order`(pgvector 0.8+) 필수, k보다 적게 돌아올 수 있음
- **Correctness**: 색인 시점과 질의 시점 토크나이저가 동일해야 함 — 불일치는 조용히 실패함. `tsv_tokenizer_version`이 재색인 범위를 좁히기 위해 존재
- **Budget**: Railway Hobby $5/mo + Supabase + LLM 종량 — 개인 프로젝트 수준 예산

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 테넌시는 팀 우선 | `workspace_members` + 역할 기반 RLS가 필수가 되고, `disputed` 기능이 의미를 가짐 | ✓ Good — RLS 38/38 통과 |
| Neo4j 제외, `wiki_links` + recursive CTE | GDS가 Aura 기본 티어에 없음. 이 규모에선 순회 이점 없음. 팀 모드에선 RLS 부재가 보안 부담 | ✓ Good — 5채널 EXPLAIN 인덱스 사용 확인 |
| 한국어 검색은 앱 레이어 bigram + tsvector | Postgres에 한국어 형태소 분석기 없음. pg_bigm/pgroonga는 Supabase 미제공. 의존성 0, 사내 약어·신조어 누락 없음 | — Pending (앱 코드 미구현) |
| 렌즈 필터는 `wiki_pages.category` 재사용 | 스키마 변경 0으로 `[전체]/[개념]/[엔티티]/[가이드]/[맵]` 확보 | — Pending |
| 원본 파일은 Supabase Storage 보관 | "불변 원본 보존" 약속 이행 + 파서 개선 시 재처리 경로 확보 | — Pending (`0005` 미적용) |
| LLM은 OpenRouter 경유, 모델은 env | 모델 교체 자유도 | ⚠️ Revisit — 네이티브 캐싱 포기, 비용이 소스 수에 선형 (P4에서 재검토) |
| 구조화 출력은 프롬프트 + Pydantic + 3회 재시도 | OpenRouter로는 Anthropic 네이티브 `output_config.format`을 못 씀 | — Pending |
| 잡 큐는 Postgres `jobs` + `SKIP LOCKED` 폴링 | 새 인프라 0, 잡 상태를 그대로 프론트에 노출 가능 | ✓ Good — 8워커 400잡 동시성 통과 |
| DB 접근은 하이브리드 (사용자=JWT, 워커=service_role) | `service_role`은 RLS를 완전 우회. 사용자 경로에 JWT를 쓰면 DB가 격리를 강제해 코드 실수를 막아줌 | ✓ Good |
| 배포는 Railway (api + worker 2서비스) | Hobby $5/월이 서비스 단위가 아닌 **워크스페이스 단위** 구독. CPU 실사용분 과금이 LLM 대기 워커에 유리 | — Pending |
| DB 레이어는 Validated로 확정, 로드맵에서 제외 | 이미 적용·검증이 끝난 것을 GSD가 다시 계획하려 드는 것을 방지 | — Pending |
| v1 = checklists.json Phase 0~4 전체 | 기존 계획을 스코프 변경 없이 그대로 GSD로 이관 | — Pending |
| 실행은 `/gsd-spec-phase` 주도 (SDD) | 페이즈마다 spec을 먼저 확정하고 거기서 plan을 도출 — spec이 단일 진실 소스 | — Pending |
| 리전은 싱가포르 양쪽 (Supabase `ap-southeast-1` + Railway `asia-southeast1`) | Railway에 서울·도쿄가 없음. 서울 DB + 싱가포르 컴퓨트는 왕복당 60~80ms를 5채널마다 지불. 페널티를 브라우저→API 한 번으로 이동 | — Pending (P0에서 실측) |
| v1 위키 페이지는 읽기 전용, UI가 명시 | 자유 편집이 `(workspace_id, slug)` 업서트와 정면 충돌 — 재컴파일이 편집을 덮어씀. 멱등성 보장을 깨지 않고 기대치를 정확히 설정 | — Pending |
| `0007`에 `verified_by`/`verified_at`/`expires_at` + `embedding_version`/`chunker_version` 추가 | 주인·만료 없는 검증 배지는 쓰이지 않고(Guru가 유일하게 살린 이유는 랭킹 강등), 어휘 검색에만 버전이 있던 비대칭은 모델 교체 경로를 막음 | — Pending |
| Cytoscape 캔버스 v1 유지 (리서치 권고와 반대) | 리서처 3명이 최저 우선순위로 봤으나 데모·설득 가치를 인정해 유지. 단 Phase 6 마지막 표면으로 배치하고 1000행 캡 처리를 요구사항에 명시 | ⚠️ Revisit — 사용 데이터로 재평가 |
| DB 트랜스포트는 스파이크로 결정 | 리서처 간 유일한 정면 충돌(asyncpg vs `SECURITY INVOKER` RPC). `create function ... SET hnsw.iterative_scan`이 RPC로 먹히는지가 판정 기준 — 문서가 아니라 실측이 결정 | ✓ Good — RPC 채택, `0007` 섹션 1에 반영 |
| 임베딩은 bge-m3(1024차) 호스티드, OpenAI 아님 | 근거는 비용이 아니라 한국어 검색 품질. 한국어 NDCG@10에서 OpenAI 최상위 모델(3-large 0.61670)이 주요 오픈소스 전부에 밀림 — bge-m3 0.68723. 단가는 양쪽 다 반올림 오차. KURE-v1이 0.0075 더 높으나 호스티드 API가 없고 자체 호스팅은 예산 10배 | — Pending (`0008`이 Phase 3 전에 필요) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-02 after research, requirements, and roadmap creation*
