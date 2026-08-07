# Embedding Model Research

**Domain:** 한국어 위키/원문 청크의 벡터 표현 — 5채널 하이브리드 검색 중 벡터 채널 2개(`source_chunks.embedding`, `wiki_embeddings.embedding`)를 담당합니다.
**Researched:** 2026-08-07
**Confidence:** HIGH on 한국어 벤치마크 수치(고려대 NLP&AI Lab 공개 리더보드 직접 조회) · HIGH on 코드베이스 현황(직접 grep) · MEDIUM on 단가(공급자 공개 가격표, 변동 가능) · LOW on 자체 호스팅 지연 추정(실측 아님)

> **이 문서가 뒤집는 것.** `.planning/research/STACK.md`의 scope guard는 "OpenAI 1536-d embeddings"를 잠긴 전제로 취급합니다. 그 문장은 **2026-08-01 시점의 스냅샷**이며 이 문서로 대체됩니다. STACK.md는 날짜가 박힌 조사 기록이므로 수정하지 않습니다.

---

## 요약

OpenAI 임베딩을 오픈소스 임베딩으로 바꾸는 근거는 **비용이 아니라 한국어 검색 품질**입니다. OpenAI의 최상위 임베딩 모델이 한국어 검색 벤치마크에서 주요 오픈소스 모델 전부에 밀립니다. 이 프로젝트의 코어 가치가 "원문 청크와 위키 페이지 양쪽으로 추적 가능한 답변"이고 그 전제가 검색 품질이므로, 이 격차는 부수적 개선이 아닙니다.

동시에 **"오픈소스 모델"이 "API 키 제거"를 뜻하지 않습니다.** 호스티드 API로 부르면 벤더만 바뀌고 키는 남습니다. 키를 실제로 없애려면 자체 호스팅뿐이고, 그건 현재 예산의 약 10배입니다.

---

## 1. 전환 비용이 지금 가장 싼 이유

| 항목 | 상태 | 확인 방법 |
|---|---|---|
| 임베딩 **코드** | **없음** — `OPENAI_API_KEY`는 `WorkerSettings` 필드로만 존재 | `apps/worker/src/worker/settings.py:27` |
| 임베딩 **데이터** | **0건** | 스파이크 코퍼스는 난수 벡터였고 `db reset`으로 소거 (`supabase/spike/README.md`) |
| 모델을 정한 결정 | **없었음** — 태스크 설명의 전제로만 존재 | `checklists.json` P2-EMB 태스크 description |
| `embedding_version text` | **이미 존재** | `0007:276`, `0007:280` |

`embedding_version`은 `0007`이 "어휘 검색에만 버전이 있던 비대칭이 모델 교체 경로를 막는다"는 이유로 넣은 컬럼입니다(PROJECT.md Key Decisions). 그 판단이 지금 값을 합니다 — 교체 경로가 이미 열려 있습니다.

**데이터가 0건이므로 재임베딩 비용이 없습니다.** Phase 3가 임베딩을 생성하는 순간 이 창은 닫히고, 이후 교체는 전량 재임베딩을 수반합니다.

---

## 2. 한국어 검색 품질 — 결정 근거

고려대 NLP&AI Lab이 공개한 한국어 검색 리더보드, **NDCG@10 평균** (Ko-StrategyQA · AutoRAGRetrieval · MIRACL-ko 등):

| 모델 | NDCG@10 | 차원 | 최대 길이 | 라이선스 |
|---|---|---|---|---|
| **nlpai-lab/KURE-v1** | **0.69473** | 1024 | 8192 | MIT |
| BAAI/bge-m3 | 0.68723 | 1024 | 8192 | MIT |
| intfloat/multilingual-e5-large | 0.66370 | 1024 | 512 | MIT |
| intfloat/multilingual-e5-large-instruct | 0.64451 | 1024 | 512 | MIT |
| intfloat/multilingual-e5-base | 0.63216 | 768 | 512 | MIT |
| **openai/text-embedding-3-large** | **0.61670** | 3072 | 8191 | 독점 |

읽는 법 세 가지:

1. **OpenAI의 *상위* 모델이 표의 꼴찌입니다.** KURE-v1과의 격차는 +0.078 NDCG@10, 상대 **+12.7%**.
2. **이 프로젝트가 계획했던 건 `text-embedding-3-small`이고, 표에 없습니다.** 3-small은 MTEB 종합에서 3-large보다 낮으므로 한국어에서도 3-large 아래일 가능성이 높지만 — **이건 추론이지 측정이 아닙니다.** 표에 없는 숫자를 지어내지 않습니다.
3. **KURE-v1은 bge-m3에서 파인튜닝된 모델입니다.** 한국어 질의-문서 200만 쌍 + 예시당 hard negative 5개로 학습했고, 이득은 +0.0075 — bge-m3가 이미 대부분을 가져갑니다. 즉 **bge-m3만 써도 OpenAI 대비 이득의 90%를 얻습니다.**

⚠ 벤치마크는 데이터셋과 평가 조건에 종속됩니다. 최종 판정은 Phase 4 `RTV-06` 골든 질의 세트로 이 프로젝트의 실제 코퍼스에서 내려야 합니다.

---

## 3. 비용 — 전환의 근거가 **아닙니다**

| 방식 | 단가 | 이 프로젝트 규모의 실제 비용 |
|---|---|---|
| OpenAI text-embedding-3-small | $0.02 / 1M tokens (batch $0.01) | 1000페이지 PDF 전량 재색인 ≈ **$0.01** |
| bge-m3 — OpenRouter · Together | **$0.01 / 1M tokens** | 위의 절반 |
| bge-m3 — DeepInfra | OpenAI 임베딩 API 호환 | 동급 |
| **자체 호스팅 (Railway)** | RAM $10/GB·월 + $20/vCPU·월 | **~$40–50 / 월** |

OpenAI 임베딩 비용은 이 규모에서 **반올림 오차**입니다. 아끼려고 바꿀 이유가 없고, 실제로 오픈소스 호스티드가 더 싸긴 하지만 그 차액도 무의미합니다.

반대 방향이 중요합니다: **자체 호스팅은 예산을 파괴합니다.** bge-m3(568M 파라미터)는 fp16 가중치 ~1.1GB, 배치 활성화 포함 현실적으로 3–4GB RAM. Railway Hobby는 $5/월에 $5 크레딧이 전부이므로 양립하지 않습니다.

---

## 4. 세 갈래

### A. bge-m3 호스티드 API — **채택**

- 품질 +0.070 NDCG@10 (vs text-embedding-3-large), 단가 절반
- 아키텍처 변경 최소 — 임베딩 호출부가 아직 없으므로 처음부터 이 모델로 쓰면 됨
- ⚠ **키는 남습니다.** 벤더가 OpenAI → DeepInfra/Together/OpenRouter로 이동할 뿐입니다
- `0008`로 1024차 전환 필요

### B. KURE-v1 자체 호스팅 — 보류

- 한국어 최고 품질 + 키 완전 제거
- 호스티드 API 없음 (연구실 모델) → 자체 호스팅이 유일한 경로
- 월 $40–50으로 예산 10배 초과
- ⚠ 추가 위험: **질의 시점 임베딩은 사용자 질문의 크리티컬 패스**에 있습니다. 이미 교차 리전(`ap-southeast-1` ↔ `asia-southeast1`)으로 부풀려진 왕복 위에 CPU 추론 지연이 얹힙니다. 색인 시점(워커·배치)과 달리 이건 체감 지연입니다
- 예산 전제가 바뀌면 재검토 — bge-m3와 API 호환이므로 전환 비용은 재임베딩뿐

### C. OpenAI 유지 — 기각

변경 0. 대신 한국어 검색 품질을 측정된 선택지 중 가장 낮은 값으로 고정합니다.

---

## 5. `0008`이 해야 할 일

`0007` 이하는 클라우드에 올라가 **영구히 수정 불가**이므로 보정 마이그레이션이 필요합니다.

1. `source_chunks.embedding`, `wiki_embeddings.embedding` → `extensions.vector(1024)`
   (`0002:77`, `0002:138`)
2. HNSW 인덱스 2개 **drop → recreate** — 컬럼 타입 변경 시 필수
   (`source_chunks_embedding_idx`, `wiki_embeddings_embedding_idx`)
3. `search_chunks` RPC **drop → recreate** — 시그니처에 차원이 박혀 있음
   (`0007:72` `p_query extensions.vector(1536)`)
4. `embedding_version`에 새 모델 식별자를 쓰도록 앱 계약 확정 (컬럼은 이미 존재)
5. 섹션 8 revoke/grant 쌍은 **재적용 불필요** — 기존 테이블이며 새 테이블을 만들지 않음

**재임베딩 없음** (데이터 0건). 이것이 지금 하는 것과 Phase 3 이후에 하는 것의 유일하고 결정적인 차이입니다.

⚠ `0002:76`의 주석 `-- text-embedding-3-small(1536차원).`은 `0002`가 수정 불가이므로 그대로 남습니다. `0008` 헤더에 이 주석이 무효임을 명시해야 읽는 사람이 속지 않습니다.

---

## 6. 남은 미결정과 후속 후보

**미결정 — `0008` 착수 전 판정 필요:** 공급자 선택 (DeepInfra vs Together vs OpenRouter). 판정 기준은 단가가 아니라 **`ap-southeast-1`/`asia-southeast1`에서의 지연**과 OpenAI 임베딩 API 호환 여부입니다. 셋 다 $0.01/M 수준이라 가격은 변별력이 없습니다.

**후속 후보 (지금 결정하지 않음):** bge-m3는 dense · **sparse** · multi-vector를 한 모델에서 냅니다. 이 프로젝트는 Supabase가 `pg_bigm`/`pgroonga`를 제공하지 않아 앱 레이어 bigram 토크나이저를 직접 만들었는데(02-05), bge-m3의 sparse 벡터가 그 어휘 채널을 보강하거나 대체할 여지가 있습니다. 다만 5채널 구조와 `tsv_tokenizer_version` 체계를 동시에 건드리는 큰 변경이므로, **Phase 4 `RTV-06` 골든 질의 세트로 판정할 후보**로만 둡니다.

---

## 출처

- [KURE — 고려대 한국어 검색 특화 임베딩 모델 (벤치마크 리더보드)](https://github.com/nlpai-lab/KURE)
- [KURE: Embedding Model for Korean-Specific Retrieval (HCLT)](https://koreascience.kr/article/CFKO202533761230731.page)
- [BAAI/bge-m3 · Hugging Face](https://huggingface.co/BAAI/bge-m3)
- [bge-m3 — OpenRouter 가격](https://openrouter.ai/baai/bge-m3)
- [BAAI/bge-m3 — DeepInfra API Reference](https://deepinfra.com/BAAI/bge-m3/api)
- [OpenAI Embedding Pricing 2026](https://embeddingcost.com/openai)
- [BGE-M3 Hardware Requirements](https://runthisllm.com/model/bge-m3/)
- [Railway Pricing Plans](https://docs.railway.com/pricing/plans)
