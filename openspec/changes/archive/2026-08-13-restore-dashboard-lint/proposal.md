## Why

The dashboard `lint` script cannot run because ESLint 9 requires a flat configuration file that the project does not provide. This prevents the completed Korean wiki slug change and future dashboard work from receiving the intended lint verification.

## What Changes

- Add a dashboard-scoped ESLint flat configuration compatible with the existing ESLint 9 and Next.js dependencies.
- Keep the existing `pnpm lint` command as the supported verification entry point.
- Verify linting completes successfully for the dashboard codebase without changing application behavior.

## Capabilities

### New Capabilities

None — this is tooling-only work with no product behavior change.

### Modified Capabilities

None.

## Impact

- Affected code: dashboard lint configuration and, only if required by valid lint findings, directly affected source formatting or correctness fixes.
- No API, database schema, authentication, routing, or user-facing behavior changes.
