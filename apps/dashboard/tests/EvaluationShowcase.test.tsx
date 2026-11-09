import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { GET } from "@/app/showcase/evaluation/results.json/route";
import {
  ControlledAiShowcase,
  type ControlledAiEvidence,
} from "@/components/ControlledAiShowcase";
import {
  EvaluationShowcase,
  type EvaluationRecord,
} from "@/components/EvaluationShowcase";
import {
  EvidenceResearchShowcase,
  type ResearchEvaluation,
} from "@/components/EvidenceResearchShowcase";
import controlled from "@/content/controlled-ai/step1.json";
import committed from "@/content/evaluation.json";
import research from "@/content/evidence-research.json";

const record = committed as unknown as EvaluationRecord;
const clone = (): EvaluationRecord => structuredClone(record);

describe("평가 공개 페이지 · 반복 측정 요약", () => {
  it("결론 문장을 회차 수치에서 조립하고 합성 샘플임을 먼저 알린다", () => {
    render(<EvaluationShowcase record={record} />);
    expect(
      screen.getByText(
        "세 번 모두 답할 수 있는 29문항 중 28개를 맞혔습니다. 틀린 1문항(q06)은 매번 같은 문항이었습니다.",
      ),
    ).toBeInTheDocument();
    const notice = screen.getByRole("note");
    expect(notice).toHaveTextContent("합성 평가입니다");
    expect(notice).toHaveTextContent("문서 8개");
    expect(notice).toHaveTextContent("질문 30개");
    expect(notice).toHaveTextContent("안정성을 보장하지 않습니다");
  });

  it("회차 요약표가 경로 · 실행 수 · 통과 · 범위 · 비용을 회차마다 보인다", () => {
    render(<EvaluationShowcase record={record} />);
    const table = screen.getByRole("table", { name: /회차별 결과/ });
    expect(
      within(table).getByRole("columnheader", { name: "HTTP 1" }),
    ).toBeInTheDocument();
    expect(
      within(table).getByRole("columnheader", {
        name: "스크립트 재집계 #232",
      }),
    ).toBeInTheDocument();
    expect(within(table).getAllByText("30/30")).toHaveLength(3);
    expect(within(table).getAllByText("28/29")).toHaveLength(3);
    expect(within(table).getAllByText("82.8%에서 99.4%")).toHaveLength(3);
    expect(within(table).getByText("$0.7603")).toBeInTheDocument();
    expect(
      screen.getByText(/HTTP 요청 회차만 2회: 최소 28\/29/),
    ).toBeInTheDocument();
    expect(screen.getByText(/전체 3회 사이: 최소 28\/29/)).toBeInTheDocument();
    expect(
      screen.getByText(/회차를 합친 범위는 내지 않습니다/),
    ).toBeInTheDocument();
  });

  it("거절 성능을 통과 수와 따로, 표본 수와 함께 보인다", () => {
    render(<EvaluationShowcase record={record} />);
    const table = screen.getByRole("table", { name: "회차별 거절 결과" });
    // 통과 · 정확한 거절 · 잘못된 거절 세 수치를 같은 구역에서 각각 분모와 함께 보인다.
    expect(within(table).getAllByText("28/29")).toHaveLength(3);
    expect(within(table).getAllByText("1/1 (거절 문항 1개)")).toHaveLength(3);
    expect(within(table).getAllByText("0/29")).toHaveLength(3);
    expect(
      screen.getByText(/거절해야 하는 문항은 회차마다 1개뿐/),
    ).toBeInTheDocument();
  });

  it("거절 문항이 없는 회차의 정확한 거절은 0이 아니라 없음이다", () => {
    const variant = clone();
    variant.series.runs[0] = {
      ...variant.series.runs[0],
      refusal_asked: 0,
      refusal_correct: null,
    };
    render(<EvaluationShowcase record={variant} />);
    const table = screen.getByRole("table", { name: "회차별 거절 결과" });
    expect(
      within(table).getByText("없음 · 이 회차엔 거절 문항 없음"),
    ).toBeInTheDocument();
    expect(within(table).queryByText(/^0\/0/)).not.toBeInTheDocument();
  });

  it("무효 묶음이면 결론 · 요약표 · 거절에 수치를 보이지 않는다", () => {
    const variant = clone();
    variant.series = {
      valid: false,
      invalid_reason: "묶음 키 값이 없다: model",
      key: null,
      runs: [],
      questions: [],
      spread: null,
      stability_counts: null,
    };
    render(<EvaluationShowcase record={variant} />);
    expect(
      screen.queryByRole("table", { name: /회차별/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("table", { name: /통과가 아닌 결과/ }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/맞혔습니다/)).not.toBeInTheDocument();
    expect(screen.getByText(/기록이 무효입니다/)).toBeInTheDocument();
    // 반복 측정 · 거절 구역과 지도의 파생 칸 두 개가 모두 무효를 말한다.
    expect(screen.getAllByText(/묶음 키 값이 없다: model/)).toHaveLength(4);
    const map = screen.getByRole("table", { name: /측정면별 상태/ });
    for (const surface of ["최종 답 정답성", "거절"]) {
      const row = within(map)
        .getByRole("rowheader", { name: surface })
        .closest("tr")!;
      expect(row).toHaveTextContent("무효");
      expect(row).not.toHaveTextContent(/\d+\/\d+/);
    }
  });

  it("격자는 예외부터 펼치고 q06의 보고 단계와 자동 단계를 함께 보인다", () => {
    render(<EvaluationShowcase record={record} />);
    const table = screen.getByRole("table", {
      name: "통과가 아닌 결과가 있는 문항",
    });
    const rows = within(table).getAllByRole("rowheader");
    expect(rows).toHaveLength(1);
    expect(rows[0]).toHaveTextContent("q06");
    const q06 = rows[0].closest("tr")!;
    expect(within(q06).getAllByText("실패")).toHaveLength(3);
    expect(within(q06).getByText("모든 회차 실패")).toBeInTheDocument();
    expect(table).toHaveTextContent("알려진 실패");
    expect(table).toHaveTextContent("보고 단계: 질문이 두 가지로 읽힘");
    expect(table).toHaveTextContent(
      "자동 판정이 찾은 처음 틀어진 단계: 검색에서 정답 근거를 못 찾음",
    );
    expect(
      within(table).getByRole("columnheader", { name: "HTTP 2" }),
    ).toBeInTheDocument();
  });

  it("모든 회차 통과 문항은 접힌 곳에 있고 q30은 거절 문항으로 표시된다", () => {
    const { container } = render(<EvaluationShowcase record={record} />);
    const details = container.querySelector("details")!;
    expect(details.open).toBe(false);
    expect(details.querySelector("summary")).toHaveTextContent(
      "결과가 세 번 모두 통과인 29문항 보기",
    );
    const steady = within(details).getByRole("table", {
      name: "모든 회차에서 통과한 문항",
    });
    expect(within(steady).getAllByRole("rowheader")).toHaveLength(29);
    const q30 = within(steady).getByText("q30").closest("th")!;
    expect(q30).toHaveTextContent("거절 문항");
  });

  it("멈춘 회차의 미실행 칸은 실패로 세지 않고 펼친 표에 보인다", () => {
    const variant = clone();
    const q01 = variant.series.questions.find((q) => q.id === "q01")!;
    q01.outcomes = ["pass", "pass", "not_run"];
    variant.series.runs[2] = {
      ...variant.series.runs[2],
      asked: 29,
      answerable_asked: 28,
      answerable_passed: 27,
    };
    render(<EvaluationShowcase record={variant} />);
    const table = screen.getByRole("table", {
      name: "통과가 아닌 결과가 있는 문항",
    });
    const row = within(table).getByText("q01").closest("tr")!;
    expect(within(row).getByText("미실행")).toBeInTheDocument();
    expect(within(row).queryAllByText("실패", { exact: true })).toHaveLength(0);
    expect(within(row).getByText("모든 회차 통과")).toBeInTheDocument();
  });

  it("질문 문구의 스크립트를 실행하지 않고 글자로 보인다", () => {
    const variant = clone();
    variant.series.questions[5].query = "<script>window.bad=1</script>";
    const { container } = render(<EvaluationShowcase record={variant} />);
    expect(
      screen.getByText(/<script>window.bad=1<\/script>/),
    ).toBeInTheDocument();
    expect(container.querySelector("script")).toBeNull();
  });

  it("평가 지도는 10개 측정면을 상태 · 값 · 분모 · 측정일 · 출처와 함께 보인다", () => {
    render(<EvaluationShowcase record={record} />);
    const map = screen.getByRole("table", { name: /측정면별 상태/ });
    expect(within(map).getAllByRole("rowheader")).toHaveLength(10);
    const search = within(map)
      .getByRole("rowheader", { name: "검색" })
      .closest("tr")!;
    expect(search).toHaveTextContent("일부만");
    expect(search).toHaveTextContent("1순위 적중 27/29");
    expect(search).toHaveTextContent("분모: 답할 수 있는 29문항, 근거 8개");
    expect(search).toHaveTextContent("2026-11-09");
    expect(
      within(search).getByRole("link", { name: /ask-sample-replay.md/ }),
    ).toHaveAttribute("href", expect.stringMatching(/^https:\/\/github.com\//));
    const answer = within(map)
      .getByRole("rowheader", { name: "최종 답 정답성" })
      .closest("tr")!;
    expect(answer).toHaveTextContent(
      "세 번 모두 28/29 · 회차마다 결과가 달라진 문항 0개",
    );
    expect(
      within(answer).getByRole("link", { name: "반복 측정 보기" }),
    ).toHaveAttribute("href", "#repetition");
    const refusal = within(map)
      .getByRole("rowheader", { name: "거절" })
      .closest("tr")!;
    expect(refusal).toHaveTextContent(
      "세 번 모두 정확한 거절 1/1 (거절 문항 1개) · 잘못된 거절 0/29",
    );
  });

  it("비어 있는 측정면은 수치 없이 이유를 보인다", () => {
    render(<EvaluationShowcase record={record} />);
    const map = screen.getByRole("table", { name: /측정면별 상태/ });
    for (const surface of [
      "모델 선택",
      "판사 자체",
      "위키 컴파일 품질",
      "도구 궤적",
    ]) {
      const row = within(map)
        .getByRole("rowheader", { name: surface })
        .closest("tr")!;
      expect(row).toHaveTextContent("비어 있음");
      expect(row).not.toHaveTextContent(/\d+\/\d+/);
      expect(row.querySelectorAll("td")[1].textContent!.length).toBeGreaterThan(
        10,
      );
    }
  });

  it("적용 원장은 날짜 오름차순이고 첫 문장이 측정이 바꾼 것이다", () => {
    render(<EvaluationShowcase record={record} />);
    const ledger = screen
      .getByRole("heading", { name: "적용 원장" })
      .closest("section")!;
    const items = within(ledger).getAllByRole("listitem");
    expect(items).toHaveLength(record.ledger.length);
    const dates = items.map((item) =>
      item.querySelector("time")!.getAttribute("dateTime")!,
    );
    expect(dates).toEqual([...dates].sort());
    items.forEach((item, index) => {
      expect(item.querySelector("p")).toHaveTextContent(
        record.ledger[index].changed,
      );
    });
    expect(
      within(items[0]).getByRole("link", { name: /PR #223/ }),
    ).toHaveAttribute("href", "https://github.com/kanziman/NexusWiki/pull/223");
  });

  it("원장 설명의 HTML은 글자로 보인다", () => {
    const variant = clone();
    variant.ledger[0].applied = "<b onclick=alert(1)>굵게</b>";
    const { container } = render(<EvaluationShowcase record={variant} />);
    expect(
      screen.getByText("<b onclick=alert(1)>굵게</b>"),
    ).toBeInTheDocument();
    expect(container.querySelector("b[onclick]")).toBeNull();
  });

  it("점프 목차가 다섯 구역으로 연결된다", () => {
    render(<EvaluationShowcase record={record} />);
    const toc = screen.getByRole("navigation", { name: "이 페이지의 구역" });
    expect(
      within(toc)
        .getAllByRole("link")
        .map((a) => a.getAttribute("href")),
    ).toEqual(["#repetition", "#refusal", "#map", "#ledger", "#conditions"]);
  });

  it("재현 조건과 한계를 결과와 같은 페이지에 둔다", () => {
    render(<EvaluationShowcase record={record} />);
    const section = screen.getByRole("region", { name: "재현 조건과 한계" });
    expect(section).toHaveTextContent("독립 표본이 아닙니다");
    expect(section).toHaveTextContent("안정성을 보장하지 않습니다");
    expect(section).toHaveTextContent("anthropic/claude-sonnet-4.6");
    expect(section).toHaveTextContent("hybrid-rrf-v2");
    expect(section).toHaveTextContent(record.series.key!.snapshot_sha256);
    expect(section).toHaveTextContent(record.series.key!.prompt_sha256);
    for (const text of record.limitations) {
      expect(within(section).getByText(text)).toBeInTheDocument();
    }
    expect(screen.getByRole("link", { name: /JSON 다운로드/ })).toHaveAttribute(
      "href",
      "/showcase/evaluation/results.json",
    );
  });

  it("기록 문자열의 HTML을 실행하지 않고 글자로 보인다", () => {
    const variant = clone();
    variant.limitations = ["<img src=x onerror=alert(1)>"];
    const { container } = render(<EvaluationShowcase record={variant} />);
    expect(
      screen.getByText("<img src=x onerror=alert(1)>"),
    ).toBeInTheDocument();
    expect(container.querySelector("img")).toBeNull();
  });

  it("다운로드는 페이지가 렌더링에 쓴 공개 기록과 같다", async () => {
    const response = GET();
    expect(response.headers.get("Content-Disposition")).toContain(
      "evaluation.v1.json",
    );
    expect(await response.json()).toEqual(committed);
  });

  it("세 쇼케이스가 서로 연결된다", () => {
    const { unmount } = render(<EvaluationShowcase record={record} />);
    expect(screen.getAllByRole("link", { name: /AI 통제/ })[0]).toHaveAttribute(
      "href",
      "/showcase/controlled-ai",
    );
    expect(screen.getAllByRole("link", { name: /재검색/ })[0]).toHaveAttribute(
      "href",
      "/showcase/evidence-research",
    );
    unmount();
    const first = render(
      <ControlledAiShowcase
        evidence={controlled as unknown as ControlledAiEvidence}
      />,
    );
    expect(
      screen.getByRole("link", { name: /평가 지도 · 반복 측정/ }),
    ).toHaveAttribute("href", "/showcase/evaluation");
    first.unmount();
    render(
      <EvidenceResearchShowcase
        evaluation={research as unknown as ResearchEvaluation}
      />,
    );
    expect(
      screen.getByRole("link", { name: /평가 지도 · 반복 측정/ }),
    ).toHaveAttribute("href", "/showcase/evaluation");
  });

  it("공개 경계에서 운영 데이터 클라이언트를 사용하지 않는다", () => {
    for (const path of [
      "app/showcase/evaluation/page.tsx",
      "app/showcase/evaluation/results.json/route.ts",
      "components/EvaluationShowcase.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), path), "utf8");
      expect(source).not.toMatch(
        /from ["'].*(?:supabase|api-client|server-client)/,
      );
      expect(source).not.toMatch(/\bfetch\s*\(/);
      expect(source).not.toMatch(/dangerouslySetInnerHTML/);
    }
  });
});
