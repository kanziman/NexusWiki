import Link from "next/link";

import {
  decisionLabels,
  experimentSnapshot,
  featuredAdoption,
  type Decision,
  type Experiment,
  type FeaturedAdoption,
  type Snapshot,
} from "@/lib/experiments";

// ⚠️ 이 섹션의 링크는 모두 prefetch를 끈다. 켜 두면 세션이 있는 방문자가 랜딩을 열기만 해도
// 대상 경로의 미들웨어와 서버 렌더링이 돌아 인증 서버와 DB 요청이 생긴다.

/** 실행 출처별 상세 화면. 매핑이 없는 출처는 평가 설계 페이지로 보낸다. */
const detailHref: Partial<Record<Experiment["run_source"], string>> = {
  research: "/showcase/evidence-research",
};

const decisionTone: Record<Decision["status"], string> = {
  adopted: "bg-[var(--good-soft)] text-[var(--good)]",
  not_adopted: "bg-[var(--warning-soft)] text-[var(--warning)]",
  deferred: "bg-[var(--surface)] text-[var(--muted)]",
};

const evaluationPages = [
  {
    href: "/showcase/evaluation",
    title: "평가 설계",
    body: "채점 기준 검증부터 실패 통제, 도입 판단까지 평가 기록 전체를 한 페이지에서 봅니다.",
  },
  {
    href: "/showcase/controlled-ai",
    title: "통제 전후 비교",
    body: "합성 시나리오로 측정한 AI 통제 전후의 동작을 나란히 비교합니다.",
  },
  {
    href: "/showcase/regression",
    title: "회귀 작업대",
    body: "평가 실행을 비교해 문항별 개선과 회귀, 비용과 지연을 분석합니다.",
  },
] as const;

function ArrowIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="shrink-0"
    >
      <path d="M5 12h14m-7-7 7 7-7 7" />
    </svg>
  );
}

function FeaturedExperiment({
  experiment,
  synthetic,
}: {
  experiment: FeaturedAdoption;
  synthetic: boolean;
}) {
  const { conditions } = experiment.criteria;
  const { decision } = experiment;
  const met = conditions.filter((item) => item.met).length;
  const unmet = conditions.filter((item) => !item.met);
  const href = detailHref[experiment.run_source] ?? "/showcase/evaluation";

  return (
    <article
      aria-labelledby="featured-experiment-title"
      className="mb-5 min-w-0 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 md:p-7"
    >
      <p className="mb-4 text-[12px] font-semibold text-[var(--accent)]">
        대표 실험{synthetic ? " · 합성 시나리오 기준" : ""}
      </p>
      <div className="grid min-w-0 grid-cols-1 gap-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] md:gap-10">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2.5">
            <h3
              id="featured-experiment-title"
              className="text-xl font-extrabold tracking-tight"
            >
              {experiment.title}
            </h3>
            <span
              className={`rounded-md px-2 py-0.5 text-[12px] font-bold ${decisionTone[decision.status]}`}
            >
              {decisionLabels[decision.status]}
            </span>
          </div>
          <p className="mb-5 break-keep text-sm leading-relaxed text-[var(--muted)]">
            {experiment.question}
          </p>
          <p className="mb-5 text-base font-bold">
            원래 기준 {conditions.length}개 중 {met}개 충족
          </p>
          <Link
            href={href}
            prefetch={false}
            className="nw-focus-ring inline-flex items-center gap-2 rounded-lg text-sm font-semibold text-[var(--accent)] hover:underline"
          >
            실험 기록 자세히 보기
            <ArrowIcon />
          </Link>
        </div>

        {unmet.length > 0 ? (
          <div className="min-w-0 border-t border-[var(--border)] pt-5 md:border-l md:border-t-0 md:pl-8 md:pt-0">
            <p className="mb-3 text-[12px] font-semibold text-[var(--muted)]">
              미충족 기준
            </p>
            <ul className="flex flex-col gap-3">
              {unmet.map((item) => (
                <li key={item.key} className="min-w-0">
                  <p className="text-sm font-semibold">{item.label}</p>
                  <p className="break-words text-sm text-[var(--muted)]">
                    실제 {item.actual} · 허용 {item.limit}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </article>
  );
}

/**
 * 랜딩의 평가 소개. 대표 실험 판정은 커밋된 실험 스냅샷 값만 쓴다.
 * 계약: openspec/specs/public-marketing-landing/spec.md (기록된 평가 판정의 랜딩 소개)
 */
export function PublicLandingEvaluation({
  snapshot = experimentSnapshot,
}: {
  snapshot?: Snapshot;
}) {
  const featured = featuredAdoption(snapshot);

  return (
    <section
      aria-labelledby="evaluation-intro-title"
      className="border-t border-[var(--border)] px-6 py-16 md:py-20"
    >
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 max-w-2xl">
          <h2
            id="evaluation-intro-title"
            className="scroll-mt-28 mb-4 text-2xl font-extrabold tracking-tight md:text-3xl"
          >
            AI의 답변을, 검증하며 개선합니다.
          </h2>
          <p className="break-keep text-base leading-relaxed text-[var(--muted)]">
            기대한 사실과 실제 답변을 대조합니다. 변경 전후의 품질과 비용을
            비교하고, 실험 결과로 기능 도입을 결정합니다. 실제 실험의 결과와
            한계까지 공개합니다.
          </p>
        </div>

        {featured ? (
          <FeaturedExperiment
            experiment={featured}
            synthetic={snapshot.synthetic === true}
          />
        ) : null}

        <ul className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {evaluationPages.map((page) => (
            <li key={page.href} className="min-w-0">
              <Link
                href={page.href}
                prefetch={false}
                className="nw-focus-ring group flex h-full min-w-0 flex-col rounded-2xl border border-[var(--border)] p-5 transition-colors hover:bg-[var(--surface)]"
              >
                <span className="mb-2 inline-flex items-center justify-between gap-2 text-base font-bold group-hover:text-[var(--accent)]">
                  {page.title}
                  <ArrowIcon />
                </span>
                <span className="break-keep text-sm leading-relaxed text-[var(--muted)]">
                  {page.body}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
