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

  it("홈 스켈레톤은 벤토 메트릭 4칸과 비대칭 지식 그리드 골격을 쓴다", () => {
    render(<WorkspaceHomeLoading />);
    const skeleton = screen.getByTestId("workspace-home-skeleton");
    const metrics = screen.getByTestId("workspace-home-metric-skeleton");
    const grid = screen.getByTestId("workspace-home-grid-skeleton");

    expect(skeleton.querySelector(".stats")).toBeNull();
    expect(metrics).toHaveClass("grid", "grid-cols-2", "lg:grid-cols-4");
    expect(metrics.children).toHaveLength(4);
    expect(grid).toHaveClass("sections");
    expect(grid.children).toHaveLength(2);
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

  it("위키 라이브러리 스켈레톤은 벤토 5칸과 카드 행 골격을 쓴다", () => {
    render(<WikiLibraryLoading />);
    const skeleton = screen.getByTestId("wiki-library-loading-skeleton");
    const health = screen.getByTestId("wiki-library-health-skeleton");

    expect(skeleton.querySelector(".stats")).toBeNull();
    expect(health.children).toHaveLength(5);
    expect(skeleton.querySelectorAll(".wiki-card")).toHaveLength(5);
  });

  it("위키 문서 상세 리더 스켈레톤을 정상적으로 렌더링한다", () => {
    render(<WikiDetailLoading />);
    const skeleton = screen.getByTestId("wiki-detail-loading-skeleton");
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveAttribute("aria-busy", "true");
  });
});
