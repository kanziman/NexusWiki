"use client";

import {
  AlertTriangle,
  BookOpen,
  Clock,
  Plus,
  Search,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import React, { useState } from "react";

import { formatRelativeTime } from "@/lib/relative-time";
import { workspacePath } from "@/lib/workspace-path";
import { BacklogDetailModal } from "./BacklogDetailModal";
import { Pagination } from "./Pagination";

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
  // 미해결 링크·위키 조회가 실패했는지. 빈 결과와 구분하지 못하면 화면이
  // "모든 위키 링크가 정상적으로 연결되어 있습니다"라고 단정하게 된다.
  loadFailed?: boolean;
};

const EMPTY_HEADING = "작성 대기 중인 백로그가 없습니다";
const EMPTY_BODY = "모든 위키 링크가 정상적으로 연결되어 있습니다.";
const LOAD_FAILED_HEADING = "지식 공백을 불러오지 못했습니다";
const LOAD_FAILED_BODY = "잠시 후 다시 시도해주세요.";

type CitationFilter = "all" | "multi" | "single";

/**
 * 헤더 행과 데이터 행이 이 값 하나만 참조한다. 각자 폭을 선언하면 한쪽만
 * 고쳤을 때 축이 어긋난다.
 */
const BACKLOG_COLS = "minmax(0,1.4fr) minmax(0,1.25fr) 95px 100px 105px";

/**
 * UI-06 작성 대기 백로그 — 미해결 레드링크(`to_wiki_id IS NULL`)를 target_slug
 * 로 집계해 인용 빈도 내림차순으로 보여준다.
 */
export function BacklogList({
  workspaceId,
  initialItems,
  loadFailed = false,
}: BacklogListProps) {
  const [items] = useState<BacklogItem[]>(initialItems);
  const [filter, setFilter] = useState<CitationFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [openTopic, setOpenTopic] = useState<BacklogItem | null>(null);

  const PAGE_SIZE = 8;

  const multiCitedCount = items.filter((item) => item.impact >= 2).length;
  const singleCitedCount = items.filter((item) => item.impact === 1).length;

  const FILTERS: { id: CitationFilter; label: string }[] = [
    { id: "all", label: `전체 ${items.length}` },
    { id: "multi", label: `다중 인용 ${multiCitedCount}` },
    { id: "single", label: `단일 인용 ${singleCitedCount}` },
  ];

  // 필터와 검색어는 함께 걸린다 — 한쪽이 다른 쪽을 리셋하지 않는다.
  const filteredItems = items.filter((item) => {
    if (filter === "multi" && item.impact < 2) return false;
    if (filter === "single" && item.impact !== 1) return false;
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    const matchesTitle = item.display_title.toLowerCase().includes(query);
    const matchesSlug = item.target_slug.toLowerCase().includes(query);
    const matchesPage = item.referencing_pages.some((page) =>
      page.title.toLowerCase().includes(query),
    );
    return matchesTitle || matchesSlug || matchesPage;
  });

  const paginatedItems = filteredItems.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE,
  );

  const distinctReferringPages = new Set(
    items.flatMap((item) => item.referencing_pages.map((p) => p.id)),
  );

  // 최다 인용 — impact 내림차순, 동률이면 target_slug 오름차순으로 결정적으로
  // 하나를 고른다(design.md "표기 결정 규칙은 결정적이어야 한다"와 같은 원칙).
  const mostCited =
    items.length > 0
      ? [...items].sort(
          (a, b) =>
            b.impact - a.impact ||
            a.target_slug.localeCompare(b.target_slug, "ko"),
        )[0]
      : null;

  // 가장 오래 대기 중 — first_detected_at 오름차순, 동률이면 impact 내림차순,
  // 그다음 target_slug 오름차순으로 깬다.
  const longestWaiting =
    items.length > 0
      ? [...items].sort(
          (a, b) =>
            new Date(a.first_detected_at).getTime() -
              new Date(b.first_detected_at).getTime() ||
            b.impact - a.impact ||
            a.target_slug.localeCompare(b.target_slug, "ko"),
        )[0]
      : null;

  return (
    <div className="content backlog">
      {/* 헤더 영역 */}
      <section className="hero" data-od-id="backlog-header">
        <div>
          <h1>지식 공백</h1>
          <p>
            위키 문서에서 참조되었으나 아직 작성되지 않은 레드링크 목록입니다.
            관련 소스를 추가하면 자동으로 컴파일되어 해결됩니다.
          </p>
        </div>
      </section>

      {/* 우선순위 요약 벤토 (조회가 성공했고 주제가 있을 때만 표시).
          네 칸 모두 수치와 라벨을 텍스트로 함께 둔다 — 색만으로 상태를
          전달하면 지표가 사라지는 사용자가 생긴다. */}
      {!loadFailed && items.length > 0 && mostCited && longestWaiting && (
        <section
          className="mt-8 mb-2 grid grid-cols-2 gap-3.5 md:grid-cols-4"
          aria-label="지식 공백 요약"
        >
          {/* 1. 미해결 레드링크 */}
          <div
            data-testid="backlog-metric-unresolved"
            className="flex flex-col gap-2.5 overflow-hidden rounded-[14px] border border-[var(--border)] bg-[var(--surface)] px-[18px] py-4"
          >
            <div className="flex items-center justify-between text-[12px] font-semibold text-[var(--muted)]">
              <span>미해결 레드링크</span>
              <AlertTriangle
                size={16}
                className="text-[var(--warning)]"
                aria-hidden="true"
              />
            </div>
            <div className="flex flex-wrap items-baseline gap-2">
              <b className="font-mono text-[26px] font-extrabold tracking-tight text-[var(--fg)]">
                {items.length}
              </b>
              <span className="text-[11px] text-[var(--muted)]">개 주제</span>
            </div>
            <span className="w-fit rounded-md bg-[var(--warning)]/12 px-1.5 py-0.5 text-[11px] font-bold text-[var(--warning)]">
              우선 해결 필요
            </span>
          </div>

          {/* 2. 영향받는 위키 */}
          <div
            data-testid="backlog-metric-affected-wikis"
            className="flex flex-col gap-2.5 overflow-hidden rounded-[14px] border border-[var(--border)] bg-[var(--surface)] px-[18px] py-4"
          >
            <div className="flex items-center justify-between text-[12px] font-semibold text-[var(--muted)]">
              <span>영향받는 위키</span>
              <BookOpen
                size={16}
                className="text-[var(--accent)]"
                aria-hidden="true"
              />
            </div>
            <div className="flex flex-wrap items-baseline gap-2">
              <b className="font-mono text-[26px] font-extrabold tracking-tight text-[var(--fg)]">
                {distinctReferringPages.size}
              </b>
              <span className="text-[11px] text-[var(--muted)]">개 문서</span>
            </div>
            <span className="w-fit rounded-md bg-[var(--soft)] px-1.5 py-0.5 text-[11px] font-bold text-[var(--accent)]">
              링크 결손 발생
            </span>
          </div>

          {/* 3. 최다 인용 공백 */}
          <div
            data-testid="backlog-metric-most-cited"
            className="flex flex-col gap-2.5 overflow-hidden rounded-[14px] border border-[var(--border)] bg-[var(--surface)] px-[18px] py-4"
          >
            <div className="flex items-center justify-between text-[12px] font-semibold text-[var(--muted)]">
              <span>최다 인용 공백</span>
              <TrendingUp
                size={16}
                className="text-[var(--danger)]"
                aria-hidden="true"
              />
            </div>
            <b
              title={mostCited.display_title}
              className="block truncate font-mono text-[16px] font-extrabold tracking-tight text-[var(--fg)]"
            >
              {mostCited.display_title}
            </b>
            <span className="w-fit rounded-md bg-[var(--danger)]/12 px-1.5 py-0.5 text-[11px] font-bold text-[var(--danger)]">
              {`${mostCited.impact}회 인용 집중`}
            </span>
          </div>

          {/* 4. 가장 오래 대기 중 */}
          <div
            data-testid="backlog-metric-longest-waiting"
            className="flex flex-col gap-2.5 overflow-hidden rounded-[14px] border border-[var(--border)] bg-[var(--surface)] px-[18px] py-4"
          >
            <div className="flex items-center justify-between text-[12px] font-semibold text-[var(--muted)]">
              <span>가장 오래 대기 중</span>
              <Clock
                size={16}
                className="text-[var(--muted)]"
                aria-hidden="true"
              />
            </div>
            <b className="font-mono text-[26px] font-extrabold tracking-tight text-[var(--fg)]">
              {formatRelativeTime(longestWaiting.first_detected_at)}
            </b>
            <span
              title={longestWaiting.display_title}
              className="block truncate text-[11px] text-[var(--muted)]"
            >
              {longestWaiting.display_title}
            </span>
          </div>
        </section>
      )}

      {/* 툴바 & 테이블 섹션 */}
      <section data-od-id="backlog-table-section">
        {loadFailed ? (
          <div
            role="alert"
            className="table-wrap mt-3 rounded-lg border border-[var(--border)] bg-[var(--surface)]/30 p-12 text-center"
          >
            <b className="block text-[14px] text-[var(--fg)]">
              {LOAD_FAILED_HEADING}
            </b>
            <span className="mt-1.5 block text-xs text-[var(--muted)]">
              {LOAD_FAILED_BODY}
            </span>
          </div>
        ) : (
          <>
            {items.length > 0 && (
              <div className="toolbar flex items-center justify-between gap-4">
                {/* 인용 빈도 세그먼트 필터. 상호배타 단일 선택이라 tab
                    시맨틱을 쓴다 — 소스 화면과 같은 패턴. */}
                <nav
                  className="flex h-9 flex-wrap items-center gap-1"
                  role="tablist"
                  aria-label="지식 공백 필터"
                >
                  {FILTERS.map((tab) => (
                    <button
                      key={tab.id}
                      type="button"
                      role="tab"
                      aria-selected={filter === tab.id}
                      onClick={() => {
                        setFilter(tab.id);
                        setPage(1);
                      }}
                      className={`nw-focus-ring box-border inline-flex h-9 cursor-pointer items-center rounded-lg border px-3 text-[12px] font-bold transition-colors ${
                        filter === tab.id
                          ? "border-[var(--accent)] bg-[var(--soft)] text-[var(--accent)]"
                          : "border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] hover:border-[var(--border-strong)] hover:text-[var(--fg)]"
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </nav>

                {/* 검색 인풋. .field.search 가 높이 36px 를 고정한다 — 이 규칙은
                    소스·위키 라이브러리 검색창과 공유하므로 여기서 고치지
                    않는다. */}
                <div className="relative h-9 w-full max-w-[280px] flex-none">
                  <Search
                    size={14}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none"
                  />
                  <input
                    className="field search"
                    value={searchQuery}
                    onChange={(event) => {
                      setSearchQuery(event.target.value);
                      setPage(1);
                    }}
                    placeholder="주제 또는 참조 문서로 검색"
                    aria-label="지식 공백 검색"
                  />
                </div>
              </div>
            )}

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
              /* 일체형 목록 컨테이너.
                 ⚠️ <table> 을 쓰지 않지만 표 시맨틱은 명시적으로 얹는다 —
                 인용 빈도가 이 화면의 정렬 축이라 행·열 관계가 보조기술에
                 남아야 한다. display:grid 는 <table> 의 기본 role 도
                 지우므로 굳이 <table> 요소를 쓰는 것보다 명시적 role 이
                 낫다. */
              <div
                role="table"
                id="backlog-items-list"
                className="mt-3 overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--bg)]"
                style={
                  { "--backlog-cols": BACKLOG_COLS } as React.CSSProperties
                }
              >
                <div
                  role="row"
                  className="hidden items-center gap-5 border-b border-[var(--border)] bg-[var(--surface)] px-4 py-2.5 text-[11px] font-bold tracking-wider text-[var(--muted)] uppercase md:grid"
                  style={{ gridTemplateColumns: "var(--backlog-cols)" }}
                >
                  <span role="columnheader">백로그 주제</span>
                  <span role="columnheader">인용 중인 위키</span>
                  <span role="columnheader" className="text-right">
                    인용 빈도
                  </span>
                  <span role="columnheader">최초 감지</span>
                  <span role="columnheader" className="text-right">
                    해결 액션
                  </span>
                </div>

                <div className="divide-y divide-[var(--border)]">
                  {paginatedItems.map((item) => {
                    const visibleCited = item.referencing_pages.slice(0, 2);
                    const hiddenCitedCount =
                      item.referencing_pages.length - visibleCited.length;

                    return (
                      <div
                        role="row"
                        key={item.target_slug}
                        className="grid grid-cols-1 items-center gap-3 px-4 py-3 text-xs transition-colors hover:bg-[var(--surface)]/50 md:h-[68px] md:gap-5 md:py-0 md:[grid-template-columns:var(--backlog-cols)]"
                      >
                        {/* 1. 백로그 주제 */}
                        <div role="cell" className="min-w-0">
                          <button
                            type="button"
                            className="topic group block w-full text-left focus:outline-none"
                            onClick={() => setOpenTopic(item)}
                            aria-haspopup="dialog"
                          >
                            <b
                              title={item.display_title}
                              className="block truncate text-[13.5px] font-bold text-[var(--fg)] transition-colors group-hover:text-[var(--accent)]"
                            >
                              {item.display_title}
                            </b>
                            <span className="mt-0.5 block truncate font-mono text-[10.5px] text-[var(--muted)]">
                              {item.target_slug}
                            </span>
                          </button>
                        </div>

                        {/* 2. 인용 중인 위키 — 인용 수에 따라 행 높이가
                            달라지지 않게 한 줄에 최대 2개만 그린다. */}
                        <div role="cell" className="min-w-0">
                          {item.referencing_pages.length === 0 ? (
                            <span className="text-[11px] text-[var(--muted)] italic">
                              인용 문서 없음
                            </span>
                          ) : (
                            <div className="flex min-w-0 items-center gap-1.5 overflow-hidden whitespace-nowrap">
                              {visibleCited.map((page) => (
                                <Link
                                  key={page.id}
                                  href={`${workspacePath(workspaceId)}/wiki/${page.slug}`}
                                  className="doc-chip min-w-0"
                                  title={page.title}
                                >
                                  <span className="truncate">{page.title}</span>
                                </Link>
                              ))}
                              {hiddenCitedCount > 0 && (
                                <span className="flex-none text-[11px] font-semibold text-[var(--muted)]">
                                  {`+${hiddenCitedCount}개 더`}
                                </span>
                              )}
                            </div>
                          )}
                        </div>

                        {/* 3. 인용 빈도 (우측 정렬, 정렬 축) */}
                        <div
                          role="cell"
                          className="whitespace-nowrap md:text-right"
                        >
                          <span className="inline-flex items-center gap-1 font-mono">
                            <b className="text-[13.5px] font-bold text-[var(--fg)]">
                              {item.impact}
                            </b>
                            <span className="text-[11px] text-[var(--muted)]">
                              회
                            </span>
                          </span>
                        </div>

                        {/* 4. 최초 감지 */}
                        <div
                          role="cell"
                          className="whitespace-nowrap text-[11.5px] text-[var(--muted)]"
                        >
                          {formatRelativeTime(item.first_detected_at)}
                        </div>

                        {/* 5. 해결 액션 */}
                        <div
                          role="cell"
                          className="whitespace-nowrap md:text-right"
                        >
                          <Link
                            href={`${workspacePath(workspaceId)}/sources?prefillTitle=${encodeURIComponent(
                              item.display_title,
                            )}&tab=text`}
                            className="button compact inline-flex items-center gap-1 rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1 text-[11.5px] font-semibold shadow-2xs transition-all hover:border-[var(--accent)] hover:bg-[var(--accent)] hover:text-white"
                          >
                            <Plus size={11} className="opacity-70" />
                            <span>소스 추가</span>
                          </Link>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {filteredItems.length > 0 && (
              <Pagination
                currentPage={page}
                totalItems={filteredItems.length}
                pageSize={PAGE_SIZE}
                onPageChange={setPage}
              />
            )}
          </>
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
