import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/sse", () => ({
  parseSseStream: async function* () {
    /* empty */
  },
}));

const searchParamsMock = vi.hoisted(() => ({
  value: new URLSearchParams(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => searchParamsMock.value,
}));

const { apiFetch, MockApiError } = vi.hoisted(() => {
  class MockApiError extends Error {
    status: number;
    detail: string;
    constructor(status: number, detail: string) {
      super(detail);
      this.status = status;
      this.detail = detail;
    }
  }
  return { apiFetch: vi.fn(), MockApiError };
});

vi.mock("@/lib/api-client", () => ({
  apiFetch: (...args: unknown[]) => apiFetch(...args),
  ApiError: MockApiError,
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
import {
  notifyAskThreadsChanged,
  subscribeAskThreadsChanged,
} from "@/lib/ask-threads-events";

describe("AskThreadLifecycle", () => {
  beforeEach(() => {
    searchParamsMock.value = new URLSearchParams({ thread: "gone-id" });
    process.env.NEXT_PUBLIC_API_URL = "http://api.test";
    vi.stubGlobal(
      "prompt",
      vi.fn(() => "바뀐 제목"),
    );
    apiFetch.mockImplementation(
      async (
        path: string,
        init?: { method?: string; body?: { title?: string } },
      ) => {
        if (path.endsWith("/ask/threads") && !init?.method) {
          return [
            {
              id: "thread-1",
              title: "원래 제목",
              created_at: "2026-08-23T00:00:00Z",
              updated_at: "2026-08-23T00:00:00Z",
            },
          ];
        }
        if (path.endsWith("/ask/threads/gone-id")) {
          throw new MockApiError(403, "forbidden");
        }
        if (
          path.endsWith("/ask/threads/thread-1") &&
          init?.method === "PATCH"
        ) {
          return {
            id: "thread-1",
            title: init.body?.title,
            created_at: "2026-08-23T00:00:00Z",
            updated_at: "2026-08-23T00:01:00Z",
          };
        }
        if (
          path.endsWith("/ask/threads/thread-1") &&
          init?.method === "DELETE"
        ) {
          return {
            id: "thread-1",
            title: "원래 제목",
            created_at: "2026-08-23T00:00:00Z",
            updated_at: "2026-08-23T00:00:00Z",
          };
        }
        return [];
      },
    );
  });

  it("삭제된 딥링크는 notice와 새 대화를 보여주고 이름 변경·삭제가 동작한다", async () => {
    render(<AskConversation workspaceId="ws-1" />);

    expect(await screen.findByTestId("thread-gone")).toHaveTextContent(
      "삭제된 대화입니다.",
    );

    fireEvent.click(screen.getByRole("button", { name: "대화 목록 열기" }));
    expect(await screen.findByText("원래 제목")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "원래 제목 대화 이름 바꾸기" }),
    );
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/workspaces/ws-1/ask/threads/thread-1",
        expect.objectContaining({
          method: "PATCH",
          body: { title: "바뀐 제목" },
        }),
      );
    });

    fireEvent.click(
      screen.getByRole("button", { name: "바뀐 제목 대화 옵션" }),
    );
    expect(
      screen.getByText(
        "삭제: '바뀐 제목' 대화를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.",
      ),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "삭제" }));
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/workspaces/ws-1/ask/threads/thread-1",
        expect.objectContaining({ method: "DELETE" }),
      );
    });
  });

  it("이름 변경과 삭제를 사이드바에 알린다", async () => {
    const changed = vi.fn();
    const unsubscribe = subscribeAskThreadsChanged("sidebar", changed);
    render(<AskConversation workspaceId="ws-1" />);

    fireEvent.click(screen.getByRole("button", { name: "대화 목록 열기" }));
    fireEvent.click(
      await screen.findByRole("button", { name: "원래 제목 대화 이름 바꾸기" }),
    );
    await waitFor(() => expect(changed).toHaveBeenCalledTimes(1));

    fireEvent.click(
      await screen.findByRole("button", { name: "바뀐 제목 대화 옵션" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "삭제" }));
    await waitFor(() => expect(changed).toHaveBeenCalledTimes(2));

    unsubscribe();
  });

  it("사이드바가 대화를 바꾸면 서랍 목록을 다시 불러온다", async () => {
    render(<AskConversation workspaceId="ws-1" />);
    fireEvent.click(screen.getByRole("button", { name: "대화 목록 열기" }));
    expect(await screen.findByText("원래 제목")).toBeInTheDocument();

    apiFetch.mockImplementation(async () => [
      {
        id: "thread-1",
        title: "사이드바에서 바꾼 제목",
        created_at: "2026-08-23T00:00:00Z",
        updated_at: "2026-08-23T00:01:00Z",
      },
    ]);
    act(() => notifyAskThreadsChanged("sidebar"));

    expect(
      await screen.findByText("사이드바에서 바꾼 제목"),
    ).toBeInTheDocument();
  });
});
