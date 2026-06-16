---
type: spec
title: "CT2 - Plan Evidence"
version: "0.1.0"
---

# CT2 Plan Evidence

Plan Evidence records the plan-first forge path before execution. The goal is
to let reviewers compare intended scope, touched files, and verification
commands against what actually happened.

## Storage

Plans live under `.ct2/plans/{ticket-id}-r{review-round}.md` or `.json`.

Helm planning canvases live under `.ct2/plans/canvas/{open,answered,sealed,
expired}/` and are governed by `spec/helm-canvas.md`. A sealed canvas
(`canvas/sealed/{ticket}/`) is plan evidence: it records the plan the user
agreed to before the ticket entered `backlog/`.

Each plan should include:

- ticket id and review round;
- intended files and commands;
- acceptance criteria mapping;
- a `## Rework Resolutions` section at review-round `n > 0` referencing each
  `### [BLOCKING]` issue from the round `n-1` sidecars (see
  `spec/review-protocol.md` § *Rework Resolution Contract*);
- explicit `plan-exempt` reason if no plan is required.

## Rules

- Forge produces plan evidence before execution unless a ticket is explicitly
  plan-exempt.
- Reviewers treat missing required plan evidence as a review finding.
- Plan evidence is advisory evidence; it does not move ticket state.

## Audit

`ct2-plan-audit` verifies tickets in `in-progress/`, `in-review/`, and `done/`
have `.ct2/plans/{ticket-id}-r{round}.md`, `.json`, or an explicit
`plan-exempt` reason.
