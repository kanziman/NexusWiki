import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const exchangeCodeForSession = vi.fn();

vi.mock("@supabase/ssr", () => ({
  createServerClient: () => ({ auth: { exchangeCodeForSession } }),
}));
vi.mock("@/lib/env", () => ({ requireEnv: () => "test-value" }));

import { GET } from "@/app/auth/callback/route";

describe("OAuth callback", () => {
  beforeEach(() => {
    exchangeCodeForSession.mockReset();
  });

  it("코드를 한 번 교환하고 허용된 내부 next로 이동한다", async () => {
    exchangeCodeForSession.mockResolvedValue({ error: null });

    const response = await GET(
      new NextRequest(
        "https://dashboard.test/auth/callback?code=code-1&next=/w/ws-1",
      ),
    );

    expect(exchangeCodeForSession).toHaveBeenCalledWith("code-1");
    expect(response.headers.get("location")).toBe(
      "https://dashboard.test/w/ws-1",
    );
  });

  it.each(["https://evil.test", "//evil.test", "relative"])(
    "외부 또는 상대 next %s는 루트로 정규화한다",
    async (next) => {
      exchangeCodeForSession.mockResolvedValue({ error: null });

      const response = await GET(
        new NextRequest(
          `https://dashboard.test/auth/callback?code=code-1&next=${encodeURIComponent(next)}`,
        ),
      );

      expect(response.headers.get("location")).toBe("https://dashboard.test/");
    },
  );

  it("코드 교환 실패는 단일 오류 경로로 이동한다", async () => {
    exchangeCodeForSession.mockResolvedValue({
      error: { message: "bad code" },
    });

    const response = await GET(
      new NextRequest("https://dashboard.test/auth/callback?code=code-1"),
    );

    expect(response.headers.get("location")).toBe(
      "https://dashboard.test/login?error=auth",
    );
  });
});
