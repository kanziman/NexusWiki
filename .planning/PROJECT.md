# NexusWiki

## What This Is

원시 소스(PDF · URL · 텍스트)를 넣으면 LLM이 상호 링크된 위키로 컴파일하고, 5채널 하이브리드 검색으로 **원문과 위키 양쪽을 함께 인용한 답변**을 돌려주는 Cairni 스타일 Living Wiki SaaS입니다. 팀 단위 워크스페이스가 기본 단위이며, 테넌트 격리는 애플리케이션이 아니라 Postgres RLS가 강제합니다. 사용 대상은 흩어진 문서를 하나의 검증 가능한 지식 베이스로 만들고 싶은 소규모 팀입니다.

## Core Value

질문에 대한 답이 **원문 청크와 컴파일된 위키 페이지 양쪽으로 추적 가능해야 한다** — 이중 Citation이 무너지면 이 제품은 그냥 또 하나의 RAG 챗봇입니다.

## Requirements

### Validated

<!-- v1.0 milestone 전체(Phase 1-7)가 여기 있다. supabase/migrations/0001~0014, 73/73 요구사항. -->

- ✓ 워크스페이스 기반 팀 멀티테넌시 — `workspaces` + `workspace_members`, 역할 owner(3) > editor(2) > viewer(1), 소유자 자동 등록 트리거 (`0001`)
- ✓ 9개 테이블 전체 RLS 격리 — 정책 20+개, `SECURITY DEFINER` 멤버십 헬퍼로 재귀(42P17) 회피, 38/38 격리 케이스 통과 (`0004`)
- ✓ 불변 원시 소스 계층 — `raw_sources`(UPDATE 정책 부재로 불변성 강제) + `content_hash` 기반 재수집 멱등성 (`0001`)
- ✓ 5채널 검색 스키마 — `wiki_embeddings`/`source_chunks` pgvector HNSW, `wiki_pages`/`source_chunks` bigram GIN, `wiki_links` recursive CTE. EXPLAIN으로 5채널 전부 인덱스 사용 확인 (`0002`)
- ✓ 복합 FK 테넌트 전파 — `(id, workspace_id)` UNIQUE + 자식 테이블 복합 FK로 RLS를 우회하는 워커조차 테넌트를 넘을 수 없음 (`0002`)
- ✓ Postgres 네이티브 잡 큐 — `jobs` + `claim_job`/`complete_job`/`fail_job`/`reap_stale_jobs`, `FOR UPDATE SKIP LOCKED`, 8워커 400잡 동시성 통과 (`0003`)
- ✓ 레드 링크 모델 — `wiki_links.to_wiki_id IS NULL`이 곧 "다음에 쓸 페이지" 백로그 (`0002`)
- ✓ 상황별 프롬프트 템플릿 — 전역 템플릿 5종(compile 1 + ask 4), `{{variable}}` 치환, `target_type`당 기본값 1개를 부분 유니크 인덱스로 강제 (`0001`, `0006`)
- ✓ 로컬 Supabase 개발 스택 — Postgres 17, 포트 544xx (zettlink와 충돌 회피) (`supabase/config.toml`)
- ✓ Phase 1 bootstrap — Storage 정책, uv monorepo, 공용 구조화 로깅/재귀 redaction, Next.js 15 스캐폴드, Railway api/worker 배포, Auth hardening, Singapore RTT baseline 검증 완료 (Phase 1, BOOT-01~10)
- ✓ 5채널 하이브리드 검색 + RRF 융합 — 2웨이브 오케스트레이션(채널 1~4 동시 실행 → RRF → 채널 5 그래프 확장 시드 → 재융합), 순위 전용 RRF·가중치/`k`/limit은 Python 정책 계층, `hnsw.iterative_scan`/`ef_search`/`max_scan_tuples` 3-GUC 세트, `channel_hits`·`returned < requested_k` 1급 메트릭, `EXPLAIN` 회귀로 HNSW 인덱스 스캔 단언, 채널 장애 시 부분 실패 허용(`meta` 보고), 30~50문항 한국어/영어/혼합 골든 세트로 `strict_order` 대 `relaxed_order` 벤치마크 근거 기록 (Phase 4, RTV-01~09)
- ✓ 테넌트 격리 스파인 — `service_role` 코드 경로 부재(존재 자체가 아니라 접근 불가), `UserDb` 0행→403 단일 매핑, DB 트랜스포트 스파이크로 RPC 채택, 공용 한국어 토크나이저(NFC/NFD/전각 왕복) (Phase 2, SEC-01~06 · DOM-01~09)
- ✓ 수집→컴파일 파이프라인 — 파일/URL/텍스트 인큐 즉시 202, `content_hash` 멱등, `needs_ocr` 품질 게이트, 토큰 기준 청킹, `parse→compile→link_sync→embed` 잡 체인, LLM 구조화 출력(프롬프트+Pydantic+3회 재시도), 인큐 시점 비용 상한(`usage_events`) (Phase 3, ING-01~07 · COMP-01~08 · OPS-01)
- ✓ 이중 Citation과 답변 API — 서버 발급 짧은 별칭(`[[wiki:w1]]`/`[[src:s1]]`) 기반 앵커, `double_citation` = 파싱된 앵커 ∩ 발급된 앵커, 위조 앵커 수집 시점 제거, SSE `meta→delta→citations→done` 스트리밍, 지식 충돌 감지(`disputed`), 검증 상태 전이(`verified_by`/`verified_at`/`expires_at`) (Phase 5, CITE-01~06 · API-01~04 · QC-01~02)
- ✓ 브라우저 전용 워크스페이스 운영 — 인증·워크스페이스 전환·멤버 초대, 실제 5단계 잡 스테퍼 드롭존, 인라인 이중 Citation Ask UI, 읽기 전용 위키 뷰어(레드 링크 CTA), Cytoscape 지식 캔버스(1000행 상한 처리) (Phase 6, UI-01~06)
- ✓ 통합·운영 기준선 — 빈 워크스페이스 E2E(수집→컴파일→임베딩→검색), 재수집 멱등성(중복 무증가 + 축소 재처리 잔여 0), 9테이블 전수 요청자-JWT 격리 매트릭스, 25k+25k 합성 코퍼스 HNSW `strict_order` 대 `relaxed_order` 실측 기준선, 워크스페이스별 비용·잡 파이프라인 관측 패널(Settings, editor+) (Phase 7, OPS-02~06) — `.planning/phases/07-integration-and-ops-baseline/07-VERIFICATION.md`

### Active

<!-- v1.0 milestone 완료로 이 섹션은 비어 있다. 다음 마일스톤 요구사항은 /gsd-new-milestone에서 정의한다. -->

(v2 후보 아이디어는 아카이브된 `.planning/milestones/v1.0-REQUIREMENTS.md`의 `## v2 Requirements` 섹션 참고 — NAV-01~03, MNT-01~03, QCV-01~03, PLT-01~03)

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

- **v1.0 마일스톤 완료 (2026-08-13).** Phase 1~7 전 페이즈, 73/73 v1 요구사항, 55개 플랜 전부 완료·검증(passed). 393커밋 · 12일(2026-08-01~13) · 30k+ LOC(py/ts/tsx/sql). 상세는 `.planning/MILESTONES.md`와 아카이브 `.planning/milestones/v1.0-ROADMAP.md`/`v1.0-REQUIREMENTS.md` 참고.
- **RLS 위반은 에러가 아닐 수 있음.** `USING`에 막힌 UPDATE/DELETE는 예외 없이 0행을 반환합니다. API는 *affected rows = 0*을 403으로 매핑해야 합니다. `WITH CHECK` 위반만 `42501`을 던집니다. — `UserDb` 단일 지점에서 구현·검증 완료 (Phase 2).
- **잡은 at-least-once.** `reap_stale_jobs` 기본 타임아웃 15분. 모든 핸들러는 멱등이어야 하고, 3개 업서트 키가 정확히 이 목적으로 존재합니다. — Phase 3에서 확정, Phase 7 OPS-03에서 축소 재처리 케이스까지 실측 검증.
- **수익 모델 미정.** SaaS를 지향하지만 가격/과금은 아직 결정된 바 없습니다. 워크스페이스별 월 LLM 비용 상한($5.00 기본)과 관측 패널(OPS-06)은 구현·검증 완료 — 다음 마일스톤에서 실제 과금 모델을 정의해야 함.
- **SDD(`/gsd-spec-phase`)는 Phase 1~2에서만 실제로 쓰였다.** Phase 3~7은 `01-SPEC.md`/`02-SPEC.md` 이후 SPEC.md 없이 discuss-phase → plan-phase로 직행했고, edge/prohibition 커버리지는 spec-less probe fallback이 대신 채웠다. 다음 마일스톤에서 SDD를 다시 쓸지 결정 필요.
- **"Cairni"는 검색되지 않는 제품이다.** 리서치가 확인한 바로는 실존 레퍼런스가 아니며, 실질적 조상은 Karpathy의 LLM Wiki 패턴(ingest / query / **maintain**)이다. 현재 스키마가 거의 1:1로 대응하되 `maintain` 워크플로우와 컴파일 로그는 v1.0에 없다 — v2 후보로 아카이브된 REQUIREMENTS.md(`MNT-01~03`)에 추적 중.
- **v2 후보.** `.planning/milestones/v1.0-REQUIREMENTS.md`의 `## v2 Requirements`: Navigation(백링크·레드링크 백로그), Maintain(중복 탐지·컴파일 로그), Quality & History(타입 있는 충돌 감지·답변 이력), Platform(공개 공유·외부 커넥터·SSO).

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
| 한국어 검색은 앱 레이어 bigram + tsvector | Postgres에 한국어 형태소 분석기 없음. pg_bigm/pgroonga는 Supabase 미제공. 의존성 0, 사내 약어·신조어 누락 없음 | ✓ Good — Phase 4 골든 세트(30-50문항 한/영/혼합)로 검색 채널 3/4 측정 완료 |
| 렌즈 필터는 `wiki_pages.category` 재사용 | 스키마 변경 0으로 `[전체]/[개념]/[엔티티]/[가이드]/[맵]` 확보 | ✓ Good — Phase 6 `GraphLensFilter.tsx`로 구현·검증 완료 |
| 원본 파일은 Supabase Storage 보관 | "불변 원본 보존" 약속 이행 + 파서 개선 시 재처리 경로 확보 | ✓ Good — `0005` 적용, ING-03 경로 규약 강제 검증 |
| LLM은 OpenRouter 경유, 모델은 env | 모델 교체 자유도 | ⚠️ Revisit — 네이티브 캐싱 포기 유지 중. Phase 7 OPS-06 관측 패널(워크스페이스별 비용)로 실제 지출 가시화는 됐으나, 캐싱 없는 구조적 비용 문제 자체는 미해결 |
| 구조화 출력은 프롬프트 + Pydantic + 3회 재시도 | OpenRouter로는 Anthropic 네이티브 `output_config.format`을 못 씀 | ✓ Good — COMP-01 구현·검증(Phase 3). Ask 스트리밍 경로(Phase 5)는 별도 셰이프(스트리밍 vs 재시도)로 분리 |
| 잡 큐는 Postgres `jobs` + `SKIP LOCKED` 폴링 | 새 인프라 0, 잡 상태를 그대로 프론트에 노출 가능 | ✓ Good — 8워커 400잡 동시성 통과, Phase 6 JobStepper가 실제 잡 상태 그대로 노출 |
| DB 접근은 하이브리드 (사용자=JWT, 워커=service_role) | `service_role`은 RLS를 완전 우회. 사용자 경로에 JWT를 쓰면 DB가 격리를 강제해 코드 실수를 막아줌 | ✓ Good — Phase 7 OPS-04 9테이블 전수 매트릭스로 재확인 |
| 배포는 Railway (api + worker 2서비스) | Hobby $5/월이 서비스 단위가 아닌 **워크스페이스 단위** 구독. CPU 실사용분 과금이 LLM 대기 워커에 유리 | ✓ Good — Phase 1/2 실측 p50 84ms/p99 127ms, 12일간 안정 운영 |
| DB 레이어는 Validated로 확정, 로드맵에서 제외 | 이미 적용·검증이 끝난 것을 GSD가 다시 계획하려 드는 것을 방지 | ✓ Good — Phase 1-7 어느 페이즈도 `0001`~`0004`/`0006`을 재작업하지 않음 |
| v1 = checklists.json Phase 0~4 전체 | 기존 계획을 스코프 변경 없이 그대로 GSD로 이관 | ✓ Good — 73/73 v1 요구사항 GSD 로드맵(Phase 1-7)으로 이관·완료 |
| 실행은 `/gsd-spec-phase` 주도 (SDD) | 페이즈마다 spec을 먼저 확정하고 거기서 plan을 도출 — spec이 단일 진실 소스 | ⚠️ Revisit — 실제로는 Phase 1·2만 SPEC.md를 썼다. Phase 3~7은 discuss-phase→plan-phase 직행 + spec-less probe fallback으로 edge/prohibition 커버리지를 대신 채움 |
| 리전은 싱가포르 양쪽 (Supabase `ap-southeast-1` + Railway `asia-southeast1`) | Railway에 서울·도쿄가 없음. 서울 DB + 싱가포르 컴퓨트는 왕복당 60~80ms를 5채널마다 지불. 페널티를 브라우저→API 한 번으로 이동 | ✓ Good — Phase 1 p50 29ms/p95 38ms, Phase 2 noop 왕복 p99 127ms(N=219) 실측 확정 |
| v1 위키 페이지는 읽기 전용, UI가 명시 | 자유 편집이 `(workspace_id, slug)` 업서트와 정면 충돌 — 재컴파일이 편집을 덮어씀. 멱등성 보장을 깨지 않고 기대치를 정확히 설정 | ✓ Good — Phase 6 UI-05 "이 페이지는 컴파일됩니다" 배너로 구현·검증 |
| `0007`에 `verified_by`/`verified_at`/`expires_at` + `embedding_version`/`chunker_version` 추가 | 주인·만료 없는 검증 배지는 쓰이지 않고(Guru가 유일하게 살린 이유는 랭킹 강등), 어휘 검색에만 버전이 있던 비대칭은 모델 교체 경로를 막음 | ✓ Good — `0007` 적용, QC-02 검증 상태 전이 API가 세 필드 모두 사용 |
| Cytoscape 캔버스 v1 유지 (리서치 권고와 반대) | 리서처 3명이 최저 우선순위로 봤으나 데모·설득 가치를 인정해 유지. 단 Phase 6 마지막 표면으로 배치하고 1000행 캡 처리를 요구사항에 명시 | ⚠️ Revisit — 구현·검증(UI-06)은 완료됐으나 실사용 데이터로 가치 재평가는 아직 없음 |
| DB 트랜스포트는 스파이크로 결정 | 리서처 간 유일한 정면 충돌(asyncpg vs `SECURITY INVOKER` RPC). `create function ... SET hnsw.iterative_scan`이 RPC로 먹히는지가 판정 기준 — 문서가 아니라 실측이 결정 | ✓ Good — RPC 채택, `0007` 섹션 1에 반영, Ask LLM 스트리밍(Phase 5)에도 동일 내부 리스너 패턴 재사용 |
| 임베딩은 bge-m3(1024차) 호스티드, OpenAI 아님 | 근거는 비용이 아니라 한국어 검색 품질. 한국어 NDCG@10에서 OpenAI 최상위 모델(3-large 0.61670)이 주요 오픈소스 전부에 밀림 — bge-m3 0.68723. 단가는 양쪽 다 반올림 오차. KURE-v1이 0.0075 더 높으나 호스티드 API가 없고 자체 호스팅은 예산 10배 | ✓ Good — `0008` 적용, Phase 7 25k+25k 코퍼스 골든 세트 벤치마크로 최종 검증 |
| Phase 5 — Worker가 provider secret을 소유하고 API가 내부 HTTP+토큰으로 프록시 (Ask LLM 스트리밍) | Phase 4 쿼리 임베딩 경계와 동일 패턴 재사용 — `service_role`/OpenRouter 키가 `ApiSettings`에 존재하지 않는 D-06 보안 모델을 그대로 적용 | ✓ Good — `apps/worker/src/worker/query_embedding.py` 자매 리스너로 구현, Phase 5 검증 통과 |
| Phase 5 — Citation 앵커는 서버 발급 요청-스코프 별칭(`[[wiki:w1]]`) | 36자 UUID를 모델이 정확히 복사하도록 요구하지 않음(CITE-01). `double_citation`은 파싱된 앵커 ∩ 발급된 앵커 | ✓ Good — CITE-01~06 전부 검증, 위조 앵커는 수집 시점(parse.py)에 이미 제거 |
| Phase 6 — 워크스페이스 전환 URL 소유(`/w/[workspaceId]`), `middleware.ts`가 유일한 쿠키 기록자 | React state의 낡은 workspace id가 조용히 빈 결과를 내는 것을 CVE-2025-29927 회피 미들웨어 경계와 동시에 구조적으로 방지 | ✓ Good — UI-01 검증 완료 |
| Phase 7 — 테넌트 격리 전수 스위트는 로컬 스택 한정, 클라우드 재실행 안 함 | RLS 정책은 스키마 정의(마이그레이션 적용)로 결정되며 로컬·클라우드 간 로직 차이가 없음 — 클라우드 전수 재실행은 비용/시간 대비 증분 신호가 낮음 | ✓ Good — OPS-04 9테이블 전수(읽기/쓰기/잡/Storage) 통과, `07-CONTEXT.md` D-09 |
| Phase 7 — 검색 기준선은 합성 벡터로 10^4~10^5 규모 로컬 패딩 후 실제 골든 세트 계층 | Phase 4의 12/12/8행 코퍼스는 플래너가 HNSW를 아예 고르지 않아 `strict_order` 대 `relaxed_order` 비교가 무의미했음(WINDOWS #10) | ✓ Good — 25k+25k 코퍼스로 WINDOWS #10 해소, `docs/ops/hnsw-order-benchmark.md` Phase 7 섹션 |
| Phase 7 — 비용/잡 파이프라인 관측은 새 라우트가 아니라 기존 Settings 페이지 탭 | Phase 6이 이미 5-표면 내비게이션을 확정 — 새 표면 추가보다 기존 셸 재사용이 일관적 | ✓ Good — Operations 패널, editor+ 권한, 폴링 없는 수동 새로고침으로 구현·검증 |

## Current State

**Shipped: v1.0 (2026-08-13).** All 73 v1 requirements across 7 phases are implemented and verified (`.planning/MILESTONES.md`). The product does what "What This Is" describes end to end: drop a PDF/URL/text source into a workspace, watch it become a linked wiki page, and ask questions that come back with citations traceable to both the compiled wiki and the original source chunk. Tenant isolation is enforced by Postgres RLS across all 9 tables and all application paths (read/write/job/Storage), not by application convention. Cost and job-pipeline health are observable per-workspace from the dashboard.

Not yet built (tracked as v2 candidates, not gaps): the `maintain` workflow (dedup/lint/compile log), backlinks/red-link-backlog panels, typed conflict detection, answer history, public sharing, external connectors, SSO. See `.planning/milestones/v1.0-REQUIREMENTS.md` §v2 Requirements.

## Next Milestone Goals

Not yet defined — run `/gsd-new-milestone` to scope v1.1. Candidate starting points surfaced during v1.0:
- Decide whether the OpenRouter-forfeited-caching cost problem needs addressing before opening ingest to more users (flagged ⚠️ Revisit in Key Decisions).
- Decide whether `/gsd-spec-phase` (SDD) should be used consistently, given it was only used for Phase 1-2 of v1.0.
- Evaluate real usage data on the Cytoscape knowledge canvas (kept in v1.0 against research recommendation) before investing further in it.
- Pricing/billing model — the cost cap and observation infrastructure (OPS-01, OPS-06) exist, but no actual pricing model is defined yet.

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
*Last updated: 2026-08-13 after v1.0 milestone completion*
