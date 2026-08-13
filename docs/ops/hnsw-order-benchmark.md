# HNSW 순서 모드 · 그래프 기본값 결정 기록

> 갱신: 2026-08-11, Phase 04 Plan 09 (RTV-04 gap closure). 이 문서는 로컬의
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

### v4 strict/relaxed 쌍 — superseded-invalid (RTV-04 gap closure, Plan 09)

`04-VERIFICATION.md`(검증 2026-08-11T12:12:40Z)가 발견한 정확한 결함: 위 v4 strict
기록(`git_sha 6adb0453d9cce3267a4d180e1dd95af65733442d`)과 v4 relaxed 기록
(`git_sha 466205625053b00d785312db84ae9f1c228ae1b2`)은 **서로 다른 두 git 리비전**에서
캡처됐다. `compare_order_records()`의 `_pins()`가 당시 `git_sha`를 포함하지 않아
이 러너-리비전 불일치를 잡지 못했고, 실제로는 비교 불가능한 두 실행을
`status: ok`로 통과시켰다. Plan 09가 `_pins()`에 `git_sha`를 아홉 번째 고정 필드로
추가하고, `compare_order_records()`에 `{left.order_mode, right.order_mode} ==
{strict_order, relaxed_order}` 단언을 추가한 뒤, 고정된 비교기로 이 v4 쌍을 다시
비교하면 `order_pair_pin_or_policy_mismatch`로 **거부**된다(종료 코드 2) — 이전에
`ok`를 반환하던 것과 대조적으로 수정된 비교기가 정확히 이 결함을 잡는다는 증거다.

**위 표의 v4 strict/relaxed 두 행은 이 순간부터 superseded-invalid로 취급한다.**
JSON 파일은 byte-for-byte 보존하고 삭제·덮어쓰기·재번호 매기지 않는다 — 다만 이
문서의 현재 order-mode 비교 결론이나 정책 근거로는 더 이상 인용하지 않는다.
v4 graph off/on 쌍(같은 `git_sha 466205625053b00d785312db84ae9f1c228ae1b2`)은 이
결함의 영향을 받지 않으며 그대로 유효하다 — 위 문단의 그래프 비교 결과는 변경 없음.

### v5 strict/relaxed 쌍 — 하나의 동일 커밋에서 재생성한 유효 기록

Plan 09 Task 2는 하나의 clean, committed 리비전(`git_sha
b9cda858979619da23121a341569a58afed61c46`)에서 strict, relaxed 두 arm을 커밋 없이
연속으로 실행했다. 각 arm은 고정 workspace `ca4d1e07-2a51-5701-94d5-41c9a6081c6b`를
loader/cleanup 계약으로 새로 적재·정리했고(각 arm 종료 후 해당 workspace 행 수 0을
`docker exec ... psql`로 직접 확인), 새 파일명(`-v5-`)에만 기록해 어떤 `-v4-` 또는
이전 파일도 편집·덮어쓰지 않았다.

| arm | immutable v5 기록 | recall / strict pass | query underfill | p50 / p95 ms |
|---|---|---:|---:|---:|
| strict, graph off | [v5 strict](benchmark-records/phase-04-rerun-v5-strict-order.json) | 0.7222222222 / 0.7222222222 | 0 / 36 | 296.318 / 336.208 |
| relaxed, graph off | [v5 relaxed](benchmark-records/phase-04-rerun-v5-relaxed-order.json) | 0 / 0 | 36 / 36 | 190.0925 / 210.191 |

The fixed comparator returned `{"status":"ok","quality_delta":-0.7222222222222222}`
(right minus left) for this v5 pair — `git_sha` and every other pin match, and both
records form a valid `{strict_order, relaxed_order}` pair, so the comparability
guarantee the gap-closure task exists to prove now holds. The relaxed arm again
shows zero vector-channel hits and full underfill (`wiki_vector`/`source_vector`
channel_hits both 0 across all 36 queries), consistent in direction with what the
invalid v4 relaxed record also showed — this is now measured evidence from one
pinned revision rather than an artifact of a runner mismatch, and it reinforces
(does not newly justify) keeping `strict_order` as the current default. Root-causing
why the caller-session relaxed-order direct-vector path returns zero hits on this
corpus is out of scope for this plan; it is not a `0011_retrieval.sql` RPC behavior
since `relaxed_order` never invokes that deployed function (see the note at the top
of this document).

⚠️ **git 작업 트리 참고:** 두 arm을 캡처하는 동안 `scripts/`, `apps/`, `packages/`,
`supabase/` — 즉 벤치마크 실행 경로에 영향을 주는 모든 디렉터리 — 는
`git status --porcelain -- scripts/ apps/ packages/ supabase/`로 clean함을 확인했다.
`.planning/`, `HANDOFF.md`, `checklists.json`, `docs/architecture/` 등 이 플랜과
무관한 사전 존재 문서·설정 변경사항은 워킹 트리에 남아 있었으나, 벤치마크 코드
경로와 무관하고 `git rev-parse HEAD`로 캡처하는 `git_sha` 값에도 영향을 주지 않는다
— 두 arm 사이에 어떤 커밋도 만들지 않았으므로 두 기록의 `git_sha`는 위와 같이
byte-identical하다.

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

RTV-04's remaining gap was the comparator, not the code path: `compare_order_records()`
did not pin runner identity, so it accepted the v4 strict/relaxed pair despite the two
records being captured from different git revisions. That comparator gap is now closed
(`_pins()` includes `git_sha`; the comparator also asserts a distinct
`{strict_order, relaxed_order}` pair), and the v5 pair is the first strict/relaxed
evidence that is genuinely comparable by that fixed check. It still does not change
either default — see 배포와 되돌리기 below.

## 배포와 되돌리기

This work made no migration and did not run `supabase db push`; there is no deployed
policy change to roll back. A future adoption of relaxed order or graph-on needs its own
versioned policy/migration change, new append-only comparable records, independent
review approval, deployment evidence, and an explicit successor rollback path.

## Phase 7 local canonical 50k strict/relaxed baseline

Phase 7 captured two new append-only full-path records on one committed revision
(`135a0f16a548ca54ad2d4dad01c326b42d55235a`), with the canonical 1024-dimension
25,000-source plus 25,000-wiki-vector corpus, unchanged 36-query multilingual golden
set, graph off, and repeat-count pin 3. The comparator accepted the pair:
`{"status":"ok","quality_delta":-0.2222222222222222}` (relaxed minus strict).

| arm | record | recall / strict pass | underfill | p50 / p95 total ms |
|---|---|---:|---:|---:|
| strict | [Phase 7 strict](benchmark-records/phase-07-strict-order.json) | 0.2222222222 / 0.2222222222 | 24 / 36 | 215.092 / 352.423 |
| relaxed | [Phase 7 relaxed](benchmark-records/phase-07-relaxed-order.json) | 0 / 0 | 36 / 36 | 215.6465 / 278.638 |

Each record retains `retrieval-hnsw-explain-v1` raw `EXPLAIN (ANALYZE, BUFFERS,
FORMAT JSON)` evidence for the scoped `search_chunks`/`source_chunks` and
`search_wiki_embeddings`/`wiki_embeddings` vector shapes. Both raw plans contain an
embedding index scan (`source_chunks_embedding_idx`, `wiki_embeddings_embedding_idx`),
so each truthfully records `representative_hnsw_observed`; no scale escalation is
required for this local baseline. The per-channel p50/p95 summaries are stored in each
immutable record rather than being inferred from this table.

This evidence neither changes `strict_order` nor authorizes a policy change. The
relaxed caller-session measurement underfills every golden query and is not a deployed
RPC policy result; any future proposal must cite these pinned records through
[`retrieval-policy-change-log.md`](retrieval-policy-change-log.md).
