import { beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  user: { id: "user-1" } as { id: string } | null,
  inserts: [] as Array<Record<string, string>>,
  results: [] as Array<{
    data: { id: string } | null;
    error: { code?: string } | null;
  }>,
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: async () => ({
    auth: { getUser: async () => ({ data: { user: state.user } }) },
    from: () => ({
      insert: (record: Record<string, string>) => {
        state.inserts.push(record);
        return {
          select: () => ({
            single: async () =>
              state.results.shift() ?? { data: null, error: null },
          }),
        };
      },
    }),
  }),
}));

import { createPersonalWorkspace } from "@/app/onboarding-actions";

describe("createPersonalWorkspace", () => {
  beforeEach(() => {
    state.user = { id: "user-1" };
    state.inserts = [];
    state.results = [];
  });

  it("personal workspace를 요청자 owner로 생성한다", async () => {
    state.results.push({ data: { id: "ws-1" }, error: null });

    await expect(createPersonalWorkspace("나의 위키")).resolves.toEqual({
      workspaceId: "ws-1",
    });
    expect(state.inserts).toEqual([
      {
        name: "나의 위키",
        slug: "나의-위키",
        kind: "personal",
        owner_id: "user-1",
      },
    ]);
  });

  it("전역 slug 충돌이면 숫자 접미사로 재시도한다", async () => {
    state.results.push(
      { data: null, error: { code: "23505" } },
      { data: { id: "ws-2" }, error: null },
    );

    await expect(createPersonalWorkspace("나의 위키")).resolves.toEqual({
      workspaceId: "ws-2",
    });
    expect(state.inserts.map(({ slug }) => slug)).toEqual([
      "나의-위키",
      "나의-위키-2",
    ]);
  });

  it("1~100자 밖의 이름은 삽입하지 않는다", async () => {
    await expect(createPersonalWorkspace(" ")).resolves.toEqual({
      error: "이름은 1~100자여야 합니다.",
    });
    await expect(createPersonalWorkspace("가".repeat(101))).resolves.toEqual({
      error: "이름은 1~100자여야 합니다.",
    });
    expect(state.inserts).toEqual([]);
  });
});
