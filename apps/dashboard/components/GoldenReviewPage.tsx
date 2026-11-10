"use client";

// #266: 로컬 판정 저장 계약을 공유하는 집중 검토 화면. 모델을 호출하지 않는다.
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  AdditionalAiReview,
  HumanForm,
  type JudgeSnapshot,
} from "./GoldenJudgePanel";
import formStyles from "./GoldenJudgePanel.module.css";
import styles from "./GoldenReviewPage.module.css";

export function GoldenReviewPage({
  enabled = process.env.NODE_ENV === "development",
}: {
  enabled?: boolean;
}) {
  const [data, setData] = useState<JudgeSnapshot | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState("");
  const [mode, setMode] = useState<"question" | "sample">("question");
  const [origin, setOrigin] = useState("stored");
  const [sampleId, setSampleId] = useState("");
  const [onlyPending, setOnlyPending] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [draftEpoch, setDraftEpoch] = useState(0);
  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/local-evaluation?view=judge", {
        cache: "no-store",
      });
      const value = await response.json();
      if (!response.ok) throw new Error(value.error);
      if (!value.dataset || !Array.isArray(value.samples))
        throw new Error("실행기를 최신 버전으로 다시 시작해 주세요.");
      setData(value);
      setError("");
      return true;
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "로컬 실행기에 연결하지 못했습니다.",
      );
      return false;
    }
  }, []);
  useEffect(() => {
    if (!enabled) return;
    void refresh();
    const timer = setInterval(() => void refresh(), 3000);
    return () => clearInterval(timer);
  }, [enabled, refresh]);
  async function save(payload: object) {
    try {
      const response = await fetch("/api/local-evaluation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const value = await response.json();
      if (!response.ok) throw new Error(value.error);
      return await refresh();
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "검토 저장 실패. 작성한 내용을 보존하고 다시 연결해 주세요.",
      );
      return false;
    }
  }
  const questions = data?.dataset.questions ?? [];
  const question = questions.find((q) => q.id === selected) ?? questions[0];
  const samples =
    data?.samples.filter(
      (s) => s.question_id === question?.id && s.origin === origin,
    ) ?? [];
  const sample = samples.find((s) => s.id === sampleId) ?? samples[0];
  const reviewed = questions.filter((q) => data?.reviews[q.fingerprint]).length;
  const position = questions.findIndex((q) => q.id === question?.id);
  const list = questions.filter(
    (q) => !onlyPending || !data?.reviews[q.fingerprint],
  );
  function choose(id: string) {
    setSelected(id);
    setSampleId("");
  }
  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <Link href="/showcase/regression#judge-workbench" prefetch={false}>
          ← 검사 대시보드
        </Link>
        <span>로컬 전용 · 사람 검토에는 모델 비용 없음</span>
      </header>
      <div className={styles.heading}>
        <h1>한 문항씩, 근거를 보고 검토하세요.</h1>
        <p>
          정답 기준을 확인하는 일과 AI 답변을 채점하는 일을 나눴습니다. 저장한
          판정은 기존 대시보드에도 반영됩니다.
        </p>
      </div>
      {!enabled ? (
        <p className={styles.notice}>
          사람 검토는 로컬 개발 환경에서 사용할 수 있습니다.
        </p>
      ) : (
        <>
          {error && (
            <div role="alert" className={styles.error}>
              {error} <button onClick={() => void refresh()}>다시 연결</button>
            </div>
          )}
          {!data && !error && (
            <p role="status">검토할 문항을 불러오고 있습니다.</p>
          )}
          {data && question && (
            <>
              <div className={styles.toolbar}>
                <div role="group" aria-label="검토 종류">
                  <button
                    aria-pressed={mode === "question"}
                    disabled={dirty}
                    onClick={() => setMode("question")}
                  >
                    문항·정답 기준 검토
                  </button>
                  <button
                    aria-pressed={mode === "sample"}
                    disabled={dirty}
                    onClick={() => setMode("sample")}
                  >
                    AI 답변 채점
                  </button>
                </div>
                <p>
                  정답 기준 검토{" "}
                  <strong>
                    {reviewed}/{questions.length}
                  </strong>{" "}
                  완료
                </p>
              </div>
              {dirty && (
                <p className={styles.notice} role="status">
                  작성 중인 검토가 있습니다. 저장하면 다른 문항으로 이동할 수
                  있습니다.{" "}
                  <button
                    type="button"
                    onClick={() => {
                      setDraftEpoch((x) => x + 1);
                      setDirty(false);
                    }}
                  >
                    작성 취소
                  </button>
                </p>
              )}
              <div className={styles.layout}>
                <aside className={styles.sidebar} aria-label="검토 문항 목록">
                  <label className={styles.filter}>
                    <input
                      type="checkbox"
                      checked={onlyPending}
                      onChange={(e) => setOnlyPending(e.target.checked)}
                    />
                    정답 기준 미검토만
                  </label>
                  <nav aria-label="문항 선택">
                    {list.map((q) => (
                      <button
                        key={q.id}
                        aria-current={q.id === question.id ? "step" : undefined}
                        disabled={dirty && q.id !== question.id}
                        onClick={() => choose(q.id)}
                      >
                        <span>
                          {q.id} ·{" "}
                          {data.reviews[q.fingerprint]
                            ? "기준 검토 완료"
                            : "기준 미검토"}
                        </span>
                        {q.query}
                      </button>
                    ))}
                  </nav>
                  {!list.length && (
                    <p>
                      모든 정답 기준을 검토했습니다. 필터를 해제하면 다시 볼 수
                      있습니다.
                    </p>
                  )}
                </aside>
                <article
                  className={styles.content}
                  aria-labelledby="question-title"
                >
                  <p className={styles.position}>
                    {position + 1} / {questions.length} 문항 ·{" "}
                    {question.answerable
                      ? "자료로 답할 수 있는 질문"
                      : "자료에 답이 없어 거절해야 하는 질문"}
                  </p>
                  <h2 id="question-title">{question.query}</h2>
                  <p className={styles.instruction}>
                    {mode === "question"
                      ? "아래의 기대한 사실이 원문과 맞는지 확인하고, 맨 아래에서 검토를 저장하세요."
                      : "기대한 사실·원문과 실제 답변을 대조한 뒤 네 항목을 직접 채점하세요."}
                  </p>
                  <section aria-label="정답 기준" className={styles.expected}>
                    <h3>기대한 사실</h3>
                    {question.expected_facts.length ? (
                      <ul>
                        {question.expected_facts.map((f) => (
                          <li key={f}>{f}</li>
                        ))}
                      </ul>
                    ) : (
                      <p>
                        자료에서 답을 확인할 수 없다고 설명해야 합니다. 추측으로
                        수치나 이름을 만들면 안 됩니다.
                      </p>
                    )}
                    <p>{question.allowed_expressions.join(" · ")}</p>
                  </section>
                  <section aria-label="정답 원문">
                    <h3>원문에서 확인하세요</h3>
                    {question.evidence.map((ref, i) => {
                      const doc = data.dataset.documents.find(
                        (d) => d.id === ref.doc_id,
                      )!;
                      return (
                        <details
                          key={`${question.id}:${ref.doc_id}`}
                          open={i === 0}
                          className={styles.source}
                        >
                          <summary>{doc.title}</summary>
                          <div className={styles.text}>
                            {Array.from(doc.text)
                              .slice(ref.start, ref.end)
                              .join("")}
                          </div>
                        </details>
                      );
                    })}
                  </section>
                  {mode === "question" ? (
                    <section className={styles.judgement}>
                      <h3>정답 기준이 원문과 일치하나요?</h3>
                      <p>
                        일치하지 않거나 질문이 모호하면 검토 완료를 체크하지
                        마세요. 수정이 필요한 내용을 확인한 뒤 진행해 주세요.
                      </p>
                      <div className={formStyles.body}>
                        <HumanForm
                          key={`${question.fingerprint}:${draftEpoch}`}
                          id={question.id}
                          target={question.fingerprint}
                          kind="question"
                          review={data.reviews[question.fingerprint]}
                          save={save}
                          onDirtyChange={setDirty}
                        />
                      </div>
                    </section>
                  ) : (
                    <>
                      <div
                        className={`${formStyles.body} ${styles.answerControls}`}
                      >
                        <label>
                          답변 출처
                          <select
                            value={origin}
                            disabled={dirty}
                            onChange={(e) => {
                              setOrigin(e.target.value);
                              setSampleId("");
                            }}
                          >
                            <option value="stored">
                              저장된 실제 모델 답변
                            </option>
                            <option value="synthetic">
                              검증용 합성 예시 · 모델 출력 아님
                            </option>
                          </select>
                        </label>
                        {samples.length > 0 && (
                          <label>
                            검토할 답변
                            <select
                              value={sample?.id ?? ""}
                              disabled={dirty}
                              onChange={(e) => setSampleId(e.target.value)}
                            >
                              {samples.map((s) => (
                                <option key={s.id} value={s.id}>
                                  {s.label} · {s.id}
                                </option>
                              ))}
                            </select>
                          </label>
                        )}
                      </div>
                      {!sample ? (
                        <p className={styles.notice}>
                          이 문항에는 해당 출처의 답변이 없습니다. 다른 문항을
                          고르거나 검증용 예시로 바꿀 수 있습니다.
                        </p>
                      ) : (
                        <>
                          <section aria-label="검토할 AI 답변">
                            <h3>
                              {sample.origin === "stored"
                                ? "실제 모델이 남긴 답변"
                                : "검증용 합성 예시 · 실제 모델 출력 아님"}
                            </h3>
                            <pre className={styles.text} tabIndex={0}>
                              {sample.answer}
                            </pre>
                          </section>
                          <section>
                            <h3>답변이 인용한 자료</h3>
                            {sample.supplied_evidence ? (
                              Object.entries(sample.supplied_evidence).map(
                                ([anchor, text]) => (
                                  <details
                                    key={`${sample.id}:${anchor}`}
                                    className={styles.source}
                                  >
                                    <summary>{anchor}</summary>
                                    <div className={styles.text}>{text}</div>
                                  </details>
                                ),
                              )
                            ) : (
                              <p className={styles.notice}>
                                생성 당시 인용 근거가 저장되지 않았습니다.
                                인용이 주장을 뒷받침하는지는 추측해서 판정하지
                                말고 ‘검토 필요’를 선택하세요.
                              </p>
                            )}
                          </section>
                          <section className={styles.judgement}>
                            <h3>이 답변을 직접 채점하세요</h3>
                            <dl className={styles.guide}>
                              <div>
                                <dt>사실 일치</dt>
                                <dd>기대한 사실과 대상·조건이 맞나요?</dd>
                              </div>
                              <div>
                                <dt>인용 정확도</dt>
                                <dd>
                                  인용한 자료가 답변의 주장을 뒷받침하나요?
                                </dd>
                              </div>
                              <div>
                                <dt>주요 주장 인용 충실도</dt>
                                <dd>근거가 필요한 주장에 출처가 붙었나요?</dd>
                              </div>
                              <div>
                                <dt>거절 적절성</dt>
                                <dd>
                                  자료에 없는 질문에 추측 없이 거절했나요? 답할
                                  수 있는 질문이면 ‘적용 안 됨’입니다.
                                </dd>
                              </div>
                            </dl>
                            <div className={formStyles.body}>
                              <AdditionalAiReview
                                review={data.ai_reviews?.[sample.fingerprint]}
                              />
                              <HumanForm
                                key={`${sample.fingerprint}:${draftEpoch}`}
                                id={sample.id}
                                target={sample.fingerprint}
                                kind="sample"
                                review={data.reviews[sample.fingerprint]}
                                save={save}
                                onDirtyChange={setDirty}
                              />
                            </div>
                          </section>
                        </>
                      )}
                    </>
                  )}
                  <footer className={styles.navigation}>
                    <button
                      disabled={dirty || position <= 0}
                      onClick={() => choose(questions[position - 1].id)}
                    >
                      이전 문항
                    </button>
                    <span>
                      {position + 1} / {questions.length}
                    </span>
                    <button
                      disabled={dirty || position >= questions.length - 1}
                      onClick={() => choose(questions[position + 1].id)}
                    >
                      다음 문항
                    </button>
                  </footer>
                </article>
              </div>
            </>
          )}
        </>
      )}
    </main>
  );
}
