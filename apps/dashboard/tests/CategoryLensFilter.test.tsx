import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CategoryLensFilter } from "@/components/CategoryLensFilter";

describe("CategoryLensFilter", () => {
  it("renders 5 category tabs with labels", () => {
    const onSelect = vi.fn();
    render(
      <CategoryLensFilter
        activeCategory={null}
        onSelectCategory={onSelect}
        counts={{ all: 10, concepts: 4, entities: 2, guides: 3, maps: 1 }}
      />,
    );

    expect(screen.getByRole("tab", { name: /전체/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /개념/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /엔티티/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /가이드/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /맵/ })).toBeInTheDocument();
  });

  it("calls onSelectCategory when a tab is clicked", () => {
    const onSelect = vi.fn();
    render(
      <CategoryLensFilter activeCategory={null} onSelectCategory={onSelect} />,
    );

    const conceptsTab = screen.getByRole("tab", { name: /개념/ });
    fireEvent.click(conceptsTab);

    expect(onSelect).toHaveBeenCalledWith("concepts");
  });
});
