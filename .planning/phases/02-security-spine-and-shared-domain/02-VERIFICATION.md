---
phase: 02-security-spine-and-shared-domain
verified: 2026-08-07T06:02:29Z
status: human_needed
score: 5/5 roadmap success criteria verified (갭 2건 해소 후; 아래 resolution 참조)
resolution:
  resolved_at: 2026-08-07
  note: "검증 보고 이후 갭 2건이 모두 닫혔다. 검증자의 원 판정은 아래 gaps 블록에 그대로 보존한다."
  gap_1: "REQUIREMENTS.md의 SEC-03·SEC-05를 `[x]`/`Complete`로 갱신. 근거는 검증자가 인용한 실제 GH Actions 실행 2건(31148248589 / 31148250775). 순수 원장 정합성 수정."
  gap_2: "소유자가 human_verification 1번에서 (b) '이월'을 선택했다. ROADMAP 성공기준 5의 문언을 '잠정 타임아웃이 실측에서 유도되고 그 한계가 함께 문서화된다'로 개정하고, 개정 사유를 인라인 주석으로 남겼다. 실제 설정은 핸들러 지속시간을 아는 Phase 3으로 이월한다."
  remaining: "human_verification 2·3번은 미해소 — 02-UAT.md로 넘겼다. 이 페이즈의 격리 증명은 로컬 스택·workspaces 한 테이블에 한정된다."
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "SEC-03과 SEC-05가 REQUIREMENTS.md에서 여전히 미완료로 표시된다"
    status: failed
    reason: "02-09가 두 요구를 구현했고 검증자가 실제 GitHub Actions 실행으로 동작을 확인했으나(run 31148248589 / 31148250775), REQUIREMENTS.md의 체크박스는 `[ ]`, 추적 표는 `Pending`으로 남아 있다. 15개 ID 중 2개가 원장에서 잘못 계상된 상태다. 구현 결함이 아니라 원장 정합성 결함이다."
    artifacts:
      - path: ".planning/REQUIREMENTS.md"
        issue: "32행 SEC-03 · 34행 SEC-05가 `[ ]`이고, 193·195행 추적 표가 `Pending`이다"
    missing:
      - "SEC-03 · SEC-05 체크박스를 `[x]`로, 추적 표 상태를 `Complete`로 갱신 (근거: docs/ops/ci-security-gate.md의 위반 브랜치 2종 red 관측)"
  - truth: "reap_stale_jobs 타임아웃이 추측이 아니라 실측 p99로 설정된다 (ROADMAP 성공기준 5의 마지막 절)"
    status: partial
    reason: "측정 자체는 엄격하게 수행됐다 — 표본 N=219(문턱 200 초과), p99 127.054 ms, 콜드/워밍업 분리, 잠정 2초 유도. 그러나 `reap_stale_jobs`의 타임아웃은 **설정되지 않았다**. 0003의 기본값 15분이 그대로이고 코드 어디에도 타임아웃을 넘기는 경로가 없다. 문서는 2초를 '하한이지 최종 타임아웃이 아니다'라고 명시하며 그 이유(noop 핸들러는 아무 일도 하지 않아 핸들러 지속시간 항이 0)를 설명한다. 판단으로서는 타당하나 성공기준의 문언('설정된다')은 문자 그대로 충족되지 않았다."
    artifacts:
      - path: "docs/ops/reap-timeout-baseline.md"
        issue: "잠정 2초를 하한으로만 기록하고 실제 적용은 Phase 3로 미룬다 (86행, 102-114행)"
      - path: "supabase/migrations/0003_jobs.sql"
        issue: "reap_stale_jobs 기본 타임아웃 15분이 미변경 — 실측에 근거하지 않은 값"
    missing:
      - "성공기준 5의 이 절을 Phase 3 LLM 실측까지 이월할 것인지, 아니면 현재 하한으로 잠정 설정할 것인지에 대한 명시적 결정 (아래 human_verification 1번)"
deferred:
  - truth: "reap_stale_jobs 최종 타임아웃을 실제 핸들러 지속시간 p99로 확정"
    addressed_in: "Phase 3"
    evidence: "docs/ops/reap-timeout-baseline.md 114행 '그 값은 첫 LLM 잡이 도는 Phase 3에서 재측정해 확정한다' · 02-CONTEXT.md > D-17 · ROADMAP Phase 3 성공기준 5(잡 진행·재시도·last_error)가 큐 운영 표면을 다룬다"
  - truth: "0007 섹션 1 search_chunks의 벡터 차원을 임베딩 모델에 맞춘다"
    addressed_in: "Phase 3 (0008 보정 마이그레이션)"
    evidence: "checklists.json > decisions.embedding_model.implication — 'p_query extensions.vector(1536)이 박혀 있음', bge-m3 1024차로 교체 필요. 임베딩 데이터 0건이라 창이 열려 있으며 Phase 3가 첫 임베딩을 만드는 순간 닫힌다"
  - truth: "미등록 job type을 한 번의 왕복으로 dead로 보낸다"
    addressed_in: "Phase 3 (0008 dead_letter_job())"
    evidence: "apps/worker/src/worker/queue.py:117-123에 한계가 인라인 기록됨 — 현재는 fail_job(backoff='0 seconds')로 max_attempts 안에 수렴. 02-07-SUMMARY에 0008 dead_letter_job() 제안 기록"
  - truth: "전 테이블·클라우드에 대한 격리 왕복 전수 스위트"
    addressed_in: "Phase 7 (OPS-04)"
    evidence: "REQUIREMENTS.md 279행 'SEC-06은 Phase 2의 단일 격리 테스트이고, OPS-04는 모든 애플리케이션 경로가 존재한 뒤 도는 Phase 7의 전수 스위트다'"
human_verification:
  - test: "ROADMAP 성공기준 5의 'reap_stale_jobs 타임아웃이 실측 p99로 설정된다'를 현 상태로 충족으로 볼지 결정한다. docs/ops/reap-timeout-baseline.md 84-114행을 읽고, (a) 15분 기본값 유지 + 하한 문서화로 이 절을 닫을지 (b) Phase 3까지 명시적으로 이월할지 (c) 지금 잠정값을 적용할지 고른다."
    expected: "셋 중 하나가 선택되고 그 근거가 checklists.json 또는 ROADMAP에 기록된다. 문서는 (c)를 반대하는 논거를 이미 갖고 있다 — noop 기준 2초를 큐에 적용하면 Phase 3 컴파일 잡이 LLM 응답을 기다리는 동안 reap된다."
    why_human: "성공기준 문언과 엔지니어링 판단이 충돌한다. 어느 쪽이 계약인지는 코드가 아니라 소유자가 정한다."
  - test: "클라우드(ap-southeast-1)에서 교차 테넌트 쓰기가 403으로 막히는지 실제 왕복으로 확인한다. 로컬에서 통과한 apps/api/tests/test_workspaces_isolation.py와 동등한 시나리오를 클라우드 프로젝트에 대해 1회 수행한다."
    expected: "로컬과 동일하게 교차 테넌트 PATCH/DELETE가 403을 받는다."
    why_human: "검증자는 로컬 스택에서만 격리 왕복을 재현했다. 마이그레이션 목록은 로컬/원격이 일치하지만(0001~0007), 정책의 **런타임 거동**은 원격에서 관측되지 않았다. conftest.py는 루프백 가드가 있어 원격을 가리킬 수 없으므로 자동 실행이 불가능하다."
  - test: "workspaces 이외 8개 테이블(raw_sources · wiki_pages · source_chunks · wiki_embeddings · wiki_links · workspace_members · prompt_templates · jobs)의 RLS 정책이 교차 테넌트 접근을 실제로 막는지 표본 확인한다."
    expected: "각 테이블에서 타 워크스페이스 행에 대한 읽기/쓰기가 차단된다."
    why_human: "격리 왕복 증명(fail-first 포함)은 `workspaces` 한 테이블만 덮는다. 나머지 8개는 정책 정의와 권한 매트릭스로만 확인됐고 라우터가 없어 애플리케이션 경로 왕복이 존재하지 않는다. Phase 7 OPS-04의 전수 스위트가 본래 담당이나, 그 전까지는 미관측 상태임을 소유자가 알아야 한다."
---

# Phase 2: Security Spine and Shared Domain 검증 보고서

**Phase Goal:** 테넌트 격리가 코드 규약이 아니라 **역량 부재**로 강제되고, 라우터를 쓰기 전에 DB 트랜스포트와 공용 토크나이저가 확정된다
**Verified:** 2026-08-07T06:02:29Z
**Status:** gaps_found (실질 목표는 달성 — 결함 2건은 원장 정합성과 성공기준 문언 해석)
**Re-verification:** No — initial verification

## 요약

**보안 척추는 실제로 동작한다.** 이 판정은 SUMMARY의 서술이 아니라 검증자가 직접 재현한 관측에 근거한다. 특히 이 페이즈에서 가장 비싼 실패(공허하게 통과하는 격리 테스트)를 배제하기 위해 **fail-first 증명을 독립적으로 재현**했다 — 0004 정책을 느슨하게 만든 상태에서 격리 테스트가 정확히 5건 실패/8건 통과했고(문서 기록과 일치), 복원 후 정책 문자열이 바이트 단위로 동일했으며 13건이 다시 통과했다.

발견된 결함 2건은 어느 것도 목표 달성을 막지 않는다. 하나는 REQUIREMENTS.md 체크박스 2개가 구현보다 뒤처진 것이고, 다른 하나는 성공기준 5의 마지막 절이 문언대로는 충족되지 않은 것(의도적·문서화된 결정)이다.

## Goal Achievement

### Observable Truths (ROADMAP 성공기준 = 계약)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | worker 밖 코드가 service key에 닿을 수 없다 — `ApiSettings` 필드 부재 · ruff banned-api와 CI가 빌드 실패 · 번들 grep 무검출 | ✓ VERIFIED | `ApiSettings.model_fields` 런타임 조회 = `['ENVIRONMENT','LOG_LEVEL','SUPABASE_PUBLISHABLE_KEY','SUPABASE_URL']`, secret 4종 0개. 위반 픽스처를 `apps/api/`에 복사해 `ruff check` 실행 → **TID251 exit 1** 실제 발화. GitHub Actions run **31148248589**(`ci-violation/service-import`)에서 `service key 격리 (SEC-03)` 잡 red, run **31148250775**(`ci-violation/bundle-secret`)에서 `번들 secret 유출 (SEC-05)` 잡만 red·나머지 3잡 green(선택적 red 확인). 두 스크립트 직접 실행 exit 0 |
| 2 | 교차 테넌트 수정·삭제가 조용한 0행이 아니라 403이며, 매핑이 `UserDb` 한 곳에 있다 | ✓ VERIFIED | `_exactly_one`이 `len(rows) != 1`에서 `WorkspaceForbidden` — 0행과 2행 이상을 모두 포착(`user.py:113`). 읽기 경로 `select()`에는 미적용. 렌더는 `errors.py`의 단일 `_render_isolation_failure` 하나, `create_app`에서 1회 등록(`main.py:47`). 라우터에 Forbidden 상태 리터럴 0건. **fail-first 독립 재현**: 느슨한 정책에서 5 failed/8 passed → 복원 후 정책 diff 무차이, 13 passed |
| 3 | GUC 스파이크로 트랜스포트가 결정·기록되고, `0007`이 6개 요소를 추가한다 | ✓ VERIFIED | 스파이크 문서에 rpc/asyncpg × 3회 × 5개 실측 열이 개별 기록. 판정 절이 조건 2를 **거짓으로 정직하게 기록**하고 결론과의 차이를 명시. `0007`은 `begin;`(34행)~`commit;`(392행) 단일 트랜잭션, 8개 섹션. 로컬 DB에서 `search_chunks`·`complete_job_and_chain`·`release_job`·`jobs_dedup_idx`·`verified_by/at`·`expires_at`·`embedding_version`·`chunker_version` 전부 실존 확인. `migration list --linked` = 0001~0007 로컬/원격 완전 일치 |
| 4 | NFC·NFD·전각 입력이 단일 토크나이저로 서로를 검색해내고, 버전이 정규화 형식까지 인코딩한다 | ✓ VERIFIED | 세 형식 → 동일 bigram 문자열(`한국 국어 위키 se ea ar rc ch`). **실제 Postgres로 독립 확인**: `to_tsvector('simple',…) @@ phraseto_tsquery('simple',…)`가 nfd→nfc `t`, 전각→nfc `t`, 부분문자열 `t`. `TSV_TOKENIZER_VERSION='bigram-nfkc-cf-v1'`(알고리즘·형식·casefold·버전). DB 컬럼 2개 모두 `text` |
| 5 | 워커가 noop을 claim→complete 통과, SIGTERM에 잡 무손실, 같은 title→같은 슬러그, reap 타임아웃이 실측 p99로 **설정**된다 | ⚠️ PARTIAL | 앞 3절 충족: worker 59건 전원 통과(skip 0 — 실 DB 왕복 테스트 포함), release/grace/late-completion 등 불변식 7건 통과, `0007_queue_functions.sql` 실행 `queue_functions: ok`(트랜잭션 롤백). 슬러그 1,000회 동일·한글 보존·충돌 2/3 증가·퇴화 입력 결정적 폴백. **마지막 절 미충족**: p99 127.054 ms(N=219)를 측정하고 잠정 2초를 유도했으나 `reap_stale_jobs`는 15분 기본값 유지, 코드에 타임아웃 전달 경로 없음 |

**Score:** 4/5 성공기준 완전 검증 (1건 부분 충족, 0건 실패)

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | reap 최종 타임아웃을 핸들러 지속시간 p99로 확정 | Phase 3 | reap-timeout-baseline.md:114 · D-17 |
| 2 | `search_chunks`의 벡터 차원 1536→1024 (0008) | Phase 3 | decisions.embedding_model.implication |
| 3 | 미등록 job type의 1회 왕복 dead 처리 (0008 `dead_letter_job()`) | Phase 3 | queue.py:117-123 인라인 기록 |
| 4 | 전 테이블·전 경로 격리 전수 스위트 | Phase 7 (OPS-04) | REQUIREMENTS.md:279 |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/core/src/nexuswiki_core/settings.py` | BaseAppSettings, secret 부재 | ✓ VERIFIED | secret 0개, 빈 문자열 거부 validator, `MissingSettingError`가 키 이름 보고 |
| `apps/api/src/api/settings.py` | 필드 추가 없음 | ✓ VERIFIED | 런타임 `model_fields` 4개, banned 4종 0개 |
| `apps/worker/src/worker/settings.py` | secret 4종 보유 | ✓ VERIFIED | 4종 전부 존재, casefold가 `REDACTED_KEYS`와 일치(True) |
| `apps/worker/src/worker/db/service.py` | 인자 필수 팩토리 | ✓ VERIFIED | `service_client(settings: WorkerSettings, *, timeout_seconds=10.0)`, `ApiSettings` 전달 시 TypeError, 테이블 헬퍼 전부 keyword-only `workspace_id` 무기본값 |
| `apps/api/src/api/db/user.py` | 0행→403, 읽기 제외 | ✓ VERIFIED | `_exactly_one` !=1 판정, `select()` 미적용, `_require_filters`가 무조건 쓰기 차단 |
| `apps/api/src/api/errors.py` | 단일 403 핸들러 | ✓ VERIFIED | 렌더 함수 1개, 42501만 403·그 외 500, 고정 본문(열거 방지) |
| `apps/api/src/api/routers/workspaces.py` | 상태 코드 리터럴 없음 | ✓ VERIFIED | 403/FORBIDDEN/status.HTTP 매치 0건 |
| `supabase/migrations/0007_*.sql` | 6섹션 단일 트랜잭션 | ✓ VERIFIED | 8섹션(7·8은 기록된 이탈), begin/commit 감쌈, 로컬+원격 적용 |
| `supabase/tests/0007_queue_functions.sql` | release_job 계약 | ✓ VERIFIED | 실행 시 `queue_functions: ok`, ROLLBACK로 상태 무변경 |
| `supabase/tests/0004_loosened_rls_violation.sql` | fail-first 픽스처 | ✓ VERIFIED | 적용·복원 양방향 실제 실행, 복원 후 `pg_policies` 무차이 |
| `packages/core/src/nexuswiki_core/tokenizer.py` | normalize/bigram/버전 | ✓ VERIFIED | 3형식 수렴, 미정규화 입력 ValueError, 퇴화 입력 계약 고정 |
| `packages/core/src/nexuswiki_core/slug.py` | 결정적 슬러그 | ✓ VERIFIED | 1,000회 동일, 한글 보존, 2-source 충돌 해소 |
| `apps/worker/src/worker/queue.py` | claim→complete·SIGTERM | ✓ VERIFIED | 상태기계 헤더, `release_job` 반납, 핸들러에 workspace_id 전달 |
| `.github/workflows/ci.yml` | 4잡 PR 게이트 | ✓ VERIFIED | 4잡 독립(의존 없음), 실패 삼킴 구문 0건, secret 미참조 |
| `scripts/ci_check_service_usage.sh` | 0건→fail | ✓ VERIFIED | 대상 0개 시 exit 2, grep exit≥2 구분, 실행 시 46파일 ok |
| `scripts/ci_check_bundle_secrets.sh` | 산출물 부재→fail | ✓ VERIFIED | 디렉터리 부재 exit 1, 파일 0개 exit 1, 매치값 미출력, 실행 시 71파일 ok |
| `docs/ops/db-transport-spike.md` | 5열 실측 × 판정 | ✓ VERIFIED | 6행 × 5열 × 2계획, 조건별 참/거짓 표 |
| `docs/ops/reap-timeout-baseline.md` | 5요소 | ✓ VERIFIED | 값·유도·noop 한계·Phase 3 재측정·하트비트 미추가 근거 3개 모두 존재 |
| `docs/ops/tenant-isolation-proof.md` | red 관측 기록 | ✓ VERIFIED | 5단계 표(0/1/0 exit), 실패 5건 케이스명 기록 |
| `docs/ops/ci-security-gate.md` | 위반 2종 관측 | ✓ VERIFIED | 실제 GH run과 대조 일치 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `BaseAppSettings` | `ApiSettings`/`WorkerSettings` | 상속 경계 | ✓ WIRED | secret이 Base에 없어 Api가 상속받을 수 없음 — SEC-01 집행점 |
| `WorkerSettings` 필드명 | `REDACTED_KEYS` | casefold 일치 | ✓ WIRED | 런타임 부분집합 검사 True |
| `create_app(settings)` | `register_error_handlers` | `main.py:47` | ✓ WIRED | 단일 호출 지점 |
| `workspaces` 라우터 | `UserDb.update_one/delete_one` | `workspaces.py:22,61` | ✓ WIRED | 라우터가 상태 코드 미판정 |
| `WorkspaceForbidden` | 403 응답 | 단일 핸들러 | ✓ WIRED | fail-first에서 `assert 200 == 403` 형태로 역증명 |
| `service_client` | `WorkerSettings` 타입 | 시그니처 | ✓ WIRED | ApiSettings 거부 확인 |
| ruff banned-api 문자열 | `worker.db.service` 실경로 | TID251 | ✓ WIRED | 실제 발화 exit 1 |
| `0007` 섹션 7 | `TSV_TOKENIZER_VERSION` 문자열 | text 컬럼 | ✓ WIRED | DB에서 두 컬럼 `text` 확인 |
| `release_job()` | SIGTERM 반납 경로 | `queue.py:213` | ✓ WIRED | grace 초과 시 호출, attempts 미소모 |
| 로컬 migration list | 원격 migration list | `--linked` | ✓ WIRED | 0001~0007 완전 일치 |
| `ci_check_bundle_secrets.sh` | `apps/dashboard/.next` | 빌드 후 실행 | ✓ WIRED | CI에서 build 스텝 직후 배치 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `UserDb` | `rows` | PostgREST 실 HTTP 왕복(요청자 JWT) | 예 — 실 스택에서 행 반환·차단 관측 | ✓ FLOWING |
| `queue.py` | `job` | `claim_job` RPC | 예 — 실 DB 왕복 테스트 통과 | ✓ FLOWING |
| `tokenizer.py` | bigram 문자열 | 순수 함수 | 예 — 실 Postgres tsvector 매치 확인 | ✓ FLOWING |
| `queue_baseline.py` | 지연 표본 | Railway→Supabase 실측 | 예 — N=219 실표본 | ✓ FLOWING |
| `search_chunks` RPC | 검색 결과 | HNSW + RLS | 미관측 — 호출 경로가 Phase 4 | ⚠️ 미소비 (설계상 정상) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| ApiSettings에 secret 부재 | `python -c "ApiSettings.model_fields"` | banned 4종 0개 | ✓ PASS |
| ruff banned-api 발화 | 위반 픽스처 복사 후 `ruff check` | TID251, exit 1 | ✓ PASS |
| service_client가 ApiSettings 거부 | `service_client(ApiSettings())` | TypeError | ✓ PASS |
| fail-first 격리 red | 느슨 정책 + `pytest test_workspaces_isolation.py` | 5 failed, 8 passed | ✓ PASS |
| 정책 복원 무손실 | `pg_policies` diff | 무차이, 13 passed | ✓ PASS |
| 3형식 실 DB 왕복 자가검색 | `to_tsvector @@ phraseto_tsquery` | t / t / t | ✓ PASS |
| 슬러그 1,000회 결정성 | `{slugify(...) for _ in range(1000)}` | 1개 값, 한글 보존 | ✓ PASS |
| release_job SQL 계약 | `psql < 0007_queue_functions.sql` | `queue_functions: ok`, ROLLBACK | ✓ PASS |
| SIGTERM 불변식 | `pytest -k "release or grace or late_completion"` | 7 passed | ✓ PASS |
| CI 실패 삼킴 부재 | `grep -nE 'continue-on-error\|\|\| true\|set \+e'` | 매치 0건 | ✓ PASS |
| 두 CI 스크립트 | 직접 실행 | 46 / 71 파일 스캔, exit 0 | ✓ PASS |
| 0007 객체 실존 | `information_schema` + `pg_proc` + `pg_indexes` | 전 객체 확인 | ✓ PASS |
| 로컬/원격 마이그레이션 일치 | `supabase migration list --linked` | 0001~0007 일치 | ✓ PASS |
| 전체 스위트 | `pytest -rs` | 143 passed, skip 0 | ✓ PASS |
| 린트 | `ruff check apps packages` | All checks passed | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| `supabase/tests/0007_queue_functions.sql` | `psql -v ON_ERROR_STOP=1 <` | `queue_functions: ok` | PASS |
| `scripts/ci_check_service_usage.sh` | `bash` | exit 0, 46 files | PASS |
| `scripts/ci_check_bundle_secrets.sh` | `bash` | exit 0, 71 files | PASS |
| `supabase/tests/0004_loosened_rls_violation.sql` | 섹션 1 적용 → pytest → 섹션 2 복원 | 5 failed → 복원 → 13 passed | PASS |

> `scripts/spike_db_transport.py`는 재실행하지 않았다 — 50,000행 코퍼스가 `supabase db reset`으로 이미 제거됐고(open_questions에 기록), 재적재는 상태 변경이다. 문서의 실측 표를 증거로 채택한다.

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
|-------------|-------------|--------|----------|
| SEC-01 | 02-02 | ✓ SATISFIED | `model_fields` 런타임 검사 secret 0개 |
| SEC-02 | 02-03 | ✓ SATISFIED | user.py/service.py 분리, TID251 실발화 |
| SEC-03 | 02-09 | ✓ SATISFIED (원장 미갱신) | GH run 31148248589에서 SEC-03 잡 red — **REQUIREMENTS.md는 `[ ]` Pending** |
| SEC-04 | 02-03 | ✓ SATISFIED | `_exactly_one` 단일 지점, 0행·2행+ 모두 |
| SEC-05 | 02-09 | ✓ SATISFIED (원장 미갱신) | GH run 31148250775에서 SEC-05 잡만 red — **REQUIREMENTS.md는 `[ ]` Pending** |
| SEC-06 | 02-04 | ✓ SATISFIED | fail-first 독립 재현 (workspaces 한정) |
| DOM-01 | 02-01 | ✓ SATISFIED | 스파이크 실측 + decisions.db_transport 잠금 |
| DOM-02 | 02-06 | ✓ SATISFIED | 검색 함수·jobs_dedup_idx·complete_job_and_chain DB 실존 |
| DOM-03 | 02-06 | ✓ SATISFIED | wiki_pages.verified_by/verified_at/expires_at 실존 |
| DOM-04 | 02-06 | ✓ SATISFIED | source_chunks·wiki_embeddings 버전 컬럼 실존 |
| DOM-05 | 02-05 | ✓ SATISFIED | 단일 모듈, 미정규화 거부, 버전이 형식 인코딩 |
| DOM-06 | 02-05 | ✓ SATISFIED | 실 Postgres 왕복으로 독립 확인 |
| DOM-07 | 02-05 | ✓ SATISFIED | 1,000회 결정성 + 2-source 병합 충돌 해소 |
| DOM-08 | 02-07 | ✓ SATISFIED | noop claim→complete, SIGTERM 반납, 데드레터 수렴 |
| DOM-09 | 02-08 | ⚠️ PARTIAL | 하트비트 확인·근거 기록 완료. 타임아웃 **설정**은 미수행(15분 유지) |

**Orphaned requirements:** 없음 — 15개 ID 전부가 플랜 frontmatter에 청구되어 있다.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | TBD/FIXME/XXX/TODO/HACK | — | **0건**. 유일한 `PLACEHOLDER` 매치는 `REDACTION_PLACEHOLDER` 상수명(정상 식별자) |

부채 마커 게이트: **통과**. `apps` · `packages` · `scripts` · `supabase` · `.github` 전체에서 미참조 부채 마커 0건.

### 주목할 관측 (결함 아님, 기록 목적)

1. **스파이크 판정 규칙의 문언 이탈이 정직하게 공개돼 있다.** 02-01-PLAN의 must_have는 "3조건 중 하나라도 거짓이면 asyncpg 채택"이었고, 기본 계획에서 조건 2(HNSW Index Scan)가 **양 경로 모두 거짓**이었다. 문서는 이를 은폐하지 않고 149-151행에 "규칙상 asyncpg가 되지만 그 탈락 사유가 asyncpg의 장점과 무관하다"고 명시한 뒤 RPC를 선택했다. 게이트 체크포인트에서 사람이 내린 결정으로 기록돼 있다. 이 프로젝트가 요구하는 검증 위생을 오히려 잘 보여주는 사례로, 결함으로 분류하지 않는다.

2. **DOM-06 테스트가 DB가 아닌 Python 시뮬레이션을 쓴다.** `packages/core/tests/test_tokenizer.py:30`의 `_phrase_matches`가 `phraseto_tsquery`의 `<->` 인접성을 문자열 수준에서 재현한다. docstring이 이를 명시하므로 은폐는 아니지만, 시뮬레이션이 Postgres 의미론과 어긋나면 테스트가 green인 채 실검색이 조용히 실패할 수 있다 — CLAUDE.md가 경고하는 바로 그 실패 형태다. 검증자가 **실제 Postgres로 직접 확인해 이 공백을 닫았고**(t/t/t), 세 형식이 바이트 동일 문자열로 수렴하므로 구조적으로도 안전하다. Phase 4의 EXPLAIN 회귀 테스트에서 실 DB 검증으로 승격할 것을 권한다.

3. **0007 섹션 8 권한 매트릭스를 건수가 아니라 동작 단위로 재검증했다.** 알려진 한계는 "건수로만 확인"이었으나 검증자가 `role_table_grants`를 동작 단위로 조회한 결과 매트릭스가 의미상 정합했다 — `anon` 0행(완전 거부), `authenticated`는 `raw_sources`에 UPDATE 없음(원문 불변성 유지), `service_role`은 `workspaces`·`workspace_members`에 SELECT만, `jobs`에 DELETE 없음. 건수도 23/25로 문서와 일치. **이 한계는 해소된 것으로 본다.**

### Gaps Summary

목표 자체는 달성됐다. 격리는 규약이 아니라 역량 부재로 강제되며(필드 부재 + 린트 + CI 3중), 트랜스포트와 토크나이저는 라우터 이전에 확정됐고 `0007`이 로컬·클라우드 양쪽에 올라가 있다. 검증자가 fail-first를 직접 재현했으므로 격리 테스트가 공허하지 않다는 것도 확인됐다.

남은 결함 2건은 성격이 다르다.

**(1) 원장 정합성** — SEC-03과 SEC-05가 REQUIREMENTS.md에서 미완료로 표시돼 있다. 구현은 검증됐고 실제 CI 실행에서 red까지 관측됐으므로 순수한 기록 누락이다. 15개 ID 중 2개가 잘못 계상된 상태를 남기면 이후 페이즈의 추적이 이 지점부터 어긋난다. 체크박스와 추적 표 갱신으로 닫힌다.

**(2) 성공기준 5의 문언** — "`reap_stale_jobs` 타임아웃이 실측 p99로 **설정된다**"에서 측정은 엄격했으나 설정은 이뤄지지 않았다. 문서는 그 이유를 설득력 있게 설명한다: noop 핸들러는 아무 일도 하지 않으므로 측정값은 전송 비용의 하한일 뿐이고, 2초를 실제로 적용하면 Phase 3의 LLM 잡이 응답 대기 중 reap된다. 즉 성공기준을 문자대로 이행하는 것이 오히려 해로운 경우다. 그러나 그 판단이 성공기준을 자동으로 재정의하지는 않으므로 소유자 결정이 필요하다.

---

_Verified: 2026-08-07T06:02:29Z_
_Verifier: Claude (gsd-verifier)_
