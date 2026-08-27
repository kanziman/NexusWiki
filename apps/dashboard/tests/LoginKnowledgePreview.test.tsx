import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LoginKnowledgePreview } from "@/components/LoginKnowledgePreview";

const initialQuestion = "지난 분기 고객 이탈 원인은 무엇이었나요?";

function mockMatchMedia(matches: boolean) {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: vi.fn().mockReturnValue({
      matches,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }),
  });
}

describe("LoginKnowledgePreview", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockMatchMedia(false);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("질문을 타이핑한 뒤 답변과 근거를 순서대로 표시한다", async () => {
    render(<LoginKnowledgePreview />);

    expect(screen.getByText(initialQuestion)).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(900);
    });

    expect(screen.getByText("질문 입력 중")).toBeInTheDocument();
    expect(screen.queryByText(initialQuestion)).not.toBeInTheDocument();
  });

  it("감소 모션 설정에서는 타이핑 순환을 시작하지 않고 완성된 내용을 유지한다", async () => {
    mockMatchMedia(true);
    render(<LoginKnowledgePreview />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000);
    });

    expect(screen.getByText(initialQuestion)).toBeInTheDocument();
    expect(screen.getByText("근거 연결 완료")).toBeInTheDocument();
  });
});
