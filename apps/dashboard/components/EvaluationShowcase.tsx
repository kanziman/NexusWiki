import Link from "next/link";

import styles from "./EvaluationShowcase.module.css";

// 공개 기록 형식은 scripts/evaluation_showcase.py의 허용 목록(설계 D2)과 같다.
type Spread = {
  runs: number;
  paths: string[];
  answerable_passed: number[];
  min_rate: number;
  max_rate: number;
  mean_rate: number;
};
type Run = {
  label: string;
  path: "http" | "harness";
  planned: number;
  asked: number;
  answerable_passed: number;
  answerable_asked: number;
  interval_95: [number, number] | null;
  refusal_correct: number | null;
  refusal_asked: number;
  false_refusals: number;
  cost_usd: number;
};
type Outcome = "pass" | "fail" | "not_run";
type Question = {
  id: string;
  query: string;
  kind: "answerable" | "refusal";
  outcomes: Outcome[];
  stability: "stable_pass" | "stable_fail" | "unstable" | "not_run";
  known_failure: boolean;
  reported_stage: string | null;
  automatic_stage: string | null;
  note: string | null;
};
type Series = {
  valid: boolean;
  invalid_reason: string | null;
  key: {
    snapshot_sha256: string;
    fixture_sha256: string;
    prompt_sha256: string;
    model: string;
    policy_version: string;
    requested_k: number;
  } | null;
  runs: Run[];
  questions: Question[];
  spread: { all: Spread | null; http_only: Spread | null } | null;
  stability_counts: Record<
    "stable_pass" | "stable_fail" | "unstable" | "not_run",
    number
  > | null;
};
type MapEntry = {
  surface: string;
  status: "measured" | "partial" | "empty";
  derived_from: "series.answerable" | "series.refusal" | null;
  summary: string | null;
  detail: string | null;
  denominator: string | null;
  measured_at: string | null;
  source: string | null;
  source_url: string | null;
  reason: string | null;
};
type LedgerEntry = {
  date: string;
  changed: string;
  technique: string;
  applied: string;
  evidence: string;
  evidence_url: string | null;
};
export type EvaluationRecord = {
  schema: string;
  generated_at: string;
  provenance: Record<string, string>;
  synthetic: {
    documents: number;
    questions: number;
    answerable: number;
    unanswerable: number;
  };
  series: Series;
  map: MapEntry[];
  ledger: LedgerEntry[];
  limitations: string[];
};

// 화면 문구 사전(설계 D6). 기록 값은 내부 용어라 방문자에게 그대로 보이지 않는다.
const pathLabels: Record<Run["path"], string> = {
  http: "HTTP 요청",
  harness: "스크립트 재집계",
};
const outcomeLabels: Record<Outcome, string> = {
  pass: "통과",
  fail: "실패",
  not_run: "미실행",
};
const stabilityLabels: Record<Question["stability"], string> = {
  stable_pass: "모든 회차 통과",
  stable_fail: "모든 회차 실패",
  unstable: "회차마다 결과가 달라진 문항",
  not_run: "실행되지 않음",
};
const stageLabels: Record<string, string> = {
  retrieval_miss: "검색에서 정답 근거를 못 찾음",
  question_ambiguity: "질문이 두 가지로 읽힘",
  composition: "근거는 찾았지만 답 작성에서 틀림",
  execution_failure: "실행 장애",
  retrieval_evidence_unavailable: "검색 근거 기록이 없어 판정 못 함",
  grader_error: "채점기 오류",
  other: "기타",
  mixed: "회차마다 다름",
};
const stage = (value: string | null) =>
  value == null ? "없음" : (stageLabels[value] ?? value);
const statusLabels: Record<MapEntry["status"], string> = {
  measured: "잰 것",
  partial: "일부만",
  empty: "비어 있음",
};
const countWords = ["", "한", "두", "세", "네", "다섯"];
const times = (n: number) => `${countWords[n] ?? n} 번`;
const pct = (rate: number) => `${(rate * 100).toFixed(1)}%`;
// 스크린리더가 "82.8 대시 99.4"로 읽지 않도록 범위를 말로 쓴다.
const range = (interval: [number, number] | null) =>
  interval ? `${pct(interval[0])}에서 ${pct(interval[1])}` : "미측정";
const usd = (value: number) => `$${value.toFixed(4)}`;

function conclusion(series: Series): string {
  const runs = series.runs;
  const counts = series.stability_counts;
  const passed = runs.map((r) => r.answerable_passed);
  const asked = runs.map((r) => r.answerable_asked);
  const same =
    new Set(passed).size === 1 && new Set(asked).size === 1 && runs.length > 0;
  const head = same
    ? `${times(runs.length)} 모두 답할 수 있는 ${asked[0]}문항 중 ${passed[0]}개를 맞혔습니다.`
    : `${times(runs.length)} 돌려 답할 수 있는 문항 통과가 최소 ${Math.min(...passed)}개, 최대 ${Math.max(...passed)}개였습니다.`;
  if (!counts) return head;
  if (counts.unstable > 0)
    return `${head} 회차마다 결과가 달라진 문항이 ${counts.unstable}개 있습니다.`;
  if (counts.stable_fail > 0) {
    const ids = series.questions
      .filter((q) => q.stability === "stable_fail")
      .map((q) => q.id);
    return `${head} 틀린 ${counts.stable_fail}문항(${ids.join(", ")})은 매번 같은 문항이었습니다.`;
  }
  return head;
}

function minMax(spread: Spread, denominators: number[]) {
  const passed = spread.answerable_passed;
  const lo = Math.min(...passed);
  const hi = Math.max(...passed);
  const denominator = new Set(denominators).size === 1 ? denominators[0] : null;
  const frac = (n: number) => (denominator ? `${n}/${denominator}` : `${n}`);
  return `최소 ${frac(lo)} (${pct(spread.min_rate)}), 최대 ${frac(hi)} (${pct(spread.max_rate)})`;
}

function refusalCell(run: Run) {
  if (run.refusal_asked === 0) return "없음 · 이 회차엔 거절 문항 없음";
  return `${run.refusal_correct ?? 0}/${run.refusal_asked} (거절 문항 ${run.refusal_asked}개)`;
}

// 반복 측정에서 나오는 지도 칸은 공개 기록의 회차 수치에서만 만든다(설계 D5).
// 큐레이션 문장으로 두면 묶음이 무효여도 28/29가 남는다.
function derivedSummary(
  kind: NonNullable<MapEntry["derived_from"]>,
  series: Series,
): string {
  const runs = series.runs;
  const n = runs.length;
  if (kind === "series.answerable") {
    const passed = runs.map((r) => r.answerable_passed);
    const asked = runs.map((r) => r.answerable_asked);
    const unstable = series.stability_counts?.unstable ?? 0;
    const tail = ` · 회차마다 결과가 달라진 문항 ${unstable}개`;
    if (new Set(passed).size === 1 && new Set(asked).size === 1)
      return `${times(n)} 모두 ${passed[0]}/${asked[0]}${tail}`;
    return `${n}회 통과 최소 ${Math.min(...passed)}개, 최대 ${Math.max(...passed)}개${tail}`;
  }
  const cells = runs.map((r) => refusalCell(r));
  const falses = runs.map((r) => `${r.false_refusals}/${r.answerable_asked}`);
  if (new Set(cells).size === 1 && new Set(falses).size === 1)
    return `${times(n)} 모두 정확한 거절 ${cells[0]} · 잘못된 거절 ${falses[0]}`;
  return `회차마다 다름 (${n}회)`;
}

function MapValue({ entry, series }: { entry: MapEntry; series: Series }) {
  if (entry.derived_from) {
    if (!series.valid)
      return (
        <>
          <strong>무효:</strong> {series.invalid_reason ?? "이유 미기록"}
        </>
      );
    return (
      <>
        {derivedSummary(entry.derived_from, series)}
        <a className={styles.mapLink} href="#repetition">
          반복 측정 보기
        </a>
      </>
    );
  }
  if (entry.status === "empty") return <>{entry.reason}</>;
  return (
    <>
      {entry.summary}
      {entry.denominator && (
        <span className={styles.denominator}> (분모: {entry.denominator})</span>
      )}
      {entry.detail && (
        <details className={styles.mapDetail}>
          <summary>자세히</summary>
          <p>{entry.detail}</p>
        </details>
      )}
    </>
  );
}

function Source({
  entry,
  embedded = false,
}: {
  entry: MapEntry;
  embedded?: boolean;
}) {
  if (!entry.source) return <>—</>;
  if (!entry.source_url) return <>{entry.source}</>;
  return (
    <a
      href={entry.source_url}
      rel="noopener noreferrer"
      target={embedded ? undefined : "_blank"}
    >
      {entry.source}
    </a>
  );
}

// 미실행 칸이 하나라도 있으면 "모든 회차 통과"여도 펼친다. 접힌 곳에 숨기면 미실행이 안 보인다.
const isException = (q: Question) =>
  q.stability !== "stable_pass" || q.outcomes.includes("not_run");

function OutcomeCell({ outcome }: { outcome: Outcome }) {
  return (
    <td data-outcome={outcome}>
      {/* 미실행은 실패와 다른 기호를 쓴다. 기호는 읽지 않고 글자만 읽힌다. */}
      <span aria-hidden="true" className={styles.mark}>
        {outcome === "pass" ? "○" : outcome === "fail" ? "×" : "—"}
      </span>{" "}
      {outcomeLabels[outcome]}
    </td>
  );
}

function QuestionTable({
  caption,
  questions,
  runs,
  colLabel,
  explain,
}: {
  caption: string;
  questions: Question[];
  runs: Run[];
  colLabel: (run: Run) => string;
  explain: boolean;
}) {
  return (
    <div
      className={styles.tableWrap}
      tabIndex={0}
      role="region"
      aria-label={caption}
    >
      <table className={styles.grid}>
        <caption>{caption}</caption>
        <thead>
          <tr>
            <th scope="col">문항</th>
            {runs.map((run) => (
              <th key={run.label} scope="col">
                {colLabel(run)}
              </th>
            ))}
            <th scope="col">안정성</th>
          </tr>
        </thead>
        <tbody>
          {questions.map((q) => (
            <QuestionRows
              key={q.id}
              question={q}
              span={runs.length + 2}
              explain={explain}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function QuestionRows({
  question: q,
  span,
  explain,
}: {
  question: Question;
  span: number;
  explain: boolean;
}) {
  const failed = q.outcomes.includes("fail");
  return (
    <>
      <tr>
        <th scope="row">
          <span className={styles.qid}>{q.id}</span> {q.query}
          {q.kind === "refusal" && (
            <span className={styles.kind}> · 거절 문항</span>
          )}
        </th>
        {q.outcomes.map((outcome, index) => (
          <OutcomeCell key={index} outcome={outcome} />
        ))}
        <td>{stabilityLabels[q.stability]}</td>
      </tr>
      {explain && (failed || q.note) && (
        <tr className={styles.explain}>
          <td colSpan={span}>
            {q.known_failure && <strong>알려진 실패. </strong>}
            {failed && (
              <>
                보고 단계: {stage(q.reported_stage)} · 자동 판정이 찾은 처음
                틀어진 단계: {stage(q.automatic_stage)}
              </>
            )}
            {q.note && <span className={styles.qnote}>메모: {q.note}</span>}
          </td>
        </tr>
      )}
    </>
  );
}

function Invalid({ reason }: { reason: string | null }) {
  return (
    <p className={styles.invalid}>
      <strong>무효:</strong> {reason ?? "이유가 기록되지 않았습니다."} 이 묶음의
      통과 수 · 범위 · 안정성은 보여주지 않습니다.
    </p>
  );
}

const sections = [
  { id: "repetition", title: "반복 측정" },
  { id: "refusal", title: "거절 성능" },
  { id: "map", title: "평가 지도" },
  { id: "ledger", title: "적용 원장" },
  { id: "conditions", title: "재현 조건과 한계" },
];

export function EvaluationShowcase({
  record,
  embedded = false,
}: {
  record: EvaluationRecord;
  embedded?: boolean;
}) {
  const Container = embedded ? "div" : "main";
  const { series, synthetic } = record;
  const valid = series.valid;
  const runs = valid ? series.runs : [];
  const http = runs.filter((r) => r.path === "http");
  const spread = valid ? series.spread : null;
  const counts = valid ? series.stability_counts : null;
  const refusalSample = Math.max(0, ...runs.map((r) => r.refusal_asked));
  const totalCost = runs.reduce((sum, r) => sum + r.cost_usd, 0);
  // 공개 회차 이름은 export가 경로에서 만든다("HTTP 1" · "스크립트 재집계 #232"). 경로를 덧붙이면
  // 같은 말이 두 번 나온다. 이름에 경로가 없으면 그때만 덧붙인다.
  const colLabel = (run: Run) =>
    run.label.startsWith(pathLabels[run.path].split(" ")[0])
      ? run.label
      : `${run.label} · ${pathLabels[run.path]}`;
  const questions = valid ? series.questions : [];
  const exceptions = questions.filter(isException);
  const steady = questions.filter((q) => !isException(q));

  return (
    <Container className={styles.page}>
      <nav hidden={embedded} className={styles.nav} aria-label="관련 페이지">
        {/* ⚠️ 프리페치를 끈다. 켜 두면 홈 라우트의 미들웨어가 돌아 세션이 있는 방문자에게서
            인증 서버와 DB 요청이 생긴다. */}
        <Link href="/" prefetch={false}>
          NexusWiki
        </Link>
        <span className={styles.navLinks}>
          <Link href="/showcase/controlled-ai" prefetch={false}>
            AI 통제 실험
          </Link>
          <Link href="/showcase/evidence-research" prefetch={false}>
            재검색 실험
          </Link>
        </span>
      </nav>

      <header hidden={embedded} className={styles.header}>
        <h1>Ask 답변 품질을 무엇으로, 어디까지 쟀나</h1>
        <p className={styles.conclusion}>
          {valid
            ? conclusion(series)
            : "반복 측정 결과를 보여줄 수 없습니다. 기록이 무효입니다."}
        </p>
      </header>
      <aside className={styles.notice} role="note">
        <strong>합성 평가입니다.</strong> 가상 회사 문서 {synthetic.documents}
        개와 고정 질문 {synthetic.questions}개(답할 수 있는{" "}
        {synthetic.answerable}개 · 거절해야 하는 {synthetic.unanswerable}개)로
        쟀습니다.{" "}
        {valid &&
          `같은 질문을 ${times(runs.length)} 반복한 결과라 안정성을 보장하지 않습니다. `}
        운영 성과가 아닙니다.
      </aside>
      <nav
        hidden={embedded}
        className={styles.toc}
        aria-label="이 페이지의 구역"
      >
        {sections.map((s) => (
          <a key={s.id} href={`#${s.id}`}>
            {s.title}
          </a>
        ))}
      </nav>

      <section
        id="repetition"
        className={styles.section}
        aria-labelledby="repetition-title"
      >
        <h2 id="repetition-title">반복 측정</h2>
        {!valid ? (
          <Invalid reason={series.invalid_reason} />
        ) : (
          <>
            <div
              className={styles.tableWrap}
              tabIndex={0}
              role="region"
              aria-label="회차별 결과 표"
            >
              <table>
                <caption>
                  회차별 결과. 95% 범위는 이 표본 크기에서 실제 통과율이 있을
                  법한 범위입니다.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">지표</th>
                    {runs.map((run) => (
                      <th key={run.label} scope="col">
                        {colLabel(run)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <th scope="row">실행한 문항</th>
                    {runs.map((run) => (
                      <td key={run.label}>
                        {run.asked}/{run.planned}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <th scope="row">답할 수 있는 문항 통과</th>
                    {runs.map((run) => (
                      <td key={run.label}>
                        {run.answerable_passed}/{run.answerable_asked}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <th scope="row">95% 범위</th>
                    {runs.map((run) => (
                      <td key={run.label}>{range(run.interval_95)}</td>
                    ))}
                  </tr>
                  <tr>
                    <th scope="row">회차 비용 (전체 문항)</th>
                    {runs.map((run) => (
                      <td key={run.label}>{usd(run.cost_usd)}</td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
            <ul className={styles.spread}>
              {spread?.all && (
                <li>
                  전체 {spread.all.runs}회 사이:{" "}
                  {minMax(
                    spread.all,
                    runs.map((r) => r.answerable_asked),
                  )}
                </li>
              )}
              {spread?.http_only && (
                <li>
                  HTTP 요청 회차만 {spread.http_only.runs}회:{" "}
                  {minMax(
                    spread.http_only,
                    http.map((r) => r.answerable_asked),
                  )}
                </li>
              )}
            </ul>
            <p className={styles.note}>
              회차를 합친 범위는 내지 않습니다. 같은 질문을 반복한 회차는 독립
              표본이 아니기 때문입니다.
            </p>
            <h3 className={styles.subhead}>문항별 결과</h3>
            {exceptions.length === 0 ? (
              <p>모든 문항이 모든 회차에서 통과했습니다.</p>
            ) : (
              <QuestionTable
                caption="통과가 아닌 결과가 있는 문항"
                questions={exceptions}
                runs={runs}
                colLabel={colLabel}
                explain
              />
            )}
            {steady.length > 0 && (
              <details className={styles.steady}>
                <summary>
                  결과가 {times(runs.length)} 모두 통과인 {steady.length}문항
                  보기
                </summary>
                <QuestionTable
                  caption="모든 회차에서 통과한 문항"
                  questions={steady}
                  runs={runs}
                  colLabel={colLabel}
                  explain={false}
                />
              </details>
            )}
          </>
        )}
      </section>

      <section
        id="refusal"
        className={styles.section}
        aria-labelledby="refusal-title"
      >
        <h2 id="refusal-title">거절 성능</h2>
        {!valid ? (
          <Invalid reason={series.invalid_reason} />
        ) : (
          <>
            <p>
              근거가 없는 질문을 거절했는지와, 답할 수 있는 질문을 잘못
              거절했는지를 통과 수와 따로 셉니다.
            </p>
            <div
              className={styles.tableWrap}
              tabIndex={0}
              role="region"
              aria-label="회차별 거절 표"
            >
              <table>
                <caption>회차별 거절 결과</caption>
                <thead>
                  <tr>
                    <th scope="col">지표</th>
                    {runs.map((run) => (
                      <th key={run.label} scope="col">
                        {colLabel(run)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <th scope="row">답할 수 있는 문항 통과</th>
                    {runs.map((run) => (
                      <td key={run.label}>
                        {run.answerable_passed}/{run.answerable_asked}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <th scope="row">정확한 거절</th>
                    {runs.map((run) => (
                      <td key={run.label}>{refusalCell(run)}</td>
                    ))}
                  </tr>
                  <tr>
                    <th scope="row">잘못된 거절 (답할 수 있는 문항 중)</th>
                    {runs.map((run) => (
                      <td key={run.label}>
                        {run.false_refusals}/{run.answerable_asked}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      <section id="map" className={styles.section} aria-labelledby="map-title">
        <h2 id="map-title">평가 지도</h2>
        <p>
          무엇을 쟀고 무엇이 아직 비어 있는지를 측정면마다 보입니다. 비어 있는
          칸도 숨기지 않습니다.
        </p>
        <div
          className={styles.tableWrap}
          tabIndex={0}
          role="region"
          aria-label="측정면별 상태 표"
        >
          <table className={styles.map}>
            <caption>측정면별 상태 · 지금 값 · 측정일 · 출처</caption>
            <thead>
              <tr>
                <th scope="col">측정면</th>
                <th scope="col">상태</th>
                <th scope="col">지금 값</th>
                <th scope="col">측정일</th>
                <th scope="col">출처</th>
              </tr>
            </thead>
            <tbody>
              {record.map.map((entry) => (
                <tr key={entry.surface} data-status={entry.status}>
                  <th scope="row">{entry.surface}</th>
                  <td data-label="상태">{statusLabels[entry.status]}</td>
                  <td data-label="지금 값">
                    {/* 좁은 화면의 2열 격자에서 값 · 분모 · 상세가 한 칸에 머물도록 감싼다. */}
                    <div>
                      <MapValue entry={entry} series={series} />
                    </div>
                  </td>
                  <td data-label="측정일">{entry.measured_at ?? "—"}</td>
                  <td data-label="출처">
                    <Source entry={entry} embedded={embedded} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section
        id="ledger"
        className={styles.section}
        aria-labelledby="ledger-title"
      >
        <h2 id="ledger-title">적용 원장</h2>
        <p>
          평가 기법을 실제로 적용한 기록입니다. 측정이 무언가를 바꾼 적용만
          남깁니다.
        </p>
        <ol className={styles.ledger}>
          {record.ledger.map((entry, index) => (
            <li key={`${entry.date}-${index}`}>
              <h3>
                <time dateTime={entry.date}>{entry.date}</time>
              </h3>
              <p className={styles.changed}>{entry.changed}</p>
              <dl>
                <div>
                  <dt>적용한 기법</dt>
                  <dd>{entry.technique}</dd>
                </div>
                <div>
                  <dt>한 일</dt>
                  <dd>{entry.applied}</dd>
                </div>
                <div>
                  <dt>증거</dt>
                  <dd>
                    {entry.evidence_url ? (
                      <a
                        href={entry.evidence_url}
                        rel="noopener noreferrer"
                        target={embedded ? undefined : "_blank"}
                      >
                        {entry.evidence}
                      </a>
                    ) : (
                      entry.evidence
                    )}
                  </dd>
                </div>
              </dl>
            </li>
          ))}
        </ol>
      </section>

      <section
        id="conditions"
        className={styles.section}
        aria-labelledby="conditions-title"
      >
        <h2 id="conditions-title">재현 조건과 한계</h2>
        <ul className={styles.limits}>
          {valid && (
            <>
              <li>
                회차는 {runs.length}번이고, 같은 질문을 반복한 것이라 독립
                표본이 아닙니다.
              </li>
              {counts && counts.unstable === 0 && (
                <li>
                  회차마다 결과가 달라진 문항이 0개라는 것은 이 {runs.length}번
                  안에서 흔들림이 보이지 않았다는 뜻일 뿐, 안정성을 보장하지
                  않습니다.
                </li>
              )}
              <li>
                거절해야 하는 문항은 회차마다 {refusalSample}개뿐이라 거절
                성능은 예시 수준입니다.
              </li>
            </>
          )}
          {record.limitations.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
        {valid && series.key && (
          <dl className={styles.conditions}>
            <div>
              <dt>답변 모델</dt>
              <dd>{series.key.model}</dd>
            </div>
            <div>
              <dt>검색 정책</dt>
              <dd>{series.key.policy_version}</dd>
            </div>
            <div>
              <dt>근거 수 (k)</dt>
              <dd>{series.key.requested_k}</dd>
            </div>
            <div>
              <dt>측정 비용</dt>
              <dd>
                {usd(totalCost)} ({runs.length}회 합계, 회차마다 질문{" "}
                {synthetic.questions}개 전체)
              </dd>
            </div>
          </dl>
        )}
        <details>
          <summary>고정 입력 지문과 기록 출처</summary>
          <dl className={styles.conditions}>
            {valid && series.key && (
              <>
                <div>
                  <dt>수집 스냅샷</dt>
                  <dd>
                    <code>{series.key.snapshot_sha256}</code>
                  </dd>
                </div>
                <div>
                  <dt>질문 fixture</dt>
                  <dd>
                    <code>{series.key.fixture_sha256}</code>
                  </dd>
                </div>
                <div>
                  <dt>답변 프롬프트</dt>
                  <dd>
                    <code>{series.key.prompt_sha256}</code>
                  </dd>
                </div>
              </>
            )}
            {Object.entries(record.provenance).map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd>
                  <code>{value}</code>
                </dd>
              </div>
            ))}
          </dl>
        </details>
        <p className={styles.footerLinks}>
          <a href="/showcase/evaluation/results.json" download>
            평가 기록 JSON 다운로드 ↓
          </a>
          <Link
            href={embedded ? "#control" : "/showcase/controlled-ai"}
            prefetch={false}
          >
            AI 통제 전후 보기 →
          </Link>
          <Link
            href={embedded ? "#research" : "/showcase/evidence-research"}
            prefetch={false}
          >
            재검색 OFF/ON 평가 보기 →
          </Link>
        </p>
      </section>
    </Container>
  );
}
