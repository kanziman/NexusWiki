import React from "react";

export default function SourcesLoading() {
  return (
    <div
      className="content sources"
      aria-busy="true"
      data-testid="sources-loading-skeleton"
    >
      {/* 스켈레톤은 실제 목록과 같은 골격이어야 한다. 옛 3칸 `.stats` 줄과
          6열 테이블을 그대로 두면 로딩→렌더 전환에서 헤더 아래 높이가 튀고,
          카드 행이 테이블 줄처럼 보였다가 바뀐다. */}
      {/* 1. 히어로 헤더 스켈레톤 */}
      <section className="hero animate-pulse flex items-start justify-between">
        <div>
          <div className="h-8 w-36 rounded-lg bg-[var(--surface)]" />
          <div className="mt-2 h-4 w-80 max-w-full rounded-md bg-[var(--surface)]" />
        </div>
        <div className="h-9 w-28 rounded-lg bg-[var(--surface)]" />
      </section>

      {/* 2. 파이프라인 요약 벤토 4칸 */}
      <section
        className="mt-8 mb-2 grid grid-cols-2 gap-3.5 md:grid-cols-4 animate-pulse"
        aria-label="파이프라인 요약 로딩 중"
        data-testid="sources-metric-skeleton"
      >
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="flex flex-col gap-2.5 overflow-hidden rounded-[14px] border border-[var(--border)] bg-[var(--surface)] px-[18px] py-4"
          >
            <div className="h-3 w-20 rounded bg-[var(--border)]" />
            <div className="h-7 w-12 rounded-md bg-[var(--border)]" />
            <div className="h-3 w-24 rounded bg-[var(--border)]" />
          </div>
        ))}
      </section>

      {/* 3. 툴바 & 카드-로우 스켈레톤 */}
      <section className="animate-pulse">
        {/* 툴바: 세그먼트 탭 3개 + 검색창. 본문과 같은 36px 높이를 쓴다 —
            스켈레톤만 다른 높이면 전환에서 툴바 줄이 흔들린다. */}
        <div className="toolbar flex items-center justify-between gap-4">
          <div className="flex h-9 items-center gap-1">
            <div className="h-9 w-20 rounded-lg bg-[var(--surface)]" />
            <div className="h-9 w-16 rounded-lg bg-[var(--surface)] opacity-70" />
            <div className="h-9 w-32 rounded-lg bg-[var(--surface)] opacity-70" />
          </div>

          <div className="h-9 w-full max-w-[360px] rounded-lg bg-[var(--surface)]" />
        </div>

        {/* 목록 뼈대. 컬럼 정의는 본문과 마찬가지로 컨테이너에 한 번만 둔다. */}
        <div
          className="mt-3 overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--bg)]"
          data-testid="sources-rows-skeleton"
          style={
            {
              "--sources-cols":
                "minmax(0,26fr) minmax(0,24fr) minmax(0,14fr) minmax(0,20fr) minmax(0,16fr)",
            } as React.CSSProperties
          }
        >
          <div
            className="hidden items-center gap-4 border-b border-[var(--border)] bg-[var(--surface)] px-4 py-2.5 md:grid"
            style={{ gridTemplateColumns: "var(--sources-cols)" }}
          >
            <div className="h-3.5 w-16 rounded bg-[var(--border)]" />
            <div className="h-3.5 w-28 rounded bg-[var(--border)]" />
            <div className="h-3.5 w-20 rounded bg-[var(--border)] md:ml-auto" />
            <div className="h-3.5 w-16 rounded bg-[var(--border)]" />
            <div className="h-3.5 w-10 rounded bg-[var(--border)] md:ml-auto" />
          </div>

          <div className="divide-y divide-[var(--border)]">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div
                key={i}
                className="grid grid-cols-1 items-center gap-3 px-4 py-3 md:h-[72px] md:gap-4 md:py-0 md:[grid-template-columns:var(--sources-cols)]"
              >
                {/* 소스 파일 */}
                <div className="flex min-w-0 items-center gap-2.5">
                  <div className="h-[22px] w-9 flex-none rounded-[5px] bg-[var(--surface)]" />
                  <div className="min-w-0 flex-1 space-y-1.5">
                    <div className="h-4 w-36 max-w-full rounded bg-[var(--surface)]" />
                    <div className="h-3 w-44 max-w-full rounded bg-[var(--surface)] opacity-70" />
                  </div>
                </div>

                {/* 연결된 위키 문서 — 칩 2개 고정 */}
                <div className="flex items-center gap-1.5">
                  <div className="h-[22px] w-24 rounded-md bg-[var(--surface)]" />
                  <div className="h-[22px] w-20 rounded-md bg-[var(--surface)] opacity-70" />
                </div>

                {/* 청크 및 좌표 */}
                <div className="space-y-1.5 md:flex md:flex-col md:items-end">
                  <div className="h-4 w-14 rounded bg-[var(--surface)]" />
                  <div className="h-3 w-24 rounded bg-[var(--surface)] opacity-70" />
                </div>

                {/* 파이프라인 */}
                <div className="space-y-1.5">
                  <div className="h-4 w-32 rounded bg-[var(--surface)]" />
                  <div className="h-2 w-24 rounded bg-[var(--surface)] opacity-60" />
                </div>

                {/* 작업 */}
                <div className="flex items-center gap-2 md:justify-end">
                  <div className="h-3.5 w-12 rounded bg-[var(--surface)]" />
                  <div className="h-6 w-[30px] rounded bg-[var(--surface)] opacity-70" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
