import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// parseSseStream만 모킹한다 — AskConversation은 이 파서가 내보내는 이벤트
// 순서(meta -> delta* -> citations -> done)로만 상태 기계를 구동하므로,
// 실제 fetch/ReadableStream을 흉내 낼 필요가 없다.
const sseFrames = vi.fn();
vi.mock("@/lib/sse", () => ({
  parseSseStream: (...args: unknown[]) => sseFrames(...args),
}));

// D-03/GraphLensFilter.test.tsx와 같은 패턴 — 인용 마커 클릭이 이제
// CitationSidePanel 대신 router.push로 ContentViewer 쿼리 파라미터를
// 바꾸므로, push 호출 인자를 직접 관찰한다.
const push = vi.fn();
const searchParamsMock = vi.hoisted(() => ({
  value: new URLSearchParams(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  useSearchParams: () => searchParamsMock.value,
}));

// wiki_pages 조회(handleMarkerClick의 wiki-kind 분기)가 workspace_id로
// 스코프됐는지 직접 관찰할 수 있도록 .eq() 호출 인자를 기록한다.
const wikiLookupCalls = vi.fn();
const wikiLookupResult: { current: { data: { slug: string } | null } } = {
  current: { data: null },
};

function makeQueryBuilder(
  table: string,
  result: { data: unknown; error?: unknown },
) {
  const builder: Record<string, unknown> = {
    select: () => builder,
    eq: (column: string, value: string) => {
      if (table === "wiki_pages") wikiLookupCalls(column, value);
      return builder;
    },
    or: () => builder,
    single: () =>
      Promise.resolve(
        table === "wiki_pages"
          ? { data: wikiLookupResult.current.data, error: null }
          : result,
      ),
    then: (resolve: (value: typeof result) => void) =>
      Promise.resolve(result).then(resolve),
  };
  return builder;
}

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: {
      getSession: () =>
        Promise.resolve({ data: { session: { access_token: "test-token" } } }),
    },
    from: (table: string) => makeQueryBuilder(table, { data: [] }),
  }),
}));

vi.mock("@/lib/api-client", () => ({
  apiFetch: vi.fn().mockResolvedValue([]),
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

import { AskConversation } from "@/components/AskConversation";
import { apiFetch } from "@/lib/api-client";

async function* toAsyncGenerator<T>(items: T[]): AsyncGenerator<T> {
  for (const item of items) {
    yield item;
  }
}

async function askQuestion(text: string) {
  fireEvent.change(screen.getByLabelText("질문"), { target: { value: text } });
  fireEvent.click(screen.getByRole("button", { name: "질문하기" }));
}

describe("AskConversation", () => {
  const originalApiUrl = process.env.NEXT_PUBLIC_API_URL;

  beforeEach(() => {
    sseFrames.mockReset();
    push.mockReset();
    searchParamsMock.value = new URLSearchParams();
    wikiLookupCalls.mockReset();
    wikiLookupResult.current = { data: null };
    sessionStorage.clear();
    window.history.replaceState(null, "", "/");
    vi.mocked(apiFetch).mockResolvedValue([]);
    // 06-REVIEW.md WR-02 fix: AskConversation이 SSE 루프에 들어가기 전에
    // response.ok를 확인하므로, 기존 성공 경로 테스트들이 계속 통과하려면
    // 목 fetch도 ok:true를 흉내내야 한다.
    global.fetch = vi.fn().mockResolvedValue({ ok: true } as Response);
    // 06-REVIEW.md WR-05 fix: fetch URL 조립이 이제 requireEnv로 이 값의
    // 존재를 요구한다(api-client.test.ts와 같은 패턴).
    process.env.NEXT_PUBLIC_API_URL = "http://api.test";
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_API_URL = originalApiUrl;
  });

  it("URL 쿼리 파라미터(q)가 있으면 자동으로 질문을 제출하여 대화를 시작한다", async () => {
    searchParamsMock.value = new URLSearchParams({
      q: "RLS 격리 규칙이 무엇인가요?",
    });
    sseFrames.mockReturnValue(
      toAsyncGenerator([
        { event: "meta", data: {} },
        { event: "delta", data: { text: "RLS 격리 답변입니다." } },
        { event: "citations", data: { text: "RLS 격리 답변입니다." } },
        { event: "done", data: {} },
      ]),
    );

    render(<AskConversation workspaceId="ws-1" />);

    // 자동으로 첫 질문 버블이 렌더링되고 fetch가 호출됨
    await waitFor(() => {
      expect(
        screen.getByText("RLS 격리 규칙이 무엇인가요?"),
      ).toBeInTheDocument();
      expect(screen.getByText("RLS 격리 답변입니다.")).toBeInTheDocument();
    });
    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [, init] = vi.mocked(global.fetch).mock.calls[0] as [
      string,
      { body?: string },
    ];
    expect(JSON.parse(init.body ?? "{}")).not.toHaveProperty("template_id");
  });

  it("응답 헤더에서 진행 중 스레드를 세션과 URL에 즉시 기록하고 대화를 유지한다", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ "X-Ask-Thread-Id": "thread-streaming-1" }),
    } as Response);
    sseFrames.mockReturnValue(toAsyncGenerator([]));

    render(<AskConversation workspaceId="ws-1" />);
    await askQuestion("라우트를 떠나도 남나요?");

    await waitFor(() => {
      expect(sessionStorage.getItem("nexuswiki:active-ask-thread:ws-1")).toBe(
        "thread-streaming-1",
      );
      expect(window.location.pathname).toBe("/w/ws-1/ask");
      expect(window.location.search).toBe("?thread=thread-streaming-1");
      expect(screen.getByText("라우트를 떠나도 남나요?")).toBeInTheDocument();
    });
  });

  it("저장된 streaming 턴을 다시 열면 생성 중 상태로 복원한다", async () => {
    searchParamsMock.value = new URLSearchParams({
      thread: "thread-streaming-2",
    });
    vi.mocked(apiFetch).mockImplementation(async (path: string) => {
      if (path.endsWith("/threads/thread-streaming-2")) {
        return {
          id: "thread-streaming-2",
          title: "진행 중 질문",
          created_at: "2026-08-29T00:00:00Z",
          updated_at: "2026-08-29T00:00:00Z",
          messages: [
            {
              id: "message-1",
              client_turn_id: "turn-1",
              question: "진행 중인가요?",
              answer_text: "",
              citations: { text: "", resolved: [] },
              status: "streaming",
              created_at: "2026-08-29T00:00:00Z",
            },
          ],
        };
      }
      return [];
    });

    render(<AskConversation workspaceId="ws-1" />);

    expect(await screen.findByText("진행 중인가요?")).toBeInTheDocument();
    expect(screen.getByText("생성 중")).toBeInTheDocument();
    expect(sessionStorage.getItem("nexuswiki:active-ask-thread:ws-1")).toBe(
      "thread-streaming-2",
    );
  });

  it("빈 대화에서는 empty-state 문구를 렌더링한다", () => {
    render(<AskConversation workspaceId="ws-1" />);
    expect(screen.getByText("무엇이든 물어보세요")).toBeInTheDocument();
    expect(
      screen.getByText(
        "워크스페이스에 등록된 소스와 위키에서 답을 찾아드립니다.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("group", { name: "프롬프트 템플릿" }),
    ).not.toBeInTheDocument();
  });

  it("meta.no_evidence:true면 CITE-04 경고 카드를 정확한 문구로, 채팅 버블과 구분되게 렌더링한다", async () => {
    sseFrames.mockReturnValue(
      toAsyncGenerator([
        { event: "meta", data: { no_evidence: true } },
        {
          event: "citations",
          data: {
            text: "근거를 찾지 못했습니다.",
            resolved: [],
            cited_anchor_count: 0,
            fabricated_anchor_count: 0,
            dual_citation_rate: 0,
            unsourced_sentence_ratio: 0,
          },
        },
        { event: "done", data: {} },
      ]),
    );

    render(<AskConversation workspaceId="ws-1" />);
    await askQuestion("질문입니다");

    const card = await screen.findByTestId("no-evidence-card");
    expect(card).toHaveAttribute("data-variant", "warning");
    expect(card).toHaveTextContent("근거를 찾지 못했습니다.");
  });

  it("done 이벤트 없이 스트림이 끝나면(delta 이후 종료) 연결 끊김 문구를 정확히 렌더링하고 재시도 버튼을 노출한다", async () => {
    sseFrames.mockReturnValue(
      toAsyncGenerator([
        {
          event: "meta",
          data: { template_id: "t1", template_name: "기본", evidence_count: 2 },
        },
        { event: "delta", data: { text: "답변을 생성하는 중" } },
        // citations/done 없이 스트림이 종료된다.
      ]),
    );

    render(<AskConversation workspaceId="ws-1" />);
    await askQuestion("질문입니다");

    const card = await screen.findByTestId("stream-drop-card");
    expect(card).toHaveTextContent("연결이 끊어졌습니다. 다시 시도해주세요.");
    expect(screen.getByRole("button", { name: "재시도" })).toBeInTheDocument();
  });

  it("citations.error(budget_exceeded)는 no-evidence 카드와 구분되는 에러 카드를 사용량 확인 버튼과 함께 렌더링한다", async () => {
    sseFrames.mockReturnValue(
      toAsyncGenerator([
        { event: "meta", data: { template_id: "t1", evidence_count: 1 } },
        {
          event: "citations",
          data: { error: "budget_exceeded", resolved: [] },
        },
        { event: "done", data: {} },
      ]),
    );

    render(<AskConversation workspaceId="ws-1" />);
    await askQuestion("질문입니다");

    const errorCard = await screen.findByTestId("ask-error-card");
    expect(errorCard).toHaveAttribute("data-variant", "error");
    expect(errorCard).toHaveTextContent(
      "이번 달 무료 크레딧을 모두 소진했습니다.",
    );
    expect(screen.queryByTestId("no-evidence-card")).not.toBeInTheDocument();
    expect(
      screen.getByText("이번 달 무료 크레딧을 모두 소진했습니다"),
    ).toBeInTheDocument();
  });

  it("meta.missing_channels가 비어있지 않으면 인라인 안내 문구를 렌더링한다", async () => {
    sseFrames.mockReturnValue(
      toAsyncGenerator([
        {
          event: "meta",
          data: {
            template_id: "t1",
            evidence_count: 1,
            missing_channels: ["graph"],
          },
        },
        {
          event: "citations",
          data: { text: "답변입니다", resolved: [] },
        },
        { event: "done", data: {} },
      ]),
    );

    render(<AskConversation workspaceId="ws-1" />);
    await askQuestion("질문입니다");

    await waitFor(() =>
      expect(screen.getByTestId("missing-channels-notice")).toHaveTextContent(
        "일부 검색 채널을 사용할 수 없어 답변이 불완전할 수 있습니다.",
      ),
    );
  });

  it("citations 이벤트 도착 후에만 마커가 번호 붙은 클릭 가능 링크로 바뀌고, 클릭하면 ContentViewer의 source 탭으로 전환한다", async () => {
    sseFrames.mockReturnValue(
      toAsyncGenerator([
        { event: "meta", data: { template_id: "t1", evidence_count: 1 } },
        { event: "delta", data: { text: "본문 [[src:s1]] 끝" } },
        {
          event: "citations",
          data: {
            text: "본문 [[src:s1]] 끝",
            resolved: [{ alias: "s1", kind: "source", id: "chunk-uuid-1" }],
          },
        },
        { event: "done", data: {} },
      ]),
    );

    render(<AskConversation workspaceId="ws-1" />);
    await askQuestion("질문입니다");

    // 스트리밍 중에는 마커가 button이 아니라 비활성 placeholder다.
    // citations 이벤트가 처리된 뒤에야 번호 붙은 버튼(1)로 바뀐다.
    const marker = await screen.findByRole("button", { name: "1" });
    fireEvent.click(marker);

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith(
        "/w/ws-1/ask?chunkId=chunk-uuid-1&tab=source",
      ),
    );
  });

  it("wiki 마커 클릭 시 workspace_id로 스코프된 조회로 slug를 찾아 wiki 탭으로 전환한다", async () => {
    wikiLookupResult.current = { data: { slug: "meeting-notes" } };
    sseFrames.mockReturnValue(
      toAsyncGenerator([
        { event: "meta", data: { template_id: "t1", evidence_count: 1 } },
        { event: "delta", data: { text: "본문 [[wiki:w1]] 끝" } },
        {
          event: "citations",
          data: {
            text: "본문 [[wiki:w1]] 끝",
            resolved: [{ alias: "w1", kind: "wiki", id: "wiki-uuid-1" }],
          },
        },
        { event: "done", data: {} },
      ]),
    );

    render(<AskConversation workspaceId="ws-1" />);
    await askQuestion("질문입니다");

    const marker = await screen.findByRole("button", { name: "1" });
    fireEvent.click(marker);

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith(
        "/w/ws-1/ask?slug=meeting-notes&tab=wiki",
      ),
    );
    expect(wikiLookupCalls).toHaveBeenCalledWith("workspace_id", "ws-1");
    expect(wikiLookupCalls).toHaveBeenCalledWith("id", "wiki-uuid-1");
  });

  it("402 budget_exceeded 에러 시 에러 카드와 크레딧 한도 모달을 표시한다", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 402,
      text: () =>
        Promise.resolve(JSON.stringify({ detail: "budget_exceeded" })),
    } as unknown as Response);

    render(<AskConversation workspaceId="ws-1" />);
    await askQuestion("질문입니다");

    expect(
      await screen.findByText("이번 달 무료 크레딧을 모두 소진했습니다."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("이번 달 무료 크레딧을 모두 소진했습니다"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("ask-error-card")).toBeInTheDocument();
  });

  it("삭제되거나 접근할 수 없는 wiki 마커를 콘텐츠 뷰어의 안내 상태로 연결한다", async () => {
    wikiLookupResult.current = { data: null };
    sseFrames.mockReturnValue(
      toAsyncGenerator([
        { event: "meta", data: { template_id: "t1", evidence_count: 1 } },
        { event: "delta", data: { text: "본문 [[wiki:w1]] 끝" } },
        {
          event: "citations",
          data: {
            text: "본문 [[wiki:w1]] 끝",
            resolved: [{ alias: "w1", kind: "wiki", id: "deleted-wiki" }],
          },
        },
        { event: "done", data: {} },
      ]),
    );

    render(<AskConversation workspaceId="ws-1" />);
    await askQuestion("질문입니다");
    fireEvent.click(await screen.findByRole("button", { name: "1" }));

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith(
        "/w/ws-1/ask?tab=wiki&missingCitation=wiki",
      ),
    );
  });
});
