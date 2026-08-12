"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { CheckCircle2, RefreshCw, X, XCircle } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { apiFetch } from "@/lib/api-client";

export type JobStepperProps = {
  workspaceId: string;
  rawSourceId: string;
};

type JobRow = {
  id: string;
  type: string;
  step_label: string;
  chain_position: number | null;
  chain_total: number;
  status: string;
  attempts: number;
  max_attempts: number;
  run_after: string;
  last_error: string | null;
  cancel_requested_at: string | null;
  created_at: string;
  updated_at: string;
};

// D-05 verbatim 5단계 캡션 — jobs.py의 STEP_LABELS(서버 소유, 오류 템플릿용
// step_label에서만 쓴다)와는 다른, 이 스테퍼 헤더 전용 고정 문구다. "업로드"는
// raw_source 행이 이미 있어야 이 컴포넌트가 렌더된다는 사실 자체로 항상
// 완료 상태인 implicit 단계라 대응하는 잡 type이 없다.
const STAGE_TYPES = ["parse", "compile", "link_sync", "embed"] as const;
const STAGE_CAPTIONS: Record<(typeof STAGE_TYPES)[number], string> = {
  parse: "파싱",
  compile: "컴파일",
  link_sync: "링크 동기화",
  embed: "임베딩",
};

const TERMINAL_STATUSES = new Set(["succeeded", "dead", "canceled"]);
const CURRENT_CANDIDATE_STATUSES = new Set(["queued", "running"]);

const POLL_INTERVAL_MS = 3000;
const LAST_ERROR_TRUNCATE_LENGTH = 200;

// UI-SPEC Copywriting Contract — 문구를 한 글자도 바꾸지 않는다.
const CANCEL_CONFIRM_COPY =
  "진행 중인 작업을 취소하시겠습니까? 이미 사용된 비용은 환불되지 않습니다.";

// 06-REVIEW.md WR-04: STAGE_TYPES 4개가 전부 종결 상태(TERMINAL_STATUSES)에
// 도달했으면 잡 체인이 더 이상 바뀌지 않는다 — 아직 시작조차 안 한 단계
// (row가 없는 경우)는 종결이 아니므로 계속 폴링해야 한다.
function isChainSettled(rows: JobRow[]): boolean {
  return STAGE_TYPES.every((type) => {
    const job = rows.find((row) => row.type === type);
    return job !== undefined && TERMINAL_STATUSES.has(job.status);
  });
}

function truncateLastError(message: string | null): string {
  if (!message) return "";
  return message.length > LAST_ERROR_TRUNCATE_LENGTH
    ? `${message.slice(0, LAST_ERROR_TRUNCATE_LENGTH)}…`
    : message;
}

/**
 * 잡 진행 스테퍼 — 불확정 스피너 대신 실제 5단계를 보여준다 (D-05, ING-06).
 *
 * 관련 태스크: 06-05-PLAN.md Task 2
 * 설계 근거: apps/api/src/api/routers/jobs.py (`_job_response`의 정확한 형태,
 *            CHAIN_ORDER, STEP_LABELS는 서버 소유 — 여기서 다시 만들지 않는다)
 */
export function JobStepper({ workspaceId, rawSourceId }: JobStepperProps) {
  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [cancelTarget, setCancelTarget] = useState<JobRow | null>(null);
  const [canceling, setCanceling] = useState(false);

  // 06-REVIEW.md WR-04: 인터벌 핸들을 ref로 들고 있어야 "polled to a
  // terminal state, so stop" 판정 이후 이 컴포넌트를 언마운트하지 않고도
  // 인터벌을 멈출 수 있다. SourcesList는 행마다 이 컴포넌트를 마운트한 채
  // 유지하므로(언마운트 없음), effect의 cleanup만으로는 부족하다.
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // 원래 코드의 `cancelled` 클로저 변수와 같은 역할 — poll이 이제 컴포넌트
  // 레벨 콜백(재시도/취소 핸들러에서도 호출)이라 effect 지역 변수로는 더 이상
  // 표현할 수 없다.
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const poll = useCallback(async () => {
    try {
      const result = await apiFetch<{ jobs: JobRow[] }>(
        `/workspaces/${workspaceId}/sources/${rawSourceId}/jobs`,
      );
      if (!mountedRef.current) return;
      setJobs(result.jobs);
      setLoaded(true);
      if (isChainSettled(result.jobs) && pollTimerRef.current !== null) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    } catch {
      // 폴링 한 번의 실패로 스테퍼를 깨뜨리지 않는다 — 다음 tick에서 다시
      // 시도한다(3초 간격 폴링에서 일시적 네트워크 실패는 흔하다).
    }
  }, [workspaceId, rawSourceId]);

  useEffect(() => {
    void poll();
    pollTimerRef.current = setInterval(() => void poll(), POLL_INTERVAL_MS);

    return () => {
      if (pollTimerRef.current !== null) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [poll]);

  // 재시도/취소는 종결 상태였던 잡을 다시 비종결 상태로 되돌릴 수 있다
  // (dead -> queued, running -> canceled 전이 등) — 폴링이 이미 멈춰 있었다면
  // 여기서 다시 켠다. 인터벌이 살아있는 중이면(pollTimerRef.current !== null)
  // 아무것도 하지 않는다.
  function resumePollingIfStopped() {
    if (pollTimerRef.current === null) {
      pollTimerRef.current = setInterval(() => void poll(), POLL_INTERVAL_MS);
    }
  }

  async function handleRetry(jobId: string) {
    setRetryingId(jobId);
    try {
      await apiFetch(`/workspaces/${workspaceId}/jobs/${jobId}/retry`, {
        method: "POST",
      });
      resumePollingIfStopped();
      void poll();
    } catch {
      // 실패해도 다음 폴링이 최신 상태로 자연 정정한다.
    } finally {
      setRetryingId(null);
    }
  }

  async function handleConfirmCancel() {
    if (!cancelTarget) return;
    setCanceling(true);
    try {
      await apiFetch(
        `/workspaces/${workspaceId}/jobs/${cancelTarget.id}/cancel`,
        { method: "POST" },
      );
      resumePollingIfStopped();
      void poll();
    } catch {
      // 실패해도 다음 폴링이 최신 상태로 자연 정정한다.
    } finally {
      setCanceling(false);
      setCancelTarget(null);
    }
  }

  if (!loaded) {
    return (
      <div
        aria-busy="true"
        data-testid="job-stepper-skeleton"
        className="h-8 animate-pulse rounded-sm bg-surface-soft"
      />
    );
  }

  // "현재 단계"는 (parse, compile, link_sync, embed) 순서에서 상태가
  // queued/running인 첫 행이다 — Task 2 <action>의 정의를 그대로 따른다.
  const currentJob = STAGE_TYPES.map((type) =>
    jobs.find((row) => row.type === type),
  ).find(
    (job): job is JobRow =>
      job !== undefined && CURRENT_CANDIDATE_STATUSES.has(job.status),
  );

  return (
    <div className="flex flex-col gap-xs">
      <ol className="flex flex-col gap-sm">
        {/* 업로드 — 이 컴포넌트가 렌더된다는 것 자체가 raw_source 행의 존재를
            증명하므로 항상 완료 상태다 (implicit stage, 대응하는 잡 없음). */}
        <li className="flex items-center gap-sm">
          <CheckCircle2
            size={16}
            aria-hidden="true"
            className="text-success-text"
          />
          <span className="text-ink" style={{ font: "var(--font-caption)" }}>
            업로드
          </span>
        </li>

        {STAGE_TYPES.map((type) => {
          const job = jobs.find((row) => row.type === type);
          const caption = STAGE_CAPTIONS[type];
          const isDone = job?.status === "succeeded";
          const isDead = job?.status === "dead";
          const isCurrent = job !== undefined && job === currentJob;
          const showCancel =
            job !== undefined && !TERMINAL_STATUSES.has(job.status);

          const labelClassName = isCurrent
            ? "text-primary"
            : isDead
              ? "text-primary-error-text"
              : isDone
                ? "text-ink"
                : "text-muted";

          return (
            <li key={type} className="flex flex-col gap-xs">
              <div className="flex items-center gap-sm">
                {isDone ? (
                  <CheckCircle2
                    size={16}
                    aria-hidden="true"
                    className="text-success-text"
                  />
                ) : isDead ? (
                  <XCircle
                    size={16}
                    aria-hidden="true"
                    className="text-primary-error-text"
                  />
                ) : (
                  <span
                    aria-hidden="true"
                    className={`h-4 w-4 rounded-full border-2 ${
                      isCurrent
                        ? "border-primary bg-primary"
                        : "border-hairline"
                    }`}
                  />
                )}
                <span
                  className={labelClassName}
                  style={{ font: "var(--font-caption)" }}
                >
                  {caption}
                </span>

                {isDead && job ? (
                  // Icon-only touch target: 44x44px + aria-label (D-08, UI-SPEC 예외 규칙).
                  <button
                    type="button"
                    aria-label="재시도"
                    onClick={() => handleRetry(job.id)}
                    disabled={retryingId === job.id}
                    className="flex h-11 w-11 items-center justify-center rounded-sm text-primary-error-text disabled:opacity-60"
                  >
                    <RefreshCw size={18} aria-hidden="true" />
                  </button>
                ) : null}

                {showCancel && job ? (
                  <button
                    type="button"
                    aria-label="취소"
                    onClick={() => setCancelTarget(job)}
                    className="flex h-11 w-11 items-center justify-center rounded-sm text-muted"
                  >
                    <X size={18} aria-hidden="true" />
                  </button>
                ) : null}
              </div>

              {isDead && job ? (
                // UI-SPEC Copywriting Contract "Error state" 템플릿 — {단계}는
                // 서버가 준 step_label(풀 네임)을 쓰고, {last_error 요약}은
                // 200자에서 잘라 원문 예외를 그대로 노출하지 않는다.
                <p
                  role="alert"
                  className="text-primary-error-text"
                  style={{ font: "var(--font-caption)" }}
                >
                  {`${job.step_label} 단계에서 실패했습니다 — ${truncateLastError(
                    job.last_error,
                  )}. 재시도를 눌러 다시 시도하세요.`}
                </p>
              ) : null}
            </li>
          );
        })}
      </ol>

      <Dialog.Root
        open={cancelTarget !== null}
        onOpenChange={(open) => {
          if (!open) setCancelTarget(null);
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/40" />
          <Dialog.Content className="fixed top-1/2 left-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-md bg-canvas p-lg shadow-[var(--shadow-modal)]">
            <Dialog.Title
              className="text-ink"
              style={{ font: "var(--font-title-md)" }}
            >
              작업 취소
            </Dialog.Title>
            <Dialog.Description
              className="text-body"
              style={{ font: "var(--font-body-md)" }}
            >
              {CANCEL_CONFIRM_COPY}
            </Dialog.Description>

            <div className="flex justify-end gap-sm">
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="rounded-sm border border-border-strong px-base py-sm text-ink"
                >
                  계속 진행
                </button>
              </Dialog.Close>
              <button
                type="button"
                onClick={handleConfirmCancel}
                disabled={canceling}
                className="rounded-sm bg-primary-error-text px-base py-sm text-on-primary disabled:opacity-60"
              >
                취소하기
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
