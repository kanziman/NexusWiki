import Link from "next/link";
import React, { Fragment } from "react";

import { RedLinkCta } from "@/components/RedLinkCta";
import { safeMarkdownHref } from "@/lib/markdown-url";
import { workspacePath } from "@/lib/workspace-path";
import { resolveWikiLinks } from "@/lib/wiki-links";

export type WikiDocumentLink = { target_slug: string; resolved: boolean };

export type WikiDocumentBodyProps = {
  content: string;
  /**
   * `internal`은 워크스페이스 위키 링크로 해소한다.
   * `public`은 같은 조판을 쓰되 [[WikiLink]] 를 평문으로만 펼친다 — 공개
   * 표면에 /w/ 링크를 만들면 테넌트 식별자가 새어 나간다.
   */
  linkMode: "internal" | "public";
  links?: WikiDocumentLink[];
  workspaceId?: string;
};

export function WikiDocumentBody({
  content,
  linkMode,
  links = [],
  workspaceId = "",
}: WikiDocumentBodyProps) {
  if (!content) return null;

  const lines = content.split("\n");
  const nodes: React.ReactNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed) {
      index++;
      continue;
    }

    if (trimmed.startsWith("```")) {
      const lang = trimmed.slice(3).trim();
      const codeLines: string[] = [];
      index++;
      while (index < lines.length && !lines[index].trim().startsWith("```")) {
        codeLines.push(lines[index]);
        index++;
      }
      if (index < lines.length) {
        index++;
      }
      nodes.push(
        <div
          key={`code-${index}`}
          className="my-4 overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface)]"
        >
          {lang ? (
            <div className="border-b border-[var(--border)] bg-[var(--bg)] px-3.5 py-1.5 font-mono text-[10px] font-semibold text-[var(--muted)]">
              {lang}
            </div>
          ) : null}
          <pre
            className="overflow-x-auto p-3.5 font-mono text-xs leading-relaxed text-[var(--fg)]"
            spellCheck={false}
            lang="zxx"
            translate="no"
          >
            {codeLines.join("\n")}
          </pre>
        </div>,
      );
      continue;
    }

    if (trimmed.startsWith("|") && trimmed.includes("|", 1)) {
      const tableLines: string[] = [];
      while (
        index < lines.length &&
        lines[index].trim().startsWith("|") &&
        lines[index].trim().includes("|", 1)
      ) {
        tableLines.push(lines[index].trim());
        index++;
      }

      if (tableLines.length >= 2) {
        const headerCells = splitTableRow(tableLines[0]);
        const isDivider = tableLines[1]
          .split("|")
          .filter(Boolean)
          .every((cell) => /^[\s:-]+$/.test(cell));
        const bodyRows = (
          isDivider ? tableLines.slice(2) : tableLines.slice(1)
        ).map(splitTableRow);

        nodes.push(
          <div
            key={`table-${index}`}
            className="my-5 overflow-x-auto rounded-lg border border-[var(--border)] bg-[var(--bg)]"
          >
            <table className="w-full border-collapse text-left text-xs">
              <thead className="border-b border-[var(--border)] bg-[var(--surface)] text-[var(--fg)]">
                <tr>
                  {headerCells.map((cell, cIdx) => (
                    <th
                      key={cIdx}
                      className="px-3.5 py-2 font-semibold tracking-tight text-[var(--fg)]"
                    >
                      {renderRichText(cell, links, workspaceId, linkMode)}
                    </th>
                  ))}
                </tr>
              </thead>
              {bodyRows.length > 0 ? (
                <tbody className="divide-y divide-[var(--border)]">
                  {bodyRows.map((row, rIdx) => (
                    <tr
                      key={rIdx}
                      className="hover:bg-[var(--surface)]/40 transition-colors"
                    >
                      {row.map((cell, cIdx) => (
                        <td
                          key={cIdx}
                          className="px-3.5 py-2.5 align-top leading-6 text-[var(--fg)]"
                        >
                          {renderRichText(cell, links, workspaceId, linkMode)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              ) : null}
            </table>
          </div>,
        );
        continue;
      }
    }

    const headingMatch = /^(#{1,4})\s+(.+?)\s*$/.exec(line);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const title = headingMatch[2];
      const sectionId = `section-${index}`;
      const renderedTitle = renderRichText(title, links, workspaceId, linkMode);
      index++;

      if (level === 1) {
        nodes.push(
          <h2
            key={`h2-${index}`}
            id={sectionId}
            className="scroll-mt-20 mt-9 mb-3 pb-1.5 text-lg font-bold tracking-tight text-[var(--fg)] border-b border-[var(--border)]"
          >
            {renderedTitle}
          </h2>,
        );
      } else if (level === 2) {
        nodes.push(
          <h3
            key={`h3-${index}`}
            id={sectionId}
            className="scroll-mt-20 mt-7 mb-2 text-[15px] font-bold tracking-tight text-[var(--fg)]"
          >
            {renderedTitle}
          </h3>,
        );
      } else if (level === 3) {
        nodes.push(
          <h4
            key={`h4-${index}`}
            id={sectionId}
            className="scroll-mt-20 mt-5 mb-1.5 text-xs font-bold tracking-tight text-[var(--fg)]"
          >
            {renderedTitle}
          </h4>,
        );
      } else {
        nodes.push(
          <h5
            key={`h5-${index}`}
            id={sectionId}
            className="scroll-mt-20 mt-4 mb-1 text-[11px] font-bold uppercase tracking-wider text-[var(--muted)]"
          >
            {renderedTitle}
          </h5>,
        );
      }
      continue;
    }

    if (/^(\*\*\*|---|___)$/.test(trimmed)) {
      nodes.push(
        <hr
          key={`hr-${index}`}
          className="my-6 border-t border-[var(--border)]"
        />,
      );
      index++;
      continue;
    }

    if (trimmed.startsWith(">")) {
      const quoteLines: string[] = [];
      while (index < lines.length && lines[index].trim().startsWith(">")) {
        quoteLines.push(lines[index].trim().replace(/^>\s?/, ""));
        index++;
      }
      nodes.push(
        <blockquote
          key={`quote-${index}`}
          className="my-4 border-l-2 border-[var(--accent)] pl-4 pr-3 py-1 text-[13.5px] italic text-[var(--muted)] leading-relaxed break-words"
        >
          {quoteLines.map((ql, qIdx) => (
            <p
              key={qIdx}
              className={`${qIdx > 0 ? "mt-1.5" : "my-0"} break-words`}
            >
              {renderRichText(ql, links, workspaceId, linkMode)}
            </p>
          ))}
        </blockquote>,
      );
      continue;
    }

    if (/^(\s*[-*+]|\s*\d+\.)\s+/.test(line)) {
      const isOrdered = /^\s*\d+\.\s+/.test(line);
      const listItems: string[] = [];
      while (
        index < lines.length &&
        /^(\s*[-*+]|\s*\d+\.)\s+/.test(lines[index])
      ) {
        listItems.push(lines[index].replace(/^(\s*[-*+]|\s*\d+\.)\s+/, ""));
        index++;
      }

      const ListTag = isOrdered ? "ol" : "ul";
      nodes.push(
        <ListTag
          key={`list-${index}`}
          className={`my-3 space-y-1.5 pl-5 text-[14px] leading-[1.8] text-[var(--fg)] ${
            isOrdered ? "list-decimal" : "list-disc"
          }`}
        >
          {listItems.map((li, lIdx) => (
            <li key={lIdx} className="marker:text-[var(--muted)]">
              {renderRichText(li, links, workspaceId, linkMode)}
            </li>
          ))}
        </ListTag>,
      );
      continue;
    }

    const paragraphLines: string[] = [line];
    index++;
    while (
      index < lines.length &&
      lines[index].trim() &&
      !lines[index].trim().startsWith("#") &&
      !lines[index].trim().startsWith("```") &&
      !lines[index].trim().startsWith(">") &&
      !lines[index].trim().startsWith("|") &&
      !/^(\s*[-*+]|\s*\d+\.)\s+/.test(lines[index])
    ) {
      paragraphLines.push(lines[index]);
      index++;
    }

    nodes.push(
      <p
        key={`p-${index}`}
        className="my-2.5 text-[14px] leading-[1.8] text-[var(--fg)]"
      >
        {renderRichText(paragraphLines.join(" "), links, workspaceId, linkMode)}
      </p>,
    );
  }

  return <>{nodes}</>;
}

function splitTableRow(rowStr: string): string[] {
  const trimmed = rowStr.trim();
  const inner = trimmed.startsWith("|") ? trimmed.slice(1) : trimmed;
  const cleaned = inner.endsWith("|") ? inner.slice(0, -1) : inner;
  return cleaned.split("|").map((cell) => cell.trim());
}

function renderRichText(
  text: string,
  links: WikiDocumentLink[],
  workspaceId: string,
  linkMode: "internal" | "public",
): React.ReactNode {
  if (!text) return null;

  const wikiParts = resolveWikiLinks(text, links);

  return wikiParts.map((part, pIdx) => {
    if (part.type === "link") {
      if (linkMode === "public") {
        return (
          <span key={pIdx} className="font-medium text-[var(--fg)]">
            {part.title}
          </span>
        );
      }
      if (part.resolved) {
        return (
          <Link
            key={pIdx}
            href={`${workspacePath(workspaceId)}/wiki/${part.slug}`}
            className="cite inline-flex items-center gap-1 text-[13px] font-medium text-[var(--accent)] hover:opacity-80 transition-opacity align-baseline no-underline"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="11"
              height="11"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="flex-none opacity-70"
              aria-hidden="true"
            >
              <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
              <path d="M6 6h10" />
              <path d="M6 10h10" />
            </svg>
            <span>{part.title}</span>
          </Link>
        );
      }
      return (
        <RedLinkCta
          key={pIdx}
          title={part.title}
          slug={part.slug}
          workspaceId={workspaceId}
        />
      );
    }

    return <Fragment key={pIdx}>{parseInlineMarkdown(part.value)}</Fragment>;
  });
}

function parseInlineMarkdown(text: string): React.ReactNode {
  if (!text) return null;
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;
  let safetyCounter = 0;
  const maxIterations = text.length * 2 + 10;

  while (remaining.length > 0 && safetyCounter++ < maxIterations) {
    const codeMatch = remaining.match(/^`([^`]+)`/);
    if (codeMatch) {
      parts.push(
        <code
          key={key++}
          className="inline-flex max-w-full align-middle whitespace-nowrap rounded border border-[var(--border)] bg-[var(--surface)] px-1.5 py-0.5 font-mono text-[11px] font-medium leading-snug text-[var(--accent)]"
        >
          {codeMatch[1]}
        </code>,
      );
      remaining = remaining.slice(codeMatch[0].length);
      continue;
    }

    const linkMatch = remaining.match(/^\[([^\]]+)\]\(([^)]+)\)/);
    if (linkMatch) {
      const href = safeMarkdownHref(linkMatch[2]);
      parts.push(
        href ? (
          <a
            key={key++}
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-[var(--accent)] underline underline-offset-3 hover:opacity-80 transition-opacity"
          >
            {linkMatch[1]}
          </a>
        ) : (
          <span key={key++}>{linkMatch[1]}</span>
        ),
      );
      remaining = remaining.slice(linkMatch[0].length);
      continue;
    }

    const boldMatch = remaining.match(/^(\*\*|__)(.+?)\1/);
    if (boldMatch) {
      parts.push(
        <strong key={key++} className="font-bold text-[var(--fg)]">
          {parseInlineMarkdown(boldMatch[2])}
        </strong>,
      );
      remaining = remaining.slice(boldMatch[0].length);
      continue;
    }

    const italicMatch = remaining.match(/^(\*|_)(.+?)\1/);
    if (italicMatch) {
      parts.push(
        <em key={key++} className="italic text-[var(--fg)]">
          {parseInlineMarkdown(italicMatch[2])}
        </em>,
      );
      remaining = remaining.slice(italicMatch[0].length);
      continue;
    }

    const strikeMatch = remaining.match(/^~~(.+?)~~/);
    if (strikeMatch) {
      parts.push(
        <del key={key++} className="line-through text-[var(--muted)]">
          {parseInlineMarkdown(strikeMatch[1])}
        </del>,
      );
      remaining = remaining.slice(strikeMatch[0].length);
      continue;
    }

    const nextSpecial = nextMarkupIndex(remaining);
    if (nextSpecial === -1) {
      parts.push(remaining);
      remaining = "";
      break;
    } else if (nextSpecial === 0) {
      parts.push(remaining[0]);
      remaining = remaining.slice(1);
    } else {
      parts.push(remaining.slice(0, nextSpecial));
      remaining = remaining.slice(nextSpecial);
    }
  }

  return parts;
}

/**
 * 인라인 마크업 시작 위치. 단어 안의 `_` 는 SQL·식별자(`wiki_pages_sources_idx`)
 * 이므로 이탤릭 구분자로 쓰지 않는다 — 그 자리를 특수문자로 보면 밑줄처럼 접힌다.
 */
function nextMarkupIndex(text: string): number {
  for (let index = 0; index < text.length; index += 1) {
    const ch = text[index];
    if (ch === "`" || ch === "*" || ch === "~" || ch === "[") return index;
    if (ch !== "_") continue;
    const prev = index > 0 ? text[index - 1] : "";
    const next = text[index + 1] ?? "";
    const prevWord = /[0-9A-Za-z가-힣]/.test(prev);
    const nextWord = /[0-9A-Za-z가-힣]/.test(next);
    if (prevWord && nextWord) continue;
    return index;
  }
  return -1;
}
