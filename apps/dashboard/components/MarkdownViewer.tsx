"use client";

import React, { ReactNode } from "react";

import { safeMarkdownHref } from "@/lib/markdown-url";

type MarkdownViewerProps = {
  content?: string | null;
  className?: string;
};

/**
 * 경량, 안전 및 고품질 마크다운 렌더러 컴포넌트
 */
export function MarkdownViewer({
  content = "",
  className = "",
}: MarkdownViewerProps) {
  const safeContent = typeof content === "string" ? content : "";
  const elements = parseMarkdown(safeContent);

  return (
    <div
      className={`markdown-body space-y-3.5 text-xs leading-relaxed text-[var(--fg)] break-words ${className}`}
    >
      {elements}
    </div>
  );
}

function parseMarkdown(text: string): ReactNode[] {
  if (!text) return [];
  const lines = text.split("\n");
  const nodes: ReactNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    // 1. 빈 줄
    if (!trimmed) {
      index++;
      continue;
    }

    // 2. 코드 블록 (``` ... ```)
    if (trimmed.startsWith("```")) {
      const lang = trimmed.slice(3).trim();
      const codeLines: string[] = [];
      index++;
      while (index < lines.length && !lines[index].trim().startsWith("```")) {
        codeLines.push(lines[index]);
        index++;
      }
      if (index < lines.length) {
        index++; // closing ```
      }
      nodes.push(
        <div
          key={`code-${index}`}
          className="my-3 overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-2xs"
        >
          {lang ? (
            <div className="border-b border-[var(--border)] bg-[var(--bg)] px-3.5 py-1.5 font-mono text-[10px] font-semibold text-[var(--muted)]">
              {lang}
            </div>
          ) : null}
          <pre className="overflow-x-auto p-3.5 font-mono text-xs leading-relaxed text-[var(--fg)]">
            <code>{codeLines.join("\n")}</code>
          </pre>
        </div>,
      );
      continue;
    }

    // 3. 표 (Table: | ... |)
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
            className="my-3.5 overflow-x-auto rounded-md border border-[var(--border)] shadow-2xs bg-[var(--bg)]"
          >
            <table className="w-full border-collapse text-left text-xs">
              <thead className="bg-[var(--surface)] text-[var(--fg)] border-b border-[var(--border)]">
                <tr>
                  {headerCells.map((cell, cIdx) => (
                    <th
                      key={cIdx}
                      className="px-3.5 py-2 font-semibold tracking-tight text-[var(--fg)]"
                    >
                      {parseInline(cell)}
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
                        <td key={cIdx} className="px-3.5 py-2 text-[var(--fg)]">
                          {parseInline(cell)}
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

    // 4. 제목 (Heading: #, ##, ###, ####)
    const headingMatch = trimmed.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const title = headingMatch[2];
      const inline = parseInline(title);
      index++;

      if (level === 1) {
        nodes.push(
          <h1
            key={`h1-${index}`}
            className="mt-5 mb-2 text-lg font-bold tracking-tight text-[var(--fg)] border-b border-[var(--border)] pb-1.5"
          >
            {inline}
          </h1>,
        );
      } else if (level === 2) {
        nodes.push(
          <h2
            key={`h2-${index}`}
            className="mt-4 mb-2 text-sm font-bold tracking-tight text-[var(--fg)]"
          >
            {inline}
          </h2>,
        );
      } else if (level === 3) {
        nodes.push(
          <h3
            key={`h3-${index}`}
            className="mt-3.5 mb-1.5 text-xs font-bold text-[var(--fg)]"
          >
            {inline}
          </h3>,
        );
      } else {
        nodes.push(
          <h4
            key={`h4-${index}`}
            className="mt-3 mb-1 text-[11px] font-bold text-[var(--muted)] uppercase tracking-wider"
          >
            {inline}
          </h4>,
        );
      }
      continue;
    }

    // 5. 구분선 (Horizontal Rule: ---, ***)
    if (/^(\*\*\*|---|___)$/.test(trimmed)) {
      nodes.push(
        <hr
          key={`hr-${index}`}
          className="my-4 border-t border-[var(--border)]"
        />,
      );
      index++;
      continue;
    }

    // 6. 인용구 (Blockquote: > ...)
    if (trimmed.startsWith(">")) {
      const quoteLines: string[] = [];
      while (index < lines.length && lines[index].trim().startsWith(">")) {
        quoteLines.push(lines[index].trim().replace(/^>\s?/, ""));
        index++;
      }
      nodes.push(
        <blockquote
          key={`quote-${index}`}
          className="my-3 border-l-2 border-[var(--accent)] pl-3.5 pr-2 py-1 text-xs italic text-[var(--muted)] leading-relaxed break-words"
        >
          {quoteLines.map((ql, qIdx) => (
            <p key={qIdx} className={qIdx > 0 ? "mt-1" : "my-0"}>
              {parseInline(ql)}
            </p>
          ))}
        </blockquote>,
      );
      continue;
    }

    // 7. 목록 (Lists: - item, * item, 1. item)
    if (/^(\s*[-*+]|\s*\d+\.)\s+/.test(line)) {
      const isOrdered = /^\s*\d+\.\s+/.test(line);
      const listItems: string[] = [];
      while (
        index < lines.length &&
        /^(\s*[-*+]|\s*\d+\.)\s+/.test(lines[index])
      ) {
        const itemLine = lines[index];
        const text = itemLine.replace(/^(\s*[-*+]|\s*\d+\.)\s+/, "");
        listItems.push(text);
        index++;
      }

      const ListTag = isOrdered ? "ol" : "ul";
      nodes.push(
        <ListTag
          key={`list-${index}`}
          className={`my-2 space-y-1 pl-5 text-xs leading-relaxed text-[var(--fg)] ${
            isOrdered ? "list-decimal" : "list-disc"
          }`}
        >
          {listItems.map((li, lIdx) => (
            <li key={lIdx} className="marker:text-[var(--muted)]">
              {parseInline(li)}
            </li>
          ))}
        </ListTag>,
      );
      continue;
    }

    // 8. 일반 단락
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
      <p key={`p-${index}`} className="my-1.5 leading-relaxed text-[var(--fg)]">
        {parseInline(paragraphLines.join(" "))}
      </p>,
    );
  }

  return nodes;
}

function splitTableRow(rowStr: string): string[] {
  const trimmed = rowStr.trim();
  const inner = trimmed.startsWith("|") ? trimmed.slice(1) : trimmed;
  const cleaned = inner.endsWith("|") ? inner.slice(0, -1) : inner;
  return cleaned.split("|").map((cell) => cell.trim());
}

/**
 * 인라인 서식 파싱: **볼드**, *이탤릭*, `코드`, ~~취소선~~, [링크](url), <br>
 */
function parseInline(text: string): ReactNode {
  if (!text) return null;
  const lines = text.split(/<br\s*\/?>/gi);
  if (lines.length > 1) {
    return lines.map((line, i) => (
      <React.Fragment key={i}>
        {i > 0 ? <br /> : null}
        {parseInlineFormatting(line)}
      </React.Fragment>
    ));
  }

  return parseInlineFormatting(text);
}

function parseInlineFormatting(text: string): ReactNode {
  if (!text) return null;
  const parts: ReactNode[] = [];
  let remaining = text;
  let key = 0;

  let safetyCounter = 0;
  const maxIterations = text.length * 2 + 10;

  while (remaining.length > 0 && safetyCounter++ < maxIterations) {
    // 1. 인라인 코드: `code`
    const codeMatch = remaining.match(/^`([^`]+)`/);
    if (codeMatch) {
      parts.push(
        <code
          key={key++}
          className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-1.5 py-0.5 font-mono text-[11px] text-[var(--accent)] font-semibold"
        >
          {codeMatch[1]}
        </code>,
      );
      remaining = remaining.slice(codeMatch[0].length);
      continue;
    }

    // 2. 링크: [label](url)
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
            className="font-medium text-[var(--accent)] underline underline-offset-2 hover:opacity-80 transition-opacity"
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

    // 3. 볼드: **text** or __text__
    const boldMatch = remaining.match(/^(\*\*|__)(.+?)\1/);
    if (boldMatch) {
      parts.push(
        <strong key={key++} className="font-bold text-[var(--fg)]">
          {parseInlineFormatting(boldMatch[2])}
        </strong>,
      );
      remaining = remaining.slice(boldMatch[0].length);
      continue;
    }

    // 4. 이탤릭: *text* or _text_
    const italicMatch = remaining.match(/^(\*|_)(.+?)\1/);
    if (italicMatch) {
      parts.push(
        <em key={key++} className="italic text-[var(--fg)]">
          {parseInlineFormatting(italicMatch[2])}
        </em>,
      );
      remaining = remaining.slice(italicMatch[0].length);
      continue;
    }

    // 5. 취소선: ~~text~~
    const strikeMatch = remaining.match(/^~~(.+?)~~/);
    if (strikeMatch) {
      parts.push(
        <del key={key++} className="line-through text-[var(--muted)]">
          {parseInlineFormatting(strikeMatch[1])}
        </del>,
      );
      remaining = remaining.slice(strikeMatch[0].length);
      continue;
    }

    // 6. 일반 텍스트 (다음 특수 기호까지)
    const nextSpecial = remaining.search(/[`*_~\[]/);
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
