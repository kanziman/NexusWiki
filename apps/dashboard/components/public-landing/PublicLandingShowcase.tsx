import type {
  PresetItem,
  WorkspaceScenario,
} from "@/components/public-landing/content";

type PublicLandingShowcaseProps = {
  scenarios: WorkspaceScenario[];
  currentWorkspaceIndex: number;
  currentPresetIndex: number;
  onWorkspaceChange: (index: number) => void;
  onPresetChange: (index: number) => void;
};

function PresetIcon({ type }: { type: PresetItem["iconType"] }) {
  const common = {
    width: 14,
    height: 14,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    className: "shrink-0",
  };

  if (type === "flame") {
    return (
      <svg {...common}>
        <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 3.5z" />
      </svg>
    );
  }
  if (type === "lightbulb") {
    return (
      <svg {...common}>
        <line x1="9" y1="18" x2="15" y2="18" />
        <line x1="10" y1="22" x2="14" y2="22" />
        <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14" />
      </svg>
    );
  }
  if (type === "bolt") {
    return (
      <svg {...common}>
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
      </svg>
    );
  }
  if (type === "lock") {
    return (
      <svg {...common}>
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

function SourceIcon({ wiki = false }: { wiki?: boolean }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="shrink-0"
    >
      {wiki ? (
        <>
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        </>
      ) : (
        <>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </>
      )}
    </svg>
  );
}

export function PublicLandingShowcase({
  scenarios,
  currentWorkspaceIndex,
  currentPresetIndex,
  onWorkspaceChange,
  onPresetChange,
}: PublicLandingShowcaseProps) {
  const currentWorkspace = scenarios[currentWorkspaceIndex];
  const activeScenario = currentWorkspace.presets[currentPresetIndex];

  return (
    <section
      id="showcase"
      aria-labelledby="showcase-heading"
      className="mx-auto mb-24 max-w-5xl scroll-mt-28 px-4 sm:px-6"
    >
      <div className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--bg)] text-left shadow-xl">
        <div className="flex flex-col gap-3 border-b border-[var(--border)] bg-[var(--surface)] p-4 md:flex-row md:items-center md:justify-between md:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-[var(--good-soft)] px-2.5 py-1 text-xs font-bold text-[var(--good)]">
              <span className="size-1.5 rounded-full bg-current" />
              LIVE DEMO
            </span>
            <strong id="showcase-heading" className="min-w-0 text-sm font-bold">
              {currentWorkspace.workspace}
            </strong>
          </div>

          <div
            role="tablist"
            aria-label="쇼케이스 워크스페이스"
            className="flex max-w-full gap-1 overflow-x-auto rounded-lg bg-[var(--surface-raised)] p-1"
          >
            {scenarios.map((scenario, index) => (
              <button
                key={scenario.workspace}
                id={`showcase-tab-${index}`}
                type="button"
                role="tab"
                aria-selected={currentWorkspaceIndex === index}
                aria-controls="showcase-panel"
                onClick={() => onWorkspaceChange(index)}
                className={`nw-focus-ring inline-flex min-h-9 shrink-0 items-center rounded-md px-3 py-1.5 text-xs font-bold transition-colors ${
                  currentWorkspaceIndex === index
                    ? "bg-[var(--bg)] text-[var(--fg)] shadow-sm"
                    : "text-[var(--muted)] hover:text-[var(--fg)]"
                }`}
              >
                {scenario.shortLabel}
              </button>
            ))}
          </div>
        </div>

        <div className="border-b border-[var(--border)] bg-[var(--bg)] p-5 md:p-6">
          <p className="mb-3 flex items-center gap-1.5 text-xs font-bold text-[var(--muted)]">
            <span aria-hidden="true" className="text-[var(--accent)]">
              ↳
            </span>
            추천 질문을 선택해 원문·위키 인용 답변을 확인해 보세요
          </p>
          <div
            role="group"
            aria-label="추천 질문"
            className="flex flex-wrap gap-2.5"
          >
            {currentWorkspace.presets.map((preset, index) => (
              <button
                key={preset.label}
                type="button"
                aria-pressed={currentPresetIndex === index}
                onClick={() => onPresetChange(index)}
                className={`nw-focus-ring inline-flex min-h-10 items-center gap-2 rounded-full border px-4 py-2 text-left text-xs font-medium transition-colors md:text-sm ${
                  currentPresetIndex === index
                    ? "border-[var(--accent)] bg-[var(--accent)] text-white shadow-sm"
                    : "border-[var(--border)] bg-[var(--surface)] text-[var(--fg)] hover:border-[var(--accent)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)]"
                }`}
              >
                <PresetIcon type={preset.iconType} />
                <span>{preset.label}</span>
              </button>
            ))}
          </div>
        </div>

        <div
          id="showcase-panel"
          role="tabpanel"
          aria-labelledby={`showcase-tab-${currentWorkspaceIndex}`}
          aria-live="polite"
          className="grid grid-cols-1 gap-8 bg-[var(--bg)] p-5 md:p-8 lg:grid-cols-[1.4fr_1fr]"
        >
          <div className="min-w-0">
            <div className="mb-6">
              <span className="mb-1.5 block font-mono text-[11px] font-bold tracking-wider text-[var(--muted)]">
                QUESTION
              </span>
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3.5 text-lg font-bold text-[var(--fg)] shadow-sm">
                {activeScenario.q}
              </div>
            </div>

            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg)] p-5 shadow-sm">
              <span className="mb-2 block font-mono text-[11px] font-bold tracking-wider text-[var(--muted)]">
                NEXUSWIKI GROUNDED ANSWER
              </span>
              <p className="mb-4 text-[15px] leading-relaxed text-[var(--fg)]">
                {activeScenario.a}
              </p>
              <div className="flex flex-wrap gap-2">
                <span className="inline-flex max-w-full items-center gap-1.5 break-all rounded border border-[var(--accent)]/30 bg-[var(--accent-soft)] px-2.5 py-1 text-xs font-semibold text-[var(--accent)]">
                  <SourceIcon />
                  {activeScenario.source}
                </span>
                <span className="inline-flex max-w-full items-center gap-1.5 break-all rounded border border-[var(--accent)]/30 bg-[var(--accent-soft)] px-2.5 py-1 text-xs font-semibold text-[var(--accent)]">
                  <SourceIcon wiki />
                  {activeScenario.wiki}
                </span>
                <span className="inline-flex items-center gap-1.5 rounded border border-[var(--good)]/40 bg-[var(--good-soft)] px-2.5 py-1 text-xs font-semibold text-[var(--good)]">
                  <span aria-hidden="true">✓</span>
                  근거 연결 완료
                </span>
              </div>
            </div>
          </div>

          <aside
            className="flex min-w-0 flex-col gap-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5"
            aria-label="서버 검증 근거"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-bold text-[var(--fg)]">
              <span>서버 검증 근거 뷰어</span>
              <small className="font-mono text-[var(--muted)]">
                4-Channel Hybrid
              </small>
            </div>

            <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)] p-3.5 text-xs">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2 font-mono text-[10px] text-[var(--muted)]">
                <span className="inline-flex items-center gap-1">
                  <SourceIcon /> SOURCE CHUNK
                </span>
                <span className="break-all">{activeScenario.source}</span>
              </div>
              <blockquote className="rounded border border-[var(--border)] bg-[var(--surface)] p-2.5 italic leading-relaxed text-[var(--fg)]">
                {activeScenario.sourceText}
              </blockquote>
            </div>

            <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)] p-3.5 text-xs">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2 font-mono text-[10px] text-[var(--muted)]">
                <span className="inline-flex items-center gap-1">
                  <SourceIcon wiki /> WIKI ENTITY
                </span>
                <span className="break-all">{activeScenario.wiki}</span>
              </div>
              <p className="rounded border border-[var(--border)] bg-[var(--surface)] p-2.5 leading-relaxed text-[var(--fg)]">
                {activeScenario.wikiText}
              </p>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}
