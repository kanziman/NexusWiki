import { describe, expect, it, vi } from "vitest";

const fixtureSource = {
  id: "source-1",
  title: "킥오프 문서",
  source_type: "text",
  created_at: "2026-08-12T00:00:00Z",
};

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(async () => ({
    from: (table: string) => {
      let matchedId = false;
      const query = {
        select: () => query,
        eq: (column: string, value: string) => {
          if (table === "raw_sources" && column === "id") {
            matchedId = value === fixtureSource.id;
          }
          return query;
        },
        single: async () =>
          table === "raw_sources" && matchedId
            ? { data: fixtureSource, error: null }
            : { data: null, error: { message: "not found" } },
      };
      return query;
    },
  })),
}));

import SourceDetailRoute from "@/app/w/[workspaceId]/sources/[id]/page";

describe("SourceDetailRoute", () => {
  it("renders the source title behind a real return link to the sources library", async () => {
    const result = await SourceDetailRoute({
      params: Promise.resolve({
        workspaceId: "workspace-1",
        id: fixtureSource.id,
      }),
    });

    const children = (result as { props: { children: unknown[] } }).props
      .children as [React.ReactElement, React.ReactElement];
    const [detailHeader] = children;

    expect(
      (detailHeader.props as { title: string; libraryHref: string }).title,
    ).toBe(fixtureSource.title);
    expect(
      (detailHeader.props as { title: string; libraryHref: string })
        .libraryHref,
    ).toBe("/w/workspace-1/sources");
  });

  it("returns the generic not-found state for an unknown id", async () => {
    const result = await SourceDetailRoute({
      params: Promise.resolve({
        workspaceId: "workspace-1",
        id: "missing-source",
      }),
    });

    expect((result as { props: { children: string } }).props.children).toBe(
      "자료를 찾을 수 없습니다",
    );
  });
});
