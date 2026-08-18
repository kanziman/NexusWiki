import { LoginForm } from "@/components/LoginForm";

// 로그인 화면 자체는 인증 상태를 판정하지 않는다 — 이미 로그인된 사용자를 `/`로
// 돌려보내는 것은 middleware.ts(D-02, 유일한 쿠키 기록자)의 몫이다.
export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-xxl p-lg">
      <h1 className="m-0 text-ink" style={{ font: "var(--font-display-xl)" }}>
        NexusWiki
      </h1>
      <div className="w-full max-w-[360px]">
        <LoginForm initialError={error === "auth"} />
      </div>
    </main>
  );
}
