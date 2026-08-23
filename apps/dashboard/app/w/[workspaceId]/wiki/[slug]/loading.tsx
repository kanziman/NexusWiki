import React from "react";

export default function WikiDetailLoading() {
  return (
    <div
      className="reader-layout"
      aria-busy="true"
      data-testid="wiki-detail-loading-skeleton"
    >
      <article className="reader animate-pulse">
        {/* 상단 브레드크럼 경로 */}
        <div className="h-3.5 w-24 rounded bg-[var(--surface)] opacity-70" />

        {/* 문서 타이틀 + 즐겨찾기 버튼 */}
        <div className="title-row mt-2 flex items-center justify-between">
          <div className="h-8 w-72 max-w-[80%] rounded-lg bg-[var(--surface)]" />
          <div className="h-6 w-6 rounded-full bg-[var(--surface)] opacity-50 flex-none" />
        </div>

        {/* 거버넌스 메타데이터 바 */}
        <div className="governance mt-3 flex items-center gap-2">
          <div className="h-5 w-14 rounded-md bg-[var(--surface)]" />
          <div className="h-5 w-24 rounded-md bg-[var(--surface)] opacity-70" />
        </div>

        {/* 컴파일 안내 캡션 */}
        <div className="mt-3 h-3.5 w-64 rounded bg-[var(--surface)] opacity-60" />

        {/* 본문 렌더링 스켈레톤 (문단 + 블록) */}
        <div className="article mt-8 space-y-4">
          <div className="space-y-2">
            <div className="h-4 w-full rounded bg-[var(--surface)]" />
            <div className="h-4 w-[92%] rounded bg-[var(--surface)]" />
            <div className="h-4 w-[85%] rounded bg-[var(--surface)]" />
            <div className="h-4 w-[60%] rounded bg-[var(--surface)]" />
          </div>

          {/* 중간 코드/테이블 박스 뼈대 */}
          <div className="my-6 h-28 w-full rounded-xl border border-[var(--border)] bg-[var(--surface)]/40 p-4 space-y-2">
            <div className="h-3.5 w-32 rounded bg-[var(--surface)]" />
            <div className="h-3.5 w-3/4 rounded bg-[var(--surface)] opacity-70" />
            <div className="h-3.5 w-1/2 rounded bg-[var(--surface)] opacity-50" />
          </div>

          <div className="space-y-2">
            <div className="h-4 w-[96%] rounded bg-[var(--surface)]" />
            <div className="h-4 w-[88%] rounded bg-[var(--surface)]" />
            <div className="h-4 w-[45%] rounded bg-[var(--surface)]" />
          </div>
        </div>

        {/* 하단 관련 문서 섹션 */}
        <div className="mt-10 border-t border-[var(--border)] pt-6 space-y-3">
          <div className="h-4 w-20 rounded bg-[var(--surface)]" />
          <div className="flex gap-2">
            <div className="h-6 w-32 rounded-md bg-[var(--surface)] opacity-70" />
            <div className="h-6 w-28 rounded-md bg-[var(--surface)] opacity-70" />
          </div>
        </div>
      </article>

      {/* 우측 인용 소스 및 목차 사이드 패널 뼈대 */}
      <aside className="reader-aside hidden lg:block animate-pulse w-72 flex-none space-y-4 pl-6 border-l border-[var(--border)]">
        <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
          <div className="h-5 w-24 rounded bg-[var(--surface)]" />
          <div className="h-4 w-12 rounded bg-[var(--surface)] opacity-60" />
        </div>

        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div
              key={i}
              className="rounded-xl border border-[var(--border)] bg-[var(--surface)]/30 p-3.5 space-y-2"
            >
              <div className="h-4 w-36 rounded bg-[var(--surface)]" />
              <div className="h-3 w-48 rounded bg-[var(--surface)] opacity-70" />
              <div className="h-3 w-28 rounded bg-[var(--surface)] opacity-50" />
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}
