## Why

새 사용자는 계정을 만들거나 첫 워크스페이스를 만들 수 없어 제품에 진입할 수 없다. Google OAuth 단일 인증과 개인 워크스페이스 온보딩으로 안전한 셀프서비스 진입 경로를 제공한다.

용어: **온보딩**은 인증된 사용자가 RLS로 보이는 워크스페이스가 없을 때 첫 개인 워크스페이스를 만드는 흐름이다.

GitHub umbrella: https://github.com/kanziman/NexusWiki/issues/15

## What Changes

- **BREAKING** 이메일·비밀번호 로그인 대신 Google OAuth 단일 로그인·가입을 제공한다.
- OAuth 콜백이 코드 교환 후 내부 경로로만 이동하도록 한다.
- 워크스페이스가 없는 인증 사용자가 이름 하나로 `personal` 워크스페이스를 만든다.
- `/signup`에 이용약관·개인정보 처리방침 준비 중 경로를 연결한다. 법률 문안·게시 승인은 제외한다.
- Supabase 로컬 Google Provider 설정을 시크릿 참조만으로 추가한다.

## Capabilities

### New Capabilities

- `google-authentication`: Google OAuth 단일 인증과 안전한 콜백 계약을 제공한다.
- `workspace-onboarding`: 첫 개인 워크스페이스의 셀프서비스 생성 흐름을 제공한다.

### Modified Capabilities

- `workspace-entry-flow`: 0개 워크스페이스 사용자의 초대 안내를 온보딩으로 변경한다.

## Impact

- Dashboard 인증 화면·미들웨어·Route Handler·루트 진입 화면과 테스트에 영향을 준다.
- `supabase/config.toml`에 로컬 Provider 설정을 추가한다.
- Google Cloud와 Supabase Cloud Provider의 실제 자격 증명·등록은 별도 권한이 필요하다.
