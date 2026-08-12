import { createBrowserClient } from "@supabase/ssr";

/**
 * 브라우저 전용 Supabase 클라이언트 팩토리.
 *
 * 관련 태스크: 06-01-PLAN.md Task 1 (D-02)
 *
 * ⚠️ 이 파일이 브라우저 Supabase 클라이언트를 만드는 유일한 곳이다. 인증 또는
 * 요청자 세션을 필요로 하는 클라이언트 컴포넌트는 전부 여기서 `createClient()`를
 * 가져와야 한다 — 클라이언트 컴포넌트마다 `createBrowserClient`를 새로 호출하면
 * D-02(middleware.ts가 유일한 쿠키 기록자)의 경계를 우회하는 경로가 생길 수 있다.
 */
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
  );
}
