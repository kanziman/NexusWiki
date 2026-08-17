## Context

현 인증은 이메일·비밀번호뿐이며, 루트는 0개 워크스페이스 사용자에게 초대 안내만 표시한다. 요구 계약은 proposal과 delta specs를 따른다.

## Goals / Non-Goals

**Goals:** Google OAuth 단일 경로, 안전한 콜백, 개인 워크스페이스 온보딩, TDD-lite 검증을 제공한다.

**Non-Goals:** Google Cloud·Supabase Cloud 자격 증명 발급, 법률 문안 작성·게시, 이메일 초대 재설계, UUID 기반 내부 라우트 전환은 하지 않는다.

## Decisions

### ADR-1: Route Handler가 OAuth 코드를 교환한다

**Context:** 코드는 1회용이고 세션 쿠키를 직접 쓴다.

**Decision:** `/auth/callback`만 코드를 교환하며 middleware matcher에서 제외한다. `next`는 내부 경로 allowlist로 정규화한다.

**Alternatives:** middleware 교환은 리다이렉트 경쟁으로 코드를 소비할 수 있고, 클라이언트 교환은 쿠키 경계를 넓힌다.

**Consequences:** 콜백은 middleware와 함께 유일한 쿠키 기록자가 된다.

### ADR-2: 온보딩은 requester JWT로 직접 INSERT한다

**Context:** RLS와 owner 멤버십 트리거가 이미 사용자 경로를 강제한다.

**Decision:** 서버 action은 요청자 클라이언트로 전역 slug 집합을 읽고 `slugify`한 personal workspace를 INSERT한다.

**Alternatives:** service_role은 RLS를 우회하고, DB 기본 slug는 생성 규칙을 분산한다.

**Consequences:** UNIQUE 충돌은 최종 방어선이며 충돌 재시도를 구현한다.

## Risks / Trade-offs

- [외부 Provider 미설정] → 코드·단위 테스트는 완료하되 실제 OAuth smoke test는 자격 증명 제공 뒤 수행한다.
- [법률 문안 부재] → 준비 중 경로만 제공하고 공개 전 별도 legal 검토를 요구한다.
