---
phase: 01-bootstrap-and-ground-truth
plan: 06
subsystem: deployment
tags: [docker, railway, fastapi, worker, supply-chain]

requires:
  - phase: 01-bootstrap-and-ground-truth
    provides: uv 워크스페이스와 API/worker tracer
provides:
  - venv만 포함하는 비루트 단일 Docker 런타임 이미지
  - Railway Singapore의 api/worker 이중 서비스
  - 서비스별 Supabase 변수 격리와 공개 API 헬스 엔드포인트
  - deployment ID 기반 동일 코드 런타임 판정 기록
affects: [phase-02-worker, phase-03-api, railway, operations]

actuals:
  tasks: 3
  commits: 5

tech-stack:
  added: [python:3.12-slim, ghcr.io/astral-sh/uv, Railway]
  patterns: [single-runtime-image, venv-only-copy, service-scoped-secrets, paired-deployment-verification]

key-files:
  created:
    - Dockerfile
    - .dockerignore
    - railway.json
    - docs/ops/railway-deploy-record.md
  modified:
    - scripts/smoke_tracer.sh
    - apps/worker/src/worker/__main__.py

key-decisions:
  - "두 서비스는 하나의 runtime stage와 Dockerfile을 공유하고 worker만 Custom Start Command를 사용한다."
  - "SUPABASE_SECRET_KEY는 worker 서비스 스코프에만 두며 공유 변수 그룹을 만들지 않는다."
  - "개별 Railway 빌드의 다이제스트가 달라 R8의 2차 판정(커밋·Dockerfile·런타임 SHA)을 사용한다."

patterns-established:
  - "Container boundary: runtime에는 /app/.venv만 복사하고 uid 10001 Python 프로세스가 PID 1로 실행된다."
  - "Deployment evidence: 공개 도메인과 deployment ID를 ops 문서의 재실행 가능한 입력으로 남긴다."

requirements-completed: [BOOT-08]

coverage:
  - id: D1
    description: "같은 로컬 이미지가 api와 worker를 기동하고 SIGTERM에 10초 안에 종료된다."
    requirement: BOOT-08
    verification:
      - kind: integration
        ref: "docker build; bash scripts/smoke_tracer.sh --image nexuswiki:local"
        status: pass
    human_judgment: false
  - id: D2
    description: "Railway 두 서비스가 Singapore에서 같은 Git 커밋과 Dockerfile을 실행한다."
    requirement: BOOT-08
    verification:
      - kind: deployment
        ref: "api deployment 9950852a-4d5d-4e36-aac0-85edc286290f; worker deployment a1164100-ba01-4733-b7ba-06121a898cc8"
        status: pass
    human_judgment: false
  - id: D3
    description: "api에는 service key가 없고 worker에만 존재한다."
    requirement: BOOT-08
    verification:
      - kind: security
        ref: "Railway service-scoped variable name inspection"
        status: pass
    human_judgment: false

duration: 3h
completed: 2026-08-03
status: complete
---

# Phase 01 Plan 06: Railway Single-Image Deployment Summary

**비루트 venv-only Docker 이미지 하나가 Railway Singapore의 api와 worker에서 실행되며, 서비스별 비밀 격리와 paired deployment 관측으로 동일 코드를 증명했다.**

## Performance

- **Duration:** 약 3시간 (인증·GitHub 설정 체크포인트 포함)
- **Completed:** 2026-08-03T12:57:52Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- builder에서 세 uv workspace package를 비편집 wheel로 설치하고 runtime에는 `/app/.venv`만 복사했다.
- uid 10001과 exec form CMD로 API/worker의 PID 1 및 graceful SIGTERM 경계를 검증했다.
- Railway `api`와 `worker`를 `asia-southeast1`에 배포하고 start command, healthcheck, 변수 스코프를 분리했다.
- 배포 `/health` 200과 API/worker 런타임 SHA 일치를 특정 deployment ID에서 확인했다.

## Task Commits

1. **Task 1: 단일 Docker 이미지와 image smoke tracer** — `1eb2dc6` (feat)
2. **Task 2: Railway 이중 서비스 구성과 배포 기록** — `3e1a3a8` (feat)
3. **Task 3: worker SHA 관측점과 paired deployment 판정** — `18f4d0a`, `5ca73af`, `261d462` (feat/chore/docs)

## Files Created/Modified

- `Dockerfile` — 단일 builder/runtime, venv-only COPY, 비루트 exec CMD
- `.dockerignore` — 프런트엔드·문서·시크릿·캐시 빌드 컨텍스트 제외
- `scripts/smoke_tracer.sh` — 같은 이미지 태그로 API와 worker를 기동하고 `docker stop` 검증
- `railway.json` — 시크릿 없는 공용 Dockerfile builder 설정
- `apps/worker/src/worker/__main__.py` — `worker.started.git_sha` 런타임 관측점
- `docs/ops/railway-deploy-record.md` — 서비스 구성, 공개 도메인, deployment ID, R8 2차 판정

## Decisions Made

- Railway의 서비스별 빌드가 byte-identical digest를 만들지 않아 커밋 SHA, `Dockerfile` 경로, 런타임 `GIT_SHA`가 모두 같은 R8 2차 판정을 적용했다.
- `api`는 이미지 기본 CMD를 유지하고 `worker`에만 `python -m worker`를 설정했다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] uv workspace member 전체 설치**
- **Found during:** Task 1
- **Issue:** package=false인 루트에서 계획의 `uv sync --frozen --no-dev --no-editable`만 실행하면 workspace member가 설치되지 않아 `import api`가 실패했다.
- **Fix:** 설치 명령에 `--all-packages`를 추가했다.
- **Files modified:** `Dockerfile`
- **Verification:** 컨테이너에서 `import api, worker, nexuswiki_core` 성공
- **Committed in:** `1eb2dc6`

**2. [Rule 3 - Blocking] Railway trial 단일 리전 구성 교정**
- **Found during:** Task 2
- **Issue:** 기본 `sfo` replica에 Singapore가 추가되어 trial 플랜의 단일 리전 제한으로 최초 재배포가 실패했다.
- **Fix:** `multiRegionConfig`에서 `sfo`를 제거하고 Singapore replica 하나만 유지한 뒤 두 서비스를 재배포했다.
- **Files modified:** Railway service configuration
- **Verification:** 두 서비스 `SUCCESS`, `asia-southeast1` replica 각 1개
- **Committed in:** 외부 Railway 설정, paired redeploy `5ca73af`

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 blocker). **Impact:** 계획의 단일 이미지·단일 리전 의도를 충족하기 위한 최소 교정이며 범위 확장은 없다.

## Issues Encountered

- `.env.local`의 기존 Railway token은 유효하지 않아 사용자의 CLI 로그인 세션으로 전환했다.
- 최초 저장소에는 Git remote가 없어 GitHub 연결 체크포인트 후 자동 배포를 재개했다.
- `/health/ready`는 HTTP 503으로 관측됐다. 계획 01-03의 클라우드 마이그레이션 push 전에는 허용되는 비차단 상태다.

## Authentication Gates

- Railway token 실패 후 사용자가 `railway login`을 완료했고, 이후 모든 CLI 호출에서 `RAILWAY_TOKEN`을 unset하여 로그인 세션만 사용했다.

## User Setup Required

None - Railway 로그인과 GitHub remote 연결이 체크포인트 중 완료됐다.

## Next Phase Readiness

- 후속 worker/API 계획은 `RAILWAY_GIT_COMMIT_SHA`와 공개 API 도메인을 그대로 사용할 수 있다.
- 계획 01-03 완료 후 `/health/ready` 200을 다시 확인해야 한다.

## Self-Check: PASSED

- key-files.created 전부 존재
- 01-06 production/task 커밋 5건 존재
- Docker build/import/non-root/CMD/image smoke, ruff, pytest 7건 통과
- Railway 두 서비스 SUCCESS, Singapore 단일 리전, Dockerfile 경로와 런타임 SHA 일치
- api service key 부재 및 worker 전용 스코프 확인

---
*Phase: 01-bootstrap-and-ground-truth*
*Completed: 2026-08-03*
