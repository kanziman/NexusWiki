---
phase: 01-bootstrap-and-ground-truth
plan: 02
subsystem: database
tags: [supabase, postgres, storage, rls, docker]

requires:
  - phase: 01-bootstrap-and-ground-truth
    provides: uv 기반 bootstrap tracer와 로컬 검증 기반
provides:
  - 비공개 sources 버킷과 50MiB 제한
  - 예외 없이 UUID 3세그먼트 경로를 판정하는 SQL 함수
  - 멤버십 기반 Storage 조회·삽입·삭제 정책과 실행형 회귀 테스트
affects: [phase-01-cloud-push, phase-03-ingestion, storage, security]

actuals:
  tokens: 1816
  tasks: 3
  commits: 2

tech-stack:
  added: [Supabase CLI 2.111.0]
  patterns: [정규식 선검증 후 UUID 캐스팅, 정책 부재로 원본 불변성 강제, 트랜잭션 롤백 SQL 정책 테스트]

key-files:
  created:
    - supabase/migrations/0005_storage.sql
    - supabase/tests/0005_storage_policies.sql
    - scripts/verify_storage_policies.sh
  modified: []

key-decisions:
  - "경로 파서는 정확한 UUID/UUID/파일명 형식만 첫 UUID를 반환하고 나머지는 null을 반환한다."
  - "sources 객체에는 변경 정책을 만들지 않아 사용자 경로의 원본 덮어쓰기를 차단한다."
  - "CLI 호출에는 SUPABASE_NO_ANALYTICS=1을 적용한다."

patterns-established:
  - "Storage 경로 정책: bucket_id를 고정하고 storage_path_workspace(name)의 결과로 기존 멤버십 헬퍼를 호출한다."
  - "정책 회귀 테스트: ON_ERROR_STOP=1과 단일 트랜잭션 rollback으로 실패와 무잔여 상태를 함께 보장한다."

requirements-completed: [BOOT-01, BOOT-03]

coverage:
  - id: D1
    description: "비공개 sources 버킷과 정확한 3세그먼트 경로를 강제하는 Storage 정책"
    requirement: BOOT-01
    verification:
      - kind: integration
        ref: "supabase db reset && pg_policies sources_objects_% count = 3"
        status: pass
    human_judgment: false
  - id: D2
    description: "정상 경로 성공과 2세그먼트·비멤버·비 UUID 경로 거부의 실행형 증명"
    requirement: BOOT-01
    verification:
      - kind: integration
        ref: "bash scripts/verify_storage_policies.sh"
        status: pass
      - kind: integration
        ref: "INSERT 정책 제거 시 검증 스크립트 실패"
        status: pass
    human_judgment: false
  - id: D3
    description: "Supabase CLI 2.111.0과 544xx 로컬 스택에서 전체 마이그레이션 재적용"
    requirement: BOOT-03
    verification:
      - kind: integration
        ref: "SUPABASE_NO_ANALYTICS=1 supabase db reset; schema_migrations count = 6"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-08-03
status: complete
---

# Phase 1 Plan 2: Storage 경로 정책 Summary

**비공개 `sources` 버킷에서 UUID 3세그먼트 경로와 워크스페이스 역할을 함께 강제하고, 거부 동작을 재실행 가능한 SQL로 증명했다.**

## Performance

- **Duration:** 30 min
- **Started:** 2026-08-03T09:08:00Z
- **Completed:** 2026-08-03T09:37:57Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Supabase CLI 2.111.0으로 업그레이드하고 `SUPABASE_NO_ANALYTICS=1` 상태에서 544xx 로컬 스택과 여섯 마이그레이션을 재검증했다.
- `sources` 버킷과 조회·삽입·삭제 정책을 추가해 경로 형식과 워크스페이스 역할을 동시에 강제했다.
- 정상 3세그먼트만 허용하고 2세그먼트·비멤버·비 UUID 경로는 모두 42501로 거부되는 회귀 테스트를 추가했다.

## Task Commits

1. **Task 1: Supabase CLI 업그레이드 및 로컬 스택 재검증** - 환경 도구 업그레이드 (저장소 변경 없음)
2. **Task 2: sources 버킷과 경로 강제 정책** - `e50c6fe` (feat)
3. **Task 3: Storage 정책 집행 증명** - `2c7b54e` (test)

## Files Created/Modified

- `supabase/migrations/0005_storage.sql` - 안전한 경로 파서, 비공개 버킷, 역할별 정책 3종
- `supabase/tests/0005_storage_policies.sql` - 실제 authenticated 역할로 정책을 판정하는 롤백 테스트
- `scripts/verify_storage_policies.sh` - SQL 오류를 성공으로 오인하지 않는 실행 래퍼

## Decisions Made

- 계획의 D-05~D-08을 그대로 적용했다.
- CLI 2.111.0 배포 압축 파일에 함께 제공되는 `supabase`와 `supabase-go`를 SHA-256 검증 후 사용자 PATH에 설치했다.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Docker Desktop 엔진이 처음에는 응답하지 않아 애플리케이션을 재기동했다.
- CLI 업그레이드 뒤 새 컨테이너 이미지를 받는 동안 registry rate-limit이 일시 발생했으나 재시도 후 완료됐다.
- CLI 2.111.0은 `supabase-go` 동반 바이너리가 필요했다. 공식 압축 파일의 두 바이너리를 함께 설치한 뒤 `db reset`이 통과했다.
- 저장소에는 아직 `.pre-commit-config.yaml`이 없어 `pre-commit run --all-files`는 실행할 수 없었다. Task 커밋 자체의 기존 Git hook은 정상 통과했다.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `0005`가 `0006`보다 앞에 존재하고 전체 재적용되어 계획 01-03의 첫 클라우드 push 전제가 충족됐다.
- 로컬 CLI는 2.111.0이며 `sources` 정책의 긍정·부정 경로가 자동 검증된다.

## Self-Check: PASSED

- 생성 산출물 3개와 task commit 2개 확인
- `supabase db reset` 통과, `schema_migrations` 6행 확인
- `sources_objects_%` 정책 3행 및 변경 정책 부재 확인
- `bash scripts/verify_storage_policies.sh` 통과
- INSERT 정책 제거 시 검증 실패 확인 후 `supabase db reset`으로 복구

---
*Phase: 01-bootstrap-and-ground-truth*
*Completed: 2026-08-03*
