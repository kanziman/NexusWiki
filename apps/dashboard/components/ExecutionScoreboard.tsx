"use client";

import { useState } from "react";
import committed from "@/content/evaluation-runs.json";
import styles from "./ExecutionScoreboard.module.css";

export type ExecutionRow = {
  id: string;
  query: string;
  kind: string;
  expected: { any: string[]; all: string[][] };
  response_text: string;
  status: string;
  passed: boolean;
  reason: string | null;
  keyword_hit: boolean | null;
  refused: boolean;
  cited_wiki: number | null;
  cited_source: number | null;
  fabricated: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  cost_micros: number | null;
  elapsed_ms: number | null;
  route: string | null;
};
export type ExecutionRun = {
  id: string;
  label: string;
  path: string;
  model: string;
  revision: string | null;
  answerable_asked: number;
  answerable_passed: number;
  refusal_asked: number;
  refusal_passed: number;
  cost_micros: number;
  total_tokens: number;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  rows: ExecutionRow[];
};
export type ExecutionRecords = {
  schema: string;
  synthetic: boolean;
  runs: ExecutionRun[];
};
const money = (value: number | null) =>
  value === null ? "기록 없음" : `$${(value / 1e6).toFixed(4)}`;
const seconds = (value: number | null) =>
  value === null ? "미측정" : `${(value / 1000).toFixed(2)}초`;
const count = (value: number | null) =>
  value === null ? "기록 없음" : `${value}개`;

function Check({
  label,
  result,
  detail,
}: {
  label: string;
  result: boolean | null;
  detail: string;
}) {
  return (
    <li data-result={result === null ? "unknown" : result ? "pass" : "fail"}>
      <span className={styles.checkStatus}>
        {result === null ? "미기록" : result ? "통과" : "실패"}
      </span>
      <b>{label}</b>
      <span>{detail}</span>
    </li>
  );
}

export function ExecutionScoreboard({
  records = committed as ExecutionRecords,
  available = true,
}: {
  records?: ExecutionRecords;
  available?: boolean;
}) {
  const [selected, setSelected] = useState(records.runs[0]?.id ?? "");
  const [filter, setFilter] = useState("failed");
  const run =
    records.runs.find((entry) => entry.id === selected) ?? records.runs[0];
  if (!available || !records.synthetic || !run)
    return (
      <p role="status">
        유효한 공개 합성 실행 기록이 없어 성적표를 표시하지 않습니다.
      </p>
    );
  const failed = run.rows.filter((row) => !row.passed);
  const rows = run.rows.filter(
    (row) =>
      filter === "all" ||
      (filter === "failed" ? !row.passed : row.kind === "refusal"),
  );
  return (
    <section className={styles.board} aria-labelledby="execution-title">
      <header className={styles.header}>
        <div>
          <h3 id="execution-title">실제 실행 성적표</h3>
          <p>실행을 선택하고, 문항을 펼쳐 판정과 답변을 직접 대조해 보세요.</p>
        </div>
        <span className={styles.badge}>
          저장된 합성 실행 · 추가 모델 호출 없음
        </span>
      </header>
      <div
        className={styles.scroll}
        tabIndex={0}
        role="region"
        aria-label="실행별 성적표 가로 스크롤"
      >
        <table className={styles.runs}>
          <caption>
            같은 문서·질문·모델의 반복 측정. 답할 수 있는 문항과 거절 문항은
            따로 셉니다.
          </caption>
          <thead>
            <tr>
              <th scope="col">실행 선택</th>
              <th scope="col">답변 통과</th>
              <th scope="col">정확한 거절</th>
              <th scope="col">전체 비용</th>
              <th scope="col">토큰</th>
              <th scope="col">지연 p50 / p95</th>
            </tr>
          </thead>
          <tbody>
            {records.runs.map((item) => (
              <tr key={item.id} data-selected={item.id === run.id}>
                <th scope="row">
                  <button
                    type="button"
                    aria-pressed={item.id === run.id}
                    onClick={() => {
                      setSelected(item.id);
                      setFilter("failed");
                    }}
                  >
                    {item.label}
                    <span>
                      {item.path === "http"
                        ? "HTTP · SSE 경유"
                        : "프로세스 내부 · HTTP 미경유"}
                    </span>
                  </button>
                </th>
                <td>
                  {item.answerable_passed}/{item.answerable_asked}
                </td>
                <td>
                  {item.refusal_passed}/{item.refusal_asked}
                </td>
                <td>{money(item.cost_micros)}</td>
                <td>{item.total_tokens.toLocaleString("ko-KR")}</td>
                <td>
                  {seconds(item.latency_p50_ms)} /{" "}
                  {seconds(item.latency_p95_ms)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className={styles.selection}>
        <h4>{run.label}의 문항 기록</h4>
        <span>
          {run.rows.length}문항 · {run.model}
        </span>
      </div>
      <div className={styles.filters} role="group" aria-label="실행 문항 필터">
        {[
          ["failed", `실패 ${failed.length}`],
          ["all", `전체 ${run.rows.length}`],
          ["refusal", `거절 ${run.refusal_asked}`],
        ].map(([value, label]) => (
          <button
            type="button"
            key={value}
            aria-pressed={filter === value}
            onClick={() => setFilter(value)}
          >
            {label}
          </button>
        ))}
      </div>
      <p className={styles.definition}>
        통과는 기대 표현·완료 상태·인용 조건을 코드로 확인한 결과입니다. 답변
        전체의 의미적 정확성을 보장하지 않습니다.
      </p>
      <div aria-live="polite" className={styles.resultCount}>
        {rows.length}문항 표시 · 다른 실행을 고르면 실패 문항부터 보여줍니다.
      </div>
      {rows.length === 0 ? (
        <p role="status" className={styles.empty}>
          이 필터에 해당하는 문항이 없습니다.
        </p>
      ) : (
        rows.map((row) => (
          <details key={`${run.id}-${row.id}`} className={styles.question}>
            <summary>
              <code>{row.id}</code>
              <span>{row.query}</span>
              <b data-passed={row.passed}>{row.passed ? "통과" : "실패"}</b>
            </summary>
            <div className={styles.questionBody}>
              <div className={styles.expectation}>
                <h5>기대 사실과 판정 방식</h5>
                {row.kind === "refusal" ? (
                  <p>
                    자료에 없는 질문이므로 거절해야 합니다. 고정 거절 문구 또는
                    근거 없음 상태와 위조 인용 여부로 판정합니다.
                  </p>
                ) : (
                  <>
                    <p>
                      {row.expected.any.length > 0 && (
                        <>
                          다음 표현 중 하나 포함:{" "}
                          <strong>{row.expected.any.join(" / ")}</strong>
                        </>
                      )}
                      {row.expected.all.length > 0 && (
                        <>
                          모든 표현 묶음에서 하나 이상 포함:{" "}
                          <strong>
                            {row.expected.all
                              .map((group) => `(${group.join(" / ")})`)
                              .join(" + ")}
                          </strong>
                        </>
                      )}
                    </p>
                    <p>표현의 공백 차이를 무시하는 키워드 판정입니다.</p>
                  </>
                )}
              </div>
              <h5>판정 근거를 한 줄씩</h5>
              <ol className={styles.checks}>
                {row.kind === "refusal" ? (
                  <Check
                    label="자료 없는 질문 거절"
                    result={row.refused}
                    detail={
                      row.refused
                        ? "표준 거절 문구 또는 근거 없음 상태 확인"
                        : "거절 조건 불충족"
                    }
                  />
                ) : (
                  <Check
                    label="정상 완료"
                    result={row.status === "resolved"}
                    detail={`저장된 상태: ${row.status}`}
                  />
                )}
                <Check
                  label="위조 인용 없음"
                  result={row.fabricated === null ? null : row.fabricated === 0}
                  detail={`검출 ${count(row.fabricated)}`}
                />
                {row.kind !== "refusal" && (
                  <>
                    <Check
                      label="기대 사실 포함"
                      result={row.keyword_hit}
                      detail={
                        row.keyword_hit === null
                          ? "판정 기록 없음"
                          : row.keyword_hit
                            ? "기대 표현 확인"
                            : "기대 표현을 찾지 못함"
                      }
                    />
                    <Check
                      label="원문·위키 양쪽 인용"
                      result={
                        row.cited_wiki === null || row.cited_source === null
                          ? null
                          : row.cited_wiki >= 1 && row.cited_source >= 1
                      }
                      detail={`위키 ${count(row.cited_wiki)} · 원문 ${count(row.cited_source)}`}
                    />
                  </>
                )}
              </ol>
              <p className={styles.verdict}>
                <b>최종 판정: {row.passed ? "통과" : "실패"}</b>{" "}
                {row.reason ?? "해당 문항의 통과 조건 충족"}
              </p>
              <h5>
                실제 모델 답변 <span>저장된 본문 그대로</span>
              </h5>
              <pre
                className={styles.response}
                tabIndex={0}
                aria-label={`${row.id} 실제 답변`}
              >
                {row.response_text}
              </pre>
              <p className={styles.definition}>
                [[wiki:w…]]·[[src:s…]]는 당시 답변의 근거 앵커 표기입니다. 원문
                본문과 앵커의 대응표는 이 공개 사본에 포함되지 않습니다.
              </p>
              <dl className={styles.metrics}>
                <div>
                  <dt>입력 / 출력 토큰</dt>
                  <dd>
                    {row.prompt_tokens ?? "미기록"} /{" "}
                    {row.completion_tokens ?? "미기록"}
                  </dd>
                </div>
                <div>
                  <dt>문항 비용</dt>
                  <dd>{money(row.cost_micros)}</dd>
                </div>
                <div>
                  <dt>전체 지연</dt>
                  <dd>{seconds(row.elapsed_ms)}</dd>
                </div>
                <div>
                  <dt>경로 결정</dt>
                  <dd>{row.route ?? "미기록 (하네스)"}</dd>
                </div>
              </dl>
            </div>
          </details>
        ))
      )}
      <footer className={styles.footer}>
        <p>
          질문별 처리 구간 시간과 서버 로그 원문은 이 기록에 없습니다. 단계
          타임라인이나 내부 추론으로 재구성하지 않았습니다. 같은 질문을 반복한
          결과이므로 회차는 독립 표본이 아닙니다.
        </p>
        <a href="/showcase/evaluation/runs.json" download>
          공개 실행 기록 JSON 다운로드 ↓
        </a>
      </footer>
    </section>
  );
}
