"use client";

import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import styles from "@/components/ControlRoom.module.css";
import { ApiError, apiFetch } from "@/lib/api-client";
import { formatCredits } from "@/lib/credits";

/**
 * Control Room 추적 탭.
 *
 * 관련 이슈: #165, #166
 * 계약: openspec/changes/ai-control-flow-accounting/specs/ai-control-room/spec.md
 *
 * ⚠️ 응답에 실재하는 값만 그린다. 이후 Step의 탭은 데이터가 생기기 전까지 빈 상태만 표시하며
 * 예시 수치를 넣지 않는다. 스펙이 금지하는 사항이다.
 */

type Route = { decision: string | null; reason: string | null } | null;

type TraceSummary = {
  trace_id: string;
  kind: "ask" | "ingest";
  status: string;
  started_at: string;
  route: Route;
  total_ms: number | null;
};

type TraceList = { items: TraceSummary[]; can_view_workspace: boolean };

type Span = {
  name: string;
  label: string;
  start_ms: number;
  duration_ms: number;
};

type Stage = {
  type: string;
  label: string;
  state: string;
  attempts: number;
  duration_ms: number | null;
  error_category: string | null;
};

type Call = {
  call: string | null;
  kind: string;
  model: string;
  attempt: number | null;
  incomplete: boolean;
  route: string | null;
  total_tokens: number;
  cost_micros: number;
  duration_ms: number | null;
  occurred_at: string;
};

type TraceDetail = TraceSummary & {
  spans: Span[];
  stages: Stage[];
  calls: Call[];
  totals: {
    call_count: number;
    total_tokens: number;
    cost_micros: number;
    incomplete_call_count: number;
  };
  evidence?: { wiki: number; source: number };
  missing_channels?: string[];
  citation?: { cited_anchor_count: number; dual_citation_rate: number };
};

type AskAggregate = {
  days: number;
  turn_count: number;
  resolved_count: number;
  no_evidence_count: number;
  error_count: number;
  decision_counts: Record<string, number>;
  p50_total_ms: number | null;
  p95_total_ms: number | null;
  total_cost_micros: number;
  incomplete_call_count: number;
};

const FUTURE_TABS = [
  { id: "budget", label: "예산", step: "Step 2" },
  { id: "quality", label: "품질", step: "Step 3" },
  { id: "risk", label: "리스크", step: "Step 4" },
] as const;

type TabId = "trace" | (typeof FUTURE_TABS)[number]["id"];

const STATUS_LABELS: Record<string, string> = {
  resolved: "완료",
  "no-evidence": "근거 없음",
  error: "오류",
  streaming: "진행 중",
  succeeded: "완료",
  running: "진행 중",
  failed: "실패",
  canceled: "취소",
};

const STATE_LABELS: Record<string, string> = {
  completed: "완료",
  active: "진행 중",
  pending: "대기",
  retrying: "재시도 대기",
  failed: "실패",
  canceled: "취소",
};

const dateFormatter = new Intl.DateTimeFormat("ko-KR", {
  dateStyle: "short",
  timeStyle: "medium",
});

function formatMs(value: number | null | undefined) {
  if (value === null || value === undefined) return "측정 없음";
  return value >= 1000 ? `${(value / 1000).toFixed(2)}s` : `${value}ms`;
}

function microsDisplay(micros: number) {
  return `$${(micros / 1_000_000).toFixed(4)} (${formatCredits(micros)})`;
}

function statusTone(status: string) {
  if (status === "error" || status === "failed") return styles.toneBad;
  if (status === "running" || status === "streaming") return styles.toneActive;
  return styles.toneGood;
}

export type ControlRoomProps = { workspaceId: string };

export function ControlRoom({ workspaceId }: ControlRoomProps) {
  const [tab, setTab] = useState<TabId>("trace");
  const [list, setList] = useState<TraceList | null>(null);
  const [aggregate, setAggregate] = useState<AskAggregate | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TraceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [detailError, setDetailError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const next = await apiFetch<TraceList>(
        `/workspaces/${workspaceId}/control/traces`,
      );
      setList(next);
      setSelectedId((current) => current ?? next.items[0]?.trace_id ?? null);
      if (next.can_view_workspace) {
        setAggregate(
          await apiFetch<AskAggregate>(
            `/workspaces/${workspaceId}/control/ask-aggregate`,
          ),
        );
      }
    } catch {
      // 원시 오류는 운영 정보가 될 수 있으므로 계약 문구만 렌더한다.
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setDetailError(false);
    apiFetch<TraceDetail>(
      `/workspaces/${workspaceId}/control/traces/${selectedId}`,
    )
      .then((next) => {
        if (!cancelled) setDetail(next);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setDetail(null);
        setDetailError(error instanceof ApiError || error instanceof Error);
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId, selectedId]);

  return (
    <div className={styles.room} aria-busy={loading}>
      <header className={styles.header}>
        <div>
          <h1>Control Room</h1>
          <p>
            요청과 수집 작업이 어떤 경로로 처리되었고 시간과 비용이 어디에
            쓰였는지 확인합니다. 질문과 답변 본문은 저장하지 않습니다.
          </p>
        </div>
        <button
          type="button"
          className="button"
          onClick={() => void load()}
          disabled={loading}
        >
          <RefreshCw size={15} aria-hidden="true" />
          새로고침
        </button>
      </header>

      <div className={styles.tabs} role="tablist" aria-label="통제 영역">
        <button
          type="button"
          role="tab"
          id="control-tab-trace"
          aria-selected={tab === "trace"}
          className={tab === "trace" ? styles.tabActive : styles.tab}
          onClick={() => setTab("trace")}
        >
          추적
        </button>
        {FUTURE_TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            id={`control-tab-${item.id}`}
            aria-selected={tab === item.id}
            className={tab === item.id ? styles.tabActive : styles.tab}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab !== "trace" ? (
        <section
          role="tabpanel"
          aria-labelledby={`control-tab-${tab}`}
          className={styles.empty}
        >
          <h2>
            {FUTURE_TABS.find((item) => item.id === tab)?.step}에서 수집을
            시작합니다
          </h2>
          <p>아직 수집된 데이터가 없습니다.</p>
        </section>
      ) : (
        <section role="tabpanel" aria-labelledby="control-tab-trace">
          {loadError ? (
            <p role="alert" className="invite-feedback error show">
              추적 정보를 불러오지 못했습니다. 새로고침을 시도해주세요.
            </p>
          ) : null}

          {aggregate ? <AggregateRow aggregate={aggregate} /> : null}

          {list && list.items.length === 0 ? (
            <div className={styles.empty} data-testid="control-empty">
              <h2>아직 기록된 trace가 없습니다</h2>
              <p>질문을 하거나 원문을 등록하면 첫 trace가 여기에 나타납니다.</p>
            </div>
          ) : null}

          {list && list.items.length > 0 ? (
            <div className={styles.split}>
              <ul className={styles.list} aria-label="trace 목록">
                {list.items.map((item) => (
                  <li key={item.trace_id}>
                    <button
                      type="button"
                      aria-current={
                        item.trace_id === selectedId ? "true" : undefined
                      }
                      className={
                        item.trace_id === selectedId
                          ? styles.itemActive
                          : styles.item
                      }
                      onClick={() => setSelectedId(item.trace_id)}
                    >
                      <span className={styles.itemHead}>
                        <b>{item.kind === "ask" ? "질문" : "원문 수집"}</b>
                        <span
                          className={`${styles.pill} ${statusTone(item.status)}`}
                        >
                          {STATUS_LABELS[item.status] ?? item.status}
                        </span>
                      </span>
                      <small>
                        {dateFormatter.format(new Date(item.started_at))}
                        {item.total_ms ? ` · ${formatMs(item.total_ms)}` : ""}
                      </small>
                    </button>
                  </li>
                ))}
              </ul>

              <div className={styles.detail}>
                {detailError ? (
                  <p role="alert" className="invite-feedback error show">
                    이 trace를 볼 수 없습니다.
                  </p>
                ) : null}
                {detail ? <TraceDetailView detail={detail} /> : null}
              </div>
            </div>
          ) : null}
        </section>
      )}
    </div>
  );
}

function AggregateRow({ aggregate }: { aggregate: AskAggregate }) {
  const decisions = Object.entries(aggregate.decision_counts);
  return (
    <section
      className={styles.aggregate}
      aria-label={`최근 ${aggregate.days}일 질문 집계`}
    >
      <Metric label="질문 수" value={`${aggregate.turn_count}건`} />
      <Metric label="지연 p50" value={formatMs(aggregate.p50_total_ms)} />
      <Metric label="지연 p95" value={formatMs(aggregate.p95_total_ms)} />
      <Metric
        label="질문 비용"
        value={microsDisplay(aggregate.total_cost_micros)}
      />
      <Metric label="오류" value={`${aggregate.error_count}건`} />
      <Metric
        label="미완료 호출"
        value={`${aggregate.incomplete_call_count}건`}
      />
      <p className={styles.note}>
        Router 결정 (참고 수치):{" "}
        {decisions.length > 0
          ? decisions.map(([name, count]) => `${name} ${count}`).join(" · ")
          : "기록 없음"}
      </p>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.metric}>
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

function TraceDetailView({ detail }: { detail: TraceDetail }) {
  const timelineTotal = Math.max(
    detail.total_ms ?? 0,
    ...detail.spans.map((span) => span.start_ms + span.duration_ms),
    1,
  );
  return (
    <article aria-label="trace 상세">
      <h2 className={styles.detailTitle}>
        {detail.kind === "ask" ? "질문" : "원문 수집"}
        <code>{detail.trace_id}</code>
      </h2>

      <div className={styles.metrics}>
        <Metric
          label="최종 상태"
          value={STATUS_LABELS[detail.status] ?? detail.status}
        />
        <Metric label="호출" value={`${detail.totals.call_count}건`} />
        <Metric
          label="토큰"
          value={detail.totals.total_tokens.toLocaleString("ko-KR")}
        />
        <Metric label="비용" value={microsDisplay(detail.totals.cost_micros)} />
        {detail.route?.decision ? (
          <Metric label="Router 결정" value={detail.route.decision} />
        ) : null}
      </div>

      {detail.totals.incomplete_call_count > 0 ? (
        <p role="status" className={styles.warning}>
          최종 사용량을 받지 못한 호출이 {detail.totals.incomplete_call_count}건
          있어 실제 비용이 더 클 수 있습니다.
        </p>
      ) : null}

      {detail.missing_channels && detail.missing_channels.length > 0 ? (
        <p role="status" className={styles.warning}>
          실패한 검색 채널: {detail.missing_channels.join(", ")}
        </p>
      ) : null}

      {detail.kind === "ask" && detail.spans.length === 0 ? (
        <p role="status" className={styles.note}>
          구간 기록이 없습니다. 턴이 완료되기 전에 처리가 중단되었을 수
          있습니다.
        </p>
      ) : null}

      {detail.spans.length > 0 ? (
        <section aria-label="구간 타임라인" className={styles.timeline}>
          {detail.spans.map((span) => (
            <div className={styles.span} key={`${span.name}-${span.start_ms}`}>
              <span>{span.label}</span>
              <div className={styles.track}>
                <i
                  style={{
                    left: `${(span.start_ms / timelineTotal) * 100}%`,
                    width: `${(span.duration_ms / timelineTotal) * 100}%`,
                  }}
                />
              </div>
              <small>{formatMs(span.duration_ms)}</small>
            </div>
          ))}
        </section>
      ) : null}

      {detail.stages.length > 0 ? (
        <ol className={styles.stages} aria-label="처리 단계">
          {detail.stages.map((stage) => (
            <li key={`${stage.type}-${stage.state}`} data-state={stage.state}>
              <b>{stage.label}</b>
              <span>{STATE_LABELS[stage.state] ?? stage.state}</span>
              <small>
                {stage.attempts > 1 ? `시도 ${stage.attempts}회 · ` : ""}
                {stage.duration_ms !== null ? formatMs(stage.duration_ms) : ""}
                {stage.error_category ? ` ${stage.error_category}` : ""}
              </small>
            </li>
          ))}
        </ol>
      ) : null}

      {detail.calls.length > 0 ? (
        <div className={styles.tableScroll}>
          <table className={styles.calls}>
            <caption>공급자 호출</caption>
            <thead>
              <tr>
                <th scope="col">호출</th>
                <th scope="col">모델</th>
                <th scope="col">Router 결정</th>
                <th scope="col">시도</th>
                <th scope="col">토큰</th>
                <th scope="col">시간</th>
                <th scope="col">비용</th>
              </tr>
            </thead>
            <tbody>
              {detail.calls.map((call, index) => (
                <tr key={`${call.occurred_at}-${index}`}>
                  <td>
                    {call.call ?? call.kind}
                    {call.incomplete ? " (미완료)" : ""}
                  </td>
                  <td>{call.model}</td>
                  <td>{call.route ?? "-"}</td>
                  <td>{call.attempt ?? "-"}</td>
                  <td>{call.total_tokens.toLocaleString("ko-KR")}</td>
                  <td>{formatMs(call.duration_ms)}</td>
                  <td>${(call.cost_micros / 1_000_000).toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </article>
  );
}
