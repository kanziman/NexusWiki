## Why

현재 단위 테스트만으로는 실제 합성 답변에서 확인한 정답·인용·거절 판정이 채점기 변경 뒤 유지되는지 알 수 없다. 저장된 결과를 네트워크 없이 PR마다 재채점하는 관문을 둔다. 추적: https://github.com/kanziman/NexusWiki/issues/245.

## What Changes

- 실제 합성 재생의 허용 필드만 추린 고정 fixture와 문항별 기대 판정, 원본 해시를 저장한다.
- 현재 `ask_replay.verdict`로 재채점하고 판정 차이·누락·중복·손상된 fixture를 실패 처리하는 CLI를 추가한다.
- 자격증명이나 모델 호출 없이 PR CI에서 실행하고, 의도한 판정 변경은 fixture와 근거를 함께 검토한다.
- 기존 출력 재채점은 새 모델·프롬프트의 출력 품질을 검증하지 못한다는 한계를 표시한다.

## Capabilities

### New Capabilities

- `offline-eval-regression-gate`: 저장된 합성 답변의 오프라인 재채점과 PR 실패 판정.

### Modified Capabilities

없음.

## Impact

`scripts/`의 검사 CLI·fixture, worker 테스트, `.github/workflows/ci.yml`, 평가 문서. 운영 코드·DB·모델 호출은 변경하지 않는다. 사용자가 권장안에 따른 계획 게이트와 구현 진행을 승인했다.
