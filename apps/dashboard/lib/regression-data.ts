import execution from "@/content/evaluation-runs.json";
import evaluation from "@/content/evaluation.json";
import research from "@/content/evidence-research.json";
import type { AnalysisSuite } from "./regression-analysis";

/** 공개된 합성 기록만 읽는다. 서로 다른 평가 세트는 비교 후보로 섞지 않는다. */
export const regressionSuites: AnalysisSuite[] = [
  {
    id: "research",
    name: "재검색 OFF / ON",
    guide: {
      short: "재검색의 효과와 비용",
      question: "한 번 더 검색하면 답변이 좋아질까요?",
      data: "가상 물류 회사 문서 8개와 질문 42개입니다. 기존 질문 30개에 여러 문서를 비교하는 질문 6개, 원문과 표현이 다른 질문 6개를 더했습니다.",
      method:
        "같은 문서·모델·검색 정책에서 재검색을 끈 상태(OFF)와 켠 상태(ON)를 각각 한 번 실행했습니다. 답변의 통과 여부와 비용·지연을 비교합니다.",
      interpretation:
        "전체 통과 수가 같아도 개별 질문은 좋아지거나 나빠질 수 있습니다. 회귀 문항과 추가 비용을 함께 확인하세요. 복구 대상이 0개여서 놓친 근거를 되찾는 효과는 입증하지 못했습니다.",
    },
    description:
      "동일 문서·모델·검색 정책에서 재검색 기능의 품질과 추가 비용 비교",
    limitation:
      "합성 42문항 · OFF/ON 1쌍. 복구 대상 0개로 복구 효과는 미측정입니다. 공개 기록에는 답변 본문이 없습니다.",
    runs: (["off", "on"] as const)
      .filter(() => research.valid && research.conditions_match)
      .map((mode) => {
        const summary = research.summary[mode];
        return {
          id: mode,
          label: mode === "off" ? "OFF · 기존 검색" : "ON · 모델 재검색",
          path: "HTTP",
          model: research.conditions.model,
          revision:
            research.runs.find((run) => run.mode === mode)?.revision ?? null,
          conditions: research.conditions,
          cost: summary.cost_micros,
          tokens: summary.prompt_tokens + summary.completion_tokens,
          p50: summary.latency_p50,
          p95: summary.latency_p95,
          rows: research.rows.map((row) => ({
            id: row.id,
            query: row.query,
            passed: mode === "off" ? row.before_pass : row.after_pass,
            reason: mode === "off" ? row.before_reason : row.after_reason,
            cost: mode === "off" ? row.before_cost : row.after_cost,
            latency: mode === "off" ? row.before_ms : row.after_ms,
            answer: null,
            failed: row.measurement_failed,
            kind: row.type,
          })),
        };
      }),
  },
  {
    id: "reliability",
    name: "Ask 반복 측정",
    guide: {
      short: "같은 질문의 반복 결과",
      question: "같은 질문에 다시 답해도 결과가 유지될까요?",
      data: "가상 물류 회사 문서 8개와 고정 질문 30개입니다. 답할 수 있는 질문 29개, 자료가 없어 거절해야 하는 질문 1개로 구성했습니다.",
      method:
        "같은 조건으로 실행한 HTTP 요청 2회와 프로세스 내부 실행 1회의 보존 기록입니다. 실행 두 개를 골라 같은 질문이 계속 통과하거나 실패했는지 확인합니다.",
      interpretation:
        "여기서는 새로운 답변을 만들지 않고 당시 기록을 비교합니다. 몇 번 결과가 같았다고 안정성을 보장하지 않습니다. 프로세스 내부 실행은 HTTP 통신을 거치지 않아 지연을 해석할 때 주의해야 합니다.",
    },
    description: "같은 질문을 HTTP 2회와 프로세스 내부 1회 실행한 기록 비교",
    limitation:
      "합성 30문항 · 같은 질문의 반복은 독립 표본이 아닙니다. HTTP와 하네스는 실행 경로가 다르며 안정성을 보장하지 않습니다.",
    runs: execution.runs
      .filter(() => evaluation.series.valid)
      .map((run) => ({
        id: run.id,
        label: run.label,
        path: run.path === "http" ? "HTTP · SSE" : "프로세스 내부",
        model: run.model,
        revision: run.revision,
        conditions: Object.fromEntries(
          Object.entries(evaluation.series.key).map(([key, value]) => [
            key,
            String(value),
          ]),
        ),
        cost: run.cost_micros,
        tokens: run.total_tokens,
        p50: run.latency_p50_ms,
        p95: run.latency_p95_ms,
        rows: run.rows.map((row) => ({
          id: row.id,
          query: row.query,
          passed: row.passed,
          reason: row.reason,
          cost: row.cost_micros,
          latency: row.elapsed_ms,
          answer: row.response_text,
          failed: ["error", "not-run"].includes(row.status),
          kind: row.kind,
          expected:
            row.kind === "refusal"
              ? "자료에 없는 질문에 대한 거절"
              : row.expected.any.join(" / "),
        })),
      })),
  },
];
