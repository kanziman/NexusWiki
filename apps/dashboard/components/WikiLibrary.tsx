"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { workspacePath } from "@/lib/workspace-path";

export type WikiLibraryPage = {
  id: string;
  slug: string;
  title: string;
  category: string;
  content: string;
  verification_status: string;
  disputed: boolean;
};
const categories = ["concepts", "entities", "guides", "maps"];
const labels: Record<string, string> = {
  concepts: "개념",
  entities: "항목",
  guides: "가이드",
  maps: "맵",
};

function stateLabel(page: WikiLibraryPage) {
  if (page.disputed) return "충돌 감지";
  if (page.verification_status === "verified") return "검증됨";
  if (page.verification_status === "partial") return "부분 검증";
  return "검증 필요";
}

function preview(content: string) {
  return content
    .replace(/\[\[([^\]]+)\]\]/g, "$1")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 150);
}

export function WikiLibrary({
  pages,
  workspaceId,
}: {
  pages: WikiLibraryPage[];
  workspaceId: string;
}) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const visible = useMemo(
    () =>
      pages.filter(
        (page) =>
          (!category || page.category === category) &&
          `${page.title} ${preview(page.content)}`
            .toLocaleLowerCase()
            .includes(query.toLocaleLowerCase()),
      ),
    [category, pages, query],
  );
  return (
    <section className="mx-auto flex w-full max-w-4xl flex-col gap-xl">
      <header className="flex flex-col gap-sm">
        <div className="flex items-baseline justify-between gap-base">
          <h1
            className="text-ink"
            style={{ font: "600 28px/1.2 var(--font-family-base)" }}
          >
            위키
          </h1>
          <span className="text-muted" style={{ font: "var(--font-body-sm)" }}>
            {pages.length}개 문서
          </span>
        </div>
        <p className="text-body" style={{ font: "var(--font-body-md)" }}>
          팀의 소스에서 컴파일된 지식 문서입니다.
        </p>
      </header>
      <div className="flex flex-col gap-sm">
        <input
          aria-label="위키 문서 검색"
          className="nw-input h-12 px-base text-ink"
          placeholder="제목이나 내용으로 검색"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <div className="flex flex-wrap gap-xs" aria-label="카테고리 필터">
          <button
            type="button"
            aria-pressed={category === null}
            className="nw-focus-ring rounded-full border border-hairline px-base py-sm text-ink"
            onClick={() => setCategory(null)}
          >
            전체
          </button>
          {categories.map((item) => (
            <button
              key={item}
              type="button"
              aria-pressed={category === item}
              className="nw-focus-ring rounded-full border border-hairline px-base py-sm text-ink"
              onClick={() => setCategory(category === item ? null : item)}
            >
              {labels[item]}
            </button>
          ))}
        </div>
      </div>
      {visible.length ? (
        <ul className="divide-y divide-hairline border-y border-hairline">
          {visible.map((page) => (
            <li key={page.id}>
              <Link
                className="nw-focus-ring block py-lg hover:bg-surface-soft"
                href={`${workspacePath(workspaceId)}/wiki/${page.slug}`}
              >
                <div className="flex flex-wrap items-center gap-sm">
                  <h2
                    className="text-ink"
                    style={{ font: "var(--font-title-md)" }}
                  >
                    {page.title}
                  </h2>
                  <span
                    className="text-muted"
                    style={{ font: "var(--font-caption-sm)" }}
                  >
                    {labels[page.category] ?? page.category} ·{" "}
                    {stateLabel(page)}
                  </span>
                </div>
                <p
                  className="mt-xs line-clamp-2 text-body"
                  style={{ font: "var(--font-body-sm)" }}
                >
                  {preview(page.content)}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="rounded-sm bg-surface-soft p-lg text-body" role="status">
          조건에 맞는 위키 문서가 없습니다.
        </p>
      )}
    </section>
  );
}
