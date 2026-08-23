import React from "react";

export default function WorkspaceHomeLoading() {
  return (
    <div
      className="content"
      aria-busy="true"
      data-testid="workspace-home-skeleton"
    >
      {/* 1. 지식 그룹/워크스페이스 히어로 헤더 스켈레톤 */}
      <section
        className="context animate-pulse"
        data-od-id="workspace-header-skeleton"
      >
        <div>
          <div className="title-row">
            <div className="h-8 w-44 rounded-lg bg-[var(--surface)]" />
          </div>
          <div className="mt-2 h-4 w-96 max-w-full rounded-md bg-[var(--surface)]" />
        </div>
      </section>

      {/* 2. 현황 요약 통계 4개 카드 스켈레톤 */}
      <section
        className="stats animate-pulse"
        aria-label="워크스페이스 현황 로딩 중"
      >
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="stat">
            <div className="h-7 w-12 rounded-md bg-[var(--surface)]" />
            <div className="mt-2 h-3.5 w-20 rounded bg-[var(--surface)]" />
          </div>
        ))}
      </section>

      {/* 3. 중앙 질문창 (AskHero 둥근 뼈대) 스켈레톤 */}
      <section className="ask animate-pulse" aria-label="질문 입력창 로딩 중">
        <div className="ask-main">
          <div className="h-5 w-5 rounded-full bg-[var(--surface)] flex-none" />
          <div className="flex-1 space-y-2">
            <div className="h-5 w-3/4 rounded-md bg-[var(--surface)]" />
            <div className="h-4 w-1/2 rounded-md bg-[var(--surface)] opacity-70" />
          </div>
        </div>

        <div className="ask-bottom mt-4 flex items-center justify-between border-t border-[var(--border)] pt-3">
          <div className="h-7 w-32 rounded-lg bg-[var(--surface)]" />
          <div className="h-8 w-24 rounded-lg bg-[var(--surface)]" />
        </div>
      </section>

      {/* 4. 2열 지식 그리드 스켈레톤 */}
      <div className="sections">
        {/* 좌측: 컴파일된 위키 문서 (5개 행) */}
        <section className="animate-pulse" aria-label="위키 문서 로딩 중">
          <div className="section-head mb-3 flex items-center justify-between">
            <div className="h-5 w-36 rounded-md bg-[var(--surface)]" />
            <div className="h-4 w-16 rounded bg-[var(--surface)]" />
          </div>

          <div className="doc-list divide-y divide-[var(--border)]">
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="doc flex items-center justify-between py-3.5 px-3"
              >
                <div className="doc-body flex-1 min-w-0 pr-4 space-y-2">
                  <div className="h-4 w-48 max-w-full rounded-md bg-[var(--surface)]" />
                  <div className="h-3 w-32 rounded bg-[var(--surface)] opacity-70" />
                </div>
                <div className="h-4 w-4 rounded bg-[var(--surface)] opacity-40 flex-none" />
              </div>
            ))}
          </div>
        </section>

        {/* 우측: 작성 대기 백로그 (3개 행) */}
        <section
          className="backlog animate-pulse"
          aria-label="작성 대기 백로그 로딩 중"
        >
          <div className="section-head mb-3 flex items-center justify-between">
            <div className="h-5 w-32 rounded-md bg-[var(--surface)]" />
            <div className="h-4 w-16 rounded bg-[var(--surface)]" />
          </div>

          <div className="doc-list divide-y divide-[var(--border)]">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="doc flex items-center justify-between py-3.5 px-3"
              >
                <div className="doc-body flex-1 min-w-0 pr-4 space-y-2">
                  <div className="h-4 w-44 max-w-full rounded-md bg-[var(--surface)]" />
                  <div className="h-3 w-36 rounded bg-[var(--surface)] opacity-70" />
                </div>
                <div className="h-4 w-4 rounded bg-[var(--surface)] opacity-40 flex-none" />
              </div>
            ))}
          </div>

          {/* 소스 연결 콜아웃 박스 */}
          <div className="source-line mt-4 flex items-center justify-between rounded-xl border border-[var(--border)] p-4 bg-[var(--surface)]/30">
            <div className="space-y-1.5">
              <div className="h-4 w-36 rounded-md bg-[var(--surface)]" />
              <div className="h-3 w-52 rounded bg-[var(--surface)] opacity-70" />
            </div>
            <div className="h-7 w-20 rounded-lg bg-[var(--surface)]" />
          </div>
        </section>
      </div>
    </div>
  );
}
