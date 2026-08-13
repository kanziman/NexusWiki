import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-base border-b border-[var(--nw-rule)] pb-xl sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl">
        <h1 className="text-3xl font-semibold tracking-[-0.04em] text-[var(--nw-ink)] sm:text-4xl">
          {title}
        </h1>
        {description ? (
          <p className="mt-sm text-base leading-7 text-[var(--nw-body)]">
            {description}
          </p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </header>
  );
}

export function SectionHeading({
  title,
  detail,
}: {
  title: string;
  detail?: string;
}) {
  return (
    <div className="flex items-baseline justify-between gap-base">
      <h2 className="text-lg font-semibold tracking-[-0.02em] text-[var(--nw-ink)]">
        {title}
      </h2>
      {detail ? (
        <span className="text-sm text-[var(--nw-muted)]">{detail}</span>
      ) : null}
    </div>
  );
}

export function EmptyState({
  title,
  detail,
  action,
}: {
  title: string;
  detail: string;
  action?: ReactNode;
}) {
  return (
    <section className="flex flex-col items-center gap-sm border-y border-[var(--nw-rule)] px-base py-section text-center">
      <h2 className="text-lg font-semibold text-[var(--nw-ink)]">{title}</h2>
      <p className="max-w-lg text-sm leading-6 text-[var(--nw-muted)]">
        {detail}
      </p>
      {action ? <div className="mt-sm">{action}</div> : null}
    </section>
  );
}

export function StatusBadge({
  tone = "neutral",
  children,
}: {
  tone?: "neutral" | "success" | "warning" | "danger";
  children: ReactNode;
}) {
  const colors = {
    neutral: "text-[var(--nw-muted)]",
    success: "text-success-text",
    warning: "text-warning-text",
    danger: "text-primary-error-text",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border border-[var(--nw-rule)] px-sm py-xs text-xs font-medium ${colors[tone]}`}
    >
      {children}
    </span>
  );
}

export function DetailHeader({
  libraryHref,
  libraryLabel,
  kind,
  title,
  meta,
  navigationLabel = "라이브러리 탐색",
  breadcrumb,
}: {
  libraryHref: string;
  libraryLabel: string;
  kind: string;
  title: string;
  meta?: ReactNode;
  navigationLabel?: string;
  breadcrumb?: string;
}) {
  return (
    <header className="flex flex-col gap-sm border-b border-[var(--nw-rule)] pb-lg">
      <nav aria-label={navigationLabel}>
        <a
          href={libraryHref}
          className="nw-focus-ring w-fit text-sm text-[var(--nw-muted)] hover:text-[var(--nw-ink)]"
        >
          ← {libraryLabel}
        </a>
        {breadcrumb ? <span className="sr-only">{breadcrumb}</span> : null}
      </nav>
      <div className="flex flex-wrap items-center gap-sm">
        <span className="text-xs font-medium text-[var(--nw-muted)]">
          {kind}
        </span>
        {meta}
      </div>
      <h1 className="text-3xl font-semibold tracking-[-0.04em] text-[var(--nw-ink)]">
        {title}
      </h1>
    </header>
  );
}
