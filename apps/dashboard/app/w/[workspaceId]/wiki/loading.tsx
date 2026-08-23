import React from "react";

export default function WikiLibraryLoading() {
  return (
    <div
      className="content library"
      aria-busy="true"
      data-testid="wiki-library-loading-skeleton"
    >
      {/* 1. 히어로 헤더 스켈레톤 */}
      <section
        className="hero animate-pulse"
        data-od-id="wiki-library-header-skeleton"
      >
        <div>
          <div className="h-8 w-24 rounded-lg bg-[var(--surface)]" />
          <div className="mt-2 h-4 w-64 max-w-full rounded-md bg-[var(--surface)]" />
        </div>
      </section>

      {/* 2. 요약 지표 2개 카드 스켈레톤 */}
      <section className="stats animate-pulse" aria-label="위키 요약 로딩 중">
        {[1, 2].map((i) => (
          <div key={i} className="stat">
            <div className="h-7 w-12 rounded-md bg-[var(--surface)]" />
            <div className="mt-2 h-3.5 w-16 rounded bg-[var(--surface)]" />
          </div>
        ))}
      </section>

      {/* 3. 툴바 & 문서 목록 스켈레톤 */}
      <section
        className="animate-pulse"
        data-od-id="wiki-library-list-skeleton"
      >
        {/* 카테고리 칩 5개 + 검색창 */}
        <div className="toolbar flex items-center justify-between gap-4">
          <div className="chips flex items-center gap-1.5 flex-wrap">
            <div className="h-7 w-12 rounded-lg bg-[var(--surface)]" />
            <div className="h-7 w-12 rounded-lg bg-[var(--surface)] opacity-70" />
            <div className="h-7 w-12 rounded-lg bg-[var(--surface)] opacity-70" />
            <div className="h-7 w-14 rounded-lg bg-[var(--surface)] opacity-70" />
            <div className="h-7 w-10 rounded-lg bg-[var(--surface)] opacity-70" />
          </div>

          <div className="h-9 w-full max-w-[280px] rounded-lg bg-[var(--surface)]" />
        </div>

        {/* 문서 목록 (5개 행) */}
        <div className="doc-list mt-2 divide-y divide-[var(--border)] border-t border-b border-[var(--border)]">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="doc flex items-center justify-between py-3.5 px-3 rounded-none"
            >
              <div className="doc-body flex-1 min-w-0 pr-4 space-y-2.5">
                {/* 상단 메타 뱃지 바 */}
                <div className="flex items-center gap-2">
                  <div className="h-4 w-12 rounded bg-[var(--surface)]" />
                  <div className="h-4 w-16 rounded bg-[var(--surface)] opacity-70" />
                </div>

                {/* 문서 제목 바 */}
                <div className="h-4.5 w-56 max-w-full rounded bg-[var(--surface)]" />

                {/* 발췌문 2줄 바 */}
                <div className="space-y-1.5">
                  <div className="h-3 w-full max-w-[500px] rounded bg-[var(--surface)] opacity-60" />
                  <div className="h-3 w-3/4 max-w-[360px] rounded bg-[var(--surface)] opacity-60" />
                </div>
              </div>

              <div className="h-4 w-4 rounded bg-[var(--surface)] opacity-40 flex-none" />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
