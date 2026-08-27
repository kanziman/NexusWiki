import Image from "next/image";
import Link from "next/link";

import { LoginKnowledgePreview } from "@/components/LoginKnowledgePreview";
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
    <main className="login-page">
      <section className="login-visual" aria-labelledby="login-visual-title">
        <Image
          className="login-landscape"
          src="/nexuswiki-login-knowledge-landscape-bright.png"
          alt=""
          fill
          priority
          sizes="(max-width: 900px) 100vw, 58vw"
        />
        <div className="login-visual-content">
          <Link className="login-brand-lockup" href="/">
            <Image
              src="/nexuswiki-mark.png"
              alt=""
              width={34}
              height={34}
              priority
            />
            <span>
              NexusWiki
              <small>LIVING KNOWLEDGE</small>
            </span>
          </Link>

          <div className="login-visual-copy">
            <h1 id="login-visual-title">
              팀의 지식을,
              <br />
              답으로 연결하다.
            </h1>
            <p>
              원문과 위키를 함께 탐색해 답변의 출처와 맥락을 한 화면에서
              연결합니다.
            </p>
          </div>

          <LoginKnowledgePreview />
        </div>
      </section>

      <section className="login-pane" aria-labelledby="login-title">
        <div className="login-auth-card">
          <div className="login-auth-brand">
            <Image
              src="/nexuswiki-mark.png"
              alt=""
              width={31}
              height={31}
              priority
            />
            <span>NexusWiki</span>
          </div>

          <p className="login-kicker">WELCOME BACK</p>
          <h2 id="login-title" aria-label="팀의 지식으로 돌아오세요.">
            팀의 지식으로
            <br />
            돌아오세요.
          </h2>
          <p className="login-intro">
            Google 계정 하나로 워크스페이스와 연결된 지식에 안전하게 접근합니다.
          </p>

          <LoginForm initialError={error === "auth"} presentation="login" />

          <div className="login-divider" aria-hidden="true" />
          <p className="login-signup-copy">
            처음 오셨나요? <Link href="/signup">Google 계정으로 시작하기</Link>
          </p>
        </div>
      </section>
    </main>
  );
}
