import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import {
  landingPublicWikis,
  publicWikiHref,
  type PublicWikiShowcase,
} from "@/components/public-landing/content";

function WorkspaceCard({ wiki }: { wiki: PublicWikiShowcase }) {
  const featuredHref = publicWikiHref(wiki.workspaceSlug, wiki.featured.slug);

  return (
    <article className="flex min-h-full min-w-0 flex-col rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-5 md:p-6">
      <div className="mb-5 flex items-baseline justify-between gap-3">
        <h3 className="text-base font-extrabold tracking-tight text-[var(--fg)]">
          {wiki.workspace}
        </h3>
        <p className="shrink-0 text-[12px] text-[var(--muted)]">
          공개 문서 {wiki.docCount}편
        </p>
      </div>

      <Link
        href={featuredHref}
        className="nw-focus-ring group mb-6 block min-w-0"
      >
        <p className="mb-1 text-[12px] font-semibold text-[var(--accent)]">
          대표 문서
        </p>
        <p className="mb-2 inline-flex max-w-full items-start gap-1 text-[17px] font-bold leading-snug text-[var(--fg)] group-hover:text-[var(--accent)]">
          <span>{wiki.featured.title}</span>
          <ArrowUpRight
            size={16}
            aria-hidden="true"
            className="mt-0.5 shrink-0 opacity-50 group-hover:opacity-100"
          />
        </p>
        <p className="line-clamp-3 text-sm leading-relaxed text-[var(--muted)]">
          {wiki.featured.excerpt}
        </p>
      </Link>

      <div className="mt-auto border-t border-[var(--border)] pt-4">
        <p className="mb-2 text-[12px] font-semibold text-[var(--muted)]">
          다른 문서
        </p>
        <ul className="flex flex-col gap-1">
          {wiki.related.map((page) => (
            <li key={page.slug}>
              <Link
                href={publicWikiHref(wiki.workspaceSlug, page.slug)}
                className="nw-focus-ring group/item inline-flex max-w-full items-center gap-1 rounded-md text-sm text-[var(--muted)] hover:text-[var(--accent)] hover:underline"
              >
                <span className="truncate">{page.title}</span>
                <ArrowUpRight
                  size={13}
                  aria-hidden="true"
                  className="shrink-0 opacity-40 group-hover/item:opacity-100"
                />
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </article>
  );
}

export function PublicLandingShowcase() {
  return (
    <section
      id="showcase"
      aria-labelledby="showcase-heading"
      className="mx-auto mb-24 max-w-5xl scroll-mt-28 px-4 sm:px-6"
    >
      <div className="mb-8 max-w-prose">
        <h2
          id="showcase-heading"
          className="mb-2 text-2xl font-extrabold tracking-tight md:text-3xl"
        >
          공개된 지식 워크스페이스
        </h2>
        <p className="text-base leading-relaxed text-[var(--muted)]">
          실제로 발행된 위키입니다. 원문에서 컴파일된 문서를 바로 읽을 수
          있습니다.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 md:gap-5">
        {landingPublicWikis.map((wiki) => (
          <WorkspaceCard key={wiki.workspaceSlug} wiki={wiki} />
        ))}
      </div>
    </section>
  );
}
