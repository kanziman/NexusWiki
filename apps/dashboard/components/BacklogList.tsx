"use client";

import { CircleAlert, FileText, Plus, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import {
  EmptyState,
  PageHeader,
  StatusBadge,
} from "@/components/DashboardPrimitives";
import { workspacePath } from "@/lib/workspace-path";

export type BacklogReferencingPage = {
  id: string;
  slug: string;
  title: string;
};

export type BacklogItem = {
  target_slug: string;
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

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("ko-KR", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

export function BacklogList({ workspaceId, initialItems }: BacklogListProps) {
  const [items] = useState<BacklogItem[]>(initialItems);
  const [searchQuery, setSearchQuery] = useState("");

  const filteredItems = items.filter((item) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    const matchesSlug = item.target_slug.toLowerCase().includes(query);
    const matchesPage = item.referencing_pages.some((page) =>
      page.title.toLowerCase().includes(query),
    );
    return matchesSlug || matchesPage;
  });

  const distinctReferringPages = new Set(
    items.flatMap((item) => item.referencing_pages.map((p) => p.id)),
  );

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-xxl">
      <PageHeader
        title="미완성 백로그"
        description="위키 문서에서 참조되었으나 아직 작성되지 않은 레드링크 목록입니다. 관련 소스를 추가하면 자동으로 컴파일되어 해결됩니다."
      />

      {/* 상단 통계 2종 */}
      <div className="grid grid-cols-1 gap-base sm:grid-cols-2">
        <div className="flex flex-col gap-xs rounded-lg border border-[var(--border)] bg-[var(--surface)] p-lg shadow-sm">
          <span className="text-xs font-semibold text-[var(--muted)]">
            미해결 백로그
          </span>
          <div className="flex items-baseline gap-xs">
            <span className="text-2xl font-bold text-[var(--fg)]">
              {items.length}
            </span>
            <span className="text-xs text-[var(--muted)]">개 주제</span>
          </div>
        </div>

        <div className="flex flex-col gap-xs rounded-lg border border-[var(--border)] bg-[var(--surface)] p-lg shadow-sm">
          <span className="text-xs font-semibold text-[var(--muted)]">
            영향받는 위키 문서
          </span>
          <div className="flex items-baseline gap-xs">
            <span className="text-2xl font-bold text-[var(--fg)]">
              {distinctReferringPages.size}
            </span>
            <span className="text-xs text-[var(--muted)]">개 문서</span>
          </div>
        </div>
      </div>

      {/* 검색 바 */}
      {items.length > 0 && (
        <div className="relative flex items-center">
          <Search
            size={16}
            className="absolute left-3 text-[var(--muted)] pointer-events-none"
            aria-hidden="true"
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="백로그 주제 또는 참조 문서 검색..."
            aria-label="백로그 검색"
            className="w-full rounded-md border border-[var(--border)] bg-[var(--surface)] py-2 pl-9 pr-3 text-sm text-[var(--fg)] placeholder-[var(--muted)] outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
          />
        </div>
      )}

      {filteredItems.length === 0 ? (
        <EmptyState
          title={items.length === 0 ? EMPTY_HEADING : "검색 결과가 없습니다"}
          detail={
            items.length === 0
              ? EMPTY_BODY
              : "다른 검색어를 입력하거나 필터를 초기화하세요."
          }
        />
      ) : (
        <ul
          id="backlog-items-list"
          className="flex flex-col border-y border-[var(--nw-rule)]"
        >
          {filteredItems.map((item) => (
            <li
              key={item.target_slug}
              className="flex flex-col gap-base border-b border-[var(--nw-rule)] py-lg last:border-b-0"
            >
              <div className="flex flex-col gap-sm sm:flex-row sm:items-start sm:justify-between">
                <div className="flex min-w-0 flex-1 flex-col gap-xs">
                  <div className="flex items-center gap-sm">
                    <CircleAlert
                      size={18}
                      className="shrink-0 text-[var(--accent)]"
                      aria-hidden="true"
                    />
                    <span
                      title={item.target_slug}
                      aria-label={item.target_slug}
                      className="min-w-0 font-semibold tracking-[-0.02em] text-[var(--nw-ink)]"
                      style={{ font: "var(--font-title-sm)" }}
                    >
                      {item.target_slug.replace(/-/g, " ")}
                    </span>
                    <StatusBadge>참조 {item.impact}회</StatusBadge>
                  </div>
                  <span className="text-xs text-[var(--muted)]">
                    최초 감지: {formatDate(item.first_detected_at)}
                  </span>
                </div>

                <Link
                  href={`${workspacePath(workspaceId)}/sources?prefillTitle=${encodeURIComponent(
                    item.target_slug.replace(/-/g, " "),
                  )}&tab=text`}
                  className="nw-focus-ring flex shrink-0 items-center gap-xs rounded-sm bg-[var(--accent)] px-base py-xs text-xs font-semibold text-[var(--accent-fg)] hover:opacity-90 active:scale-95 transition-all"
                >
                  <Plus size={14} aria-hidden="true" />
                  <span>소스 추가</span>
                </Link>
              </div>

              {/* 인용 중인 위키 문서 목록 */}
              {item.referencing_pages.length > 0 && (
                <div className="flex flex-wrap items-center gap-xs pt-xs">
                  <span className="text-xs font-medium text-[var(--muted)]">
                    인용 문서:
                  </span>
                  {item.referencing_pages.map((page) => (
                    <Link
                      key={page.id}
                      href={`${workspacePath(workspaceId)}/wiki/${page.slug}`}
                      className="inline-flex items-center gap-1 rounded border border-[var(--border)] bg-[var(--surface-soft)] px-2 py-0.5 text-xs text-[var(--fg)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition-colors"
                    >
                      <FileText size={12} className="text-[var(--muted)]" />
                      <span>{page.title}</span>
                    </Link>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
