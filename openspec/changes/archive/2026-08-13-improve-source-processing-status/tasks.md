## 1. Compact status presentation

- [x] 1.1 Refactor `JobStepper` to derive compact current/terminal status and completed-stage progress from the existing job-chain response while retaining polling lifecycle behavior.
- [x] 1.2 Replace the always-expanded five-stage list with an accessible compact summary, progress indicator, and the existing cancellation confirmation flow for the current cancellable job.

## 2. Failure recovery behavior

- [x] 2.1 Render bounded failure detail and accessible retry controls only for dead jobs, preserving retry behavior and polling resumption.

## 3. Verification

- [x] 3.1 Update component tests for compact progress, terminal states, failure-only recovery details, retry, and cancellation.
- [x] 3.2 Run dashboard tests, typecheck, lint, and strict OpenSpec validation.
