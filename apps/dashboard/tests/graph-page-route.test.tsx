import { beforeEach, describe, expect, it, vi } from "vitest";

const redirectMock = vi.fn();
vi.mock("next/navigation", () => ({
  redirect: (url: string) => redirectMock(url),
}));

import GraphPage from "@/app/w/[workspaceId]/graph/page";

describe("GraphPage", () => {
  beforeEach(() => {
    redirectMock.mockReset();
  });

  it("redirects into the unified workspace viewer's graph tab", async () => {
    await GraphPage({
      params: Promise.resolve({ workspaceId: "workspace-1" }),
    });

    expect(redirectMock).toHaveBeenCalledWith("/w/workspace-1/ask?tab=graph");
  });
});
