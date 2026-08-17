"use client";

export type CategoryLensFilterProps = {
  activeCategory: string | null;
  onSelectCategory: (category: string | null) => void;
  counts?: {
    all?: number;
    concepts?: number;
    entities?: number;
    guides?: number;
    maps?: number;
  };
};

const LENSES = [
  { id: null, label: "전체", key: "all" },
  { id: "concepts", label: "개념", key: "concepts" },
  { id: "entities", label: "엔티티", key: "entities" },
  { id: "guides", label: "가이드", key: "guides" },
  { id: "maps", label: "맵", key: "maps" },
] as const;

export function CategoryLensFilter({
  activeCategory,
  onSelectCategory,
  counts = {},
}: CategoryLensFilterProps) {
  return (
    <div
      className="flex flex-wrap items-center gap-xs"
      role="tablist"
      aria-label="카테고리 렌즈 필터"
    >
      {LENSES.map(({ id, label, key }) => {
        const isActive =
          activeCategory === id || (id === null && !activeCategory);
        const count = counts[key as keyof typeof counts];

        return (
          <button
            key={label}
            type="button"
            role="tab"
            aria-selected={isActive}
            className={`badge ${isActive ? "accent" : ""} transition-colors cursor-pointer py-1 px-2.5 text-xs font-semibold`}
            onClick={() => onSelectCategory(id)}
          >
            <span>{label}</span>
            {typeof count === "number" && (
              <span className="ml-1 opacity-70 font-mono text-[10px]">
                {String(count).padStart(2, "0")}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
