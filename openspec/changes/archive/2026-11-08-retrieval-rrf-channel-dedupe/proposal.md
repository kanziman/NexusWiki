## Why

검색 결과에서 위키가 원문보다 구조적으로 높게 매겨진다. RRF 결합(`fuse_ranked_hits`)이 위키는 페이지 단위로 묶으면서 **같은 채널 안의 여러 청크 점수를 더하고**, 원문은 청크마다 따로 경쟁하게 두기 때문이다. 재생 검색 평가(PR #226)에서 30문항 모두 상위 6개가 위키, 원문은 7~8위였고 채널 장애는 0건이었다. 표준 RRF는 채널마다 문서 하나에 순위 하나만 준다. 이슈 #195의 B 항목이다.

## What Changes

- 융합 방식을 검색 정책의 명시적 필드로 올린다. 같은 채널에서 한 문서(위키 페이지 또는 원문 청크)는 그 채널 안의 **최고 순위로 한 번만** 기여한다(`best_rank`). 기존 동작(`sum`)은 정책 값으로 남아 이전 기록을 재현할 수 있다.
- `POLICY_VERSION`을 `hybrid-rrf-v1`에서 `hybrid-rrf-v2`로 올린다.
- 공식 검색 벤치마크에 융합 방식 비교(`compare-fusion-records`)를 추가한다. 핀이 같고 정책 차이가 융합 방식(과 버전)뿐일 때만 통과한다.
- 재생 검색 평가 기록에 근거별 채널 기여도(`contributions`)를 남긴다. 위키 우세가 같은 채널 합산에서 왔는지를 기록으로 보이기 위해서다.
- 전후 측정: 공식 벤치마크, 재생 검색 평가, 성적표 재생(답변 품질 회귀 확인)을 같은 조건에서 전후로 돌린다.

**BREAKING(내부 계약)**: 같은 질의의 검색 순위가 바뀐다. 검색 API 응답 형식은 같다.

범위 밖(#195의 나머지): A. 어휘 채널이 문장형 질문에 0건(`phraseto_tsquery`), C. 질의 임베딩 실패 시 근거 없음과 구별되지 않음. 각각 별도 change로 다룬다.

## Capabilities

### New Capabilities

(없음)

### Modified Capabilities

- `hybrid-retrieval`: "Rank-based configurable fusion" 요구사항에 같은 채널 안에서 문서당 한 번만 기여하는 규칙과 시나리오를 더한다
- `ask-replay-scorecard`: 검색 채점 기록에 근거별 채널 기여도를 남기는 규칙을 더한다

## Impact

- 코드: `packages/core/src/nexuswiki_core/rrf.py`, `retrieval_policy.py`, `packages/core/tests/test_rrf.py`, `scripts/benchmark_retrieval.py`, `scripts/ask_replay.py`와 테스트
- 동작: 검색 API와 Ask 후보의 순위. Ask 컨텍스트는 후보에서 이중 근거 쿼터(`select_dual_evidence`)로 고르므로 답변 영향은 측정으로 확인한다.
- DB · RLS · 마이그레이션 변경 없음.
- 문서: `docs/ops/retrieval-policy-change-log.md`(변경 이력 행과 독립 리뷰어 서명), `hnsw-order-benchmark.md` 또는 새 기록, `ask-sample-replay.md`, `evaluation-map.md`
- 비용: 성적표 재생 전후 약 $0.82 × 2, 문서 수집 약 $0.22. 공식 벤치마크와 검색 평가는 질의 임베딩만 쓴다.
