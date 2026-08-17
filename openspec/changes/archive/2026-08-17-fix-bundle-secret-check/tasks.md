## 1. SEC-05 bundle 검사 계약

- [x] 1.1 실제 Supabase secret key 값만 차단하고 SDK 진단 문자열은 허용하도록 검사와 회귀 fixture를 구현한다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/22)
  - Given: OAuth SDK bundle에 `sb_secret_` 및 `SUPABASE_SECRET_KEY` 식별자가 존재하고 실제 secret 값은 없다.
  - When: SEC-05 검사를 실행한다.
  - Then: 진단 문자열 fixture는 통과하고, static·server·source map의 실제 secret key fixture는 실패하며, cache 제외와 빈 산출물 fail-closed 계약은 유지된다.
  - Verification: 새 focused 검사 테스트, `pnpm --dir apps/dashboard build`, `bash scripts/ci_check_bundle_secrets.sh`, `openspec validate fix-bundle-secret-check --strict`를 통과한다.
