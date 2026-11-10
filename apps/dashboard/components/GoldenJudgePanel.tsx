"use client";

// #266 · golden-answer-judge: 후보 검토와 실제 사람 제출을 구분하는 로컬 작업대.
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import styles from "./GoldenJudgePanel.module.css";

const metricNames = {
  facts: "사실 일치",
  citation_accuracy: "인용 정확도",
  citation_coverage: "주요 주장 인용 충실도",
  refusal: "거절 적절성",
};
type Metric = keyof typeof metricNames;
const metrics = Object.keys(metricNames) as Metric[];
const verdicts: Record<string, string> = {
  pass: "통과",
  fail: "실패",
  review_needed: "검토 필요",
  not_applicable: "적용 안 됨",
  not_evaluable: "심사 불가",
};
type Judgement = {
  verdict: string;
  reason: string;
  answer_quote?: string;
  evidence?: { anchor: string; quote: string }[];
};
type Review = {
  revision: number;
  reason: string;
  metrics: Partial<Record<Metric | "verified", string | boolean>>;
  saved_at: string;
};
type Sample = {
  id: string;
  question_id: string;
  origin: "synthetic" | "stored";
  label: string;
  fingerprint: string;
  answer: string;
  supplied_evidence: Record<string, string> | null;
  code: Judgement | null;
  citation_validity: Judgement;
};
type Question = {
  id: string;
  query: string;
  kind: string;
  expected_facts: string[];
  allowed_expressions: string[];
  answerable: boolean;
  fingerprint: string;
  evidence: { doc_id: string; start: number; end: number }[];
};
type Result = {
  status: string;
  error?: string;
  metrics: Partial<Record<Metric, Judgement>>;
};
type Stat = {
  paired: number;
  excluded: number;
  agreement: number | null;
  false_pass: number;
  false_fail: number;
};
export type JudgeSnapshot = {
  dataset: {
    version: string;
    questions: Question[];
    documents: { id: string; title: string; text: string }[];
  };
  samples: Sample[];
  results: Record<string, Result>;
  reviews: Record<string, Review>;
  ai_reviews?: Record<
    string,
    { metrics: Record<Metric, Judgement>; reviewed_at?: string }
  >;
  models: string[];
  busy: boolean;
  max_budget_micros: number;
  jobs: {
    id: string;
    status: string;
    asked: number;
    planned: number;
    spent_micros: number;
    unknown_cost: boolean;
    error: string | null;
    not_run?: string[];
  }[];
  agreement: Record<"synthetic" | "stored", Record<Metric, Stat>>;
};

export function AdditionalAiReview({
  review,
}: {
  review?: NonNullable<JudgeSnapshot["ai_reviews"]>[string];
}) {
  if (!review) return null;
  return (
    <details>
      <summary>AI 추가 검토 보기</summary>
      <p>
        대화형 AI가 답변과 실제 인용 자료를 대조한 결과입니다. 사람 판정과
        별도이며 사람 기준 일치도에 포함하지 않습니다.
      </p>
      {metrics.map((key) => {
        const item = review.metrics[key];
        return (
          <section key={key}>
            <h4>
              {metricNames[key]} · {verdicts[item.verdict]}
            </h4>
            <p>{item.reason}</p>
            {item.answer_quote && <blockquote>{item.answer_quote}</blockquote>}
            {item.evidence?.map((ref, index) => (
              <p key={`${ref.anchor}:${index}`} className={styles.quote}>
                {ref.anchor} · {ref.quote}
              </p>
            ))}
          </section>
        );
      })}
    </details>
  );
}

export function HumanForm({
  id,
  target,
  kind,
  review,
  save,
  onDirtyChange,
}: {
  id: string;
  target: string;
  kind: "question" | "sample";
  review?: Review;
  save: (payload: object) => Promise<boolean>;
  onDirtyChange?: (dirty: boolean) => void;
}) {
  const [reason, setReason] = useState("");
  const [choices, setChoices] = useState<Partial<Record<Metric, string>>>({});
  const [confirmed, setConfirmed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [editingRevision, setEditingRevision] = useState(review?.revision ?? 0);
  const stale = (review?.revision ?? 0) !== editingRevision && !saving;
  useEffect(() => {
    onDirtyChange?.(
      !saved && Boolean(reason || confirmed || Object.keys(choices).length),
    );
  }, [reason, confirmed, choices, saved, onDirtyChange]);
  return (
    <form
      className={styles.form}
      onSubmit={async (event) => {
        event.preventDefault();
        if (stale) return;
        setSaving(true);
        setSaved(false);
        const ok = await save({
          action: "judge-review",
          kind,
          id,
          target,
          revision: editingRevision,
          reason,
          metrics: kind === "question" ? { verified: true } : choices,
        });
        setSaving(false);
        setSaved(ok);
        if (ok) setEditingRevision(editingRevision + 1);
      }}
    >
      {review && (
        <p>
          이전 저장: {new Date(review.saved_at).toLocaleString("ko-KR")} ·{" "}
          {review.reason}
        </p>
      )}
      {stale && (
        <p role="alert">
          다른 검토가 저장됐습니다. 작성 중인 내용은 제출하지 않았습니다.{" "}
          <button
            type="button"
            onClick={() => {
              setEditingRevision(review?.revision ?? 0);
              setReason("");
              setChoices({});
              setConfirmed(false);
              setSaved(false);
            }}
          >
            최신 판정으로 다시 검토
          </button>
        </p>
      )}
      {kind === "sample" ? (
        <div className={styles.controls}>
          {metrics.map((metric) => (
            <label key={metric}>
              {metricNames[metric]}
              <select
                required
                value={choices[metric] ?? ""}
                onChange={(e) => {
                  setChoices({ ...choices, [metric]: e.target.value });
                  setSaved(false);
                }}
              >
                <option value="" disabled>
                  직접 선택
                </option>
                {Object.entries(verdicts)
                  .filter(([v]) => v !== "not_evaluable")
                  .map(([v, name]) => (
                    <option value={v} key={v}>
                      {name}
                    </option>
                  ))}
              </select>
            </label>
          ))}
        </div>
      ) : (
        <label className={styles.confirm}>
          <input
            type="checkbox"
            required
            checked={confirmed}
            onChange={(e) => {
              setConfirmed(e.target.checked);
              setSaved(false);
            }}
          />
          질문·기대 사실·원문 근거를 직접 확인했습니다.
        </label>
      )}
      <label>
        검토 근거
        <textarea
          required
          maxLength={1000}
          value={reason}
          onChange={(e) => {
            setReason(e.target.value);
            setSaved(false);
          }}
          placeholder="대조한 사실과 판단 이유를 남겨 주세요."
        />
      </label>
      <button
        disabled={
          saving ||
          stale ||
          !reason.trim() ||
          (kind === "question" ? !confirmed : metrics.some((m) => !choices[m]))
        }
      >
        {saving
          ? "저장 중"
          : kind === "question"
            ? "골든셋 후보 검토 저장"
            : "이 답변의 사람 판정 저장"}
      </button>
      {saved && <p role="status">검토를 로컬 디스크에 저장했습니다.</p>}
    </form>
  );
}

export function GoldenJudgePanel({
  enabled = process.env.NODE_ENV === "development",
}: {
  enabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<JudgeSnapshot | null>(null);
  const [error, setError] = useState("");
  const [origin, setOrigin] = useState<"synthetic" | "stored">("synthetic");
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState("");
  const [model, setModel] = useState("");
  const [budget, setBudget] = useState("0.20");
  const [scope, setScope] = useState("single");
  const [sending, setSending] = useState(false);
  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/local-evaluation?view=judge", {
        cache: "no-store",
      });
      const next = await response.json();
      if (!response.ok) throw new Error(next.error);
      if (!next.dataset || !Array.isArray(next.samples))
        throw new Error("실행기를 최신 버전으로 다시 시작해 주세요.");
      setData(next);
      setError("");
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "실행기에 연결하지 못했습니다.",
      );
    }
  }, []);
  useEffect(() => {
    if (!enabled || !open) return;
    void refresh();
    const timer = setInterval(() => void refresh(), 3000);
    return () => clearInterval(timer);
  }, [enabled, open, refresh]);
  if (!enabled) return null;
  async function action(payload: object) {
    try {
      const response = await fetch("/api/local-evaluation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      await refresh();
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "저장하지 못했습니다.");
      return false;
    }
  }
  const available = data?.samples.filter((s) => s.origin === origin) ?? [];
  const visible = available.filter((s) => {
    const human = data?.reviews[s.fingerprint];
    const llm = data?.results[s.fingerprint];
    if (filter === "unreviewed") return !human;
    if (filter === "unavailable")
      return (
        !llm ||
        llm.status === "error" ||
        metrics.some((m) => llm.metrics[m]?.verdict === "not_evaluable")
      );
    if (filter === "disagreed")
      return metrics.some(
        (m) =>
          ["pass", "fail"].includes(String(human?.metrics[m])) &&
          ["pass", "fail"].includes(llm?.metrics[m]?.verdict ?? "") &&
          human?.metrics[m] !== llm?.metrics[m]?.verdict,
      );
    return true;
  });
  const sample = visible.find((s) => s.id === selected) ?? visible[0];
  const question = data?.dataset.questions.find(
    (q) => q.id === sample?.question_id,
  );
  const human = sample ? data?.reviews[sample.fingerprint] : undefined;
  const llm = sample ? data?.results[sample.fingerprint] : undefined;
  const reviewed =
    data?.dataset.questions.filter((q) => data.reviews[q.fingerprint]).length ??
    0;
  return (
    <details
      id="judge-workbench"
      className={styles.panel}
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary>
        골든셋과 AI 심사 <span>기대한 사실 · 인용 근거 · 사람과의 불일치</span>
      </summary>
      <div className={styles.body}>
        <h2>AI가 채점한 결과도, 근거와 대조합니다.</h2>
        <p className={styles.intro}>
          질문과 정답 근거를 먼저 확인하고, 저장 답변을 심사한 뒤 사람의 판단과
          비교합니다. 이 작업대는 로컬 전용입니다. 열어 보기에는 모델 비용이
          들지 않습니다.
        </p>
        <p>
          <Link href="/showcase/review" prefetch={false}>
            검토 전용 페이지 열기 →
          </Link>
        </p>
        {error && (
          <p role="alert" className={styles.error}>
            {error}{" "}
            <button type="button" onClick={() => void refresh()}>
              다시 연결
            </button>
          </p>
        )}
        {!data && !error && (
          <p role="status">골든셋 후보와 로컬 기록을 불러오고 있습니다.</p>
        )}
        {data && (
          <>
            <p className={styles.notice}>
              <strong>30문항 중 {reviewed}문항을 사람이 검토했습니다.</strong>{" "}
              나머지는 골든셋 후보입니다. 합성 예시 답변은 실제 모델의 성적이
              아닙니다.
            </p>
            <div className={styles.controls}>
              <label>
                답변 출처
                <select
                  value={origin}
                  onChange={(e) => {
                    setOrigin(e.target.value as typeof origin);
                    setSelected("");
                  }}
                >
                  <option value="synthetic">
                    검증용 합성 예시 · 실측 아님
                  </option>
                  <option value="stored">저장된 실제 모델 답변</option>
                </select>
              </label>
              <label>
                검토할 표본
                <select
                  value={filter}
                  onChange={(e) => {
                    setFilter(e.target.value);
                    setSelected("");
                  }}
                >
                  <option value="all">전체</option>
                  <option value="unreviewed">사람 미검토</option>
                  <option value="disagreed">사람과 AI 불일치</option>
                  <option value="unavailable">미심사 또는 심사 불가</option>
                </select>
              </label>
              <label>
                질문과 답변
                <select
                  value={sample?.id ?? ""}
                  onChange={(e) => setSelected(e.target.value)}
                >
                  {!visible.length && <option value="">표본 없음</option>}
                  {visible.map((s) => (
                    <option value={s.id} key={s.id}>
                      {s.question_id} · {s.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {!sample && (
              <p className={styles.notice}>
                이 조건의 표본이 없습니다. 다른 출처나 필터를 선택해 주세요.
                질문이 변경된 과거 답변은 자동 연결하지 않습니다.
              </p>
            )}
            {sample && question && (
              <article>
                <h3>{question.query}</h3>
                <p>
                  {question.id} ·{" "}
                  {question.answerable ? "답변 가능" : "근거 부족으로 거절"} ·{" "}
                  {data.dataset.version}
                </p>
                <div className={styles.evidence}>
                  <section aria-label="기대한 사실">
                    <h4>기대한 사실</h4>
                    {question.expected_facts.length ? (
                      <ul>
                        {question.expected_facts.map((f) => (
                          <li key={f}>{f}</li>
                        ))}
                      </ul>
                    ) : (
                      <p>자료에서 답을 확인할 수 없다고 설명해야 합니다.</p>
                    )}
                    <p>{question.allowed_expressions.join(" · ")}</p>
                  </section>
                  <section aria-label="대조할 답변">
                    <h4>대조할 답변</h4>
                    <p>
                      {sample.origin === "synthetic"
                        ? "검증용 합성 예시 · 실제 모델 출력 아님"
                        : sample.label}
                    </p>
                    <pre tabIndex={0}>{sample.answer}</pre>
                  </section>
                </div>
                <details>
                  <summary>정답 원문 근거와 후보 검토</summary>
                  {question.evidence.map((ref) => {
                    const doc = data.dataset.documents.find(
                      (d) => d.id === ref.doc_id,
                    )!;
                    return (
                      <details key={ref.doc_id}>
                        <summary>
                          {doc.title} · {ref.start}–{ref.end}
                        </summary>
                        <p className={styles.quote}>
                          {doc.text.slice(ref.start, ref.end)}
                        </p>
                      </details>
                    );
                  })}
                  <HumanForm
                    key={question.fingerprint}
                    id={question.id}
                    target={question.fingerprint}
                    kind="question"
                    review={data.reviews[question.fingerprint]}
                    save={action}
                  />
                </details>
                <details>
                  <summary>답변 생성 당시 제공된 인용 근거</summary>
                  {sample.supplied_evidence ? (
                    Object.entries(sample.supplied_evidence).map(
                      ([anchor, text]) => (
                        <details key={anchor}>
                          <summary>{anchor}</summary>
                          <p className={styles.quote}>{text}</p>
                        </details>
                      ),
                    )
                  ) : (
                    <p>
                      이 기록에는 생성 당시 근거 맵이 없습니다. 정답 원문으로
                      대신 채우지 않으며 인용 의미 지표는 심사 불가로 남깁니다.
                    </p>
                  )}
                </details>
                <div className={styles.tableWrap}>
                  <table>
                    <caption>코드 / LLM / 사람 판정 대조</caption>
                    <thead>
                      <tr>
                        <th scope="col">검사 항목</th>
                        <th scope="col">코드</th>
                        <th scope="col">LLM 심사</th>
                        <th scope="col">사람 확인</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <th scope="row">인용 표식 유효성</th>
                        <td>
                          {verdicts[sample.citation_validity.verdict]}
                          <small>{sample.citation_validity.reason}</small>
                        </td>
                        <td>코드 검사 항목</td>
                        <td>의미 심사와 별도</td>
                      </tr>
                      {metrics.map((m) => (
                        <tr key={m}>
                          <th scope="row">{metricNames[m]}</th>
                          <td>
                            {m === "facts" && sample.code ? (
                              <>
                                {verdicts[sample.code.verdict]}
                                <small>
                                  {sample.code.reason} · 기존 규칙 판정
                                </small>
                              </>
                            ) : (
                              "코드 의미 판정 없음"
                            )}
                          </td>
                          <td>
                            {llm?.metrics[m] ? (
                              <>
                                {verdicts[llm.metrics[m]!.verdict]}
                                <small>{llm.metrics[m]!.reason}</small>
                              </>
                            ) : (
                              (llm?.error ?? "미심사")
                            )}
                          </td>
                          <td>
                            {human?.metrics[m]
                              ? verdicts[String(human.metrics[m])]
                              : "사람 미검토"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {llm && (
                  <details>
                    <summary>AI 심사의 답변·근거 구간</summary>
                    {metrics.map((m) => (
                      <section key={m}>
                        <h4>{metricNames[m]}</h4>
                        <p>
                          {llm.metrics[m]?.answer_quote || "답변 구간 없음"}
                        </p>
                        {llm.metrics[m]?.evidence?.map((e, i) => (
                          <blockquote key={i}>
                            {e.anchor}: {e.quote}
                          </blockquote>
                        ))}
                      </section>
                    ))}
                  </details>
                )}
                <details>
                  <summary>이 답변의 사람 판정 남기기</summary>
                  <p>
                    후보 검토와 별도입니다. 네 항목을 직접 선택하고 대조한
                    근거를 남깁니다.
                  </p>
                  <HumanForm
                    key={sample.fingerprint}
                    id={sample.id}
                    target={sample.fingerprint}
                    kind="sample"
                    review={human}
                    save={action}
                  />
                </details>
              </article>
            )}
            <details className={styles.run}>
              <summary>저장 답변을 AI로 심사하기 · 유료</summary>
              <p>
                새 답변을 만들지 않고 현재 저장된 답변을 심사합니다.
                모델·예산·범위를 확인한 뒤 실행하세요. 공급자 비용 보고 지연으로
                절대 지출 상한을 보장하지는 않습니다.
              </p>
              {!data.models.length && (
                <p className={styles.notice}>
                  심사 모델이 준비되지 않았습니다. 서버에 허용 모델과 가격·키를
                  설정한 뒤 실행기를 다시 시작하세요. 후보와 근거 확인은 지금
                  가능합니다.
                </p>
              )}
              <form
                className={styles.form}
                onSubmit={async (e) => {
                  e.preventDefault();
                  setSending(true);
                  await action({
                    action: "judge-run",
                    model,
                    budget_micros: Math.round(Number(budget) * 1e6),
                    sample_ids:
                      scope === "single"
                        ? [sample!.id]
                        : available.slice(0, 30).map((s) => s.id),
                  });
                  setSending(false);
                }}
              >
                <div className={styles.controls}>
                  <label>
                    심사 모델
                    <select
                      required
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                    >
                      <option value="" disabled>
                        모델 선택
                      </option>
                      {data.models.map((m) => (
                        <option key={m}>{m}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    심사 예산 (USD)
                    <input
                      type="number"
                      required
                      min="0.01"
                      max={data.max_budget_micros / 1e6}
                      step="0.01"
                      value={budget}
                      onChange={(e) => setBudget(e.target.value)}
                    />
                  </label>
                  <label>
                    심사 범위
                    <select
                      value={scope}
                      onChange={(e) => setScope(e.target.value)}
                    >
                      <option value="single">현재 답변 1개</option>
                      <option value="group">
                        현재 출처의 첫 {Math.min(available.length, 30)}개 답변 ·
                        필터 무관
                      </option>
                    </select>
                  </label>
                </div>
                <button
                  disabled={
                    !sample ||
                    !model ||
                    !data.models.length ||
                    data.busy ||
                    sending
                  }
                >
                  {sending
                    ? "요청 중"
                    : data.busy
                      ? "다른 평가 진행 중"
                      : "선택한 저장 답변 심사 · 유료"}
                </button>
              </form>
              {data.jobs.map((job) => (
                <p key={job.id} role="status">
                  {
                    (
                      {
                        queued: "대기",
                        running: "진행 중",
                        completed: "심사 완료",
                        partial: "부분 실행",
                        failed: "실패",
                        interrupted: "중단",
                      } as Record<string, string>
                    )[job.status]
                  }{" "}
                  · {job.asked}/{job.planned}개 시도 · 관측 비용 $
                  {(job.spent_micros / 1e6).toFixed(4)}
                  {job.unknown_cost && " · 비용 미관측 호출 있음"}
                  {job.error && ` · ${job.error}`}
                  {job.not_run?.length
                    ? ` · 미실행 ${job.not_run.length}개`
                    : ""}
                </p>
              ))}
            </details>
            <h3>사람 판정과 얼마나 일치하나요?</h3>
            <p>
              현재 출처:{" "}
              {origin === "synthetic"
                ? "검증용 합성 예시"
                : "저장된 실제 모델 답변"}
              . 동일 입력·지표에 사람과 AI가 명시적으로 통과·실패를 정한 쌍만
              비교합니다.
            </p>
            <div className={styles.tableWrap}>
              <table>
                <caption>출처별 사람 기준 일치도</caption>
                <thead>
                  <tr>
                    <th>항목</th>
                    <th>일치율</th>
                    <th>비교/제외</th>
                    <th>오통과/오실패</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.map((m) => {
                    const s = data.agreement[origin][m];
                    return (
                      <tr key={m}>
                        <th scope="row">{metricNames[m]}</th>
                        <td>
                          {s.agreement === null
                            ? "미측정"
                            : `${(s.agreement * 100).toFixed(1)}%`}
                        </td>
                        <td>
                          {s.paired} / {s.excluded}
                        </td>
                        <td>
                          {s.false_pass} / {s.false_fail}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </details>
  );
}
