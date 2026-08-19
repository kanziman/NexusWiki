import { describe, expect, it, vi } from "vitest";

// ⚠️ 이 테스트가 존재하는 이유: public-wiki-page-route.test.tsx 는
// `@/lib/supabase/public` 을 통째로 목킹하므로 **이 파일 자체의 회귀는 못 잡는다.**
// `getAll()` 을 `cookieStore.getAll()` 로 되돌리면 라우트 테스트 4건은 전부
// 통과한 채 킬스위치만 다시 무력화된다 — 같은 조용한 실패가 한 파일 옆으로
// 옮겨간 형태다. 그 한 칸을 여기서 막는다.
const calls = vi.hoisted(() => [] as unknown[][]);

vi.mock("@supabase/ssr", () => ({
  createServerClient: (...args: unknown[]) => {
    calls.push(args);
    return {};
  },
}));

// next/headers 를 import 하면 즉시 실패한다 — 공개 클라이언트가 요청 쿠키에
// 손을 대는 유일한 통로다.
vi.mock("next/headers", () => ({
  cookies: () => {
    throw new Error("공개 클라이언트가 next/headers 의 쿠키를 읽었다");
  },
}));

import { createPublicClient } from "@/lib/supabase/public";

type CookieAdapter = {
  cookies: { getAll: () => unknown[]; setAll: (value: unknown) => void };
};

describe("createPublicClient", () => {
  it("요청 쿠키를 읽지 않아 항상 anon 으로 실행된다", () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = "http://supabase.test";
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY = "sb_publishable_test";

    createPublicClient();

    expect(calls).toHaveLength(1);
    const options = calls[0][2] as CookieAdapter;

    // 빈 배열이라야 @supabase/ssr 이 세션 없는 클라이언트를 만든다.
    expect(options.cookies.getAll()).toEqual([]);

    // 세션 주입 통로 셋을 넘기지 않는다(global.headers · accessToken · storage).
    const passed = options as unknown as Record<string, unknown>;
    expect(passed.global).toBeUndefined();
    expect(passed.accessToken).toBeUndefined();
    expect(passed.auth).toBeUndefined();
  });
});
