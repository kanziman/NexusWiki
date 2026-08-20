import { beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  user: { id: "user-1" } as { id: string } | null,
  upserts: [] as Array<{
    record: Record<string, string>;
    options: Record<string, unknown>;
  }>,
  deletes: [] as string[],
  upsertError: null as { message: string } | null,
  deleteError: null as { message: string } | null,
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: async () => ({
    auth: { getUser: async () => ({ data: { user: state.user } }) },
    from: () => ({
      upsert: async (
        record: Record<string, string>,
        options: Record<string, unknown>,
      ) => {
        state.upserts.push({ record, options });
        return { error: state.upsertError };
      },
      delete: () => ({
        eq: (_col: string, wikiId: string) => {
          state.deletes.push(wikiId);
          return { error: state.deleteError };
        },
      }),
    }),
  }),
}));

import { setWikiBookmark } from "@/app/bookmark-actions";

describe("setWikiBookmark", () => {
  beforeEach(() => {
    state.user = { id: "user-1" };
    state.upserts = [];
    state.deletes = [];
    state.upsertError = null;
    state.deleteError = null;
  });

  it("로그인하지 않았으면 오류를 반환한다", async () => {
    state.user = null;

    await expect(setWikiBookmark("wiki-1", "ws-1", true)).resolves.toEqual({
      error: "로그인이 필요합니다.",
    });
    expect(state.upserts).toEqual([]);
  });

  it("bookmarked=true면 upsert(ignoreDuplicates)로 추가한다", async () => {
    await expect(setWikiBookmark("wiki-1", "ws-1", true)).resolves.toEqual({
      bookmarked: true,
    });

    expect(state.upserts).toEqual([
      {
        record: { user_id: "user-1", wiki_id: "wiki-1", workspace_id: "ws-1" },
        options: { onConflict: "user_id,wiki_id", ignoreDuplicates: true },
      },
    ]);
    expect(state.deletes).toEqual([]);
  });

  it("bookmarked=false면 delete로 제거한다", async () => {
    await expect(setWikiBookmark("wiki-1", "ws-1", false)).resolves.toEqual({
      bookmarked: false,
    });

    expect(state.deletes).toEqual(["wiki-1"]);
    expect(state.upserts).toEqual([]);
  });

  it("이미 존재해도(같은 (user_id, wiki_id)) upsert가 충돌 없이 성공한다", async () => {
    // ignoreDuplicates: true라 두 번 연달아 추가해도(레이스로 두 탭이
    // 동시에 같은 요청을 보내도) 둘 다 성공으로 끝난다 — 23505를 던지지
    // 않는다는 게 이 옵션의 요점이라 mock도 항상 성공만 반환한다.
    await setWikiBookmark("wiki-1", "ws-1", true);
    await expect(setWikiBookmark("wiki-1", "ws-1", true)).resolves.toEqual({
      bookmarked: true,
    });
  });

  it("추가 실패 시 오류를 반환한다", async () => {
    state.upsertError = { message: "upsert failed" };

    await expect(setWikiBookmark("wiki-1", "ws-1", true)).resolves.toEqual({
      error: "즐겨찾기에 추가하지 못했습니다.",
    });
  });

  it("해제 실패 시 오류를 반환한다", async () => {
    state.deleteError = { message: "delete failed" };

    await expect(setWikiBookmark("wiki-1", "ws-1", false)).resolves.toEqual({
      error: "즐겨찾기를 해제하지 못했습니다.",
    });
  });
});
