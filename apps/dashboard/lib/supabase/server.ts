import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

import { requireEnv } from "@/lib/env";

/**
 * 서버 컴포넌트/RSC 전용 Supabase 클라이언트 팩토리.
 *
 * 관련 태스크: 06-01-PLAN.md Task 1 (D-02, API-04 RSC carve-out)
 *
 * 요청자 자신의 세션 쿠키로 클라이언트를 만든다 — `app/page.tsx`,
 * `app/w/[workspaceId]/layout.tsx` 등에서 이 클라이언트로 직접 PostgREST를
 * 읽으면 RLS가 요청자 JWT 기준으로 격리를 강제한다(service_role 아님).
 *
 * ⚠️ 서버 컴포넌트는 쿠키를 쓸 수 없다 (Next.js가 렌더링 중 응답 헤더 변경을 막음).
 * `setAll`의 try/catch는 버그를 숨기는 것이 아니라 `@supabase/ssr` 공식 문서가
 * 명시하는 패턴이다 — 세션 갱신은 `middleware.ts`(D-02, 유일한 쿠키 기록자)의 몫이고,
 * 여기서 쓰기가 무시돼도 미들웨어가 다음 요청에서 다시 갱신한다.
 *
 * 06-REVIEW.md WR-05: `!` 비-null 단언 대신 `requireEnv`로 런타임에 실제로
 * 검증한다(CLAUDE.md fail-fast 규칙).
 */
export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    requireEnv("NEXT_PUBLIC_SUPABASE_URL"),
    requireEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"),
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            for (const { name, value, options } of cookiesToSet) {
              cookieStore.set(name, value, options);
            }
          } catch {
            // 서버 컴포넌트에서 호출된 경우 — middleware.ts가 세션 갱신을 담당한다.
          }
        },
      },
    },
  );
}
