# Phase 4: Hybrid Retrieval and Fusion - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-11
**Phase:** 4-Hybrid Retrieval and Fusion
**Areas discussed:** Golden query set, Fusion policy

---

## Golden Query Set

| Decision | Alternatives considered | Selected |
|---|---|---|
| Evaluation ground truth | Evidence-unit gold labels / human-centered evaluation / hybrid | ✓ Evidence-unit gold labels |
| Query distribution | Real-user scenarios / technique diagnostics / equal hybrid | ✓ Real-user scenarios |
| Evaluation corpus | Fixed representative corpus / per-workspace data / both | ✓ Fixed representative corpus |
| Passing threshold | Required-evidence recovery plus rank / top-k inclusion only / answer quality first | ✓ Required-evidence recovery plus rank |

**Notes:** The set will contain Korean, English, and mixed-language user scenarios. Its version-pinned corpus and evidence labels make regression results reproducible.

---

## Fusion Policy

| Decision | Alternatives considered | Selected |
|---|---|---|
| Policy location | Versioned Python policy / SQL policy / runtime-only configuration | ✓ Versioned Python policy |
| Initial RRF weights | Equal then evidence-based tuning / semantic-heavy fixed weights / per-query heuristics | ✓ Equal then evidence-based tuning |
| Candidate limits | Versioned per-channel over-fetch plus final k / one shared limit / database-selected limits | ✓ Versioned policy constants |
| Policy adoption | Evidence-gated benchmark / ad hoc tuning / production-only experimentation | ✓ Evidence-gated benchmark |

**Notes:** The user selected all recommended options for this area.

---

## the agent's Discretion

- Choose precise metric definitions, initial numeric defaults, corpus fixtures, and benchmark tooling while keeping the recorded decisions reproducible.

## Deferred Ideas

None.
