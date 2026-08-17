import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

import { requireEnv } from "@/lib/env";

function normalizeNext(next: string | null) {
  return next?.startsWith("/") && !next.startsWith("//") ? next : "/";
}

// authorization code는 한 번만 교환할 수 있으므로 middleware가 아닌 이 handler가
// 세션 쿠키를 기록한다. middleware matcher는 이 경로를 포함하지 않는다.
export async function GET(request: NextRequest) {
  const cookieResponse = NextResponse.next();
  const supabase = createServerClient(
    requireEnv("NEXT_PUBLIC_SUPABASE_URL"),
    requireEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"),
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (cookies) => {
          for (const { name, value, options } of cookies) {
            cookieResponse.cookies.set(name, value, options);
          }
        },
      },
    },
  );

  const code = request.nextUrl.searchParams.get("code");
  const next = normalizeNext(request.nextUrl.searchParams.get("next"));
  const { error } = code
    ? await supabase.auth.exchangeCodeForSession(code)
    : { error: new Error("missing authorization code") };
  const destination = error ? "/login?error=auth" : next;
  const response = NextResponse.redirect(new URL(destination, request.url));

  for (const cookie of cookieResponse.cookies.getAll()) {
    response.cookies.set(cookie);
  }

  return response;
}
