import React from "react";

export default function WikiLibraryLoading() {
  return (
    <div
      className="content library"
      aria-busy="true"
      data-testid="wiki-library-loading-skeleton"
    >
      {/* 스켈레톤은 실제 라이브러리 본문과 같은 골격이어야 한다. 옛 2칸
          `.stats` 줄과 구분선 행을 그대로 두면 로딩→렌더 전환에서 헤더
          아래 높이가 튀고, 카드 행이 리스트 줄처럼 보였다가 바뀐다. */}
      {/* 1. 히어로 헤더 스켈레톤 (타이틀 + 문서 수 뱃지) */}
      <section
        className="hero animate-pulse"
        data-od-id="wiki-library-header-skeleton"
      >
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="h-8 w-40 rounded-lg bg-[var(--surface)]" />
            <div className="h-[26px] w-10 rounded-full bg-[var(--surface)]" />
          </div>
          <div className="mt-2 h-4 w-80 max-w-full rounded-md bg-[var(--surface)]" />
        </div>
      </section>

      {/* 2. 지식 건강 벤토 5칸. 검증률 + 카테고리 4. */}
      <section
        className="mt-8 mb-2 grid grid-cols-2 gap-3.5 md:grid-cols-3 lg:grid-cols-5 animate-pulse"
        aria-label="지식 건강 로딩 중"
        data-testid="wiki-library-health-skeleton"
      >
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className="flex flex-col gap-2.5 overflow-hidden rounded-[14px] border border-[var(--border)] bg-[var(--surface)] px-[18px] py-4"
          >
            <div className="h-3 w-14 rounded bg-[var(--border)]" />
            <div className="h-7 w-12 rounded-md bg-[var(--border)]" />
            <div className="h-3 w-20 rounded bg-[var(--border)]" />
          </div>
        ))}
      </section>

      {/* 3. 툴바 & 카드 행 스켈레톤 */}
      <section
        className="animate-pulse"
        data-od-id="wiki-library-list-skeleton"
      >
        <div className="toolbar flex items-center justify-between gap-4">
          <div className="chips flex items-center gap-1.5 flex-wrap">
            <div className="h-7 w-16 rounded-lg bg-[var(--surface)]" />
            <div className="h-7 w-16 rounded-lg bg-[var(--surface)] opacity-70" />
            <div className="h-7 w-[4.5rem] rounded-lg bg-[var(--surface)] opacity-70" />
            <div className="h-7 w-[4.5rem] rounded-lg bg-[var(--surface)] opacity-70" />
            <div className="h-7 w-14 rounded-lg bg-[var(--surface)] opacity-70" />
          </div>

          <div className="h-9 w-full max-w-[280px] rounded-lg bg-[var(--surface)]" />
        </div>

        <div className="wiki-cards">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="wiki-card flex items-start gap-4 rounded-xl border border-[var(--border)] bg-[var(--bg)] p-4"
            >
              <div className="flex-1 min-w-0 space-y-2.5">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-10 rounded bg-[var(--surface)]" />
                  <div className="h-3 w-12 rounded bg-[var(--surface)] opacity-70" />
                  <div className="h-3 w-16 rounded bg-[var(--surface)] opacity-70" />
                </div>
                <div className="h-5 w-56 max-w-full rounded bg-[var(--surface)]" />
                <div className="space-y-1.5">
                  <div className="h-3 w-full max-w-3xl rounded bg-[var(--surface)] opacity-60" />
                  <div className="h-3 w-3/4 max-w-xl rounded bg-[var(--surface)] opacity-60" />
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
