"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import React, { useState } from "react";

import { workspacePath } from "@/lib/workspace-path";

type CreateWorkspace = (
  name: string,
) => Promise<{ workspaceId: string } | { error: string }>;

type WorkspaceOnboardingProps = {
  createWorkspace: CreateWorkspace;
};

export function WorkspaceOnboarding({
  createWorkspace,
}: WorkspaceOnboardingProps) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const trimmedName = name.trim();

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!trimmedName || submitting) return;

    setSubmitting(true);
    setError(null);
    const result = await createWorkspace(trimmedName);

    if ("error" in result) {
      setError(result.error);
      setSubmitting(false);
      return;
    }

    router.push(workspacePath(result.workspaceId));
  }

  return (
    <main className="relative flex min-h-screen w-full flex-col items-center justify-center p-4 sm:p-6 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[var(--soft)]/30 via-[var(--bg)] to-[var(--bg)]">
      <div className="w-full max-w-[420px] rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-6 sm:p-8 shadow-xl">
        <div className="flex flex-col items-center text-center">
          <div className="flex items-center justify-center gap-2.5">
            <Image
              src="/nexuswiki-mark.png"
              alt="NexusWiki"
              width={38}
              height={38}
              priority
              className="rounded-xl shadow-xs"
            />
            <span className="font-extrabold text-xl tracking-tight text-[var(--fg)]">
              NexusWiki
            </span>
          </div>

          <h1 className="mt-5 text-xl font-bold tracking-tight text-[var(--fg)]">
            첫 워크스페이스 만들기
          </h1>
          <p className="mt-1 text-xs text-[var(--muted)]">
            개인 지식 베이스를 시작할 이름을 입력하세요.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <label className="flex flex-col gap-1.5 text-xs font-bold text-[var(--fg)]">
            <span>워크스페이스 이름</span>
            <input
              name="workspace-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={100}
              placeholder="예: 프로젝트 지식 허브"
              required
              className="h-10 rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 text-xs text-[var(--fg)] focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/15 focus:outline-none transition-all"
            />
          </label>

          {error ? (
            <p
              role="alert"
              className="rounded-md bg-[var(--danger)]/10 border border-[var(--danger)]/20 p-2 text-xs font-semibold text-[var(--danger)]"
            >
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={!trimmedName || submitting}
            className="button primary mt-2 flex h-10 w-full items-center justify-center rounded-lg text-xs font-bold shadow-xs disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {submitting ? "생성 중..." : "워크스페이스 만들기"}
          </button>
        </form>
      </div>
    </main>
  );
}
