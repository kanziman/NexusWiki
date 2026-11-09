"use client";

import { useCallback, useEffect, useState } from "react";
import type { AnalysisRun, AnalysisSuite } from "@/lib/regression-analysis";
import styles from "./RegressionDashboard.module.css";

type Job = {
  id: string;
  label: string;
  mode: string;
  status: string;
  asked: number;
  planned: number;
  error: string | null;
  spent_micros?: number;
};
export type LocalSnapshot = {
  runs: (AnalysisRun & { mode: string })[];
  baseline_id: string | null;
  jobs: Job[];
  model_ready: boolean;
  max_budget_micros: number;
};
const labels: Record<string, string> = {
  queued: "대기",
  running: "실행 중",
  completed: "완료",
  partial: "부분 실행",
  failed: "실행 실패",
  interrupted: "중단됨",
};
export function LocalEvaluationPanel({
  onSuite,
  enabled = process.env.NODE_ENV === "development",
}: {
  onSuite: (suite: AnalysisSuite) => void;
  enabled?: boolean;
}) {
  const [snapshot, setSnapshot] = useState<LocalSnapshot | null>(null);
  const [error, setError] = useState("");
  const [label, setLabel] = useState("");
  const [mode, setMode] = useState("rescore");
  const [budget, setBudget] = useState("1");
  const [limit, setLimit] = useState("30");
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/local-evaluation", {
        cache: "no-store",
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error);
      setSnapshot(data);
      setError("");
      if (data.runs.length) {
        const runs = data.runs as AnalysisRun[];
        const baseline = data.baseline_id ?? runs[0].id;
        const candidate = [...runs]
          .reverse()
          .find((run) => run.id !== baseline)?.id;
        onSuite({
          id: "local",
          name: "로컬 누적 실행",
          guide: {
            short: "내가 실행한 검증 이력",
            question: "이번 검증은 기준 실행과 무엇이 달라졌나요?",
            data: "이 컴퓨터에서 완료한 합성 질문 평가를 모았습니다. 실행 이름은 사용자가 붙인 이름이며, 이름이 달라도 사용한 질문과 답변이 같을 수 있습니다.",
            method:
              "지정한 기준과 새로 완료한 실행을 비교합니다. 무료 재채점은 저장된 답변을 그대로 두고 채점 규칙만 다시 적용합니다. 새 답변 생성은 모델을 다시 호출하는 별도 실행입니다.",
            interpretation:
              "같은 답변을 같은 규칙으로 두 번 재채점하면 결과가 같은 것이 정상입니다. 실제 답변 품질의 변화를 보려면 새 답변 생성 실행을 비교하세요. 재채점의 비용·지연은 원본 답변 생성 당시 기록입니다.",
          },
          description: "지정한 기준 실행과 새로 완료된 평가를 자동 비교합니다.",
          limitation:
            "재채점은 저장된 답변을 다시 채점합니다. 표시되는 모델 비용·지연은 원본 실행 값이며 새 호출 비용이 아닙니다. 유료 실행은 로컬 API·워커 준비가 필요합니다.",
          runs,
          baselineId: baseline,
          candidateId: candidate,
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "실행기를 확인하세요.");
    }
  }, [onSuite]);
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    const load = () => {
      if (active) void refresh();
    };
    load();
    const timer = setInterval(load, 2000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [enabled, refresh]);
  if (!enabled) return null;
  async function action(payload: object) {
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/local-evaluation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "실행 요청 실패");
    } finally {
      setBusy(false);
    }
  }
  const running = snapshot?.jobs.some((job) =>
    ["queued", "running"].includes(job.status),
  );
  return (
    <details id="new-check" className={styles.runDrawer}>
      <summary>
        새 검사 시작 <span>저장 답변 다시 채점 · AI 답변 새로 만들기</span>
      </summary>
      <section className={styles.localPanel} aria-labelledby="local-title">
        <div className={styles.sectionHeader}>
          <h2 id="local-title">검사 방법과 이름을 정하세요</h2>
          <span>
            {snapshot
              ? "접속됨 · 결과는 로컬 디스크에 보존"
              : error
                ? "실행기 연결 필요"
                : "연결을 확인하고 있습니다"}
          </span>
        </div>
        {!snapshot && (
          <>
            <p>다음 명령으로 루프백 전용 실행기를 시작하세요.</p>
            <code>.venv/bin/python scripts/local_evaluation_server.py</code>
            <button
              type="button"
              className={styles.secondary}
              onClick={() => void refresh()}
            >
              연결 다시 확인
            </button>
          </>
        )}
        {snapshot && (
          <>
            <div className={styles.localForm}>
              <label>
                검사 방법
                <select value={mode} onChange={(e) => setMode(e.target.value)}>
                  <option value="rescore">저장 답변 다시 채점 · 무료</option>
                  <option value="model" disabled={!snapshot.model_ready}>
                    AI 답변 새로 만들기 · 유료
                    {!snapshot.model_ready ? " (API 준비 필요)" : ""}
                  </option>
                </select>
              </label>
              <label>
                검사 이름
                <input
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  maxLength={60}
                  placeholder="예: 인용 채점기 수정 후"
                />
              </label>
              {mode === "model" && (
                <>
                  <label>
                    지출 목표 상한 ($)
                    <input
                      type="number"
                      min="0.2"
                      max={snapshot.max_budget_micros / 1e6}
                      step="0.1"
                      value={budget}
                      onChange={(e) => setBudget(e.target.value)}
                    />
                  </label>
                  <label>
                    문항 수
                    <input
                      type="number"
                      min="1"
                      max="30"
                      value={limit}
                      onChange={(e) => setLimit(e.target.value)}
                    />
                  </label>
                </>
              )}
              <button
                type="button"
                className={styles.primary}
                disabled={
                  busy ||
                  running ||
                  !label.trim() ||
                  (mode === "model" &&
                    (!snapshot.model_ready ||
                      !Number.isFinite(Number(budget)) ||
                      Number(budget) < 0.2 ||
                      Number(budget) > snapshot.max_budget_micros / 1e6 ||
                      !Number.isInteger(Number(limit)) ||
                      Number(limit) < 1 ||
                      Number(limit) > 30))
                }
                onClick={() =>
                  void action({
                    action: "run",
                    mode,
                    label: label.trim(),
                    budget_micros: Math.round(Number(budget) * 1e6),
                    limit: Number(limit),
                  })
                }
              >
                {busy
                  ? "요청 중"
                  : running
                    ? "검사 중"
                    : mode === "rescore"
                      ? "다시 채점하기 · 무료"
                      : "새 답변 만들어 검사하기 · 유료"}
              </button>
            </div>
            {!snapshot.model_ready && (
              <p className={styles.footnote}>
                AI 답변 새로 만들기는 아직 준비되지 않았습니다. 로컬 실행 환경을
                연결한 뒤 사용할 수 있습니다. 지금은 저장된 답변을 무료로 다시
                채점할 수 있습니다.
              </p>
            )}
            {mode === "model" && (
              <p className={styles.footnote}>
                다음 호출 전 추정 비용을 확인해 멈춥니다. 공급자 비용 보고
                지연이나 추정 오차가 있어 절대 지출 보장은 아닙니다. 기존
                워크스페이스 예산 제한도 적용됩니다.
              </p>
            )}
            <div className={styles.localJobs} aria-live="polite">
              {snapshot.jobs.slice(0, 4).map((job) => (
                <div key={job.id}>
                  <b>{job.label}</b>
                  <span>
                    {labels[job.status] ?? job.status} · {job.asked}/
                    {job.planned}
                    문항{job.mode === "rescore" ? " · 새 모델 호출 없음" : ""}
                  </span>
                  {job.error && <small>{job.error}</small>}
                </div>
              ))}
            </div>
            {snapshot.runs.length > 0 && (
              <label className={styles.baselineSelect}>
                기준 실행 지정
                <select
                  aria-label="로컬 기준 실행 지정"
                  value={snapshot.baseline_id ?? ""}
                  disabled={busy || running}
                  onChange={(e) =>
                    void action({ action: "baseline", run_id: e.target.value })
                  }
                >
                  {snapshot.runs.map((run) => (
                    <option key={run.id} value={run.id}>
                      {run.label}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </>
        )}
        {error && <p role="alert">{error}</p>}
      </section>
    </details>
  );
}
