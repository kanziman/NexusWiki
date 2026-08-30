import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "@/components/LoginForm";

const signInWithOAuth = vi.fn();

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({ auth: { signInWithOAuth } }),
}));

describe("LoginForm", () => {
  beforeEach(() => {
    signInWithOAuth.mockReset();
  });

  it("Google CTA만 제공하고 내부 콜백으로 OAuth를 시작한다", async () => {
    signInWithOAuth.mockResolvedValue({ data: {}, error: null });

    render(<LoginForm />);

    expect(screen.queryByLabelText("이메일")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("비밀번호")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Google로 계속하기" }));

    await waitFor(() =>
      expect(signInWithOAuth).toHaveBeenCalledWith({
        provider: "google",
        options: {
          redirectTo: "http://localhost:3000/auth/callback?next=%2F",
        },
      }),
    );
  });

  it("OAuth 시작 실패는 계정 존재 여부를 드러내지 않는 단일 문구로 표시한다", async () => {
    signInWithOAuth.mockResolvedValue({
      data: {},
      error: { message: "provider failure" },
    });

    render(<LoginForm />);
    fireEvent.click(screen.getByRole("button", { name: "Google로 계속하기" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "로그인에 실패했습니다. 다시 시도해 주세요.",
    );
  });

  it("로그인 화면 표현은 OAuth 진행 중 중복 요청을 막고 상태를 알린다", async () => {
    let resolveOAuth:
      ((value: { data: object; error: null }) => void) | undefined;
    signInWithOAuth.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveOAuth = resolve;
        }),
    );

    render(<LoginForm presentation="login" />);
    const button = screen.getByRole("button", {
      name: "Google 계정으로 계속하기",
    });

    fireEvent.click(button);

    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(screen.getByText("Google로 이동 중")).toBeInTheDocument();
    expect(
      screen.getByText("보안 인증 페이지를 준비하고 있습니다."),
    ).toBeInTheDocument();

    resolveOAuth?.({ data: {}, error: null });
  });

  it("가입 화면 표현은 'Google 계정으로 시작하기' 버튼을 제공한다", async () => {
    signInWithOAuth.mockResolvedValue({ data: {}, error: null });

    render(<LoginForm presentation="signup" />);
    const button = screen.getByRole("button", {
      name: "Google 계정으로 시작하기",
    });

    expect(button).toBeInTheDocument();
    fireEvent.click(button);

    await waitFor(() =>
      expect(signInWithOAuth).toHaveBeenCalledWith({
        provider: "google",
        options: {
          redirectTo: "http://localhost:3000/auth/callback?next=%2F",
        },
      }),
    );
  });
});
