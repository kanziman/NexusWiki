import { describe, expect, it, vi } from "vitest";

const fixturePage = {
  id: "wiki-1",
  title: "회의록",
  content: "본문",
  verification_status: "unverified",
  verified_by: null,
  verified_at: null,
  expires_at: null,
  disputed: false,
};

const state = vi.hoisted(() => ({
  requestedSlugs: [] as string[],
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(async () => ({
    from: (table: string) => {
      let slug: string | undefined;
      const query = {
        select: () => query,
        eq: (column: string, value: string) => {
          if (table === "wiki_pages" && column === "slug") {
            slug = value;
            state.requestedSlugs.push(value);
          }
          return query;
        },
        single: async () =>
          table === "wiki_pages" &&
          ["meeting-notes", "회의록", "meeting-회의록"].includes(slug ?? "")
            ? { data: fixturePage, error: null }
            : { data: null, error: { message: "not found" } },
        then: (resolve: (value: { data: unknown; error: null }) => unknown) =>
          resolve({ data: [], error: null }),
      };
      return query;
    },
    rpc: async () => ({ data: true, error: null }),
  })),
}));

import WikiPageRoute from "@/app/w/[workspaceId]/wiki/[slug]/page";

describe("WikiPageRoute", () => {
  it.each([
    ["ASCII slug", "meeting-notes", "meeting-notes"],
    ["percent-encoded Hangul slug", "%ED%9A%8C%EC%9D%98%EB%A1%9D", "회의록"],
    ["already-decoded mixed slug", "meeting-회의록", "meeting-회의록"],
  ])(
    "looks up a %s using its decoded slug",
    async (_name, slug, expectedSlug) => {
      state.requestedSlugs.length = 0;

      const result = await WikiPageRoute({
        params: Promise.resolve({ workspaceId: "workspace-1", slug }),
      });

      expect(state.requestedSlugs).toContain(expectedSlug);
      expect((result as { props: { page: unknown } }).props.page).toEqual(
        fixturePage,
      );
    },
  );

  it("returns the generic not-found state without querying for a malformed slug", async () => {
    state.requestedSlugs.length = 0;

    const result = await WikiPageRoute({
      params: Promise.resolve({ workspaceId: "workspace-1", slug: "%E0%A4%A" }),
    });

    expect(state.requestedSlugs).toEqual([]);
    expect(
      (result.type as () => { props: { children: string } })().props.children,
    ).toBe("페이지를 찾을 수 없습니다");
  });
});
