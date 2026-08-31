"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { AlertCircle, CheckCircle2, KeyRound, X, Zap } from "lucide-react";
import Link from "next/link";

type CreditLimitModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId?: string;
};

export function CreditLimitModal({
  open,
  onOpenChange,
  workspaceId,
}: CreditLimitModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md transition-all duration-200" />
        <Dialog.Content className="fixed top-1/2 left-1/2 z-50 w-[min(480px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-6 shadow-2xl outline-none">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--warning)]/15 text-[var(--warning)] flex-none">
                <AlertCircle size={22} aria-hidden="true" />
              </div>
              <div>
                <Dialog.Title className="text-base font-bold text-[var(--fg)]">
                  이번 달 무료 크레딧을 모두 소진했습니다
                </Dialog.Title>
                <Dialog.Description className="text-xs text-[var(--muted)] mt-0.5">
                  월간 무료 AI 질의 및 소스 분석 한도에 도달했습니다.
                </Dialog.Description>
              </div>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="icon-btn rounded-lg p-1 text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--fg)] transition-colors cursor-pointer"
                aria-label="창 닫기"
              >
                <X size={16} aria-hidden="true" />
              </button>
            </Dialog.Close>
          </div>

          <div className="space-y-3 my-4 text-xs text-[var(--fg)] leading-relaxed">
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)]/50 p-4 space-y-2.5">
              <div className="flex items-start gap-2">
                <CheckCircle2
                  size={15}
                  className="text-[var(--accent)] flex-none mt-0.5"
                />
                <span>
                  무료 크레딧은 <b>매월 1일</b>에 자동으로 다시 충전됩니다.
                </span>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2
                  size={15}
                  className="text-[var(--accent)] flex-none mt-0.5"
                />
                <span>
                  이미 등록된 위키 문서와 원문 소스는 제한 없이 계속 열람하고
                  복사할 수 있습니다.
                </span>
              </div>
              <div className="flex items-start gap-2 pt-1 border-t border-[var(--border)] text-[var(--fg)] font-medium">
                <Zap
                  size={15}
                  className="text-[var(--accent)] flex-none mt-0.5"
                />
                <span>
                  <b>내 OpenRouter API 키 등록 시 무제한 사용:</b> 워크스페이스
                  설정에서 개인 키를 연결하면 크레딧 제한 없이 바로 작업을
                  이어갈 수 있습니다.
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2 pt-2 border-t border-[var(--border)] mt-6">
            <Dialog.Close asChild>
              <button type="button" className="button compact">
                닫기
              </button>
            </Dialog.Close>
            {workspaceId && (
              <>
                <Dialog.Close asChild>
                  <Link
                    href={`/w/${workspaceId}/settings`}
                    className="button compact primary inline-flex items-center gap-1.5"
                  >
                    <KeyRound size={13} aria-hidden="true" />
                    <span>내 API 키 등록 (무제한)</span>
                  </Link>
                </Dialog.Close>
              </>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
