## Context

See `proposal.md`. SEC-05는 현재 bundle의 모든 파일에서 `sb_secret_`과 `SUPABASE_SECRET_KEY`의 단순 문자열 존재를 검사한다. OAuth SDK가 포함하는 오류·진단 문구도 같은 문자열을 사용하므로, 값이 전혀 없는 CI build에서도 false positive가 발생한다.

## Goals / Non-Goals

**Goals:**

- 실제 Supabase secret key 값이 bundle에 있으면 CI를 실패시킨다.
- SDK가 포함하는 진단용 식별자와 source map은 실제 값으로 판정하지 않는다.
- 대상 경로 부재·빈 산출물·grep 오류를 실패시키는 현재 fail-closed 동작을 유지한다.

**Non-Goals:**

- 다른 provider의 secret 검사 추가
- Vercel 또는 Supabase 환경변수 설정 변경
- Next.js 산출물 구성 변경

## Decisions

### 실제 키 값 형식을 검사한다

`sb_secret_` 뒤에 충분한 길이의 key payload가 이어지는 경우만 위반으로 판정한다. `SUPABASE_SECRET_KEY` 변수명은 실제 값이 아니므로 패턴 목록에서 제거한다.

단순 접두어 탐지는 SDK의 정상적인 오류 메시지를 실제 비밀값으로 오인한다. 반대로 검사 자체를 제거하거나 `.next/static`만 검사하면 실제 값이 server artifact나 source map에 들어간 경우를 놓친다.

### 검사는 테스트 fixture로 계약을 고정한다

독립 temporary bundle fixture에 SDK 진단 문자열, 실제 secret key 모양, cache 경로, 빈 경로를 만들어 스크립트의 허용·차단 동작을 검증한다. 이 방식은 production build나 secret 환경변수 없이도 회귀를 재현한다.

## Risks / Trade-offs

- [새 key 형식이 현재 가정보다 짧음] → Supabase key 형식의 최소 payload 길이를 보수적으로 정하고, 실제 운영 key 형식으로 fixture를 검증한다.
- [source map에 실제 값이 들어감] → source map을 계속 검사하며 실제 값 형식은 실패시킨다.
- [검사 완화로 탐지 범위가 줄어듦] → 단순 식별자만 제외하고 값 패턴과 fail-closed 동작을 테스트로 고정한다.
