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
const monthFormatter = new Intl.DateTimeFormat("ko-KR", {
  dateStyle: "medium",
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
    <div aria-busy={isBusy}>
      <div className="section-head">
        <div>
          <h2>운영 현황</h2>
          <p>이번 달 추론 예산과 작업 파이프라인 적체를 확인합니다.</p>
        </div>
        <button
          type="button"
          onClick={() => void load(true)}
          disabled={isBusy}
          aria-busy={isBusy}
          className="button"
        >
          <RefreshCw size={15} aria-hidden="true" />
          운영 현황 새로고침
        </button>
      </div>

      {loading && snapshot === null ? (
        <div aria-label="운영 현황을 불러오는 중" className="grid gap-[22px]">
          <div className="h-32 animate-pulse rounded-xl bg-[var(--surface)]" />
          <div className="h-48 animate-pulse rounded-xl bg-[var(--surface)]" />
        </div>
      ) : null}
      {loadError ? (
        <p role="alert" className="invite-feedback error show">
          {LOAD_ERROR}
        </p>
      ) : null}

      {snapshot && budget ? (
        <>
          <section className="budget" data-od-id="budget-card">
            <div className="budget-main">
              <h3>이번 달 LLM 추론 예산</h3>
              {/* ⚠️ authoritative:false 는 계약의 일부다(PRD §3.3.1) — 상한
                  집행은 enqueue_source_job 이 하고 여기는 표시용이다. */}
              <p>표시용 수치입니다. 상한 집행은 작업 등록 시점에 이뤄집니다.</p>

              <div className="budget-amount">
                {formatMicros(budget.spent_micros)}{" "}
                <span>/ {formatMicros(budget.cap_micros)}</span>
              </div>

              {budget.cap_micros === 0 ? (
                <p className="mt-[18px] mb-0 text-[11px]">
                  예산이 설정되지 않았습니다.
                </p>
              ) : (
                <div
                  className="progress"
                  aria-label={`예산 사용률 ${Math.round(budgetPercent ?? 0)}%`}
                >
                  <i style={{ width: `${budgetPercent ?? 0}%` }} />
                </div>
              )}

              <div className="budget-meta">
                <span>
                  {budget.spent_micros === 0
                    ? "이번 달 사용 기록이 없습니다."
                    : `집계 시작 ${monthFormatter.format(new Date(budget.month_start))}`}
                </span>
                <span>남은 금액 {formatMicros(budget.remaining_micros)}</span>
              </div>
            </div>

            {/* ⚠️ 일 평균 사용액·다음 초기화일·예산 상태 뱃지는 그리지 않는다 —
                응답에 없고 파생 규칙도 정의되지 않았다(PRD §3.3.1). 여기에는
                응답에 실재하는 값만 둔다. */}
            <div className="budget-aside">
              <div>
                <span>사용액</span>
                <b>{formatMicros(budget.spent_micros)}</b>
              </div>
              <div>
                <span>남은 금액</span>
                <b>{formatMicros(budget.remaining_micros)}</b>
              </div>
              <div>
                <span>월 상한</span>
                <b>{formatMicros(budget.cap_micros)}</b>
              </div>

              {budget.cap_micros > 0 &&
              budget.spent_micros > budget.cap_micros ? (
                <p className="m-0 text-[11px] text-[var(--danger)]">
                  이번 달 예산을 초과했습니다. 새 작업 등록이 제한될 수
                  있습니다.
                </p>
              ) : null}
              {budget.cap_micros > 0 &&
              budget.spent_micros >= budget.cap_micros * 0.8 &&
              budget.spent_micros <= budget.cap_micros ? (
                <p className="m-0 text-[11px] text-[var(--danger)]">
                  이번 달 예산에 가깝습니다.
                </p>
              ) : null}
              {budget.truncated ? (
                <p className="m-0 text-[11px] text-[var(--muted)]">
                  표시할 수 있는 사용 기록이 많아 합계가 일부만 반영되었을 수
                  있습니다. 정확한 한도 판단은 작업 등록 시 적용됩니다.
                </p>
              ) : null}
            </div>
          </section>

          <section className="pipeline" data-od-id="pipeline-card">
            <div className="pipeline-head">
              <div>단계</div>
              <div>대기</div>
              <div>실행 중</div>
              <div>실패</div>
            </div>

            {/* ⚠️ 라벨은 서버가 소유한다 — type 문자열을 클라이언트가 매칭하면
                단계가 추가될 때 조용히 빈 라벨이 된다(PRD §3.3.2). */}
            {snapshot.pipeline.map((row) => (
              <div className="pipeline-row" key={row.type}>
                <div className="pipe-title truncate" title={row.step_label}>
                  {row.step_label}
                  <span>{row.type}</span>
                </div>
                <div className="metric">
                  <span>{countOrUnavailable(row.queued)}</span>
                  <small>대기</small>
                </div>
                <div className="metric running">
                  <span>{countOrUnavailable(row.running)}</span>
                  <small>실행 중</small>
                </div>
                <div
                  className={`metric ${row.dead !== null && row.dead > 0 ? "dead" : ""}`}
                >
                  <span>{deadCountOrUnavailable(row.dead)}</span>
                  <small>실패</small>
                </div>
              </div>
            ))}
          </section>

          {allPipelineCountsZero ? (
            <p className="mt-3 mb-0 text-[11px] text-[var(--muted)]">
              처리 중이거나 대기 중인 작업이 없습니다.
            </p>
          ) : null}

          <p className="mt-3 mb-0 text-[10px] text-[var(--muted)]">
            마지막 갱신: {dateFormatter.format(new Date(snapshot.observed_at))}
          </p>
        </>
      ) : null}
    </div>
  );
}
