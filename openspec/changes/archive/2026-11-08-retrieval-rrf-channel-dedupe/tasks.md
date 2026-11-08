추적 이슈: [#195](https://github.com/kanziman/NexusWiki/issues/195)의 B 항목. A·C 및 비용 예약 복구는 이 change 범위 밖이다. 측정·검증 근거와 재개 경로는 `verification.md`를 본다.

## 1. 정책과 융합

- [x] 1.1 `retrieval_policy.py`에 `same_channel_aggregation`(`"sum"` | `"best_rank"`, 기본 `best_rank`) 필드와 검증 추가, `POLICY_VERSION`을 `hybrid-rrf-v2`로 올린다
- [x] 1.2 `rrf.py`의 `fuse_ranked_hits`가 `best_rank`일 때 같은 채널 · 같은 `canonical_id`는 최소 순위 한 번만 기여하게 한다. `sum`이면 기존 동작
- [x] 1.3 `packages/core/tests/test_rrf.py`에 스펙 시나리오 테스트 추가(같은 채널 청크 3개 → 1위 몫 한 번, 다른 채널 → 합산, 정렬되지 않은 입력에도 최소 순위, `sum` 재현), 기존 합산 가정 갱신

## 2. 공식 벤치마크

- [x] 2.1 `benchmark_retrieval.py`의 `policy_content`에 `same_channel_aggregation`을 포함한다
- [x] 2.2 `compare-fusion-records` 하위 명령 추가: 핀 동일, 정책 차이가 `same_channel_aggregation` · `version`뿐일 때만 통과, 없는 필드는 `sum`으로 해석. 거부 사례 테스트 포함

## 3. 재생 검색 기록

- [x] 3.1 `scripts/ask_replay.py`의 검색 기록 `ranked` 항목에 응답의 `channels`와 `contributions`를 담는다(본문 없음)
- [x] 3.2 기여가 없는 이전 기록과도 비교가 동작하는 테스트 추가

## 4. 전후 측정

- [x] 4.1 `main`을 worktree로 준비하고, 공유 544xx 스택 사용 여부를 확인한 뒤 공식 벤치마크 before(v1) · after(v2)를 같은 핀으로 실행해 append-only 기록을 남기고 `compare-fusion-records`로 비교한다
- [x] 4.2 546xx 재생 스택에 문서를 한 번 수집하고, 같은 수집 위에서 before 코드 · after 코드로 `retrieval-eval`과 `ask` 재생을 각각 실행한다(약 $0.82 × 2 + 수집 $0.22)
- [x] 4.3 설계 결정 7의 성공 기준으로 판정하고, before 기록의 채널 기여로 위키 합산을 숫자로 보인다
- [x] 4.4 재생 스택 · 서버 · worktree를 정리하고 측정 기록을 보존 폴더에 둔다

## 5. 문서

- [x] 5.1 `docs/ops/retrieval-policy-change-log.md`에 변경 이력 행을 추가한다(독립 리뷰어 칸은 사용자 서명 전까지 "승인 대기")
- [x] 5.2 `docs/ops/ask-sample-replay.md`에 전후 비교와 해석을 적는다
- [x] 5.3 `docs/ops/evaluation-map.md`에 적용 원장 행을 추가하고, 다음 순서에 "위키 기여 분리 실험(원문만 · 위키만 · 둘 다)"을 더한다

## 6. 검증

- [x] 6.1 새로 실행: `packages/core` · 재생 스크립트 테스트 · 루트 pytest 관련분 · ruff check · ruff format --check · `openspec validate retrieval-rrf-channel-dedupe --strict` · `openspec validate --specs`

## 7. 스펙 리뷰 후속

- [x] 7.1 검색 응답 meta에 `same_channel_aggregation`을 추가하고, 기본 `best_rank`와 명시적 `sum` 정책의 버전·규칙이 함께 보고되는지 API 서비스 테스트로 확인한다
