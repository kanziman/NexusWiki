"use client";

import { useId, useState } from "react";

import { createClient } from "@/lib/supabase/client";

// 이메일/비밀번호가 로그인 방식의 전부다 (D-01 — 매직링크/OAuth 없음).
export function LoginForm() {
  const emailId = useId();
  const passwordId = useId();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = email.trim().length > 0 && password.length > 0;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit || submitting) return;

    setSubmitting(true);
    setError(null);

    const supabase = createClient();
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    setSubmitting(false);

    if (signInError) {
      // D-12(no-enumeration)를 로그인 화면에도 그대로 적용한다 — "계정 없음"과
      // "비밀번호 오류"를 구분하지 않는다 (UI-SPEC 카피 계약 원문 그대로).
      setError("이메일 또는 비밀번호가 올바르지 않습니다.");
      return;
    }

    // app/page.tsx가 실제 워크스페이스 id를 조회해 /w/[workspaceId]로 리다이렉트한다.
    //
    // ⚠️ router.push가 아니라 전체 네비게이션을 쓴다 — 06-01 실측 중 발견한 버그:
    // signInWithPassword 직후 client-side router.push("/")를 쓰면 Next.js RSC
    // soft-navigation fetch가 @supabase/ssr이 막 쓴 세션 쿠키를 middleware/서버가
    // 아직 인식하기 전에 발생할 수 있어(RSC 요청과 쿠키 반영 사이의 경쟁 조건),
    // 방금 로그인했는데도 "/"가 미인증 상태로 렌더링되는 것을 실측으로 확인했다.
    // 전체 네비게이션은 항상 새 HTTP 요청이므로 이 경쟁 조건이 구조적으로
    // 발생하지 않는다 — 06-01-PLAN.md Task 1 <behavior>가 "router.push (or full
    // navigation)"으로 두 방식을 모두 허용해 두었다.
    window.location.assign("/");
  }

  // 스타일은 1차로 design-tokens.css의 기존 유틸리티 클래스(.airbnb-input,
  // .btn-primary)와 CSS 커스텀 프로퍼티만 사용한다 — Tailwind @theme 편입(06-01
  // Task 2)이 아직 없으므로 존재하지 않는 유틸리티 클래스명을 미리 쓰지 않는다.
  return (
    <form
      onSubmit={handleSubmit}
      style={{
        display: "flex",
        width: "100%",
        flexDirection: "column",
        gap: "var(--spacing-base)",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "var(--spacing-xs)",
        }}
      >
        <label htmlFor={emailId} style={{ font: "var(--font-caption)" }}>
          이메일
        </label>
        <input
          id={emailId}
          name="email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="airbnb-input"
        />
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "var(--spacing-xs)",
        }}
      >
        <label htmlFor={passwordId} style={{ font: "var(--font-caption)" }}>
          비밀번호
        </label>
        <input
          id={passwordId}
          name="password"
          type="password"
          required
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="airbnb-input"
        />
        <p
          style={{
            font: "var(--font-caption-sm)",
            color: "var(--color-muted)",
          }}
        >
          비밀번호는 12자 이상이어야 합니다.
        </p>
      </div>

      {error !== null ? (
        <p
          data-state="error"
          role="alert"
          style={{
            font: "var(--font-caption)",
            color: "var(--color-primary-error-text)",
          }}
        >
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={!canSubmit || submitting}
        className="btn-primary"
      >
        로그인
      </button>
    </form>
  );
}
