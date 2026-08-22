import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: (...args: unknown[]) => apiFetch(...args) };
});

import {
  RETRIEVAL_CHANNELS,
  RetrievalDebugViewer,
  type RetrievalResponse,
} from "@/components/RetrievalDebugViewer";
import { ApiError } from "@/lib/api-client";

function responseFixture(): RetrievalResponse {
  return {
    evidence: [
      {
        id: "wiki-b",
        kind: "wiki",
        document_id: "doc-b",
        channels: ["wiki_vector"],
        contributions: { wiki_vector: 0.01 },
        metadata: { title: "두 번째 문서" },
      },
      {
        id: "source-a",
        kind: "source",
        document_id: "doc-a",
        channels: ["source_vector", "source_lexical"],
        contributions: { source_vector: 0.012, source_lexical: 0.011 },
        metadata: { chunk_index: 2 },
      },
    ],
    meta: {
      policy_version: "hybrid-rrf-v1",
      elapsed_ms: 12.345,
      wiki_vector: {
        status: "ok",
        returned: 1,
        elapsed_ms: 2.1,
        raw_hit_ids: ["wiki-b"],
      },
      source_vector: {
        status: "ok",
        returned: 1,
        elapsed_ms: 3.2,
        raw_hit_ids: ["source-a"],
      },
      wiki_lexical: {
        status: "failed",
        returned: 0,
        elapsed_ms: 1.4,
        error_code: "rpc_unavailable",
      },
      source_lexical: {
        status: "ok",
        returned: 1,
        elapsed_ms: 2.8,
        raw_hit_ids: ["source-a"],
      },
    },
  };
}

describe("RetrievalDebugViewer", () => {
  beforeEach(() => {
    apiFetch.mockReset();
  });

  it("빈 질의는 네트워크 요청 없이 인라인 에러로 표시한다", () => {
    render(<RetrievalDebugViewer workspaceId="ws-1" />);

    fireEvent.click(screen.getByRole("button", { name: "검색 실행" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "질의를 입력해 주세요.",
    );
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("선택한 requested_k와 요청자 세션용 apiFetch 경로로 질의한다", async () => {
    apiFetch.mockResolvedValue(responseFixture());
    render(<RetrievalDebugViewer workspaceId="ws/1" />);

    fireEvent.change(screen.getByLabelText("질의"), {
      target: { value: "  검색 품질  " },
    });
    fireEvent.change(screen.getByLabelText("결과 수"), {
      target: { value: "3" },
    });
    fireEvent.click(screen.getByRole("button", { name: "검색 실행" }));

    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1));
    expect(apiFetch).toHaveBeenCalledWith("/workspaces/ws%2F1/retrieval", {
      method: "POST",
      body: { query: "검색 품질", requested_k: 3 },
    });
    expect(screen.getByText("hybrid-rrf-v1")).toBeInTheDocument();
  });

  it("4개 채널 카드를 유지하고 실패·0건 상태를 숨기지 않는다", async () => {
    apiFetch.mockResolvedValue(responseFixture());
    render(<RetrievalDebugViewer workspaceId="ws-1" />);

    fireEvent.change(screen.getByLabelText("질의"), {
      target: { value: "검색" },
    });
    fireEvent.click(screen.getByRole("button", { name: "검색 실행" }));

    await screen.findByRole("heading", { name: "채널별 원시 결과" });
    const rawSection = screen
      .getByRole("heading", { name: "채널별 원시 결과" })
      .closest("section");
    expect(rawSection).not.toBeNull();
    for (const channel of RETRIEVAL_CHANNELS) {
      expect(within(rawSection!).getByText(channel)).toBeInTheDocument();
    }
    expect(
      within(rawSection!).getByText("채널을 사용할 수 없음"),
    ).toBeInTheDocument();
    expect(
      within(rawSection!).getByText("rpc_unavailable"),
    ).toBeInTheDocument();
  });

  it("contribution 합계로 융합 순서를 다시 정렬한다", async () => {
    apiFetch.mockResolvedValue(responseFixture());
    render(<RetrievalDebugViewer workspaceId="ws-1" />);

    fireEvent.change(screen.getByLabelText("질의"), {
      target: { value: "검색" },
    });
    fireEvent.click(screen.getByRole("button", { name: "검색 실행" }));

    const table = await screen.findByRole("table");
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent("doc-a");
    expect(rows[0]).toHaveTextContent("0.023000");
    expect(rows[1]).toHaveTextContent("doc-b");
  });

  it("알 수 없는 채널 키와 ApiError.detail을 그대로 드러낸다", async () => {
    const unknown = responseFixture();
    unknown.meta.experimental = { status: "ok", returned: 0 };
    unknown.evidence[0].channels.push("experimental");
    unknown.evidence[0].contributions.experimental = 0.002;
    apiFetch
      .mockResolvedValueOnce(unknown)
      .mockRejectedValueOnce(new ApiError(403, "forbidden"));
    render(<RetrievalDebugViewer workspaceId="ws-1" />);

    fireEvent.change(screen.getByLabelText("질의"), {
      target: { value: "검색" },
    });
    fireEvent.click(screen.getByRole("button", { name: "검색 실행" }));
    await screen.findByText(/알 수 없는 채널:/);
    expect(
      screen.getByText("experimental", { selector: "code" }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "검색 실행" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("forbidden");
  });
});
