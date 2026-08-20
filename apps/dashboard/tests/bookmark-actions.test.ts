import { beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  user: { id: "user-1" } as { id: string } | null,
  existing: null as { wiki_id: string } | null,
  inserts: [] as Array<Record<string, string>>,
  deletes: [] as string[],
  insertError: null as { message: string } | null,
  deleteError: null as { message: string } | null,
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: async () => ({
    auth: { getUser: async () => ({ data: { user: state.user } }) },
    from: () => ({
      select: () => ({
        eq: () => ({
          maybeSingle: async () => ({ data: state.existing, error: null }),
        }),
      }),
      delete: () => ({
        eq: (_col: string, wikiId: string) => {
          state.deletes.push(wikiId);
          return { error: state.deleteError };
        },
      }),
      insert: async (record: Record<string, string>) => {
        state.inserts.push(record);
        return { error: state.insertError };
      },
    }),
  }),
}));

import { toggleWikiBookmark } from "@/app/bookmark-actions";

describe("toggleWikiBookmark", () => {
  beforeEach(() => {
    state.user = { id: "user-1" };
    state.existing = null;
    state.inserts = [];
    state.deletes = [];
    state.insertError = null;
    state.deleteError = null;
  });

  it("로그인하지 않았으면 오류를 반환한다", async () => {
    state.user = null;

    await expect(toggleWikiBookmark("wiki-1", "ws-1")).resolves.toEqual({
      error: "로그인이 필요합니다.",
    });
    expect(state.inserts).toEqual([]);
  });

  it("즐겨찾기가 없으면 추가한다", async () => {
    state.existing = null;

    await expect(toggleWikiBookmark("wiki-1", "ws-1")).resolves.toEqual({
      bookmarked: true,
    });
    expect(state.inserts).toEqual([
      { user_id: "user-1", wiki_id: "wiki-1", workspace_id: "ws-1" },
    ]);
    expect(state.deletes).toEqual([]);
  });

  it("이미 즐겨찾기돼 있으면 해제한다", async () => {
    state.existing = { wiki_id: "wiki-1" };

    await expect(toggleWikiBookmark("wiki-1", "ws-1")).resolves.toEqual({
      bookmarked: false,
    });
    expect(state.deletes).toEqual(["wiki-1"]);
    expect(state.inserts).toEqual([]);
  });

  it("추가 실패 시 오류를 반환하고 상태를 바꾸지 않는다", async () => {
    state.existing = null;
    state.insertError = { message: "insert failed" };

    await expect(toggleWikiBookmark("wiki-1", "ws-1")).resolves.toEqual({
      error: "즐겨찾기에 추가하지 못했습니다.",
    });
  });

  it("해제 실패 시 오류를 반환한다", async () => {
    state.existing = { wiki_id: "wiki-1" };
    state.deleteError = { message: "delete failed" };

    await expect(toggleWikiBookmark("wiki-1", "ws-1")).resolves.toEqual({
      error: "즐겨찾기를 해제하지 못했습니다.",
    });
  });
});
