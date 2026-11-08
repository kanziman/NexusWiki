# Spec Conformance 리뷰 — retrieval-rrf-channel-dedupe r1

- 판정: needs_fix
- 대상: `git diff HEAD`와 미추적 RRF 산출물. 기준 HEAD `5dded7b220147489e071d6e7f9d562af07834e11`, 커밋 전 작업 트리
- 일시: 2026-11-08
- 계약: 이 아카이브의 `specs/**/spec.md` 및 동기화된 `openspec/specs/`

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Rank-based configurable fusion / Channels return incomparable score ranges | 충족 | `packages/core/src/nexuswiki_core/rrf.py:95`는 원 점수 대신 채널 가중치와 순위로 기여를 계산한다. `packages/core/tests/test_rrf.py:44`는 거리 값 반전에도 순서가 유지됨을 확인한다. |
| Rank-based configurable fusion / Wiki page with several matching chunks in one channel | 충족 | `packages/core/src/nexuswiki_core/rrf.py:109`~`117`은 같은 채널의 중복 기여를 최댓값 한 번으로 남긴다. 가중치가 양수이므로 최고 순위 기여와 같다(`retrieval_policy.py:69`). `packages/core/tests/test_rrf.py:113`은 1·2·3위 청크가 1위 몫만 받음을 확인하고 `:135`는 입력 순서 독립성을 확인한다. |
| Rank-based configurable fusion / Evidence found by different channels | 충족 | `packages/core/src/nexuswiki_core/rrf.py:110`은 새 채널 기여를 별도로 저장하고 `:127`에서 채널 간 합산한다. `packages/core/tests/test_rrf.py:123`은 위키 벡터·어휘 기여의 합을 확인한다. |
| Rank-based configurable fusion / Policy identifies the aggregation rule | 부분 충족·수정 필요 | 벤치마크는 `scripts/benchmark_retrieval.py:74`~`96`에서 `same_channel_aggregation`과 버전을 기록하며 `packages/core/tests/test_retrieval_golden.py:457`에서 이를 확인한다. 기본 버전은 `retrieval_policy.py:16`의 v2다. 그러나 검색 결과의 `apps/api/src/api/services/retrieval.py:174`~`180`에는 `policy_version`만 있고 규칙 식별 내용은 없다. 검색 결과 팔을 검증하는 테스트도 추가되지 않았다. |
| Retrieval scoring records keep per-item channel contributions / Contribution kept for a ranked item | 충족 | `scripts/ask_replay.py:568`~`576`은 응답의 채널·기여를 기록하고 본문 필드를 복사하지 않는다. `apps/worker/tests/test_ask_replay_script.py:735`는 두 채널·두 기여와 본문 제외를 검증한다. |
| Retrieval scoring records keep per-item channel contributions / Older record without contributions | 충족 | `scripts/ask_replay.py:662`~`679`는 채널 기여 필드에 의존하지 않고 공통 문항을 집계한다. `apps/worker/tests/test_ask_replay_script.py:748`은 기여 없는 옛 기록과 새 기록을 비교한다. |

## 조치가 필요한 항목

1. **검색 결과에 융합 규칙 식별 내용이 없다.**
   - 근거: `openspec/specs/hybrid-retrieval/spec.md:35`~`37`의 `Policy identifies the aggregation rule`은 검색 결과와 벤치마크를 모두 대상으로 삼는다.
   - 위치: `apps/api/src/api/services/retrieval.py:174`~`180`.
   - 영향: 검색 응답은 v2라는 버전만 제공하고 `same_channel_aggregation`은 제공하지 않아, 명세가 요구한 정책 내용으로 합산 방식을 식별할 수 없다. 벤치마크 쪽 구현만으로 검색 결과 팔의 충족을 주장할 수 없다.
   - 제안: 검색 결과가 보고하는 정책 식별 내용에 `same_channel_aggregation`을 포함하고, 실제 검색 결과 경로에서 v2·`best_rank`가 함께 보고되는 테스트를 추가한다. 외부 응답 형식을 유지한다는 설계 의도 때문에 이 동작을 원하지 않는다면, 구현을 통과 처리하지 말고 해당 시나리오의 범위를 사람과 먼저 확정해야 한다.

## 검증 및 범위

리뷰 중 새로 실행한 `uv run python -m pytest packages/core/tests/test_rrf.py packages/core/tests/test_retrieval_golden.py apps/worker/tests/test_ask_replay_script.py -q`는 100개 통과했다. 테스트 통과는 위 검색 결과 시나리오의 누락을 대체하지 않는다.

측정·성공 기준 판정은 `verification.md`와 기록을 확인했다. q06의 실제 검색·답변 회귀를 숨기지 않고 명시했으며, 집계 기준 충족과 독립 사람 채택 승인을 구분하고 있다. 이 리뷰는 그 사람 승인을 대신하지 않는다.

## 판정 근거

여섯 시나리오 중 다섯 개는 구현과 테스트로 충족했다. 남은 하나는 벤치마크 팔만 구현돼 있고 검색 결과 팔에는 규칙 식별 내용과 테스트가 없다. 명시된 시나리오 범위 안의 코드·테스트 수정으로 해결할 수 있으므로 `needs_fix`다. 코드와 테스트는 수정하지 않았다.
