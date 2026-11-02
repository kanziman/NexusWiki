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
  observed_cost_micros?: number;
  pending_micros?: number;
  accounting_status?: string | null;
  tokens_known?: boolean;
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
    pending_micros?: number;
    budget_micros?: number;
    unresolved_count?: number;
    manual_review_count?: number;
    over_reserve_count?: number;
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
  pending_micros?: number;
  budget_micros?: number;
  incomplete_call_count: number;
};

type BudgetCallPathItem = {
  call: string;
  kind: string;
  call_count: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  reported_micros: number;
  pending_micros: number;
  budget_micros: number;
};

type BudgetSnapshot = {
  days: number;
  can_view_workspace: boolean;
  month_start: string;
  cap_micros: number;
  reported_micros: number;
  pending_micros: number;
  budget_micros: number;
  remaining_micros: number;
  unresolved_count: number;
  manual_review_count: number;
  over_reserve_count: number;
  policy: {
    ask_max_context_tokens: number;
    compile_max_input_tokens: number;
    compile_max_output_tokens: number;
    compile_max_pages: number;
    conflict_max_input_tokens: number;
    conflict_max_output_tokens: number;
  };
  savings: {
    ask_no_evidence_count: number;
    ask_context_truncated_count: number;
    compile_truncated_count: number;
    compile_skipped_count: number;
  };
  by_call_path: BudgetCallPathItem[];
};

const CALL_PATH_LABELS: Record<string, string> = {
  ask: "질문 답변 (ask)",
  compile: "위키 컴파일 (compile)",
  conflict_check: "지식 충돌 검사 (conflict_check)",
  embed_source: "원문 임베딩 (embed_source)",
  embed_wiki: "위키 임베딩 (embed_wiki)",
  query_embedding: "질의 임베딩 (query_embedding)",
};

type TabId = "trace" | "budget" | "quality" | "risk";

type PendingProposal = {
  id: string;
  wiki_id: string;
  risk_reason: string;
  slug: string | null;
  current_title: string | null;
  current_content: string | null;
  proposed_title: string;
  proposed_content: string;
  updated_at: string;
};

type RiskSnapshot = {
  days: number;
  can_view_workspace: boolean;
  write_mode: string;
  policy_version: string;
  recorded_policy_versions: string[];
  revisions: { low: number; medium: number; high: number };
  proposals: {
    pending: number;
    approved_waiting: number;
    applied: number;
    rejected: number;
  };
  pending_proposals: PendingProposal[];
};

const RISK_MODE_LABELS: Record<string, string> = {
  enforce: "검증·공개 문서 변경을 승인 대기로 보류",
  shadow: "쓰기를 진행하고 위험 등급만 기록",
  off: "꺼짐",
};

const RISK_REASON_LABELS: Record<string, string> = {
  verified_page: "검증 완료 문서",
  published_page: "공개된 문서",
};

type QualitySnapshot = {
  days: number;
  can_view_workspace: boolean;
  mode: string;
  ask: {
    turns: number;
    violation_turns: number;
    no_citation_turns: number;
    fabricated_turns: number;
    repair_attempted: number;
    repaired: number;
    fallback: number;
  };
  structured: {
    calls: number;
    fence_stripped: number;
    json_invalid: number;
    schema_invalid: number;
    semantic_invalid: number;
    missing_content: number;
    exhausted: number;
  } | null;
  evidence: { pages_total: number; pages_with_evidence: number } | null;
};

const QUALITY_MODE_LABELS: Record<string, string> = {
  enforce: "수리·근거 목록 대체 적용 중",
  shadow: "위반 기록만 (적용 안 함)",
  off: "꺼짐",
};

const STATUS_LABELS: Record<string, string> = {
  resolved: "완료",
  "no-evidence": "근거 없음",
  fallback: "근거 목록",
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
  const [budget, setBudget] = useState<BudgetSnapshot | null>(null);
  const [budgetError, setBudgetError] = useState(false);
  const [quality, setQuality] = useState<QualitySnapshot | null>(null);
  const [qualityError, setQualityError] = useState(false);
  const [risk, setRisk] = useState<RiskSnapshot | null>(null);
  const [riskError, setRiskError] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TraceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [detailError, setDetailError] = useState(false);

  const loadBudget = useCallback(async () => {
    setBudgetError(false);
    try {
      const next = await apiFetch<BudgetSnapshot>(
        `/workspaces/${workspaceId}/control/budget`,
      );
      setBudget(next);
    } catch {
      setBudgetError(true);
    }
  }, [workspaceId]);

  const loadQuality = useCallback(async () => {
    setQualityError(false);
    try {
      setQuality(
        await apiFetch<QualitySnapshot>(
          `/workspaces/${workspaceId}/control/quality`,
        ),
      );
    } catch {
      setQualityError(true);
    }
  }, [workspaceId]);

  const loadRisk = useCallback(async () => {
    setRiskError(false);
    try {
      setRisk(
        await apiFetch<RiskSnapshot>(`/workspaces/${workspaceId}/control/risk`),
      );
    } catch {
      setRiskError(true);
    }
  }, [workspaceId]);

  const decideProposal = useCallback(
    async (proposalId: string, decision: "approve" | "reject") => {
      setRiskError(false);
      try {
        await apiFetch(
          `/workspaces/${workspaceId}/wiki-proposals/${proposalId}/${decision}`,
          { method: "POST" },
        );
        await loadRisk();
      } catch {
        setRiskError(true);
      }
    },
    [workspaceId, loadRisk],
  );

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
      if (tab === "budget") {
        await loadBudget();
      }
      if (tab === "quality") {
        await loadQuality();
      }
      if (tab === "risk") {
        await loadRisk();
      }
    } catch {
      // 원시 오류는 운영 정보가 될 수 있으므로 계약 문구만 렌더한다.
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, [workspaceId, tab, loadBudget, loadQuality, loadRisk]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (tab === "budget" && !budget && !budgetError) {
      void loadBudget();
    }
  }, [tab, budget, budgetError, loadBudget]);

  useEffect(() => {
    if (tab === "quality" && !quality && !qualityError) {
      void loadQuality();
    }
  }, [tab, quality, qualityError, loadQuality]);

  useEffect(() => {
    if (tab === "risk" && !risk && !riskError) {
      void loadRisk();
    }
  }, [tab, risk, riskError, loadRisk]);

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
        <button
          type="button"
          role="tab"
          id="control-tab-budget"
          aria-selected={tab === "budget"}
          className={tab === "budget" ? styles.tabActive : styles.tab}
          onClick={() => setTab("budget")}
        >
          예산
        </button>
        <button
          type="button"
          role="tab"
          id="control-tab-quality"
          aria-selected={tab === "quality"}
          className={tab === "quality" ? styles.tabActive : styles.tab}
          onClick={() => setTab("quality")}
        >
          품질
        </button>
        <button
          type="button"
          role="tab"
          id="control-tab-risk"
          aria-selected={tab === "risk"}
          className={tab === "risk" ? styles.tabActive : styles.tab}
          onClick={() => setTab("risk")}
        >
          리스크
        </button>
      </div>

      {tab === "budget" ? (
        <section role="tabpanel" aria-labelledby="control-tab-budget">
          {budgetError ? (
            <p role="alert" className="invite-feedback error show">
              예산 정보를 불러오지 못했습니다. 새로고침을 시도해주세요.
            </p>
          ) : null}
          {budget ? <BudgetPanel snapshot={budget} /> : null}
        </section>
      ) : tab === "quality" ? (
        <section role="tabpanel" aria-labelledby="control-tab-quality">
          {qualityError ? (
            <p role="alert" className="invite-feedback error show">
              품질 정보를 불러오지 못했습니다. 새로고침을 시도해주세요.
            </p>
          ) : null}
          {quality ? <QualityPanel snapshot={quality} /> : null}
        </section>
      ) : tab === "risk" ? (
        <section role="tabpanel" aria-labelledby="control-tab-risk">
          {riskError ? (
            <p role="alert" className="invite-feedback error show">
              리스크 정보를 불러오거나 처리하지 못했습니다. 새로고침을
              시도해주세요.
            </p>
          ) : null}
          {risk ? (
            <RiskPanel snapshot={risk} onDecide={decideProposal} />
          ) : null}
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
      <Metric
        label="미확정 예산 점유"
        value={microsDisplay(aggregate.pending_micros ?? 0)}
      />
      <Metric
        label="예산 판정액"
        value={microsDisplay(
          aggregate.budget_micros ?? aggregate.total_cost_micros,
        )}
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

function RiskPanel({
  snapshot,
  onDecide,
}: {
  snapshot: RiskSnapshot;
  onDecide: (proposalId: string, decision: "approve" | "reject") => void;
}) {
  const { revisions, proposals } = snapshot;
  return (
    <div>
      <p>
        위키 쓰기 모드:{" "}
        {RISK_MODE_LABELS[snapshot.write_mode] ?? snapshot.write_mode}
      </p>
      <p>적용 중인 LLM 정책: {snapshot.policy_version}</p>
      <section
        className={styles.aggregate}
        aria-label={`최근 ${snapshot.days}일 위키 개정 위험 등급`}
      >
        <Metric label="개정 낮음" value={`${revisions.low}건`} />
        <Metric label="개정 중간" value={`${revisions.medium}건`} />
        <Metric label="개정 높음" value={`${revisions.high}건`} />
        <Metric label="승인 대기" value={`${proposals.pending}건`} />
        <Metric
          label="승인 후 반영 중"
          value={`${proposals.approved_waiting}건`}
        />
        <Metric label="승인 반영" value={`${proposals.applied}건`} />
        <Metric label="거부" value={`${proposals.rejected}건`} />
      </section>
      {snapshot.can_view_workspace ? (
        snapshot.pending_proposals.length > 0 ? (
          <section aria-label="승인 대기 위키 변경">
            <h2>승인 대기 위키 변경</h2>
            <ul>
              {snapshot.pending_proposals.map((proposal) => (
                <li key={proposal.id}>
                  <strong>{proposal.proposed_title}</strong>{" "}
                  <span>
                    {RISK_REASON_LABELS[proposal.risk_reason] ??
                      proposal.risk_reason}
                  </span>
                  <details>
                    <summary>현재 본문과 제안 본문 보기</summary>
                    <h3>현재 본문</h3>
                    <pre>{proposal.current_content}</pre>
                    <h3>제안 본문</h3>
                    <pre>{proposal.proposed_content}</pre>
                  </details>
                  <button
                    type="button"
                    onClick={() => onDecide(proposal.id, "approve")}
                  >
                    승인
                  </button>{" "}
                  <button
                    type="button"
                    onClick={() => onDecide(proposal.id, "reject")}
                  >
                    거부
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ) : (
          <p>승인을 기다리는 위키 변경이 없습니다.</p>
        )
      ) : (
        <p>조회 전용(viewer) 멤버에게는 집계만 표시합니다.</p>
      )}
    </div>
  );
}

function QualityPanel({ snapshot }: { snapshot: QualitySnapshot }) {
  const { ask, structured, evidence } = snapshot;
  // 위키 쪽수는 기간과 무관하므로 빈 상태 판정에 넣지 않는다.
  if (ask.turns === 0 && !structured?.calls) {
    return (
      <p className={styles.empty}>
        최근 {snapshot.days}일 동안 집계할 답변과 수집 호출이 없습니다. 질문을
        하거나 원문을 등록하면 여기에 쌓입니다.
      </p>
    );
  }
  return (
    <div>
      <p>
        인용 계약 모드: {QUALITY_MODE_LABELS[snapshot.mode] ?? snapshot.mode}
      </p>
      <section
        className={styles.aggregate}
        aria-label={`최근 ${snapshot.days}일 답변 인용 계약`}
      >
        <Metric label="답변 턴" value={`${ask.turns}건`} />
        <Metric label="계약 위반 턴" value={`${ask.violation_turns}건`} />
        <Metric label="인용 없음" value={`${ask.no_citation_turns}건`} />
        <Metric label="위조 앵커" value={`${ask.fabricated_turns}건`} />
        <Metric
          label="수리 성공 / 시도"
          value={`${ask.repaired}건 / ${ask.repair_attempted}건`}
        />
        <Metric label="근거 목록 대체" value={`${ask.fallback}건`} />
      </section>
      {structured && evidence ? (
        <>
          <section
            className={styles.aggregate}
            aria-label={`최근 ${snapshot.days}일 구조화 출력`}
          >
            <Metric label="구조화 호출" value={`${structured.calls}건`} />
            <Metric
              label="코드 펜스 제거"
              value={`${structured.fence_stripped}건`}
            />
            <Metric label="JSON 오류" value={`${structured.json_invalid}건`} />
            <Metric
              label="스키마 오류"
              value={`${structured.schema_invalid}건`}
            />
            <Metric
              label="내용 오류"
              value={`${structured.semantic_invalid}건`}
            />
            <Metric
              label="본문 없는 응답"
              value={`${structured.missing_content}건`}
            />
            <Metric label="시도 소진" value={`${structured.exhausted}건`} />
          </section>
          <section className={styles.aggregate} aria-label="위키 근거 청크">
            <Metric
              label="근거가 연결된 페이지"
              value={`${evidence.pages_with_evidence}쪽 / ${evidence.pages_total}쪽`}
            />
          </section>
        </>
      ) : (
        <p>조회 전용(viewer) 멤버에게는 본인 답변의 집계만 표시합니다.</p>
      )}
    </div>
  );
}

function BudgetPanel({ snapshot }: { snapshot: BudgetSnapshot }) {
  const utilizationPct =
    snapshot.cap_micros > 0
      ? ((snapshot.budget_micros / snapshot.cap_micros) * 100).toFixed(1)
      : "0.0";
  return (
    <div>
      <section className={styles.aggregate} aria-label="당월 예산 현황">
        <Metric
          label="월간 예산 한도"
          value={microsDisplay(snapshot.cap_micros)}
        />
        <Metric
          label="예산 판정액 (소진율)"
          value={`${microsDisplay(snapshot.budget_micros)} (${utilizationPct}%)`}
        />
        <Metric
          label="공급자 보고 비용"
          value={microsDisplay(snapshot.reported_micros)}
        />
        <Metric
          label="미확정 예산 점유"
          value={microsDisplay(snapshot.pending_micros)}
        />
        <Metric
          label="남은 한도"
          value={microsDisplay(snapshot.remaining_micros)}
        />
        <Metric
          label="미정산 / 수동검토"
          value={`${snapshot.unresolved_count}건 / ${snapshot.manual_review_count}건`}
        />
      </section>

      <section className={styles.metrics} aria-label="활성 토큰 예산 정책">
        <Metric
          label="Ask 컨텍스트 토큰 상한"
          value={`${snapshot.policy.ask_max_context_tokens.toLocaleString("ko-KR")} 토큰 (이중 근거 1+1 보장)`}
        />
        <Metric
          label="위키 컴파일 입력 상한"
          value={`${snapshot.policy.compile_max_input_tokens.toLocaleString("ko-KR")} 토큰`}
        />
        <Metric
          label="위키 컴파일 출력 상한"
          value={`${snapshot.policy.compile_max_output_tokens.toLocaleString("ko-KR")} 토큰 · 최대 ${snapshot.policy.compile_max_pages}페이지`}
        />
        <Metric
          label="충돌 검사 입·출력 상한"
          value={`입력 ${snapshot.policy.conflict_max_input_tokens.toLocaleString("ko-KR")} / 출력 ${snapshot.policy.conflict_max_output_tokens.toLocaleString("ko-KR")} 토큰`}
        />
      </section>

      <section
        className={styles.metrics}
        aria-label={`최근 ${snapshot.days}일 예산 절감 실행`}
      >
        <Metric
          label="Ask 근거 0건 단락 (NO_EVIDENCE)"
          value={`${snapshot.savings.ask_no_evidence_count}건`}
        />
        <Metric
          label="Ask 컨텍스트 예산 절단"
          value={`${snapshot.savings.ask_context_truncated_count}건`}
        />
        {snapshot.can_view_workspace ? (
          <>
            <Metric
              label="컴파일 입력 절단 (TRUNCATED)"
              value={`${snapshot.savings.compile_truncated_count}건`}
            />
            <Metric
              label="변경 없는 원문 컴파일 생략 (SKIP_UNCHANGED)"
              value={`${snapshot.savings.compile_skipped_count}건`}
            />
          </>
        ) : (
          <p className={styles.note}>
            조회 전용(viewer) 멤버에게는 워크스페이스 월간 예산 현황과 본인의
            질문 절감 건수만 표시됩니다.
          </p>
        )}
      </section>

      {snapshot.can_view_workspace ? (
        snapshot.by_call_path.length > 0 ? (
          <div className={styles.tableScroll}>
            <table className={styles.calls}>
              <caption>호출 경로별 비용 및 토큰</caption>
              <thead>
                <tr>
                  <th scope="col">호출 경로</th>
                  <th scope="col">종류</th>
                  <th scope="col">호출 건수</th>
                  <th scope="col">입력 토큰</th>
                  <th scope="col">출력 토큰</th>
                  <th scope="col">총 토큰</th>
                  <th scope="col">공급자 보고 비용</th>
                  <th scope="col">미확정 점유</th>
                  <th scope="col">예산 판정액</th>
                </tr>
              </thead>
              <tbody>
                {snapshot.by_call_path.map((item) => (
                  <tr key={`${item.call}-${item.kind}`}>
                    <td>{CALL_PATH_LABELS[item.call] ?? item.call}</td>
                    <td>{item.kind}</td>
                    <td>{item.call_count.toLocaleString("ko-KR")}건</td>
                    <td>{item.prompt_tokens.toLocaleString("ko-KR")}</td>
                    <td>{item.completion_tokens.toLocaleString("ko-KR")}</td>
                    <td>{item.total_tokens.toLocaleString("ko-KR")}</td>
                    <td>{microsDisplay(item.reported_micros)}</td>
                    <td>{microsDisplay(item.pending_micros)}</td>
                    <td>{microsDisplay(item.budget_micros)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className={styles.empty}>
            <h2>최근 {snapshot.days}일 동안 기록된 공급자 호출이 없습니다</h2>
            <p>
              질문이나 원문 컴파일이 실행되면 경로별 비용과 토큰이 집계됩니다.
            </p>
          </div>
        )
      ) : null}
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
          label="관측 토큰"
          value={detail.totals.total_tokens.toLocaleString("ko-KR")}
        />
        <Metric
          label="공급자 보고 비용"
          value={microsDisplay(detail.totals.cost_micros)}
        />
        <Metric
          label="미확정 예산 점유"
          value={microsDisplay(detail.totals.pending_micros ?? 0)}
        />
        <Metric
          label="예산 판정액"
          value={microsDisplay(
            detail.totals.budget_micros ?? detail.totals.cost_micros,
          )}
        />
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
      {(detail.totals.unresolved_count ?? 0) > 0 ? (
        <p role="status">
          미확정 비용의 임시 점유는 실제 청구액이 아닙니다.
          {(detail.totals.manual_review_count ?? 0) > 0
            ? " 운영자 확인이 필요한 호출이 있습니다."
            : ""}
        </p>
      ) : null}
      {(detail.totals.over_reserve_count ?? 0) > 0 ? (
        <p role="status">확보액을 넘은 공급자 비용을 전액 반영했습니다.</p>
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
                <th scope="col">원 관측 비용</th>
                <th scope="col">공급자 보고 비용 (정산 반영)</th>
                <th scope="col">미확정 점유</th>
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
                  <td>
                    {call.tokens_known === false
                      ? "기록 없음"
                      : call.total_tokens.toLocaleString("ko-KR")}
                  </td>
                  <td>{formatMs(call.duration_ms)}</td>
                  <td>
                    {microsDisplay(
                      call.observed_cost_micros ?? call.cost_micros,
                    )}
                  </td>
                  <td>{microsDisplay(call.cost_micros)}</td>
                  <td>{microsDisplay(call.pending_micros ?? 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </article>
  );
}
