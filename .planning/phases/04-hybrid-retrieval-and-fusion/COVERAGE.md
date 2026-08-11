# API Coverage — Phase 4 검색 경로의 외부 표면

> Full coverage by default. Opt-outs are explicit, reasoned decisions.
>
> Phase 4의 외부 표면은 **셋**이고, 그중 하나는 이 페이즈가 결정하지 않는다.
>
> 1. **Supabase PostgREST** — 요청자 JWT로 검색 RPC를 부르는 경로 (`apps/api/src/api/db/user.py`)
> 2. **워커의 private query-embedding 리스너** — API가 부르는 유일한 비-Supabase 아웃바운드
>    (`apps/api/src/api/services/retrieval.py:50`)
> 3. **OpenRouter `POST /embeddings`** — 워커 뒤에 있으며 API는 이것을 보지 못한다.
>    이미 `03-ingest-and-compile-pipeline/COVERAGE.md` §2가 결정했고 **여기서 다시 결정하지 않는다.**
>
> ⚠️ 이 표는 **뺄셈의 기록**이다. 모든 능력은 INTEGRATE에서 시작하고, OPT-OUT은 한 줄 사유를
> 반드시 동반한다. 사유 없는 OPT-OUT은 결정되지 않은 구멍이며 이 게이트가 닫으려는 실패 양상
> 그 자체다.

## 1. Supabase PostgREST — `POST {SUPABASE_URL}/rest/v1/rpc/{function}`

전송 결정은 `checklists.json > decisions.db_transport` (rpc + SECURITY INVOKER + 요청자 JWT).
권한 매트릭스는 `supabase/migrations/0011_retrieval.sql:218-240`.

| capability | decision | reason |
|---|---|---|
| `POST /rpc/search_chunks` (원문 dense) | INTEGRATE | |
| `POST /rpc/search_wiki_embeddings` (위키 dense) | INTEGRATE | |
| `POST /rpc/search_source_lexical` (원문 어휘) | INTEGRATE | |
| `POST /rpc/search_wiki_lexical` (위키 어휘) | INTEGRATE | |
| `POST /rpc/expand_wiki_graph` (2차 웨이브 그래프) | INTEGRATE | |
| `Authorization: Bearer {요청자 JWT}` | INTEGRATE | |
| `apikey: {SUPABASE_PUBLISHABLE_KEY}` | INTEGRATE | |
| RPC 안에서 설정하는 HNSW GUC 3종 | INTEGRATE | `iterative_scan`·`ef_search`·`max_scan_tuples`는 함수 본문이 소유한다 — 호출자가 정할 수 있으면 재현성 축이 하나 늘어난다 |
| `service_role`로 검색 RPC 호출 | **OPT-OUT** | `service_role`은 BYPASSRLS다. 검색은 사용자 요청 경로이고 이 경로의 격리 수단은 RLS뿐이다 (`.claude/CLAUDE.md` Security). `0011:226-240`이 5개 함수 전부를 `authenticated`에만 grant해 이 선택을 구조로 만들었다 |
| `index_source_chunk_lexical` · `index_wiki_page_lexical` 호출 | **OPT-OUT** | 색인은 워커의 일이고 `0011:223-224`가 `service_role`에만 grant했다 — API가 이것을 부를 수 있으면 사용자가 자기 워크스페이스 색인을 임의로 다시 쓸 수 있다 |
| PostgREST 테이블 직접 SELECT (`GET /rest/v1/source_chunks?...`) | **OPT-OUT** | 융합 정책·과다인출·HNSW GUC가 전부 RPC 본문 안에 있다. 테이블을 직접 읽으면 그 전부를 우회하면서 `POLICY_VERSION` 스탬프 없는 결과가 나온다 — 벤치마크가 재현할 수 없는 경로 |
| PostgREST 전문검색 연산자 (`fts`·`plfts`·`wfts`) | **OPT-OUT** | ⚠️ 한국어 어휘 채널은 앱이 만든 bigram + `phraseto_tsquery('simple', …)`다. PostgREST 연산자를 쓰면 **질의 시점 토크나이저가 색인 시점과 달라지고 그 불일치는 조용히 실패한다** (`.claude/CLAUDE.md` Correctness). `tsv_tokenizer_version`이 존재하는 이유가 이것이다 |
| Embedded resources (`select=*,wiki_pages(*)`) | OPT-OUT | 증거 단위를 조립하는 것은 `RetrievalService`의 RRF 융합이다 — PostgREST 조인이 만든 중첩 구조는 채널별 기여도(`contributions`)를 표현할 수 없다 |
| `Range` / `Prefer: count=exact` 페이지네이션 | OPT-OUT | `requested_k`가 상한 8로 묶여 있다 (`routers/retrieval.py:23`) — 페이지네이션할 크기가 아니고, 2페이지는 다른 융합 결과를 뜻해 재현성이 깨진다 |
| `on_conflict` upsert | OPT-OUT | 검색 경로는 읽기 전용이다 |
| `Prefer: return=representation` | OPT-OUT | RPC가 이미 행 집합을 돌려준다 |
| GraphQL 엔드포인트 (`/graphql/v1`) | OPT-OUT | `config.toml`이 `graphql_public`을 노출하지만 검색 표면은 RPC 하나로 고정한다 — 두 번째 전송은 권한 매트릭스를 두 곳에서 지켜야 한다 |
| Realtime (구독) | OPT-OUT | 검색은 요청-응답이다. 잡 진행 구독은 03-07이 폴링으로 이미 닫았다 |
| Storage | OPT-OUT | 검색은 청크 텍스트를 읽지 원본 파일을 읽지 않는다 — 원본 접근은 Phase 5 이중 Citation의 몫 |

## 2. 워커 private query-embedding 리스너 — `POST {QUERY_EMBEDDING_INTERNAL_URL}`

경계 결정은 `docs/architecture/query-embedding-boundary.md` (Approved, **one-way**, 롤백 비용 high).
CI 가드는 `scripts/ci_check_query_embedding_boundary.sh`.

| capability | decision | reason |
|---|---|---|
| `POST` with `json={"text": …}` | INTEGRATE | |
| `Authorization: Bearer {QUERY_EMBEDDING_INTERNAL_TOKEN}` | INTEGRATE | 공급자 자격증명과 **다른** 토큰이다 — 내부 호출자 인증 전용 |
| `QUERY_EMBEDDING_TIMEOUT_SECONDS` 경계 | INTEGRATE | |
| `RETRIEVAL_MAX_QUERY_CHARS` 입력 상한 | INTEGRATE | `routers/retrieval.py:62` — 초과는 422 |
| 응답의 1024차 벡터 검증 | INTEGRATE | 워커가 검증한 벡터만 돌려준다 |
| 공급자 오류 마스킹 | INTEGRATE | 워커가 redact한다 — 공급자 메시지가 API 응답으로 새면 키·호스트가 드러난다 |
| API가 `OPENROUTER_API_KEY`를 갖는 것 | **OPT-OUT** | 경계 문서가 명시적으로 기각한 대안이다. 키는 워커 전용이며 `ApiSettings`·브라우저 어디에도 없다 |
| 리스너의 public 도메인/라우트 | **OPT-OUT** | Railway private network 전용. `railway.json`이 선언하고 CI가 지킨다 — 공개되면 무료 임베딩 프록시가 된다 |
| 리스너에 DB 클라이언트 | **OPT-OUT** | 경계 불변식이다. 검색의 DB 접근은 요청자 JWT `UserDb.rpc` 하나뿐이고 `service_role` 클라이언트는 이 경로에 없다 |
| 브라우저 직접 임베딩 | **OPT-OUT** | 경계 문서가 기각한 대안 — 공급자 자격증명이 워커 밖으로 나간다 |
| 배치 임베딩 (`input` 배열) | OPT-OUT | 질의는 요청당 하나다. 배치는 색인 경로(03-09)의 것이며 그쪽이 이미 갖고 있다 |
| 질의 임베딩 캐시 | OPT-OUT | not needed yet — 캐시 키가 `EMBEDDING_MODEL`·정규화 규칙에 묶여 무효화 축이 늘어난다. 도입한다면 근거는 Phase 4 골든 세트가 아니라 실사용 반복률이어야 한다 |

## 3. OpenRouter `POST /embeddings` — API 계층은 직접 붙지 않는다

이 표면은 워커 뒤에 있다. Phase 4가 내리는 결정은 "무엇을 쓸까"가 아니라 **"API가 여기에 직접
붙을 것인가"** 이고, 답은 아니오다 — 그래서 아래는 전부 OPT-OUT이다. 공급자 능력 자체의
INTEGRATE/OPT-OUT 판정은 `03-ingest-and-compile-pipeline/COVERAGE.md` §2가 소유하며,
03-04가 실측으로 닫았다 (`observed_embedding_dimensions: 1024`, provider DeepInfra).

| capability | decision | reason |
|---|---|---|
| API가 `POST /embeddings`를 직접 호출 | **OPT-OUT** | 경계 문서가 기각한 대안이다 — 직접 호출하려면 `ApiSettings`가 `OPENROUTER_API_KEY`를 가져야 하고, 그 순간 공급자 자격증명이 워커 capability 경계 밖으로 나간다 (`docs/architecture/query-embedding-boundary.md` §Rejected alternatives) |
| API가 `model`·`provider.order`·`encoding_format`을 정하는 것 | **OPT-OUT** | 임베딩 파라미터를 두 곳에서 정하면 색인 시점과 질의 시점 임베딩이 갈라진다 — 그 불일치는 dense 채널에서 조용히 품질만 떨어뜨린다. 워커가 양쪽을 모두 소유해야 한 축으로 남는다 |
| API가 공급자 `usage`·비용 필드를 읽는 것 | **OPT-OUT** | 비용 회계의 단위는 워크스페이스별 월 상한(`usage_events`, OPS-01)이고 그것을 쓰는 것은 워커다 — API가 공급자 응답을 직접 읽으면 같은 값을 두 곳에서 기록하게 된다 |
| 공급자 오류 본문을 API 응답으로 전달 | **OPT-OUT** | 워커가 redact한다 — 공급자 메시지에는 호스트·모델·때로는 키 조각이 들어 있다 |

## 4. 미확정 값 (관측되지 않은 사실 — 값을 지어내지 말 것)

| 값 | 확인처 | 기록처 | 상태 |
|---|---|---|---|
| `strict_order` vs `relaxed_order`의 실제 지연·언더필 차이 | 10⁴~10⁵ 청크 규모 + 프로덕션급 하드웨어에서 동일 corpus/golden/policy/model 해시로 양쪽 실행 | `docs/ops/hnsw-order-benchmark.md` | **미관측** — 04-04 Task 3 수용기준 #1 미충족, WINDOWS #10, Phase 7 OPS 이월 |
| graph off/on의 품질 델타 | 그래프 토글이 있는 러너 + graph 골든 질의 확장 (현재 36개 중 5개) | 같은 문서 | **미관측** — 기본값 off 유지가 안전 기본값이라 승격 근거가 없을 뿐 |
| `scripts/verify_retrieval_contract.sh` 결과 | 로컬 Docker 스택 기동 후 실행 | `04-VERIFICATION.md` | **미실행** — 04-03·04-04 양쪽 세션에서 스택 미기동 |

⚠️ 위 세 값은 Phase 4를 complete로 넘기기 전에 최소한 **상태가 정직하게 기록되어** 있어야 한다.
셋 다 "돌렸는데 통과했다"가 아니라 "돌리지 않았다"이며, 그 구분이 이 표의 존재 이유다.
