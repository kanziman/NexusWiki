# Phase 1: Bootstrap and Ground Truth — Specification

**Created:** 2026-08-02
**Ambiguity score:** 0.09 (gate: ≤ 0.20)
**Requirements:** 10 locked

## Goal

되돌릴 수 없거나 매주 비싸지는 결정(리전 · 키 체계 · `0005` 순서 · monorepo 형태 · 배포 토폴로지)이 전부 확정되고, `api`(web)와 `worker`(resident) 두 서비스가 **동일 이미지**로 Railway `asia-southeast1`에서 기동하며, `0001`~`0006`이 Supabase Cloud `ap-southeast-1`에 순서대로 적용된다.

## Background

**코드로 존재하는 것:**
- `supabase/migrations/` — `0001_core_schema.sql` · `0002_search_schema.sql` · `0003_jobs.sql` · `0004_rls_policies.sql` · `0006_seed_prompts.sql` (총 1,288줄). 로컬 적용·검증 완료(RLS 38/38, 8워커 400잡 동시성, 5채널 EXPLAIN 인덱스 사용)
- `supabase/config.toml` — Postgres 17, 포트 544xx(`zettlink`와 충돌 회피)
- `docs/` — 아키텍처 설명 HTML, `design-tokens.css` / `design-tokens.json`
- `.env.sample` · `.env.local`(gitignore 대상)

**존재하지 않는 것 (= 이 페이즈의 델타):**
- `supabase/migrations/0005_storage.sql` — 번호 시퀀스에 **구멍**. 클라우드 첫 `db push` 이전에 반드시 들어가야 함
- `apps/` 디렉터리 자체가 없음. `pyproject.toml` · `uv.lock` · `package.json` · `Dockerfile` · `.pre-commit-config.yaml` · `.editorconfig` · 루트 `README.md` 전부 부재
- Railway 계정 없음

**스카우트로 확인한 현재 상태:**
- Supabase Cloud 프로젝트는 **이미 존재하며 리전은 `ap-southeast-1`** (인터뷰 Round 1 확인). `.env.local`에 `sb_publishable_` / `sb_secret_` 형식의 실제 키가 있음
- `supabase/.temp/`에 `project-ref`가 없음 → CLI `link` 이력 없음 → `db push` 이력도 없을 가능성이 높으나 **대시보드 SQL 에디터 경로를 배제할 수 없어 검증 대상**
- Supabase CLI 2.33.2 설치됨 (upstream 최신 2.111.0 — 78 마이너 버전 차)
- 호스트 툴체인: uv 0.11.32 · Node v25.9.0 · Python 3.11.5 · Docker Desktop
- `checklists.json` `P0-INIT-00`은 `in_progress`, 나머지 P0 4건은 `pending`

## Requirements

1. **Storage 마이그레이션 `0005`**: 비공개 `sources` 버킷과 실제 `storage.objects` 정책이 경로 규약을 강제한다.
   - Current: `0005`가 존재하지 않음. 경로 규약 `{workspace_id}/{raw_source_id}/{filename}`은 `0001_core_schema.sql:108`의 **주석으로만** 존재
   - Target: `supabase/migrations/0005_storage.sql`이 비공개 `sources` 버킷과 SELECT/INSERT/UPDATE/DELETE 정책을 만들고, 정책이 (a) 첫 세그먼트 `workspace_id`에 대한 멤버십과 (b) 경로가 정확히 3세그먼트임을 **둘 다** 검사한다
   - Acceptance: 멤버가 아닌 `workspace_id` 경로 업로드가 거부됨 · 멤버여도 2세그먼트 경로(`{workspace_id}/evil.pdf`) 업로드가 거부됨 · 정상 3세그먼트 업로드는 성공

2. **클라우드 프로젝트 검증 및 마이그레이션 적용**: `ap-southeast-1` 프로젝트에 `0001`~`0006`이 번호 순서대로 적용된다.
   - Current: 프로젝트는 존재하나 CLI link 이력 없음. 클라우드에 마이그레이션이 적용되었는지 미확인
   - Target: 리전이 `ap-southeast-1`임을 확인하고, `sb_publishable_` / `sb_secret_` 키 체계 사용을 확인하며, **`0005` 작성 전에** 클라우드 `supabase_migrations.schema_migrations`가 비어 있음을 먼저 확인한 뒤 `0001`~`0006`을 순서대로 push
   - Acceptance: `supabase projects list`(또는 대시보드)가 리전 `ap-southeast-1`을 보고 · push 직전 `schema_migrations`가 비어 있음이 기록됨 · push 후 `schema_migrations`에 `0001`,`0002`,`0003`,`0004`,`0005`,`0006`이 이 순서로 존재 · 비어 있지 않았다면 순서 복구 경로(해당 프로젝트 폐기 후 `ap-southeast-1` 재생성)가 실행되고 기록됨

3. **Supabase CLI 업그레이드**: CLI를 최신으로 올리고 로컬 스택이 그대로 동작함을 재검증한다.
   - Current: CLI 2.33.2, `config.toml`은 2.33.2 스키마 기준으로 작성됨
   - Target: 최신 버전(2.111.0 이상)으로 업그레이드. `config.toml` 스키마 변경이 필요하면 그 수정도 이 페이즈의 산출물
   - Acceptance: 업그레이드 후 `supabase start`가 성공하고 포트가 544xx로 유지됨 · `supabase db reset`이 `0001`~`0006` 전체를 에러 없이 재적용 · 필요했던 `config.toml` 변경이 커밋에 포함됨

4. **uv 워크스페이스 monorepo**: `packages/core` · `apps/api` · `apps/worker` 3멤버 워크스페이스가 클린 클론에서 재현 가능하게 설치된다.
   - Current: `apps/`도 `packages/`도 없음. `pyproject.toml`·`uv.lock` 없음
   - Target: 루트 `pyproject.toml`이 uv 워크스페이스를 선언하고 `packages/core`가 두 앱의 의존성으로 선언됨. `uv.lock`을 저장소에 커밋
   - Acceptance: 별도 디렉터리에 새로 clone한 뒤 `uv sync --frozen`이 성공 · `apps/api`와 `apps/worker` 양쪽에서 `packages/core` 모듈 import가 동작 · `uv.lock`이 git에 추적됨

5. **공통 툴링**: 포맷·린트를 어긴 커밋이 pre-commit에서 거부된다.
   - Current: `.pre-commit-config.yaml`·`.editorconfig`·루트 `README.md` 없음. `.gitignore`만 존재
   - Target: pre-commit이 ruff(대상 `apps/**`·`packages/**`)와 prettier(대상 `apps/dashboard/**`)를 실행. `docs/**`·`checklists.json`·`supabase/**`는 **대상에서 제외**해 기존 문서의 대규모 재포맷을 방지. `.editorconfig`와 루트 `README.md` 추가
   - Acceptance: 의도적으로 포맷을 어긴 Python/TS 파일 커밋이 거부됨 · `pre-commit run --all-files`가 통과하며 **기존 파일을 하나도 변경하지 않음**

6. **FastAPI 기동과 구조화 로깅**: `lifespan`으로 기동하고 헬스 엔드포인트 2종을 제공하며 로그가 컨텍스트를 실어 나른다.
   - Current: Python 애플리케이션 코드가 존재하지 않음
   - Target: `apps/api`가 `lifespan`으로 기동. `/health`는 프로세스 생존만으로 200. `/health/ready`는 DB 왕복을 포함하되 **명시적 타임아웃(2초)** 을 두고 초과 시 매달리지 않고 503 + 사유 반환. `packages/core`가 structlog 설정을 소유하고 `job_id`/`workspace_id`를 contextvar로 바인딩해 JSON 로그 한 줄에 포함시킨다
   - Acceptance: `/health`가 DB 없이도 200 · DB 도달 불가 상태에서 `/health/ready`가 3초 이내에 503 반환 · `job_id`/`workspace_id`를 바인딩한 로그 한 줄이 두 키를 모두 포함한 JSON으로 출력됨 · `apps/api`와 `apps/worker`가 **같은** `packages/core` 로깅 모듈을 사용

7. **Next.js 앱 스캐폴딩**: 15.5.22 이상 앱이 Tailwind 4 · TypeScript strict로 구성되고 테스트가 통과한다.
   - Current: `package.json`이 없음
   - Target: Next.js 15.5.22 이상(CVE-2025-29927 하한 15.2.3 위) · Tailwind 4 · TS strict · Vitest + Testing Library. 스모크 테스트 대상은 **`'use client'` 컴포넌트 1개 + 순수 함수 1개**로 한정(RSC 테스트 전략은 Phase 6)
   - Acceptance: `package.json`의 next 버전이 15.5.22 이상 · `tsc --noEmit` 통과 · `vitest run`이 2개 테스트를 통과 · 로컬 dev 서버 기동

8. **Railway 2서비스 배포**: 단일 Dockerfile로 `api`와 `worker`가 `asia-southeast1`에 배포되고 동일 빌드임이 증명된다.
   - Current: Railway 계정 없음. `Dockerfile`·`railway.json` 없음
   - Target: Railway 가입 + Hobby($5/mo) 구독 + 프로젝트 1개 · 서비스 2개. 단일 Dockerfile, Root Directory `/`, start command만 다름. 리전 `asia-southeast1`
   - Acceptance: 두 서비스가 모두 running · 배포된 `api`의 공개 URL `/health`가 200 · **동일 빌드 판정**: (1차) 두 서비스의 이미지 다이제스트 일치, 또는 (2차, 비결정적 빌드 시) 동일 커밋 SHA + 동일 Dockerfile 경로 + 두 서비스가 로그/응답에 동일한 `GIT_SHA`를 출력 — 둘 중 하나 충족 시 합격

9. **Railway↔Supabase RTT 실측 기록**: 왕복 지연이 숫자로 문서에 남고 5채널 환산이 함께 기록된다.
   - Current: 미측정. `checklists.json` open question #2가 열려 있음
   - Target: **배포된 Railway `api`에서** Supabase로 단순 쿼리를 워밍업 후 N≥50회 실행해 p50/p95를 구하고, 콜드 첫 요청 값도 별도로 기록. 5채널 환산(×5)을 함께 저장소 문서에 남긴다
   - Acceptance: 문서에 p50·p95·콜드 첫 요청·N값·측정 방법·×5 환산이 모두 존재 · 로컬이 아니라 배포된 api에서 측정했음이 명시 · `checklists.json` open question #2가 해소로 표시됨

10. **인증 하드닝**: 프로덕션 Auth 설정이 CLI 기본값을 벗어난다.
    - Current: Supabase 기본값(최소 6자, 이메일 확인 off)으로 추정
    - Target: 최소 비밀번호 길이 12자 · 이메일 확인 필수. 적용 시점에 `auth.users`가 비어 있음을 확인하고, 비어 있지 않으면 해당 계정을 삭제해 정책이 전수에 적용되게 한다
    - Acceptance: 6자 비밀번호 가입 시도가 거부됨 · 미확인 이메일로는 로그인 불가 · 정책 적용 시점의 `auth.users` 행 수 0이 기록됨(또는 잔존 계정 삭제가 기록됨)

## Boundaries

**In scope:**
- `supabase/migrations/0005_storage.sql` (버킷 + `storage.objects` 정책)
- Supabase Cloud 프로젝트 리전·키 체계 검증, `0001`~`0006` 클라우드 적용
- Supabase CLI 업그레이드 + `config.toml` 호환 수정
- uv 워크스페이스 monorepo (`packages/core` · `apps/api` · `apps/worker`) + 커밋된 `uv.lock`
- `packages/core`의 **공용 structlog 로깅 모듈**(이 페이즈에서 core가 담는 유일한 실질 내용)
- pre-commit(ruff + prettier) · `.editorconfig` · 루트 `README.md`
- FastAPI `lifespan` + `/health` + `/health/ready`
- Next.js 15.5.22+ 스캐폴딩 (Tailwind 4 · TS strict · Vitest 2 테스트)
- Railway 가입 · Hobby 구독 · 프로젝트 1개 + 서비스 2개 배포 (`asia-southeast1`)
- RTT 실측 문서
- Supabase Auth 하드닝 (12자 · 이메일 확인)

**Out of scope:**
- **JWT 인증 · 워크스페이스 컨텍스트 · `user_client`/`service_client` 분리 · `UserDb` 403 매핑** — 전부 Phase 2 (SEC-01~06). Phase 1의 `api`는 인증 없는 헬스 엔드포인트만 노출한다
- **`/health`·`/health/ready` 외의 모든 라우터** — 수집·검색·Ask는 Phase 3~5. 라우터를 지금 쓰면 DB 트랜스포트 미결(DOM-01) 위에 쌓게 된다
- **실제 잡 처리 로직 · `claim_job` 폴링 루프** — Phase 2 (DOM-08). Phase 1의 `worker`는 기동·로깅·graceful shutdown까지만
- **마이그레이션 `0007`** (검색 함수 · `jobs_dedup_idx` · `complete_job_and_chain()` · `verified_by`/`verified_at`/`expires_at` · `embedding_version`/`chunker_version`) — Phase 2 (DOM-02~04). Phase 1이 손대는 스키마는 `0005` 하나뿐
- **한국어 토크나이저(`normalize()`/`bigram()`)** — Phase 2 (DOM-05). `packages/core`에는 로깅만 들어간다
- **Next.js 배포(Vercel)** — Phase 6. Phase 1의 "클라우드 기동"은 `api`·`worker` 두 서비스만 의미한다
- **설정(Settings) 공통 조상 클래스** — SEC-01(`ApiSettings`에 service key 필드 부재)이 Phase 2라 지금 설계하면 두 번 바꾸게 된다
- **RSC 테스트 전략** — Phase 6. Phase 1 Vitest는 클라이언트 컴포넌트 + 순수 함수만

## Constraints

- **리전은 프로젝트 생성 후 변경 불가.** Supabase는 `ap-southeast-1`, Railway는 `asia-southeast1`로 확정 (Railway에 서울·도쿄 리전 없음)
- **`0005`는 클라우드 첫 `db push` 이전에 반드시 존재해야 한다.** `0006`보다 번호가 낮아 이후에 넣으면 로컬/클라우드 적용 순서가 어긋난다
- **Next.js 하한 15.2.3** — CVE-2025-29927은 `x-middleware-subrequest` 헤더 위조로 미들웨어를 우회하는데, 이 앱의 테넌트 게이트가 미들웨어다. 목표는 15.5.22 이상
- **2025-11 이후 생성 프로젝트에는 legacy 키가 발급되지 않는다** — `sb_publishable_` / `sb_secret_` 체계 전제
- **로컬 포트는 544xx 고정** — 같은 머신의 `zettlink` 스택이 543xx를 점유
- **로컬 `psql` 없음** — `docker exec -it supabase_db_NexusWiki psql -U postgres -d postgres` 사용
- **예산: Railway Hobby $5/mo** — 워크스페이스 단위 구독. `worker`는 resident라 Free 티어로는 상시 구동 불가
- **Gunicorn 금지** — Railway SIGTERM drain을 깨고 $5 인스턴스에서 유휴 메모리를 2배로 만든다 (REQUIREMENTS Out of Scope)

## Acceptance Criteria

- [ ] `0005_storage.sql`이 비공개 `sources` 버킷을 만들고, 비멤버 `workspace_id` 경로 업로드가 정책에 의해 거부된다
- [ ] 멤버여도 2세그먼트 경로(`{workspace_id}/x.pdf`) 업로드가 거부되고, 3세그먼트 정상 경로는 성공한다
- [ ] `0005` 작성 전 클라우드 `supabase_migrations.schema_migrations`가 비어 있음이 확인·기록되었다
- [ ] 클라우드 `schema_migrations`에 `0001`→`0006`이 번호 순서대로 존재한다
- [ ] Supabase Cloud 프로젝트 리전이 `ap-southeast-1`임이 확인·기록되었다
- [ ] Supabase CLI가 2.111.0 이상이고, 업그레이드 후 `supabase start` + `supabase db reset`이 성공한다(포트 544xx 유지)
- [ ] 별도 디렉터리에 새로 clone 후 `uv sync --frozen`이 성공하고, `uv.lock`이 git에 추적된다
- [ ] `apps/api`·`apps/worker` 양쪽에서 `packages/core` import가 동작한다
- [ ] `pre-commit run --all-files`가 통과하며 기존 파일을 하나도 변경하지 않는다
- [ ] 포맷을 어긴 Python 및 TS 파일의 커밋이 pre-commit에서 거부된다
- [ ] `/health`가 DB 없이도 200을 반환한다
- [ ] DB 도달 불가 상태에서 `/health/ready`가 3초 이내에 503과 사유를 반환한다(매달리지 않는다)
- [ ] `job_id`/`workspace_id`를 바인딩한 로그 한 줄이 두 키를 모두 포함한 JSON으로 출력된다
- [ ] `package.json`의 next 버전이 15.5.22 이상이다
- [ ] `tsc --noEmit`이 통과하고 `vitest run`이 클라이언트 컴포넌트 1개 + 순수 함수 1개 테스트를 통과한다
- [ ] Railway `asia-southeast1`에 `api`(web)와 `worker`(resident) 두 서비스가 running 상태다
- [ ] 배포된 `api`의 공개 URL `/health`가 200을 반환한다
- [ ] 동일 빌드가 증명된다 — 이미지 다이제스트 일치, 또는 (동일 커밋 SHA + 동일 Dockerfile 경로 + 두 서비스가 동일 `GIT_SHA` 출력)
- [ ] RTT 문서에 p50 · p95 · 콜드 첫 요청 · N값 · 측정 방법 · ×5 환산이 모두 존재하고, 배포된 api에서 측정했음이 명시된다
- [ ] `checklists.json` open question #2가 해소로 표시된다
- [ ] 6자 비밀번호 가입 시도가 거부된다
- [ ] 미확인 이메일로는 로그인할 수 없다
- [ ] 인증 하드닝 적용 시점의 `auth.users` 행 수 0이 기록되거나, 잔존 계정 삭제가 기록된다

**부정 수용기준 (Prohibitions에서 승격):**

- [ ] Railway `api` 서비스의 환경변수 목록에 `SUPABASE_SECRET_KEY`(또는 동등한 service key)가 **존재하지 않는다** — 공유 스코프가 아니라 `worker` 서비스 스코프에만 주입된다
- [ ] 구조화 로그가 이메일 · `Authorization` 헤더 · API 키 · 소스 원문을 평문으로 출력하지 않는다 (core의 redaction 프로세서가 지정 키를 마스킹함을 단위 테스트로 증명)
- [ ] 빌드·런타임이 사용자 동의 없이 외부 텔레메트리를 전송하지 않는다 (`NEXT_TELEMETRY_DISABLED=1`이 Dockerfile·환경에 고정)
- [ ] RTT 측정 문서가 project ref · `DATABASE_URL` · 어떤 키도 포함하지 않는다

## Edge Coverage

**Coverage:** 10/10 applicable edges resolved · 0 unresolved

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| unclassified (경로 형태) | R1 | ✅ covered | 정책이 멤버십 + **3세그먼트**를 둘 다 검사. 2세그먼트 업로드 거부가 수용기준 |
| unclassified (선행 상태) | R2 | ✅ covered | `0005` 작성 전 클라우드 `schema_migrations`가 비어 있음을 먼저 확인. 비어 있지 않으면 프로젝트 재생성이 조건부 요구사항 |
| unclassified (설정 호환) | R3 | ✅ covered | 업그레이드 후 필요한 `config.toml` 수정도 Phase 1 산출물. 합격은 `supabase start` + `db reset` 둘 다 성공 |
| concurrency (재현성) | R4 | ✅ covered | `uv.lock` 커밋 + 별도 디렉터리 clone 후 `uv sync --frozen` 성공이 합격 기준 (로컬 캐시 위양성 차단) |
| unclassified (도구 범위) | R5 | ✅ covered | prettier는 `apps/dashboard/**`, ruff는 `apps/**`·`packages/**`로 제한. `pre-commit run --all-files`가 기존 파일을 바꾸지 않아야 통과 |
| unclassified (행 매달림) | R6 | ✅ covered | `/health/ready`에 명시적 2초 타임아웃, 초과 시 503 + 사유. 합격은 "3초 이내 503" |
| unclassified (테스트 경계) | R7 | ✅ covered | 스모크 대상을 `'use client'` 컴포넌트 1개 + 순수 함수 1개로 한정. RSC 테스트는 Phase 6 |
| concurrency (비결정 빌드) | R8 | ✅ covered | 1차 다이제스트 일치, 실패 시 2차 (커밋 SHA + Dockerfile 경로 + 런타임 `GIT_SHA` 일치). 둘 중 하나 충족이면 합격 |
| concurrency (콜드스타트) | R9 | ✅ covered | 워밍업 후 N≥50회 p50/p95를 측정하되 콜드 첫 요청 값도 별도 기록 |
| unclassified (기존 상태) | R10 | ✅ covered | 하드닝 적용 시점 `auth.users` 행 수 0 확인, 잔존 시 삭제. 정책이 전수에 적용됨을 보장 |

## Prohibitions (must-NOT)

**Coverage:** 4/4 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| Railway `api` 서비스가 Supabase service key(`SUPABASE_SECRET_KEY`)에 접근할 수 있어서는 안 된다 — 단일 이미지 배포에서 환경변수를 공유 스코프에 넣는 순간 `api`가 BYPASSRLS를 얻고 38개 격리 정책이 장식이 된다 | R8 | resolved | verification: **test** — 배포 설정 검증(`api` 서비스 env 목록에 키 부재). 서술자 미포착(SOFT): 검증이 `node-test`/`lint-rule` 어느 쪽에도 매핑되지 않음 → verify 단계에서 fail-closed 플래그 |
| 구조화 로그가 사용자 이메일 · `Authorization` 헤더/JWT · API 키 · 소스 원문을 평문으로 출력해서는 안 된다 | R6 | resolved | verification: **test** — `packages/core`의 redaction 프로세서가 지정 키를 마스킹함을 단위 테스트로 증명. 서술자 미포착(SOFT): pytest라 스키마의 `node-test`/`lint-rule`에 해당 없음 |
| 빌드·런타임이 사용자 동의 없이 외부 텔레메트리를 전송해서는 안 된다 (Next.js · Supabase CLI 기본 동작) | R7, R8 | resolved | verification: **test** — `NEXT_TELEMETRY_DISABLED=1`이 Dockerfile·환경에 고정되어 있음을 설정 검증. 서술자 미포착(SOFT) |
| RTT 측정 문서가 Supabase project ref · `DATABASE_URL` · 어떤 API 키도 포함해서는 안 된다 | R9 | resolved | verification: **test** — 문서 대상 grep 체크로 기계적 판정 가능. 서술자 미포착(SOFT): 대상이 마크다운 문서라 `lint-rule` 스키마에 맞지 않음 |

**캐논 참조 (여기서 주조하지 않음):**
- `.env.local`/시크릿의 VCS 커밋 방지 — 캐논 시크릿 관리. `.gitignore`(`.env.*`)와 `/gsd-secure-phase` 소관
- `/health` 응답의 정보 노출(버전·env·DB URL) — 캐논 정보 노출(OWASP). `/gsd-secure-phase` 소관
- uv 사설/임의 인덱스 추가 — 캐논 공급망 보안. `/gsd-secure-phase` 소관

**서술자 미포착에 관한 주석:** 4건 모두 `verification: test`이지만 `check_kind`(`node-test` | `lint-rule`) 서술자를 포착하지 않았다. 이 페이즈의 검증 수단은 Python pytest · Railway 배포 설정 · 마크다운 grep이라 스키마의 두 종류 어디에도 정확히 맞지 않는다. SOFT capture 규칙에 따라 비워 두며, 결과적으로 verify 단계에서 자동 green이 되지 않고 fail-closed로 플래그된다 — 의도된 동작이다.

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                              |
|--------------------|-------|------|--------|----------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | "클라우드 기동" = `api`+`worker` 2서비스로 한정 확정 |
| Boundary Clarity   | 0.94  | 0.70 | ✓      | 제외 4건(JWT · 라우터 · 잡 루프 · `0007`) 명시 선택  |
| Constraint Clarity | 0.90  | 0.65 | ✓      | 리전 불변 · `0005` 순서 · Next 하한 · 예산           |
| Acceptance Criteria| 0.90  | 0.70 | ✓      | 24개 pass/fail + 부정 수용기준 4개                  |
| **Ambiguity**      | 0.09  | ≤0.20| ✓      | 게이트 통과, 미달 차원 없음                          |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective     | Question summary                          | Decision locked                                                        |
|-------|-----------------|-------------------------------------------|------------------------------------------------------------------------|
| 0     | Scout           | 코드베이스 현재 상태는?                    | `0005` 부재 · `apps/` 전무 · CLI link 이력 없음 · `.env.local`에 실제 키 |
| 1     | Researcher      | Supabase Cloud 프로젝트 존재 여부·리전?    | **존재, `ap-southeast-1`** → BOOT-02는 생성이 아니라 검증               |
| 1     | Researcher      | Railway 계정·결제 상태?                    | 계정 없음 → 가입 + Hobby 구독 + 프로젝트 생성이 범위 안                  |
| 1     | Researcher      | Phase 1에서 Next.js는 어디까지?            | 스캐폴딩 + 로컬 테스트 통과만. 배포는 Phase 6                            |
| 2     | Simplifier      | `packages/core`가 Phase 1에 담는 것?       | **공용 로깅만** (structlog + contextvar). 토크나이저·Settings는 Phase 2  |
| 2     | Simplifier      | `/health`의 판정 범위?                     | liveness `/health` + readiness `/health/ready` **분리**                 |
| 2     | Researcher      | BOOT-09 RTT의 합격 기준?                   | 숫자(p50/p95) + ×5 환산 기록 자체가 합격. 임계값 없음                    |
| 3     | Boundary Keeper | CLI 업그레이드 목표와 판정?                | 최신(2.111.0+) + `db reset` 재검증. `config.toml` 수정도 산출물          |
| 3     | Boundary Keeper | "동일 이미지"를 어떻게 기계 증명?          | 빌드 다이제스트 비교 (실패 시 커밋 SHA + `GIT_SHA` 대체 판정)            |
| 3     | Boundary Keeper | 인증 하드닝 구체 수치?                     | 최소 12자 + 이메일 확인 필수                                            |
| 3     | Boundary Keeper | 명시적 제외 항목?                          | JWT 인증 · 비즈니스 라우터 · 잡 처리 루프 · 마이그레이션 `0007` 전부 제외 |
| 5.5   | Edge Probe      | 10개 요구사항 엣지 후보                    | 10/10 covered — 경로 3세그먼트 · push 선행공백 · config 마이그레이션 · `--frozen` · prettier 범위 · ready 타임아웃 · 클라이언트 컴포넌트 한정 · 다이제스트 2단 판정 · 워밍업 후 측정 · 기존 사용자 0명 |
| 5.6   | Prohibition     | must-NOT 4건 (캐논 3건은 breadcrumb 후 제외) | 4/4 resolved (전부 test 티어, 서술자 SOFT 미포착)                       |

---

*Phase: 01-bootstrap-and-ground-truth*
*Spec created: 2026-08-02*
*Next step: /gsd-discuss-phase 1 — 구현 결정 (Dockerfile 구조, uv 워크스페이스 레이아웃, structlog 프로세서 체인, Railway 서비스 설정 방식 등)*
