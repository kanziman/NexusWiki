type FaqItem = {
  q: string;
  a: string;
};

type PublicLandingFaqProps = {
  items: readonly FaqItem[];
  openIndex: number | null;
  onToggle: (index: number) => void;
};

export function PublicLandingFaq({
  items,
  openIndex,
  onToggle,
}: PublicLandingFaqProps) {
  return (
    <section
      id="faq"
      aria-labelledby="faq-heading"
      className="mx-auto max-w-3xl scroll-mt-28 px-4 py-20 sm:px-6"
    >
      <div className="mb-12 text-center">
        <p className="mb-3 text-sm font-semibold text-[var(--accent)]">
          제품을 시작하기 전에 확인하세요
        </p>
        <h2 id="faq-heading" className="text-3xl font-extrabold tracking-tight">
          자주 묻는 질문
        </h2>
      </div>

      <div className="space-y-3 text-left">
        {items.map((item, index) => {
          const expanded = openIndex === index;
          const buttonId = `landing-faq-button-${index}`;
          const panelId = `landing-faq-panel-${index}`;

          return (
            <div
              key={item.q}
              className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)]"
            >
              <h3>
                <button
                  id={buttonId}
                  type="button"
                  onClick={() => onToggle(index)}
                  className="nw-focus-ring flex min-h-14 w-full items-center justify-between gap-4 rounded-xl p-5 text-left text-[15px] font-bold transition-colors hover:bg-[var(--surface-raised)]"
                  aria-expanded={expanded}
                  aria-controls={panelId}
                >
                  <span>{item.q}</span>
                  <svg
                    className={`shrink-0 text-[var(--muted)] transition-transform duration-200 motion-reduce:transition-none ${
                      expanded ? "rotate-180 text-[var(--accent)]" : ""
                    }`}
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </button>
              </h3>
              {expanded ? (
                <div
                  id={panelId}
                  role="region"
                  aria-labelledby={buttonId}
                  className="px-5 pb-5 text-sm leading-relaxed text-[var(--muted)]"
                >
                  {item.a}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}
