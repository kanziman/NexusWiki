"use client";

import React, { Fragment, ReactNode } from "react";

import { CitationMarker } from "@/components/CitationMarker";
import type { AnchorPart, TextPart } from "@/lib/citation-anchors";
import { safeMarkdownHref } from "@/lib/markdown-url";

type MarkdownAnswerProps = {
  segments: (TextPart | AnchorPart)[];
  resolved: boolean;
  onMarkerClick: (part: AnchorPart) => void;
  className?: string;
};

/**
 * 인용 마커(CitationMarker)가 인라인으로 포함된 AI 답변용 리치 마크다운 렌더러
 * (제목, 표, 목록, 인용구, 코드, 볼드, 이탤릭, 인용 뱃지 완벽 지원)
 */
export function MarkdownAnswer({
  segments,
  resolved,
  onMarkerClick,
  className = "",
}: MarkdownAnswerProps) {
  if (segments.length === 0) return null;

  // 1. 세그먼트들을 (string | ReactNode) 평탄화
  let anchorCounter = 0;
  const rawPieces: (string | ReactNode)[] = [];

  for (let i = 0; i < segments.length; i++) {
    const part = segments[i];
    if (part.type === "text") {
      rawPieces.push(part.value);
    } else {
      const idx = anchorCounter++;
      rawPieces.push(
        <CitationMarker
          key={`cite-${i}`}
          part={part}
          index={idx}
          resolved={resolved}
          onClick={onMarkerClick}
        />,
      );
    }
  }

  // 2. 줄(Line) 단위로 쪼개기
  const lines: (string | ReactNode)[][] = [[]];
  for (const piece of rawPieces) {
    if (typeof piece === "string") {
      const splitLines = piece.split("\n");
      for (let sIdx = 0; sIdx < splitLines.length; sIdx++) {
        if (sIdx > 0) {
          lines.push([]);
        }
        if (splitLines[sIdx]) {
          lines[lines.length - 1].push(splitLines[sIdx]);
        }
      }
    } else {
      lines[lines.length - 1].push(piece);
    }
  }

  // 3. 줄 단위 마크다운 블록 파싱
  const blocks: ReactNode[] = [];
  let lineIdx = 0;

  while (lineIdx < lines.length) {
    const currentLine = lines[lineIdx];
    const textContent = getLineText(currentLine).trim();

    // 1. 빈 줄
    if (!textContent && currentLine.length === 0) {
      lineIdx++;
      continue;
    }

    // 2. 코드 블록 (``` ... ```) — 인용 React 노드가 끼어 있어도 순서를
    // 문자열로 되돌리지 않고 그대로 보존한다.
    if (textContent.startsWith("```")) {
      const lang = textContent.slice(3).trim();
      const codeNodes: ReactNode[] = [];
      lineIdx++;
      while (
        lineIdx < lines.length &&
        !getLineText(lines[lineIdx]).trim().startsWith("```")
      ) {
        if (codeNodes.length > 0) codeNodes.push("\n");
        codeNodes.push(...lines[lineIdx]);
        lineIdx++;
      }
      if (lineIdx < lines.length) lineIdx++;

      blocks.push(
        <div
          key={`code-${lineIdx}`}
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
            {codeNodes}
          </pre>
        </div>,
      );
      continue;
    }

    // 3. 구분선 (---, ***)
    if (/^(\*\*\*|---|___)$/.test(textContent)) {
      blocks.push(
        <hr
          key={`hr-${lineIdx}`}
          className="my-4 border-t border-[var(--border)]"
        />,
      );
      lineIdx++;
      continue;
    }

    // 4. 제목 (Heading: #, ##, ###, ####)
    const headingMatch = textContent.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const parsedChildren = stripHeadingSyntax(currentLine, headingMatch[1]);
      lineIdx++;

      if (level === 1) {
        blocks.push(
          <h1
            key={`h1-${lineIdx}`}
            className="mt-5 mb-2.5 text-lg font-bold tracking-tight text-[var(--fg)] border-b border-[var(--border)] pb-1.5"
          >
            {parsedChildren}
          </h1>,
        );
      } else if (level === 2) {
        blocks.push(
          <h2
            key={`h2-${lineIdx}`}
            className="mt-4 mb-2 text-sm font-bold tracking-tight text-[var(--fg)]"
          >
            {parsedChildren}
          </h2>,
        );
      } else if (level === 3) {
        blocks.push(
          <h3
            key={`h3-${lineIdx}`}
            className="mt-3.5 mb-1.5 text-xs font-bold text-[var(--fg)]"
          >
            {parsedChildren}
          </h3>,
        );
      } else {
        blocks.push(
          <h4
            key={`h4-${lineIdx}`}
            className="mt-3 mb-1 text-[11px] font-bold text-[var(--muted)] uppercase tracking-wider"
          >
            {parsedChildren}
          </h4>,
        );
      }
      continue;
    }

    // 5. 표 (Table: | ... |)
    if (textContent.startsWith("|") && textContent.includes("|", 1)) {
      const tableRows: (string | ReactNode)[][] = [];
      while (
        lineIdx < lines.length &&
        getLineText(lines[lineIdx]).trim().startsWith("|") &&
        getLineText(lines[lineIdx]).trim().includes("|", 1)
      ) {
        tableRows.push(lines[lineIdx]);
        lineIdx++;
      }

      if (tableRows.length >= 2) {
        const headerRow = parseTableRowNodes(tableRows[0]);
        const secondRowText = getLineText(tableRows[1]).trim();
        const isDivider = secondRowText
          .split("|")
          .filter(Boolean)
          .every((cell) => /^[\s:-]+$/.test(cell));

        const bodyRowNodes = (
          isDivider ? tableRows.slice(2) : tableRows.slice(1)
        ).map(parseTableRowNodes);

        blocks.push(
          <div
            key={`table-${lineIdx}`}
            className="my-3.5 overflow-x-auto rounded-md border border-[var(--border)] shadow-2xs bg-[var(--bg)]"
          >
            <table className="w-full border-collapse text-left text-xs">
              <thead className="bg-[var(--surface)] text-[var(--fg)] border-b border-[var(--border)]">
                <tr>
                  {headerRow.map((cell, cIdx) => (
                    <th
                      key={cIdx}
                      className="px-3.5 py-2 font-semibold tracking-tight text-[var(--fg)]"
                    >
                      {cell}
                    </th>
                  ))}
                </tr>
              </thead>
              {bodyRowNodes.length > 0 ? (
                <tbody className="divide-y divide-[var(--border)]">
                  {bodyRowNodes.map((row, rIdx) => (
                    <tr
                      key={rIdx}
                      className="hover:bg-[var(--surface)]/40 transition-colors"
                    >
                      {row.map((cell, cIdx) => (
                        <td
                          key={cIdx}
                          className="align-top px-3.5 py-2 text-[var(--fg)]"
                        >
                          {cell}
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

    // 6. 인용구 (Blockquote: > ...)
    if (textContent.startsWith(">")) {
      const quoteLines: (string | ReactNode)[][] = [];
      while (
        lineIdx < lines.length &&
        getLineText(lines[lineIdx]).trim().startsWith(">")
      ) {
        quoteLines.push(stripLeadingQuote(lines[lineIdx]));
        lineIdx++;
      }
      blocks.push(
        <blockquote
          key={`quote-${lineIdx}`}
          className="my-3 border-l-2 border-[var(--accent)] pl-3.5 pr-2 py-1 text-xs italic text-[var(--muted)] leading-relaxed break-words"
        >
          {quoteLines.map((ql, qIdx) => (
            <p key={qIdx} className={qIdx > 0 ? "mt-1" : "my-0"}>
              {renderLineInline(ql)}
            </p>
          ))}
        </blockquote>,
      );
      continue;
    }

    // 7. 목록 (Lists: - item, * item, 1. item)
    if (/^(\s*[-*+]|\s*\d+\.)\s+/.test(textContent)) {
      const isOrdered = /^\s*\d+\.\s+/.test(textContent);
      const listItems: (string | ReactNode)[][] = [];
      while (
        lineIdx < lines.length &&
        /^(\s*[-*+]|\s*\d+\.)\s+/.test(getLineText(lines[lineIdx]))
      ) {
        listItems.push(stripLeadingListMarker(lines[lineIdx]));
        lineIdx++;
      }

      const ListTag = isOrdered ? "ol" : "ul";
      blocks.push(
        <ListTag
          key={`list-${lineIdx}`}
          className={`my-2 space-y-1 pl-5 text-xs leading-relaxed text-[var(--fg)] ${
            isOrdered ? "list-decimal" : "list-disc"
          }`}
        >
          {listItems.map((li, lIdx) => (
            <li key={lIdx} className="marker:text-[var(--muted)]">
              {renderLineInline(li)}
            </li>
          ))}
        </ListTag>,
      );
      continue;
    }

    // 8. 일반 단락 (Paragraph)
    const paragraphNodes: (string | ReactNode)[] = [];
    paragraphNodes.push(...currentLine);
    lineIdx++;

    while (
      lineIdx < lines.length &&
      getLineText(lines[lineIdx]).trim() &&
      !getLineText(lines[lineIdx]).trim().startsWith("#") &&
      !getLineText(lines[lineIdx]).trim().startsWith("```") &&
      !getLineText(lines[lineIdx]).trim().startsWith(">") &&
      !getLineText(lines[lineIdx]).trim().startsWith("|") &&
      !/^(\s*[-*+]|\s*\d+\.)\s+/.test(getLineText(lines[lineIdx]))
    ) {
      paragraphNodes.push(" ");
      paragraphNodes.push(...lines[lineIdx]);
      lineIdx++;
    }

    blocks.push(
      <p key={`p-${lineIdx}`} className="my-2 leading-relaxed text-[var(--fg)]">
        {renderLineInline(paragraphNodes)}
      </p>,
    );
  }

  return (
    <div
      className={`markdown-answer space-y-2.5 text-xs leading-relaxed text-[var(--fg)] break-words ${className}`}
    >
      {blocks}
    </div>
  );
}

function getLineText(lineNodes: (string | ReactNode)[]): string {
  return lineNodes.filter((n) => typeof n === "string").join("");
}

function stripHeadingSyntax(
  lineNodes: (string | ReactNode)[],
  headingLevelHashes: string,
): ReactNode {
  let hasStripped = false;
  const result: (string | ReactNode)[] = [];

  for (const node of lineNodes) {
    if (typeof node === "string" && !hasStripped) {
      const stripped = node.replace(
        new RegExp(`^\\s*${headingLevelHashes}\\s*`),
        "",
      );
      hasStripped = true;
      if (stripped) result.push(stripped);
    } else {
      result.push(node);
    }
  }

  return renderLineInline(result);
}

function stripLeadingQuote(
  lineNodes: (string | ReactNode)[],
): (string | ReactNode)[] {
  let hasStripped = false;
  const result: (string | ReactNode)[] = [];

  for (const node of lineNodes) {
    if (typeof node === "string" && !hasStripped) {
      const stripped = node.replace(/^\s*>\s?/, "");
      hasStripped = true;
      if (stripped) result.push(stripped);
    } else {
      result.push(node);
    }
  }
  return result;
}

function stripLeadingListMarker(
  lineNodes: (string | ReactNode)[],
): (string | ReactNode)[] {
  let hasStripped = false;
  const result: (string | ReactNode)[] = [];

  for (const node of lineNodes) {
    if (typeof node === "string" && !hasStripped) {
      const stripped = node.replace(/^(\s*[-*+]|\s*\d+\.)\s+/, "");
      hasStripped = true;
      if (stripped) result.push(stripped);
    } else {
      result.push(node);
    }
  }
  return result;
}

function parseTableRowNodes(lineNodes: (string | ReactNode)[]): ReactNode[] {
  const cells: (string | ReactNode)[][] = [[]];

  for (const node of lineNodes) {
    if (typeof node === "string") {
      const parts = node.split("|");
      for (let pIdx = 0; pIdx < parts.length; pIdx++) {
        if (pIdx > 0) {
          cells.push([]);
        }
        if (parts[pIdx]) {
          cells[cells.length - 1].push(parts[pIdx]);
        }
      }
    } else {
      cells[cells.length - 1].push(node);
    }
  }

  // 앞뒤 빈 셀 필터링 (e.g. | col1 | col2 | -> [col1, col2])
  const filteredCells = cells.filter((c, idx) => {
    const txt = getLineText(c).trim();
    if (idx === 0 && !txt && c.length <= 1) return false;
    if (idx === cells.length - 1 && !txt && c.length <= 1) return false;
    return true;
  });

  return filteredCells.map((c) => renderLineInline(c));
}

function renderLineInline(lineNodes: (string | ReactNode)[]): ReactNode {
  return lineNodes.map((node, i) => {
    if (typeof node === "string") {
      return <Fragment key={i}>{parseInlineFormatting(node)}</Fragment>;
    }
    return <Fragment key={i}>{node}</Fragment>;
  });
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
          className="inline-flex max-w-full align-middle whitespace-nowrap rounded border border-[var(--border)] bg-[var(--surface)] px-1.5 py-0.5 font-mono text-[11px] font-medium leading-snug text-[var(--accent)]"
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
 * 인라인 마크업 시작 위치. 단어 안의 `_` 는 SQL·식별자이므로 이탤릭
 * 구분자로 쓰지 않는다 — 위키 본문 WikiDocumentBody 와 같은 규칙이다.
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
