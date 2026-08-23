"use client";

import { Plus, Search } from "lucide-react";
import Link from "next/link";
import React, { useState } from "react";

import { formatRelativeTime } from "@/lib/relative-time";
import { workspacePath } from "@/lib/workspace-path";
import { BacklogDetailModal } from "./BacklogDetailModal";

export type BacklogReferencingPage = {
  id: string;
  slug: string;
  title: string;
  excerpt: string | null;
};

export type BacklogItem = {
  target_slug: string;
  display_title: string;
  impact: number;
  first_detected_at: string;
  referencing_pages: BacklogReferencingPage[];
};

export type BacklogListProps = {
  workspaceId: string;
  initialItems: BacklogItem[];
};

const EMPTY_HEADING = "작성 대기 중인 백로그가 없습니다";
const EMPTY_BODY = "모든 위키 링크가 정상적으로 연결되어 있습니다.";

/**
 * UI-06 작성 대기 백로그 — 미해결 레드링크(`to_wiki_id IS NULL`)를 target_slug
 * 로 집계해 인용 빈도 내림차순으로 보여준다.
 */
export function BacklogList({ workspaceId, initialItems }: BacklogListProps) {
  const [items] = useState<BacklogItem[]>(initialItems);
  const [searchQuery, setSearchQuery] = useState("");
  const [openTopic, setOpenTopic] = useState<BacklogItem | null>(null);

  const filteredItems = items.filter((item) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    const matchesTitle = item.display_title.toLowerCase().includes(query);
    const matchesSlug = item.target_slug.toLowerCase().includes(query);
    const matchesPage = item.referencing_pages.some((page) =>
      page.title.toLowerCase().includes(query),
    );
    return matchesTitle || matchesSlug || matchesPage;
  });

  const distinctReferringPages = new Set(
    items.flatMap((item) => item.referencing_pages.map((p) => p.id)),
  );

  return (
    <div className="content backlog">
      {/* 헤더 영역 */}
      <section className="hero" data-od-id="backlog-header">
        <div>
          <h1>미완성 백로그</h1>
          <p>
            위키 문서에서 참조되었으나 아직 작성되지 않은 레드링크 목록입니다.
            관련 소스를 추가하면 자동으로 컴파일되어 해결됩니다.
          </p>
        </div>
      </section>

      {/* 요약 통계 */}
      <section className="stats" aria-label="백로그 요약">
        <div className="stat">
          <b>{items.length}</b>
          <span>미해결 백로그</span>
        </div>
        <div className="stat">
          <b>{distinctReferringPages.size}</b>
          <span>영향받는 위키</span>
        </div>
      </section>

      {/* 툴바 & 테이블 섹션 */}
      <section data-od-id="backlog-table-section">
        <div className="toolbar flex items-center justify-between gap-4">
          <nav className="tabs" role="tablist" aria-label="백로그 필터">
            <button
              type="button"
              role="tab"
              aria-selected
              className="tab active text-xs font-bold"
            >
              전체 {items.length}
            </button>
          </nav>

          {/* 검색 인풋 */}
          <div className="relative w-full max-w-[280px] flex-none">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none"
            />
            <input
              className="field search"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="주제 또는 참조 문서로 검색"
              aria-label="백로그 검색"
            />
          </div>
        </div>

        {filteredItems.length === 0 ? (
          <div className="table-wrap p-12 text-center border border-[var(--border)] rounded-lg bg-[var(--surface)]/30 mt-3">
            <b className="block text-[14px] text-[var(--fg)]">
              {items.length === 0 ? EMPTY_HEADING : "검색 결과가 없습니다"}
            </b>
            <span className="mt-1.5 block text-xs text-[var(--muted)]">
              {items.length === 0
                ? EMPTY_BODY
                : "다른 검색어를 입력하거나 검색어를 지우세요."}
            </span>
          </div>
        ) : (
          <div className="table-wrap overflow-x-auto rounded-lg border border-[var(--border)] bg-[var(--bg)] mt-3">
            <table
              className="table w-full text-left border-collapse"
              id="backlog-items-list"
            >
              <colgroup>
                <col style={{ width: "32%" }} />
                <col style={{ width: "32%" }} />
                <col style={{ width: "12%" }} />
                <col style={{ width: "12%" }} />
                <col style={{ width: "12%" }} />
              </colgroup>
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--surface)]/60 text-[11px] font-bold text-[var(--muted)] uppercase tracking-wider">
                  <th scope="col" className="py-2.5 px-4">
                    백로그 주제
                  </th>
                  <th scope="col" className="py-2.5 px-4">
                    인용 중인 위키
                  </th>
                  <th scope="col" className="py-2.5 px-4 text-center">
                    인용 빈도
                  </th>
                  <th scope="col" className="py-2.5 px-4">
                    최초 감지
                  </th>
                  <th scope="col" className="py-2.5 px-4 text-right">
                    <span className="sr-only">작업</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)] text-xs">
                {filteredItems.map((item) => {
                  return (
                    <tr
                      key={item.target_slug}
                      className="hover:bg-[var(--surface)]/50 transition-colors"
                    >
                      {/* 백로그 주제 */}
                      <td className="py-3 px-4">
                        <button
                          type="button"
                          className="topic group text-left block w-full focus:outline-none"
                          onClick={() => setOpenTopic(item)}
                          aria-haspopup="dialog"
                        >
                          <b
                            title={item.display_title}
                            className="font-bold text-[13.5px] text-[var(--fg)] group-hover:text-[var(--accent)] transition-colors block truncate"
                          >
                            {item.display_title}
                          </b>
                          <span className="font-mono text-[10.5px] text-[var(--muted)] block truncate mt-0.5">
                            {item.target_slug}
                          </span>
                        </button>
                      </td>

                      {/* 인용 중인 위키 */}
                      <td className="py-3 px-4">
                        {item.referencing_pages.length === 0 ? (
                          <span className="sub text-[11px] text-[var(--muted)] italic">
                            인용 문서 없음
                          </span>
                        ) : (
                          <div className="doc-chips flex flex-wrap gap-1.5">
                            {item.referencing_pages.map((page) => (
                              <Link
                                key={page.id}
                                href={`${workspacePath(workspaceId)}/wiki/${page.slug}`}
                                className="doc-chip"
                                title={page.title}
                              >
                                <span className="truncate">{page.title}</span>
                              </Link>
                            ))}
                          </div>
                        )}
                      </td>

                      {/* 인용 빈도 */}
                      <td className="py-3 px-4 text-center whitespace-nowrap">
                        <span className="inline-flex items-center gap-1 font-mono">
                          <b className="impact text-[13.5px] font-bold text-[var(--fg)]">
                            {item.impact}
                          </b>
                          <span className="impact-unit text-[11px] text-[var(--muted)]">
                            회
                          </span>
                        </span>
                      </td>

                      {/* 최초 감지 */}
                      <td className="py-3 px-4 text-[11.5px] text-[var(--muted)] whitespace-nowrap">
                        <span className="sub">
                          {formatRelativeTime(item.first_detected_at)}
                        </span>
                      </td>

                      {/* 소스 추가 액션 버튼 */}
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <Link
                          href={`${workspacePath(workspaceId)}/sources?prefillTitle=${encodeURIComponent(
                            item.display_title,
                          )}&tab=text`}
                          className="button compact inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11.5px] font-semibold border border-[var(--border)] bg-[var(--bg)] hover:bg-[var(--accent)] hover:text-white hover:border-[var(--accent)] transition-all shadow-2xs"
                        >
                          <Plus size={11} className="opacity-70" />
                          <span>소스 추가</span>
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 상세 패널 다이얼로그 */}
      <BacklogDetailModal
        workspaceId={workspaceId}
        item={openTopic}
        onClose={() => setOpenTopic(null)}
      />
    </div>
  );
}
