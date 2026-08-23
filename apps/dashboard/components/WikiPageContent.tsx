"use client";

import Link from "next/link";
import React, { Fragment, useEffect, useState } from "react";
import { ArrowLeft, ArrowUpRight, FileText, Layers } from "lucide-react";

import { FavoriteButton } from "@/components/FavoriteButton";
import { RedLinkCta } from "@/components/RedLinkCta";
import { safeMarkdownHref } from "@/lib/markdown-url";
import { apiFetch } from "@/lib/api-client";
import { verificationLabel } from "@/lib/verification-label";
import { workspacePath } from "@/lib/workspace-path";
import { resolveWikiLinks } from "@/lib/wiki-links";

// UI-SPEC Copywriting Contract "Wiki viewer (UI-05)" — 문구를 한 글자도 바꾸지 않는다.
const READ_ONLY_BANNER =
  "이 페이지는 컴파일됩니다 — 직접 편집할 수 없으며, 소스가 갱신되면 다시 컴파일됩니다.";
// ⚠️ 상태 이름은 lib/verification-label.ts 에서 파생한다.
const DISPUTED_CALLOUT = `${verificationLabel({ disputed: true })} — 상충하는 정보가 있습니다. 원문을 확인하세요.`;
const VERIFY_ACTION_LABEL = "검증됨으로 표시";
const VERIFY_FAILURE_MESSAGE = "검증 처리에 실패했습니다. 다시 시도해주세요.";

// workspace-home-prd.md 카테고리 표시명 매핑 — wiki_pages.category CHECK 4종 고정.
const CATEGORY_LABELS: Record<string, string> = {
  concepts: "개념",
  entities: "엔티티",
  guides: "가이드",
  maps: "맵",
};

type WikiPage = {
  id: string;
  title: string;
  content: string;
  category: string;
  verification_status: string;
  verified_by: string | null;
  verified_at: string | null;
  expires_at: string | null;
  disputed: boolean;
};

export type WikiPageContentProps = {
  page: WikiPage;
  links: { target_slug: string; resolved: boolean }[];
  workspaceId: string;
  canVerify: boolean;
  initialBookmarked: boolean;
};

type VerifyResponse = {
  id: string;
  slug: string;
  verification_status: string;
  verified_by: string | null;
  verified_at: string | null;
  expires_at: string | null;
  disputed: boolean;
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

type HeadingItem = {
  id: string;
  level: number;
  title: string;
};

/**
 * 위키 문서 뷰어 본체 — 미니멀 & 클린 에디토리얼 조판
 */
export function WikiPageContent({
  page,
  links,
  workspaceId,
  canVerify,
  initialBookmarked,
}: WikiPageContentProps) {
  const [status, setStatus] = useState(page.verification_status);
  const [verifiedAt, setVerifiedAt] = useState(page.verified_at);
  const [expiresAt, setExpiresAt] = useState(page.expires_at);
  const [disputed, setDisputed] = useState(page.disputed);
  const [submitting, setSubmitting] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [activeHeadingId, setActiveHeadingId] = useState<string | null>(null);

  async function handleVerify() {
    if (submitting) return;
    setSubmitting(true);
    setVerifyError(null);

    try {
      const result = await apiFetch<VerifyResponse>(
        `/workspaces/${workspaceId}/wiki/${page.id}/verify`,
        { method: "PATCH", body: { verification_status: "verified" } },
      );
      setStatus(result.verification_status);
      setVerifiedAt(result.verified_at);
      setExpiresAt(result.expires_at);
      setDisputed(result.disputed);
    } catch {
      setVerifyError(VERIFY_FAILURE_MESSAGE);
    } finally {
      setSubmitting(false);
    }
  }

  const isExpired =
    expiresAt !== null && new Date(expiresAt).getTime() < Date.now();

  const sanitizedContent = cleanWikiContent(page.content);
  const headings = extractHeadings(sanitizedContent);
  const relatedLinks = [
    ...new Map(
      links
        .filter((link) => link.resolved)
        .map((link) => [link.target_slug, link]),
    ).values(),
  ];

  // ScrollSpy: 목차 활성 섹션 감지
  useEffect(() => {
    if (headings.length === 0) return;

    function handleScroll() {
      const scrollPosition = window.scrollY + 100;
      let currentActive: string | null = null;

      for (const h of headings) {
        const el = document.getElementById(h.id);
        if (el) {
          const top = el.getBoundingClientRect().top + window.scrollY;
          if (scrollPosition >= top) {
            currentActive = h.id;
          }
        }
      }

      if (currentActive) {
        setActiveHeadingId(currentActive);
      } else if (headings[0]) {
        setActiveHeadingId(headings[0].id);
      }
    }

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();

    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, [headings]);

  const categoryLabel = CATEGORY_LABELS[page.category] ?? page.category;

  return (
    <div className="reader-layout">
      <article className="reader">
        {/* 상단 네비게이션: 뒤로가기 + 브레드크럼 경로 */}
        <div className="flex items-center gap-2.5 mb-2.5">
          <Link
            href={`${workspacePath(workspaceId)}/wiki`}
            className="flex items-center gap-1 text-xs text-[var(--muted)] hover:text-[var(--fg)] transition-colors py-0.5 px-1.5 -ml-1.5 rounded hover:bg-[var(--surface)] font-medium"
            aria-label="위키 목록으로 돌아가기"
          >
            <ArrowLeft size={13} aria-hidden="true" />
            <span>위키 목록</span>
          </Link>
          <span
            className="text-[var(--border-strong)] opacity-50 font-mono text-xs select-none"
            aria-hidden="true"
          >
            /
          </span>
          <nav
            aria-label="위키 탐색 경로"
            className="breadcrumb-path m-0 text-xs"
          >
            {categoryLabel}
          </nav>
        </div>

        {/* 문서 타이틀 + 즐겨찾기 */}
        <div className="title-row">
          <h1>{page.title}</h1>
          <FavoriteButton
            key={page.id}
            wikiId={page.id}
            workspaceId={workspaceId}
            initialBookmarked={initialBookmarked}
          />
        </div>

        {/* 거버넌스 메타데이터 바 */}
        <div className="governance">
          <span className="tag">{categoryLabel}</span>
          {disputed ? (
            <span className="badge" style={{ color: "var(--danger)" }}>
              {DISPUTED_CALLOUT}
            </span>
          ) : (
            <VerificationCallout
              status={status}
              verifiedAt={verifiedAt}
              expiresAt={expiresAt}
              isExpired={isExpired}
            />
          )}
        </div>

        {/* 컴파일 안내 캡션 (담백하고 미니멀한 텍스트) */}
        <p className="mt-2.5 mb-0 text-[11px] text-[var(--muted)] leading-relaxed">
          {READ_ONLY_BANNER}
        </p>

        {/* 검증 액션 버튼 */}
        {canVerify ? (
          <div className="mt-3.5 flex flex-col gap-1">
            <button
              type="button"
              onClick={handleVerify}
              disabled={submitting}
              className="button primary self-start"
            >
              {submitting ? "검증 처리 중..." : VERIFY_ACTION_LABEL}
            </button>
            {verifyError !== null ? (
              <p role="alert" className="invite-feedback error show mt-1">
                {verifyError}
              </p>
            ) : null}
          </div>
        ) : null}

        {/* 본문 렌더링 */}
        <div className="article mt-7">
          <DocumentBody
            content={sanitizedContent}
            links={links}
            workspaceId={workspaceId}
          />
        </div>

        {/* 하단 관련 문서 섹션 */}
        {relatedLinks.length ? (
          <section
            className="mt-12 border-t border-[var(--border)] pt-8"
            aria-labelledby="related-wiki-heading"
          >
            <div className="flex items-center justify-between gap-2 mb-4">
              <div className="flex items-center gap-2">
                <Layers
                  size={16}
                  className="text-[var(--accent)]"
                  aria-hidden="true"
                />
                <h2
                  id="related-wiki-heading"
                  className="m-0 text-sm font-semibold text-[var(--fg)] tracking-tight"
                >
                  관련 문서
                </h2>
                <span className="rounded-full bg-[var(--surface)] border border-[var(--border)] px-2 py-0.5 text-[10px] font-mono font-medium text-[var(--muted)]">
                  {relatedLinks.length}
                </span>
              </div>
              <p className="m-0 text-xs text-[var(--muted)] hidden sm:block">
                이 문서와 연결된 지식 문서입니다
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {relatedLinks.map((link) => (
                <Link
                  key={link.target_slug}
                  href={`${workspacePath(workspaceId)}/wiki/${link.target_slug}`}
                  className="group relative flex items-center justify-between p-3.5 rounded-xl border border-[var(--border)] bg-[var(--bg)] hover:bg-[var(--surface)]/50 hover:border-[var(--accent)]/50 transition-all duration-150 shadow-[var(--shadow-sm)] hover:shadow"
                >
                  <div className="flex items-center gap-3 min-w-0 pr-2">
                    <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded-lg bg-[var(--surface)] border border-[var(--border)] group-hover:border-[var(--accent)]/30 group-hover:text-[var(--accent)] text-[var(--muted)] transition-colors">
                      <FileText size={15} aria-hidden="true" />
                    </div>
                    <div className="min-w-0 flex flex-col">
                      <span className="text-xs font-semibold text-[var(--fg)] group-hover:text-[var(--accent)] truncate transition-colors">
                        {link.target_slug.replace(/-/g, " ")}
                      </span>
                      <span className="text-[10px] font-mono text-[var(--muted)]">
                        위키 문서 보기
                      </span>
                    </div>
                  </div>
                  <ArrowUpRight
                    size={14}
                    className="shrink-0 text-[var(--muted)] group-hover:text-[var(--accent)] group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all duration-150"
                    aria-hidden="true"
                  />
                </Link>
              ))}
            </div>
          </section>
        ) : null}
      </article>

      {/* 우측 목차 (TOC) 패널 */}
      <aside className="toc">
        <div className="toc-heading">
          <h2>목차</h2>
        </div>
        {headings.length ? (
          <nav aria-label="이 문서에서" className="toc-list">
            {headings.map((heading) => {
              const isActive = activeHeadingId === heading.id;
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
                  className={`${isActive ? "active" : ""} ${indentClass} transition-colors block text-[11px] leading-snug py-1`}
                  onClick={(e) => {
                    e.preventDefault();
                    const target = document.getElementById(heading.id);
                    if (target) {
                      target.scrollIntoView({ behavior: "smooth" });
                      window.history.pushState(null, "", `#${heading.id}`);
                      setActiveHeadingId(heading.id);
                    }
                  }}
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
      </aside>
    </div>
  );
}

/**
 * 마크다운 본문 끝에 생성된 중복 "관련 문서" 섹션을 제거하여
 * 위키 전용 카드 칩 UI로 단일화한다.
 */
function cleanWikiContent(content: string): string {
  if (!content) return "";
  return content
    .replace(
      /(?:\r?\n)+(?:#{1,4})\s*(?:관련\s*문서|관련문서|Related\s*Documents?)\s*(?:\r?\n)[\s\S]*$/i,
      "",
    )
    .trimEnd();
}

/**
 * 본문에서 목차 항목 추출
 */
function extractHeadings(content: string): HeadingItem[] {
  if (!content) return [];
  const lines = content.split("\n");
  const result: HeadingItem[] = [];

  for (let index = 0; index < lines.length; index++) {
    const line = lines[index];
    const match = /^(#{1,4})\s+(.+?)\s*$/.exec(line);
    if (match) {
      const level = match[1].length;
      const rawTitle = match[2]
        .replace(/\[\[(?:[^\]|]+\|)?([^\]]+)\]\]/g, "$1")
        .replace(/[*_`~]/g, "")
        .trim();
      result.push({
        id: `section-${index}`,
        level,
        title: rawTitle,
      });
    }
  }

  return result;
}

type DocumentBodyProps = {
  content: string;
  links: { target_slug: string; resolved: boolean }[];
  workspaceId: string;
};

/**
 * 위키 문서 본문 마크다운 + WikiLink 렌더러
 */
function DocumentBody({ content, links, workspaceId }: DocumentBodyProps) {
  if (!content) return null;

  const lines = content.split("\n");
  const nodes: React.ReactNode[] = [];
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
          <pre className="overflow-x-auto p-3.5 font-mono text-xs leading-relaxed text-[var(--fg)]">
            <code>{codeLines.join("\n")}</code>
          </pre>
        </div>,
      );
      continue;
    }

    // 3. 마크다운 테이블 (| ... |)
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
                      {renderRichText(cell, links, workspaceId)}
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
                          {renderRichText(cell, links, workspaceId)}
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

    // 4. 헤딩 (#, ##, ###, ####)
    const headingMatch = /^(#{1,4})\s+(.+?)\s*$/.exec(line);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const title = headingMatch[2];
      const sectionId = `section-${index}`;
      const renderedTitle = renderRichText(title, links, workspaceId);
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

    // 5. 구분선 (---, ***)
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

    // 6. 블록 인용구 (> ...)
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
              {renderRichText(ql, links, workspaceId)}
            </p>
          ))}
        </blockquote>,
      );
      continue;
    }

    // 7. 리스트 (- item, * item, 1. item)
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
          className={`my-3 space-y-1.5 pl-5 text-[14px] leading-[1.8] text-[var(--fg)] ${
            isOrdered ? "list-decimal" : "list-disc"
          }`}
        >
          {listItems.map((li, lIdx) => (
            <li key={lIdx} className="marker:text-[var(--muted)]">
              {renderRichText(li, links, workspaceId)}
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
      <p
        key={`p-${index}`}
        className="my-2.5 text-[14px] leading-[1.8] text-[var(--fg)]"
      >
        {renderRichText(paragraphLines.join(" "), links, workspaceId)}
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

/**
 * 인라인 마크다운 서식 + [[WikiLink]] 통합 파싱 함수
 */
function renderRichText(
  text: string,
  links: { target_slug: string; resolved: boolean }[],
  workspaceId: string,
): React.ReactNode {
  if (!text) return null;

  const wikiParts = resolveWikiLinks(text, links);

  return wikiParts.map((part, pIdx) => {
    if (part.type === "link") {
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

/**
 * 인라인 마크다운 파싱: **볼드**, *이탤릭*, `인라인 코드`, ~~취소선~~, [링크](url)
 */
function parseInlineMarkdown(text: string): React.ReactNode {
  if (!text) return null;
  const parts: React.ReactNode[] = [];
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
          className="rounded border border-[var(--border)] bg-[var(--surface)] px-1.5 py-0.5 font-mono text-[11px] font-medium text-[var(--accent)]"
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

    // 3. 볼드: **text** or __text__
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

    // 4. 이탤릭: *text* or _text_
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

    // 5. 취소선: ~~text~~
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

    // 6. 일반 텍스트
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

type VerificationCalloutProps = {
  status: string;
  verifiedAt: string | null;
  expiresAt: string | null;
  isExpired: boolean;
};

// ⚠️ verifiedBy(계정 UUID)는 의도적으로 prop에서 받지 않는다. 이 컴포넌트에는
// UUID를 표시명으로 바꿀 조회 경로가 없어, 넘겨받아도 화면에는 못 쓴다 — 안
// 쓰는 prop을 시그니처에 남겨 두면 다음 사람이 "표시할 수 있는데 안 하나?"로
// 헷갈린다.
function VerificationCallout({
  status,
  verifiedAt,
  expiresAt,
  isExpired,
}: VerificationCalloutProps) {
  if (status === "verified" && !isExpired) {
    // ⚠️ 검증자를 표시하지 않는다. `verified_by`는 auth 사용자 UUID이고 이
    // 라우트에는 그것을 이름으로 바꿀 조회 경로가 없다 — 그대로 찍으면 화면에
    // 36자짜리 식별자가 남아 정작 읽어야 할 검증 날짜를 밀어낸다. 사람이 읽을
    // 이름을 붙이려면 표시명 조회가 먼저 필요하고, 그건 이 화면 밖의 일이다.
    const dateLabel = verifiedAt !== null ? formatDate(verifiedAt) : "";
    return (
      <span className="badge verified">
        {`${verificationLabel({ verification_status: "verified" })}${dateLabel ? ` · ${dateLabel}` : ""}`}
      </span>
    );
  }

  if (status === "verified" && isExpired) {
    // isExpired가 true인 분기이므로 expiresAt는 사실상 항상 non-null이지만,
    // prop 시그니처가 string | null이라 렌더 시점에 한 번 더 널가드한다.
    // ⚠️ 상태 이름은 모듈에서 파생한다 — 목록 화면이 같은 문서를 부르는 말과
    // 갈리면 안 된다. 뒤의 날짜·안내는 이 화면 고유의 확장이다.
    const dateLabel = expiresAt !== null ? formatDate(expiresAt) : "";
    const stateName = verificationLabel({
      verification_status: "verified",
      expires_at: expiresAt ?? "1970-01-01T00:00:00Z",
    });
    return (
      <span className="badge" style={{ color: "var(--danger)" }}>
        {`${stateName}${dateLabel ? ` · ${dateLabel} 이후 재검증 필요` : " · 재검증 필요"}`}
      </span>
    );
  }

  if (status === "partial") {
    // UI-SPEC에 partial 전용 문구가 없다 — expired-style(warning-text) 처리를
    // 이 컴포넌트의 합리적 확장으로 채택한다(06-07-PLAN.md Task 2 <action>).
    // ⚠️ 상태 이름 자체는 lib/verification-label.ts 에서 파생한다. 예전에는
    // 여기만 "부분 검증됨"이라 홈·라이브러리의 "부분 검증"과 갈렸다. 뒤에
    // 붙는 안내 문구는 이 화면 고유의 확장이라 그대로 둔다.
    return (
      <span className="badge">
        {verificationLabel({ verification_status: "partial" })} · 재검증이
        필요합니다
      </span>
    );
  }

  // "unverified" — UI-SPEC은 중립 기본 상태로 명시적 콜아웃을 요구하지 않는다.
  return null;
}
