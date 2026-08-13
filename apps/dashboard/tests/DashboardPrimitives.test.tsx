import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  EmptyState,
  PageHeader,
  StatusBadge,
} from "@/components/DashboardPrimitives";

describe("DashboardPrimitives", () => {
  it("provides a consistent heading, state text, and optional action", () => {
    render(
      <>
        <PageHeader
          title="자료"
          description="설명"
          action={<button type="button">추가</button>}
        />
        <StatusBadge tone="warning">검증 필요</StatusBadge>
        <EmptyState title="비어 있음" detail="다음 행동" />
      </>,
    );
    expect(screen.getByRole("heading", { name: "자료" })).toBeInTheDocument();
    expect(screen.getByText("검증 필요")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "추가" })).toBeInTheDocument();
  });
});
