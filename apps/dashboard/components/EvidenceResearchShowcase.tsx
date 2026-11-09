"use client";

import Link from "next/link";
import { useState } from "react";

import styles from "./EvidenceResearchShowcase.module.css";

type Side = {
  questions: number;
  passed: number;
  regression_passed: number;
  cost_micros: number;
  prompt_tokens: number;
  completion_tokens: number;
  fabricated: number;
  latency_p50: number | null;
  latency_p95: number | null;
  first_token_p50: number | null;
  first_token_p95: number | null;
};
type Row = {
  id: string;
  pair: number;
  query: string;
  type: string;
  before_pass: boolean;
  after_pass: boolean;
  before_reason: string | null;
  after_reason: string | null;
  eligible: boolean;
  evidence_recovered: boolean;
  answer_recovered: boolean;
  measurement_failed: boolean;
  initial_all_found: boolean | null;
  final_all_found: boolean | null;
  before_ms: number | null;
  after_ms: number | null;
  before_cost: number | null;
  after_cost: number | null;
  tool_calls: number;
  research_status: string;
};
export type ResearchEvaluation = {
  version: number;
  synthetic: boolean;
  valid: boolean;
  adopted: boolean;
  conditions: Record<string, string | null>;
  checks: Record<string, boolean>;
  runs: {
    mode: string;
    pair: number;
    revision: string;
    created_at: string;
    source_state?: string;
  }[];
  summary: { off?: Side; on?: Side };
  rows: Row[];
  measurement_failures: number;
  recovery: {
    eligible: number;
    evidence: number;
    answer: number;
    rate: number | null;
  };
  method: string;
};

const usd = (value: number | null | undefined) =>
  value == null ? "미측정" : `$${(value / 1e6).toFixed(4)}`;
const seconds = (value: number | null | undefined) =>
  value == null ? "미측정" : `${(value / 1000).toFixed(1)}초`;
const found = (value: boolean | null) =>
  value == null ? "미측정" : value ? "전체 확보" : "일부 누락";
const researchLabels: Record<string, string> = {
  sufficient: "모델이 근거가 충분하다고 판단",
  searched: "추가 검색 완료",
  no_initial_evidence: "초기 근거 없음",
  timeout: "추가 단계 시간 초과",
  off: "재검색 OFF",
  decision_or_search_failed: "판단 또는 검색 실패",
  search_failed: "검색 실패",
};
const checkLabels: Record<string, string> = {
  conditions_match: "비교 조건 일치",
  measurements_complete: "측정 장애 없음",
  answer_recovered: "답변 복구 1건 이상",
  total_pass_improved: "전체 통과 증가",
  no_regression: "기존 문항 통과 감소 없음",
  no_fabrication_increase: "위조 인용 증가 없음",
  cost_within_limit: "평균 비용 증가 50% 이하",
  latency_within_limit: "p95 지연 증가 15초 이하",
};

export function EvidenceResearchShowcase({
  evaluation: data,
  embedded = false,
}: {
  evaluation: ResearchEvaluation;
  embedded?: boolean;
}) {
  const Container = embedded ? "div" : "main";
  // 쌍 수와 분모는 기록에서 센다. 고정값을 쓰면 실행 계획이 바뀔 때 화면이 거짓 분모를 보인다.
  const pairs = [
    ...new Set(
      (data.rows.length ? data.rows : data.runs).map((item) => item.pair),
    ),
  ].sort((a, b) => a - b);
  if (pairs.length === 0) pairs.push(1);
  const regressionTotal = data.rows.filter(
    (row) => row.type === "regression",
  ).length;
  const perPair = Math.round(data.rows.length / pairs.length);
  const [filter, setFilter] = useState(embedded ? "changed" : "all");
  const [pair, setPair] = useState(String(pairs[0]));
  const rows = data.rows.filter(
    (row) =>
      String(row.pair) === pair &&
      (filter === "all" ||
        (filter === "changed" &&
          !row.measurement_failed &&
          row.before_pass !== row.after_pass) ||
        (filter === "recovered" && row.answer_recovered) ||
        (filter === "regressed" &&
          !row.measurement_failed &&
          row.before_pass &&
          !row.after_pass) ||
        (filter === "research" && row.type !== "regression") ||
        (filter === "failed" && row.measurement_failed)),
  );
  const { off, on } = data.summary;
  const metrics: [string, string, string][] =
    off && on
      ? [
          [
            "답변 통과",
            `${off.passed} / ${off.questions}`,
            `${on.passed} / ${on.questions}`,
          ],
          [
            pairs.length > 1
              ? `기존 문항 통과 · ${pairs.length}쌍 합계`
              : "기존 문항 통과",
            `${off.regression_passed} / ${regressionTotal}`,
            `${on.regression_passed} / ${regressionTotal}`,
          ],
          [
            "문항당 평균 비용 · 모든 호출",
            usd(off.cost_micros / off.questions),
            usd(on.cost_micros / on.questions),
          ],
          [
            "전체 입력 토큰",
            off.prompt_tokens.toLocaleString("ko-KR"),
            on.prompt_tokens.toLocaleString("ko-KR"),
          ],
          [
            "전체 출력 토큰",
            off.completion_tokens.toLocaleString("ko-KR"),
            on.completion_tokens.toLocaleString("ko-KR"),
          ],
          [
            "총 지연 p50 / p95",
            `${seconds(off.latency_p50)} / ${seconds(off.latency_p95)}`,
            `${seconds(on.latency_p50)} / ${seconds(on.latency_p95)}`,
          ],
          [
            "첫 답변 토큰 p50 / p95",
            `${seconds(off.first_token_p50)} / ${seconds(off.first_token_p95)}`,
            `${seconds(on.first_token_p50)} / ${seconds(on.first_token_p95)}`,
          ],
          ["위조 인용", String(off.fabricated), String(on.fabricated)],
        ]
      : [];

  return (
    <Container className={styles.page}>
      <nav hidden={embedded} className={styles.nav} aria-label="관련 페이지">
        <Link href="/" prefetch={false}>
          NexusWiki
        </Link>
        <span className={styles.navLinks}>
          <Link href="/showcase/controlled-ai" prefetch={false}>
            AI 통제 실험 보기 ↗
          </Link>
          <Link href="/showcase/evaluation" prefetch={false}>
            평가 지도 · 반복 측정 보기 ↗
          </Link>
        </span>
      </nav>
      <header hidden={embedded} className={styles.header}>
        <p className={styles.kicker}>검색 품질 실험 · 실제 모델 호출</p>
        <h1>
          한 번 더 찾으면,
          <br />
          답도 더 좋아질까?
        </h1>
        <p>
          첫 검색에서 빠진 대상을 모델이 찾아내고, 최대 두 번 재검색합니다. 같은
          문서·모델·RRF 정책에서 품질과 추가 비용을 함께 비교했습니다.
        </p>
      </header>
      <aside className={styles.notice} role="note">
        <strong>합성 평가입니다.</strong> 가상의 물류 회사 문서 8개와 42문항을
        사용했습니다. 비용 절감을 위해 OFF/ON 한 쌍만 비교했으며 반복 안정성은
        미측정입니다. 운영 성과나 통계적 우월성을 뜻하지 않습니다.
      </aside>

      <section className={styles.section} aria-labelledby="result-title">
        <h2 id="result-title">
          {!data.valid
            ? data.measurement_failures > 0
              ? "측정 장애로 비교를 보류했습니다"
              : "아직 유효한 비교가 없습니다"
            : data.adopted
              ? "실험 기준 통과 · 기본 설정은 OFF"
              : "채택 기준 미달 · 기본 설정 OFF 유지"}
        </h2>
        {!data.valid ? (
          <p>
            미측정·조건 불일치 또는 측정 장애가 있습니다. 개선 수치를 표시하지
            않습니다.
            {data.measurement_failures > 0 &&
              ` 측정 장애 ${data.measurement_failures}문항·실행은 복구 성공으로 집계하지 않습니다. 실패한 호출의 짧은 지연과 0원 비용은 개선이 아닙니다.`}
          </p>
        ) : (
          <>
            <p className={styles.result}>
              초기 근거가 부족했던 전용 문항{" "}
              <strong>{data.recovery.eligible}회</strong> 중 근거 복구{" "}
              <strong>{data.recovery.evidence}회</strong>, 답변까지 복구{" "}
              <strong>{data.recovery.answer}회</strong>.
              {data.recovery.rate == null
                ? " 복구율은 미측정입니다."
                : ` 답변 복구율 ${(data.recovery.rate * 100).toFixed(1)}%.`}
            </p>
            <div className={styles.tableWrap}>
              <table>
                <caption>
                  OFF / ON · {perPair}문항
                  {pairs.length > 1 ? `씩 ${pairs.length}쌍` : " 1쌍"}, 전체
                  호출 포함
                </caption>
                <thead>
                  <tr>
                    <th scope="col">지표</th>
                    <th scope="col">OFF · 기존 검색</th>
                    <th scope="col">ON · 모델 재검색</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.map(([label, before, after]) => (
                    <tr key={label}>
                      <th scope="row">{label}</th>
                      <td>{before}</td>
                      <td>{after}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        <ul className={styles.checks}>
          {Object.entries(data.checks)
            .filter(
              ([key]) =>
                data.valid ||
                ["conditions_match", "measurements_complete"].includes(key),
            )
            .map(([key, pass]) => (
              <li key={key}>
                <span aria-hidden="true">{pass ? "✓" : "—"}</span>{" "}
                {checkLabels[key] ?? key}:{" "}
                <strong>{pass ? "충족" : "미충족"}</strong>
              </li>
            ))}
        </ul>
      </section>

      <section className={styles.section} aria-labelledby="questions-title">
        <h2 id="questions-title">어떤 질문이 달라졌나</h2>
        <div className={styles.filters}>
          <label>
            실행 쌍{" "}
            <select
              value={pair}
              onChange={(event) => setPair(event.target.value)}
            >
              {pairs.map((n) => (
                <option key={n} value={n}>
                  {n}차
                </option>
              ))}
            </select>
          </label>
          <label>
            문항 보기{" "}
            <select
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            >
              <option value="all">전체 문항</option>
              <option value="changed">판정이 바뀐 문항</option>
              <option value="research">재검색 전용 12문항</option>
              <option value="recovered">답변 복구</option>
              <option value="regressed">통과 → 실패</option>
              <option value="failed">측정 장애</option>
            </select>
          </label>
          <span role="status">{rows.length}문항</span>
        </div>
        {rows.length === 0 ? (
          <p className={styles.empty}>이 조건에 해당하는 문항이 없습니다.</p>
        ) : (
          <div className={styles.questions}>
            {rows.map((row) => (
              <details key={`${row.pair}-${row.id}`}>
                <summary>
                  <span className={styles.id}>{row.id}</span>
                  <span>{row.query}</span>
                  <span className={styles.verdict}>
                    {row.measurement_failed ? (
                      "측정 장애 · 비교 제외"
                    ) : (
                      <>
                        {row.before_pass ? "통과" : "실패"} →{" "}
                        {row.after_pass ? "통과" : "실패"}
                      </>
                    )}
                    {data.valid && row.answer_recovered ? " · 복구" : ""}
                  </span>
                </summary>
                <div className={styles.detail}>
                  <dl>
                    <div>
                      <dt>첫 문맥 → 최종 문맥</dt>
                      <dd>
                        {found(row.initial_all_found)} →{" "}
                        {found(row.final_all_found)}
                      </dd>
                    </div>
                    <div>
                      <dt>추가 검색</dt>
                      <dd>
                        {row.tool_calls}회 ·{" "}
                        {researchLabels[row.research_status] ?? "미측정"}
                      </dd>
                    </div>
                    <div>
                      <dt>OFF / ON 지연</dt>
                      <dd>
                        {seconds(row.before_ms)} / {seconds(row.after_ms)}
                      </dd>
                    </div>
                    <div>
                      <dt>OFF / ON 비용</dt>
                      <dd>
                        {usd(row.before_cost)} / {usd(row.after_cost)}
                      </dd>
                    </div>
                  </dl>
                  <p>
                    OFF: {row.before_reason ?? "통과"}
                    <br />
                    ON: {row.after_reason ?? "통과"}
                  </p>
                  {row.measurement_failed && (
                    <p>측정 장애가 있어 복구 성공으로 집계하지 않았습니다.</p>
                  )}
                </div>
              </details>
            ))}
          </div>
        )}
      </section>

      <section className={styles.section}>
        <h2>재현 조건과 해석 범위</h2>
        <p>{data.method}</p>
        <p>
          정답 판정은 고정된 필수 표현과 원문·위키 인용을 사용합니다. 표현이
          달라 오판할 수 있으며, 같은 원문으로 만든 위키를 찾았다는 사실이 정답
          문장 확보를 보장하지는 않습니다.
        </p>
        <details>
          <summary>고정 조건 해시와 실행 기록</summary>
          <dl className={styles.conditions}>
            {Object.entries(data.conditions).map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd>
                  <code>{value ?? "미기록"}</code>
                </dd>
              </div>
            ))}
          </dl>
          <ul>
            {data.runs.map((run) => (
              <li key={`${run.pair}-${run.mode}`}>
                {run.pair}차 {run.mode.toUpperCase()} ·{" "}
                {run.source_state ?? "코드 상태 미기록"} ·{" "}
                <code>{run.revision.slice(0, 12)}</code> · {run.created_at}
              </li>
            ))}
          </ul>
        </details>
        <a
          className={styles.download}
          href="/showcase/evidence-research/results.json"
          download
        >
          평가 기록 JSON 다운로드 ↓
        </a>
      </section>
    </Container>
  );
}
