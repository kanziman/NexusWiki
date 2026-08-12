"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

export type GraphLensFilterProps = {
  workspaceId: string;
  activeCategory: string | null;
};

// UI-06 렌즈 필터: wiki_pages.category(0001) CHECK가 고정한 4값을 그대로
// 재사용한다 — 새 분류 체계를 만들지 않는다 (PROJECT.md "렌즈 필터는
// wiki_pages.category 재사용").
const CATEGORY_OPTIONS: { value: string; label: string }[] = [
  { value: "concepts", label: "개념" },
  { value: "entities", label: "엔티티" },
  { value: "guides", label: "가이드" },
  { value: "maps", label: "맵" },
];

// "전체" 상태는 별도 칩이 아니라 activeCategory === null인 암묵 상태다 —
// 이미 활성인 칩을 다시 누르면 이 상태로 되돌아간다 (Task 2 <action>).
export function GraphLensFilter({
  workspaceId: _workspaceId,
  activeCategory,
}: GraphLensFilterProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function handleToggle(category: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (activeCategory === category) {
      params.delete("category");
    } else {
      params.set("category", category);
    }
    const query = params.toString();
    router.push(query ? `${pathname}?${query}` : pathname);
  }

  return (
    <div role="group" aria-label="카테고리 필터" className="flex gap-sm">
      {CATEGORY_OPTIONS.map((option) => {
        const isActive = activeCategory === option.value;

        return (
          <button
            key={option.value}
            type="button"
            data-active={isActive ? "true" : undefined}
            aria-pressed={isActive}
            onClick={() => handleToggle(option.value)}
            className={`rounded-full border px-base py-sm transition-colors ${
              isActive
                ? "border-primary bg-primary text-on-primary"
                : "border-border-strong bg-canvas text-ink"
            }`}
            style={{ font: "var(--font-caption)" }}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
