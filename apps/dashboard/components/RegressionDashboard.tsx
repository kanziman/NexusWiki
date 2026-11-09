"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LocalEvaluationPanel } from "./LocalEvaluationPanel";
import {
  ArrowLeftRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  CircleAlert,
  Download,
  FlaskConical,
  GitCompareArrows,
  Search,
} from "lucide-react";
import {
  compareRuns,
  outcomeLabels,
  type AnalysisSuite,
  type ComparedRow,
  type Outcome,
} from "@/lib/regression-analysis";
import { regressionSuites } from "@/lib/regression-data";
import styles from "./RegressionDashboard.module.css";

const usd = (value: number | null) =>
  value === null ? "미측정" : `$${(value / 1e6).toFixed(4)}`;
const seconds = (value: number | null) =>
  value === null ? "미측정" : `${(value / 1000).toFixed(2)}초`;
const signed = (value: number, digits = 0) =>
  `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;

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
          ["기준 실행", row.before],
          ["비교 실행", row.after],
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
  const isRescore = after.mode === "rescore" || after.path.includes("재채점");
  const runLabel = (run: typeof before) =>
    suite.runs.filter((item) => item.label === run.label).length > 1
      ? run.label + " · 기록 " + (suite.runs.indexOf(run) + 1)
      : run.label;
  function openNewCheck() {
    const drawer = document.getElementById("new-check");
    if (drawer instanceof HTMLDetailsElement) drawer.open = true;
    drawer?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
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
        {process.env.NODE_ENV === "development" && (
          <button
            type="button"
            className={styles.secondary}
            onClick={openNewCheck}
          >
            새 검사 시작
          </button>
        )}
      </header>
      {analysis.valid ? (
        <section
          className={styles.readingSummary}
          aria-labelledby="reading-title"
        >
          <h2 id="reading-title">
            {analysis.total}개 중 {analysis.afterPassed}개가 검사 기준을
            통과했습니다.
          </h2>
          <p>
            {analysis.beforePassed === analysis.afterPassed
              ? "기준으로 본 결과와 통과 수는 같습니다."
              : "기준으로 본 결과보다 " +
                Math.abs(analysis.afterPassed - analysis.beforePassed) +
                "개 " +
                (analysis.afterPassed > analysis.beforePassed
                  ? "더 통과했습니다."
                  : "덜 통과했습니다.")}{" "}
            질문별 변화도 함께 확인하세요.
          </p>
          <dl>
            <div>
              <dt>새로 실패</dt>
              <dd>
                {analysis.counts.regressed}
                <small>개</small>
              </dd>
              <span>전에는 통과, 이번에는 실패</span>
            </div>
            <div>
              <dt>여전히 실패</dt>
              <dd>
                {analysis.counts.failed}
                <small>개</small>
              </dd>
              <span>두 결과에서 모두 실패</span>
            </div>
            <div>
              <dt>새로 통과</dt>
              <dd>
                {analysis.counts.improved}
                <small>개</small>
              </dd>
              <span>전에는 실패, 이번에는 통과</span>
            </div>
          </dl>
          {analysis.counts.excluded > 0 && (
            <p>
              검사를 마치지 못한 {analysis.counts.excluded}개 질문은 위 통과
              수에서 제외했습니다.
            </p>
          )}
          <p className={styles.evidenceNote}>
            {isRescore
              ? "저장된 답변을 다시 채점한 결과입니다. 새 답변은 만들지 않았고, 추가 모델 호출 비용은 없습니다."
              : "저장된 모델 실행 기록을 비교합니다. 이 화면을 열어도 모델을 새로 호출하지 않습니다."}
          </p>
          {!isRescore && (
            <p className={styles.costSentence}>
              답변 생성 당시 비용: 기준 {usd(before.cost)} → 확인할 결과{" "}
              {usd(after.cost)}
              {analysis.costChange !== null
                ? " (" + signed(analysis.costChange, 1) + "%)"
                : ""}
              .
            </p>
          )}
          <button
            type="button"
            className={styles.primary}
            onClick={() => {
              setFilter("attention");
              setQuery("");
              setSelectedId(null);
              document
                .getElementById("questions-heading")
                ?.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
          >
            확인할 질문{" "}
            {analysis.counts.regressed +
              analysis.counts.failed +
              analysis.counts.excluded}
            개 보기
          </button>
          <p className={styles.footnote}>
            통과는 정해 둔 기대 표현과 인용 조건을 만족했다는 뜻입니다. 답변
            전체가 정확하다는 보장은 아닙니다.
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
          <p>
            아래 ‘비교할 검사 기록과 상세 수치 보기’를 펼쳐 서로 다른 결과를
            선택하세요.
          </p>
        </section>
      )}

      {suite.guide && (
        <details className={styles.methodGuide}>
          <summary>어떤 자료로, 어떻게 검사했나요?</summary>
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

      <details className={styles.technicalDetails} open={!analysis.valid}>
        <summary>비교할 검사 기록과 상세 수치 보기</summary>
        <section
          id="comparison"
          className={styles.compareControls}
          aria-label="비교 실행 선택"
        >
          <label>
            기준 실행
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
            aria-label="기준과 비교 실행 맞바꾸기"
            onClick={() => {
              setBaselineId(candidateId);
              setCandidateId(baselineId);
              controlsChanged();
            }}
          >
            <ArrowLeftRight size={18} aria-hidden="true" />
          </button>
          <label>
            비교 실행
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
        <p className={styles.scope}>
          <FlaskConical size={15} aria-hidden="true" />
          {suite.limitation}
        </p>
        {analysis.valid && (
          <>
            <section className={styles.summary} aria-label="비교 결과 요약">
              <div>
                <span>검사 통과</span>
                <strong>
                  {analysis.beforePassed}
                  <small>/{analysis.total}</small>
                  <span> → </span>
                  {analysis.afterPassed}
                  <small>/{analysis.total}</small>
                </strong>
                <p>
                  {signed(analysis.afterPassed - analysis.beforePassed)}개 ·
                  검사 중단 {analysis.counts.excluded}개 제외
                </p>
              </div>
              <div>
                <span>질문별 변화</span>
                <strong>
                  <em data-kind="regressed">
                    새로 실패 {analysis.counts.regressed}
                  </em>
                  <em data-kind="improved">
                    새로 통과 {analysis.counts.improved}
                  </em>
                </strong>
                <p>
                  여전히 실패 {analysis.counts.failed} · 계속 통과{" "}
                  {analysis.counts.passed}
                </p>
              </div>
              <div>
                <span>
                  {isRescore ? "원본 답변 생성 비용" : "전체 답변 생성 비용"}
                </span>
                <strong>{usd(after.cost)}</strong>
                <p>
                  {usd(before.cost)} 대비{" "}
                  {analysis.costChange === null
                    ? "변화율 미측정"
                    : signed(analysis.costChange, 1) + "%"}
                  {isRescore && " · 이번 재채점 비용이 아닙니다"}
                </p>
              </div>
              <div>
                <span>
                  {isRescore ? "원본 답변 응답 시간 (p95)" : "응답 시간 (p95)"}
                </span>
                <strong>{seconds(after.p95)}</strong>
                <p>
                  기준 {seconds(before.p95)} ·{" "}
                  {analysis.p95Change === null
                    ? "차이 미측정"
                    : signed(analysis.p95Change / 1000, 2) + "초"}
                </p>
              </div>
            </section>
            <p className={styles.footnote}>
              p95는 응답 시간을 빠른 순서로 정렬했을 때 95% 지점의 값입니다.
              재채점에 표시되는 모델 지표는 원본 실행 당시 값입니다.
            </p>
            <section
              className={styles.verdict}
              aria-label="검토 기준 결과"
              data-pass={within && thresholdsValid}
            >
              <GitCompareArrows size={21} aria-hidden="true" />
              <div>
                <h2>
                  {!thresholdsValid
                    ? "검토 기준을 확인해 주세요"
                    : within
                      ? "설정한 비교 조건은 충족했습니다"
                      : "적용 전 확인할 조건이 있습니다"}
                </h2>
                <p>
                  새로 실패한 질문 {analysis.counts.regressed}개, 여전히 실패한
                  질문 {analysis.counts.failed}개입니다.{" "}
                  {!costOk && "비용 조건은 미충족 또는 미측정입니다. "}
                  {!latencyOk && "응답 시간 조건은 미충족 또는 미측정입니다. "}
                  수치 조건을 만족해도 남은 실패가 해결됐다는 뜻은 아닙니다.
                </p>
              </div>
            </section>
          </>
        )}
        <details className={styles.criteria}>
          <summary>검토 기준과 고정 조건</summary>
          <div className={styles.criteriaFields}>
            <label>
              허용 비용 증가 (%)
              <input
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
                type="number"
                min="0"
                step="1"
                value={latencyLimit}
                onChange={(e) => setLatencyLimit(e.target.value)}
              />
            </label>
            <p>
              새로 실패 0개 · 검사 중단 0개. 기준 충족은 운영 적용 승인이
              아닙니다.
            </p>
          </div>
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
          {before.path !== after.path && (
            <p>
              실행 경로가 다릅니다: {before.path} / {after.path}. 시간 차이를
              모델 품질 차이로 해석하지 않습니다.
            </p>
          )}
        </details>
        <button
          type="button"
          className={styles.secondary}
          onClick={exportComparison}
          disabled={!analysis.valid || !thresholdsValid}
        >
          <Download size={16} aria-hidden="true" /> 비교 결과 JSON
        </button>
      </details>

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
            질문을 선택하면 어떤 기준을 통과하지 못했는지, 기록된 답변이
            무엇인지 확인할 수 있습니다.
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
          <LocalEvaluationPanel onSuite={receiveSuite} enabled={localEnabled} />
        </main>
      </div>
    </div>
  );
}
