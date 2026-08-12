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

  // Task 2: globals.css의 @theme 매핑이 생성한 Tailwind 유틸리티 클래스를 쓴다
  // (bg-primary/rounded-sm/p-lg 등) — Task 1의 .airbnb-input/.btn-primary
  // 원시 유틸리티 클래스 대신이다. 로그인 제출 버튼만 accent 색(bg-primary)을
  // 쓰는 것이 이 화면의 유일한 accent 요소여야 한다는 UI-SPEC Primary Visual
  // Anchor 계약이다. 4개 타이포그래피 역할(Body/Label/Heading/Display)은
  // design-tokens.css의 합성 `font` 축약 토큰을 그대로 쓴다 — Tailwind
  // `--text-*`/`--font-weight-*` 네임스페이스로 재매핑하지 않는다(Task 2
  // action이 색상/spacing/radius/font-family만 @theme으로 옮기라고 명시).
  return (
    <form onSubmit={handleSubmit} className="flex w-full flex-col gap-base">
      <div className="flex flex-col gap-xs">
        <label
          htmlFor={emailId}
          className="text-ink"
          style={{ font: "var(--font-caption)" }}
        >
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
          className="h-14 w-full rounded-sm border border-border-strong bg-canvas px-base text-ink outline-none focus:border-ink focus:border-2"
          style={{ font: "var(--font-body-md)" }}
        />
      </div>

      <div className="flex flex-col gap-xs">
        <label
          htmlFor={passwordId}
          className="text-ink"
          style={{ font: "var(--font-caption)" }}
        >
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
          className="h-14 w-full rounded-sm border border-border-strong bg-canvas px-base text-ink outline-none focus:border-ink focus:border-2"
          style={{ font: "var(--font-body-md)" }}
        />
        <p className="text-muted" style={{ font: "var(--font-caption-sm)" }}>
          비밀번호는 12자 이상이어야 합니다.
        </p>
      </div>

      {error !== null ? (
        <p
          data-state="error"
          role="alert"
          className="text-primary-error-text"
          style={{ font: "var(--font-caption)" }}
        >
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={!canSubmit || submitting}
        className="h-12 rounded-sm bg-primary px-lg text-on-primary transition-colors active:bg-primary-active disabled:bg-primary-disabled disabled:cursor-not-allowed"
        style={{ font: "var(--font-button-md)" }}
      >
        로그인
      </button>
    </form>
  );
}
