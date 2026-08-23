import React from "react";

export default function SourcesLoading() {
  return (
    <div
      className="content sources"
      aria-busy="true"
      data-testid="sources-loading-skeleton"
    >
      {/* 1. 히어로 헤더 스켈레톤 */}
      <section className="hero animate-pulse flex items-start justify-between">
        <div>
          <div className="h-8 w-36 rounded-lg bg-[var(--surface)]" />
          <div className="mt-2 h-4 w-80 max-w-full rounded-md bg-[var(--surface)]" />
        </div>
        <div className="h-9 w-28 rounded-lg bg-[var(--surface)]" />
      </section>

      {/* 2. 요약 통계 3개 카드 스켈레톤 */}
      <section className="stats animate-pulse" aria-label="소스 통계 로딩 중">
        {[1, 2, 3].map((i) => (
          <div key={i} className="stat">
            <div className="h-7 w-12 rounded-md bg-[var(--surface)]" />
            <div className="mt-2 h-3.5 w-24 rounded bg-[var(--surface)]" />
          </div>
        ))}
      </section>

      {/* 3. 툴바 & 테이블 스켈레톤 */}
      <section className="animate-pulse">
        {/* 툴바: 탭 3개 + 검색창 */}
        <div className="toolbar flex items-center justify-between gap-4">
          <div className="tabs flex items-center gap-1">
            <div className="h-8 w-20 rounded-lg bg-[var(--surface)]" />
            <div className="h-8 w-16 rounded-lg bg-[var(--surface)] opacity-70" />
            <div className="h-8 w-28 rounded-lg bg-[var(--surface)] opacity-70" />
          </div>

          <div className="h-9 w-full max-w-[280px] rounded-lg bg-[var(--surface)]" />
        </div>

        {/* 테이블 뼈대 */}
        <div className="table-wrap overflow-x-auto rounded-lg border border-[var(--border)] bg-[var(--bg)] mt-3">
          <table className="table w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[var(--border)] bg-[var(--surface)]/60">
                <th className="py-2.5 px-4">
                  <div className="h-3.5 w-16 rounded bg-[var(--surface)]" />
                </th>
                <th className="py-2.5 px-4">
                  <div className="h-3.5 w-24 rounded bg-[var(--surface)]" />
                </th>
                <th className="py-2.5 px-4">
                  <div className="h-3.5 w-20 rounded bg-[var(--surface)]" />
                </th>
                <th className="py-2.5 px-4">
                  <div className="h-3.5 w-24 rounded bg-[var(--surface)]" />
                </th>
                <th className="py-2.5 px-4">
                  <div className="h-3.5 w-12 rounded bg-[var(--surface)]" />
                </th>
                <th className="py-2.5 px-4 text-right">
                  <div className="h-3.5 w-12 rounded bg-[var(--surface)] ml-auto" />
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <tr key={i} className="py-3 px-4">
                  {/* 파일명 & 포맷 */}
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2.5">
                      <div className="h-5 w-8 rounded bg-[var(--surface)] flex-none" />
                      <div className="space-y-1.5 flex-1 min-w-0">
                        <div className="h-4 w-36 max-w-full rounded bg-[var(--surface)]" />
                        <div className="h-3 w-20 rounded bg-[var(--surface)] opacity-70" />
                      </div>
                    </div>
                  </td>
                  {/* 연결된 위키 문서 */}
                  <td className="py-3 px-4">
                    <div className="flex gap-1.5">
                      <div className="h-5 w-20 rounded-md bg-[var(--surface)]" />
                      <div className="h-5 w-16 rounded-md bg-[var(--surface)]" />
                    </div>
                  </td>
                  {/* 청크 및 좌표 */}
                  <td className="py-3 px-4">
                    <div className="space-y-1.5">
                      <div className="h-4 w-14 rounded bg-[var(--surface)]" />
                      <div className="h-3 w-24 rounded bg-[var(--surface)] opacity-70" />
                    </div>
                  </td>
                  {/* 파이프라인 상태 */}
                  <td className="py-3 px-4">
                    <div className="space-y-1.5">
                      <div className="h-4 w-36 rounded bg-[var(--surface)]" />
                      <div className="h-2 w-28 rounded bg-[var(--surface)] opacity-60" />
                    </div>
                  </td>
                  {/* 업로드 일시 */}
                  <td className="py-3 px-4">
                    <div className="h-3.5 w-16 rounded bg-[var(--surface)]" />
                  </td>
                  {/* 상세 보기 액션 */}
                  <td className="py-3 px-4 text-right">
                    <div className="h-3.5 w-12 rounded bg-[var(--surface)] ml-auto" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
