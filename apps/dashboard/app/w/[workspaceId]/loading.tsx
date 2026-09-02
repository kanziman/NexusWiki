import React from "react";

export default function WorkspaceHomeLoading() {
  return (
    <div
      className="content"
      aria-busy="true"
      data-testid="workspace-home-skeleton"
    >
      {/* 스켈레톤은 실제 홈 본문과 같은 골격이어야 한다. 벤토 메트릭 4칸과
          `.sections` 비대칭(1.4fr / 1fr) 그리드를 맞추지 않으면 로딩→렌더
          전환에서 레이아웃이 튄다. */}
      {/* 1. 지식 그룹/워크스페이스 히어로 헤더 스켈레톤 */}
      <section
        className="context animate-pulse"
        data-od-id="workspace-header-skeleton"
      >
        <div>
          <div className="title-row">
            <div className="h-8 w-44 rounded-lg bg-[var(--surface)]" />
            <div className="h-[26px] w-[108px] rounded-full bg-[var(--surface)]" />
          </div>
          <div className="mt-2 h-4 w-96 max-w-full rounded-md bg-[var(--surface)]" />
        </div>
      </section>

      {/* 2. 벤토 지식 건강 메트릭 4칸. 옛 `.stats` 줄은 본문 카드 높이와
          달라 전환 때 본문이 아래로 밀린다. */}
      <section
        className="mt-8 mb-7 grid grid-cols-2 gap-3.5 lg:grid-cols-4 animate-pulse"
        aria-label="워크스페이스 현황 로딩 중"
        data-testid="workspace-home-metric-skeleton"
      >
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="flex flex-col gap-2.5 overflow-hidden rounded-[14px] border border-[var(--border)] bg-[var(--surface)] px-[18px] py-4"
          >
            <div className="flex items-center justify-between">
              <div className="h-3 w-20 rounded bg-[var(--border)]" />
              <div className="h-4 w-4 rounded bg-[var(--border)]" />
            </div>
            <div className="flex items-baseline gap-2">
              <div className="h-7 w-12 rounded-md bg-[var(--border)]" />
              <div className="h-4 w-16 rounded bg-[var(--border)]" />
            </div>
            <div className="mt-1 h-1 overflow-hidden rounded-full bg-[var(--border)]">
              <div className="h-full w-2/3 rounded-full bg-[var(--border)]" />
            </div>
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

      {/* 4. 비대칭 6:4 지식 그리드. 홈 KnowledgeGrid 와 같은 `.sections` 를
          쓴다 — 비율을 스켈레톤에서만 바꾸면 로딩→렌더에서 그리드가 튄다. */}
      <div className="sections" data-testid="workspace-home-grid-skeleton">
        {/* 좌측: 컴파일된 위키 문서 (5개 행) */}
        <section className="animate-pulse" aria-label="위키 문서 로딩 중">
          <div className="section-head">
            <div className="h-5 w-36 rounded-md bg-[var(--surface)]" />
            <div className="h-4 w-16 rounded bg-[var(--surface)]" />
          </div>

          <div className="doc-list">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="doc">
                <div className="doc-body">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <div className="h-3 w-10 rounded bg-[var(--surface)]" />
                    <div className="h-3 w-12 rounded bg-[var(--surface)] opacity-70" />
                    <div className="h-3 w-16 rounded bg-[var(--surface)] opacity-70" />
                  </div>
                  <div className="h-4 w-48 max-w-full rounded-md bg-[var(--surface)]" />
                </div>
                <div className="h-4 w-4 rounded bg-[var(--surface)] opacity-40 flex-none" />
              </div>
            ))}
          </div>
        </section>

        {/* 우측: 작성 대기 백로그 (3개 행) */}
        <section
          className="backlog animate-pulse"
          aria-label="지식 공백 로딩 중"
        >
          <div className="section-head">
            <div className="h-5 w-32 rounded-md bg-[var(--surface)]" />
            <div className="h-4 w-16 rounded bg-[var(--surface)]" />
          </div>

          <div className="doc-list">
            {[1, 2, 3].map((i) => (
              <div key={i} className="doc">
                <div className="doc-body">
                  <div className="h-4 w-44 max-w-full rounded-md bg-[var(--surface)]" />
                  <div className="h-3 w-36 rounded bg-[var(--surface)] opacity-70" />
                </div>
                <div className="h-7 w-20 rounded-lg bg-[var(--surface)] flex-none" />
              </div>
            ))}
          </div>

          {/* 소스 연결 콜아웃 박스 */}
          <div className="source-line">
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
