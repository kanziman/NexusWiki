"use client";

import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api-client";

type PipelineRow = {
  type: string;
  step_label: string;
  queued: number | null;
  running: number | null;
  dead: number | null;
};

type OperationsSnapshot = {
  budget: {
    cap_micros: number;
    spent_micros: number;
    remaining_micros: number;
    month_start: string;
    truncated: boolean;
    authoritative: false;
  };
  pipeline: PipelineRow[];
  observed_at: string;
};

export type OperationsPanelProps = { workspaceId: string };

const LOAD_ERROR =
  "운영 현황을 불러오지 못했습니다. 운영 현황 새로고침을 시도해주세요.";
const moneyFormatter = new Intl.NumberFormat("ko-KR", {
  style: "currency",
  currency: "USD",
});
const dateFormatter = new Intl.DateTimeFormat("ko-KR", {
  dateStyle: "medium",
  timeStyle: "short",
});

function formatMicros(micros: number) {
  return moneyFormatter.format(micros / 1_000_000);
}

function countOrUnavailable(value: number | null) {
  return value === null ? "집계 불가" : `${value}건`;
}

function deadCountOrUnavailable(value: number | null) {
  if (value === null) return "집계 불가";
  return value > 0 ? `실패한 작업 ${value}건` : "0건";
}

export function OperationsPanel({ workspaceId }: OperationsPanelProps) {
  const [snapshot, setSnapshot] = useState<OperationsSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState(false);

  async function load(manual: boolean) {
    if (manual) setRefreshing(true);
    else setLoading(true);
    setLoadError(false);
    try {
      const next = await apiFetch<OperationsSnapshot>(
        `/workspaces/${workspaceId}/operations`,
      );
      setSnapshot(next);
    } catch {
      // apiFetch 오류의 raw detail은 운영 정보가 될 수 있으므로 계약 문구만 렌더한다.
      setLoadError(true);
    } finally {
      if (manual) setRefreshing(false);
      else setLoading(false);
    }
  }

  useEffect(() => {
    void load(false);
    // 탭 진입 시 한 번만 요청한다. 자동 재조회/폴링은 의도적으로 없다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId]);

  const isBusy = loading || refreshing;
  const allPipelineCountsZero = snapshot?.pipeline.every(
    (row) => row.queued === 0 && row.running === 0 && row.dead === 0,
  );
  const budget = snapshot?.budget;
  const budgetPercent =
    budget && budget.cap_micros > 0
      ? Math.min(
          100,
          Math.max(0, (budget.spent_micros / budget.cap_micros) * 100),
        )
      : null;

  return (
    <section className="flex flex-col gap-lg" aria-busy={isBusy}>
      <div className="flex flex-wrap items-start justify-between gap-base">
        <h2 className="text-ink" style={{ font: "var(--font-title-md)" }}>
          운영 현황
        </h2>
        <button
          type="button"
          onClick={() => void load(true)}
          disabled={isBusy}
          aria-busy={isBusy}
          className="flex min-h-11 shrink-0 items-center gap-xs rounded-sm bg-primary px-base text-on-primary disabled:opacity-60"
          style={{ font: "var(--font-caption)", fontWeight: 600 }}
        >
          <RefreshCw size={16} aria-hidden="true" />
          운영 현황 새로고침
        </button>
      </div>

      {loading && snapshot === null ? (
        <div
          aria-label="운영 현황을 불러오는 중"
          className="flex flex-col gap-base"
        >
          <div className="h-32 animate-pulse rounded-sm bg-surface-soft" />
          <div className="h-48 animate-pulse rounded-sm bg-surface-soft" />
        </div>
      ) : null}
      {loadError ? (
        <p role="alert" className="text-primary-error-text">
          {LOAD_ERROR}
        </p>
      ) : null}

      {snapshot && budget ? (
        <>
          <section className="flex flex-col gap-base rounded-sm border border-hairline bg-canvas p-base">
            <h3 className="text-ink" style={{ font: "var(--font-title-md)" }}>
              이번 달 사용량
            </h3>
            <div className="flex flex-wrap items-baseline justify-between gap-base">
              <p className="text-ink" style={{ font: "var(--font-title-md)" }}>
                {formatMicros(budget.spent_micros)} /{" "}
                {formatMicros(budget.cap_micros)}
              </p>
              <p className="text-muted">
                남은 금액: {formatMicros(budget.remaining_micros)}
              </p>
            </div>
            {budget.cap_micros === 0 ? (
              <p className="text-muted">예산이 설정되지 않았습니다.</p>
            ) : (
              <div
                className="h-2 overflow-hidden rounded-sm bg-surface-soft"
                aria-label={`예산 사용률 ${Math.round(budgetPercent ?? 0)}%`}
              >
                <div
                  className="h-full bg-primary"
                  style={{ width: `${budgetPercent ?? 0}%` }}
                />
              </div>
            )}
            {budget.spent_micros === 0 ? (
              <p className="text-muted">이번 달 사용 기록이 없습니다.</p>
            ) : null}
            {budget.cap_micros > 0 &&
            budget.spent_micros > budget.cap_micros ? (
              <p className="text-warning-text">
                이번 달 예산을 초과했습니다. 새 작업 등록이 제한될 수 있습니다.
              </p>
            ) : null}
            {budget.cap_micros > 0 &&
            budget.spent_micros >= budget.cap_micros * 0.8 &&
            budget.spent_micros <= budget.cap_micros ? (
              <p className="text-warning-text">이번 달 예산에 가깝습니다.</p>
            ) : null}
            {budget.truncated ? (
              <p className="text-warning-text">
                표시할 수 있는 사용 기록이 많아 합계가 일부만 반영되었을 수
                있습니다. 정확한 한도 판단은 작업 등록 시 적용됩니다.
              </p>
            ) : null}
          </section>

          <section className="flex flex-col gap-base">
            <h3 className="text-ink" style={{ font: "var(--font-title-md)" }}>
              파이프라인 상태
            </h3>
            <div className="overflow-x-auto rounded-sm border border-hairline">
              <table className="min-w-[560px] w-full text-left">
                <thead className="bg-surface-soft">
                  <tr>
                    <th className="px-base py-sm">단계</th>
                    <th className="px-base py-sm">대기</th>
                    <th className="px-base py-sm">실행 중</th>
                    <th className="px-base py-sm">실패</th>
                  </tr>
                </thead>
                <tbody>
                  {snapshot.pipeline.map((row) => (
                    <tr key={row.type} className="border-t border-hairline">
                      <th
                        scope="row"
                        title={row.step_label}
                        className="max-w-56 truncate px-base py-sm"
                      >
                        {row.step_label}
                      </th>
                      <td className="px-base py-sm">
                        {countOrUnavailable(row.queued)}
                      </td>
                      <td className="px-base py-sm">
                        {countOrUnavailable(row.running)}
                      </td>
                      <td className="px-base py-sm text-primary-error-text">
                        {deadCountOrUnavailable(row.dead)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {allPipelineCountsZero ? (
              <p className="text-muted">
                처리 중이거나 대기 중인 작업이 없습니다.
              </p>
            ) : null}
          </section>
          <p className="text-muted" style={{ font: "var(--font-caption)" }}>
            마지막 갱신: {dateFormatter.format(new Date(snapshot.observed_at))}
          </p>
        </>
      ) : null}
    </section>
  );
}
