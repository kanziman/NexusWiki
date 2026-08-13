import { describe, expect, it, vi } from "vitest";

const redirect = vi.hoisted(() =>
  vi.fn((destination: string) => {
    throw new Error(`redirect:${destination}`);
  }),
);
const navShell = vi.hoisted(() => vi.fn(() => null));

vi.mock("next/navigation", () => ({ redirect }));
vi.mock("@/components/NavShell", () => ({ NavShell: navShell }));
vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(async () => {
    const query = {
      select: () => query,
      eq: () => query,
      single: async () => ({ data: null, error: { message: "not found" } }),
    };
    return {
      auth: {
        getUser: async () => ({
          data: { user: { email: "member@example.com" } },
        }),
      },
      from: () => query,
    };
  }),
}));

import WorkspaceLayout from "@/app/w/[workspaceId]/layout";

describe("workspace layout access boundary", () => {
  it("redirects inaccessible workspace IDs without rendering workspace navigation", async () => {
    await expect(
      WorkspaceLayout({
        children: <p>비공개 데이터</p>,
        params: Promise.resolve({ workspaceId: "inaccessible-workspace" }),
      }),
    ).rejects.toThrow("redirect:/");

    expect(navShell).not.toHaveBeenCalled();
  });
});
