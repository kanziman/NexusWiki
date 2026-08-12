import { LoginForm } from "@/components/LoginForm";

// 로그인 화면 자체는 인증 상태를 판정하지 않는다 — 이미 로그인된 사용자를 `/`로
// 돌려보내는 것은 middleware.ts(D-02, 유일한 쿠키 기록자)의 몫이다.
export default function LoginPage() {
  return (
    <main
      style={{
        display: "flex",
        minHeight: "100vh",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "var(--spacing-xxl)",
        padding: "var(--spacing-lg)",
      }}
    >
      <h1 style={{ font: "var(--font-display-xl)", margin: 0 }}>NexusWiki</h1>
      <div style={{ width: "100%", maxWidth: "360px" }}>
        <LoginForm />
      </div>
    </main>
  );
}
