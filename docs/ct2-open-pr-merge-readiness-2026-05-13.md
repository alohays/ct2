---
type: maintainer-gate
title: "CT2 Open PR Merge Readiness Gate"
date: 2026-05-13
snapshot_utc: 2026-05-12T16:29:03Z
---

# CT2 Open PR Merge Readiness Gate

This gate is intentionally binary. A PR is merge-ready only when every hard
gate below passes. Scores are diagnostics for triage priority, not permission
to merge around a blocker.

## Snapshot Evidence

- Repository: `alohays/ct2`
- Local base refreshed to `origin/main` at `84373a46cd006cd5eb65a4286860e2afbfb2e3e1`
- Open PRs observed: #8, #9, #10, #12
- Baseline verification on current `main`:
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests` -> 52 tests passed
  - `PYTHONDONTWRITEBYTECODE=1 python3 bin/ct2-vao-self-verify --run-checks --json --repo .` -> `complete: true`
- Specs read for this gate:
  - `spec/state-machine.md`
  - `spec/ticket-format.md`
  - `spec/review-protocol.md`
  - `spec/directory-structure.md`
  - `spec/git-workflow.md`
  - `spec/plan-evidence.md`
  - `spec/evidence-graph.md`

## Hard Gates

### G1. Base Freshness And Mergeability

Required evidence:

- PR targets `main` and is not draft.
- Branch is current with `origin/main`, or the check run is proven to have run
  against the current base commit.
- `git merge-tree origin/main <pr-head>` reports no conflicts.
- GitHub merge state is clean or mergeable.
- No stale green checks: CI must be green after the latest base movement.

Metrics:

- `base_lag_commits = 0`
- `conflict_count = 0`
- `required_ci_success = 5/5`
- `draft = false`

### G2. CT2 Spec Invariants

Required evidence:

- State transitions use atomic `mv`; no `cp`-based state transition.
- File writes for tickets, sidecars, inbox messages, telemetry, evidence, and
  decision records use tmpfile-then-`mv` through `.ct2/.tmp/` where the spec
  requires it.
- Directory location remains the source of truth for ticket state.
- No path to `done/` bypasses dual approved lens sidecars.
- Review sidecars stay immutable; re-review creates a new round.
- Writer ownership in `spec/ticket-format.md` is respected.
- Advisory planes (`runtime/`, `evidence/`, `telemetry/`, `decisions/`,
  `watchers/`) never become state authority.
- `.ct2/` remains excluded via `.git/info/exclude`, never tracked or hidden by
  committed `.gitignore`.

Metrics:

- `spec_invariant_violations = 0`
- `tracked_ct2_files = 0`
- `owner_field_violations = 0`
- `advisory_state_mutations = 0`

### G3. Verification Coverage

Required evidence:

- GitHub CI is green for:
  - `unit tests / Python 3.10`
  - `unit tests / Python 3.11`
  - `unit tests / Python 3.12`
  - `unit tests / Python 3.13`
  - `repository validation`
- Maintainer local reproduction passes with `PYTHONDONTWRITEBYTECODE=1`:
  - full unittest discovery
  - `ct2-vao-self-verify --run-checks --json --repo .`
  - all PR-specific targeted tests
  - `git diff --check`
- New commands must pass `--help`, syntax discovery, positive behavior tests,
  and negative false-positive tests.
- No generated `__pycache__` or runtime residue remains in the worktree.

Metrics:

- `local_full_unittest = pass`
- `local_self_verify_complete = true`
- `targeted_test_success = 100%`
- `diff_check = pass`
- `residue_count = 0`

### G4. Review Closure And Maintainer Accountability

Required evidence:

- Every prior blocking review finding is mapped to a commit or an explicit
  non-fix rationale.
- Unresolved review threads are zero.
- In a solo-maintainer repository with no available non-author reviewer, a
  maintainer-authored review trail may satisfy review closure only when all
  blocking findings are resolved, the final evidence is public on the PR, and
  the technical gates in this document are independently reproducible by
  command output.
- For CT2 invariant, command, verifier, or lifecycle changes: the PR body or
  final maintainer note must include both semantic/spec evidence and
  adversarial verification evidence.
- For docs-only visual changes: the PR body or final maintainer note must
  include explicit visual inspection evidence.

Metrics:

- `unresolved_threads = 0`
- `blocking_findings = 0`
- `maintainer_evidence_note = present`
- `solo_maintainer_exception = allowed`

### G5. Scope And Operator Contract

Required evidence:

- PR body names the relevant specs and commands verified.
- Diff scope matches the PR title and does not smuggle unrelated behavior.
- Operator-visible behavior changes have a migration note or no-op proof.
- No external package, pip dependency, or non-stdlib runtime requirement is
  introduced.
- Commit messages preserve the structured decision trailers already used in
  this repo when commits are kept visible.

Metrics:

- `scope_drift_files = 0`
- `new_external_dependencies = 0`
- `migration_note_required_missing = 0`
- `structured_trailer_coverage = 100%`

### G6. README And Visual Asset Gate

Applies to README/image PRs, especially #12.

Required evidence:

- README first viewport still communicates CT2 accurately.
- Every referenced image path exists.
- Alt text matches the actual image content.
- Any embedded text is legible and free of typos, overlap, or AI text artifacts.
- New raster assets are optimized for README load time. Default limit:
  no new README raster asset may exceed the current largest README raster
  asset by more than 25% unless the PR documents an accepted exception.
  Current largest raster on `main`: `docs/assets/ct2-hero-switchyard-labeled.png`
  at about 1.6 MB, so the default cap is about 2.0 MB.
- Generated assets disclose enough provenance in the PR body for maintainers to
  understand and reproduce the intent, even if not byte-for-byte reproducible.

Metrics:

- `broken_image_links = 0`
- `visual_text_defects = 0`
- `asset_size_bytes <= 2.0MB` unless exception accepted
- `alt_text_accuracy = pass`

## PR-Specific Gates

### PR #8: Seal Tickets With Atomic State Moves

Additional required evidence:

- `ct2-seal` never creates a backlog file whose frontmatter still says
  `status: draft`.
- Destination collision preserves the existing backlog file.
- Required-field validation does not move the ticket.
- Frontmatter rewrite is scoped to frontmatter only.
- `.ct2/.tmp/` cleanup is covered.

Current status:

- CI: 5/5 green on the PR head.
- Mergeability: clean against current `origin/main`.
- Base freshness: pass; refreshed onto current `origin/main`.
- Review closure: pass under the solo-maintainer G4 rule; prior blocking
  findings are resolved or outdated, and final evidence is public on the PR.

Next actions:

- Merge after final maintainer spot-check.

### PR #9: Enforce CT2 Local Exclude Contract

Additional required evidence:

- Tracked `.gitignore` rejects every `.ct2` ignore-family pattern.
- `ct2-init` writes exactly one `.ct2/` line to `.git/info/exclude`.
- `ct2-init --repair` is idempotent.
- Linked worktree common-dir behavior is covered.
- Non-git initialization warns and does not create `.gitignore`.
- PR body or final maintainer note tells existing clone users to run
  `ct2-init --repair` if `.ct2/` appears in `git status`.

Current status:

- CI: 5/5 green on the PR head.
- Mergeability: clean against current `origin/main`.
- Base freshness: pass; refreshed onto current `origin/main`.
- Review closure: pass under the solo-maintainer G4 rule; prior findings are
  resolved or outdated, and final evidence is public on the PR.
- Operator note: pass; the PR body now tells existing clone users to run
  `ct2-init --repair` if `.ct2/` appears in `git status`.

Next actions:

- Merge after final maintainer spot-check.

### PR #10: Add Per-Ticket Evidence Audit

Additional required evidence:

- `ct2-ticket-audit` is read-only.
- Done tickets require approved verdict, dual matching sidecars, checked ACs,
  and live evidence claim paths.
- `plan-exempt` is structured frontmatter only, never a body substring.
- Evidence claim matching accepts valid ticket aliases but rejects stale paths,
  unsupported kinds, and failed claims.
- `--json`, human output, and `--ticket` filtering are covered.
- After #7, the PR must not reintroduce stale static verifier target lists.

Current status:

- CI: 5/5 green on the refreshed PR head.
- Mergeability: clean against current `origin/main`.
- Base freshness: pass; refreshed onto current `origin/main`.
- Conflict resolution: pass; `README.md` and `bin/ct2-vao-self-verify`
  conflicts were resolved by keeping dynamic verifier target discovery as the
  source of truth.
- Review closure: pass under the solo-maintainer G4 rule; prior blocking
  findings are resolved or outdated, and final evidence is public on the PR.

Next actions:

- Merge after final maintainer spot-check.

### PR #12: Add CT2 Four-Panel README Hero Comic

Additional required evidence:

- PR is converted from draft only after visual acceptance.
- First README viewport remains useful and not decorative-only.
- Panel captions are exact and unambiguous.
- No caption overlaps subtitles or illustration.
- Asset size meets the README raster budget or carries a documented exception.
- Existing switchyard diagram remains below the opening explanation.

Current status:

- CI: 5/5 green.
- Mergeability: clean against current `origin/main`.
- Draft: pass; PR is ready for review.
- Base freshness: pass; refreshed onto current `origin/main`.
- Review closure: pass under the solo-maintainer G4 rule; final evidence is
  public on the PR.
- Asset size: pass. The optimized JPEG is about 397 KB, below the about 2.0 MB
  default cap.
- Visual inspection: pass. Panel 2's title was redrawn so "goals" is
  unambiguous in the rendered bitmap.

Next actions:

- Merge after final maintainer spot-check.

## Merge Order

Recommended order under this gate:

1. PR #9. It is the narrowest invariant cleanup.
2. PR #8. It is independent of #9 but touches a lifecycle command.
3. PR #10. It adds the operator trust command and should land after the
   verifier-discovery merge already present on `main`.
4. PR #12. It is independent of the code PRs, but rerun merge checks if #10
   lands first because both touch `README.md`.

All open PRs are merge-ready under this solo-maintainer gate snapshot.
