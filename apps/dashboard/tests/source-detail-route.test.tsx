import { beforeEach, describe, expect, it, vi } from "vitest";

const fixtureSource = {
  id: "source-1",
  title: "킥오프 문서",
  source_type: "text",
  created_at: "2026-08-12T00:00:00Z",
};

const fixtureChunk = {
  id: "chunk-1",
  raw_source_id: fixtureSource.id,
  chunk_index: 0,
  char_start: 0,
  char_end: 5,
  content: "청크 내용",
};

const fixtureWikiPages = [
  {
    id: "wiki-1",
    title: "인용 문서",
    slug: "citing-page",
    category: "guides",
    sources: [{ raw_source_id: fixtureSource.id }],
  },
  {
    id: "wiki-2",
    title: "무관한 문서",
    slug: "unrelated-page",
    category: "guides",
    sources: [{ raw_source_id: "another-source" }],
  },
];

type QueryError = { code: string; message: string } | null;

const queryState = vi.hoisted(() => ({
  eqCalls: [] as { table: string; column: string; value: string }[],
  sourceError: null as QueryError,
  chunksError: null as QueryError,
  wikiError: null as QueryError,
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(async () => ({
    from: (table: string) => {
      let matchedId = false;
      let matchedWorkspace = false;
      const query = {
        select: () => query,
        eq: (column: string, value: string) => {
          queryState.eqCalls.push({ table, column, value });
          if (column === "workspace_id") {
            matchedWorkspace = value === "workspace-1";
          }
          if (table === "raw_sources" && column === "id") {
            matchedId = value === fixtureSource.id;
          }
          return query;
        },
        order: () => query,
        maybeSingle: async () =>
          queryState.sourceError
            ? { data: null, error: queryState.sourceError }
            : table === "raw_sources" && matchedWorkspace && matchedId
              ? { data: fixtureSource, error: null }
              : { data: null, error: null },
        then: (resolve: (val: unknown) => unknown) => {
          if (table === "source_chunks") {
            return resolve(
              queryState.chunksError
                ? { data: null, error: queryState.chunksError }
                : { data: matchedWorkspace ? [fixtureChunk] : [], error: null },
            );
          }
          if (table === "wiki_pages") {
            return resolve(
              queryState.wikiError
                ? { data: null, error: queryState.wikiError }
                : {
                    data: matchedWorkspace ? fixtureWikiPages : [],
                    error: null,
                  },
            );
          }
          return resolve({ data: null, error: null });
        },
      };
      return query;
    },
  })),
}));

import SourceDetailRoute from "@/app/w/[workspaceId]/sources/[id]/page";

describe("SourceDetailRoute", () => {
  beforeEach(() => {
    queryState.eqCalls.length = 0;
    queryState.sourceError = null;
    queryState.chunksError = null;
    queryState.wikiError = null;
    vi.spyOn(console, "error").mockImplementation(() => undefined);
  });

  it("scopes every query and passes the visible source trace to the detail component", async () => {
    const result = await SourceDetailRoute({
      params: Promise.resolve({
        workspaceId: "workspace-1",
        id: fixtureSource.id,
      }),
    });
    const props = (
      result as {
        props: {
          workspaceId: string;
          source: { title: string };
          chunks: { id: string }[];
          citingPages: { slug: string }[];
        };
      }
    ).props;

    expect(props.source.title).toBe(fixtureSource.title);
    expect(props.workspaceId).toBe("workspace-1");
    expect(props.chunks).toEqual([fixtureChunk]);
    expect(props.citingPages).toEqual([
      {
        id: "wiki-1",
        title: "인용 문서",
        slug: "citing-page",
        category: "guides",
      },
    ]);
    for (const table of ["raw_sources", "source_chunks", "wiki_pages"]) {
      expect(queryState.eqCalls).toContainEqual({
        table,
        column: "workspace_id",
        value: "workspace-1",
      });
    }
    expect(queryState.eqCalls).toContainEqual({
      table: "source_chunks",
      column: "raw_source_id",
      value: fixtureSource.id,
    });
  });

  it.each([
    ["unknown id", "workspace-1", "missing-source"],
    ["another workspace", "workspace-2", fixtureSource.id],
  ])(
    "returns the same not-found state for %s",
    async (_case, workspaceId, id) => {
      const result = await SourceDetailRoute({
        params: Promise.resolve({ workspaceId, id }),
      });

      expect((result as { props: { children: string } }).props.children).toBe(
        "자료를 찾을 수 없습니다",
      );
    },
  );

  it.each(["source", "chunks", "wiki"] as const)(
    "shows a load error instead of an empty state when the %s query fails",
    async (target) => {
      const error = { code: "PGRST500", message: `${target} failed` };
      if (target === "source") queryState.sourceError = error;
      if (target === "chunks") queryState.chunksError = error;
      if (target === "wiki") queryState.wikiError = error;

      const result = await SourceDetailRoute({
        params: Promise.resolve({
          workspaceId: "workspace-1",
          id: fixtureSource.id,
        }),
      });

      expect((result as { props: { children: string } }).props.children).toBe(
        "자료를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.",
      );
      expect(console.error).toHaveBeenCalled();
    },
  );
});
