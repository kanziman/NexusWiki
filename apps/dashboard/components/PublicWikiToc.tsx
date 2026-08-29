"use client";

import { useEffect, useState } from "react";

import type { WikiHeading } from "@/lib/wiki-document";

type PublicWikiTocProps = {
  headings: WikiHeading[];
};

export function PublicWikiToc({ headings }: PublicWikiTocProps) {
  const [activeId, setActiveId] = useState<string | null>(
    headings[0]?.id ?? null,
  );

  useEffect(() => {
    if (headings.length === 0) return;

    function handleScroll() {
      const scrollPosition = window.scrollY + 100;
      let currentActive: string | null = null;
      for (const heading of headings) {
        const el = document.getElementById(heading.id);
        if (!el) continue;
        const top = el.getBoundingClientRect().top + window.scrollY;
        if (scrollPosition >= top) currentActive = heading.id;
      }
      if (currentActive) {
        setActiveId(currentActive);
      } else if (headings[0]) {
        setActiveId(headings[0].id);
      }
    }

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, [headings]);

  return (
    <>
      <div className="toc-heading">
        <h2>목차</h2>
      </div>
      {headings.length ? (
        <nav aria-label="이 문서에서" className="toc-list">
          {headings.map((heading) => {
            const indentClass =
              heading.level === 3
                ? "pl-4"
                : heading.level >= 4
                  ? "pl-6"
                  : "pl-2";
            return (
              <a
                key={heading.id}
                href={`#${heading.id}`}
                className={`${activeId === heading.id ? "active" : ""} ${indentClass} block py-1 text-[11px] leading-snug`}
              >
                {heading.title}
              </a>
            );
          })}
        </nav>
      ) : (
        <p className="m-0 text-[11px] text-[var(--muted)]">
          제목이 없는 문서입니다.
        </p>
      )}
    </>
  );
}
