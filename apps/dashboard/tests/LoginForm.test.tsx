import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "@/components/LoginForm";

// `LoginForm`이 브라우저 Supabase 클라이언트를 통해서만 인증을 수행하도록 강제한다
// (D-02: middleware.ts만 쿠키를 쓴다 — 컴포넌트는 supabase-js 호출만 하고 쿠키에
// 손대지 않는다). `lib/supabase/client.ts`를 모킹해 실제 네트워크 호출 없이
// signInWithPassword 성공/실패 분기만 검증한다.
const signInWithPassword = vi.fn();

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: { signInWithPassword },
  }),
}));

// router.push 대신 전체 네비게이션(window.location.assign)을 쓴다 — RSC
// soft-navigation과 방금 쓴 세션 쿠키 사이의 경쟁 조건을 구조적으로 피하기 위해서다
// (06-01 실측으로 발견, LoginForm.tsx 주석 참고). jsdom의 기본 location은 assign을
// 스텁만 하고 "Not implemented: navigation" 경고를 내므로 테스트에서 직접 대체한다.
const assign = vi.fn();
const originalLocation = window.location;

describe("LoginForm", () => {
  beforeEach(() => {
    signInWithPassword.mockReset();
    assign.mockReset();
    // @ts-expect-error - 테스트 전용 location 스텁 교체
    delete window.location;
    // @ts-expect-error - 테스트 전용 location 스텁 교체
    window.location = { ...originalLocation, assign };
  });

  afterEach(() => {
    // @ts-expect-error - 원래 location 복구
    window.location = originalLocation;
  });

  it("이메일 또는 비밀번호가 비어 있으면 제출 버튼이 비활성화된다", () => {
    render(<LoginForm />);

    const submit = screen.getByRole("button", { name: "로그인" });
    expect(submit).toBeDisabled();
  });

  it('잘못된 자격 증명이면 정확한 오류 문구를 data-state="error" 영역에 렌더링한다', async () => {
    signInWithPassword.mockResolvedValue({
      data: { user: null, session: null },
      error: { message: "Invalid login credentials" },
    });

    render(<LoginForm />);

    fireEvent.change(screen.getByLabelText("이메일"), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText("비밀번호"), {
      target: { value: "wrong-password-but-12-chars" },
    });
    fireEvent.click(screen.getByRole("button", { name: "로그인" }));

    const error = await screen.findByText(
      "이메일 또는 비밀번호가 올바르지 않습니다.",
    );
    expect(error.closest('[data-state="error"]')).not.toBeNull();
    expect(assign).not.toHaveBeenCalled();
  });

  it("올바른 자격 증명이면 전체 네비게이션으로 루트로 이동한다", async () => {
    signInWithPassword.mockResolvedValue({
      data: { user: { id: "user-1" }, session: { access_token: "token" } },
      error: null,
    });

    render(<LoginForm />);

    fireEvent.change(screen.getByLabelText("이메일"), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText("비밀번호"), {
      target: { value: "correct-password-12-chars" },
    });
    fireEvent.click(screen.getByRole("button", { name: "로그인" }));

    await waitFor(() => expect(assign).toHaveBeenCalledWith("/"));
  });

  it("비밀번호 필드 아래에 최소 길이 안내 문구를 표시한다", () => {
    render(<LoginForm />);

    expect(
      screen.getByText("비밀번호는 12자 이상이어야 합니다."),
    ).toBeInTheDocument();
  });
});
