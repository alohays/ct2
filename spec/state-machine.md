---
type: spec
title: "CT2 — Kanban State Machine"
version: "0.1.0"
---

# CT2 State Machine

## State Transition Diagram

```
              [Authored by ct2-helm]
                    │
                    ▼
               ┌─────────┐◄────────────────────────── ct2-revise
               │  draft  │──── ct2-helm WIP (in draft/)   (archives sidecars,
               └────┬────┘                                 resets frontmatter)
                    │ ct2-seal (explicit seal by helm)           ▲
                    ▼                                            │
              ┌──────────┐                                       │
              │ backlog  │──── Awaiting forge, priority-ordered  │
              └────┬─────┘                                       │
                   │ forge picks up highest-priority ticket      │
                   ▼                                             │
           ┌─────────────┐                                       │
           │ in-progress │─── duration CB bounce ─► backlog      │
           └──────┬──────┘   (elapsed > max_ticket_duration_min) │
                  │ forge declares completion (all ACs checked)  │
                  ▼                                              │
            ┌──────────┐                                         │
            │ in-review │──── lens-cc + lens-cx review independently│
            └─────┬─────┘     each writes its own sidecar to reviews/
                  │ reconciler confirms both sidecars present    │
        ┌─────────┼──────────────────────────┐                   │
        │                   │                 │                  │
   (both approved)    (any rejected)    (review-round ≥          │
        ▼                   ▼             max_review_rounds)     │
     ┌──────┐         ┌──────────┐       ┌───────────┐           │
     │ done │         │ rejected │       │ escalated │───────────┘
     └──────┘         └────┬─────┘       └───────────┘ ct2-revise
      ↑ Only               │ review-round++     ↑     (human-triggered)
      approved path        └──────► in-progress  │
                                                  └── helm inbox escalation
```

## State Transition Rules

Each automated transition also has a corresponding git action when
`git_strategy: branch-per-ticket`. See `spec/git-workflow.md` for the full
git contract; the "Git action" column summarizes the coupling.

| Transition                    | Trigger              | Actor         | Precondition                                                               | Git action |
|-------------------------------|----------------------|---------------|----------------------------------------------------------------------------|------------|
| `draft → backlog`             | `ct2-seal` runs      | ct2-helm      | `title`, `priority`, `touched-files`, `## Acceptance Criteria` all present | none       |
| `backlog → in-progress`       | Automatic pickup     | ct2-forge     | `in-progress/` is empty; no `touched-files` overlap                        | `ct2-git-start` (create branch from base) |
| `in-progress → in-review`     | Work completion      | ct2-forge     | All AC checklist items checked `[x]`                                       | `ct2-git-submit` (push, open PR, record `pr:` URL) |
| `in-review → done`            | `ct2-reconcile` verdict | reconciler | `cc sidecar = approved` AND `cx sidecar = approved`                        | `ct2-git-finalize approved` (squash-merge if `git_auto_merge_on_approval`) |
| `in-review → rejected`        | `ct2-reconcile` verdict | reconciler | `cc sidecar = rejected` OR `cx sidecar = rejected`                         | `ct2-git-finalize rejected` (no-op — PR open) |
| `rejected → in-progress`      | Automatic pickup     | ct2-forge     | `review-round < max_review_rounds`                                         | `ct2-git-start` (checkout existing branch; rework appends commits) |
| `in-review → escalated`       | Circuit breaker      | reconciler    | `review-round + 1 ≥ max_review_rounds`; also sends escalation to helm inbox | `ct2-git-finalize escalated` (comment on PR) |
| `in-progress → backlog`       | Duration CB bounce   | ct2-forge     | `now − .meta/{id}.started > max_ticket_duration_min`; stamp removed on bounce | none (branch preserved for resume) |
| `escalated → draft`           | `ct2-revise` (manual)| human, via ct2-helm | Archives every `reviews/{id}-*.md` to `reviews/.archive/{ts}-{id}/`; resets frontmatter (`status=draft`, `review-round=0`, `verdict=pending`, `sealed=null`, `pr=null`, nested `review-status.lens-*.*` reset); drops stale `.meta/{id}.started` if present | `ct2-git-cleanup` (close PR, delete local + remote branch) |
| `rejected → draft`            | `ct2-revise --from=rejected` | human, via ct2-helm | Same semantics as `escalated → draft`. Escape hatch when a rejected ticket is stuck outside normal rework (e.g. requirements must be rewritten, not re-implemented). | `ct2-git-cleanup` (close PR, delete local + remote branch) |

> **Invariant**: `done` is reachable **only** when both reviewers have verdict `approved`.
> No automation — including the circuit breaker — may place a ticket into `done` without satisfying this condition.
> `ct2-revise` is a human-triggered escape and deliberately out of the automated pipeline: it is the only way to re-open a terminal `escalated` ticket.

## File-Based State Representation

State is represented by the **directory containing the ticket file**:

| State         | File location                     |
|---------------|-----------------------------------|
| `draft`       | `.ct2/draft/{id}-{slug}.md`       |
| `backlog`     | `.ct2/backlog/{id}-{slug}.md`     |
| `in-progress` | `.ct2/in-progress/{id}-{slug}.md` |
| `in-review`   | `.ct2/in-review/{id}-{slug}.md`   |
| `rejected`    | `.ct2/rejected/{id}-{slug}.md`    |
| `escalated`   | `.ct2/escalated/{id}-{slug}.md`   |
| `done`        | `.ct2/done/{id}-{slug}.md`        |

All state transitions use `mv` (atomic on same-filesystem paths) to eliminate race conditions.

## Reconciler

The reconciler runs as the one-shot `ct2-reconcile` tool. Lens adapters invoke
it after writing their own sidecar; `ct2-reconcile --discover` can also finish
any ticket-round with both sidecars present.

It:

1. Checks whether both `reviews/{id}-cc-r{n}.md` and `reviews/{id}-cx-r{n}.md` exist
2. Uses an `O_EXCL` lockfile to ensure exactly one reconciler instance runs per ticket/round
3. Reads both sidecar verdicts
4. Updates ticket `status`, `review-status`, and `verdict` frontmatter fields
5. Moves the ticket to `done/` or `rejected/` or `escalated/` accordingly

The reconciler is the **sole automatic writer** of `review-status` and `verdict` fields in ticket frontmatter. `ct2-revise` is the only other writer of these fields and is a manual human-triggered escape; see the transition table above.

## Circuit Breaker Conditions

| Condition                                      | Action                                                                 |
|------------------------------------------------|------------------------------------------------------------------------|
| `review-round + 1 ≥ max_review_rounds`         | Move to `escalated/`; send `escalation` message to ct2-helm inbox     |
| `now − mtime(.meta/{id}.started) > max_ticket_duration_min` | Abort forge work; return ticket to `backlog/`; remove the `.started` stamp; log event |

> **Note**: The ticket-duration timer reads `.meta/{id}.started` (written by forge at pickup and rework), not the ticket file's mtime. Ticket mtime mutates on every edit and is preserved across `mv`, which makes it an unreliable stopwatch.
