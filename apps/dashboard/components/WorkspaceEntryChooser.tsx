import { ChevronRight, Plus } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import React from "react";

import { workspacePath } from "@/lib/workspace-path";

type WorkspaceEntryChooserProps = {
  workspaces: { id: string; name: string }[];
};

/**
 * 초기 접속 화면 / 워크스페이스 선택 화면
 *
 * - 브랜드 로고(/nexuswiki-mark.png)와 타이포그래피 위계
 * - 세련된 워크스페이스 카드 셀렉터 및 인터랙션
 * - taste-skill 기반 고품질 조판 적용
 */
export function WorkspaceEntryChooser({
  workspaces,
}: WorkspaceEntryChooserProps) {
  return (
    <main className="relative flex min-h-screen w-full flex-col items-center justify-center p-4 sm:p-6 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[var(--soft)]/30 via-[var(--bg)] to-[var(--bg)]">
      <div className="w-full max-w-[460px] rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-6 sm:p-8 shadow-xl">
        {/* 브랜드 로고 & 헤더 */}
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
            워크스페이스 선택
          </h1>
          <p className="mt-1.5 text-xs text-[var(--muted)]">
            계속할 워크스페이스를 선택하세요.
          </p>
        </div>

        {/* 워크스페이스 목록 */}
        <div className="mt-6">
          <ul className="space-y-2.5">
            {workspaces.map((workspace) => {
              const initial = workspace.name.charAt(0).toUpperCase();
              return (
                <li key={workspace.id}>
                  <Link
                    href={workspacePath(workspace.id)}
                    aria-label={workspace.name}
                    className="group flex items-center justify-between gap-3 p-3.5 rounded-xl border border-[var(--border)] bg-[var(--surface)]/30 hover:bg-[var(--surface)] hover:border-[var(--accent)]/50 transition-all shadow-2xs"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div
                        aria-hidden="true"
                        className="flex h-9 w-9 flex-none items-center justify-center rounded-lg bg-[var(--bg)] border border-[var(--border)] font-bold text-sm text-[var(--fg)] group-hover:border-[var(--accent)] group-hover:text-[var(--accent)] transition-all"
                      >
                        {initial}
                      </div>
                      <div className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-bold text-[var(--fg)] group-hover:text-[var(--accent)] transition-colors">
                          {workspace.name}
                        </span>
                        <span
                          aria-hidden="true"
                          className="block truncate text-[11px] text-[var(--muted)] mt-0.5"
                        >
                          지식 베이스 바로가기
                        </span>
                      </div>
                    </div>
                    <ChevronRight
                      size={16}
                      className="text-[var(--muted)] group-hover:text-[var(--accent)] group-hover:translate-x-0.5 transition-all flex-none opacity-60 group-hover:opacity-100"
                    />
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>

        {/* 푸터: 새 워크스페이스 생성 안내 */}
        <div className="mt-6 pt-5 border-t border-[var(--border)] flex items-center justify-center">
          <Link
            href="/w/new"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--muted)] hover:text-[var(--accent)] transition-colors"
          >
            <Plus size={13} aria-hidden="true" />
            <span>새 워크스페이스 만들기</span>
          </Link>
        </div>
      </div>
    </main>
  );
}
