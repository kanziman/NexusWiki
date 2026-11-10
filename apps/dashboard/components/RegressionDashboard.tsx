"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { LocalEvaluationPanel } from "./LocalEvaluationPanel";
import { GoldenJudgePanel } from "./GoldenJudgePanel";
import {
  ArrowLeftRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  CircleAlert,
  Download,
  FlaskConical,
  GitCompareArrows,
  Info,
  Search,
} from "lucide-react";
import {
  compareRuns,
  outcomeLabels,
  researchLabel,
  type AnalysisSuite,
  type ComparedRow,
  type Outcome,
} from "@/lib/regression-analysis";
import { regressionSuites } from "@/lib/regression-data";
import { decisionLabels, kst } from "@/lib/experiments";
import styles from "./RegressionDashboard.module.css";

const usd = (value: number | null) =>
  value === null ? "미측정" : `$${(value / 1e6).toFixed(4)}`;
const seconds = (value: number | null) =>
  value === null ? "미측정" : `${(value / 1000).toFixed(2)}초`;
const signed = (value: number, digits = 0) =>
  `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;

const RUN_CHECK_LABEL = "내 검증 실행하기";

function openNewCheck() {
  const drawer = document.getElementById("new-check");
  if (drawer instanceof HTMLDetailsElement) drawer.open = true;
  drawer?.scrollIntoView({ behavior: "smooth", block: "start" });
}

type Review = {
  decision: string;
  reason: string;
  savedAt: string;
  fingerprint: string;
};
// 브라우저 메모가 다른 내용의 실행에 붙지 않도록 하는 변경 감지용 지문이다. 보안 서명은 아니다.
function fingerprint(value: unknown) {
  let hash = 2166136261;
  for (const char of JSON.stringify(value))
    hash = Math.imul(hash ^ char.charCodeAt(0), 16777619);
  return (hash >>> 0).toString(16);
}

function ReviewPanel({
  storageKey,
  signature,
}: {
  storageKey: string;
  signature: string;
}) {
  const [decision, setDecision] = useState("review");
  const [reason, setReason] = useState("");
  const [saved, setSaved] = useState<Review | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState(false);
  useEffect(() => {
    try {
      const value = JSON.parse(
        localStorage.getItem(storageKey) ?? "null",
      ) as Review | null;
      if (
        value &&
        value.fingerprint === signature &&
        ["review", "adopt", "hold"].includes(value.decision) &&
        typeof value.reason === "string" &&
        typeof value.savedAt === "string"
      ) {
        setDecision(value.decision);
        setReason(value.reason);
        setSaved(value);
      }
    } catch {
      setError(true);
      setMessage(
        "브라우저 저장소를 읽지 못했습니다. 메모는 현재 화면에서 작성할 수 있습니다.",
      );
    }
  }, [storageKey, signature]);
  function save() {
    if (!reason.trim()) {
      setError(true);
      setMessage("판단의 근거를 입력해 주세요.");
      return;
    }
    try {
      const review = {
        decision,
        reason: reason.trim(),
        savedAt: new Date().toISOString(),
        fingerprint: signature,
      };
      localStorage.setItem(storageKey, JSON.stringify(review));
      setSaved(review);
      setError(false);
      setMessage("이 브라우저에 검토 메모를 저장했습니다.");
    } catch {
      setError(true);
      setMessage(
        "저장하지 못했습니다. 브라우저 저장 공간과 권한을 확인해 주세요.",
      );
    }
  }
  return (
    <section
      id="review"
      className={styles.review}
      aria-labelledby="review-title"
    >
      <div>
        <h2 id="review-title">검토 메모</h2>
        <p>
          이 비교에 대한 의견을 남깁니다. 메모는 이 브라우저에만 저장되며 운영
          설정을 변경하지 않습니다.
        </p>
      </div>
      <div className={styles.reviewForm}>
        <label>
          검토 의견
          <select
            value={decision}
            onChange={(e) => setDecision(e.target.value)}
          >
            <option value="review">검토 중</option>
            <option value="adopt">채택 의견</option>
            <option value="hold">보류 의견</option>
          </select>
        </label>
        <label>
          판단 근거
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="회귀 문항, 비용 증가, 추가로 확인할 점을 기록하세요."
            rows={3}
            maxLength={4000}
          />
        </label>
        <div className={styles.saveRow}>
          <button type="button" className={styles.primary} onClick={save}>
            메모 저장
          </button>
          {saved && (
            <span>
              마지막 저장 {new Date(saved.savedAt).toLocaleString("ko-KR")}
            </span>
          )}
        </div>
        {message && <p role={error ? "alert" : "status"}>{message}</p>}
      </div>
    </section>
  );
}

function RowDetail({ row }: { row: ComparedRow }) {
  return (
    <section className={styles.detail} aria-label={`${row.id} 문항 상세`}>
      <div className={styles.detailHeading}>
        <div>
          <code>{row.id}</code>
          <h3>{row.query}</h3>
        </div>
        <span className={styles.status} data-status={row.outcome}>
          {outcomeLabels[row.outcome]}
        </span>
      </div>
      {row.after?.expected && (
        <p className={styles.expected}>기대 표현 / {row.after.expected}</p>
      )}
      <div className={styles.answers}>
        {[
          ["기준선", row.before],
          ["후보", row.after],
        ].map(([title, value]) => {
          const r = value as ComparedRow["before"];
          return (
            <article key={title as string}>
              <h4>
                {title as string}
                <span>
                  {r
                    ? r.failed
                      ? "측정 장애"
                      : r.passed
                        ? "통과"
                        : "실패"
                    : "문항 없음"}
                </span>
              </h4>
              <p className={styles.reason}>
                {r?.reason ??
                  (r?.passed ? "기록된 통과 조건 충족" : "판정 이유 없음")}
              </p>
              {r?.research && (
                <p
                  className={styles.researchNote}
                  data-ran={r.research.calls > 0}
                >
                  {researchLabel(r.research)}
                </p>
              )}
              {r?.answer ? (
                <pre tabIndex={0} aria-label={`${row.id} ${title} 답변`}>
                  {r.answer}
                </pre>
              ) : (
                <div className={styles.noAnswer}>
                  이 공개 기록에는 답변 본문이 없습니다. 저장된 판정 이유와 실행
                  지표로 비교합니다.
                </div>
              )}
              <details>
                <summary>답변 생성 당시 비용과 시간</summary>
                <dl>
                  <div>
                    <dt>답변 생성 비용</dt>
                    <dd>{usd(r?.cost ?? null)}</dd>
                  </div>
                  <div>
                    <dt>전체 지연</dt>
                    <dd>{seconds(r?.latency ?? null)}</dd>
                  </div>
                </dl>
              </details>
            </article>
          );
        })}
      </div>
      <p className={styles.footnote}>
        기록된 코드 판정입니다. 키워드와 인용 조건을 만족해도 답변 전체의
        정확성을 보장하지 않으며, 처리 단계별 시간과 내부 추론은 포함하지
        않습니다.
      </p>
    </section>
  );
}

function Workbench({ suite }: { suite: AnalysisSuite }) {
  const [baselineId, setBaselineId] = useState(
    suite.baselineId ?? suite.runs[0]?.id ?? "",
  );
  const [candidateId, setCandidateId] = useState(
    suite.candidateId ?? suite.runs[1]?.id ?? "",
  );
  const [filter, setFilter] = useState("attention");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [costLimit, setCostLimit] = useState("50");
  const [latencyLimit, setLatencyLimit] = useState("15");
  const [criteriaLoaded, setCriteriaLoaded] = useState("");
  const before = suite.runs.find((run) => run.id === baselineId);
  const after = suite.runs.find((run) => run.id === candidateId);
  const analysis = useMemo(
    () => (before && after ? compareRuns(before, after) : null),
    [before, after],
  );
  const dataSignature = useMemo(
    () => fingerprint({ before, after }),
    [before, after],
  );
  const criteriaKey = `nexuswiki:regression:criteria:${suite.id}:${baselineId}:${candidateId}`;
  useEffect(() => {
    let cost = "50",
      latency = "15";
    try {
      const value = JSON.parse(localStorage.getItem(criteriaKey) ?? "null");
      if (
        value?.fingerprint === dataSignature &&
        typeof value.cost === "string" &&
        typeof value.latency === "string" &&
        value.cost.trim() &&
        value.latency.trim() &&
        Number.isFinite(Number(value.cost)) &&
        Number(value.cost) >= 0 &&
        Number.isFinite(Number(value.latency)) &&
        Number(value.latency) >= 0
      ) {
        cost = value.cost;
        latency = value.latency;
      }
    } catch {
      /* 저장소를 읽지 못하면 기본 기준으로 시작하고 메모 영역에서 제한을 알린다. */
    }
    setCostLimit(cost);
    setLatencyLimit(latency);
    setCriteriaLoaded(criteriaKey);
  }, [criteriaKey, dataSignature]);
  useEffect(() => {
    if (
      criteriaLoaded !== criteriaKey ||
      !costLimit.trim() ||
      !latencyLimit.trim() ||
      !Number.isFinite(Number(costLimit)) ||
      Number(costLimit) < 0 ||
      !Number.isFinite(Number(latencyLimit)) ||
      Number(latencyLimit) < 0
    )
      return;
    try {
      localStorage.setItem(
        criteriaKey,
        JSON.stringify({
          fingerprint: dataSignature,
          cost: costLimit,
          latency: latencyLimit,
        }),
      );
    } catch {
      /* 검토 메모의 명시적 저장 시 저장 실패를 사용자에게 알린다. */
    }
  }, [criteriaKey, dataSignature, costLimit, latencyLimit, criteriaLoaded]);
  if (!before || !after || !analysis)
    return (
      <section className={styles.empty}>
        <h2>비교할 실행이 부족합니다</h2>
        <p>같은 평가 세트의 실행이 두 개 이상 필요합니다.</p>
      </section>
    );
  const thresholdsValid =
    costLimit.trim() !== "" &&
    latencyLimit.trim() !== "" &&
    Number.isFinite(Number(costLimit)) &&
    Number(costLimit) >= 0 &&
    Number.isFinite(Number(latencyLimit)) &&
    Number(latencyLimit) >= 0;
  const costOk =
    analysis.costChange !== null && analysis.costChange <= Number(costLimit);
  const latencyOk =
    analysis.p95Change !== null &&
    analysis.p95Change <= Number(latencyLimit) * 1000;
  const qualityOk =
    analysis.counts.regressed === 0 &&
    analysis.counts.excluded === 0 &&
    analysis.total > 0;
  const within = qualityOk && costOk && latencyOk;
  const isRescore = after.mode === "rescore" || after.path.includes("재채점");
  const researchRows = analysis.rows.filter((row) => row.after?.research);
  const regressedRows = analysis.rows.filter(
    (row) => row.outcome === "regressed",
  );
  // 도입 실험은 등록된 기준 세트가 공식 판정을 정한다. 화면은 저장된 조건별 결과를 다시 계산하지 않는다.
  const adoption =
    suite.experiment?.kind === "adoption" && suite.experiment.criteria
      ? suite.experiment
      : undefined;
  const criteria = adoption?.criteria;
  const judgeGate = {
    key: "judge",
    ok: null,
    label: "채점 방식",
    detail:
      "기대 표현·인용 조건을 확인하는 코드 판정 · 사람 판정과 대조하지 않음 · 통과가 답변 전체의 정확성을 보장하지 않음",
  };
  const regressedLinks = regressedRows.length > 0 && (
    <>
      {regressedRows.slice(0, 3).map((row) => (
        <button
          type="button"
          key={row.id}
          className={styles.gateLink}
          onClick={() => jumpToQuestions("regressed", row.id)}
        >
          {row.id}
        </button>
      ))}
      {regressedRows.length > 3 && ` 외 ${regressedRows.length - 3}개`}
    </>
  );
  // ok가 boolean인 항목은 within 판정과 같은 네 조건이어야 한다. 하나라도 빠지면 배지와 목록이 서로 다른 말을 한다.
  const thresholdGates: {
    key: string;
    ok: boolean | null;
    label: string;
    detail: ReactNode;
  }[] = [
    {
      key: "regressed",
      ok: analysis.counts.regressed === 0,
      label: `새로 실패 ${analysis.counts.regressed}개`,
      detail:
        regressedRows.length === 0 ? (
          "기준선에서 통과하고 후보에서 실패한 질문 없음"
        ) : (
          <>
            {regressedLinks}
            {regressedRows[0].after?.reason &&
              ` · ${regressedRows[0].after.reason}`}
            {regressedRows.every((row) => row.after?.research?.calls === 0) &&
              " · 재검색이 실행되지 않은 질문이라 재검색 효과가 아닐 수 있음"}
          </>
        ),
    },
    {
      key: "excluded",
      ok: analysis.counts.excluded === 0 && analysis.total > 0,
      label: `검사 중단 ${analysis.counts.excluded}개`,
      detail:
        analysis.total > 0
          ? "끝까지 검사하지 못한 질문은 통과 수에서 제외됩니다"
          : "검사를 마친 질문이 없습니다",
    },
    {
      key: "cost",
      ok: costOk,
      label:
        (isRescore ? "원본 답변 비용 " : "비용 ") +
        (analysis.costChange === null
          ? "미측정"
          : signed(analysis.costChange, 1) + "%"),
      detail: (
        <>
          {usd(before.cost)} → {usd(after.cost)} · 허용 +{costLimit}%{" "}
          <button
            type="button"
            className={styles.gateLink}
            onClick={() => openSettings("cost-limit")}
          >
            기준 바꾸기
          </button>
        </>
      ),
    },
    {
      key: "latency",
      ok: latencyOk,
      label:
        "응답 시간 p95 " +
        (analysis.p95Change === null
          ? "미측정"
          : signed(analysis.p95Change / 1000, 2) + "초"),
      detail: (
        <>
          {seconds(before.p95)} → {seconds(after.p95)} · 허용 +{latencyLimit}초{" "}
          <button
            type="button"
            className={styles.gateLink}
            onClick={() => openSettings("latency-limit")}
          >
            기준 바꾸기
          </button>
        </>
      ),
    },
    // 판정에 들어가지 않는 참고 줄이다. 판정을 얼마나 믿을지를 조건 옆에 두어 따로 읽지 않게 한다.
    judgeGate,
  ];
  const gates = criteria
    ? [
        ...criteria.conditions.map((condition) => ({
          key: condition.key,
          ok: condition.met as boolean | null,
          label: condition.label,
          detail: `${condition.actual} · 허용 ${condition.limit}` as ReactNode,
        })),
        judgeGate,
      ]
    : thresholdGates;
  const blocking = gates.filter((gate) => gate.ok === false).length;
  const gateState = criteria
    ? criteria.adopted
      ? "pass"
      : "review"
    : !thresholdsValid
      ? "invalid"
      : within
        ? "pass"
        : "review";
  const priority: Record<Outcome, number> = {
    regressed: 0,
    excluded: 1,
    failed: 2,
    improved: 3,
    passed: 4,
  };
  const filtered = analysis.rows
    .filter(
      (row) =>
        (filter === "all" ||
          (filter === "attention"
            ? ["regressed", "failed", "excluded"].includes(row.outcome)
            : row.outcome === filter)) &&
        `${row.id} ${row.query}`.toLowerCase().includes(query.toLowerCase()),
    )
    .sort(
      (a, b) =>
        priority[a.outcome] - priority[b.outcome] || a.id.localeCompare(b.id),
    );
  const selected = filtered.find((row) => row.id === selectedId) ?? filtered[0];
  const signature = fingerprint({ before, after, costLimit, latencyLimit });
  const controlsChanged = () => {
    setFilter("attention");
    setQuery("");
    setSelectedId(null);
  };
  function openSettings(inputId: string) {
    const drawer = document.getElementById("settings");
    if (drawer instanceof HTMLDetailsElement) drawer.open = true;
    const input = document.getElementById(inputId);
    input?.scrollIntoView({ behavior: "smooth", block: "center" });
    input?.focus({ preventScroll: true });
  }
  function jumpToQuestions(nextFilter: string, id: string | null) {
    setFilter(nextFilter);
    setQuery("");
    setSelectedId(id);
    document
      .getElementById("questions-heading")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  function exportComparison() {
    const content = {
      schema: "regression-comparison-v1",
      synthetic: true,
      suite: suite.name,
      baseline: before!.label,
      candidate: after!.label,
      conditions: before!.conditions,
      thresholds: {
        cost_increase_percent: Number(costLimit),
        p95_increase_seconds: Number(latencyLimit),
      },
      counts: analysis!.counts,
      rows: analysis!.rows.map((row) => ({
        id: row.id,
        query: row.query,
        outcome: row.outcome,
        before_pass: row.before?.passed ?? null,
        after_pass: row.after?.passed ?? null,
        before_reason: row.before?.reason ?? null,
        after_reason: row.after?.reason ?? null,
      })),
      cost_change_percent: analysis!.costChange,
      p95_change_ms: analysis!.p95Change,
      limitation: suite.limitation,
    };
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(content, null, 2)], {
        type: "application/json",
      }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = `regression-${suite.id}-${baselineId}-${candidateId}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  // 이름은 사람이 붙인 값이라 겹칠 수 있다. id·리비전·시각을 함께 보여야 어떤 실행인지 짚을 수 있다.
  const runIdentity = (run: typeof before) =>
    [
      run.id.length > 12 ? run.id.slice(0, 8) : run.id,
      run.revision,
      run.createdAt && kst(run.createdAt),
    ]
      .filter(Boolean)
      .join(" · ");
  const runLabel = (run: typeof before) =>
    suite.runs.filter((item) => item.label === run.label).length > 1
      ? run.label + " · 기록 " + (suite.runs.indexOf(run) + 1)
      : run.label;
  return (
    <>
      <header className={styles.pageHeader}>
        <div>
          <h1>{suite.guide?.question ?? suite.name}</h1>
          <p>
            {suite.name} · {suite.runs[0]?.rows.length ?? 0}개 질문의 저장된
            검사 결과입니다.
          </p>
        </div>
        {/* 다른 주제 머리말에 두면 그 주제의 검사를 새로 돌리는 버튼으로 오해된다. */}
        {process.env.NODE_ENV === "development" && suite.id === "local" && (
          <button
            type="button"
            className={styles.secondary}
            onClick={openNewCheck}
          >
            {RUN_CHECK_LABEL}
          </button>
        )}
      </header>
      {analysis.valid ? (
        <section
          className={styles.readingSummary}
          aria-labelledby="reading-title"
          data-state={gateState}
        >
          <div className={styles.gateHead}>
            <span className={styles.gateBadge} data-state={gateState}>
              {criteria
                ? criteria.adopted
                  ? "원래 기준 충족"
                  : "원래 기준 미충족"
                : gateState === "pass"
                  ? "조건 충족"
                  : gateState === "review"
                    ? "검토 필요"
                    : "기준 확인 필요"}
            </span>
            <h2 id="reading-title">
              {criteria
                ? blocking > 0
                  ? `원래 기준 ${criteria.conditions.length}개 중 ${blocking}개 미충족`
                  : "원래 기준을 모두 충족했습니다"
                : gateState === "pass"
                  ? "설정한 조건을 모두 충족했습니다"
                  : gateState === "review"
                    ? `적용을 막는 조건 ${blocking}개가 있습니다`
                    : "허용 기준 값을 확인해 주세요"}
            </h2>
          </div>
          <dl className={styles.gateRuns} aria-label="비교한 실행">
            {(
              [
                ["후보", suite.roles?.candidate, after],
                ["기준선", suite.roles?.baseline, before],
              ] as const
            ).map(([role, meaning, run]) => (
              <div key={role}>
                <dt>
                  {role}
                  {meaning && <small>{meaning}</small>}
                </dt>
                <dd>
                  <b>{runLabel(run)}</b>
                  <span>{runIdentity(run)}</span>
                </dd>
              </div>
            ))}
          </dl>
          <p className={styles.gateSource}>
            {isRescore
              ? "저장 답변 재채점 · 추가 모델 호출 비용 없음"
              : "저장된 기록 · 모델 호출 없음"}
          </p>
          <ul className={styles.gateList} aria-label="적용 조건">
            {gates.map((gate) => (
              <li key={gate.key} data-ok={gate.ok ?? "info"}>
                {gate.ok === null ? (
                  <Info size={15} aria-label="참고" />
                ) : gate.ok ? (
                  <Check size={15} aria-label="충족" />
                ) : (
                  <CircleAlert size={15} aria-label="미충족" />
                )}
                <strong>{gate.label}</strong>
                <span>{gate.detail}</span>
              </li>
            ))}
          </ul>
          {criteria && (
            <dl className={styles.provenance} aria-label="판정 기준과 결정">
              <div>
                <dt>판정 기준</dt>
                <dd>
                  <b>{criteria.name}</b>
                  <code>{criteria.source_path}</code>
                </dd>
              </div>
              <div>
                <dt>기록 시점</dt>
                <dd>
                  {criteria.preregistered
                    ? "사전 등록 · 실행 전에 기록됨"
                    : "실행보다 먼저 기록됐음을 증명하지 못함"}
                  <span>
                    기준 첫 커밋 <code>{criteria.source_commit}</code>{" "}
                    {kst(criteria.source_first_commit_at)} · 첫 실행{" "}
                    {kst(criteria.earliest_run_at)} (한국 시간)
                  </span>
                </dd>
              </div>
              {adoption?.decision && (
                <div>
                  <dt>결정</dt>
                  <dd>
                    <b data-status={adoption.decision.status}>
                      {decisionLabels[adoption.decision.status]}
                    </b>
                    {adoption.decision.decided_on}
                    <span>{adoption.decision.rationale}</span>
                  </dd>
                </div>
              )}
            </dl>
          )}
          <p className={styles.gateContext}>
            {criteria && regressedRows.length > 0 && (
              <>
                참고 · 원래 기준은 회귀를 합계로 봅니다. 질문 단위로는 새로 실패{" "}
                {regressedRows.length}개 {regressedLinks}
                {regressedRows.every(
                  (row) => row.after?.research?.calls === 0,
                ) &&
                  " · 재검색이 실행되지 않은 질문이라 재검색 효과가 아닐 수 있음"}
                <br />
              </>
            )}
            참고 · 통과 {analysis.beforePassed}/{analysis.total} →{" "}
            {analysis.afterPassed}/{analysis.total} · 새로 통과{" "}
            {analysis.counts.improved}개 · 여전히 실패 {analysis.counts.failed}
            개
            {researchRows.length > 0 &&
              ` · 재검색 실제 실행 ${researchRows.filter((row) => (row.after?.research?.calls ?? 0) > 0).length}/${researchRows.length}개`}
          </p>
        </section>
      ) : (
        <section className={styles.blocked} role="alert">
          <h2>이 두 결과는 비교할 수 없습니다</h2>
          <ul>
            {analysis.problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
          <p>아래 ‘실행 고르기와 기준 설정’에서 서로 다른 결과를 선택하세요.</p>
        </section>
      )}

      {analysis.valid && (
        <section
          className={styles.workarea}
          aria-labelledby="questions-heading"
        >
          <div className={styles.sectionHeader}>
            <h2 id="questions-heading">
              질문별 결과 <span>{analysis.rows.length}</span>
            </h2>
            <label className={styles.search}>
              <Search size={15} aria-hidden="true" />
              <input
                aria-label="문항 검색"
                placeholder="질문이나 번호로 찾기"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
          </div>
          <p className={styles.footnote}>
            새로 실패는 기준선 통과 → 후보 실패, 새로 통과는 기준선 실패 → 후보
            통과, 여전히 실패는 둘 다 실패입니다. 시간 순서가 아니라 고른 두
            실행의 비교이며, 맞바꾸면 의미도 뒤집힙니다.
          </p>
          <div
            className={styles.filters}
            role="group"
            aria-label="문항 변화 필터"
          >
            {[
              [
                "attention",
                "확인 필요",
                analysis.counts.regressed +
                  analysis.counts.failed +
                  analysis.counts.excluded,
              ],
              ["regressed", "새로 실패", analysis.counts.regressed],
              ["improved", "새로 통과", analysis.counts.improved],
              ["failed", "여전히 실패", analysis.counts.failed],
              ["all", "전체", analysis.rows.length],
            ].map(([value, label, n]) => (
              <button
                type="button"
                key={value}
                aria-pressed={filter === value}
                onClick={() => {
                  setFilter(String(value));
                  setSelectedId(null);
                }}
              >
                {label} <span>{n}</span>
              </button>
            ))}
          </div>
          <div className={styles.analysisLayout}>
            <div className={styles.questionList} aria-label="문항 비교 목록">
              {filtered.length === 0 ? (
                <div className={styles.empty}>
                  <h3>해당하는 질문이 없습니다</h3>
                  <p>다른 필터를 선택하거나 검색어를 지워 보세요.</p>
                  <button
                    type="button"
                    className={styles.secondary}
                    onClick={() => {
                      setFilter("all");
                      setQuery("");
                    }}
                  >
                    전체 문항 보기
                  </button>
                </div>
              ) : (
                filtered.map((row) => (
                  <button
                    type="button"
                    key={row.id}
                    className={styles.question}
                    aria-pressed={selected?.id === row.id}
                    onClick={() => setSelectedId(row.id)}
                  >
                    <div>
                      <code>{row.id}</code>
                      <span className={styles.status} data-status={row.outcome}>
                        {outcomeLabels[row.outcome]}
                      </span>
                    </div>
                    <p>{row.query}</p>
                    <small>
                      {!row.before
                        ? "질문 없음"
                        : row.before.failed
                          ? "검사 중단"
                          : row.before.passed
                            ? "통과"
                            : "실패"}{" "}
                      →{" "}
                      {!row.after
                        ? "질문 없음"
                        : row.after.failed
                          ? "검사 중단"
                          : row.after.passed
                            ? "통과"
                            : "실패"}
                    </small>
                    <ChevronRight size={16} aria-hidden="true" />
                  </button>
                ))
              )}
            </div>
            {selected && <RowDetail row={selected} />}
          </div>
          <p role="status" className={styles.footnote}>
            {filtered.length}문항 표시 · 새로 실패, 검사 중단, 여전히 실패
            순서입니다.
          </p>
        </section>
      )}

      {suite.guide && (
        <details className={styles.methodGuide}>
          <summary>
            검사 방법 <span>사용한 자료 · 검사 방법 · 해석 주의점</span>
          </summary>
          <dl>
            <div>
              <dt>사용한 자료</dt>
              <dd>{suite.guide.data}</dd>
            </div>
            <div>
              <dt>검사 방법</dt>
              <dd>{suite.guide.method}</dd>
            </div>
            <div>
              <dt>해석할 때 주의할 점</dt>
              <dd>{suite.guide.interpretation}</dd>
            </div>
          </dl>
          <p>
            ‘평가 세트’는 같은 목적으로 모은 질문 묶음이고, ‘실행’은 그 묶음을
            한 번 검사한 기록입니다.
          </p>
        </details>
      )}

      <details
        id="settings"
        className={styles.technicalDetails}
        open={!analysis.valid}
      >
        <summary>
          실행 고르기와 기준 설정{" "}
          <span>실행 선택 · 허용 기준 · 고정 조건 · JSON</span>
        </summary>
        {adoption ? (
          // 공식 판정은 등록된 쌍의 저장값이다. 다른 쌍을 고르면 판정과 질문 목록이 서로 다른 쌍을 말한다.
          <section
            id="comparison"
            className={styles.compareControls}
            aria-label="공식 판정 쌍"
          >
            <p className={styles.fixedPair}>
              공식 판정에 쓴 쌍으로 고정 · 기준선 <b>{runLabel(before)}</b> →
              후보 <b>{runLabel(after)}</b>
            </p>
            <div className={styles.match} data-valid={analysis.valid}>
              {analysis.valid ? (
                <Check size={15} aria-hidden="true" />
              ) : (
                <CircleAlert size={15} aria-hidden="true" />
              )}
              {analysis.valid
                ? "같은 질문과 조건으로 검사했습니다"
                : "비교 조건 확인 필요"}
            </div>
          </section>
        ) : (
          <section
            id="comparison"
            className={styles.compareControls}
            aria-label="비교할 실행 선택"
          >
            <label>
              기준선
              <select
                value={baselineId}
                onChange={(e) => {
                  setBaselineId(e.target.value);
                  controlsChanged();
                }}
              >
                {suite.runs.map((run) => (
                  <option key={run.id} value={run.id}>
                    {runLabel(run)}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className={styles.swap}
              aria-label="기준선과 후보 맞바꾸기"
              onClick={() => {
                setBaselineId(candidateId);
                setCandidateId(baselineId);
                controlsChanged();
              }}
            >
              <ArrowLeftRight size={18} aria-hidden="true" />
            </button>
            <label>
              후보
              <select
                value={candidateId}
                onChange={(e) => {
                  setCandidateId(e.target.value);
                  controlsChanged();
                }}
              >
                {suite.runs.map((run) => (
                  <option key={run.id} value={run.id}>
                    {runLabel(run)}
                  </option>
                ))}
              </select>
            </label>
            <div className={styles.match} data-valid={analysis.valid}>
              {analysis.valid ? (
                <Check size={15} aria-hidden="true" />
              ) : (
                <CircleAlert size={15} aria-hidden="true" />
              )}
              {analysis.valid
                ? "같은 질문과 조건으로 검사했습니다"
                : "비교 조건 확인 필요"}
            </div>
          </section>
        )}
        <p className={styles.scope}>
          <FlaskConical size={15} aria-hidden="true" />
          {suite.limitation}
        </p>
        {!adoption && (
          <section className={styles.criteria} aria-labelledby="criteria-title">
            <h3 id="criteria-title">허용 기준</h3>
            <div className={styles.criteriaFields}>
              <label>
                허용 비용 증가 (%)
                <input
                  id="cost-limit"
                  type="number"
                  min="0"
                  step="1"
                  value={costLimit}
                  onChange={(e) => setCostLimit(e.target.value)}
                />
              </label>
              <label>
                허용 p95 증가 (초)
                <input
                  id="latency-limit"
                  type="number"
                  min="0"
                  step="1"
                  value={latencyLimit}
                  onChange={(e) => setLatencyLimit(e.target.value)}
                />
              </label>
              <p>
                새로 실패 0개 · 검사 중단 0개는 고정 조건입니다. 허용 기준은 이
                브라우저에만 저장되며 팀 공용 기준이 아닙니다. 기준 충족은 운영
                적용 승인이 아닙니다.
              </p>
            </div>
            <p className={styles.footnote}>
              p95는 응답 시간을 빠른 순서로 정렬했을 때 95% 지점의 값입니다.
              재채점에 표시되는 비용·응답 시간은 원본 답변 생성 당시 값입니다.
            </p>
          </section>
        )}
        <details className={styles.conditionsDetails}>
          <summary>
            고정 조건 지문 · {Object.keys(before.conditions).length}개
          </summary>
          <dl className={styles.conditions}>
            {Object.entries(before.conditions).map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd>
                  <code>{value}</code>
                </dd>
              </div>
            ))}
          </dl>
        </details>
        {before.path !== after.path && (
          <p className={styles.footnote}>
            실행 경로가 다릅니다: {before.path} / {after.path}. 시간 차이를 모델
            품질 차이로 해석하지 않습니다.
          </p>
        )}
        <button
          type="button"
          className={styles.secondary}
          onClick={exportComparison}
          disabled={!analysis.valid || !thresholdsValid}
        >
          <Download size={16} aria-hidden="true" /> 비교 결과 JSON
        </button>
        {suite.experiment && (
          <a
            className={styles.secondary}
            href="/showcase/regression/experiments.json"
            download
          >
            <Download size={16} aria-hidden="true" /> 실험 기록 JSON
          </a>
        )}
      </details>

      <details className={styles.historyDetails}>
        <summary>전체 검사 기록 보기 · {suite.runs.length}개</summary>
        <section id="history" className={styles.history}>
          <h2>저장된 실행 기록</h2>
          <div
            className={styles.tableScroll}
            tabIndex={0}
            role="region"
            aria-label="실행 기록 표"
          >
            <table>
              <caption>
                {suite.name} · 저장된 기록입니다. 재채점의 모델 지표는 원본 실행
                값입니다.
              </caption>
              <thead>
                <tr>
                  <th scope="col">검사 기록</th>
                  <th scope="col">통과 / 검사한 질문</th>
                  <th scope="col">답변 생성 비용</th>
                  <th scope="col">토큰</th>
                  <th scope="col">응답 시간 p50 / p95</th>
                  <th scope="col">검사 방법</th>
                </tr>
              </thead>
              <tbody>
                {suite.runs.map((run) => (
                  <tr key={run.id}>
                    <th scope="row">
                      {runLabel(run)}
                      <small>{run.model}</small>
                      <small>{runIdentity(run)}</small>
                    </th>
                    <td>
                      {
                        run.rows.filter((row) => row.passed && !row.failed)
                          .length
                      }{" "}
                      / {run.rows.filter((row) => !row.failed).length}
                    </td>
                    <td>{usd(run.cost)}</td>
                    <td>{run.tokens.toLocaleString("ko-KR")}</td>
                    <td>
                      {seconds(run.p50)} / {seconds(run.p95)}
                    </td>
                    <td>{run.path}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </details>
      {analysis.valid && thresholdsValid && criteriaLoaded === criteriaKey && (
        <ReviewPanel
          key={
            suite.id + "-" + baselineId + "-" + candidateId + "-" + signature
          }
          storageKey={
            "nexuswiki:regression:" +
            suite.id +
            ":" +
            baselineId +
            ":" +
            candidateId
          }
          signature={signature}
        />
      )}
    </>
  );
}

export function RegressionDashboard({
  suites: initialSuites = regressionSuites,
  localEnabled,
}: {
  suites?: AnalysisSuite[];
  localEnabled?: boolean;
}) {
  const [localSuite, setLocalSuite] = useState<AnalysisSuite | null>(null);
  const suites = localSuite ? [...initialSuites, localSuite] : initialSuites;
  const localVersion = useRef("");
  const receiveSuite = useCallback((next: AnalysisSuite) => {
    const version = `${next.baselineId}:${next.candidateId}:${next.runs.map((run) => run.id).join(",")}`;
    if (localVersion.current === version) return;
    localVersion.current = version;
    setLocalSuite(next);
  }, []);
  const [suiteId, setSuiteId] = useState(suites[0]?.id ?? "");
  useEffect(() => {
    const selectLinkedSuite = () => {
      const id = window.location.hash.slice(1);
      if (initialSuites.some((item) => item.id === id)) setSuiteId(id);
    };
    selectLinkedSuite();
    window.addEventListener("hashchange", selectLinkedSuite);
    return () => window.removeEventListener("hashchange", selectLinkedSuite);
  }, [initialSuites]);
  const suite = suites.find((item) => item.id === suiteId);
  return (
    <div className={styles.app}>
      <aside className={styles.sidebar}>
        <Link
          href="/showcase/evaluation"
          prefetch={false}
          className={styles.brand}
        >
          NexusWiki <ArrowUpRight size={15} aria-hidden="true" />
        </Link>
        <div className={styles.sideTitle}>답변 검사</div>
        <a href="#reading-title" className={styles.activeNav}>
          <GitCompareArrows size={17} aria-hidden="true" /> 검사 결과
        </a>
        <a href="#history">실행 기록</a>
        <a href="#review">검토 메모</a>
        {process.env.NODE_ENV === "development" && (
          <a href="#judge-workbench">골든셋과 AI 심사</a>
        )}
        <div className={styles.sideTitle}>확인할 주제</div>
        <div role="group" aria-label="평가 세트 선택">
          {suites.map((item) => (
            <button
              type="button"
              key={item.id}
              aria-pressed={item.id === suiteId}
              className={styles.suiteButton}
              onClick={() => setSuiteId(item.id)}
            >
              {item.guide?.short ?? item.name}
              {item.guide && (
                <span className={styles.suiteHint}>{item.name}</span>
              )}
              <small>
                {item.runs[0]?.rows.length ?? 0}문항 · {item.runs.length}개 실행
              </small>
            </button>
          ))}
        </div>
        {process.env.NODE_ENV === "development" && (
          <button
            type="button"
            className={styles.runCheck}
            onClick={openNewCheck}
          >
            {RUN_CHECK_LABEL}
            <small>
              ‘같은 질문의 반복 결과’ 질문 30개 · 결과는 ‘내가 실행한 검증
              이력’에 쌓입니다
            </small>
          </button>
        )}
        <div className={styles.sideNote}>
          <FlaskConical size={16} aria-hidden="true" />
          <strong>저장된 합성 실행</strong>
          <p>
            보존된 합성 기록을 비교합니다. 로컬 개발 환경에서는 별도로
            재채점이나 새 답변 생성을 요청할 수 있습니다.
          </p>
        </div>
      </aside>
      <div className={styles.content}>
        <div className={styles.topbar}>
          <span>
            답변 검사 / <b>결과 비교</b>
          </span>
          <span>공개 합성 기록 · 로컬 검토 메모</span>
        </div>
        <Link
          href={`/showcase/evaluation#${suiteId === "research" ? "research" : "evaluate"}`}
          prefetch={false}
          className={styles.returnLink}
        >
          평가 설계와 실험으로 돌아가기
        </Link>
        <main>
          {localSuite && suiteId !== "local" && (
            <div className={styles.resultNotice}>
              <p>
                이 컴퓨터에 저장된 검사 기록 {localSuite.runs.length}개가
                있습니다.
              </p>
              <button
                type="button"
                className={styles.secondary}
                onClick={() => setSuiteId("local")}
              >
                내 검사 결과 보기
              </button>
            </div>
          )}
          {suite ? (
            <Workbench
              key={`${suite.id}:${suite.baselineId ?? ""}:${suite.candidateId ?? ""}`}
              suite={suite}
            />
          ) : (
            <div className={styles.empty}>
              <h1>평가 실행을 준비해 주세요</h1>
              <p>비교할 저장된 평가 세트가 없습니다.</p>
            </div>
          )}
          <LocalEvaluationPanel
            onSuite={receiveSuite}
            onOpen={() => {
              setSuiteId("local");
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
            enabled={localEnabled}
          />
          <GoldenJudgePanel enabled={localEnabled} />
        </main>
      </div>
    </div>
  );
}
