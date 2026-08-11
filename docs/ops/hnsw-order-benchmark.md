# HNSW 순서 모드 · 그래프 기본값 결정 기록

> 승인: 2026-08-11, Task 3 `strict_keep_graph_off`. 이 결정은 로컬의 통제된
> direct-query 측정이며, relaxed 결과는 변경되지 않은 0011 RPC의 측정이 아니다.

## 결정

`0011_retrieval.sql`의 `strict_order`를 그대로 배포 기본값으로 유지한다. 새
`0012` 마이그레이션은 만들지 않는다. `graph_enabled = False`도 유지한다.

엄격/완화 순서와 graph off/on 모두 동일한 입력 핀을 가진다: policy
`hybrid-rrf-v1` / content SHA-256 `936bc543…f1817`, representative corpus
`0f9fcc00…c690c4`, golden set `82fee162…e2e3b`, HNSW manifest
`5f961eeb…05252b`, seed `nexuswiki-phase-04-hnsw-v1`, workspace
`8cff8c27-82f9-5fdc-b914-f9eb77fcba48`, relation별 target 25,000 + decoy
25,000, repeat 3, local `supabase_db_NexusWiki`다. 각 arm은 해당 데이터셋을
새로 로드하고 두 named HNSW-index JSON-plan preflight를 통과한 뒤 scoped cleanup했다.

## 원시 기록과 결과

| 비교 | 원시 기록 | recall / strict pass / underfill | p50 / p95 ms |
|---|---|---:|---:|
| strict, graph off | `phase-04-strict-order.json` | 1.0 / 1.0 / 0 | 2786.23 / 2949.07 |
| relaxed, graph off | `phase-04-relaxed-order.json` | 1.0 / 1.0 / 0 | 2834.59 / 2835.78 |
| strict, graph off | `phase-04-graph-off.json` | 1.0 / 1.0 / 0 | 2777.24 / 2778.98 |
| strict, graph on | `phase-04-graph-on.json` | 1.0 / 1.0 / 0 | 87.66 / 94.23 |

원시 파일은 [strict](benchmark-records/phase-04-strict-order.json),
[relaxed](benchmark-records/phase-04-relaxed-order.json),
[graph off](benchmark-records/phase-04-graph-off.json),
[graph on](benchmark-records/phase-04-graph-on.json)에 보존한다.

품질 우선 판정에서 strict/relaxed는 recall, strict pass, 필수 근거 rank, underfill이
동률이다. strict의 p50이 더 낮고 이미 0011의 안전한 RPC 계약이므로 strict를 유지한다.
relaxed 수치는 caller-session `SET LOCAL`을 사용한 controlled direct-query 측정일
뿐이며, function-level strict GUC를 가진 0011 RPC의 배포 측정/변경 근거가 아니다.

graph on은 어떤 쿼리에도 추가 graph contribution을 만들지 않았고 품질 delta도 0이다.
관측된 지연 차이는 graph 승격의 근거로 쓰지 않는다. 따라서 reviewer 승인에 따라
`graph_enabled`는 false로 남는다.

## 배포와 되돌리기

배포 변경이 없으므로 `supabase db push`를 실행하지 않았고 migration ledger도 추가하지
않았다. 향후 relaxed를 채택하려면 별도 immutable successor migration, Plan-06 local
contract, 새 paired record, deployment evidence, 그리고 strict를 복원하는 successor
migration rollback 기록이 모두 필요하다.
