# Spec Conformance 리뷰 — retrieval-rrf-channel-dedupe r2

- 판정: pass
- 대상: `git diff HEAD`와 미추적 RRF 산출물. 기준 HEAD `5dded7b220147489e071d6e7f9d562af07834e11`, 커밋 전 작업 트리
- 일시: 2026-11-08
- 이전 라운드: `spec-conformance-r1.md`의 검색 결과 정책 식별 누락 1건

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Rank-based configurable fusion / Channels return incomparable score ranges | 충족 | `packages/core/src/nexuswiki_core/rrf.py:95`는 원 점수 대신 순위와 정책 가중치로 계산한다. `packages/core/tests/test_rrf.py:44`는 원 거리 반전에도 순서가 유지됨을 확인한다. |
| Rank-based configurable fusion / Wiki page with several matching chunks in one channel | 충족 | `packages/core/src/nexuswiki_core/rrf.py:109`~`117`은 같은 채널의 중복을 최대 기여 한 번으로 남긴다. `packages/core/tests/test_rrf.py:113`에서 1·2·3위 청크가 1위 몫만 받으며, `:135`에서 입력 순서 독립성도 검증한다. |
| Rank-based configurable fusion / Evidence found by different channels | 충족 | `packages/core/src/nexuswiki_core/rrf.py:110`은 새 채널 기여를 저장하고 `:127`은 채널 간 합을 점수로 삼는다. `packages/core/tests/test_rrf.py:123`은 위키 벡터·어휘 기여의 합을 검증한다. |
| Rank-based configurable fusion / Policy identifies the aggregation rule | 충족 | 수정된 `apps/api/src/api/services/retrieval.py:175`~`176`이 버전과 실제 정책의 `same_channel_aggregation`을 함께 보고한다. `apps/api/tests/test_retrieval_service.py:73`~`97`은 기본 v2·`best_rank`와 명시적 v1·`sum` 두 팔을 실제 서비스 경로에서 검증한다. 응답 모델은 `apps/api/src/api/routers/retrieval.py:42`의 자유 메타데이터이며 같은 파일 `:108`에서 서비스 메타데이터를 전달하므로 해당 식별자가 응답에서도 보존된다. 벤치마크는 `scripts/benchmark_retrieval.py:74`~`96`, 버전은 `retrieval_policy.py:16`, 대응 테스트는 `packages/core/tests/test_retrieval_golden.py:457`이다. |
| Retrieval scoring records keep per-item channel contributions / Contribution kept for a ranked item | 충족 | `scripts/ask_replay.py:568`~`576`이 채널·기여를 복사하고 본문 필드를 제외한다. `apps/worker/tests/test_ask_replay_script.py:735`는 두 채널·두 기여 및 본문 제외를 검증한다. |
| Retrieval scoring records keep per-item channel contributions / Older record without contributions | 충족 | `scripts/ask_replay.py:662`~`679`는 기여 필드와 독립적으로 공통 문항의 모든 비교 지표를 집계한다. `apps/worker/tests/test_ask_replay_script.py:748`은 옛 기록과 새 기록을 비교한다. |

## 조치가 필요한 항목

없음. r1에서 누락됐던 검색 결과의 정책 식별 내용과 해당 경로의 테스트가 추가됐다. 나머지 다섯 시나리오도 현재 작업 트리에서 다시 확인했다.

## 검증

리뷰 중 새로 실행한 `uv run python -m pytest packages/core/tests/test_rrf.py packages/core/tests/test_retrieval_golden.py apps/worker/tests/test_ask_replay_script.py apps/api/tests/test_retrieval_service.py -q`는 **111개 통과**했다. `git diff --check`도 통과했다. 코드·테스트는 수정하지 않았다.

## 판정 근거와 한계

모든 delta 시나리오에 구현과 테스트 근거가 있고, 동기화된 프로젝트 스펙의 대응 시나리오도 유지돼 있다. 따라서 스펙 준수는 `pass`다. 이는 q06의 실제 품질 회귀를 없애거나 정책 채택을 승인한다는 뜻이 아니다. 독립 사람 채택 승인은 별도 대기 상태이며, 사용자 요청으로 생략한 테넌트 격리 리뷰의 판정도 이 보고서에 포함하지 않는다.
