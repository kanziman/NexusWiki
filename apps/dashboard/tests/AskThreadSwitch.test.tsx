import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const sseFrames = vi.fn();
vi.mock("@/lib/sse", () => ({
  parseSseStream: (...args: unknown[]) => sseFrames(...args),
}));

const searchParamsMock = vi.hoisted(() => ({
  value: new URLSearchParams(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => searchParamsMock.value,
}));

const apiFetch = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api-client", () => ({
  apiFetch: (...args: unknown[]) => apiFetch(...args),
  ApiError: class ApiError extends Error {
    status = 0;
    detail = "";
  },
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: {
      getSession: () =>
        Promise.resolve({ data: { session: { access_token: "test-token" } } }),
    },
    from: () => ({
      select: () => ({
        eq: () => ({
          or: () => Promise.resolve({ data: [] }),
        }),
      }),
    }),
  }),
}));

import { AskConversation } from "@/components/AskConversation";

async function* toAsyncGenerator<T>(items: T[]): AsyncGenerator<T> {
  for (const item of items) {
    yield item;
  }
}

describe("AskThreadSwitch", () => {
  beforeEach(() => {
    searchParamsMock.value = new URLSearchParams();
    process.env.NEXT_PUBLIC_API_URL = "http://api.test";
    apiFetch.mockResolvedValue([]);
    global.fetch = vi.fn().mockResolvedValue({ ok: true } as Response);
    sseFrames.mockReturnValue(
      toAsyncGenerator([
        { event: "meta", data: {} },
        { event: "delta", data: { text: "진행 중" } },
        { event: "citations", data: { text: "진행 중", resolved: [] } },
        { event: "done", data: { thread_id: "t-live" } },
      ]),
    );
  });

  it("새 대화를 열면 빈 상태 문구가 다시 보이고 진행 중 fetch는 abort하지 않는다", async () => {
    const abortSpy = vi.fn();
    render(<AskConversation workspaceId="ws-1" />);

    fireEvent.change(screen.getByLabelText("질문"), {
      target: { value: "진행 중 질문" },
    });
    fireEvent.click(screen.getByRole("button", { name: "질문하기" }));

    await waitFor(() => {
      expect(screen.getByText("진행 중 질문")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "대화 목록 열기" }));
    fireEvent.click(screen.getByRole("button", { name: "새 대화" }));

    expect(screen.getByText("무엇이든 물어보세요")).toBeInTheDocument();
    expect(abortSpy).not.toHaveBeenCalled();
    expect(global.fetch).toHaveBeenCalled();
    const body = JSON.parse(
      String((global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body),
    );
    expect(body.client_turn_id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
  });
});
