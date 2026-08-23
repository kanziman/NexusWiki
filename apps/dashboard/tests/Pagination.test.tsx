import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Pagination } from "@/components/Pagination";

describe("Pagination", () => {
  it("총 항목이 1페이지 분량(8개 이하)일 때는 페이지네이션을 렌더링하지 않는다", () => {
    const { container } = render(
      <Pagination
        currentPage={1}
        totalItems={6}
        pageSize={8}
        onPageChange={vi.fn()}
      />,
    );

    expect(container.firstChild).toBeNull();
  });

  it("여러 페이지가 있을 때 항목 범위와 페이지 번호들을 정상 렌더링한다", () => {
    render(
      <Pagination
        currentPage={1}
        totalItems={24}
        pageSize={8}
        onPageChange={vi.fn()}
      />,
    );

    expect(screen.getByText(/총/)).toBeInTheDocument();
    expect(screen.getByText("24")).toBeInTheDocument();
    expect(screen.getByText("1–8")).toBeInTheDocument();

    expect(screen.getByRole("button", { name: "1 페이지" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(
      screen.getByRole("button", { name: "2 페이지" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "3 페이지" }),
    ).toBeInTheDocument();

    // 1페이지에서는 이전 버튼이 비활성화된다
    expect(screen.getByRole("button", { name: "이전 페이지" })).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "다음 페이지" }),
    ).not.toBeDisabled();
  });

  it("페이지 번호나 다음 버튼 클릭 시 onPageChange가 올바르게 호출된다", async () => {
    const user = userEvent.setup();
    const handlePageChange = vi.fn();

    render(
      <Pagination
        currentPage={1}
        totalItems={20}
        pageSize={8}
        onPageChange={handlePageChange}
      />,
    );

    await user.click(screen.getByRole("button", { name: "2 페이지" }));
    expect(handlePageChange).toHaveBeenCalledWith(2);

    await user.click(screen.getByRole("button", { name: "다음 페이지" }));
    expect(handlePageChange).toHaveBeenCalledWith(2);
  });

  it("마지막 페이지에서는 다음 버튼이 비활성화된다", () => {
    render(
      <Pagination
        currentPage={3}
        totalItems={24}
        pageSize={8}
        onPageChange={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("button", { name: "이전 페이지" }),
    ).not.toBeDisabled();
    expect(screen.getByRole("button", { name: "다음 페이지" })).toBeDisabled();
    expect(screen.getByText("17–24")).toBeInTheDocument();
  });
});
