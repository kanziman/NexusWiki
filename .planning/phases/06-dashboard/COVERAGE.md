# Phase 6 — API Coverage Matrix

Two capability surfaces are freshly consumed by `apps/dashboard` for the first time in this
phase: Supabase Auth (via `@supabase/ssr`) and the already-built `apps/api` FastAPI backend
(Phase 5). Both matrices start from full coverage; every `OPT-OUT` below cites a concrete
reason grounded in `06-CONTEXT.md` decisions or `06-UI-SPEC.md`'s explicit copy contract (if a
screen/copy row doesn't exist for a capability, the capability has no UI surface to attach to).

## Supabase Auth

| capability | decision | reason |
|---|---|---|
| `sign_in_with_password` | INTEGRATE | D-01, UI-01 — the only supported login method |
| `get_user` / session read | INTEGRATE | Required by `middleware.ts` (D-02) and every RSC direct-read page to attach the requester JWT |
| `sign_out` | INTEGRATE | Not called out by a UI-SPEC copy row, but a session-ending affordance is basic usability once login exists; added under `06-01-PLAN.md`'s nav-shell discretion with a plain "로그아웃" label |
| `sign_up` (self-service) | OPT-OUT | No signup copy exists in `06-UI-SPEC.md`'s Copywriting Contract; accounts are provisioned outside the dashboard (Studio/admin), matching `06-03-PLAN.md`'s invite flow (invitee already has an account) |
| `reset_password_for_email` | OPT-OUT | Not in D-01/UI-SPEC scope; no "비밀번호를 잊으셨나요" copy row exists |
| `verify_otp` / email confirmation UI | OPT-OUT | Enforced server-side already (`01-CONTEXT.md` D-hardening, BOOT-10); no dashboard UI needed because self-service signup (which would trigger it) is itself out of scope |
| `sign_in_with_otp` (magic link) | OPT-OUT | D-01 explicitly excludes magic link |
| OAuth providers | OPT-OUT | D-01 explicitly excludes OAuth |
| MFA (`mfa.enroll` etc.) | OPT-OUT | Not mentioned in D-01/CONTEXT; no MFA copy in UI-SPEC |
| Phone auth | OPT-OUT | D-01 is email+password only |

## `apps/api` (FastAPI backend, Phase 5 — consumed as-is per `06-CONTEXT.md` Phase Boundary)

| capability | decision | reason |
|---|---|---|
| `POST /workspaces/{id}/sources/{text, file, url}` | INTEGRATE | UI-03 dropzone (D-06) |
| `GET /workspaces/{id}/sources/{raw_source_id}/jobs` | INTEGRATE | UI-03 job stepper (D-05) |
| `POST /workspaces/{id}/jobs/{job_id}/retry` | INTEGRATE | UI-03, D-08 (dead-job retry) |
| `POST /workspaces/{id}/jobs/{job_id}/cancel` | INTEGRATE | UI-03, UI-SPEC "잡 취소" destructive-confirmation copy row |
| `GET /workspaces/{id}/budget` | OPT-OUT | No dedicated budget/usage display screen exists in UI-SPEC; the 402 rejection copy at ingest time is the only budget-related surface in scope |
| `POST /workspaces/{id}/ask` (SSE) | INTEGRATE | UI-04 Ask UI |
| `PATCH /workspaces/{id}/wiki/{wiki_id}/verify` | INTEGRATE | UI-05 verification callout action (QC-02 exposure) |
| `GET /workspaces/{id}/graph` (`wiki_graph_neighborhood` RPC) | OPT-OUT | UI-06's canvas uses direct `wiki_pages`/`wiki_links` PostgREST reads to honor the 1000-row cap; the neighborhood RPC's own 200-row cap serves a different single-seed-explore case. See `06-08-PLAN.md`. |
| `POST /workspaces/{id}/retrieval` | OPT-OUT | UI-04 uses `/ask` exclusively (which calls retrieval internally); no "raw search results" screen exists in UI-SPEC |
| `PATCH /workspaces/{id}` (rename) | OPT-OUT | No "워크스페이스 이름 변경" copy in UI-SPEC; D-04 scopes the settings page to the invite form only |
| `DELETE /workspaces/{id}` (delete workspace) | OPT-OUT | No delete-workspace copy/flow in UI-SPEC; same D-04 scoping as above |

## New backend capability added by this phase (deviation, see `06-03-PLAN.md`)

`workspace_members_list` and `invite_workspace_member` (migration `0014`) are not part of
either surface above — they are a narrowly-scoped SECURITY DEFINER RPC pair this phase adds
because no existing capability (Supabase Auth or `apps/api`) can resolve an email to a
`workspace_members.user_id` (the `auth` schema is not in `supabase/config.toml`'s exposed
`schemas`). Full investigation and rationale: `06-03-PLAN.md` task 1.
