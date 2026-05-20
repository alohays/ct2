---
type: spec
title: "CT2 — Git Workflow Specification"
version: "0.1.0"
---

# CT2 Git Workflow

CT2 couples the Kanban ticket lifecycle to a git branch + PR lifecycle so that
`done/` in the ticket state machine corresponds to "merged on the default
branch" (or equivalent) in git history. This spec is the single source of truth
for who touches git, when, and how.

## Design Principles

- **Role boundary**: only `ct2-forge` and the `reconciler` ever invoke git.
  Helm sets intent via the ticket's `branch:` field; lens reads code but never
  writes to git.
- **State parity**: each Kanban state transition has a matching git action
  (or explicit no-op). When the two drift, the ticket state wins.
- **Fail soft**: git/PR failures never corrupt CT2 state. A push that fails
  leaves commits on the local branch; a failed `gh pr create` leaves the branch
  pushed but `pr: null` in the ticket. The reconciler and revise paths treat
  git ops as best-effort.
- **Per-project strategy**: each project picks one git strategy at `ct2-init`.
  All forge/reconciler/revise helpers read `.ct2/config/harness.yaml` and
  no-op when strategy is `none`.

## Strategies

| Strategy             | Branch per ticket | PR opened | Reconciler merges | Use when                                         |
|----------------------|-------------------|-----------|-------------------|--------------------------------------------------|
| `branch-per-ticket`  | Yes               | Yes       | Configurable      | Default. Small teams, OSS contributions, any PR-centric workflow. |
| `direct-to-main`     | No                | No        | No                | Single-author repos with no code review external to CT2.          |
| `none`               | No                | No        | No                | Projects without git (rare; `ct2-init` still works).              |

Strategy is read from `.ct2/config/harness.yaml` key `git_strategy`.

## Role Responsibilities

| Role            | Branch create | Commit | Push | PR open | PR update | PR merge | PR close / branch delete |
|-----------------|:-------------:|:------:|:----:|:-------:|:---------:|:--------:|:------------------------:|
| `ct2-helm`      |               |        |      |         |           |          |                          |
| `ct2-forge`     | ✓             | ✓      | ✓    | ✓       | ✓         |          |                          |
| `ct2-lens-*`    |               |        |      |         |           |          |                          |
| `reconciler`    |               |        |      |         |           | ✓ (opt)  |                          |
| `ct2-revise`    |               |        |      |         |           |          | ✓                        |

- Helm writes the *intent* (`branch:` field in ticket frontmatter) but never
  runs git.
- Lens never touches git; it reviews the working tree as forge left it.
- Merge on approval is configurable (`git_auto_merge_on_approval`). When off,
  the reconciler leaves the PR open for human merge — `done/` in the ticket
  pipeline can thus precede the actual merge on the default branch.

## State-to-Git Map

| Ticket transition                  | Actor      | Git action                                                     |
|------------------------------------|------------|----------------------------------------------------------------|
| `draft → backlog` (ct2-seal)       | helm       | none                                                           |
| `backlog → in-progress` (`ct2-pickup`) | forge  | `ct2-git-start`: checkout existing branch or create from base |
| `rejected → in-progress` (`ct2-pickup`) | forge | `ct2-git-start`: checkout existing branch (commits preserved) |
| in-progress work                   | forge      | `git add/commit [push]` per AC + logical unit                  |
| `in-progress → in-review`          | forge      | `ct2-git-submit`: push, open or update PR, write `pr:` field; `ct2-review-enter` stamps review entry |
| `in-review → done`                 | reconciler | `ct2-git-finalize approved`: squash-merge if `auto_merge` else leave PR open |
| `in-review → rejected`             | reconciler | `ct2-git-finalize rejected`: no-op (PR stays open for rework)  |
| `in-review → escalated`            | reconciler | `ct2-git-finalize escalated`: comment on PR, PR stays open     |
| `in-progress → backlog` (duration CB) | forge   | none (branch kept; next pickup resumes it)                     |
| `escalated/rejected → draft` (ct2-revise) | human | `ct2-git-cleanup`: close PR, delete remote + local branches   |

## Commit Convention

Forge writes commits as **Conventional Commits subject + prose body**:

```
<type>(t-<id>): <imperative subject, ≤50 chars>

<Why this change is needed — not what it does; the diff shows that.
Wrap at 72 chars. Cover the motivation, alternatives considered,
and any constraint that shaped the approach.>

Refs: .ct2/in-progress/<ticket-file>
```

- `type`: `feat | fix | refactor | docs | test | chore | perf | build | ci`
- Scope is always `t-<ticket-id>` (zero-padded), e.g., `t-003`. This gives
  `git log --grep 't-003'` a reliable view of all commits for a ticket.
- Subject: imperative mood (`add`, `fix`, `refactor`). Not past tense.
- Body: explain *why*. Skip if truly trivial (typo fixes).
- `Refs:` trailer lets reviewers jump from commit to ticket.

When `git_commit_trailer_style: structured`, append the global CLAUDE.md
decision-context trailers (`Constraint:`, `Rejected:`, `Confidence:`,
`Scope-risk:`). Default is `none` because these are non-standard outside the
user's own workflow and can surprise external OSS reviewers.

## Commit Granularity

Forge decides granularity with two heuristics, whichever fits first:

1. **AC boundary**: when an AC item flips from `[ ]` to `[x]`, commit.
2. **Logical unit**: when a coherent chunk reaches a stable state
   (refactor extract, new module bootstrapped, tests green in isolation).

This produces PRs whose commit history is a readable timeline. Rework after
a review rejection **appends new commits** — never amends or rebases — so the
PR preserves the full review-round trail. On merge, `git_merge_method: squash`
keeps the default branch tidy while the PR retains the audit history.

## Rework

When forge picks up a `rejected/` ticket (Step 4 of the forge loop),
`ct2-git-start` finds the existing branch and checks it out. No state is
rewritten. Forge addresses every `[BLOCKING]` item from the review sidecars
and pushes new commits to the same branch — the open PR updates
automatically.

## ct2-revise

`ct2-revise` is the manual escape hatch for `escalated/` (and optionally
`rejected/`) tickets. In git terms, it declares "this work was wrong;
discard it." After frontmatter reset, it calls `ct2-git-cleanup` which:

1. Closes the PR if one is open.
2. Deletes the remote branch (`git push origin :<branch>`).
3. Deletes the local branch (`git branch -D <branch>`).
4. Clears the ticket's `pr:` field (back to `null`).

The `branch:` field is kept as-is — when forge re-picks the revised ticket,
`ct2-git-start` will create a fresh branch with the same name.

## Failure Modes

| Situation                                       | Behavior                                                                 |
|------------------------------------------------|--------------------------------------------------------------------------|
| Not a git repo                                 | All `ct2-git-*` helpers no-op with a warning.                            |
| `git_strategy: none`                           | All helpers no-op silently.                                              |
| `gh` CLI missing or not authenticated          | Push succeeds; PR step skipped with a warning. `pr:` stays `null`.       |
| Remote `origin` missing                        | Push step skipped with a warning. Commits remain local.                  |
| Dirty working tree at pickup                   | `ct2-git-start` aborts with guidance to commit/stash. No state change.   |
| `gh pr merge` fails on approval                | Reconciler logs the error. Ticket still moves to `done/`; PR stays open. |

## Invariants

- **No ticket reaches `done/` without both lens verdicts = approved.** Git
  auto-merge is gated on the reconciler's verdict logic; it cannot bypass it.
- **`direct-to-main` implies the PR-based review of CT2 itself is the only
  guard.** Commits still only land on `main` after both lens verdicts pass.
  (Implementation: forge works on `main`, but `ct2-git-submit` is a no-op and
  the reconciler's merge step is skipped.)
- **Git state mirrors ticket state but never drives it.** Lose a branch? The
  ticket is authoritative. Lose a ticket? The branch is garbage-collectible.
