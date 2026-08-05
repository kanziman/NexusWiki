# Supabase Auth 하드닝 검증 기록

## 정책 적용 전 계정 상태

### 측정 일시

2026-08-05 KST

### 방법

- 연결된 Supabase Cloud 데이터베이스에 `select count(*) from auth.users`를 직접 실행했다.
- 로컬 데이터베이스 컨테이너에서도 같은 쿼리를 실행했다.
- 계정이 발견되면 이메일을 마스킹해 기록한 뒤 삭제하고 다시 조회하도록 판정 기준을 고정했다.
- 프로젝트 ref, 연결 문자열, API 키 값은 기록하지 않았다.

### 결과

- 클라우드 `auth.users` 행 수: `0`
- 로컬 `auth.users` 행 수: `0`
- 삭제 대상: 없음
- 정책 적용 전 모든 기존 계정이 제거된 상태임을 확인했다.

정책 적용은 Task 2, 거부 증명은 Task 3에서 수행한다.

## Auth 정책 적용

### 적용 일시

2026-08-05 KST

### 방법

- 로컬 `supabase/config.toml`의 Auth 설정 두 값을 변경하고 스택을 재기동했다.
- 로그인된 Supabase CLI의 Management API 동기화 경로로 클라우드 Auth 설정을 적용했다.
- CLI가 전체 Auth 설정을 동기화하며 건드린 범위 밖 값은 적용 전 원격 값으로 즉시 복원했다.

### 결과

- 로컬 `minimum_password_length`: `6` → `12`
- 로컬 `enable_confirmations`: `false` → `true`
- 클라우드 Minimum password length: `6` → `12`
- 클라우드 Confirm email: 적용 전 이미 `true`, 적용 후 `true` 유지
- 클라우드의 범위 밖 Auth 설정은 적용 전 값으로 복원했다.

거부 증명은 Task 3에서 수행한다.
