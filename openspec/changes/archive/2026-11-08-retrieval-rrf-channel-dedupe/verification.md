# 검증 기록

## 2026-11-08 재개 시 확인

추적: [#195 B](https://github.com/kanziman/NexusWiki/issues/195). 검색·답변 성공 기준은 `design.md` 결정 7을 따른다. 비용 정책 수정은 사용자가 후속 작업으로 미뤘으며 이 change에 포함하지 않는다.

- `uv run python -m pytest -q`: 968 passed, 222 skipped. 환경 의존 통합 테스트의 건너뜀을 통과로 세지 않는다.
- `uv run ruff check apps packages scripts/ask_replay.py`: 통과. CI·pre-commit의 Python 검사 범위는 `apps`·`packages`다.
- `uv run ruff format --check apps packages scripts/ask_replay.py scripts/benchmark_retrieval.py`: 150개 파일 통과.
- `openspec validate retrieval-rrf-channel-dedupe --strict`: 통과.
- `openspec validate --specs --strict`: 39개 스펙 통과. delta 동기화 전 현재 스펙 검사이며 동기화 완료를 뜻하지 않는다.
- `compare-fusion-records --before docs/ops/benchmark-records/fusion-195b-v1-sum-strict.json --after docs/ops/benchmark-records/fusion-195b-v2-best-rank-strict.json`: `ok`, 통과율·recall 변화 +1/36, MRR 변화 +0.246759, 전체 언더필 변화 0.
- 범위를 넓혀 `scripts/benchmark_retrieval.py`에도 Ruff lint를 적용하면 기존 SQL 문자열·subprocess 등 13건이 남는다. 이 결과는 위 CI 범위 통과와 구별하며 별도 정리 없이 전체 스크립트 lint 통과를 주장하지 않는다.

TypeScript·DB 스키마 변경은 없다. 위 검증은 답변 품질 재생이나 독립 리뷰어 승인을 대체하지 않는다.

## 재생 원본 위치와 무결성

기존 원본 루트: `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/39c9659d-b747-432c-bee4-425c0cd18db5/scratchpad/replay4`.

| 파일 | SHA-256 |
| --- | --- |
| `retrieval-before.json` | `a67ad0925b578a996f33510acb41f1ac9f200f8d957aee328b21dbf6f75b9e4c` |
| `retrieval-after.json` | `28535fdf752aa09c913bc16abc3e49a455356fa47b745850422d82cac530c91d` |
| `ask-before.json` | `483da07749737751e7a0734bd13858dc18493aa87b5d1384b309f9ec1431f835` |
| `ask-after.json` (무효) | `dad97aa88d9a0fe0a525cbe3c13a07467cb91ea9daf402113dcda4b3bed33eb2` |
| `ask-after2.json` (무효) | `9f8d05c11d7895dcddf4a74c26c8994b055ebc587c89948fc35c580e41126564` |
| `ask-after-valid.json` (정상 재생) | `f3a8c416735cf2fa76f47450121da0c2873104fb83d7a0e8d8f776f6a1c1b2ea` |

본문·인증 상태는 커밋하지 않는다. 합산 원인 확인은 답할 수 없는 q30까지 포함한 30문항의 위키 188건 중 180건이 단일 기여 최대치 `1/61`을 넘는다는 결과다. after는 위키 98건 중 초과 0건이다. 검색 품질 비교의 분모는 q30을 제외한 29문항이다.

## 답변 재생과 성공 기준 판정

사용자가 외부 모델 전송과 비용을 승인한 뒤 한 문항 점검과 전체 30문항을 실행했다. 실행 중 API·워커의 작업 디렉터리가 현재 저장소임을 확인했고, 별도 검색 점검에서 `hybrid-rrf-v2`를 확인했다. 상태 `resolved`만으로 통과로 세지 않고 현재 `verdict`로 공통 q01~q29를 채점했다.

before 23/29 → after 28/29 통과, 위조 앵커 0 → 0. before의 위키 인용 누락 q01·q02·q03·q04·q25·q26은 모두 after에서 통과했다. q06은 일반 입고 2시간 대신 반품 검수 48시간을 답해 통과 → 실패로 바뀌었다. before q30은 무효이므로 비교에서 제외했고 after q30의 정확한 거절 통과는 별도로 기록했다. 답변 기대 사실 포함은 29/29 → 28/29다.

설계 결정 7의 원문 상위 6 진입 증가, 공식 통과율·recall 비감소, 답변 통과 비감소와 위조 앵커 0건은 모두 충족했다. q06 회귀는 실제 회귀로 남기며 다른 이슈의 탓으로 제외하지 않는다. **채택은 독립 사람 승인 대기**다.

새 실행 원본은 `/private/tmp/rrf-resume-20261108`에 남겼고, 장기 로컬 사본·로그·성적표는 Git 제외 경로 `.worktrees/rrf-evidence-20261108/`에 보존했다. 인증 상태는 복사하지 않았다. `valid-after/api.log`와 `worker.log`는 이전 실패 실행 때 시작된 서버의 로그라 이전 실패와 정상 재생 구간을 함께 포함한다. 재생 전용 한도는 $5 → $8 → $5로 복원했고 비용 정책 코드·미정산 기록은 변경하지 않았다.

API·워커 두 프로세스와 546xx 재생 컨테이너를 중지했고, 변경 없는 before worktree를 제거했다. 공유 544xx 스택과 재생 DB 볼륨은 보존했다. 독립 사람 승인과 완료 후 검토·커밋 절차가 남아 있으며 push·PR은 수행하지 않는다.

## 완료 후 검토

delta를 `openspec/specs/`에 수동 동기화한 뒤 `openspec validate --specs --strict` 39개 통과와 change strict 통과를 확인했다. 루트 pytest를 다시 실행해 968 passed, 222 skipped, CI 범위 lint와 관련 format 검사도 통과했다. 이후 `openspec archive retrieval-rrf-channel-dedupe --skip-specs --yes --json`으로 아카이브했다. `--skip-specs`는 이미 동기화·검증한 delta의 중복 반영을 피하기 위한 것이다.

테넌트 격리 리뷰는 사용자의 명시적 요청으로 생략했다. 실행 중이던 리뷰어를 중지했으며 해당 게이트를 통과했다고 주장하지 않는다. 스펙 준수 리뷰는 별도로 진행한다.

스펙 준수 r1은 검색 응답의 융합 규칙 식별 누락 1건으로 `needs_fix`였다. change를 활성 경로로 되돌리고 apply 안내를 다시 확인한 뒤, `meta.same_channel_aggregation`을 추가했다. 기존 API 서비스 테스트를 기본 `best_rank`·명시적 v1 `sum` 두 정책으로 매개변수화해 버전과 규칙을 함께 확인했다. 관련 111개 테스트, CI 범위 lint, 관련 format 검사와 change/specs strict 검증이 통과했다. 순위와 LLM 입력은 바뀌지 않아 유료 재생은 반복하지 않았다.

후속 수정 뒤 루트 pytest를 새로 실행한 최종 결과는 **969 passed, 222 skipped**다. strict 재검증 후 같은 이름으로 재아카이브했다. r1 보고서는 보존하고 r2로 수정 결과를 재검토한다.

스펙 준수 r2는 `pass`로 확정됐다. 모든 delta 시나리오를 재확인했고 관련 테스트 111개와 diff 공백 검사가 통과했다. 보고서는 `reviews/spec-conformance-r2.md`다. 테넌트 격리 리뷰 생략과 독립 사람 승인 대기는 이 판정과 구분한다. stage·commit·push·PR은 아직 수행하지 않았다.

2026-11-08 사용자는 q06 회귀를 명시한 정책 채택 및 `commit-review.md` 범위의 로컬 커밋을 “응”으로 승인했다. 독립 사람 승인 기록은 정책 변경 이력에 반영했다. push·PR·배포 승인은 포함하지 않는다.

## 향후 eval 페이지 반영용 보존

사용자의 요청에 따라 `.worktrees/rrf-evidence-20261108/evaluation-summary.json`에 실행 조건·질문 세트 및 채점 코드 해시·공통 29문항의 전후 판정·토큰·비용·검색 집계·원본 경로와 SHA-256 색인을 저장했다. 답변 전문은 각각 `before/ask-before.json`, `valid-after/ask-after-valid.json`에 있고 검색 순위·채널 기여는 같은 폴더의 `retrieval-*.json`에 있다. 무효 재시도는 `failed-after/`, 공식 벤치마크 사본은 `benchmark/`, 최종 pytest·lint·format·스펙 검사 로그는 `checks/`에 분리했다. HTML 성적표는 루트 `scorecard.html`이다.

이 폴더는 Git 제외 경로의 로컬 사본이며 원격 백업이 아니다. 향후 eval 페이지 구현은 이 색인과 원본을 입력으로 삼을 수 있지만, 공개 번들에 답변·로그·자격증명을 넣지 않는다. 인증 상태는 보존 사본과 색인 모두에서 제외했다. 현재 eval 페이지 코드나 데이터 계약을 변경한 것은 아니다.
