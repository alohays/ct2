---
type: spec
title: "CT2 — Ticket Format Specification"
version: "0.1.0"
---

# CT2 Ticket Format

## Filename Convention

```
{id}-{slug}.md
```

- `id`: Zero-padded three-digit integer (`001`, `002`, … `999`)
- `slug`: Kebab-case summary of the ticket title
- Example: `003-refactor-db-pool.md`

## YAML Frontmatter Schema

```yaml
---
id: "003"
title: "Refactor database connection pooling"
status: backlog          # draft | backlog | in-progress | in-review | rejected | escalated | done
priority: high           # critical | high | medium | low
created: 2026-04-13T10:00:00Z
updated: 2026-04-13T14:30:00Z
sealed: null             # ISO8601 timestamp; set on draft→backlog by ct2-seal; reset to null by ct2-revise
branch: feat/003-db-pool # Git working branch name (see spec/git-workflow.md)
pr: null                 # PR URL; written by ct2-git-submit, reset to null by ct2-revise
review-round: 0          # Current review round; incremented by forge on each rejected→in-progress pickup
duration-bounce-count: 0 # Consecutive duration circuit-breaker bounces since last revise
total-attempts: 0        # Monotonic implementation-attempt counter; survives ct2-revise
estimated-scope: small   # small | medium | large
touched-files:           # Files/directories forge expects to modify (overlap detection)
  - src/db/
  - src/middleware/
  - tests/test_db.py
review-status:           # ⚠ READ-ONLY for reviewers. Only the reconciler updates this field.
  lens-claude:
    status: pending      # pending | approved | rejected
    sidecar: null        # reviews/{id}-cc-r{n}.md (set by reconciler after sidecar is written)
  lens-codex:
    status: pending
    sidecar: null        # reviews/{id}-cx-r{n}.md (set by reconciler after sidecar is written)
verdict: pending         # pending | approved | rejected | escalated
---
```

### Verdict Logic

| Condition                                          | `verdict`   |
|----------------------------------------------------|-------------|
| `lens-claude = approved` AND `lens-codex = approved` | `approved` |
| `lens-claude = rejected` OR `lens-codex = rejected`  | `rejected` |
| `review-round + 1 ≥ max_review_rounds`             | `escalated` |
| `duration-bounce-count + 1 ≥ max_duration_bounces` | `escalated` |
| `total-attempts + 1 ≥ max_total_attempts`           | `escalated` |

### Writer Ownership

Automated roles own their fields exclusively. `ct2-revise` is the one
exception: it is a manual human-triggered recovery tool and resets every field
marked below, bringing the ticket back to its `draft/` shape.

| Field               | Written by                                                                        |
|---------------------|-----------------------------------------------------------------------------------|
| All metadata fields | ct2-helm (at ticket creation)                                                     |
| `status`            | ct2-seal (`draft→backlog`); ct2-forge (`→in-progress`, `→in-review` through `ct2-review-enter`); reconciler (`→done/rejected/escalated`); ct2-review-watchdog (`in-review→escalated`); ct2-revise (`→draft`) |
| `sealed`            | ct2-seal (timestamp); ct2-revise (reset to `null`)                                |
| `review-round`      | ct2-forge (incremented on rejected pickup); ct2-revise (reset to `0`)             |
| `duration-bounce-count` | `ct2-duration-check` (incremented on duration bounce); ct2-revise (reset to `0`) |
| `total-attempts`    | `ct2-duration-check` (incremented on duration bounce; never reset by ct2-revise) |
| `review-status.*`   | reconciler (automatic updates); ct2-revise (reset to `pending` / `null`)          |
| `verdict`           | reconciler (automatic verdicts); ct2-review-watchdog (`escalated` for missing-review SLA breach); ct2-revise (reset to `pending`) |
| `branch`, `pr`      | ct2-forge (via `ct2-git-start` / `ct2-git-submit`); `ct2-revise` resets `pr` to `null` |
| `updated`           | any actor that modifies the ticket                                                |

## Ticket Body Structure

```markdown
## Requirements
<!-- Functional requirements checklist to be satisfied -->
- [ ] Connection pool size must be configurable via environment variable
- [ ] Pool exhaustion must produce a clear error message
- [ ] Existing API interface must remain unchanged

## Constraints
<!-- Hard constraints that forge must not violate -->
- Must maintain Python 3.9+ compatibility
- No new external dependencies (stdlib only)

## Context
<!-- Background information explaining why this work is needed -->
The current hard-coded pool size (10) is a bottleneck under production load.

## Acceptance Criteria
<!-- Completion criteria: all must be satisfied before lens can approve -->
- [ ] All unit tests pass
- [ ] Pool size configurable with default 10, maximum 50
- [ ] No regressions in existing integration tests
```

### Section Rules

- **Requirements**: Functional capabilities to be delivered. Checkboxes optional.
- **Constraints**: Hard limits forge must not violate. Violations are automatic rejection.
- **Context**: Background explanation for forge. Not a requirement — informational only.
- **Acceptance Criteria**: The authoritative completion checklist. All items must be checked before forge moves the ticket to `in-review/`. Reviewers verify these items.
- At `ct2-seal`, Requirements, Constraints, and Acceptance Criteria are hashed
  into `.ct2/reviews/{id}-sealed.md`. Later checkbox completion is allowed, but
  text drift in these sections is a conformance failure unless helm revises and
  reseals the ticket.

## Review Sidecar Format

Stored in `.ct2/reviews/{ticket-id}-{cc|cx}-r{n}.md`. See
`spec/sidecar-format.md`.

## Priority Pickup Order

forge picks tickets from `backlog/` through `ct2-pickup`, which holds the
lifecycle lock before checking the singleton `in-progress/` precondition. The
candidate order is:
1. `critical` first
2. Within same priority: oldest `sealed` timestamp first (FIFO)
3. Tickets with `touched-files` overlapping the current `in-progress` ticket are deferred
