# 검색 정책 변경 절차와 변경 이력

> Phase 4 Plan 04/08 (RTV-04 · RTV-07). 정책을 SQL이 아니라 버전 있는 Python
> 계층이 소유한다는 결정과 그 되돌리기 비용은 `04-CONTEXT.md > D-05`~`D-08`에 있다.
> 이 문서는 그 결정을 되풀이하지 않고 **변경 증거 게이트**와 이력을 남긴다.

## 왜 이 문서가 있는가

`packages/core/src/nexuswiki_core/retrieval_policy.py`의 값 하나를 바꾸는 데는
1분이 걸리지만, 그 변경이 옳았는지 나중에 확인하는 데는 재현 가능한 기록이 필요하다.
기록 없이 바뀐 값은 되돌릴 근거도, 유지할 근거도 남기지 않는다. 그래서 정책 변경은
코드 리뷰만이 아니라 **증거 게이트**를 통과한다.

## 적용 범위

아래 중 하나라도 바뀌면 이 절차를 밟는다.

| 대상 | 위치 |
|---|---|
| `channel_weights` · `rrf_k` | `retrieval_policy.py` |
| `requested_k` · `channel_overfetch` | `retrieval_policy.py` |
| `vector_sql_max_candidates` · `lexical_sql_max_candidates` | `retrieval_policy.py` |
| `graph_enabled` 및 `graph_*` 한계값 전부 | `retrieval_policy.py` |
| 벡터 순서 모드 (`hnsw.iterative_scan`) · `ef_search` · `max_scan_tuples` | `supabase/migrations/` 신규 마이그레이션 |

범위 밖: 버그 수정, 리팩터링, 테스트 추가 — 관측 가능한 순위 결과를 바꾸지 않는 변경.

## 필수 요건 세 가지

**하나라도 빠지면 변경을 채택하지 않는다.**

### 1. 정책 버전 상승

`POLICY_VERSION`을 올린다(`hybrid-rrf-v1` → `hybrid-rrf-v2` …). 값만 바꾸고
버전을 그대로 두는 것은 금지다. 이전 벤치마크 레코드가 조용히 거짓이 되고,
`scripts/benchmark_retrieval.py`의 해시 게이트도 이 경로를 잡지 못한다.

### 2. 동일 조건 위의 before/after 벤치마크 레코드 쌍

두 레코드는 corpus/golden/manifest/generator/workspace/model/database/repeat 핀과
complete canonical `policy_content`를 보존해야 한다. 정책 차이는 변경 대상 하나로
한정해야 하며, comparator가 그 조건을 fail-closed로 검사해야 한다. `--output` 기록은
append-only다. 러너는 기존 파일 덮어쓰기를 `refusing_to_overwrite_prior_record`로
거부하며, 그 거부를 우회하지 않는다.

### 3. 독립 리뷰어 승인

변경자가 아닌 사람이 핀·정책 차이·품질·언더필을 확인하고 아래 이력 표에 서명한다.
로컬 Docker 지연을 production latency 근거로 쓰지 않는다. 승인 없는 정책 변경은
되돌린다.

## 절차

1. 가설을 한 문장으로 적는다 — 어떤 값을, 어느 방향으로, 무엇이 좋아진다고 기대하는가.
2. 현재 정책으로 before 레코드를 append-only로 남긴다.
3. 값 하나를 바꾸고 `POLICY_VERSION`을 올린다.
4. 같은 핀으로 after 레코드를 남기고 comparator를 실행한다.
5. 품질(`strict_query_pass_rate`, `recall_at_k`, 필수 근거 순위)을 먼저, 언더필을 함께,
   지연은 동률일 때만 읽는다.
6. 아래 표에 행을 추가하고 독립 리뷰어 승인을 받는다. 채택하지 않은 실험도 남긴다.

## 거부 조건 (fail-closed)

- corpus/golden/manifest/generator/workspace/model/database/repeat 핀 불일치
- 전체 `policy_content` 또는 canonical SHA 불일치(순서 비교), 혹은 graph-enabled 외
  정책 필드 차이(graph 비교)
- before 또는 after 한쪽만 있는 경우
- `POLICY_VERSION` 상승 없이 실제 정책 값을 바꾼 diff
- 로컬 Docker 지연만으로 production policy 변경을 정당화한 경우

## 변경 이력

| 날짜 | POLICY_VERSION (before → after) | 상태 / 비교 | 기록 | 관측 | 리뷰어 / 결정 |
|---|---|---|---|---|---|
| 2026-08-11 | `hybrid-rrf-v1` → `hybrid-rrf-v1` | Plan-07 history only | [strict](benchmark-records/phase-04-strict-order.json), [relaxed](benchmark-records/phase-04-relaxed-order.json), [graph off](benchmark-records/phase-04-graph-off.json), [graph on](benchmark-records/phase-04-graph-on.json) | **무효·superseded.** 실제 5채널 `RetrievalService`/bounded graph 측정이 아니어서 변경 근거가 될 수 없음. | 정책 변경 없음; 이전 `strict_keep_graph_off` 표기는 새 증거로 승인된 변경이 아님. |
| 2026-08-11 | `hybrid-rrf-v1` → `hybrid-rrf-v1` | Plan-08 measured, no policy change | [v4 strict](benchmark-records/phase-04-rerun-v4-strict-order.json) → [v4 relaxed](benchmark-records/phase-04-rerun-v4-relaxed-order.json) | order comparator `ok`; strict-pass delta −0.0277777778 (relaxed minus strict). `policy_content` byte-equivalent. | 정책 변경 없음. relaxed는 controlled direct-vector arm이며 deployed RPC 변경 근거가 아님. |
| 2026-08-11 | `hybrid-rrf-v1` → `hybrid-rrf-v1` | Plan-08 measured, no policy change | [v4 graph off](benchmark-records/phase-04-rerun-v4-graph-off.json) → [v4 graph on](benchmark-records/phase-04-rerun-v4-graph-on.json) | graph comparator `ok`; quality +0.0277777778, contribution +366, underfill 0, p50 +49.1695 ms (on minus off); 36 real graph RPC envelopes on. | 정책 변경 없음. graph-on 측정은 승인되지 않았으며 current safe default remains off. |

세 행 모두 `hybrid-rrf-v1` 값 자체를 바꾸지 않았다. 따라서 새 `POLICY_VERSION`,
migration, reviewer approval for a default change, 또는 deployment record가 없다.
현재 `strict_order`와 `graph_enabled = False`는 안전 기본값으로 유지되고, 그 변경은
이 절차의 미래 별도 작업이다.
