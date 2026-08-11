# HNSW 순서 모드 · 그래프 기본값 결정 기록

> 갱신: 2026-08-11, Phase 04 Plan 08 (RTV-04 · RTV-07). 이 문서는 로컬의
> 통제된 full-path 측정 기록이다. `relaxed_order`는 caller-session direct-vector
> query 측정이며, 변경되지 않은 `0011_retrieval.sql` RPC의 배포 측정이나 RPC 변경은 아니다.

## 현재 운영 기본값

`0011_retrieval.sql`의 `strict_order`와 Python 정책의 `graph_enabled = False`를
그대로 유지한다. 이 실행은 migration·배포·정책 버전 변경을 만들지 않았고,
벤치마크 수치만으로 기본값을 바꾸지 않는다. 변경을 채택하려면
[`retrieval-policy-change-log.md`](retrieval-policy-change-log.md)의
`POLICY_VERSION` 상승, 비교 가능한 before/after 기록, 독립 리뷰어 승인 절차를 모두
별도로 통과해야 한다.

## Plan-07 기록의 상태

아래 Plan-07 JSON 네 파일은 byte-for-byte 보존한 **무효·superseded 역사 기록**이다.
`retrieval-benchmark-v2`의 controlled direct-query/fixture 방식은 골든 질의를 실제
`RetrievalService` 5채널 경로로 실행한 RTV-04·RTV-07 증거가 아니므로, 이 문서의
현재 결론이나 정책 변경 근거로 사용하지 않는다.

| 역사 기록 (보존만 함) | 상태 |
|---|---|
| [strict](benchmark-records/phase-04-strict-order.json) · [relaxed](benchmark-records/phase-04-relaxed-order.json) | 무효·superseded — 실제 5채널/RRF 품질 측정이 아님 |
| [graph off](benchmark-records/phase-04-graph-off.json) · [graph on](benchmark-records/phase-04-graph-on.json) | 무효·superseded — 실제 bounded graph second wave 측정이 아님 |

## 재생성한 full-path 원시 기록

새 v4 JSON은 append-only로 추가했다. 각 arm은 고정 workspace
`ca4d1e07-2a51-5701-94d5-41c9a6081c6b`, 같은 corpus/golden/manifest/generator/model
핀과 repeat 3을 사용해, 36개 골든 질의 텍스트를 실제 `RetrievalService.retrieve()`에
전달했다. 각 query 결과에는 반환 UUID와 논리 ID 매핑, 네 first-wave 채널과 graph
envelope, RRF 결과 및 평가가 남아 있다. 각 기록의 전체 canonical `policy_content`와
SHA도 검증했다.

| arm | immutable v4 기록 | recall / strict pass | query underfill | p50 / p95 ms |
|---|---|---:|---:|---:|
| strict, graph off | [v4 strict](benchmark-records/phase-04-rerun-v4-strict-order.json) | 0.0277777778 / 0.0277777778 | 34 / 36 | 191.829 / 213.574 |
| relaxed, graph off | [v4 relaxed](benchmark-records/phase-04-rerun-v4-relaxed-order.json) | 0 / 0 | 36 / 36 | 273.8505 / 322.697 |
| strict, graph off | [v4 graph off](benchmark-records/phase-04-rerun-v4-graph-off.json) | 0.7222222222 / 0.7222222222 | 0 / 36 | 277.833 / 366.5 |
| strict, graph on | [v4 graph on](benchmark-records/phase-04-rerun-v4-graph-on.json) | 0.75 / 0.75 | 0 / 36 | 327.0025 / 358.931 |

The strict/relaxed comparator returned `{"status":"ok","quality_delta":-0.027777777777777776}`
(right minus left). Its policy contents and SHA are byte-equivalent; all required
comparison pins match. This is an observed quality decrease for the controlled
relaxed arm, not a claim that the deployed strict RPC was altered.

The graph comparator returned `{"status":"ok","quality_delta":0.02777777777777779,
"contribution_delta":366,"underfill_delta":0,"latency_ms_delta":49.169500000000085}`
(on minus off). The persisted policy objects differ only in `graph_enabled: false → true`.

| graph off → on observation | off | on | delta |
|---|---:|---:|---:|
| strict-query quality | 0.7222222222 | 0.75 | +0.0277777778 |
| graph contribution | 0 | 366 | +366 |
| query underfill | 0 | 0 | 0 |
| p50 total latency (ms) | 277.833 | 327.0025 | +49.1695 |

The graph-on record has 36 real `expand_wiki_graph` RPC envelopes with `status: ok`;
graph-off has 36 `disabled` envelopes. The off/on result therefore demonstrates the
bounded second wave and re-fusion, rather than a label-created ranking. Scoped cleanup
was run after every arm; the fixed benchmark workspace count is 0 after the v4 runs.

## 해석과 한계

The measurements are honest operational evidence for this pinned local corpus and
test-only deterministic embedder. They do not independently authorize a production
policy change, establish production latency, or override the deployed SQL strict GUC.
In particular, the positive graph delta is a measurement to review through the existing
change gate, not approval to turn graph on. Until that gate is completed, strict order
and graph off remain the safe current defaults.

## 배포와 되돌리기

This work made no migration and did not run `supabase db push`; there is no deployed
policy change to roll back. A future adoption of relaxed order or graph-on needs its own
versioned policy/migration change, new append-only comparable records, independent
review approval, deployment evidence, and an explicit successor rollback path.
