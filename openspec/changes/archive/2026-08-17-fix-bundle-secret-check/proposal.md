## Why

Google OAuth가 Supabase SDK의 OAuth 경로를 client bundle에 포함하면서 SDK의 진단용 키 식별자가 SEC-05 검사에 걸린다. 실제 service key 유출을 놓치지 않으면서 이 오탐을 제거해야 PR 검증이 다시 신뢰할 수 있다.

## What Changes

- SEC-05가 단순 접두어·키 이름이 아니라 실제 Supabase secret key 값의 형태를 탐지하도록 보정한다.
- SDK 진단 문자열과 source map이 있어도 통과하고, 실제 secret key 값은 실패하는 회귀 검증을 추가한다.
- 검사 대상과 cache 제외 정책은 유지한다.

## Capabilities

이 change는 제품 동작을 변경하지 않는 CI 검증 도구 수정이다. `.openspec.yaml`의 `skip_specs: true`로 delta spec 생성을 생략한다.

## Impact

- `scripts/ci_check_bundle_secrets.sh`와 해당 테스트가 영향을 받는다.
- GitHub Actions의 SEC-05 결과가 PR #20에서 다시 신뢰 가능한 보안 신호가 된다.
