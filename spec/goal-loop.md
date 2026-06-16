---
type: spec
title: "CT2 — Goal Loop"
since: "0.4.0"
---

# CT2 Goal Loop

A **goal** is a maintainer objective tracked across a set of CT2 tickets — the
outer loop above the per-ticket pipeline. `bin/ct2-goal` is the
**provider-neutral** owner of goal state; it subsumes the provider-flavoured
`ct2-codex-goal`, which becomes a thin shim. Following the Decision Bridge
precedent (`spec/decision-bridge.md`), the goal record is the single source of
truth and any provider surface (a Codex thread, a TUI render) is a *render* of
it, never a second truth.

Goals are **advisory**: they never gate a verdict and never move ticket state.
Only the reconciler moves tickets. The goal loop's job is to let the planner pull
each terminal ticket's outcome before drafting the next — closing the loop the
reconciler otherwise leaves open.

## Layout

```
.ct2/goals/{slug}/
├── goal.json     # objective, status, stopping rule, optional outcome-check
├── scope.json    # ordered ticket list + completion conditions
├── ledger.jsonl  # append-only event log
└── audit.json    # latest audit (written by `ct2-goal audit`)
```

`ct2-init` creates `.ct2/goals/`. Records are untracked `.ct2/` state.

### goal.json

| Field | Meaning |
|---|---|
| `slug` | Stable goal id (derived from the objective + timestamp, or `--slug`) |
| `objective` | The maintainer objective, verbatim |
| `status` | `open | paused | complete | abandoned` |
| `stopping_rule` | Optional free-text rule for when the goal is done |
| `outcome_check` | Optional shell command `audit` runs; its exit is recorded as evidence |
| `created` / `updated` | UTC timestamps |

### scope.json

| Field | Meaning |
|---|---|
| `slug` | The owning goal |
| `mode` | `snapshot` (captures matching tickets at `start`) or `production` (starts empty; tickets register via `add-ticket`) |
| `ticket_states` | Kanban states captured in snapshot mode |
| `tickets` | Ordered `{id, filename, added, state_at_capture, path_at_capture}` |
| `completion_conditions` | Optional human-readable conditions |

## Commands

```bash
ct2-goal start {objective…} [--slug] [--mode snapshot|production]
  [--stopping-rule …] [--outcome-check CMD] [--ticket-state STATE …]
  [--completion-condition …]
ct2-goal add-ticket {slug} {ticket}   # register a ticket (production mode)
ct2-goal status [--json]
ct2-goal audit {slug}                 # cross-reference scope + run outcome-check
ct2-goal pause {slug}
ct2-goal complete {slug}
ct2-goal abandon {slug}
```

`add-ticket` lets a production-mode goal (which starts with an empty scope)
register each ticket as the planner seals it, making `audit` the outcome tracker.

## Audit

`ct2-goal audit {slug}` cross-references every in-scope ticket against the seven
kanban directories: a ticket in `done/` or `escalated/` is terminal, anything
else is non-terminal. When `outcome_check` is set, `audit` runs the command and
records the exit code through `ct2-evidence verifier` (kind `verifier`,
`ok = exit 0`) — **evidence, never a verdict**. The goal is `complete` when every
in-scope ticket is terminal and the outcome-check (if any) passed. `audit` exits
0 when complete, 1 otherwise, and never moves ticket state.

## Feedback step — pull, never push

The planner **pulls** outcomes; the reconciler never pushes goal messages
(interactive helm reads its inbox only at init, and `helm-auto-cx` has no
inbox-read step, so a pushed message would land unread — and "Agent Owns the
Loop" puts the poll in the planner). At the top of every planning iteration the
planner runs `ct2-goal audit`, reads each newly-terminal in-scope ticket's
final-round sidecars (structured per `spec/sidecar-format.md`), appends an
outcome event to the ledger **before** drafting the next ticket, pauses the goal
and surfaces an escalated in-scope ticket to the user, and stops when the
stopping rule or outcome-check is satisfied. `ct2-reconcile` is untouched —
escalation remains its only helm message.

## Subsumption of ct2-codex-goal

`ct2-codex-goal` is a thin deprecated shim delegating to `ct2-goal`; existing
`.ct2/codex/` goal records migrate to `.ct2/goals/` through the standard
`ct2-migrate` path at the protocol bump (`spec/protocol-surface.md`,
`spec/versioning.md`).
