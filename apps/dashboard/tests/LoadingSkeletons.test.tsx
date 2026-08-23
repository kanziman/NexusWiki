import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import WorkspaceHomeLoading from "@/app/w/[workspaceId]/loading";
import SourcesLoading from "@/app/w/[workspaceId]/sources/loading";
import WikiLibraryLoading from "@/app/w/[workspaceId]/wiki/loading";
import WikiDetailLoading from "@/app/w/[workspaceId]/wiki/[slug]/loading";

describe("Loading Skeletons", () => {
  it("홈 대시보드 스켈레톤을 정상적으로 렌더링한다", () => {
    render(<WorkspaceHomeLoading />);
    const skeleton = screen.getByTestId("workspace-home-skeleton");
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveAttribute("aria-busy", "true");
  });

  it("원문 소스 관리 스켈레톤을 정상적으로 렌더링한다", () => {
    render(<SourcesLoading />);
    const skeleton = screen.getByTestId("sources-loading-skeleton");
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveAttribute("aria-busy", "true");
  });

  it("위키 라이브러리 스켈레톤을 정상적으로 렌더링한다", () => {
    render(<WikiLibraryLoading />);
    const skeleton = screen.getByTestId("wiki-library-loading-skeleton");
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveAttribute("aria-busy", "true");
  });

  it("위키 문서 상세 리더 스켈레톤을 정상적으로 렌더링한다", () => {
    render(<WikiDetailLoading />);
    const skeleton = screen.getByTestId("wiki-detail-loading-skeleton");
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveAttribute("aria-busy", "true");
  });
});
