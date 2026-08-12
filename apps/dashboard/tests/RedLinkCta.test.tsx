import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// GraphLensFilter.test.tsx와 동일한 모킹 전략 — router.push 호출 인자(URL)를
// 직접 관찰한다.
const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

import { RedLinkCta } from "@/components/RedLinkCta";

describe("RedLinkCta", () => {
  beforeEach(() => {
    push.mockReset();
  });

  it("제목과 고정 문구 '아직 작성되지 않음 · 지금 생성'을 렌더링한다", () => {
    render(<RedLinkCta title="주제 A" slug="주제-a" workspaceId="ws-1" />);

    expect(screen.getByText("주제 A")).toBeInTheDocument();
    expect(
      screen.getByText("아직 작성되지 않음 · 지금 생성"),
    ).toBeInTheDocument();
  });

  it("생성 아이콘은 aria-label='지금 생성'을 가진 버튼이다", () => {
    render(<RedLinkCta title="주제 A" slug="주제-a" workspaceId="ws-1" />);

    expect(
      screen.getByRole("button", { name: "지금 생성" }),
    ).toBeInTheDocument();
  });

  it("생성 아이콘 클릭 시 /sources?prefillTitle=<encoded title>&tab=text로 이동한다", async () => {
    const user = userEvent.setup();
    render(<RedLinkCta title="주제 A" slug="주제-a" workspaceId="ws-1" />);

    await user.click(screen.getByRole("button", { name: "지금 생성" }));

    expect(push).toHaveBeenCalledTimes(1);
    const [calledPath] = push.mock.calls[0] as [string];
    expect(calledPath).toContain("/w/ws-1/sources?");
    expect(calledPath).toContain(
      "prefillTitle=" + encodeURIComponent("주제 A"),
    );
    expect(calledPath).toContain("tab=text");
  });

  it("이 CTA는 wiki_pages 행을 직접 만들지 않는다 — sources 경로로만 이동한다", async () => {
    const user = userEvent.setup();
    render(
      <RedLinkCta
        title="긴 제목 테스트"
        slug="긴-제목-테스트"
        workspaceId="ws-2"
      />,
    );

    await user.click(screen.getByRole("button", { name: "지금 생성" }));

    const [calledPath] = push.mock.calls[0] as [string];
    expect(calledPath.startsWith("/w/ws-2/sources?")).toBe(true);
  });
});
