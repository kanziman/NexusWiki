import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getUser = vi.fn();

vi.mock("@supabase/ssr", () => ({
  createServerClient: () => ({ auth: { getUser } }),
}));
vi.mock("@/lib/env", () => ({ requireEnv: () => "test-value" }));

import { middleware } from "../middleware";

describe("middleware authentication gate", () => {
  beforeEach(() => {
    getUser.mockReset();
  });

  it("redirects a logged-out visitor from a workspace route to login", async () => {
    getUser.mockResolvedValue({ data: { user: null } });

    const response = await middleware(
      new NextRequest("https://dashboard.test/w/workspace-1/sources"),
    );

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe(
      "https://dashboard.test/login",
    );
  });

  it("redirects a logged-out visitor from the home page to login", async () => {
    getUser.mockResolvedValue({ data: { user: null } });

    const response = await middleware(
      new NextRequest("https://dashboard.test/"),
    );

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe(
      "https://dashboard.test/login",
    );
  });

  it("lets a logged-in visitor reach the home page", async () => {
    getUser.mockResolvedValue({ data: { user: { id: "user-1" } } });

    const response = await middleware(
      new NextRequest("https://dashboard.test/"),
    );

    expect(response.status).toBe(200);
  });
});
