"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

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
    <main className="flex min-h-screen items-center justify-center p-lg">
      <form
        onSubmit={handleSubmit}
        className="flex w-full max-w-[360px] flex-col gap-base"
      >
        <div>
          <h1
            className="m-0 text-ink"
            style={{ font: "var(--font-display-lg)" }}
          >
            첫 워크스페이스 만들기
          </h1>
          <p className="text-muted" style={{ font: "var(--font-body-md)" }}>
            개인 지식 베이스를 시작할 이름을 입력하세요.
          </p>
        </div>
        <label
          className="flex flex-col gap-xs"
          style={{ font: "var(--font-caption)", fontWeight: 600 }}
        >
          워크스페이스 이름
          <input
            name="workspace-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={100}
            required
            className="h-12 rounded-sm border border-border-strong bg-canvas px-base text-ink"
          />
        </label>
        {error ? <p role="alert">{error}</p> : null}
        <button
          type="submit"
          disabled={!trimmedName || submitting}
          className="h-12 rounded-sm bg-primary text-on-primary disabled:cursor-not-allowed disabled:bg-primary-disabled"
        >
          워크스페이스 만들기
        </button>
      </form>
    </main>
  );
}
