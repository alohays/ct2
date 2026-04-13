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
               ┌─────────┐
               │  draft  │──── ct2-helm WIP (in draft/)
               └────┬────┘
                    │ ct2-seal (explicit seal by helm)
                    ▼
              ┌──────────┐
              │ backlog  │──── Awaiting forge, priority-ordered (in backlog/)
              └────┬─────┘
                   │ forge picks up highest-priority ticket
                   ▼
           ┌─────────────┐
           │ in-progress │──── forge working, at most one at a time (in in-progress/)
           └──────┬──────┘
                  │ forge declares completion (all ACs checked)
                  ▼
            ┌──────────┐
            │ in-review │──── lens-cc + lens-cx review in parallel (in in-review/)
            └─────┬─────┘     each writes its own sidecar to reviews/
                  │ reconciler confirms both sidecars present
        ┌─────────┼──────────────────────────┐
        │                   │                 │
   (both approved)    (any rejected)    (review-round ≥
        ▼                   ▼             max_review_rounds)
     ┌──────┐         ┌──────────┐       ┌───────────┐
     │ done │         │ rejected │       │ escalated │
     └──────┘         └────┬─────┘       └───────────┘
      ↑ Only               │ review-round++     ↑
      approved path        └──────► in-progress  │
                                                  └── helm inbox escalation
```

## State Transition Rules

| Transition                    | Trigger              | Actor         | Precondition                                                               |
|-------------------------------|----------------------|---------------|----------------------------------------------------------------------------|
| `draft → backlog`             | `ct2-seal` runs      | ct2-helm      | `title`, `priority`, `touched-files`, `## Acceptance Criteria` all present |
| `backlog → in-progress`       | Automatic pickup     | ct2-forge     | `in-progress/` is empty; no `touched-files` overlap                        |
| `in-progress → in-review`     | Work completion      | ct2-forge     | All AC checklist items checked `[x]`                                       |
| `in-review → done`            | reconciler verdict   | reconciler    | `cc sidecar = approved` AND `cx sidecar = approved`                        |
| `in-review → rejected`        | reconciler verdict   | reconciler    | `cc sidecar = rejected` OR `cx sidecar = rejected`                         |
| `rejected → in-progress`      | Automatic pickup     | ct2-forge     | `review-round < max_review_rounds`                                         |
| `in-review → escalated`       | Circuit breaker      | reconciler    | `review-round + 1 ≥ max_review_rounds`; also sends escalation to helm inbox |

> **Invariant**: `done` is reachable **only** when both reviewers have verdict `approved`.
> No automation — including the circuit breaker — may place a ticket into `done` without satisfying this condition.

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

The reconciler runs as part of both lens loops. It:

1. Checks whether both `reviews/{id}-cc-r{n}.md` and `reviews/{id}-cx-r{n}.md` exist
2. Uses an `O_EXCL` lockfile to ensure exactly one reconciler instance runs per ticket/round
3. Reads both sidecar verdicts
4. Updates ticket `review-status` and `verdict` frontmatter fields
5. Moves the ticket to `done/` or `rejected/` or `escalated/` accordingly

The reconciler is the **sole writer** of `review-status` and `verdict` fields in ticket frontmatter.

## Circuit Breaker Conditions

| Condition                                      | Action                                                                 |
|------------------------------------------------|------------------------------------------------------------------------|
| `review-round + 1 ≥ max_review_rounds`         | Move to `escalated/`; send `escalation` message to ct2-helm inbox     |
| Ticket processing time > `max_ticket_duration_min` | Abort forge work; return ticket to `backlog/`; log event          |
| No heartbeat for > `heartbeat_timeout_min`     | Session declared dead; warning shown in `ct2-status` output           |
