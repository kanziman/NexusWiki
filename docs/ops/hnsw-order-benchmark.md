# HNSW 순서 모드 · 그래프 기본값 결정 기록

> Phase 4 Plan 04 Task 3 (RTV-04 · RTV-07). 정책 계층 결정의 배경은
> `04-CONTEXT.md > D-05`~`D-08`, 수동 검증 분류는 `04-VALIDATION.md`
> §Manual-Only Verifications를 본다.

## 결정

| 항목 | 결정 | 성격 |
|---|---|---|
| 프로덕션 벡터 순서 모드 | `strict_order` **유지** | 변경 없음 |
| 그래프 채널 기본값 | `graph_enabled = False` **유지** | 변경 없음 |

**이 문서는 비교 측정 기록이 아니다. strict 대 relaxed 비교도, 그래프 off 대 on
비교도 실행하지 않았다.** 아래의 근거는 전부 제약·안전 기본값에서 나온 것이며
측정에서 나온 것이 하나도 없다. 이 문서에 지연·재현율·run ID 수치가 없는 것은
누락이 아니라 내용이다.

## 근거 — 측정이 아니라 제약

### 순서 모드

`strict_order`는 이 프로젝트의 상시 제약이다.

- `.claude/CLAUDE.md:21` — "벡터 검색은 post-filter — `set local hnsw.iterative_scan
  = strict_order`(pgvector 0.8+) **필수**, k보다 적게 돌아올 수 있음"
- `.claude/CLAUDE.md:300` — 같은 제약의 아키텍처 서술
- `supabase/migrations/0011_retrieval.sql:76`, `:147` — 두 벡터 RPC 정의에
  `set hnsw.iterative_scan = 'strict_order'`가 하드코딩되어 **이미 원격에 적용됨**
  (`docs/ops/migration-0011-record.md`)

즉 여기에는 채택을 검토할 "변경"이 존재하지 않는다. RTV-04의 금지 조항은
비교 불가능·미기록 실행으로부터 **변경을 채택하는 것**을 금지하며, 이미 배포된
안전 기본값을 **유지하는 데** 근거를 요구하지 않는다.

### 그래프 기본값

`packages/core/src/nexuswiki_core/retrieval_policy.py:38`의
`graph_enabled: bool = False`가 이미 안전 기본값이다. RTV-07이 금지하는 것은
기록된 off/on 근거 없는 **승격**이다. off 유지는 그 금지의 반대편이 아니라
그 금지가 지시하는 상태 그 자체다.

## 비교 실행을 하지 않은 이유

가용한 픽스처로 비교를 돌리는 것은 돌리지 않는 것보다 나쁘다.

1. **코퍼스 규모가 플랜 선택을 바꾼다.** 고정 코퍼스는
   `source_chunks` 12행 · `wiki_pages` 12행 · `wiki_links` 8행이다
   (`packages/core/tests/fixtures/retrieval/representative_corpus.v1.json`).
   이 규모에서 플래너는 HNSW 인덱스를 아예 고르지 않는다. Phase 2가 정확히 이것을
   관측했다 — btree+sort 비용 233 대 HNSW 349,657 (`.planning/STATE.md`
   Decisions §[Phase 02], `docs/ops/db-transport-spike.md`).
2. **따라서 나올 숫자는 다른 플랜을 잰 값이다.** 12행에서 얻은 strict 대 relaxed
   지연 차이는 HNSW 반복 스캔의 성질이 아니라 seq/btree 경로의 잡음이다. 그런데
   기록에 남는 순간 근거처럼 보인다. 이것이 이 플랜이 막으려고 존재하는 위협
   **T-04-12(오도하는 튜닝)** 그 자체다.
3. **그래프 쪽 계측기가 얇다.** 골든 36개 중 그래프 표면을 겨냥한 것은 5개
   (`g24`~`g28`)뿐이고, `scripts/benchmark_retrieval.py`에는 그래프 on/off 토글이
   없다 — 러너의 레코드는 `graph_delta.status`를
   `not_measured_fixture_adapter`로 정직하게 비워 둔다. 승격을 정당화하기에는
   부족하고, off 유지를 정당화하기에는 충분하다.
4. **프로덕션 유사 환경 조달은 이 페이즈의 범위가 아니다.** HNSW가 실제로
   관여하려면 대략 10⁴–10⁵ 청크가 필요하고, 그 임베딩 비용은 남은 OpenRouter
   예산(약 $4.95)과 Railway Hobby $5/mo 안에서 나와야 한다. 게다가 Phase 2의
   선례상 클라우드에 남긴 프로브 데이터는 사실상 영구다 — `jobs`에는 어느 롤에도
   DELETE가 없어 워크스페이스 삭제 cascade 말고는 정리 경로가 없다
   (`.planning/WINDOWS.md` #3, `.planning/STATE.md` [Phase 3] 항목). 이 작업은
   Phase 7 OPS에 속한다.

## 현재 실제로 존재하는 스탬프

`uv run python scripts/benchmark_retrieval.py --verify`가 남기는 값 중
**측정 없이도 참인 것**은 다음이 전부다.

| 스탬프 | 값 |
|---|---|
| `policy_version` | `hybrid-rrf-v1` |
| `corpus_version` / `corpus_sha256` | `representative-corpus-v1` / `0f9fcc00…c690c4` |
| `golden_version` / `golden_sha256` | `golden-queries-v1` / `82fee162…3e2e3b` |
| `git_sha` | 실행 시점 HEAD |
| `order_mode` | `not_measured_fixture_adapter` |
| `graph_enabled` | `false` |
| `metrics.graph_delta.status` | `not_measured_fixture_adapter` |

`order_mode`와 `graph_delta.status`의 값이 곧 이 문서의 요약이다. 러너는
순서 모드를 측정한 적이 없다고 스스로 말하고 있으며, 이 기록은 그 말을 덮지
않는다.

## 한계

### 1. 증명되지 않은 것

- `strict_order`와 `relaxed_order`의 실제 지연 차이 — 알 수 없음.
- `strict_order`가 프로덕션 규모에서 만들어 낼 언더필(요청 k보다 적게 반환)의
  빈도와 크기 — 알 수 없음. 이것은 `.claude/CLAUDE.md:21`이 경고하는 바로 그
  손실이며, 지금 우리는 그 손실을 감수하기로 했을 뿐 크기를 모른다.
- 그래프 on이 품질을 올리는지 내리는지 — 알 수 없음.
- 결과적으로 **RTV-04의 수용 기준(동일 해시 위 strict/relaxed 비교 기록)은
  충족되지 않았다.** `.planning/WINDOWS.md`에 `unrun-verify`로 등록하고
  Phase 7 OPS로 이월한다.

### 2. 변경을 정당화하려면 정확히 무엇이 필요한가

지금의 결정을 뒤집으려는 사람은 아래를 **전부** 채워야 한다. 하나라도 빠지면
`docs/ops/retrieval-policy-change-log.md`의 게이트에서 거부된다.

**코퍼스 규모.** 플래너가 실제로 HNSW Index Scan을 고르는 지점까지 키워야 한다.
Phase 2 관측(233 대 349,657)이 시작점이므로 최소 10⁴ 청크, 판정 안정성을 위해
10⁵을 목표로 한다. 전환점 자체는 추정하지 말고 `EXPLAIN (analyze, buffers)`로
확인한다.

**동일성.** 두 팔이 같은 것을 재야 한다 — 동일한 고정 코퍼스 sha256, 동일한
골든 sha256, 동일한 `POLICY_VERSION`, 동일한 임베딩 모델/차원, 동일한 git SHA.
러너는 이미 이 다섯을 스탬프로 남기므로, 두 레코드의 해당 필드가 글자 단위로
일치하지 않으면 그 비교는 무효다.

**하드웨어.** Supabase `ap-southeast-1` + Railway `asia-southeast1`의 실제 교차
리전 왕복 위에서 측정한다. 로컬 Docker 수치는 지연 판정에 쓸 수 없다.

**판정 지표와 순서.** 1순위는 품질 — `strict_query_pass_rate`, `recall_at_k`,
필수 근거의 평균/최악 순위. 품질이 실질적으로 동률일 때만 2순위인
`latency_ms.p50_total`/`p95_total`로 넘어간다. 언더필(`underfill.rate`,
`underfill.by_channel`)은 3순위가 아니라 **품질 항목으로 함께 읽는다** — 적게
반환된 채널은 재현율 손실의 원인이지 별개 사건이 아니다.

**그래프 쪽 선행 작업.** 골든 세트의 그래프 시나리오를 5개보다 충분히 늘리고,
`scripts/benchmark_retrieval.py`에 graph off/on 토글과 쿼리별
`graph_delta`(on 빼기 off) 산출을 추가해야 한다. 현재 러너로는 RTV-07이 요구하는
비교 자체가 불가능하다.

### 3. 절반은 예산 없이 지금도 닫을 수 있다

프로덕션 하드웨어를 진짜로 요구하는 것은 **지연 항목 하나뿐**이다. 언더필과
플랜 형태(`EXPLAIN`이 HNSW Index Scan을 고르는지, k보다 적게 돌아오는지)는
임베딩 API 호출 없이 로컬에서 대규모로 관측할 수 있다 — 정규화한 난수 1024차원
벡터를 대량 삽입하면 거리 분포는 실제와 다르지만 **인덱스 선택과 반환 행 수는
같은 성질로 나타난다.** 실험을 두 단계로 쪼개면 (a) 로컬 합성 대규모로 언더필과
플랜 형태를 먼저 닫고, (b) 예산이 허락할 때 지연만 프로덕션에서 재는 순서가
가능하다. 지금 (a)를 건너뛴 이유는 불가능해서가 아니라 Phase 4의 범위가
아니어서다.

### 4. 이 문서의 지위

이것은 근거 문서가 아니라 **근거 부재 기록**이다. 나중에 누군가
"hnsw-order-benchmark.md에서 strict를 골랐다"고 인용한다면 그 인용은 틀렸다.
strict는 고른 것이 아니라 제약이었고, 그래프 off는 고른 것이 아니라 아직 승격을
정당화할 근거가 없는 상태다.
