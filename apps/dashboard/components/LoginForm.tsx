"use client";

import { useState } from "react";

import { createClient } from "@/lib/supabase/client";

type LoginFormProps = {
  initialError?: boolean;
  presentation?: "default" | "login";
};

// 관련 결정: checklists.json > decisions.auth revision 7.
// OAuth는 브라우저에서 시작하지만, code 교환과 세션 쿠키 기록은
// app/auth/callback/route.ts가 담당한다.
export function LoginForm({
  initialError = false,
  presentation = "default",
}: LoginFormProps) {
  const [error, setError] = useState(initialError);
  const [submitting, setSubmitting] = useState(false);
  const isLoginPresentation = presentation === "login";
  const buttonLabel = submitting
    ? "Google로 이동 중"
    : isLoginPresentation
      ? "Google 계정으로 계속하기"
      : "Google로 계속하기";

  async function handleGoogleSignIn() {
    if (submitting) return;

    setSubmitting(true);
    setError(false);

    const redirectTo = new URL("/auth/callback", window.location.origin);
    redirectTo.searchParams.set("next", "/");

    const { error: signInError } = await createClient().auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: redirectTo.toString() },
    });

    if (signInError) {
      setError(true);
      setSubmitting(false);
    }
  }

  return (
    <div
      className={
        isLoginPresentation ? "login-form" : "flex w-full flex-col gap-base"
      }
    >
      {error ? (
        <p
          data-state="error"
          role="alert"
          className={
            isLoginPresentation ? "login-auth-error" : "text-primary-error-text"
          }
          style={
            isLoginPresentation
              ? undefined
              : { font: "var(--font-caption)", fontWeight: 600 }
          }
        >
          로그인에 실패했습니다. 다시 시도해 주세요.
        </p>
      ) : null}

      <button
        type="button"
        disabled={submitting}
        onClick={handleGoogleSignIn}
        aria-busy={submitting}
        className={
          isLoginPresentation
            ? "login-google-button"
            : "h-12 rounded-sm bg-primary px-lg text-on-primary transition-colors active:bg-primary-active disabled:cursor-not-allowed disabled:bg-primary-disabled"
        }
        style={
          isLoginPresentation
            ? undefined
            : { font: "var(--font-button-md)", fontWeight: 600 }
        }
      >
        {isLoginPresentation ? (
          <>
            <svg
              className="login-google-icon"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                fill="#4285f4"
                d="M21.6 12.2c0-.7-.1-1.4-.2-2H12v3.8h5.4a4.6 4.6 0 0 1-2 3v2.5h3.2c1.9-1.8 3-4.4 3-7.3Z"
              />
              <path
                fill="#34a853"
                d="M12 22c2.7 0 5-.9 6.6-2.5l-3.2-2.5c-.9.6-2 .9-3.4.9-2.6 0-4.8-1.8-5.6-4.1H3.1v2.6A10 10 0 0 0 12 22Z"
              />
              <path
                fill="#fbbc05"
                d="M6.4 13.8a6 6 0 0 1 0-3.6V7.6H3.1a10 10 0 0 0 0 8.8l3.3-2.6Z"
              />
              <path
                fill="#ea4335"
                d="M12 6.1c1.5 0 2.8.5 3.9 1.5l2.9-2.9C17 3.1 14.7 2 12 2a10 10 0 0 0-8.9 5.6l3.3 2.6C7.2 7.9 9.4 6.1 12 6.1Z"
              />
            </svg>
            <span className="login-google-loader" aria-hidden="true" />
          </>
        ) : null}
        <span>{buttonLabel}</span>
      </button>
      {isLoginPresentation ? (
        <p className="login-auth-feedback" aria-live="polite">
          {submitting ? "보안 인증 페이지를 준비하고 있습니다." : null}
        </p>
      ) : null}
    </div>
  );
}
