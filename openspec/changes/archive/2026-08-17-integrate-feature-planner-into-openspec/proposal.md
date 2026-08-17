## Why

현재 `openspec-propose`는 모든 planning artifact를 한 번에 생성하므로 요구사항 용어 합의, 중요한 아키텍처 선택, 범위 확정, 수직 슬라이스 승인을 단계적으로 보장하지 않는다. 또한 저장소 workflow는 Linear를 전제로 하지만 실제 작업 추적은 GitHub Issues와 Project에서 수행하려는 현재 운영 방식과 맞지 않는다.

## What Changes

- 기존 `proposal.md` → delta specs → `design.md` → `tasks.md` 구조와 `openspec-propose` 진입점은 유지하되, feature 기획에 요구사항 인터뷰와 네 개의 승인 게이트를 추가한다.
- 확정 요구사항과 용어는 proposal/specs, ADR와 Non-Goals는 design, Given-When-Then 수직 슬라이스는 tasks에 기록해 별도 `docs/features/*` 문서 없이 OpenSpec을 단일 기준으로 삼는다.
- 중요한 기술 선택이 있을 때만 세 가지 아키텍처 대안을 고정 기준으로 비교하고, 단순 변경에는 억지 대안을 만들지 않는다.
- Linear 기반 workflow를 GitHub umbrella issue, 수직 슬라이스 sub-issues, 사용자 Project #1의 Todo/In Progress/Done 상태로 교체한다.
- 사용자의 연속 진행 권한은 비본질적 승인 게이트를 통과시키되 material ambiguity와 필수 검증 실패에서는 계속 중단한다.
- Codex와 Claude의 propose 진입점이 하나의 공통 workflow 계약과 OpenSpec artifact 규칙을 사용하도록 구성한다.

## Capabilities

### New Capabilities

- `feature-planning-workflow`: OpenSpec feature 기획의 인터뷰, 승인 게이트, artifact 책임, GitHub issue 분해 계약

### Modified Capabilities

- `autonomous-workflow`: 연속 진행 권한이 feature 기획 승인 게이트와 상호작용하는 방식을 명확히 함

## Impact

- `AGENTS.md`의 필수 workflow 및 외부 추적기 계약
- `openspec/config.yaml`의 artifact별 작성 규칙
- Codex `.agents/skills/openspec-propose`와 Claude `.claude/commands/opsx/propose.md` 진입점
- GitHub 저장소 `kanziman/NexusWiki` Issues 및 사용자 Project #1
- Linear 관련 과거 archive 기록은 변경하지 않음

GitHub issue: #4 (`https://github.com/kanziman/NexusWiki/issues/4`)
