import { describe, expect, it, vi } from "vitest";

import {
  isExpired,
  publishWikiPage,
  sourceIds,
  unpublishWikiPage,
} from "@/lib/wiki-publication";

describe("wiki-publication", () => {
  it("keeps only non-empty string source ids", () => {
    expect(sourceIds(["a", "", 1, null, "b"])).toEqual(["a", "b"]);
    expect(sourceIds(null)).toEqual([]);
  });

  it("treats past timestamps as expired", () => {
    expect(isExpired("2000-01-01T00:00:00Z")).toBe(true);
    expect(isExpired(null)).toBe(false);
  });

  it("upserts a snapshot for a verified page", async () => {
    const upsert = vi.fn(async () => ({ data: null, error: null }));
    const supabase = {
      from: (table: string) => {
        if (table === "wiki_pages") {
          return {
            select: () => ({
              eq: () => ({
                eq: () => ({
                  single: async () => ({
                    data: {
                      slug: "job-lifecycle",
                      title: "Job",
                      content: "본문",
                      sources: [],
                      verification_status: "verified",
                      expires_at: null,
                      disputed: false,
                    },
                    error: null,
                  }),
                }),
              }),
            }),
          };
        }
        if (table === "wiki_page_publications") {
          return { upsert };
        }
        throw new Error(table);
      },
    };

    await expect(
      publishWikiPage(supabase as never, {
        workspaceId: "ws-1",
        wikiId: "wiki-1",
        userId: "user-1",
      }),
    ).resolves.toEqual({ published_slug: "job-lifecycle" });
    expect(upsert).toHaveBeenCalledWith(
      expect.objectContaining({
        wiki_page_id: "wiki-1",
        workspace_id: "ws-1",
        published_slug: "job-lifecycle",
        published_by: "user-1",
        published_citations: [],
      }),
      { onConflict: "wiki_page_id" },
    );
  });

  it("rejects delete when supabase reports an error", async () => {
    const supabase = {
      from: () => ({
        delete: () => ({
          eq: () => ({
            eq: async () => ({
              data: null,
              error: { message: "forbidden" },
            }),
          }),
        }),
      }),
    };
    await expect(
      unpublishWikiPage(supabase as never, {
        workspaceId: "ws-1",
        wikiId: "wiki-1",
      }),
    ).rejects.toThrow("unpublish_forbidden");
  });
});
