"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import React from "react";

export type PaginationProps = {
  currentPage: number;
  totalItems: number;
  pageSize?: number;
  onPageChange: (page: number) => void;
  className?: string;
};

/**
 * taste-skill 기반 세련된 페이지네이션 컴포넌트
 *
 * - 페이지당 기본 8개 아이템 기준 분할
 * - 1페이지 이하일 경우 컨트롤을 숨겨 불필요한 시각적 노이즈 방지
 * - 스마트 페이지 번호 범위 생성 (1 ... 4 5 6 ... 10)
 * - 접근성 aria-label 및 aria-current 지원
 */
export function Pagination({
  currentPage,
  totalItems,
  pageSize = 8,
  onPageChange,
  className = "",
}: PaginationProps) {
  const totalPages = Math.ceil(totalItems / pageSize);

  if (totalPages <= 1) {
    return null;
  }

  const startItem = (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  // 스마트 페이지 번호 생성
  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      if (currentPage <= 4) {
        pages.push(1, 2, 3, 4, 5, "...", totalPages);
      } else if (currentPage >= totalPages - 3) {
        pages.push(
          1,
          "...",
          totalPages - 4,
          totalPages - 3,
          totalPages - 2,
          totalPages - 1,
          totalPages,
        );
      } else {
        pages.push(
          1,
          "...",
          currentPage - 1,
          currentPage,
          currentPage + 1,
          "...",
          totalPages,
        );
      }
    }
    return pages;
  };

  return (
    <nav
      role="navigation"
      aria-label="페이지 이동"
      className={`flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 pb-2 text-xs text-[var(--muted)] ${className}`}
    >
      {/* 항목 범위 안내 */}
      <div className="text-[12px] font-medium font-mono text-[var(--muted)]">
        총 <b className="text-[var(--fg)] font-bold">{totalItems}</b>개 중{" "}
        <span className="text-[var(--fg)]">
          {startItem}–{endItem}
        </span>
      </div>

      {/* 페이지네이션 버튼 바 */}
      <div className="flex items-center gap-1">
        {/* 이전 페이지 버튼 */}
        <button
          type="button"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          aria-label="이전 페이지"
          className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--fg)] transition-all hover:bg-[var(--surface)] hover:border-[var(--border-strong)] disabled:opacity-40 disabled:pointer-events-none cursor-pointer"
        >
          <ChevronLeft size={15} aria-hidden="true" />
        </button>

        {/* 페이지 번호들 */}
        {getPageNumbers().map((page, idx) => {
          if (page === "...") {
            return (
              <span
                key={`ellipsis-${idx}`}
                className="inline-flex h-8 w-6 items-center justify-center text-[var(--muted)] font-mono select-none"
              >
                …
              </span>
            );
          }

          const pageNum = Number(page);
          const isActive = pageNum === currentPage;

          return (
            <button
              key={pageNum}
              type="button"
              onClick={() => onPageChange(pageNum)}
              aria-current={isActive ? "page" : undefined}
              aria-label={`${pageNum} 페이지`}
              className={`inline-flex h-8 min-w-8 px-2.5 items-center justify-center rounded-lg text-xs font-mono font-bold transition-all cursor-pointer ${
                isActive
                  ? "bg-[var(--accent)] text-white shadow-2xs border border-[var(--accent)]"
                  : "border border-transparent bg-transparent text-[var(--muted)] hover:text-[var(--fg)] hover:bg-[var(--surface)] hover:border-[var(--border)]"
              }`}
            >
              {pageNum}
            </button>
          );
        })}

        {/* 다음 페이지 버튼 */}
        <button
          type="button"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          aria-label="다음 페이지"
          className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--fg)] transition-all hover:bg-[var(--surface)] hover:border-[var(--border-strong)] disabled:opacity-40 disabled:pointer-events-none cursor-pointer"
        >
          <ChevronRight size={15} aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
}
