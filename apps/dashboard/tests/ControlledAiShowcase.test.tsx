import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { dynamic } from "@/app/showcase/controlled-ai/page";
import {
  ControlledAiShowcase,
  type ControlledAiEvidence,
} from "@/components/ControlledAiShowcase";
import { config as middlewareConfig } from "@/middleware";
import evidence from "@/content/controlled-ai/step1.json";

function ControlledAiShowcasePage() {
  return <ControlledAiShowcase evidence={evidence as ControlledAiEvidence} />;
}

const SOURCES = [
  "app/showcase/controlled-ai/page.tsx",
  "components/ControlledAiShowcase.tsx",
];

function article(title: string) {
  const heading = screen.getByRole("heading", { level: 2, name: title });
  const container = heading.closest("article");
  if (!container) throw new Error(`항목을 찾지 못했습니다: ${title}`);
  return within(container);
}

describe("ControlledAiShowcase", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("합성 데이터이며 운영 성과가 아니라고 먼저 밝힌다", () => {
    render(<ControlledAiShowcasePage />);

    const notice = screen.getByRole("note");
    expect(notice).toHaveTextContent("합성 데이터입니다");
    expect(notice).toHaveTextContent("운영 성과가 아니며");
  });

  it("비용 누락 항목에 수정 전후 비용과 시나리오, 커밋을 표시한다", () => {
    render(<ControlledAiShowcasePage />);

    const item = article("충돌 판정 비용 누락");
    const recorded = item.getByRole("row", { name: /회계에 기록된 비용/ });

    expect(
      within(recorded)
        .getAllByRole("cell")
        .map((cell) => cell.textContent),
    ).toEqual(["$0.0000", "$0.0020"]);
    expect(item.getByText("conflict_judge_cost")).toBeInTheDocument();
    expect(item.getByText("79b68fe")).toBeInTheDocument();
  });

  it("모든 증거 항목에 시나리오와 양쪽 커밋을 표시한다", () => {
    render(<ControlledAiShowcasePage />);

    for (const entry of evidence.items) {
      const item = article(entry.title);
      expect(item.getByText(entry.scenario)).toBeInTheDocument();
      expect(item.getByText("수정 전 커밋")).toBeInTheDocument();
      expect(item.getByText("수정 후 커밋")).toBeInTheDocument();
    }
  });

  it("아직 커밋되지 않은 측정값을 커밋 전으로 표시한다", () => {
    render(<ControlledAiShowcasePage />);

    const uncommitted = evidence.items.filter(
      (entry) => entry.after.commit === "uncommitted",
    );
    for (const entry of uncommitted) {
      expect(article(entry.title).getByText("커밋 전")).toBeInTheDocument();
    }
  });

  it("Step 2 예산 통제 항목에 토큰 상한과 절감 결과를 표시한다", () => {
    render(<ControlledAiShowcasePage />);

    const budgetItem = article("질문 컨텍스트 무제한 주입과 원문 근거 기아");
    const contextRow = budgetItem.getByRole("row", {
      name: /프롬프트 컨텍스트 크기/,
    });
    expect(
      within(contextRow)
        .getAllByRole("cell")
        .map((cell) => cell.textContent),
    ).toEqual(["19,842토큰", "6,000토큰"]);

    const maxTokensItem = article("구조화 호출의 입출력 토큰 무제한 요청");
    const maxTokensRow = maxTokensItem.getByRole("row", {
      name: /요청한 출력 상한/,
    });
    expect(
      within(maxTokensRow)
        .getAllByRole("cell")
        .map((cell) => cell.textContent),
    ).toEqual(["기록 없음", "512토큰"]);
  });

  it("모든 Step의 증거가 있으면 다음 단계 영역을 표시하지 않는다", () => {
    render(<ControlledAiShowcasePage />);

    expect(screen.queryByRole("region", { name: "다음 단계" })).toBeNull();
    expect(
      screen.getByText("검증된 페이지의 무단 덮어쓰기"),
    ).toBeInTheDocument();
  });

  it("렌더링하는 동안 네트워크를 호출하지 않는다", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(<ControlledAiShowcasePage />);

    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("정적 라우트이고 데이터 클라이언트나 세션을 읽는 모듈을 import하지 않는다", () => {
    expect(dynamic).toBe("force-static");

    for (const path of SOURCES) {
      const source = readFileSync(resolve(process.cwd(), path), "utf8");
      expect(source, path).not.toMatch(
        /from\s+["'][^"']*(supabase|api-client)[^"']*["']/,
      );
      expect(source, path).not.toMatch(/from\s+["']next\/headers["']/);
      expect(source, path).not.toMatch(/\bfetch\(/);
    }
  });

  it("세션 미들웨어를 거치지 않아 로그인으로 이동하거나 인증 서버를 부르지 않는다", () => {
    const matcher = middlewareConfig.matcher as string[];

    expect(matcher.some((pattern) => pattern.startsWith("/showcase"))).toBe(
      false,
    );
  });

  it("다른 라우트를 프리페치해 미들웨어와 서버 렌더링을 깨우지 않는다", () => {
    const source = readFileSync(resolve(process.cwd(), SOURCES[1]), "utf8");
    const links = source.match(/<Link\b[^>]*>/g) ?? [];

    expect(links.length).toBeGreaterThan(0);
    for (const link of links) {
      expect(link).toContain("prefetch={false}");
    }
  });
});
