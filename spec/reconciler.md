---
type: spec
title: "CT2 Reconciler"
version: "0.1.0"
---

# CT2 Reconciler

`ct2-reconcile` is the only automatic tool that moves tickets from
`in-review/` to `done/`, `rejected/`, or `escalated/`.

## Forms

```bash
ct2-reconcile {ticket-id} {round}
ct2-reconcile --discover [project-dir]
ct2-reconcile --project-dir {dir} {ticket-id} {round}
```

Explicit mode reconciles one ticket round. Discovery mode scans
`.ct2/reviews/` for `{id}-cc-r{round}.md` and `{id}-cx-r{round}.md` pairs, then
attempts explicit reconciliation for every pair whose ticket is still in
`in-review/`.

## Preconditions

For ticket id `003` and round `1`, the reconciler requires:

- `.ct2/in-review/003-*.md` exists.
- `.ct2/reviews/003-cc-r1.md` exists.
- `.ct2/reviews/003-cx-r1.md` exists.
- Both sidecars have `verdict: approved` or `verdict: rejected`.

If either sidecar is missing, explicit mode exits successfully without a state
change. If a sidecar verdict is malformed, explicit mode exits non-zero without
a state change.

## Locking

The reconciler creates `.ct2/.meta/{id}-r{round}-reconcile.lock` with
`O_EXCL`. If the lock exists and is owned by a live process with recent mtime,
the reconciler exits successfully without changing state. If the lock is stale,
it may be removed and reacquired.

The lock is removed after a successful or failed reconciliation attempt by the
process that acquired it.

## Verdict Logic

| Sidecar verdicts | Ticket result |
|---|---|
| `cc=approved` and `cx=approved` | `verdict: approved`, `status: done`, move to `.ct2/done/` |
| either sidecar `rejected`, and `round + 1 < max_review_rounds` | `verdict: rejected`, `status: rejected`, move to `.ct2/rejected/` |
| either sidecar `rejected`, and `round + 1 >= max_review_rounds` | `verdict: escalated`, `status: escalated`, move to `.ct2/escalated/`, send helm escalation |

Single-reviewer approval is never enough for `done/`.

## Frontmatter Writes

The reconciler updates:

- `status`
- `updated`
- `verdict`
- `review-status.lens-claude.status`
- `review-status.lens-claude.sidecar`
- `review-status.lens-codex.status`
- `review-status.lens-codex.sidecar`

`ct2-revise` is the only non-reconciler tool that resets these review fields.

## Exit Codes

| Code | Meaning |
|---:|---|
| 0 | Reconciled, skipped because incomplete, skipped because already moved, or skipped because another live reconciler owns the lock. |
| 1 | Argument or project error. |
| 2 | Invalid sidecar verdict or ambiguous ticket state. |

Git finalization is fail-soft: `ct2-git-finalize` failures must not undo a
completed ticket state transition.
