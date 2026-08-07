---
phase: 02
slug: security-spine-and-shared-domain
status: blocked
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 1
asvs_level: 1
block_on: high
register_authored_at_plan_time: true
threats_total: 62
threats_closed: 59
created: 2026-08-07
---

# Phase 02 — Security

> 페이즈 단위 보안 계약: 위협 등록부, 수락 위험, 감사 이력.

등록부는 9개 PLAN의 `<threat_model>` 블록에서 재구성했다 — 번호 위협 59건 + `T-02-38b`
+ 공급망 위협 2건(`T-02-SC` 02-01 asyncpg · 02-02 pydantic-settings) = **62행**.

| 구분 | 수 |
|---|---|
| 종결 (mitigate 검증됨) | 54 |
| 종결 (accept, 아래 로그에 기록) | 5 |
| 미결 — **차단** (severity ≥ high) | **1** |
| 미결 — 비차단 (severity < high) | 2 |

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| 브라우저 ↔ api | 요청자 JWT를 실은 HTTP. publishable key는 클라이언트 공개 전제 | 사용자 자격증명, 워크스페이스 내용 |
| api ↔ Postgres | 요청자 JWT 기반 PostgREST RPC. **RLS가 격리를 강제하는 지점** | 테넌트 범위 행 |
| worker ↔ Postgres | `service_role` (BYPASSRLS). `workspace_id`를 코드가 명시해야 함 | 전 테넌트 행 |
| CI ↔ 저장소 | PR 트리거 정적 게이트. 공개 저장소 | 소스, 빌드 산출물 |
| worker ↔ Railway env | secret 5종 주입. api 서비스에는 없어야 정상 | service key, DB URL, 제공자 키 |

⚠️ **`service_role`은 BYPASSRLS다.** 사용자 요청 경로에 한 번만 새도 `0004`의 정책
20여 개가 전부 장식이 된다 — `checklists.json > decisions.db_access`.

---

## Threat Register

전체 62행의 근거별 증거는 `02-VERIFICATION.md`와 아래 감사 이력이 참조하는 파일에 있다.
여기에는 **미결 3건**과 종결 요약만 싣는다 — 종결 54건의 파일:행 증거를 이 문서에 복제하면
원본과 어긋나는 순간 두 곳을 고쳐야 한다.

### 미결 — 차단 (severity ≥ `high`)

| Threat ID | Category | Component | Severity | Disposition | Status |
|-----------|----------|-----------|----------|-------------|--------|
| T-02-47 | DoS | `QUEUE_BASELINE_ENABLED` | high | mitigate | **open** |

선언된 완화는 3절이다: (a) 기본값 `False`, (b) "측정 후 되돌린다", (c) "수용기준이 원상
복구를 확인한다". **(a)만 구현돼 있다** (`apps/worker/src/worker/settings.py:42`).

⚠️ Railway `worker` 서비스의 env 변수가 `false`로 되돌려졌음을 기록한 산출물이 **어디에도
없다.** `02-08-SUMMARY.md`는 "복구는 사람이 수행"이라고만 적고 관측을 남기지 않았고,
`docs/ops/reap-timeout-baseline.md`는 프로브가 **실제 배포된 Railway worker에서 클라우드
Supabase를 상대로** 돌았음을 확인해 준다. 즉 이 플래그는 운영 환경에서 참으로 설정됐고
현재 상태를 아무도 모른다.

**왜 잔소리가 아니라 차단인가:** 플래그가 여전히 참이면 worker가 재시작·재배포될 때마다
226회 `claim→complete` 왕복이 클라우드 `jobs`에 발생하고, **어느 롤도 지울 수 없는**
행이 매번 ~226건씩 쌓인다 (`0007` §8이 `jobs`에 DELETE를 아무에게도 주지 않는다).
T-02-48을 무한히 증폭시킨다.

**해소는 관측 한 번이다:** Railway `worker` 변수를 읽고, 있으면 `false`로 설정하고,
그 사실을 `docs/ops/reap-timeout-baseline.md`에 기록한다.

### 미결 — 비차단 (severity < `high`)

| Threat ID | Category | Component | Severity | Disposition | Status |
|-----------|----------|-----------|----------|-------------|--------|
| T-02-43 | DoS | 미등록 job type | medium | mitigate | open — below `high` (비차단) |
| T-02-48 | Tampering | 클라우드 프로브 잔여 | medium | mitigate | open — below `high` (비차단) |

**T-02-43** — 선언된 완화 "재시도 없이 곧바로 `dead`"의 절반만 구현됐다. `last_error`가
type 문자열을 싣고 핸들러는 한 번도 돌지 않지만, **무재시도 절은 미구현**이다.
`apps/worker/src/worker/queue.py:117-123`이 그 이유를 인라인으로 기록한다 — 현재 SQL
표면으로는 `dead`를 한 번에 강제할 원시연산이 없어 `fail_job(backoff=0)`으로
`max_attempts` 안에 수렴시킨다. `0008`의 `dead_letter_job()`이 Phase 3에서 닫는다.

**T-02-48** — 선언된 완화 "각 왕복이 자기 잡을 만들고 지운다"는 **문면 그대로 성립하지
않는다.** `0007` §8이 `jobs`에 DELETE를 어느 롤에도 주지 않으므로 프로브가 자기 잡을
지울 수 없다. 대체 통제(처분 가능한 워크스페이스에 가두기)는 실재하나 정리가 미확인이다 —
219여 건이 그 워크스페이스 삭제 cascade를 기다리고 있다.

### 종결 (59)

- **mitigate 검증됨 54건** — 감사자가 파일:행 증거로 확인. 대표 항목:
  `T-02-07`(`ApiSettings`가 필드를 0개 추가) · `T-02-12`(`service_client` 인자 필수) ·
  `T-02-19`(교차 테넌트 `PATCH`/`DELETE` 403) · `T-02-22`(fail-first가 실제로 red) ·
  `T-02-32`/`T-02-33`(새 함수 EXECUTE 회수 + `security invoker`) ·
  `T-02-52`/`T-02-55`(CI 게이트가 실제 GH 실행에서 red — run `31148250775`, `31148248589`)
- **accept 5건** — 아래 로그에 기록됨으로써 종결

---

## Accepted Risks Log

⚠️ 이 5건은 **이 표에 기록됨으로써만 종결된다.** 표를 지우면 다시 미결이 된다.

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | T-02-06 (DoS, low) | 50,000행 스파이크 코퍼스는 로컬 전용이며 `db reset`이 지운다. 클라우드에 적재되지 않는다 — `checklists.json > open_questions` | 소유자 | 2026-08-07 |
| AR-02-02 | T-02-10 (Spoofing, medium) | publishable key는 설계상 클라이언트에 공개된다(`BaseAppSettings:53`). 방어선은 키 비밀성이 아니라 RLS다 | 소유자 | 2026-08-07 |
| AR-02-03 | T-02-18 (EoP, medium) | ruff banned-api와 grep은 동적 import를 막지 못한다(`pyproject.toml:39-42`, `docs/ops/ci-security-gate.md` §4). 실질 방어선은 `ApiSettings`에 필드가 부재하다는 사실이다 | 소유자 | 2026-08-07 |
| AR-02-04 | T-02-38 (Info Disclosure, low) | `verified_by`는 `0007` §5에서 워크스페이스 멤버만 RLS를 통해 도달할 수 있다 | 소유자 | 2026-08-07 |
| AR-02-05 | T-02-59 (EoP, medium) | api와 worker가 단일 이미지를 공유하므로 정적 게이트로는 런타임 오용을 막을 수 없다. `ci.yml:19-21`이 이 한계를 명시하고 `ci-security-gate.md` §4가 재진술한다 | 소유자 | 2026-08-07 |

---

## 등록되지 않은 표면 (plan-time threat ID 없음)

감사자가 식별했으나 어떤 PLAN의 위협 등록부에도 없던 항목들이다. Phase 3 이후가 다룬다.

| Flag | Location | 평가 |
|---|---|---|
| `rls-bypass-surface` | `0007:349` | ⚠️ **Phase 3에서 살아난다.** 앞으로 만드는 모든 테이블이 `pg_default_acl`에서 `Dxtm`(RLS를 우회하는 `TRUNCATE` 포함)를 다시 상속한다. 강제 수단은 `⚠️` 주석뿐 — 테스트도, CI 검사도, event trigger도 없다. Phase 2에서는 `0007` 이후 테이블이 없어 위험 0이지만, Phase 3이 테이블을 추가하며 revoke/grant 쌍을 건너뛰는 첫 순간 악용 가능해진다. **권고:** `has_table_privilege(role, tbl, 'TRUNCATE') = false`를 3개 롤 × `public` 전 테이블에 대해 단언하는 SQL 테스트를 Phase 3에서 위협으로 등록할 것 |
| `null-dedup` | `0007` | `jobs_dedup_idx`가 `payload->>'target_id'`에 대한 부분 인덱스다. 그 키가 없는 job kind는 **조용히** 중복 제거를 받지 못한다. Phase 3 인큐 경로가 이 계약을 지켜야 한다 |
| `defense-depth-observed` | `0004` | `workspaces_select_member`와 `workspaces_update_owner`가 각각 독립으로 교차 테넌트 쓰기를 막는다. 좋은 일이지만, 정책 하나가 넓어져도 **증상이 없다**는 뜻이다. 회귀 은폐를 다루는 위협 ID가 없다 |
| `privilege-gap` | `0004` | **해소됨.** `0004` 헤더의 전제("이미 전체 GRANT를 보유")가 현행 Supabase CLI 기본값에서 거짓이어서 정책 20여 개가 무력했다. `0007` §8이 닫았고 anon 0 / authenticated 23 / service_role 25로 로컬·원격 검증 |
| `non-permanent-grant` | `supabase/spike/0002_search_fn_rpc.sql` | **해소됨.** 로컬 전용 `grant select … to authenticated`이며 `db reset`이 지운다. 코퍼스는 클라우드에 올라간 적 없다 |

---

## 좁혀진 불변식 하나 (T-02-08은 종결이지만)

`packages/core/tests/test_logging_redaction.py:36-44`는 `WorkerSettings.model_fields`가
아니라 **하드코딩된 4원소 리터럴**에 고정돼 있다. 기존 secret의 *이름 변경*은 잡지만
(`:43`이 실패한다) **`REDACTED_KEYS`에 없는 이름의 5번째 secret 필드 추가는 잡지 못한다.**
파일 자신의 `⚠️`(`:32-33`)가 이를 명시한다. ASVS L1에서는 존재하므로 CLOSED이나,
Phase 3이 제공자 자격증명을 추가하기 전에 한 줄로 고치는 편이 낫다 —
`set(WorkerSettings.model_fields) - set(BaseAppSettings.model_fields)`에서 유도해
그 차집합이 casefold되어 `REDACTED_KEYS`에 들어가는지 단언할 것.

---

## Security Audit 2026-08-07

| Metric | Count |
|--------|-------|
| Threats found | 62 |
| Closed | 59 |
| Open (blocking, ≥ high) | 1 |
| Open (non-blocking) | 2 |

**감사 방식:** `gsd-security-auditor`, ASVS L1, `block_on: high`,
`register_authored_at_plan_time: true`(9개 PLAN 전부 `<threat_model>` 보유)이므로
신규 위협 스캔이 아니라 **선언된 완화의 실재 검증**으로 수행.

**공개 저장소 노출 평가 — 물질적 노출 없음.** tracked 파일 전체에 대한
`sb_secret_*` · `sk-or-v1-*` · `sk-proj-*` · JWT 형태 grep 결과는 `.env.sample`의
플레이스홀더와 `-test` 리터럴뿐이다. `.env`는 tracked가 아니다.
`apps/api/tests/conftest.py:35-44`의 JWT는 Supabase CLI가 전 세계 모든 로컬 설치에
동일하게 배포하는 데모 키이며 `_assert_loopback()`이 그 외 대상을 가리키는 것을 막는다.

**인적 검증 한계 재확인 (`02-UAT.md`):** 교차 테넌트 **쓰기** 차단은 여전히 로컬 스택 ·
`workspaces` 한 테이블에서만 관측됐다. UAT 2건은 소유자가 `pass`로 판정했으나 양쪽 모두
`scope: partial`이며, 2번은 기록자가 `blocked`를 제안하고 소유자가 `pass`로 판정한
불일치가 그대로 보존돼 있다. 전수 폐쇄는 Phase 7 `OPS-04`.
