# Phase 3: Ingest and Compile Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-07
**Phase:** 3-Ingest and Compile Pipeline
**Areas discussed:** 0008 마이그레이션 경계

---

## 회색지대 선택

| Option | Description | Selected |
|--------|-------------|----------|
| 0008 마이그레이션 경계 | 1024차 보정 + `dead_letter_job()` 시그니처 + `usage_events` + 취소 상태 중 무엇까지 `0008`에 넣는가. push는 편도 | ✓ |
| 컴파일 산출 단위 | 소스 1개 → 페이지 N개 규칙, 같은 슬러그 재출현 시 덮어쓰기·병합·거부 | |
| 비용 상한과 취소 | OPS-01. 상한 단위·값, 인큐 거부 형태, `running` 잡 협조적 취소 | |
| 수집 게이트와 청킹 | ING-04/05. PDF 품질 임계값, URL 수집 방식, 청킹 토큰 수·오버랩 | |

**User's choice:** `0008 마이그레이션 경계` 단독
**Notes:** 나머지 3개는 researcher/planner 재량으로 위임. CONTEXT.md `<deferred>` §"이 페이즈 안에서 열려 있는 것"에 조사 대상으로 명시함.

---

## 0008 마이그레이션 경계

### Q1 — `0008`에 무엇까지 넣는가

판별 기준으로 제시한 사실: "`0008` 이하 수정 불가"는 **기존 객체 변경**에만 걸리고, 새 테이블·새 함수는 `0009`든 `0012`든 언제든 추가된다.

| Option | Description | Selected |
|--------|-------------|----------|
| 되돌릴 수 없는 것만 | 임베딩 1024차 3곳(`0002:77`, `0002:138`, `0007:72`) + HNSW 2개 drop→recreate + `search_chunks` drop→create. `dead_letter_job`·`usage_events`는 소비자 코드와 같은 마이그레이션으로 | ✓ |
| 1024차 + `dead_letter_job` | 원래 구상한 2건. 큐 원시연산을 파이프라인 코드보다 먼저 세운다. 대신 호출자 없는 함수가 클라우드에 먼저 올라간다 | |
| Phase 3 스키마 전부 한 번에 | + `usage_events` + 잡 취소 상태. push 왕복 1회. 대신 컬럼·머신을 코드 쓰기 전에 추측으로 확정해야 하고, 틀리면 그것도 수정 불가 구간에 들어간다 | |

**User's choice:** 되돌릴 수 없는 것만 → **D-01**

### Q2 — 클라우드 `db push`를 어느 지점에 박는가

제시한 사실: `0002`/`0007`이 이미 클라우드에 1536차로 올라가 있으므로 push 전에는 클라우드에서 어떤 임베딩도 만들 수 없다.

| Option | Description | Selected |
|--------|-------------|----------|
| Wave 1 단독 플랜, push까지 [BLOCKING] | `02-06-PLAN`이 `0007`에 쓴 관례. 나머지 전부가 그 위에 쌓인다 | ✓ |
| 작성·로컬만 Wave 1, push는 임베딩 플랜에서 | 공급자가 실제로 1024차를 돌려주는 걸 본 뒤 올린다. 대신 로컬↔클라우드 스키마가 페이즈 중간 내내 갈라진다 | |
| `0008`을 임베딩 핸들러 플랜에 합침 | 스키마와 소비 코드가 한 커밋에. 대신 파싱·컴파일 플랜이 기다리거나 1536차 가정 위에서 진행한다 | |

**User's choice:** Wave 1 단독 플랜, push까지 [BLOCKING] → **D-02**

### Q3 — `dead_letter_job()` 시그니처

근거로 인용한 코드: `release_job(p_job_id, p_worker_id)`의 `locked_by = p_worker_id` 술어가 "다른 워커의 진행을 덮어쓰지 않는다"를 참으로 만드는 유일한 장치이며, `supabase/tests/0007_queue_functions.sql`이 SQL 수준에서 고정한다.

| Option | Description | Selected |
|--------|-------------|----------|
| `release_job` 동형 — `(p_job_id, p_worker_id, p_error)` | 소유자 술어 포함. reap이 락을 뺏은 뒤 늦게 깨어난 워커가 남의 잡을 dead로 만드는 경로가 구조적으로 없어진다 | ✓ |
| 소유자 검사 없음 — `(p_job_id, p_error)` | service_role 전용이니 호출자를 신뢰. 대신 용도가 "독약 잡 즉시 dead"로 넓어지면 안전망이 없다 | |
| 함수를 만들지 않음 | `fail_job(backoff=0)` 수렴 유지(`queue.py:112-136`). 큐 표면은 안 늘지만 T-02-43이 열린 채 남는다 | |

**User's choice:** `release_job` 동형 → **D-03**

### Q4 — `embedding_version` 값 규약

논리적 선례로 인용: D-19가 `tsv_tokenizer_version`을 `bigram-nfkc-cf-v1`로 정한 이유 — 값의 유일한 존재 이유는 재임베딩 범위를 좁히는 것.

| Option | Description | Selected |
|--------|-------------|----------|
| 모델 + 공급자 + 버전 | `bge-m3@deepinfra-v1` 형태. 공급자마다 정규화·풀링·truncation이 달라 같은 모델명이어도 벡터가 다를 수 있다 | ✓(변형) |
| 모델명만 | `bge-m3`. 같은 가중치면 같은 벡터라는 가정 | |
| 모델 + 차원 | `bge-m3-1024`. 차원은 `vector(1024)`가 이미 강제하므로 중복 | |

**User's choice:** 자유 입력 — **"bge-m3 openrouter"**
**Notes:** 형태로는 1번(모델+공급자)을 고르면서, 동시에 `checklists.json > open_questions`에 열려 있던 **임베딩 공급자 판정(DeepInfra vs Together vs OpenRouter)까지 OpenRouter로 닫았다** → **D-04**.

전제를 검증한 뒤 진행함 — OpenRouter는 `POST /api/v1/embeddings`를 OpenAI 형식으로 제공하고 bge-m3는 1024차이므로 `.planning/research/EMBEDDING.md:116`의 판정 기준 중 "OpenAI 임베딩 API 호환"이 충족된다. 파생 이득으로 `OPENROUTER_API_KEY` 하나가 LLM과 임베딩을 모두 덮어 `OPENAI_API_KEY`가 워커에서 사라질 수 있다는 점을 함께 기록했다.

### Q5 — OpenRouter 라우팅이 백엔드 호스트를 바꾸는 문제 (Q4의 답이 되받은 질문)

제기한 우려: OpenRouter는 같은 모델을 여러 호스팅 업체에 라우팅하므로, 공급자를 인코딩하기로 한 D-04의 목적이 라우팅에 의해 무력화된다.

| Option | Description | Selected |
|--------|-------------|----------|
| 공급자 고정 + 폴백 금지 | `provider: { order: [...], allow_fallbacks: false }` 강제, 그 호스트명을 `embedding_version`에 기록. 장애 시 임베딩 잡이 실패하지만 잡은 재시도되고, 섞인 벡터는 재임베딩 외에 복구 수단이 없다 | ✓ |
| 라우팅 허용, 응답의 실제 호스트를 행별 기록 | 가용성 유지. 대신 한 워크스페이스 안에 섞인 버전이 공존한다 | |
| 신경 쓰지 않음 — `bge-m3@openrouter-v1` 고정 | 가장 단순. 틀렸다면 Phase 4 골든 세트가 품질 저하로 드러낸다 | |

**User's choice:** 공급자 고정 + 폴백 금지 → **D-05**
**Notes:** 복구 가능한 실패(잡 실패 → 재시도)를 복구 불가능한 성공(섞인 벡터)보다 택한 것으로 CONTEXT.md `<specifics>`에 기록.

---

## Claude's Discretion

사용자가 마무리 시점에 "나머지는 기존 관례를 따른 재량으로 적어도 된다"고 승인한 항목 — CONTEXT.md의 D-06~D-09.

- **D-06** — `0002:76`의 `text-embedding-3-small(1536차원)` 무효 주석을 `0008` 헤더에서 명시적으로 무효화
- **D-07** — `0008`을 단일 트랜잭션(`begin;…commit;`)으로. `0007:26-31`의 관례. `notify pgrst, 'reload schema';` 포함
- **D-08** — `search_chunks` 재생성 계약 6종을 `supabase/tests/0008_search_contract.sql` + `scripts/verify_search_contract.sh`로 단언하고 CI 게이트에 추가. 기존 `0007_queue_functions.sql` 러너 쌍을 복제
- **D-09** — 파일명 `supabase/migrations/0008_embedding_dimension.sql`, 기록 문서 `docs/ops/migration-0008-record.md`

## Deferred Ideas

논의 중 나왔거나 스카우트에서 확인되어 CONTEXT.md `<deferred>`에 보존한 항목.

**이 페이즈 안에서 위임된 것 (researcher/planner가 채움):** 컴파일 산출 단위(COMP-01/07) · 비용 상한과 잡 취소(OPS-01) · 수집 게이트와 청킹(ING-04/05).

⚠️ 이 중 **잡 취소 상태**는 `jobs.status` CHECK 변경, 즉 D-01의 판별 기준상 "기존 객체 변경"에 해당한다. `0008`에 포함되었어야 하는지 planner가 재검토하도록 CONTEXT.md에 명시했다.

**다른 페이즈로:** reap 타임아웃 최종 확정(핸들러 실측 후 Phase 3 후반) · `jobs` 하트비트 컬럼(02 D-16) · bge-m3 sparse 벡터 활용(Phase 4 RTV-06) · 나머지 4개 채널 검색 함수(`0007:64-66`이 Phase 4로 명시) · `relaxed_order` vs `strict_order` 벤치마크(Phase 4) · `README.md:16`의 `uv sync --frozen` 워크스페이스 멤버 미설치(02-02 발견, 미해결 이월)
