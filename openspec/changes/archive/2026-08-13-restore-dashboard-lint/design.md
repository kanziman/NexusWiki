## Context

See `proposal.md` for motivation. The dashboard uses ESLint 9 through its existing `lint` script, but has no flat configuration, so ESLint exits before evaluating source files. The dashboard already depends on `eslint-config-next` at the same Next.js version.

## Goals / Non-Goals

**Goals:**

- Restore a repeatable dashboard lint command using the existing package dependencies.
- Apply the framework-recommended Next.js ESLint rules while avoiding generated and dependency directories.
- Surface and resolve only lint findings necessary for a clean baseline.

**Non-Goals:**

- Upgrade ESLint, Next.js, or other dashboard dependencies.
- Change application behavior or introduce repository-wide linting.
- Reformat unrelated code.

## Decisions

- Add an `eslint.config.mjs` within `apps/dashboard` that uses `@eslint/eslintrc`'s `FlatCompat` adapter to compose the installed legacy `eslint-config-next` configuration. `eslint-config-next@15.5.22` does not expose flat configurations, and an `.eslintrc` file is rejected by the installed ESLint version. Declare the adapter as a direct development dependency because it is otherwise only transitively installed.
- Scope ignore patterns to generated Next.js output, coverage, and package-managed dependencies. Source and test files remain linted.
- Keep the existing `pnpm lint` script unchanged, so local and CI usage remains stable.

## Risks / Trade-offs

- [Existing source may violate newly enabled rules] → Fix only findings reported by the configured dashboard lint command and verify typecheck and tests afterward.
- [The installed Next.js config is legacy-format only] → Use the supported `FlatCompat` adapter and pin it as a direct development dependency.
