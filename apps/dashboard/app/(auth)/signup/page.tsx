import Image from "next/image";

import { LoginForm } from "@/components/LoginForm";

export default function SignupPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-xxl p-lg">
      <div className="flex items-center gap-sm">
        <Image
          src="/nexuswiki-mark.png"
          alt=""
          width={38}
          height={38}
          priority
        />
        <h1 className="m-0 text-ink" style={{ font: "var(--font-display-xl)" }}>
          NexusWiki 가입
        </h1>
      </div>
      <div className="flex w-full max-w-[360px] flex-col gap-base">
        <LoginForm />
        <p
          className="m-0 text-muted"
          style={{ font: "var(--font-caption-sm)" }}
        >
          계속하면 <a href="/terms">이용약관</a> 및{" "}
          <a href="/privacy">개인정보 처리방침</a>에 동의하게 됩니다. 현재 준비
          중입니다.
        </p>
      </div>
    </main>
  );
}
