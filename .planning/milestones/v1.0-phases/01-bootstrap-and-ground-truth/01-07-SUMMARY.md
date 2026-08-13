---
phase: 01-bootstrap-and-ground-truth
plan: 07
subsystem: tooling
tags: [pre-commit, ruff, prettier, editorconfig, documentation]
requires:
  - phase: 01-bootstrap-and-ground-truth
    provides: uv Python workspace and Next.js dashboard scaffold
provides:
  - Python과 dashboard에만 적용되는 pre-commit 포맷·린트 게이트
  - 저장소 구조·로컬 개발·Railway/Supabase 배포 기록을 담은 루트 README
  - 전역 결정과 페이즈 로컬 결정의 두 계층 인용 규약
affects: [all-development, repository-conventions]
actuals:
  tokens: 5200
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns: [scoped pre-commit hooks, decision-lifetime citations]
key-files:
  created: [.pre-commit-config.yaml, .editorconfig, README.md, apps/dashboard/.prettierignore]
  modified: [pyproject.toml, .claude/CLAUDE.md, checklists.json, .gitignore]
key-decisions:
  - "prettier는 dashboard 작업 디렉터리 전체를 정규화하되 파일 전달을 끄고 files 정규식으로 실행 여부를 제한한다."
  - "결정의 수명에 따라 전역 원장 또는 페이즈 컨텍스트를 인용한다."
patterns-established:
  - "Ruff는 apps/packages Python만, prettier는 apps/dashboard만 처리한다."
  - "전역 결정은 decisions.<key>, 페이즈 결정은 NN-CONTEXT.md > D-XX를 인용한다."
requirements-completed: [BOOT-05]
coverage:
  - id: D1
    description: "Python 및 dashboard 포맷·린트 pre-commit 게이트"
    requirement: BOOT-05
    verification:
      - kind: integration
        ref: "uv run pre-commit run --all-files"
        status: pass
      - kind: integration
        ref: "Python/TypeScript probe git commit rejection"
        status: pass
    human_judgment: false
  - id: D2
    description: "README와 저장소 경로·결정 인용 규약 정합"
    requirement: BOOT-05
    verification:
      - kind: other
        ref: "README/path/JSON acceptance grep commands"
        status: pass
    human_judgment: false
  - id: D3
    description: "docs, supabase, checklists 원장의 포매터 제외"
    requirement: BOOT-05
    verification:
      - kind: integration
        ref: "uv run pre-commit run --files supabase/migrations/0005_storage.sql checklists.json"
        status: pass
    human_judgment: false
duration: 12 min
completed: 2026-08-05
status: complete
---

# Phase 01 Plan 07: 공통 툴링과 저장소 문서 Summary

**Python과 dashboard에 좁게 적용되는 커밋 게이트와 실제 운영 설정을 기록한 루트 README를 구축했다.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-05T03:25:00Z
- **Completed:** 2026-08-05T03:37:00Z
- **Tasks:** 3
- **Files modified:** 21

## Accomplishments

- Ruff와 prettier가 각자 소유한 소스만 처리하며 포맷 위반 커밋을 실제로 거부한다.
- 두 번째 `pre-commit run --all-files`가 종료 코드 0으로 통과하고 실행 전후 상태가 동일했다.
- README에 monorepo 구조, 54422 로컬 DB, 두 Railway Start Command와 변경 불가 리전을 기록했다.
- 구 `apps/fastapi-backend` 표기를 제거하고 결정 인용처를 수명에 따른 두 계층으로 명문화했다.

## Task Commits

1. **Task 1: pre-commit·ruff·editorconfig 범위 설정** - `574a8ed`
2. **Task 2: README와 저장소 문서 경로 정합** - `1828bcf`
3. **Task 3: dashboard 정규화와 거부 증명** - `18f3af7`

## Files Created/Modified

- `.pre-commit-config.yaml` - 범위 제한 ruff/prettier 훅
- `.editorconfig` - 언어별 들여쓰기와 공통 텍스트 규약
- `README.md` - 개발·배포·저장소 구조 안내
- `pyproject.toml` - ruff 룰셋과 제외 범위
- `.claude/CLAUDE.md` - 실재 경로와 두 계층 결정 인용 규약
- `checklists.json` - 구 Python 앱 경로 제거

## Decisions Made

- `pnpm --dir apps/dashboard`가 전달받은 루트 상대 경로를 찾지 못하므로 prettier에 `args: [.]`와 `pass_filenames: false`를 주었다. 훅 실행 여부 자체는 좁은 `files:` 정규식이 제어한다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 기존 Python 소스의 활성 Ruff 위반 정규화**
- **Found during:** Task 1
- **Issue:** 새 룰셋에서 import 순서와 의도적인 외부 바인딩이 실패했다.
- **Fix:** import/format을 정규화하고 엔트리포인트의 `S104`만 파일별 면제했다.
- **Files modified:** Python API/worker/core 소스, `pyproject.toml`
- **Verification:** `uv run ruff check apps packages`, `uv run ruff format --check apps packages`
- **Committed in:** `574a8ed`

**2. [Rule 3 - Blocking] prettier 훅의 작업 디렉터리와 전달 경로 불일치**
- **Found during:** Task 3
- **Issue:** pnpm이 dashboard로 이동한 뒤 pre-commit의 루트 상대 파일명을 찾지 못했다.
- **Fix:** 파일 전달을 끄고 dashboard의 `.`을 포맷하되 `files:` 정규식으로 훅 실행 범위를 유지했다.
- **Verification:** `uv run pre-commit run --all-files`
- **Committed in:** `18f3af7`

**Total deviations:** 2 auto-fixed (2 blocking). **Impact:** 계획의 범위 경계를 유지하면서 실제 훅 실행을 가능하게 했으며 범위 확장은 없다.

## Issues Encountered

- Python 프로브 커밋은 `ruff-check`/`ruff-format`으로 종료 코드 1, TypeScript 프로브는 `prettier`로 종료 코드 1을 관측했다.
- 범위 회귀 실행은 모든 훅이 skipped였고 상태 변화가 없었다.
- 동시 실행기의 `.planning/config.json` 및 미추적 자료는 기준선으로 보존하고 수정하지 않았다.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- BOOT-05 커밋 게이트가 준비되어 이후 모든 구현 커밋에 자동 적용된다.
- Phase 01의 남은 계획을 실행할 수 있다.

## Self-Check: PASSED

---
*Phase: 01-bootstrap-and-ground-truth*
*Completed: 2026-08-05*
