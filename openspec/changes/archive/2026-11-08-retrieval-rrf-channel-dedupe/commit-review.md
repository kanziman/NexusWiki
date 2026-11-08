# 채택·커밋 검토 초안

2026-11-08 사용자가 아래 측정·q06 회귀와 파일 범위를 제시한 채택·로컬 커밋 요청에 “응”으로 승인했다. `docs/ops/retrieval-policy-change-log.md`의 독립 사람 승인과 `openspec/specs/pull-request-workflow/spec.md`의 사전 게이트를 충족한다. 아래 초안은 승인된 범위의 기록으로 보존한다. push·PR은 이번 실행 범위에 없다.

## 검토할 결과

- 공식 통과율·recall 26/36 → 27/36, MRR 0.316 → 0.563, 전체 언더필 0 → 0.
- 같은 수집의 재생 검색 hit@1 18/29 → 27/29, MRR 0.713 → 0.940. q06 때문에 hit@8은 29/29 → 28/29.
- 답변 공통 29문항 통과 23 → 28, 위조 앵커 0 → 0. q06은 일반 입고 2시간 대신 반품 검수 48시간을 답하는 실제 회귀다. 기대 사실 포함은 29/29 → 28/29.
- q06을 제외하거나 채점 기준을 바꾸지 않았다. 사전에 정한 성공 기준은 충족했지만 한 번의 합성 재생이며 운영 효과를 증명하지 않는다.
- 비용 정책 코드는 변경하지 않았다. 재생용 한도는 원복했고 임시 실행 환경은 정리했다. 테넌트 격리 리뷰는 사용자 요청으로 생략했다.

## 커밋 파일 범위

다음 파일만 포함한다. 로컬 `.worktrees/rrf-evidence-20261108/`의 답변·로그·성적표와 인증 파일은 제외한다. 타 작업의 worktree와 index 변경은 보존한다.

```text
apps/api/src/api/services/retrieval.py
apps/api/tests/test_retrieval_service.py
apps/worker/tests/test_ask_replay_script.py
packages/core/src/nexuswiki_core/retrieval_policy.py
packages/core/src/nexuswiki_core/rrf.py
packages/core/tests/test_retrieval_golden.py
packages/core/tests/test_rrf.py
scripts/ask_replay.py
scripts/benchmark_retrieval.py
docs/ops/ask-sample-replay.md
docs/ops/evaluation-map.md
docs/ops/retrieval-policy-change-log.md
docs/ops/benchmark-records/fusion-195-v1-sum-strict.json
docs/ops/benchmark-records/fusion-195-v2-best-rank-strict.json
docs/ops/benchmark-records/fusion-195b-v1-sum-strict.json
docs/ops/benchmark-records/fusion-195b-v2-best-rank-strict.json
openspec/specs/hybrid-retrieval/spec.md
openspec/specs/ask-replay-scorecard/spec.md
openspec/changes/archive/2026-11-08-retrieval-rrf-channel-dedupe/.openspec.yaml
openspec/changes/archive/2026-11-08-retrieval-rrf-channel-dedupe/proposal.md
openspec/changes/archive/2026-11-08-retrieval-rrf-channel-dedupe/design.md
openspec/changes/archive/2026-11-08-retrieval-rrf-channel-dedupe/tasks.md
openspec/changes/archive/2026-11-08-retrieval-rrf-channel-dedupe/specs/hybrid-retrieval/spec.md
openspec/changes/archive/2026-11-08-retrieval-rrf-channel-dedupe/specs/ask-replay-scorecard/spec.md
openspec/changes/archive/2026-11-08-retrieval-rrf-channel-dedupe/verification.md
openspec/changes/archive/2026-11-08-retrieval-rrf-channel-dedupe/reviews/spec-conformance-r1.md
openspec/changes/archive/2026-11-08-retrieval-rrf-channel-dedupe/reviews/spec-conformance-r2.md
openspec/changes/archive/2026-11-08-retrieval-rrf-channel-dedupe/commit-review.md
```

## 검증

최종 코드의 루트 pytest 969 passed, 222 skipped. 관련 111개 테스트, CI 범위 Ruff lint·관련 format과 change/specs strict 통과. 스크립트 전체 lint에는 기존 13건이 남아 있음을 `verification.md`에 기록했다. 승인 후 커밋 직전 관련 검증과 index 범위를 다시 확인한다.

## 커밋 메시지

```text
fix(retrieval): RRF 같은 채널의 중복 점수 합산 제거

- 같은 채널의 반복 근거는 최고 순위로 한 번만 반영
- 검색 응답과 재생 기록에 융합 규칙과 채널 기여 기록
- 동일 조건 전후 검색·답변 측정과 q06 회귀 기록

AC:
Given: 한 검색 채널에서 같은 위키 페이지의 청크가 여러 번 검색될 때
When: 기본 검색 정책으로 RRF 점수를 결합하면
Then: 채널별 최고 순위 한 번만 기여하고 서로 다른 채널의 기여는 합산된다

Refs: #195
```

## 향후 PR 초안

이번에는 발행하지 않는다. 기준 브랜치는 `main`, 제목은 `fix(retrieval): RRF 같은 채널의 중복 점수 합산 제거`다.

본문 초안:

```text
같은 채널에서 한 위키 페이지의 여러 청크 점수가 합산돼 위키가 원문보다 구조적으로 앞서던 동작을 고칩니다. 기본 정책을 채널별 최고 순위 한 번만 반영하는 v2로 바꾸고, 이전 sum 정책은 재현용으로 보존합니다.

공식 통과율·recall은 26/36 → 27/36, 동일 수집의 답변 공통 29문항 통과는 23 → 28, 위조 앵커는 0 → 0입니다. q06은 검색과 답변 모두 회귀했으며, 일반 입고 2시간 대신 반품 검수 48시간을 답한 한계를 기록했습니다.

검증: 루트 pytest 969 passed·222 skipped, 관련 lint·format, OpenSpec strict 검증. 스펙 준수 재리뷰 결과는 보고서를 참조합니다. 테넌트 격리 리뷰는 사용자 요청으로 생략했습니다. DB 마이그레이션은 없습니다.

Refs #195 (B 항목만 해당하며 A·C는 남아 있으므로 umbrella를 닫지 않습니다.)
```
