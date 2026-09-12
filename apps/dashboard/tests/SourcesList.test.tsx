import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/Dropzone", () => ({
  Dropzone: () => <div data-testid="dropzone" />,
}));

vi.mock("@/components/JobStepper", () => ({
  JobStepper: () => <div data-testid="job-stepper" />,
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: vi.fn(),
}));

import { SourcesList } from "@/components/SourcesList";

describe("SourcesList", () => {
  it("preserves the approved empty-state copy and renders inline Dropzone", () => {
    render(<SourcesList workspaceId="ws-1" initialSources={[]} />);

    expect(screen.getByText("아직 등록된 소스가 없습니다")).toBeInTheDocument();
    expect(
      screen.getByText(
        "파일을 드래그하거나 URL/텍스트를 붙여넣어 첫 소스를 추가하세요.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("empty-sources-dropzone-container"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("dropzone")).toBeInTheDocument();
  });

  it("keeps a truncated source title available to assistive technology", () => {
    const title =
      "A very long research source title that must remain available";
    render(
      <SourcesList
        workspaceId="ws-1"
        initialSources={[
          {
            id: "source-1",
            title,
            source_type: "text",
            created_at: "2026-08-12T00:00:00Z",
            content_hash: "hash-1",
          },
        ]}
      />,
    );

    const sourceTitle = screen.getByText(title);
    expect(sourceTitle).toHaveAttribute("title", title);
    expect(sourceTitle).toHaveAttribute("aria-label", title);
    expect(sourceTitle.closest("a")).toHaveAttribute(
      "href",
      "/w/ws-1/sources/source-1",
    );
    // ⚠️ `getAllByText`로 느슨하게 풀지 않는다. 이 날짜가 화면에 **정확히 한 번**
    //    나오는 것이 계약이다 — 30일이 지나 상대 표기가 절대 날짜로 접히면
    //    "2026년 8월 12일 · 2026년 8월 12일"이 되어 여기서 잡혀야 한다.
    expect(screen.getByText("2026년 8월 12일")).toBeInTheDocument();
  });

  it("30일이 지난 소스는 같은 날짜를 두 번 찍지 않는다", () => {
    // 실제로 배포돼 있던 버그다. `formatRelativeTime`이 30일을 넘으면 조용히
    // `formatDate`로 접히는데 그 옆에 절대 일자를 또 붙이고 있었다.
    const created = new Date(Date.now() - 90 * 86_400_000).toISOString();
    const absolute = new Date(created).toLocaleDateString("ko-KR", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });

    render(
      <SourcesList
        workspaceId="ws-1"
        initialSources={[
          {
            id: "source-1",
            title: "오래된 원문",
            source_type: "text",
            created_at: created,
            content_hash: "hash-1",
          },
        ]}
      />,
    );

    expect(screen.getAllByText(absolute)).toHaveLength(1);
  });

  it("파일명 링크가 소스 상세로 가고 별도 상세 보기 링크는 두지 않는다", () => {
    render(
      <SourcesList
        workspaceId="ws-1"
        initialSources={[
          {
            id: "source-1",
            title: "회의록",
            source_type: "text",
            created_at: "2026-08-12T00:00:00Z",
            content_hash: "hash-1",
          },
        ]}
      />,
    );

    expect(screen.getByRole("link", { name: "회의록" })).toHaveAttribute(
      "href",
      "/w/ws-1/sources/source-1",
    );
    expect(
      screen.queryByRole("link", { name: "상세 보기" }),
    ).not.toBeInTheDocument();
  });

  it("openUpload이면 업로드 모달을 연다", () => {
    render(
      <SourcesList
        workspaceId="ws-1"
        initialSources={[
          {
            id: "source-1",
            title: "회의록",
            source_type: "text",
            created_at: "2026-08-12T00:00:00Z",
            content_hash: "hash-1",
          },
        ]}
        openUpload
      />,
    );

    expect(
      screen.getByRole("dialog", { name: "소스 업로드" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "소스 업로드" })).toBeNull();
  });

  it("filters sources by MIME type tabs", () => {
    const sampleSources = [
      {
        id: "source-1",
        title: "설계문서.pdf",
        source_type: "file",
        mime_type: "application/pdf",
        created_at: "2026-08-12T00:00:00Z",
        content_hash: "hash-1",
      },
      {
        id: "source-2",
        title: "노트.md",
        source_type: "text",
        mime_type: "text/markdown",
        created_at: "2026-08-13T00:00:00Z",
        content_hash: "hash-2",
      },
    ];

    render(<SourcesList workspaceId="ws-1" initialSources={sampleSources} />);

    expect(screen.getByText("설계문서.pdf")).toBeInTheDocument();
    expect(screen.getByText("노트.md")).toBeInTheDocument();

    const pdfTab = screen.getByRole("tab", { name: /PDF/ });
    fireEvent.click(pdfTab);

    expect(screen.getByText("설계문서.pdf")).toBeInTheDocument();
    expect(screen.queryByText("노트.md")).not.toBeInTheDocument();

    const textTab = screen.getByRole("tab", { name: /텍스트\/마크다운/ });
    fireEvent.click(textTab);

    expect(screen.queryByText("설계문서.pdf")).not.toBeInTheDocument();
    expect(screen.getByText("노트.md")).toBeInTheDocument();
  });

  describe("파이프라인 요약 벤토", () => {
    const bentoSources = [
      {
        id: "source-1",
        title: "인용된 문서.md",
        source_type: "text",
        mime_type: "text/markdown",
        byte_size: 2048,
        created_at: "2026-08-12T00:00:00Z",
        content_hash: "hash-1",
      },
      {
        id: "source-2",
        title: "고아 문서.pdf",
        source_type: "file",
        mime_type: "application/pdf",
        created_at: "2026-08-13T00:00:00Z",
        content_hash: "hash-2",
      },
    ];

    const bentoChunkStats = {
      "source-1": { count: 5, charStart: 0, charEnd: 1444 },
    };

    const bentoCitingPages = {
      "source-1": [{ title: "트라이브스", slug: "tribes" }],
    };

    it("네 지표가 로드된 소스·청크·인용 관계와 일치한다", () => {
      render(
        <SourcesList
          workspaceId="ws-1"
          initialSources={bentoSources}
          chunkStats={bentoChunkStats}
          citingPages={bentoCitingPages}
        />,
      );

      const bento = within(screen.getByLabelText("파이프라인 요약"));
      expect(bento.getByText("개 문서")).toBeInTheDocument();
      expect(bento.queryByText("텍스트·마크다운 1")).not.toBeInTheDocument();
      expect(
        screen.getByRole("tab", { name: /텍스트\/마크다운 1/ }),
      ).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /PDF 1/ })).toBeInTheDocument();
      // 생성된 청크
      expect(bento.getByText("1/2 소스 청킹 완료")).toBeInTheDocument();
      // 인용 연결률 — 인용 0건 소스가 있으므로 100% 미만이어야 한다.
      // 파이프라인 카드도 진행률 50%를 쓸 수 있어 인용 칸만 본다.
      const citationCard = bento.getByText("위키 인용 연결률").closest("div")
        ?.parentElement as HTMLElement;
      expect(within(citationCard).getByText("50%")).toBeInTheDocument();
      expect(bento.queryByText(/인용됨 \(/)).not.toBeInTheDocument();
      expect(
        bento.getByText("아직 인용되지 않은 소스 1개"),
      ).toBeInTheDocument();
      // 파이프라인
      expect(bento.getByText("파이프라인 상태")).toBeInTheDocument();
      expect(bento.getByText("처리 진행 중")).toBeInTheDocument();
      expect(bento.getByText("청킹 대기 1개")).toBeInTheDocument();
    });

    it("실패한(dead) 잡이 있으면 파이프라인 상태 카드에 오류 경고를 표시한다", () => {
      render(
        <SourcesList
          workspaceId="ws-1"
          initialSources={bentoSources}
          chunkStats={bentoChunkStats}
          citingPages={bentoCitingPages}
          deadJobCount={3}
        />,
      );

      const bento = within(screen.getByLabelText("파이프라인 요약"));
      expect(bento.getByText("파이프라인 상태")).toBeInTheDocument();
      expect(bento.getByText("오류 발생")).toBeInTheDocument();
      expect(bento.getByText("파이프라인 실패 (3건)")).toBeInTheDocument();
      expect(
        bento.getByText("실패한 작업의 재시도 또는 오류 확인 필요"),
      ).toBeInTheDocument();
      // 정상 상태의 백분율이나 완료 배지가 노출되지 않는다
      expect(bento.queryByText("전 소스 처리 완료")).not.toBeInTheDocument();
    });

    it("잡 상태 조회가 실패하면 거짓 정상이 아닌 집계 불가 문구를 표시한다", () => {
      render(
        <SourcesList
          workspaceId="ws-1"
          initialSources={bentoSources}
          chunkStats={bentoChunkStats}
          citingPages={bentoCitingPages}
          deadJobsUnavailable={true}
        />,
      );

      const bento = within(screen.getByLabelText("파이프라인 요약"));
      expect(bento.getByText("파이프라인 상태")).toBeInTheDocument();
      expect(bento.getByText("집계를 불러오지 못했습니다")).toBeInTheDocument();
      expect(bento.queryByText("전 소스 처리 완료")).not.toBeInTheDocument();
      expect(bento.queryByText("오류 발생")).not.toBeInTheDocument();
    });

    it("청크 합계는 목록에 남은 소스에서만 파생된다", () => {
      // chunkStats 에 목록에 없는 소스가 섞여 있어도 합계에 들어가면 안 된다 —
      // 삭제된 소스의 청크가 요약에만 남아 행과 모순되는 상태가 된다.
      render(
        <SourcesList
          workspaceId="ws-1"
          initialSources={bentoSources}
          chunkStats={{
            ...bentoChunkStats,
            "deleted-source": { count: 99, charStart: 0, charEnd: 10 },
          }}
          citingPages={bentoCitingPages}
        />,
      );

      const bento = within(screen.getByLabelText("파이프라인 요약"));
      expect(bento.getByText("5")).toBeInTheDocument();
      expect(bento.queryByText("104")).not.toBeInTheDocument();
    });

    it("소스가 없으면 벤토를 렌더하지 않는다", () => {
      render(<SourcesList workspaceId="ws-1" initialSources={[]} />);

      expect(
        screen.queryByLabelText("파이프라인 요약"),
      ).not.toBeInTheDocument();
      expect(
        screen.getByTestId("empty-sources-dropzone-container"),
      ).toBeInTheDocument();
    });

    it("집계 조회가 실패하면 단정 대신 집계 불가를 표시한다", () => {
      render(
        <SourcesList
          workspaceId="ws-1"
          initialSources={bentoSources}
          chunkStats={{}}
          citingPages={{}}
          citingPagesUnavailable
        />,
      );

      // 인용 집계가 실패했으므로 "고아 소스" 단정을 하면 안 된다
      const bento = within(screen.getByLabelText("파이프라인 요약"));
      expect(bento.queryByText(/고아 소스/)).not.toBeInTheDocument();
      expect(bento.queryByText(/인용됨 \(/)).not.toBeInTheDocument();
      expect(bento.queryByText("50%")).not.toBeInTheDocument();
      expect(
        bento.getAllByText("집계를 불러오지 못했습니다").length,
      ).toBeGreaterThan(0);
      expect(
        screen.getAllByText("인용 정보를 불러오지 못했습니다").length,
      ).toBe(2);
      // 실패한 집계에 의존하지 않는 값은 그대로 보인다
      expect(bento.getByText("개 문서")).toBeInTheDocument();
    });

    it("청크 집계가 실패하면 청크·파이프라인 칸이 단정하지 않는다", () => {
      render(
        <SourcesList
          workspaceId="ws-1"
          initialSources={bentoSources}
          chunkStats={{}}
          citingPages={bentoCitingPages}
          chunkStatsUnavailable
        />,
      );

      const bento = within(screen.getByLabelText("파이프라인 요약"));
      // 청크가 0건인 것처럼 보이거나 청킹이 끝난 것처럼 단정하면 안 된다
      expect(bento.queryByText("전 소스 청킹 완료")).not.toBeInTheDocument();
      expect(bento.queryByText(/소스 청킹 완료$/)).not.toBeInTheDocument();
      expect(bento.queryByText("0%")).not.toBeInTheDocument();
      expect(bento.getAllByText("집계를 불러오지 못했습니다")).toHaveLength(2);
      // 행의 청크 열도 "청크 없음"으로 단정하지 않는다
      expect(screen.queryByText("청크 없음")).not.toBeInTheDocument();
      expect(screen.getAllByText("집계 불가")).toHaveLength(2);
      // 청크 집계와 무관한 인용 값은 그대로 보인다
      expect(bento.getByText("50%")).toBeInTheDocument();
    });
  });

  it("인용 위키가 많아도 제목 하나와 잔여 개수만 렌더한다", () => {
    render(
      <SourcesList
        workspaceId="ws-1"
        initialSources={[
          {
            id: "source-1",
            title: "다중 인용 문서.md",
            source_type: "text",
            mime_type: "text/markdown",
            created_at: "2026-08-12T00:00:00Z",
            content_hash: "hash-1",
          },
        ]}
        citingPages={{
          "source-1": [
            { title: "위키 하나", slug: "one" },
            { title: "위키 둘", slug: "two" },
            { title: "위키 셋", slug: "three" },
            { title: "위키 넷", slug: "four" },
          ],
        }}
      />,
    );

    expect(screen.getByText("위키 하나")).toBeInTheDocument();
    expect(screen.queryByText("위키 둘")).not.toBeInTheDocument();
    expect(screen.queryByText("위키 셋")).not.toBeInTheDocument();
    expect(screen.getByText("+3")).toBeInTheDocument();
  });

  it("byte_size가 없으면 크기를 자리표시자 없이 생략한다", () => {
    render(
      <SourcesList
        workspaceId="ws-1"
        initialSources={[
          {
            id: "source-1",
            title: "크기 있는 문서.md",
            source_type: "text",
            byte_size: 2048,
            created_at: "2026-08-12T00:00:00Z",
            content_hash: "hash-1",
          },
          {
            id: "source-2",
            title: "크기 없는 문서.md",
            source_type: "text",
            created_at: "2026-08-12T00:00:00Z",
            content_hash: "hash-2",
          },
        ]}
      />,
    );

    expect(screen.getByText("2.0 KB")).toBeInTheDocument();
    // 두 행 모두 상대 시각과 절대 일자를 함께 노출한다
    expect(screen.getAllByText("2026년 8월 12일")).toHaveLength(2);
  });

  it("8개 초과의 소스가 등록된 경우 페이지당 8개씩 페이지네이션한다", () => {
    const manySources = Array.from({ length: 12 }, (_, i) => ({
      id: `source-${i + 1}`,
      title: `문서 ${i + 1}.txt`,
      source_type: "text",
      mime_type: "text/plain",
      created_at: "2026-08-12T00:00:00Z",
      content_hash: `hash-${i + 1}`,
    }));

    render(<SourcesList workspaceId="ws-1" initialSources={manySources} />);

    // 1페이지 항목(1~8) 확인
    expect(screen.getByText("문서 1.txt")).toBeInTheDocument();
    expect(screen.getByText("문서 8.txt")).toBeInTheDocument();
    expect(screen.queryByText("문서 9.txt")).not.toBeInTheDocument();

    // 2페이지로 이동
    const page2Button = screen.getByRole("button", { name: "2 페이지" });
    fireEvent.click(page2Button);

    expect(screen.queryByText("문서 1.txt")).not.toBeInTheDocument();
    expect(screen.getByText("문서 9.txt")).toBeInTheDocument();
    expect(screen.getByText("문서 12.txt")).toBeInTheDocument();
  });
});
