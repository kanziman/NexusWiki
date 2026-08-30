import Image from "next/image";
import Link from "next/link";

import { LoginHeroTitle } from "@/components/LoginHeroTitle";
import { LoginKnowledgePreview } from "@/components/LoginKnowledgePreview";
import { LoginForm } from "@/components/LoginForm";

export default async function SignupPage({
  searchParams,
}: {
  searchParams?: Promise<{ error?: string }>;
}) {
  const resolvedSearchParams = searchParams ? await searchParams : {};
  const error = resolvedSearchParams.error;

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
            <LoginHeroTitle />
            <p>
              원문과 위키를 함께 탐색해 답변의 출처와 맥락을 한 화면에서
              연결합니다.
            </p>
          </div>

          <LoginKnowledgePreview />
        </div>
      </section>

      <section className="login-pane" aria-labelledby="signup-title">
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

          <p className="login-kicker">GET STARTED</p>
          <h2 id="signup-title" aria-label="나만의 지식 자산을 시작하세요.">
            나만의 지식 자산을
            <br />
            시작하세요.
          </h2>
          <p className="login-intro">
            Google 계정 하나로 워크스페이스를 만들고 살아있는 지식 위키를
            시작합니다.
          </p>

          <LoginForm initialError={error === "auth"} presentation="signup" />

          <div className="login-divider" aria-hidden="true" />
          <p className="login-signup-copy">
            Google 계정 하나로 새 워크스페이스 시작과 기존 계정 로그인이 모두
            가능합니다.
          </p>
        </div>
      </section>
    </main>
  );
}
