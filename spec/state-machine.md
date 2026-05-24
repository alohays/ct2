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
| `draft → backlog`             | `ct2-seal` runs      | ct2-helm      | `title`, `priority`, `touched-files`, `## Acceptance Criteria` all present; `ct2-ticket-audit --seal-gate --ticket {id}` passes (see *Seal Gate* below) | none       |
| `backlog → in-progress`       | `ct2-pickup`         | ct2-forge     | lifecycle lock held; `in-progress/` is empty                               | `ct2-git-start` (create branch from base) |
| `in-progress → in-review`     | `ct2-review-enter` after work completion | ct2-forge | All AC checklist items checked `[x]`; `.meta/{id}.in-review` stamped       | `ct2-git-submit` (push, open PR, record `pr:` URL) |
| `in-review → done`            | `ct2-reconcile` verdict | reconciler | `cc sidecar = approved` AND `cx sidecar = approved`                        | `ct2-git-finalize approved` (squash-merge if `git_auto_merge_on_approval`) |
| `in-review → rejected`        | `ct2-reconcile` verdict | reconciler | `cc sidecar = rejected` OR `cx sidecar = rejected`                         | `ct2-git-finalize rejected` (no-op — PR open) |
| `rejected → in-progress`      | `ct2-pickup`         | ct2-forge     | lifecycle lock held; `in-progress/` is empty; `review-round < max_review_rounds` | `ct2-git-start` (checkout existing branch; rework appends commits) |
| `in-review → escalated`       | Circuit breaker      | reconciler    | `review-round + 1 ≥ max_review_rounds`; also sends escalation to helm inbox | `ct2-git-finalize escalated` (comment on PR) |
| `in-review → escalated`       | `ct2-review-watchdog` | watchdog     | missing review sidecar and `now − .meta/{id}.in-review > max_review_duration_min` | send escalation to helm inbox |
| `in-progress → backlog`       | `ct2-duration-check` bounce | ct2-forge | `now − .meta/{id}.started > max_ticket_duration_min`; `duration-bounce-count < max_duration_bounces`; stamp removed on bounce | none (branch preserved for resume) |
| `in-progress → escalated`     | `ct2-duration-check` cap | ct2-forge | `duration-bounce-count + 1 ≥ max_duration_bounces` OR `total-attempts + 1 ≥ max_total_attempts`; also sends escalation to helm inbox | none (branch preserved for human recovery) |
| `escalated → draft`           | `ct2-revise` (manual)| human, via ct2-helm | Archives every `reviews/{id}-*.md` to `reviews/.archive/{ts}-{id}/`; resets frontmatter (`status=draft`, `review-round=0`, `verdict=pending`, `sealed=null`, `pr=null`, nested `review-status.lens-*.*` reset); drops stale `.meta/{id}.started` if present | `ct2-git-cleanup` (close PR, delete local + remote branch) |
| `rejected → draft`            | `ct2-revise --from=rejected` | human, via ct2-helm | Same semantics as `escalated → draft`. Escape hatch when a rejected ticket is stuck outside normal rework (e.g. requirements must be rewritten, not re-implemented). | `ct2-git-cleanup` (close PR, delete local + remote branch) |

> **Invariant**: `done` is reachable **only** when both reviewers have verdict `approved`.
> No automation — including the circuit breaker — may place a ticket into `done` without satisfying this condition.
> `ct2-revise` is a human-triggered escape and deliberately out of the automated pipeline: it is the only way to re-open a terminal `escalated` ticket.

## GitHub Issue Mirror

When `github_integration.enabled: true`, each automated transition invokes
`ct2-issue-mirror` after the local file move and frontmatter update. The mirror
is fail-soft: `gh` failures write `.ct2/.meta/{id}.issue-mirror-pending.json`
and never roll back the CT2 state transition.

| Transition | Mirror action |
|---|---|
| `draft → backlog` | create or update the issue, apply `ct2/backlog`, render status block |
| `backlog/rejected → in-progress` | apply `ct2/in-progress`, render status block |
| `in-progress → in-review` | apply `ct2/in-review`, render status block with PR link |
| `in-review → done` | apply `ct2/done`, render status block, close issue best-effort |
| `in-review → rejected` | apply `ct2/rejected`, render status block |
| `in-review → escalated` | apply `ct2/escalated`, render status block |
| `in-progress → backlog` | apply `ct2/backlog`, render status block |
| `in-progress → escalated` | apply `ct2/escalated`, render status block |
| `escalated/rejected → draft` | apply `ct2/draft`, render status block, post revision note |

## Seal Gate

`ct2-seal` requires that a draft ticket pass a static quality audit before it
becomes a `backlog/` ticket. The check is implemented by
`ct2-ticket-audit --seal-gate --ticket {id}` and runs in-process inside
`ct2-seal`; a non-zero exit aborts the seal with no state move and leaves
the draft in place.

The seal gate is intentionally **static**: it catches cheap, mechanical
failure modes (missing sections, placeholder text, unverifiable acceptance
criteria, self-contradictory constraints) before forge spends a review
round on the ticket. It is **not** an independent semantic plan review and
is not a substitute for one — issue #23's broader goal of a plan-review
gate may add further checks or a separate reviewer later.

The current checks are:

| Check | Pass condition |
|-------|----------------|
| `seal_gate_required_sections` | Ticket body contains `## Requirements`, `## Constraints`, `## Context`, and `## Acceptance Criteria` and each has meaningful text. |
| `seal_gate_touched_files_specific` | `touched-files` is non-empty and contains no whole-field placeholder values (`tbd`, `unknown`, `n/a`, etc.) or trivial entries (`-`, `.`, `*`). |
| `seal_gate_requirements_complete` | At least one Requirements bullet exists and none are weak (under 8 chars, a whole-field placeholder, or contain unambiguous placeholder markers like `TBD`, `TODO`, `FIXME`). The word `unknown` in domain prose is allowed. |
| `seal_gate_constraints_complete` | Same standard as Requirements. |
| `seal_gate_context_complete` | Context section has at least 20 meaningful characters and no unambiguous placeholder markers. |
| `seal_gate_acceptance_criteria_verifiable` | At least one AC checkbox exists, none are weak, and none are pre-checked at seal time. |
| `seal_gate_no_static_contradictions` | Constraints and goals do not contradict on a short list of patterns (forbidding *adding* tests / docs while ACs require them; declaring stdlib-only while requiring `pip install`). Retention-style constraints (e.g. "no tests may be removed") are not contradictions. |

Placeholder detection deliberately uses two scopes: a substring scanner
restricted to unambiguous markers (`tbd`, `todo`, `fixme`, `placeholder`,
`decide later`), and a whole-field matcher that additionally rejects fields
whose entire content is just `unknown`, `n/a`, `?`, `-`, etc.

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

All state transitions use `mv`/`rename(2)` on same-filesystem paths. Compound
transitions with global preconditions, such as the singleton `in-progress/`
slot, must be performed by an authoritative helper such as `ct2-pickup` while
holding the lifecycle lock. Raw role-level check-then-`mv` pickup is
non-conforming because the empty-slot check and the rename would otherwise be a
TOCTOU sequence.

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
| `now − timestamp(.meta/{id}.started) > max_ticket_duration_min` and next bounce `< max_duration_bounces` | Abort forge work; increment `duration-bounce-count` and `total-attempts`; return ticket to `backlog/`; remove the `.started` stamp; log event |
| `now − timestamp(.meta/{id}.started) > max_ticket_duration_min` and next bounce `≥ max_duration_bounces` or next total attempt `≥ max_total_attempts` | Increment counters; move ticket to `escalated/`; send `escalation` message to ct2-helm inbox |
| `now − timestamp(.meta/{id}.in-review) > max_review_duration_min` with missing sidecar | Move to `escalated/`; send `escalation` message to ct2-helm inbox |

> **Note**: The ticket-duration timer reads `.meta/{id}.started` (written by forge at pickup and rework), not the ticket file's mtime. Ticket mtime mutates on every edit and is preserved across `mv`, which makes it an unreliable stopwatch.
> The review-duration timer reads `.meta/{id}.in-review`, written by `ct2-review-enter` when forge hands the ticket to lens review.
