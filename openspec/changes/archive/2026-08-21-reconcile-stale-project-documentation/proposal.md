## Why

v1 제품 계약을 OpenSpec으로 복원했지만 일부 현재 문서는 여전히 GSD `checklists*.json`과 존재하지 않는 `HANDOFF.md`를 활성 작업 원장으로 안내하고, 최신 마이그레이션과 구현 상태도 정확히 반영하지 못한다. 이 상태는 위키·QA에서 역사적 계획과 현재 계약을 혼동하게 하므로, 현재 문서의 출처와 사실을 코드 및 OpenSpec에 맞춰 정리해야 한다.

관련 이슈: [#60](https://github.com/kanziman/NexusWiki/issues/60)

## What Changes

- `.claude/CLAUDE.md`와 현재 reference 문서에서 활성 작업 원장을 GitHub Issues + OpenSpec으로 일치시킨다.
- `checklists.json`과 `checklists_v2.json`은 GSD 시기의 역사적 스냅샷이며 현재 진행 상태를 나타내지 않는다고 명시한다.
- 현재 reference 문서의 마이그레이션 번호, 테이블 수, queue 함수, 구현 상태, 경로와 수치 오류를 코드에 맞게 교정한다.
- 날짜가 붙은 architecture·ops·review 문서는 당시 상태의 역사 자료로 보존하고, 무차별적인 최신화 대상에서 제외한다.
- README와 디자인 문서의 중복 계약 및 불일치하는 TODO 수치를 정리한다.

## Capabilities

### New Capabilities

없음. 제품 동작이나 외부 계약을 추가하지 않는 문서 정합성 작업이다.

### Modified Capabilities

없음. 현재 canonical spec의 요구사항은 변경하지 않으며 `.openspec.yaml`에서 `skip_specs: true`를 사용한다.

## Impact

- 영향 문서: `.claude/CLAUDE.md`, `README.md`, `checklists*.json`, `docs/reference/`, `docs/design-systems/v2/`, `docs/architecture/index.html`
- 영향 코드·API·DB: 없음
- 검증: 문서 내 경로·수치·구현 주장 확인, JSON 파싱, 관련 문서 검사, OpenSpec strict validation
