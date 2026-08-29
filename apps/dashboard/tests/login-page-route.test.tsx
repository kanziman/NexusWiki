import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import LoginPage from "@/app/(auth)/login/page";

describe("LoginPage", () => {
  it("데스크톱 split 로그인 경험에 가입 연결과 지식 미리보기를 제공한다", async () => {
    render(await LoginPage({ searchParams: Promise.resolve({}) }));

    expect(
      screen.getByRole("heading", { name: "팀의 지식으로 돌아오세요." }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: "NexusWiki 답변 미리보기" }),
    ).toBeInTheDocument();
    expect(screen.getByText("답으로 연결하다.")).toHaveClass(
      "login-visual-highlighted",
    );
    expect(
      screen.getByRole("link", { name: "Google 계정으로 시작하기" }),
    ).toHaveAttribute("href", "/signup");
  });

  it("콜백 오류를 로그인 폼의 단일 오류로 전달한다", async () => {
    render(
      await LoginPage({ searchParams: Promise.resolve({ error: "auth" }) }),
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "로그인에 실패했습니다. 다시 시도해 주세요.",
    );
  });
});
