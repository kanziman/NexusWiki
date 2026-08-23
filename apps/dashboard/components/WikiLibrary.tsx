"use client";

import {
  BookOpen,
  CheckCircle2,
  ChevronRight,
  FileText,
  HelpCircle,
  Map,
  Search,
} from "lucide-react";
import Link from "next/link";
import React, { useMemo, useState } from "react";

import { isVerified, verificationLabel } from "@/lib/verification-label";
import { workspacePath } from "@/lib/workspace-path";

export type WikiLibraryPage = {
  id: string;
  slug: string;
  title: string;
  category: string;
  content: string;
  verification_status: string;
  disputed: boolean;
  expires_at?: string | null;
};

// UI-SPEC Copywriting Contract "Empty wiki (no pages yet)" — 문구를 한 글자도 바꾸지 않는다.
const EMPTY_HEADING = "아직 컴파일된 위키 페이지가 없습니다";
const EMPTY_BODY = "소스를 추가하면 자동으로 위키 페이지가 생성됩니다.";
const NO_MATCH_BODY = "조건에 맞는 위키 문서가 없습니다.";

const categories = ["concepts", "entities", "guides", "maps"];
const labels: Record<string, string> = {
  concepts: "개념",
  entities: "항목",
  guides: "가이드",
  maps: "맵",
};

// 라벨 매핑은 lib/verification-label.ts 가 소유한다
const stateLabel = verificationLabel;

/**
 * 마크다운 문법(헤딩, 볼드, 코드, 테이블 등)과 브래킷([[...]])을 제거하여
 * 순수하고 깔끔한 평문 발췌문을 만든다.
 */
function cleanExcerpt(content: string): string {
  if (!content) return "";
  return content
    .replace(/\[\[(?:[^\]|]+\|)?([^\]]+)\]\]/g, "$1") // [[slug|title]] -> title
    .replace(/```[\s\S]*?```/g, "") // 코드 블록 제거
    .replace(/`([^`]+)`/g, "$1") // 인라인 코드
    .replace(/#{1,6}\s+/g, "") // 헤딩 제거
    .replace(/(\*\*|__)(.*?)\1/g, "$2") // 볼드 제거
    .replace(/(\*|_)(.*?)\1/g, "$2") // 이탤릭 제거
    .replace(/~~(.*?)~~/g, "$1") // 취소선 제거
    .replace(/^>\s?/gm, "") // 인용구 기호 제거
    .replace(/^[*-]\s+/gm, "") // 리스트 기호 제거
    .replace(/^\d+\.\s+/gm, "") // 번호 리스트 기호 제거
    .replace(/\|/g, " ") // 테이블 파이프 제거
    .replace(/\s+/g, " ") // 연속 공백/줄바꿈 축약
    .trim()
    .slice(0, 160);
}

function getCategoryIcon(category: string) {
  switch (category) {
    case "concepts":
      return <BookOpen size={13} className="opacity-75 flex-none" />;
    case "entities":
      return <FileText size={13} className="opacity-75 flex-none" />;
    case "guides":
      return <HelpCircle size={13} className="opacity-75 flex-none" />;
    case "maps":
      return <Map size={13} className="opacity-75 flex-none" />;
    default:
      return <FileText size={13} className="opacity-75 flex-none" />;
  }
}

/**
 * 위키 라이브러리 — 컴파일된 문서의 전체 목록이자 리더로 들어가는 진입점이다.
 */
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
          `${page.title} ${cleanExcerpt(page.content)}`
            .toLocaleLowerCase()
            .includes(query.toLocaleLowerCase()),
      ),
    [category, pages, query],
  );

  const isEmpty = pages.length === 0;
  const verifiedCount = pages.filter((p) => isVerified(p)).length;

  return (
    <div className="content library">
      {/* 헤더 영역 */}
      <section className="hero" data-od-id="wiki-library-header">
        <div>
          <h1>위키</h1>
          <p>팀의 소스에서 컴파일된 지식 문서입니다.</p>
        </div>
      </section>

      {/* 요약 지표 */}
      <section className="stats" aria-label="위키 요약">
        <div className="stat">
          <b>{pages.length}</b>
          <span>전체 문서</span>
        </div>
        <div className="stat">
          <b>{verifiedCount}</b>
          <span>검증됨</span>
        </div>
      </section>

      <section data-od-id="wiki-library-list">
        {isEmpty ? null : (
          <div className="toolbar flex items-center justify-between gap-4">
            {/* 카테고리 필터 */}
            <div
              className="chips flex items-center gap-1.5 flex-wrap"
              role="group"
              aria-label="카테고리 필터"
            >
              <button
                type="button"
                aria-pressed={category === null}
                className="chip transition-colors"
                onClick={() => setCategory(null)}
              >
                전체
              </button>
              {categories.map((item) => (
                <button
                  key={item}
                  type="button"
                  aria-pressed={category === item}
                  className="chip transition-colors"
                  onClick={() => setCategory(category === item ? null : item)}
                >
                  {labels[item]}
                </button>
              ))}
            </div>

            {/* 검색창 */}
            <div className="relative w-full max-w-[280px] flex-none">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none"
              />
              <input
                aria-label="위키 문서 검색"
                className="field search"
                placeholder="제목이나 내용으로 검색"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </div>
          </div>
        )}

        {/* 문서 목록 — 과도한 둥근 모서리 카드를 배제하고 명확한 상하 구분선 기반의 정갈한 리스트 */}
        {visible.length ? (
          <div className="doc-list mt-2 divide-y divide-[var(--border)] border-t border-b border-[var(--border)]">
            {visible.map((page) => {
              const verified = isVerified(page);
              const label = stateLabel(page);

              return (
                <Link
                  key={page.id}
                  className="doc group flex items-center justify-between py-3.5 px-3 hover:bg-[var(--surface)] transition-colors rounded-none"
                  href={`${workspacePath(workspaceId)}/wiki/${page.slug}`}
                  data-od-id={`wiki-document-${page.slug}`}
                >
                  <div className="doc-body flex-1 min-w-0 pr-4">
                    {/* 상단 메타 뱃지 */}
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-semibold bg-[var(--surface)] text-[var(--muted)] border border-[var(--border)]">
                        {getCategoryIcon(page.category)}
                        <span>{labels[page.category] ?? page.category}</span>
                      </span>

                      <span
                        className={`inline-flex items-center gap-1 text-[11px] font-medium ${
                          page.disputed
                            ? "text-[var(--danger)]"
                            : verified
                              ? "text-[var(--good)]"
                              : "text-[var(--muted)]"
                        }`}
                      >
                        {verified && <CheckCircle2 size={11} />}
                        <span>{label}</span>
                      </span>
                    </div>

                    {/* 문서 제목 */}
                    <span className="doc-title text-[14px] font-bold text-[var(--fg)] group-hover:text-[var(--accent)] transition-colors block truncate">
                      {page.title}
                    </span>

                    {/* 발췌문 */}
                    <p className="doc-excerpt text-xs text-[var(--muted)] leading-relaxed mt-1 line-clamp-2">
                      {cleanExcerpt(page.content)}
                    </p>
                  </div>

                  <ChevronRight
                    className="nav-icon text-[var(--muted)] group-hover:text-[var(--fg)] group-hover:translate-x-0.5 transition-all flex-none opacity-60 group-hover:opacity-100"
                    size={16}
                    aria-hidden="true"
                  />
                </Link>
              );
            })}
          </div>
        ) : (
          <div className="library-empty mt-6" role="status">
            {isEmpty ? (
              <>
                <b>{EMPTY_HEADING}</b>
                <span>{EMPTY_BODY}</span>
              </>
            ) : (
              NO_MATCH_BODY
            )}
          </div>
        )}
      </section>
    </div>
  );
}
