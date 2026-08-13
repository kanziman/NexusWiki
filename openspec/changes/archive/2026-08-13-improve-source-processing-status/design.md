## Context

`JobStepper` currently polls source jobs and renders all five processing stages for every source row. The API job-chain and action endpoints already satisfy the required behavior; this change is limited to the dashboard presentation layer. See `proposal.md` for motivation and `specs/source-processing-status/spec.md` for the behavior contract.

## Goals / Non-Goals

**Goals:**

- Present one status line with a completed-stage count and a meaningful current or terminal state.
- Keep recovery information visually quiet until a job has failed.
- Preserve polling lifecycle and existing retry/cancel request contracts.

**Non-Goals:**

- Change job-chain ordering, API responses, database state, polling interval, or retry/cancel authorization.
- Add a historical job timeline or alter source-list data loading.

## Decisions

### Derive the summary from the already-polled job chain

The component will continue using the existing ordered stage types and derive completed progress, current work, terminal success, and failure from that response. This keeps the UI aligned with the server-owned job state without adding an endpoint or duplicating state. A server-computed display field was considered but rejected because the dashboard is the only consumer of this presentation-specific aggregation.

### Use progress text instead of the always-expanded stage list

The default rendering will be a concise status sentence paired with a native progress indicator and accessible progress attributes. It will name the active stage when work is ongoing, distinguish cancellation from successful completion, and retain a skeleton until the first response. An expandable stage timeline was considered but rejected because it preserves the repeated visual noise that this change removes.

### Scope actions to the actionable job

Cancellation is offered only for the derived current queued/running job; retry and bounded error detail are rendered only for dead jobs. This preserves the existing request endpoints and confirmation dialog while avoiding controls beside every stage. Removing cancellation entirely was rejected because the proposal explicitly preserves it.

## Risks / Trade-offs

- [Partial or out-of-order job rows make a chain appear incomplete] → derive from the fixed server chain order and show the earliest queued/running stage; continue polling until every expected stage is terminal.
- [Multiple failed rows can produce multiple recovery actions] → show each failed job's bounded error and retry action while leaving non-failed stages compact.
- [Native progress appearance varies by browser] → provide text progress and accessibility attributes as the authoritative information.

## Migration Plan

Deploy as a dashboard-only change. No stored data or API migration is needed. Roll back by restoring the previous `JobStepper` rendering while retaining the unchanged polling and action handlers.
