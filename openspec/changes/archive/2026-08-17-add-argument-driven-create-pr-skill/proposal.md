## Why

NexusWiki의 OpenSpec workflow에는 구현 결과를 안전하게 commit하고 GitHub PR로 연결하는 프로젝트 전용 절차가 없다. 기존 `create-pr` 사용 경험을 유지하면서도, 더러운 작업 트리에서 무관한 변경을 포함하지 않고 `$ARGUMENTS`로 추적 이슈를 정확히 연결하는 재사용 가능한 스킬이 필요하다.

GitHub umbrella issue: https://github.com/kanziman/NexusWiki/issues/9

## What Changes

- `$ARGUMENTS`로 GitHub 이슈 번호, `#번호`, 또는 같은 저장소의 이슈 URL을 받는 canonical `create-pr` 스킬을 추가한다.
- 현재 작업 범위의 명시적 파일 manifest만 stage하고, 기존 staged 변경이나 범위 밖 변경을 보존하는 commit 절차를 정의한다.
- 변경 파일, commit 메시지, base branch, PR 제목·본문을 mutation 전에 검토하고 승인받는다.
- 관련 검증을 새로 실행한 뒤 commit, non-force push, PR 생성 또는 기존 PR 재사용, 이슈 댓글 연결을 수행한다.
- Claude Code의 `/create-pr $ARGUMENTS` 명령은 canonical 스킬을 읽고 인자를 그대로 전달하는 thin adapter로 제공한다.

## Capabilities

### New Capabilities

- `pull-request-workflow`: 명시적 변경 범위와 GitHub 이슈를 기반으로 안전하게 commit하고 PR을 생성하는 workflow 계약

### Modified Capabilities

- 없음.

## Impact

- `.agents/skills/create-pr/`: Codex 등 에이전트가 공유하는 canonical workflow
- `.claude/commands/create-pr.md`: `$ARGUMENTS`를 전달하는 Claude Code adapter
- `.claude/CLAUDE.md`, `.gitignore`, `AGENTS.md`: 스킬 탐색 및 저장소 workflow 계약
- GitHub Issues/Projects와 `git`, `gh`, 프로젝트 검증 명령을 사용하는 개발 workflow
