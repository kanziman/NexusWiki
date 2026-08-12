import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

/**
 * 테넌트 게이트이자 유일한 쿠키 기록자.
 *
 * 관련 태스크: 06-01-PLAN.md Task 1 (D-02, 06-CONTEXT.md)
 * 위협: T-06-01 (Spoofing, middleware.ts)
 *
 * ⚠️ 이 파일이 `apps/dashboard` 전체에서 세션 쿠키를 쓰는 유일한 곳이어야 한다
 * (D-02). 다른 라우트/컴포넌트가 쿠키를 직접 쓰기 시작하면 CVE-2025-29927
 * (`x-middleware-subrequest` 헤더 위조로 미들웨어 우회)이 열어 놓았던 것과 같은
 * 종류의 우회 경로가 생긴다. CLAUDE.md 제약대로 이 앱은 Next.js 15.5.22를 쓰므로
 * (>= 15.2.3) 헤더 위조 자체는 이미 막혀 있지만, 게이트가 미들웨어 하나뿐이라는
 * 불변식은 여기서 별도로 지켜야 한다.
 *
 * T-06-02 (Information Disclosure, D-12 상속): `/w/{id}`가 존재하지 않는
 * 워크스페이스인지 아니면 멤버가 아닌 워크스페이스인지 여기서는 구분하지 않는다 —
 * 이 파일은 로그인 여부만 본다. 존재/멤버십 판정은 RLS로 읽는
 * `app/w/[workspaceId]/layout.tsx`의 몫이며, 거기서도 두 경우를 구분하지 않고
 * 동일하게 `/`로 리다이렉트한다.
 */
export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          for (const { name, value } of cookiesToSet) {
            request.cookies.set(name, value);
          }
          response = NextResponse.next({ request });
          for (const { name, value, options } of cookiesToSet) {
            response.cookies.set(name, value, options);
          }
        },
      },
    },
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/w/") && !user) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.pathname = "/login";
    return NextResponse.redirect(redirectUrl);
  }

  if (pathname === "/login" && user) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.pathname = "/";
    return NextResponse.redirect(redirectUrl);
  }

  return response;
}

export const config = {
  matcher: ["/w/:path*", "/login"],
};
