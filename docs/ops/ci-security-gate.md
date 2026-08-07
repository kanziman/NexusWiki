# CI 보안 게이트 — 관측 기록

task `P2-CI-01` (`02-09-PLAN.md` Task 3) · 게이트가 지키는 경계는 `checklists.json > decisions.db_access`

이 문서는 워크플로우가 **존재한다**가 아니라 **실패시킨다**를 기록한다. 관측되지 않은 게이트는
게이트가 아니다.

---

## 1. 게이트 구성

`.github/workflows/ci.yml`, `pull_request` 트리거, 잡 4개. 서드파티 액션 0개(`actions/*`만),
`${{ secrets.* }}` 참조 0건.

| 잡 | 무엇을 막는가 | 근거 |
|---|---|---|
| `pre-commit (ruff + prettier)` | 스타일 + ruff `TID251` banned-api | 02-03이 세운 lint 경계 |
| `service key 격리 (SEC-03)` | `apps/worker` 밖의 service key 경로 사용 | `decisions.db_access` |
| `번들 secret 유출 (SEC-05)` | 클라이언트 번들에 실린 secret 문자열 | `02-CONTEXT.md > D-06` |
| `pytest (루트 전체 스위트)` | 단위 회귀 | — |

---

## 2. 원격 관측 — 위반 브랜치 2종

2026-08-07, `kanziman/NexusWiki`. 위반 PR은 **병합하지 않고** 닫았으며 브랜치는 삭제했다.

| 잡 | PR #1 `service-import` 위반 | PR #2 `bundle-secret` 위반 | 정상 PR #3 |
|---|---|---|---|
| `service key 격리 (SEC-03)` | **fail** | pass | pass |
| `번들 secret 유출 (SEC-05)` | pass | **fail** | pass |
| `pre-commit` | **fail** | pass | pass |
| `pytest` | pass | pass | pass |

실행 ID: PR #1 `31148248589` · PR #2 `31148250775` · PR #3 `31148389257`(4잡 전부 pass).

각 위반이 자기 게이트만 켠다. PR #1에서 `pre-commit`이 함께 red인 것은 정상이다 — ruff
`TID251`이 같은 위반을 grep과 **독립적으로** 잡는다. 두 층이 같은 경계를 지킨다.

**PR #1 — `service key 격리` 로그 (실행 `31148248589`)**

```
ci_check_service_usage: apps/worker 밖에서 service key 경로 사용이 발견됐다
apps/api/src/api/_ci_violation_probe.py:12:from worker.db.service import service_client
사용자 요청 경로는 요청자 JWT를 쓰는 api.db.user 를 쓴다. 근거: checklists.json > decisions.db_access
```

**PR #2 — `번들 secret 유출` 로그 (실행 `31148250775`)**

```
ci_check_bundle_secrets: 패턴 'SUPABASE_SECRET_KEY' 이 apps/dashboard/.next/server/app/index.html 에 1건 있다
ci_check_bundle_secrets: 패턴 'SUPABASE_SECRET_KEY' 이 apps/dashboard/.next/server/app/page.js 에 1건 있다
ci_check_bundle_secrets: 패턴 'SUPABASE_SECRET_KEY' 이 apps/dashboard/.next/static/chunks/app/page-24686563d88cffa7.js 에 1건 있다
번들에 실린 문자열은 모든 방문자가 읽는다. service key는 worker 전용이며 클라이언트로 내려가서는 안 된다.
```

출력은 **파일 경로 · 패턴 이름 · 매치 개수** 셋뿐이고 매치된 값은 인쇄되지 않는다. 코드 수준
근거: `grep -laF`는 파일명만 내고, 개수는 `grep -oaF … | wc -l`로 `wc`에만 흘러간다. CI 로그는
공개되므로 secret을 탐지하는 검사가 그 secret을 로그로 옮기면 유출 경로가 하나 늘어난다.

⚠️ **위반 픽스처에 자격증명 모양의 값을 쓰지 않았다.** 이 저장소는 공개이고 PR 커밋은 브랜치를
지워도 이력에 남는다. `sb_secret_…` 형태를 심으면 시크릿 스캐닝을 건드리고 영구히 남으므로,
패턴 목록의 두 번째 항목인 `SUPABASE_SECRET_KEY` 문자열 자체를 리터럴로 썼다. 대신 이 픽스처로는
"패턴명을 인쇄하는가"와 "값을 인쇄하는가"를 관측으로 구분할 수 없어, 위의 코드 수준 근거로 갈음한다.

---

## 3. 관측이 잡은 결함 3건

로컬 통과만으로는 게이트가 작동한다고 말할 수 없었다. 첫 원격 실행에서 4개 잡 중 3개가
**위반 유무와 무관하게** 실패했다. 모든 것에 red를 내는 검사는 아무것도 지키지 않는다.

### 3.1 `pnpm install` 실패가 게이트 2개를 무력화 (`be2bcc3` → `fe879bf`)

```
[ERR_PNPM_IGNORED_BUILDS] Ignored build scripts: sharp@0.34.5, unrs-resolver@1.12.2
```

`pre-commit`과 `bundle-secrets`가 빌드와 grep에 **도달조차 못 했다**. 로컬 pnpm 11.0.9는 이
에러를 내지 않아 CI 11.18.0에서만 드러났다.

수정 과정에서 함정 두 개를 연달아 밟았고, 둘 다 **에러 없이 조용히 무시되어** 원래 실패가
그대로 남았다.

1. `package.json`의 `pnpm` 필드 — pnpm 11은 읽지 않는다(경고만 남긴다).
2. `onlyBuiltDependencies` — pnpm 11에서 **제거된 키**다. 현재 키는 `allowBuilds`이며
   리스트가 아니라 패키지→불리언 맵이다.

최종 해법은 `apps/dashboard/pnpm-workspace.yaml`의 `allowBuilds`다. `.npmrc`는 답이 아니다 —
pnpm 11은 auth/registry 외의 설정을 `.npmrc`에서 읽지 않는다.

⚠️ **첫 로컬 검증은 위양성이었다.** `node_modules`가 이미 차 있으면 `install`이 no-op이라
빌드 스크립트 분기를 타지 않는다. 이 설정을 검증하려면 반드시 `rm -rf node_modules` 후
CI와 동일한 명령(repo root에서 `--dir`)으로 확인해야 한다.

### 3.2 `uv sync --frozen`이 워크스페이스 멤버를 설치하지 않음 (`be2bcc3`)

```
ImportError while loading conftest 'apps/api/tests/conftest.py'
E   ModuleNotFoundError: No module named 'httpx'
```

uv 워크스페이스 멤버는 `apps/api` · `apps/worker` · `packages/core` 셋인데 루트만 동기화됐다.
`--all-packages`를 붙여 해소했다. 02-02가 `deferred-items.md`에 남긴 결함과 같은 뿌리다.

### 3.3 `strictDepBuilds`는 기능이지 장애물이 아니다

기본 `true`이며 `allowBuilds`에 열거되지 않은 패키지는 "미검토"로 간주되어 설치가 실패한다.
새 의존성이 `postinstall`을 들고 들어오면 CI가 먼저 멈춘다 — 공급망 관점에서 임의 코드 실행을
명시 승인으로 좁히는 장치이므로 끄지 않는다.

---

## 4. 이 게이트가 지키지 **못하는** 것

게이트의 한계를 적어 두지 않으면 "grep이 막고 있으니 안전하다"는 서술이 사실과 어긋난 채
남는다. `scripts/ci_check_service_usage.sh` 헤더에 같은 취지가 인라인으로 있다.

- **동적 import를 막지 못한다.** grep도 ruff `TID251`도 `importlib.import_module("worker.db.service")`
  형태를 잡지 못한다. api와 worker가 **단일 이미지**를 공유하므로 물리적으로 가능하다.
- **런타임 오용을 막지 못한다.** 정적 검사이므로 service key를 환경변수로 읽어 직접 HTTP를
  치는 경로는 보이지 않는다.
- **번들 검사는 빌드 산출물만 본다.** 서버 전용 코드나 미빌드 경로의 유출은 범위 밖이다.
- **DB 의존 테스트는 CI에서 skip된다.** 러너에 Supabase 스택을 세우지 않는다. 격리 왕복 증명은
  로컬 스택에서 수행돼 `docs/ops/tenant-isolation-proof.md`에 있고, 전수 스위트는 Phase 7
  `OPS-04`의 일이다. `-rs`로 건너뛴 테스트를 파일·행·사유까지 인쇄하므로 skip이 조용히
  사라지지는 않는다.

진짜 방어선은 이 게이트가 아니라 `0004`의 RLS 정책과 `0007` 섹션 8의 최소권한 매트릭스다.
게이트는 실수를 PR 단계에서 싸게 잡는 장치이지 마지막 방어선이 아니다.
