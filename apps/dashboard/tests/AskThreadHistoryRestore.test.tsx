import { render, screen, waitFor } from "@testing-library/react";
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
    status: number;
    detail: string;
    constructor(status: number, detail: string) {
      super(detail);
      this.status = status;
      this.detail = detail;
    }
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
          eq: () => ({
            single: () => Promise.resolve({ data: null }),
          }),
        }),
      }),
    }),
  }),
}));

import { AskConversation } from "@/components/AskConversation";

describe("AskThreadHistoryRestore", () => {
  beforeEach(() => {
    searchParamsMock.value = new URLSearchParams({ thread: "thread-1" });
    process.env.NEXT_PUBLIC_API_URL = "http://api.test";
    apiFetch.mockImplementation(async (path: string) => {
      if (path.endsWith("/ask/threads")) {
        return [
          {
            id: "thread-1",
            title: "이중 인용 질문",
            created_at: "2026-08-23T00:00:00Z",
            updated_at: "2026-08-23T00:00:00Z",
          },
        ];
      }
      if (path.endsWith("/ask/threads/thread-1")) {
        return {
          id: "thread-1",
          title: "이중 인용 질문",
          created_at: "2026-08-23T00:00:00Z",
          updated_at: "2026-08-23T00:00:00Z",
          messages: [
            {
              id: "m1",
              client_turn_id: "c1",
              question: "이중 인용은?",
              answer_text: "위키 [[wiki:w1]] 원문 [[src:s1]]",
              citations: {
                text: "위키 [[wiki:w1]] 원문 [[src:s1]]",
                resolved: [
                  { alias: "w1", kind: "wiki", id: "wiki-1" },
                  { alias: "s1", kind: "source", id: "chunk-1" },
                ],
              },
              status: "resolved",
              created_at: "2026-08-23T00:00:00Z",
            },
          ],
        };
      }
      return [];
    });
  });

  it("저장된 스레드를 열면 위키·원문 마커가 클릭 가능한 상태로 복원된다", async () => {
    render(<AskConversation workspaceId="ws-1" />);

    await waitFor(() => {
      expect(screen.getByText("이중 인용은?")).toBeInTheDocument();
    });
    const markers = screen.getAllByTestId("citation-marker-resolved");
    expect(markers).toHaveLength(2);
    expect(markers[0]).toHaveAttribute("data-kind", "wiki");
    expect(markers[1]).toHaveAttribute("data-kind", "source");
    expect(
      screen.queryByTestId("citation-marker-placeholder"),
    ).not.toBeInTheDocument();
    expect(screen.getByText("저장된 답변")).toBeInTheDocument();
  });

  it("저장된 no-evidence 턴은 placeholder 없이 경고 카드로 복원된다", async () => {
    apiFetch.mockImplementation(async (path: string) => {
      if (path.endsWith("/ask/threads")) return [];
      if (path.endsWith("/ask/threads/thread-1")) {
        return {
          id: "thread-1",
          title: "무근거",
          created_at: "2026-08-23T00:00:00Z",
          updated_at: "2026-08-23T00:00:00Z",
          messages: [
            {
              id: "m-empty",
              client_turn_id: "c-empty",
              question: "없는 내용?",
              answer_text: "근거를 찾지 못했습니다.",
              citations: { text: "근거를 찾지 못했습니다.", resolved: [] },
              status: "no-evidence",
              created_at: "2026-08-23T00:00:00Z",
            },
          ],
        };
      }
      return [];
    });

    render(<AskConversation workspaceId="ws-1" />);
    expect(await screen.findByTestId("no-evidence-card")).toHaveTextContent(
      "근거를 찾지 못했습니다.",
    );
    expect(
      screen.queryByTestId("citation-marker-placeholder"),
    ).not.toBeInTheDocument();
  });

  it("저장된 error 턴은 placeholder 없이 재시도 카드로 복원된다", async () => {
    apiFetch.mockImplementation(async (path: string) => {
      if (path.endsWith("/ask/threads")) return [];
      if (path.endsWith("/ask/threads/thread-1")) {
        return {
          id: "thread-1",
          title: "오류",
          created_at: "2026-08-23T00:00:00Z",
          updated_at: "2026-08-23T00:00:00Z",
          messages: [
            {
              id: "m-err",
              client_turn_id: "c-err",
              question: "실패 질문",
              answer_text: "",
              citations: { text: "", resolved: [] },
              status: "error",
              created_at: "2026-08-23T00:00:00Z",
            },
          ],
        };
      }
      return [];
    });

    render(<AskConversation workspaceId="ws-1" />);
    expect(await screen.findByTestId("ask-error-card")).toHaveTextContent(
      "질문에 답하지 못했습니다. 잠시 후 다시 시도해주세요.",
    );
    expect(screen.getByRole("button", { name: "재시도" })).toBeInTheDocument();
    expect(
      screen.queryByTestId("citation-marker-placeholder"),
    ).not.toBeInTheDocument();
  });
});
