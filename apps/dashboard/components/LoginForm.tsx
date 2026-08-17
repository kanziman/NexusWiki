"use client";

import { useState } from "react";

import { createClient } from "@/lib/supabase/client";

type LoginFormProps = {
  initialError?: boolean;
};

// 관련 결정: checklists.json > decisions.auth revision 7.
// OAuth는 브라우저에서 시작하지만, code 교환과 세션 쿠키 기록은
// app/auth/callback/route.ts가 담당한다.
export function LoginForm({ initialError = false }: LoginFormProps) {
  const [error, setError] = useState(initialError);
  const [submitting, setSubmitting] = useState(false);

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
    <div className="flex w-full flex-col gap-base">
      {error ? (
        <p
          data-state="error"
          role="alert"
          className="text-primary-error-text"
          style={{ font: "var(--font-caption)", fontWeight: 600 }}
        >
          로그인에 실패했습니다. 다시 시도해 주세요.
        </p>
      ) : null}

      <button
        type="button"
        disabled={submitting}
        onClick={handleGoogleSignIn}
        className="h-12 rounded-sm bg-primary px-lg text-on-primary transition-colors active:bg-primary-active disabled:cursor-not-allowed disabled:bg-primary-disabled"
        style={{ font: "var(--font-button-md)", fontWeight: 600 }}
      >
        Google로 계속하기
      </button>
    </div>
  );
}
