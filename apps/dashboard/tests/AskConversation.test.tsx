import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// parseSseStream만 모킹한다 — AskConversation은 이 파서가 내보내는 이벤트
// 순서(meta -> delta* -> citations -> done)로만 상태 기계를 구동하므로,
// 실제 fetch/ReadableStream을 흉내 낼 필요가 없다.
const sseFrames = vi.fn();
vi.mock("@/lib/sse", () => ({
  parseSseStream: (...args: unknown[]) => sseFrames(...args),
}));

// CitationSidePanel은 Task 3의 책임(직접 PostgREST 조회)이라 여기서는 얇은
// 스텁으로 대체하고, AskConversation이 정확한 {kind,id}로 열었는지만 확인한다.
vi.mock("@/components/CitationSidePanel", () => ({
  CitationSidePanel: ({
    part,
    onClose,
  }: {
    part: { kind: string; id?: string } | null;
    onClose: () => void;
  }) =>
    part ? (
      <div data-testid="side-panel" onClick={onClose}>
        {part.kind}:{part.id}
      </div>
    ) : null,
}));

function makeQueryBuilder(result: { data: unknown; error?: unknown }) {
  const builder: Record<string, unknown> = {
    select: () => builder,
    eq: () => builder,
    or: () => builder,
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
    from: () => makeQueryBuilder({ data: [] }),
  }),
}));

import { AskConversation } from "@/components/AskConversation";

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
  beforeEach(() => {
    sseFrames.mockReset();
    // 06-REVIEW.md WR-02 fix: AskConversation이 SSE 루프에 들어가기 전에
    // response.ok를 확인하므로, 기존 성공 경로 테스트들이 계속 통과하려면
    // 목 fetch도 ok:true를 흉내내야 한다.
    global.fetch = vi.fn().mockResolvedValue({ ok: true } as Response);
  });

  it("빈 대화에서는 empty-state 문구를 렌더링한다", () => {
    render(<AskConversation workspaceId="ws-1" />);
    expect(screen.getByText("무엇이든 물어보세요")).toBeInTheDocument();
    expect(
      screen.getByText(
        "워크스페이스에 등록된 소스와 위키에서 답을 찾아드립니다.",
      ),
    ).toBeInTheDocument();
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

  it("citations.error(budget_exceeded)는 no-evidence 카드와 구분되는 에러 카드를 재시도 버튼과 함께 렌더링한다", async () => {
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
    expect(screen.queryByTestId("no-evidence-card")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "재시도" })).toBeInTheDocument();
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

  it("citations 이벤트 도착 후에만 마커가 번호 붙은 클릭 가능 링크로 바뀌고, 클릭하면 정확한 {kind,id}로 사이드 패널을 연다", async () => {
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

    const panel = await screen.findByTestId("side-panel");
    expect(panel).toHaveTextContent("source:chunk-uuid-1");
  });
});
