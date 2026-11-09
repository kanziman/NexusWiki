import Link from "next/link";

import {
  ControlledAiShowcase,
  type ControlledAiEvidence,
} from "./ControlledAiShowcase";
import {
  EvaluationShowcase,
  type EvaluationRecord,
} from "./EvaluationShowcase";
import {
  EvidenceResearchShowcase,
  type ResearchEvaluation,
} from "./EvidenceResearchShowcase";
import styles from "./AiEngineeringShowcase.module.css";
import { ExecutionScoreboard } from "./ExecutionScoreboard";

/** 공개 합성 기록 세 종류를 한 읽기 흐름으로 연결한다. 운영 클라이언트는 사용하지 않는다. */
export function AiEngineeringShowcase({
  record,
  controlled,
  research,
}: {
  record: EvaluationRecord;
  controlled: ControlledAiEvidence;
  research: ResearchEvaluation;
}) {
  const off = research.summary.off;
  const on = research.summary.on;
  const comparable =
    research.valid && research.checks.conditions_match && Boolean(off && on);
  const costChange =
    comparable && off && on && off.cost_micros > 0
      ? Math.round((on.cost_micros / off.cost_micros - 1) * 100)
      : null;
  const selected = [
    "compile-retry-cost",
    "ask-fabricated-citation",
    "verified-page-overwrite",
  ];
  const money = (micros: number) => `$${(micros / 1e6).toFixed(2)}`;
  const seconds = (ms: number | null) =>
    ms === null ? "미측정" : `${(ms / 1000).toFixed(1)}초`;
  return (
    <main className={styles.page}>
      <nav className={styles.nav} aria-label="사례 탐색">
        <Link href="/" prefetch={false} className={styles.brand}>
          NexusWiki<span> / AI ENGINEERING</span>
        </Link>
        <a href="#evaluate">평가</a>
        <a href="#control">통제</a>
        <a href="#research">도입 판단</a>
      </nav>

      <header className={styles.hero}>
        <p className={styles.eyebrow}>NEXUSWIKI · 검증과 의사결정 기록</p>
        <h1>
          AI의 답을 넘어,
          <br />
          <span>그 답을 믿을 기준까지.</span>
        </h1>
        <p className={styles.lede}>
          답변을 측정하고, 실패를 코드로 통제하고,
          <br className={styles.desktopBreak} /> 실험 결과로 기능의 도입 여부를
          결정했습니다.
        </p>
        <p className={styles.context}>
          원문과 위키를 함께 인용하는 팀 지식 도구, NexusWiki를 만들며 남긴 세
          가지 사례입니다.
        </p>
      </header>

      <ol className={styles.overview} aria-label="세 가지 엔지니어링 판단">
        <li>
          <a href="#evaluate">
            <span className={styles.index}>01 / 평가한다</span>
            <h2>
              채점 결과도
              <br /> 다시 검증했습니다.
            </h2>
            <p>
              올바른 거절을 오답으로 처리한
              <br /> 채점기를 수정했습니다.
            </p>
            <strong>
              채점 정정 ≠ 성능 개선 <span aria-hidden="true">↘</span>
            </strong>
          </a>
        </li>
        <li>
          <a href="#control">
            <span className={styles.index}>02 / 통제한다</span>
            <h2>
              실패를 예상하고,
              <br /> 코드로 경계를 뒀습니다.
            </h2>
            <p>
              비용 누락, 위조 인용,
              <br /> 승인 없는 문서 변경을 통제했습니다.
            </p>
            <strong>
              수정 전후를 같은 시나리오로 검증 <span aria-hidden="true">↘</span>
            </strong>
          </a>
        </li>
        <li>
          <a href="#research">
            <span className={styles.index}>03 / 도입을 판단한다</span>
            <h2>
              만든 기능도,
              <br /> 근거가 부족하면 보류합니다.
            </h2>
            <p>
              재검색을 구현하고 비교했지만
              <br /> 기본 설정은 OFF로 유지했습니다.
            </p>
            <strong>
              품질·비용을 함께 보고 결정 <span aria-hidden="true">↘</span>
            </strong>
          </a>
        </li>
      </ol>
      <aside className={styles.scope} role="note">
        <strong>증거의 범위를 먼저 밝힙니다.</strong> 평가는 가상 물류 회사 문서
        8개로 실제 모델을 호출한 기록입니다. 통제 사례는 가짜 공급자를 사용한
        자동화 테스트입니다. 서로 다른 검증이며, 운영 성과를 뜻하지 않습니다.
      </aside>

      <section
        id="evaluate"
        className={styles.case}
        aria-labelledby="evaluate-title"
      >
        <div className={styles.sectionHead}>
          <span className={styles.index}>01 / 평가 체계</span>
          <span className={styles.evidenceType}>
            합성 문서 · 실제 모델 호출
          </span>
        </div>
        <h2 id="evaluate-title">
          좋은 점수를 얻는 것보다,
          <br />
          점수가 무엇을 뜻하는지 확인했습니다.
        </h2>
        <p className={styles.intro}>
          질문별 기대 사실과 인용 기준을 정하고, 실패한 답을 직접 확인했습니다.
          답변의 문제와 채점기의 문제를 구분해야 다음 수정도 정확해집니다.
        </p>
        <ol className={styles.process} aria-label="평가 과정">
          <li>
            <b>기준 설정</b>
            <span>기대 사실·인용·거절</span>
          </li>
          <li>
            <b>실행·기록</b>
            <span>질문별 결과와 비용</span>
          </li>
          <li>
            <b>실패 분석</b>
            <span>검색·답변·채점 분리</span>
          </li>
          <li>
            <b>수정·재검증</b>
            <span>같은 입력으로 비교</span>
          </li>
        </ol>
        <div className={styles.storyGrid}>
          <article className={styles.finding}>
            <span className={styles.label}>발견 / 채점기의 거짓 실패</span>
            <h3>실제로는 올바른 거절이었습니다.</h3>
            <p>
              q30의 실제 답을 열어 보니 정확한 거절이었습니다. 고정 거절 문구에
              맞춰 채점기를 수정한 뒤, 같은 결과 파일을 다시 채점했습니다.
            </p>
            <div className={styles.bigChange}>
              <span>27/30</span>
              <span aria-label="에서">→</span>
              <strong>28/30</strong>
            </div>
            <p className={styles.caption}>
              2026.11.08 · 같은 답변의 재채점. 모델 성능 향상이 아닙니다.
            </p>
          </article>
          <article className={styles.finding}>
            <span className={styles.label}>결정 / 개선과 회귀를 함께 보고</span>
            <h3>검색 점수의 중복 합산을 고쳤습니다.</h3>
            <p>
              같은 채널의 검색 점수가 반복 합산되는지 확인하고, 최고 순위 한
              번만 반영하는 방식과 비교했습니다.
            </p>
            <div className={styles.bigChange}>
              <span>23/29</span>
              <span aria-label="에서">→</span>
              <strong>28/29</strong>
            </div>
            <p className={styles.caption}>
              RRF 전후 실험 · 공통 답변 29문항. q06 회귀를 공개하고
              채택했습니다.
            </p>
          </article>
        </div>
        <p className={styles.takeaway}>
          <span>배운 것</span>평가 도구도 검증 대상입니다. 점수 변화가 채점
          정정인지, 시스템 개선인지 구분해 기록합니다.
        </p>
        <div className={styles.current}>
          <h3>현재 관측과 남은 한계</h3>
          <p>
            {record.series.valid
              ? `${record.series.runs.length}회 모두 답할 수 있는 29문항 중 28문항 통과. q06은 매번 실패했습니다.`
              : "반복 측정 기록이 무효여서 현재 성적을 표시하지 않습니다."}{" "}
            통과는 키워드로 기대 사실을 확인한 판정이며, 답변 전체 의미의
            정확성을 보장하지 않습니다.
          </p>
          <p>
            거절 문항은 회차마다 1개뿐입니다. 같은 질문의 반복은 독립 표본이
            아니며 안정성 보장이 아닙니다. 이중 인용은 2026.11.03 재생에서
            24/30턴으로, 현재 반복 측정과 다른 기록입니다.
          </p>
        </div>
        <ExecutionScoreboard available={record.series.valid} />
        <p className={styles.caption}>
          <Link href="/showcase/regression#reliability" prefetch={false}>
            반복 측정의 질문별 결과 살펴보기
          </Link>
        </p>
        <details className={styles.details}>
          <summary>
            평가 상세 펼치기{" "}
            <span>회차별 결과 · 실패 문항 · 평가 지도 · 적용 원장</span>
          </summary>
          <EvaluationShowcase record={record} embedded />
        </details>
      </section>

      <section
        id="control"
        className={styles.case}
        aria-labelledby="control-title"
      >
        <div className={styles.sectionHead}>
          <span className={styles.index}>02 / 실패 통제</span>
          <span className={styles.evidenceType}>
            합성 시나리오 · 가짜 공급자 테스트
          </span>
        </div>
        <h2 id="control-title">
          프롬프트의 약속을,
          <br />
          코드의 경계로 바꿨습니다.
        </h2>
        <p className={styles.intro}>
          모델이 항상 올바르게 응답한다고 가정하지 않았습니다. 잘못된 출력과
          재시도, 위험한 쓰기를 같은 시나리오의 수정 전후 코드에서 확인했습니다.
        </p>
        <div className={styles.controls}>
          {selected.map((id, index) => {
            const item = controlled.items.find((entry) => entry.id === id);
            if (!item) return null;
            const metric =
              index === 0
                ? "recorded_cost_micros"
                : index === 1
                  ? "dual_citation_rate"
                  : "verified_body";
            const format = (value: string | number | null | undefined) =>
              value == null
                ? "기록 없음"
                : index === 0
                  ? `$${(Number(value) / 1e6).toFixed(4)}`
                  : index === 1
                    ? `${Number(value) * 100}%`
                    : String(value);
            return (
              <article key={id}>
                <span className={styles.label}>
                  {
                    [
                      "비용 / 실패한 시도까지 기록",
                      "출력 / 인용의 실재 여부 확인",
                      "권한 / 사람의 검증을 보존",
                    ][index]
                  }
                </span>
                <h3>{item.title}</h3>
                <p>{item.problem}</p>
                <div className={styles.controlCompare}>
                  <div>
                    <span>수정 전</span>
                    <b>{format(item.before.values[metric])}</b>
                  </div>
                  <span aria-hidden="true">→</span>
                  <div>
                    <span>수정 후</span>
                    <b>{format(item.after.values[metric])}</b>
                  </div>
                </div>
                <p className={styles.caption}>
                  {index === 0
                    ? "공급자 보고 비용 $0.0020 중 회계에 남은 금액"
                    : index === 1
                      ? "위조 앵커만 있는 문장의 이중 인용률. 낮아진 값이 올바른 판정입니다."
                      : "검증된 본문 상태. 수정 후 변경은 승인 대기 제안으로 남습니다."}
                </p>
                <p className={styles.fix}>{item.fix}</p>
                <details className={styles.scenario}>
                  <summary>검증 시나리오 펼치기</summary>
                  <p>
                    가짜 공급자와 합성 입력으로 수정 전후 코드를 실행한
                    관측값입니다. 운영 성능 측정이 아닙니다.
                  </p>
                  <dl>
                    <div>
                      <dt>상황</dt>
                      <dd>{item.problem}</dd>
                    </div>
                    <div>
                      <dt>확인한 동작</dt>
                      <dd>{item.fix}</dd>
                    </div>
                    <div>
                      <dt>시나리오</dt>
                      <dd>
                        <code>{item.scenario}</code>
                      </dd>
                    </div>
                    <div>
                      <dt>수정 전 / 후 코드</dt>
                      <dd>
                        <code>
                          {item.before.commit} → {item.after.commit}
                        </code>
                      </dd>
                    </div>
                  </dl>
                  <table>
                    <caption>시나리오의 저장된 관측값</caption>
                    <thead>
                      <tr>
                        <th scope="col">항목</th>
                        <th scope="col">수정 전</th>
                        <th scope="col">수정 후</th>
                      </tr>
                    </thead>
                    <tbody>
                      {item.metrics.map((m) => {
                        const display = (
                          v: string | number | null | undefined,
                        ) =>
                          v == null
                            ? "미기록"
                            : m.unit === "usd_micros"
                              ? `$${(Number(v) / 1e6).toFixed(4)}`
                              : m.unit === "rate"
                                ? `${Number(v) * 100}%`
                                : String(v);
                        return (
                          <tr key={m.key}>
                            <th scope="row">{m.label}</th>
                            <td>{display(item.before.values[m.key])}</td>
                            <td>{display(item.after.values[m.key])}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                  <p>
                    생성기: <code>{controlled.generator}</code>
                  </p>
                </details>
              </article>
            );
          })}
        </div>
        <p className={styles.takeaway}>
          <span>설계 원칙</span>비용은 응답 검증 전에 기록하고, 인용은 실제
          근거와 대조하고, 검증된 문서 변경에는 승인을 요구합니다.
        </p>
        <details className={styles.details}>
          <summary>
            통제 사례 전체 펼치기{" "}
            <span>
              {controlled.items.length}개 시나리오 · 관측값 · 수정 전후 커밋
            </span>
          </summary>
          <ControlledAiShowcase evidence={controlled} embedded />
        </details>
      </section>

      <section
        id="research"
        className={styles.case}
        aria-labelledby="research-title"
      >
        <div className={styles.sectionHead}>
          <span className={styles.index}>03 / 도입 판단</span>
          <span className={styles.evidenceType}>
            합성 42문항 · 실제 모델 OFF/ON 1쌍
          </span>
        </div>
        <h2 id="research-title">
          한 번 더 검색하면,
          <br />그 비용만큼 좋아질까요?
        </h2>
        <p className={styles.intro}>
          모델이 근거를 확인하고 최대 두 번 재검색하는 기능을 구현했습니다. 같은
          문서·모델·검색 정책에서 OFF/ON을 비교하고, 품질과 비용 기준으로
          판단했습니다.
        </p>
        {comparable && off && on ? (
          <>
            <table
              className={styles.experiment}
              aria-label="재검색 OFF ON 핵심 비교"
            >
              <caption>
                합성 {off.questions}문항 · OFF/ON 각 1회 · 전체 호출 비용
              </caption>
              <thead>
                <tr className={styles.experimentHeading}>
                  <th scope="col">관측 지표</th>
                  <th scope="col">기존 검색 OFF</th>
                  <th scope="col">재검색 ON</th>
                </tr>
              </thead>
              <tbody>
                {[
                  [
                    "전체 문항 통과",
                    `${off.passed}/${off.questions}`,
                    `${on.passed}/${on.questions}`,
                  ],
                  [
                    "평가 전체 비용",
                    money(off.cost_micros),
                    money(on.cost_micros),
                  ],
                  [
                    "응답 지연 중앙값",
                    seconds(off.latency_p50),
                    seconds(on.latency_p50),
                  ],
                ].map(([label, before, after]) => (
                  <tr className={styles.experimentRow} key={label}>
                    <th scope="row">{label}</th>
                    <td>
                      <b>{before}</b>
                    </td>
                    <td>
                      <b>{after}</b>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className={styles.decision}>
              <span className={styles.label}>
                결정 / {research.adopted ? "실험 기준 통과" : "기본 OFF 유지"}
              </span>
              <h3>
                {research.adopted
                  ? "채택 기준을 통과했습니다."
                  : "이번 평가에서는 도입 근거가 부족했습니다."}
              </h3>
              <p>
                {research.adopted
                  ? "공개 기록의 채택 기준을 통과했습니다. 기본 설정 변경은 별도 결정으로 남깁니다."
                  : `전체 통과 ${off.passed}/${off.questions} → ${on.passed}/${on.questions}, 비용 변화 ${costChange === null ? "미측정" : `${costChange > 0 ? "+" : ""}${costChange}%`}. 개선 효과와 비용 기준을 함께 보고 기본 설정을 OFF로 유지했습니다.`}
              </p>
            </div>
          </>
        ) : (
          <p className={styles.current}>
            유효하고 조건이 일치하는 비교 기록이 없어 도입 판단을 보류합니다.
          </p>
        )}
        <div className={styles.caveat}>
          <h3>이 실험이 말하지 못하는 것</h3>
          <p>
            첫 검색에서 기대 문서가 빠진 복구 대상은{" "}
            {research.recovery.eligible}개였습니다. 따라서 복구 효과를 입증하지
            못했습니다. 한 쌍의 관측으로 재검색이 항상 효과 없다고 결론 내리지
            않습니다.
          </p>
          <p>
            <strong>다음 검증:</strong> 첫 검색에서 근거가 실제로 빠지는 질문을
            확보하고, 같은 조건에서 반복 비교해야 합니다.
          </p>
        </div>
        <p className={styles.caption}>
          <Link href="/showcase/regression#research" prefetch={false}>
            재검색 실험의 질문별 결과 살펴보기
          </Link>
        </p>
        <details className={styles.details}>
          <summary>
            재검색 실험 상세 펼치기{" "}
            <span>채택 기준 · 문항별 OFF/ON · 비용·지연 · 재현 조건</span>
          </summary>
          <p className={styles.caption}>
            처음에는 판정이 바뀐 문항부터 표시합니다. 전체 통과 수가 같더라도
            개별 문항의 개선과 회귀는 다를 수 있습니다.
          </p>
          <EvidenceResearchShowcase evaluation={research} embedded />
        </details>
      </section>
      <footer className={styles.footer}>
        <p className={styles.eyebrow}>측정 → 분석 → 통제 → 결정</p>
        <h2>
          결과가 설계와 결정을
          <br />
          바꾸도록 만들었습니다.
        </h2>
        <p>
          잘된 결과와 함께 실패, 비용, 평가의 한계도 남깁니다.
          <br />각 사례의 상세 근거는 이 페이지 안에서 펼쳐 확인할 수 있습니다.
        </p>
        <a href="#evaluate">평가 과정 다시 보기 ↑</a>
      </footer>
    </main>
  );
}
