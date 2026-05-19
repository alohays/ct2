---
type: spec
title: "CT2 — .ct2/ Directory Structure"
version: "0.1.0"
---

# CT2 Directory Structure

All per-project CT2 state lives under `.ct2/` in the project root.
This directory is excluded from git via `.git/info/exclude` (never via `.gitignore`).

## Full Layout

```
.ct2/
├── config/
│   ├── harness.yaml                   # Circuit breaker settings, per-project parameters
│   ├── ct2-lens-cc-role.md            # Claude reviewer role definition (loaded by lens-cc skill)
│   └── ct2-lens-cx-role.md            # Codex reviewer role definition
├── draft/                             # WIP tickets being authored by ct2-helm
├── backlog/                           # Sealed tickets awaiting ct2-forge (priority-ordered)
├── in-progress/                       # Currently being worked on by ct2-forge (one at a time)
├── in-review/                         # Under review by lens sessions
├── rejected/                          # Rejected; awaiting rework by ct2-forge
├── escalated/                         # Circuit breaker triggered — human intervention required
├── done/                              # Both lens sessions approved (sole path to this state)
├── reviews/                           # Reviewer verdict sidecar files (immutable, authoritative)
│   ├── {ticket-id}-cc-r{n}.md        # Claude reviewer verdict sidecar (round n)
│   ├── {ticket-id}-cx-r{n}.md        # Codex reviewer verdict sidecar (round n)
│   └── .archive/                     # Populated lazily by ct2-revise on escalation/rejected rework
│       └── {YYYYMMDDTHHMMSSZ}-{id}/  # One folder per revise operation; holds archived sidecars
├── inbox/                             # Asynchronous message channels between roles
│   ├── ct2-helm/
│   │   ├── processing/                # Claimed messages (atomically renamed here)
│   │   └── done/                      # Acknowledged messages (audit trail)
│   ├── ct2-forge/
│   │   ├── processing/
│   │   └── done/
│   ├── ct2-lens-cc/
│   │   ├── processing/
│   │   └── done/
│   └── ct2-lens-cx/
│       ├── processing/
│       └── done/
├── worktrees/                         # Per-ticket git worktrees (Phase 1.5+)
│   └── {id}-{slug}/
├── runtime/                           # Advisory runtime twin and capability registry
│   ├── capabilities.json              # Written by ct2-runtime-doctor
│   ├── degradations.md                # Human-readable degraded paths
│   ├── provider-hooks/                # ct2-policy-compile output
│   └── artifacts/                     # Runtime probe artifacts
├── evidence/                          # Evidence graph records
│   ├── claims.jsonl                   # Stable evidence claim ids
│   ├── commands/                      # Command/verifier evidence records
│   ├── screenshots/                   # Screenshot evidence metadata
│   ├── verifiers/                     # Machine verifier result records
│   ├── hooks/                         # Provider hook event records
│   └── artifacts/                     # Screenshots, reports, and advisory artifacts
├── telemetry/                         # Scorecard, cost, and event streams
│   ├── baseline-2026-05.json          # Balanced scorecard baseline
│   ├── cost.jsonl                     # ct2-role-run cost/latency sink
│   └── events.jsonl                   # Bridge, watcher, hook, and autonomy events
├── decisions/                         # Provider-neutral user decision records
│   ├── pending/
│   ├── answered/
│   ├── expired/
│   └── audit/
├── plans/                             # Forge plan evidence before execution
│   └── canvas/                        # Helm planning canvases (spec/helm-canvas.md)
│       ├── open/                      # generated, awaiting the user's decision
│       ├── answered/                  # decision token recovered
│       ├── sealed/                    # {ticket}/ — plan evidence after ct2-seal
│       └── expired/                   # superseded or abandoned canvases
├── watchers/                          # Notify-only watcher definitions
├── postmortems/                       # Kill criteria/postmortem records
├── evals/                             # Role eval fixtures and results
│   ├── ct2-helm/
│   ├── ct2-forge/
│   ├── ct2-lens-cc/
│   ├── ct2-lens-cx/
│   └── results.jsonl                  # Role eval run summaries
├── logs/
│   ├── ct2-forge.log
│   └── ct2-lens-cx.log
├── .meta/
│   ├── ct2-active-role                # Current role marker consumed by PreToolUse hooks
│   ├── {id}.started                   # forge pickup stamp; drives duration circuit breaker
│   ├── {id}-r{n}-reconcile.lock       # O_EXCL lockfile held by ct2-reconcile
│   └── circuit-breaker.json           # Reserved for pipeline-wide circuit breaker state
└── .tmp/                              # Atomic write staging area (inbox sends only)
```

## Kanban Directories

| Directory     | State         | Owner         | Description                                        |
|---------------|---------------|---------------|----------------------------------------------------|
| `draft/`      | `draft`       | ct2-helm      | WIP — not yet sealed for forge                    |
| `backlog/`    | `backlog`     | ct2-helm      | Sealed, priority-ordered queue for forge           |
| `in-progress/`| `in-progress` | ct2-forge     | Single ticket, actively being worked               |
| `in-review/`  | `in-review`   | ct2-lens-cc/cx| Awaiting dual-approval review                      |
| `rejected/`   | `rejected`    | ct2-forge     | Failed review; forge reworks before re-submission  |
| `escalated/`  | `escalated`   | ct2-helm      | Circuit breaker — human must intervene             |
| `done/`       | `done`        | immutable     | Both reviewers approved; terminal success state    |

## Invariants

- `done/` is reachable **only** when both `lens-cc` and `lens-cx` verdict = `approved`.
- At most one ticket exists in `in-progress/` at any time.
- `reviews/` sidecar files are **immutable** after creation. Re-reviews produce new files under incremented round numbers.
- State transitions are performed with `mv` (atomic on same-filesystem paths).
- `.tmp/` is the staging area for CT2 atomic file writes, including inbox
  messages, decision records, evidence artifacts, telemetry snapshots, and other
  advisory/evidentiary outputs that use tmpfile-then-rename.
- `runtime/`, `evidence/`, `telemetry/`, `decisions/`, `plans/`, `watchers/`,
  and `evals/` are advisory or evidentiary planes. They never replace the
  Kanban directory as the ticket state authority.

## Git Exclusion

`ct2-init` appends to `.git/info/exclude` (local, not tracked):

```
.ct2/
```

No `.gitignore` modification is made; the project repository remains unmodified.
