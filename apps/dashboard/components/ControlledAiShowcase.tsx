import Link from "next/link";

import styles from "./ControlledAiShowcase.module.css";

/**
 * 합성 증거로 통제 전후 동작을 보여주는 공개 화면 (#168).
 *
 * 설계 근거: openspec/changes/ai-control-flow-accounting/design.md > D10
 *
 * ⚠️ 증거 파일에 있는 값만 그린다. 합성 측정값이 운영 성과처럼 읽히지 않도록 개선율 같은 요약 수치를
 * 만들지 않고, 증거가 없는 Step에는 어떤 수치도 표시하지 않는다.
 */

type MetricUnit = "usd_micros" | "count" | "tokens" | "rate" | "text";
type MetricValue = string | number | null;

type EvidenceSide = {
  commit: string;
  // JSON import의 추론 타입은 항목마다 다른 키를 `undefined`로 채운다.
  values: Record<string, MetricValue | undefined>;
};

export type ControlledAiEvidence = {
  version: number;
  synthetic: boolean;
  generator: string;
  items: {
    id: string;
    title: string;
    problem: string;
    fix: string;
    scenario: string;
    metrics: { key: string; label: string; unit: string }[];
    before: EvidenceSide;
    after: EvidenceSide;
  }[];
  upcoming: { step: number; title: string; description: string }[];
};

const TEXT_LABELS: Record<string, string> = {
  not_finalized: "종결되지 않음",
  error: "오류로 종결",
  delta: "답변 조각에서 끊김",
  done: "정상 종료 신호",
};

function formatValue(value: MetricValue, unit: string): string {
  if (value === null) return "기록 없음";
  const kind = unit as MetricUnit;
  if (kind === "usd_micros")
    return `$${(Number(value) / 1_000_000).toFixed(4)}`;
  if (kind === "rate") return `${Math.round(Number(value) * 100)}%`;
  if (kind === "count") return `${value}건`;
  if (kind === "tokens") return `${Number(value).toLocaleString("ko-KR")}토큰`;
  return TEXT_LABELS[String(value)] ?? String(value);
}

function formatCommit(commit: string): string {
  return commit === "uncommitted" ? "커밋 전" : commit;
}

export function ControlledAiShowcase({
  evidence,
}: {
  evidence: ControlledAiEvidence;
}) {
  return (
    <main className={styles.page}>
      <header className={styles.header}>
        {/* ⚠️ 프리페치를 끈다. 켜 두면 홈 라우트의 미들웨어와 서버 렌더링이 돌아, 세션이 있는
            방문자에게서 이 페이지를 열기만 해도 인증 서버와 DB 요청이 발생한다. */}
        <Link href="/" prefetch={false} className={styles.home}>
          NexusWiki
        </Link>
        <p className={styles.eyebrow}>
          Controlled AI · Step 1–4 추적·비용 회계, 컨텍스트 예산, 출력 계약,
          리스크 정책
        </p>
        <h1>AI 호출을 통제하기 전과 후</h1>
        <p className={styles.lede}>
          같은 시나리오를 수정 전 코드와 수정 후 코드에서 각각 실행해 관측한
          값을 나란히 보여줍니다.
        </p>
      </header>

      <p>
        <Link href="/showcase/evidence-research" prefetch={false}>
          모델 도구 재검색 · 실제 OFF/ON 평가 보기 →
        </Link>
      </p>
      <p>
        <Link href="/showcase/evaluation" prefetch={false}>
          Ask 평가 지도 · 반복 측정 보기 →
        </Link>
      </p>

      <aside className={styles.notice} role="note">
        <strong>합성 데이터입니다.</strong> 모든 값은 자동화 테스트가 가짜
        공급자와 합성 입력으로 만들었습니다. 실제 고객 데이터나 운영 성과가
        아니며, 이 페이지는 데이터베이스와 API를 호출하지 않습니다.
      </aside>

      <section className={styles.items} aria-label="통제 전후 비교">
        {evidence.items.map((item) => (
          <article key={item.id} className={styles.item}>
            <h2>{item.title}</h2>
            <dl className={styles.story}>
              <div>
                <dt>문제</dt>
                <dd>{item.problem}</dd>
              </div>
              <div>
                <dt>통제</dt>
                <dd>{item.fix}</dd>
              </div>
            </dl>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">관측값</th>
                  <th scope="col">수정 전</th>
                  <th scope="col">수정 후</th>
                </tr>
              </thead>
              <tbody>
                {item.metrics.map((metric) => (
                  <tr key={metric.key}>
                    <th scope="row">{metric.label}</th>
                    <td
                      className={
                        metric.unit === "text" ? styles.textValue : undefined
                      }
                    >
                      {formatValue(
                        item.before.values[metric.key] ?? null,
                        metric.unit,
                      )}
                    </td>
                    <td
                      className={[
                        styles.after,
                        metric.unit === "text" ? styles.textValue : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                    >
                      {formatValue(
                        item.after.values[metric.key] ?? null,
                        metric.unit,
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <dl className={styles.provenance}>
              <div>
                <dt>시나리오</dt>
                <dd>
                  <code>{item.scenario}</code>
                </dd>
              </div>
              <div>
                <dt>수정 전 커밋</dt>
                <dd>
                  <code>{formatCommit(item.before.commit)}</code>
                </dd>
              </div>
              <div>
                <dt>수정 후 커밋</dt>
                <dd>
                  {item.after.commit === "uncommitted" ? (
                    formatCommit(item.after.commit)
                  ) : (
                    <code>{formatCommit(item.after.commit)}</code>
                  )}
                </dd>
              </div>
            </dl>
          </article>
        ))}
      </section>

      {evidence.upcoming.length > 0 ? (
        <section className={styles.upcoming} aria-labelledby="upcoming-heading">
          <h2 id="upcoming-heading">다음 단계</h2>
          <ul>
            {evidence.upcoming.map((step) => (
              <li key={step.step}>
                <span className={styles.stepLabel}>Step {step.step}</span>
                <strong>{step.title}</strong>
                <span className={styles.stepDescription}>
                  {step.description}
                </span>
                <span className={styles.pending}>준비 중</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <footer className={styles.footer}>
        증거 생성기: <code>{evidence.generator}</code>
      </footer>
    </main>
  );
}
