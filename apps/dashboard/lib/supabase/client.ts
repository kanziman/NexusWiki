import { createBrowserClient } from "@supabase/ssr";

import { requireEnv } from "@/lib/env";

/**
 * 브라우저 전용 Supabase 클라이언트 팩토리.
 *
 * 관련 태스크: 06-01-PLAN.md Task 1 (D-02)
 *
 * ⚠️ 이 파일이 브라우저 Supabase 클라이언트를 만드는 유일한 곳이다. 인증 또는
 * 요청자 세션을 필요로 하는 클라이언트 컴포넌트는 전부 여기서 `createClient()`를
 * 가져와야 한다 — 클라이언트 컴포넌트마다 `createBrowserClient`를 새로 호출하면
 * D-02(middleware.ts가 유일한 쿠키 기록자)의 경계를 우회하는 경로가 생길 수 있다.
 *
 * 06-REVIEW.md WR-05: `!` 비-null 단언 대신 `requireEnv`로 런타임에 실제로
 * 검증한다 — 값이 없으면 Supabase SDK의 불투명한 에러 대신 어떤 키가
 * 빠졌는지 명시한 에러로 즉시 실패한다(CLAUDE.md fail-fast 규칙).
 */
export function createClient() {
  return createBrowserClient(
    requireEnv("NEXT_PUBLIC_SUPABASE_URL"),
    requireEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"),
  );
}
