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
branch: null             # Git branch; ct2-git-start derives and records it
pr: null                 # PR URL; written by ct2-git-submit, reset to null by ct2-revise
issue: null              # GitHub Issue number; created by ct2-seal or ct2-issue-adopt
issue-url: null          # GitHub Issue URL; written by the issue mirror
issue-source: null       # created | adopted
pr-review:               # GitHub PR review mirror metadata, reserved for PR publication helpers
  lens-cc:
    last-round: null
    review-id: null
    merge-ready-comment-id: null
  lens-cx:
    last-round: null
    review-id: null
    merge-ready-comment-id: null
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
| `issue`, `issue-url`, `issue-source` | `ct2-issue-mirror` (`created`) or `ct2-issue-adopt` (`adopted`); preserved by `ct2-revise` |
| `pr-review.*`      | Reserved for PR publication helpers (`ct2-pr-review`, `ct2-pr-merge-ready`) when GitHub review publication is enabled |
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

## Verification
<!-- Optional: bind ACs to deterministic check commands (helm-authored at draft time) -->
- AC1: `python -m unittest discover -s tests`
- AC2: `python -m mytool --config-check`
```

### Section Rules

- **Requirements**: Functional capabilities to be delivered. Checkboxes optional.
- **Constraints**: Hard limits forge must not violate. Violations are automatic rejection.
- **Context**: Background explanation for forge. Not a requirement — informational only.
- **Acceptance Criteria**: The authoritative completion checklist. All items must be checked before forge moves the ticket to `in-review/`. Reviewers verify these items.
- **Verification** *(optional)*: Binds individual acceptance criteria to
  deterministic check commands, one per line, in the grammar
  ``- AC{n}: `command` `` where `n` is the 1-indexed ordinal of an existing
  `## Acceptance Criteria` checkbox and `command` is a non-empty shell command.
  Helm authors this section at draft time. ACs without a binding remain
  manual / reviewer-judged, and tickets without the section behave exactly as
  before. The bound commands are the substrate for the `ct2-ac-verify`
  iterate-until-green loop; the section is the single canonical AC→command
  binding syntax (no inline directives, no frontmatter list).
- At `ct2-seal`, Requirements, Constraints, and Acceptance Criteria are hashed
  into `.ct2/reviews/{id}-sealed.md`. When a `## Verification` section is
  present it is hashed as a **conditional fourth section** (`verification-sha256`):
  legacy baselines sealed without it never flag drift (absent in both ticket
  and snapshot = ok), but adding, removing, or editing the section after seal —
  including weakening a bound command — surfaces as sealed-baseline drift, so
  forge cannot weaken its own grader mid-loop. Later checkbox completion is
  allowed, but text drift in the sealed sections is a conformance failure unless
  helm revises and reseals the ticket. (Sealing freezes the *commands*, not the
  test files they invoke — a forge can still gut a test post-seal, which is why
  lenses independently judge whether each bound command proves its AC.)
- `ct2-seal` also runs `ct2-ticket-audit --seal-gate --ticket {id}` as a
  static-quality precondition. The seal gate verifies that the four ticket
  sections exist with meaningful text, that `touched-files` is specific,
  that the Requirements/Constraints/AC items are not whole-field
  placeholders, that ACs are unchecked and verifiable, that
  Constraints do not contradict Requirements/ACs on a small set of
  patterns, and — when a `## Verification` section is present — that every
  binding parses as ``- AC{n}: `cmd` `` with a non-empty command and an `n`
  referencing an existing AC checkbox (`seal_gate_verification_binding`). See
  `spec/state-machine.md` § *Seal Gate* for the full pass conditions. A failing
  seal gate leaves the draft in place and exits non-zero from `ct2-seal`.

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

Fresh tickets should leave `branch: null`. `ct2-git-start` derives a
host-clean branch name from the ticket title according to
`trace_hygiene.branch_prefix_pattern`, records the actual branch in this field,
and reuses it on later pickups.
