---
phase: 01
slug: bootstrap-and-ground-truth
status: verified
threats_open: 0
threats_total: 64
threats_closed: 64
accepted_risks: 11
asvs_level: 1
block_on: high
created: 2026-08-05
verified: 2026-08-05
---

# Phase 01 — Security Verification

Phase 1's plan-time STRIDE register was checked against the implemented code, tests, migrations, deployment records, and operational probes. All high/critical threats are mitigated. Eleven low/medium risks explicitly marked `accept` in their plans are documented below; none meets the configured `high` blocking threshold.

## Trust Boundaries

| Boundary | Security control |
|---|---|
| External payload → structured logs | Recursive mapping/list/tuple denylist redaction before rendering |
| Browser/API → Supabase | JWT/RLS boundary, strict Storage path parsing, no API service-role secret |
| Worker → Supabase/Railway | Worker-scoped service secret, non-root container, bounded network probes |
| Source tree → build/deploy | Committed lockfiles, frozen installs, scoped hooks, secret-excluding Docker context |
| Cloud bootstrap/auth probes → records | Verdict-only output and sanitized operational evidence |

## Threat Register

| Threat IDs | Category / component | Severity | Disposition | Evidence | Status |
|---|---|---|---|---|---|
| T-01-01…04, T-01-SC | Logging, health, worker lifecycle, Python supply chain | high/medium | mitigate | `logging.py`, logging/health tests, `smoke_tracer.sh`, `uv.lock`, frozen Docker install | closed |
| T-02-01…06 | Storage RLS, object-path validation, migration safety | critical/high/medium/low | mitigate | `0005_storage.sql`, SQL policy tests, `verify_storage_policies.sh` | closed |
| T-03-01…06 | Cloud bootstrap secrets, schema state, auditability | critical/high/medium | mitigate | `cloud-bootstrap-record.md` and ordered migration ledger | closed |
| T-04-01…05 | Auth hardening, cleanup privileges, secret handling | high/medium | mitigate | `config.toml`, `verify_auth_hardening.sh`, `auth-hardening-record.md` | closed |
| T-05-01…04, T-05-SC | Dashboard dependency integrity and public-secret exposure | high/medium | mitigate | exact Next.js lock, telemetry controls, negative secret scan | closed |
| T-06-01…06, T-06-08…09, T-06-SC | Railway secret scope, container hardening, provenance | critical/high/medium | mitigate | `Dockerfile`, `.dockerignore`, deployment record, tracer | closed |
| T-07-01, T-07-03…06 | Tooling integrity, secret hygiene, lint/security enforcement | high/medium | mitigate | pre-commit config, Ruff `S` rules, README and checklist validation | closed |
| T-08-01…07 | RTT secret safety, timeout/measurement integrity, provenance | high/medium | mitigate | `rtt.py`, RTT tests, baseline and deployment records | closed |
| T-09-01…05 | Sequence-nested credential/PII disclosure | high/medium | mitigate | recursive redaction walker, fail-first regressions, full suite and tracer | closed |
| T-01-05 | Shared Settings intentionally absent in tracer scope | low | accept | No credential-bearing Settings object was required in Phase 1 | accepted |
| T-02-SC, T-03-SC, T-04-SC, T-09-SC | No new dependency introduced by these plans | low | accept | Existing locked dependency set used | accepted |
| T-04-06 | Bounded signup probe usage | low | accept | Probe is operator-run and rate-bounded | accepted |
| T-05-05 | Vitest async-RSC limitation | low | accept | Phase test scope uses supported component/unit surfaces | accepted |
| T-06-07 | Mutable base-image and uv tags | medium | accept | Deferred digest pinning; lockfile/frozen install and deployment provenance reduce exposure | accepted |
| T-07-02 | Repository-local system Prettier hook | low | accept | Hook is scoped to the repository and dependency set is locked | accepted |
| T-07-SC, T-08-SC | Reuse of approved locked dependencies | low | accept | No new package acquisition in these plans | accepted |

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---|---|---|---|---|
| AR-01 | T-01-05 | Shared Settings was deliberately outside the tracer slice and no credential-bearing configuration was added. | project plan | 2026-08-05 |
| AR-02 | T-02-SC | Storage work introduced no new dependency. | project plan | 2026-08-05 |
| AR-03 | T-03-SC | Cloud bootstrap introduced no new dependency. | project plan | 2026-08-05 |
| AR-04 | T-04-06 | The operator-only signup probe is bounded and disposable. | project plan | 2026-08-05 |
| AR-05 | T-04-SC | Auth hardening introduced no new dependency. | project plan | 2026-08-05 |
| AR-06 | T-05-05 | Async server-component rendering is outside the Phase 1 Vitest contract. | project plan | 2026-08-05 |
| AR-07 | T-06-07 | Mutable image/tool tags are temporarily accepted with frozen dependencies and deployment provenance. | project plan | 2026-08-05 |
| AR-08 | T-07-02 | Repository-local system Prettier execution is accepted. | project plan | 2026-08-05 |
| AR-09 | T-07-SC | Tooling uses the previously approved lock state. | project plan | 2026-08-05 |
| AR-10 | T-08-SC | RTT uses the existing locked HTTP client. | project plan | 2026-08-05 |
| AR-11 | T-09-SC | Redaction closure introduced no new dependency. | project plan | 2026-08-05 |

## Security Audit Trail

| Audit Date | Threats Total | Mitigated | Accepted | Blocking Open | Run By |
|---|---:|---:|---:|---:|---|
| 2026-08-05 | 64 | 53 | 11 | 0 | gsd-security-auditor |

## Sign-Off

- [x] All threats have a disposition
- [x] Accepted risks are documented
- [x] `threats_open: 0` confirmed at ASVS Level 1
- [x] `status: verified`

**Approval:** verified 2026-08-05
