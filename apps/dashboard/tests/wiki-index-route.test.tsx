import { beforeEach, describe, expect, it, vi } from "vitest";

const fixtures = vi.hoisted(() => ({
  pages: [] as {
    id: string;
    slug: string;
    title: string;
    category: string;
    content: string;
    verification_status: string;
    disputed: boolean;
  }[],
  bookmarks: [] as { wiki_id: string }[],
}));

const state = vi.hoisted(() => ({
  wikiPagesQueried: false,
  wikiPageColumns: "",
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(async () => ({
    from: (table: string) => {
      let inIds: string[] | null = null;
      const query = {
        select: (columns?: string) => {
          if (table === "wiki_pages" && columns) {
            state.wikiPageColumns = columns;
          }
          return query;
        },
        eq: () => query,
        in: (_column: string, ids: string[]) => {
          inIds = ids;
          return query;
        },
        order: () => query,
        then: (resolve: (value: { data: unknown; error: null }) => unknown) => {
          if (table === "wiki_pages") {
            state.wikiPagesQueried = true;
            const rows = inIds
              ? fixtures.pages.filter((p) => inIds!.includes(p.id))
              : fixtures.pages;
            return resolve({ data: rows, error: null });
          }
          if (table === "user_wiki_bookmarks") {
            return resolve({ data: fixtures.bookmarks, error: null });
          }
          return resolve({ data: [], error: null });
        },
      };
      return query;
    },
  })),
}));

vi.mock("@/components/WikiLibrary", () => ({
  WikiLibrary: () => null,
}));

import { WikiLibrary } from "@/components/WikiLibrary";
import WikiIndexPage from "@/app/w/[workspaceId]/wiki/page";

async function renderWikiIndexPage(bookmarked?: string) {
  const result = await WikiIndexPage({
    params: Promise.resolve({ workspaceId: "ws-1" }),
    searchParams: Promise.resolve(bookmarked ? { bookmarked } : {}),
  });
  expect(result.type).toBe(WikiLibrary);
  return result.props as { pages: { id: string }[]; workspaceId: string };
}

describe("WikiIndexPage route", () => {
  beforeEach(() => {
    fixtures.pages = [
      {
        id: "wiki-1",
        slug: "a",
        title: "A",
        category: "guides",
        content: "",
        verification_status: "unverified",
        disputed: false,
      },
      {
        id: "wiki-2",
        slug: "b",
        title: "B",
        category: "guides",
        content: "",
        verification_status: "unverified",
        disputed: false,
      },
    ];
    fixtures.bookmarks = [];
    state.wikiPagesQueried = false;
    state.wikiPageColumns = "";
  });

  it("bookmarked 파라미터가 없으면 전체 위키 목록을 그대로 넘긴다", async () => {
    const props = await renderWikiIndexPage();
    expect(props.pages.map((p) => p.id)).toEqual(["wiki-1", "wiki-2"]);
    expect(state.wikiPageColumns).toContain("sources");
    expect(state.wikiPageColumns).toContain("expires_at");
  });

  it("bookmarked=true면 즐겨찾기한 위키만 wiki_pages에서 in()으로 좁혀 조회한다", async () => {
    fixtures.bookmarks = [{ wiki_id: "wiki-2" }];

    const props = await renderWikiIndexPage("true");
    expect(props.pages.map((p) => p.id)).toEqual(["wiki-2"]);
    expect(state.wikiPageColumns).toContain("sources");
  });

  it("bookmarked=true인데 즐겨찾기가 없으면 wiki_pages 조회 자체를 생략한다", async () => {
    fixtures.bookmarks = [];

    const props = await renderWikiIndexPage("true");
    expect(props.pages).toEqual([]);
    expect(state.wikiPagesQueried).toBe(false);
  });
});
