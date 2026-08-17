import { beforeEach, describe, expect, it, vi } from "vitest";

// GraphLensFilter.test.tsx와 같은 패턴 — redirect()는 실제로는 특수 에러를
// 던져 프레임워크가 가로채는 방식이라, 여기서는 호출 인자(리다이렉트 대상
// URL)만 직접 관찰한다.
const redirectMock = vi.fn();
vi.mock("next/navigation", () => ({
  redirect: (url: string) => redirectMock(url),
}));

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
  beforeEach(() => {
    redirectMock.mockReset();
  });

  it.each([
    ["ASCII slug", "meeting-notes", "meeting-notes"],
    ["percent-encoded Hangul slug", "%ED%9A%8C%EC%9D%98%EB%A1%9D", "회의록"],
    ["already-decoded mixed slug", "meeting-회의록", "meeting-회의록"],
  ])(
    "looks up a %s using its decoded slug and redirects into the unified viewer",
    async (_name, slug, expectedSlug) => {
      state.requestedSlugs.length = 0;

      await WikiPageRoute({
        params: Promise.resolve({ workspaceId: "workspace-1", slug }),
      });

      expect(state.requestedSlugs).toContain(expectedSlug);
      expect(redirectMock).toHaveBeenCalledWith(
        `/w/workspace-1/ask?slug=${encodeURIComponent(expectedSlug)}&tab=wiki`,
      );
    },
  );

  it("returns the generic not-found state without querying for a malformed slug", async () => {
    state.requestedSlugs.length = 0;

    const result = await WikiPageRoute({
      params: Promise.resolve({ workspaceId: "workspace-1", slug: "%E0%A4%A" }),
    });

    expect(state.requestedSlugs).toEqual([]);
    expect(redirectMock).not.toHaveBeenCalled();
    expect(
      (result.type as () => { props: { children: string } })().props.children,
    ).toBe("페이지를 찾을 수 없습니다");
  });

  it("does not redirect when the workspace-scoped lookup finds no matching page", async () => {
    state.requestedSlugs.length = 0;

    const result = await WikiPageRoute({
      params: Promise.resolve({
        workspaceId: "workspace-1",
        slug: "no-such-page",
      }),
    });

    expect(redirectMock).not.toHaveBeenCalled();
    expect(
      (result.type as () => { props: { children: string } })().props.children,
    ).toBe("페이지를 찾을 수 없습니다");
  });
});
