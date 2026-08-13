---
phase: 02-security-spine-and-shared-domain
plan: 09
subsystem: ci
tags: [github-actions, supply-chain, secret-scanning, pnpm, uv-workspace, fail-first]

# Dependency graph
requires:
  - phase: 02-security-spine-and-shared-domain
    provides: "02-03의 service_client(settings) 인자 필수 팩토리와 ruff TID251 banned-api — grep 게이트가 감싸는 안쪽 층"
  - phase: 02-security-spine-and-shared-domain
    provides: "02-02의 Settings 3계층 — ApiSettings가 secret 필드를 갖지 않는다는 사실이 이 게이트가 지키는 대상"
  - phase: 02-security-spine-and-shared-domain
    provides: "02-07의 worker 레이아웃 — grep 스코프가 실제 구조와 일치해야 한다"
provides:
  - ".github/workflows/ci.yml — pull_request 트리거 4잡, 서드파티 액션 0개, ${{ secrets.* }} 참조 0건"
  - "scripts/ci_check_service_usage.sh — apps/worker 밖의 service key 경로 사용 탐지 (SEC-03)"
  - "scripts/ci_check_bundle_secrets.sh — 클라이언트 번들 secret 문자열 탐지 (SEC-05), 매치 값 미출력"
  - "apps/dashboard/pnpm-workspace.yaml — allowBuilds. 없으면 게이트 2개가 위반과 무관하게 red가 된다"
  - "docs/ops/ci-security-gate.md — 원격 관측 기록과 게이트가 지키지 못하는 것 4가지"
affects: [phase-03, phase-07]

# Actuals (#2632)
actuals:
  tokens: 6800
  tasks: 3
  commits: 8

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "게이트는 '통과함'이 아니라 '알려진 나쁜 입력에서 실패함'을 먼저 증명한 뒤에만 clean tree의 exit 0을 신뢰한다"
    - "위반 픽스처에 자격증명 모양의 값을 쓰지 않는다 — 공개 저장소에서 PR 커밋은 브랜치를 지워도 이력에 남는다"
    - "secret을 탐지하는 검사는 그 secret을 로그로 옮기지 않는다 — 파일 경로·패턴 이름·개수만 낸다"
---

# 02-09: CI 보안 게이트

## 무엇을 만들었나

worker 밖의 service key 사용과 클라이언트 번들 secret 유출을 CI가 **빌드 실패**로 막는다.
요구사항은 워크플로우가 존재하는 것이 아니라 실패시키는 것이었고, 그래서 이 플랜의 산출물은
스크립트와 워크플로우가 아니라 **원격에서 관측된 red/green 행렬**이다.

| 잡 | PR #1 `service-import` 위반 | PR #2 `bundle-secret` 위반 | PR #3 정상 |
|---|---|---|---|
| `service key 격리 (SEC-03)` | **fail** | pass | pass |
| `번들 secret 유출 (SEC-05)` | pass | **fail** | pass |
| `pre-commit (ruff + prettier)` | **fail** | pass | pass |
| `pytest (루트 전체 스위트)` | pass | pass | pass |

실행 ID `31148248589` · `31148250775` · `31148457606`. 전문은
`docs/ops/ci-security-gate.md`. 위반 PR 2건은 병합하지 않고 닫았으며 브랜치는 삭제했다.

각 위반이 자기 게이트만 켠다. PR #1에서 `pre-commit`이 함께 red인 것은 정상이다 —
ruff `TID251`이 같은 위반을 grep과 **독립적으로** 잡는다.

## 관측이 잡은 것 — 이 플랜의 실제 성과

첫 원격 실행에서 **4잡 중 3개가 위반 유무와 무관하게 실패했다.** 로컬 검증은 전부 통과한
상태였다. 모든 것에 red를 내는 검사는 아무것도 지키지 않으므로, 그 시점에는 게이트가
작동한다고 말할 수 없었다.

**1. `pnpm install`이 죽어 게이트 2개가 빌드·grep에 도달조차 못 했다.**
`ERR_PNPM_IGNORED_BUILDS`(sharp, unrs-resolver). 로컬 pnpm 11.0.9는 이 에러를 내지 않아
CI 11.18.0에서만 드러났다. 수정 과정에서 **조용히 무시되는 키를 연달아 두 번** 밟았다 —
`package.json`의 `pnpm` 필드(pnpm 11이 읽지 않음)와 `onlyBuiltDependencies`(pnpm 11에서
제거된 키). 둘 다 에러 없이 무시되어 원래 실패가 그대로 남았다. 정답은
`pnpm-workspace.yaml`의 `allowBuilds`(리스트가 아니라 패키지→불리언 맵)다.

**2. `uv sync --frozen`이 워크스페이스 멤버를 설치하지 않아 pytest가 죽었다.**
`ModuleNotFoundError: No module named 'httpx'`. `--all-packages`로 해소.
02-02가 `deferred-items.md`에 남긴 결함과 같은 뿌리다.

**3. 첫 로컬 재현이 위양성이었다.** `node_modules`가 이미 차 있으면 `install`이 no-op이라
빌드 스크립트 분기를 타지 않는다. `rm -rf node_modules` 후 CI와 동일한 명령(repo root에서
`--dir`)·동일한 pnpm 버전으로 다시 확인하고서야 진짜 재현이 됐다. 이 함정은
`pnpm-workspace.yaml` 주석에 남겼다.

## 판단이 필요했던 지점

**위반 픽스처에 자격증명 모양의 값을 쓰지 않았다.** 이 저장소는 공개이고 PR 커밋은 브랜치를
지워도 이력에 남는다. `sb_secret_…` 형태를 심으면 시크릿 스캐닝을 건드리고 영구히 남으므로,
패턴 목록의 두 번째 항목인 `SUPABASE_SECRET_KEY` 문자열 자체를 리터럴로 썼다. 대가가 있다 —
이 픽스처로는 "패턴명을 인쇄하는가"와 "값을 인쇄하는가"를 관측으로 구분할 수 없다. 대신
코드 수준으로 갈음했다: `grep -laF`는 파일명만 내고 개수는 `grep -oaF … | wc -l`로 `wc`에만
흘러가므로 매치 내용은 캡처조차 되지 않는다.

**플랜 수용기준 1건은 문자 그대로 만족 불가였다.** `grep -c 'secrets\.' ci.yml == 0`을
요구하는데, 같은 플랜이 워크플로우가 `scripts/ci_check_bundle_secrets.sh`를 호출하도록
지시한다 — 파일명이 패턴에 걸린다. 의도(repository secret 미참조)는
`grep -E '\$\{\{\s*secrets\.'`로 확인했고 **0건**이다.

## 남은 한계

`docs/ops/ci-security-gate.md` §4에 전부 적었다. 요약하면 이 게이트는 **동적 import를
막지 못하고**(api와 worker가 단일 이미지를 공유하므로 물리적으로 가능), 런타임 오용을 보지
못하며, DB 의존 테스트는 CI에서 skip된다. 진짜 방어선은 `0004`의 RLS 정책과 `0007` 섹션 8의
최소권한 매트릭스이고, 이 게이트는 실수를 PR 단계에서 싸게 잡는 장치이지 마지막 방어선이 아니다.

⚠️ `strictDepBuilds`는 기본 `true`이므로 **새 의존성이 `postinstall`을 들고 들어오면 CI가
먼저 멈춘다.** 이건 장애물이 아니라 공급망 방어 장치이므로 끄지 말고 `allowBuilds`에 명시
승인으로 추가할 것.

## Self-Check: PASSED

- 두 스크립트가 알려진 나쁜 입력에서 non-zero, clean tree에서 exit 0 — 원격 관측으로 확인
- 위반 2종이 각각 자기 잡만 red로 만듦 — 교차 오염 없음
- 정상 PR에서 4잡 전부 green (`31148457606`)
- 저장소는 `main`, 위반 브랜치 로컬·원격 모두 없음, 트리 깨끗
- 로그가 위반 파일 경로와 근거를 내고 매치 값은 내지 않음
