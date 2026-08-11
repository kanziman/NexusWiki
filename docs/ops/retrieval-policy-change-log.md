# 검색 정책 변경 절차와 변경 이력

> Phase 4 Plan 04 Task 3 (RTV-04 · RTV-08). 정책을 SQL이 아니라 버전 있는 Python
> 계층이 소유한다는 결정과 그 되돌리기 비용은 `04-CONTEXT.md > D-05`~`D-08`에 있다.
> 여기서는 그 결정을 되풀이하지 않고 **집행 절차**만 정의한다.

## 왜 이 문서가 있는가

`packages/core/src/nexuswiki_core/retrieval_policy.py`의 값 하나를 바꾸는 데는
1분이 걸리지만, 그 변경이 옳았는지 나중에 확인하는 데는 재현 가능한 기록이
필요하다. 기록 없이 바뀐 값은 되돌릴 근거도, 유지할 근거도 남기지 않는다.
그래서 정책 변경은 코드 리뷰가 아니라 **증거 게이트**를 통과한다.

## 적용 범위

아래 중 하나라도 바뀌면 이 절차를 밟는다.

| 대상 | 위치 |
|---|---|
| `channel_weights` · `rrf_k` | `retrieval_policy.py` |
| `requested_k` · `channel_overfetch` | `retrieval_policy.py` |
| `vector_sql_max_candidates` · `lexical_sql_max_candidates` | `retrieval_policy.py` |
| `graph_enabled` 및 `graph_*` 한계값 전부 | `retrieval_policy.py` |
| 벡터 순서 모드 (`hnsw.iterative_scan`) · `ef_search` · `max_scan_tuples` | `supabase/migrations/` 신규 마이그레이션 |

범위 밖: 버그 수정, 리팩터링, 테스트 추가 — 관측 가능한 순위 결과를 바꾸지
않는 변경.

## 필수 요건 세 가지

**하나라도 빠지면 변경을 채택하지 않는다.**

### 1. 정책 버전 상승

`POLICY_VERSION`을 올린다(`hybrid-rrf-v1` → `hybrid-rrf-v2` …). 값만 바꾸고
버전을 그대로 두는 것은 금지다 — 이전 벤치마크 레코드가 조용히 거짓이 되고,
`scripts/benchmark_retrieval.py`의 해시 게이트도 이 경로를 잡지 못한다.

### 2. 동일 조건 위의 before/after 벤치마크 레코드 **쌍**

두 레코드는 아래 다섯 필드가 **글자 단위로 일치**해야 한다. 하나라도 다르면
그 비교는 무효이며 변경 근거로 쓸 수 없다.

- `corpus_version` / `corpus_sha256`
- `golden_version` / `golden_sha256`
- `embedding_model_version`
- 하드웨어·리전 (문서에 명시; 지연을 근거로 쓸 때는 프로덕션 유사 환경 필수)
- 정책 차이는 **변경 대상 항목 하나로 한정** — 두 값을 동시에 바꾼 비교는
  어느 쪽이 효과를 냈는지 말하지 못한다

레코드는 `--output` 으로 파일에 남기고 커밋한다. 러너는 기존 파일을 덮어쓰기를
거부한다(`refusing_to_overwrite_prior_record`) — 이 거부를 우회하지 않는다.

### 3. 리뷰어 승인

변경자가 아닌 사람이 (a) 두 레코드의 다섯 필드 일치, (b) 품질 지표가 실제로
개선되었는지, (c) 언더필이 늘지 않았는지를 확인하고 아래 표에 서명한다.
승인 없이 머지된 정책 변경은 되돌린다.

## 절차

1. 가설을 한 문장으로 적는다 — 어떤 값을, 어느 방향으로, 무엇이 좋아진다고
   기대하는가.
2. 현재 정책으로 벤치마크를 돌려 **before** 레코드를 남긴다.
3. 값 하나를 바꾸고 `POLICY_VERSION`을 올린다.
4. 같은 조건으로 **after** 레코드를 남긴다.
5. 판정: 품질(`strict_query_pass_rate`, `recall_at_k`, 필수 근거 순위)이 1순위,
   언더필은 품질과 함께 읽는다, 지연은 품질이 동률일 때만 본다.
6. 아래 표에 행을 추가하고 리뷰어 승인을 받는다. **채택하지 않기로 한 실험도
   행을 남긴다** — 시도했다 접은 기록이 없으면 같은 실험을 반복하게 된다.

## 거부 조건 (fail-closed)

- 코퍼스/골든/정책 해시 불일치 → 러너가 종료 코드 2로 거부
- before 또는 after 한쪽만 있는 경우
- 두 값을 동시에 바꾼 비교
- 지연을 근거로 들면서 로컬 Docker에서 측정한 경우
- `POLICY_VERSION` 상승 없이 값만 바뀐 diff

## 변경 이력

| 날짜 | POLICY_VERSION (before → after) | 변경 항목 | before 레코드 | after 레코드 | corpus / golden sha256 | 리뷰어 | 결정 |
|---|---|---|---|---|---|---|---|
| 2026-08-11 | — → `hybrid-rrf-v1` | 초기 기준선 (변경 없음) | 없음 | `scripts/benchmark_retrieval.py --verify` 픽스처 계약 실행 | `0f9fcc00…c690c4` / `82fee162…3e2e3b` | — | **변경 채택 없음.** 순서 모드는 `strict_order`, 그래프는 off로 유지 — 측정이 아니라 제약·안전 기본값에 따른 유지다. 근거와 그 한계는 `docs/ops/hnsw-order-benchmark.md` |
