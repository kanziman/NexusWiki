import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import SignupPage from "@/app/(auth)/signup/page";

describe("SignupPage", () => {
  it("데스크톱 split 가입 경험에 SSO 안내와 지식 미리보기, 시작 CTA를 제공한다", async () => {
    render(await SignupPage({ searchParams: Promise.resolve({}) }));

    expect(
      screen.getByRole("heading", { name: "나만의 지식 자산을 시작하세요." }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: "NexusWiki 답변 미리보기" }),
    ).toBeInTheDocument();
    expect(screen.getByText("답으로 연결하다.")).toHaveClass(
      "login-visual-highlighted",
    );
    expect(
      screen.getByRole("button", { name: "Google 계정으로 시작하기" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Google 계정 하나로 새 워크스페이스 시작과 기존 계정 로그인이 모두 가능합니다.",
      ),
    ).toBeInTheDocument();
  });

  it("콜백 오류를 가입 폼의 단일 오류로 전달한다", async () => {
    render(
      await SignupPage({ searchParams: Promise.resolve({ error: "auth" }) }),
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "로그인에 실패했습니다. 다시 시도해 주세요.",
    );
  });
});
