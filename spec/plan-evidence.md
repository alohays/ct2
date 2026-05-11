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

Each plan should include:

- ticket id and review round;
- intended files and commands;
- acceptance criteria mapping;
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
