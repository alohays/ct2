# CT2

Multi-agent orchestration harness with dual-review workflow.
Development is spec-first: specifications are authoritative, implementations follow.

## Design Principles

- `spec/` is the single source of truth. Read the relevant spec before implementing or modifying any feature.
- **State transitions** use atomic `mv` between directories (never `cp`). This prevents partial states.
- **File writes** (inbox messages, sidecars, tickets) use tmpfile-then-`mv` pattern: write to `.ct2/.tmp/`, then `mv` to final path.
- `.ct2/` runtime directory is excluded via `.git/info/exclude`, not `.gitignore`.
- Only bash and Python stdlib. No external packages, no `pip install`.
- Repo-level `config/` contains default templates. `ct2-init` copies them to `.ct2/config/` per project. Editing `config/` changes defaults for all future projects; editing `.ct2/config/` affects only one project.

## Commands

```bash
bash install.sh                       # Install: adds to PATH, symlinks skills
ct2-init [dir]                         # Initialize .ct2/ in a project directory
ct2-init --install-trace-hook [dir]    # Install a local pre-push hook that runs ct2-trace-lint --strict
ct2-init --bootstrap-issue-labels [dir]  # Create or update CT2 GitHub Issue column labels via gh
ct2-seal {ticket-id}                   # Validate ticket, move draft -> backlog
ct2-helm-canvas {sub} ...              # Generate / recover / seal a helm planning canvas
ct2-revise {ticket-id}                 # Archive past sidecars, reset escalated/rejected ticket -> draft
ct2-status [dir]                       # Display kanban board + agent state
ct2-status --version                   # Print VERSION, plugin versions, install path, and protocol
ct2-lens-cc [dir]                      # Dispatch lens-cc review through an agent adapter
ct2-lens-cx [dir]                      # Dispatch lens-cx review through an agent adapter
ct2-reconcile {id} {round}             # Reconcile independent review sidecars into terminal state
ct2-verify [dir]                       # Run local CT2 protocol conformance checks
ct2-protocol-audit [repo]              # Verify protocol field references are cataloged
ct2-migrate-<from>-<to> [dir]          # Migrate an older .ct2/ ledger after a protocol-version bump
ct2-trace-lint [repo|range]            # Audit host repo for CT2-visible branches, commits, PR bodies
ct2-trace-hygiene-migrate [dir]        # Switch a project's host-clean preset (clean | legacy-branded)
ct2-pr-review {ticket} {sidecar}       # Publish a review sidecar as a GitHub PR review
ct2-pr-merge-ready {ticket}            # Publish a lens merge-ready or reconciler summary PR comment
ct2-pr-respond {ticket}                # Build a forge TODO from unresolved PR review comments
ct2-issue-mirror {ticket}              # Create or update the GitHub Issue mirror for a CT2 ticket
ct2-issue-adopt {issue}                # Adopt an existing GitHub Issue as a CT2 draft ticket
ct2-issue-reconcile [dir]              # Report drift between CT2 tickets and mirrored GitHub Issues
ct2-issue-bootstrap-labels [dir]       # Create or update the CT2 GitHub Issue column labels
ct2-release sync                       # Synchronize derived release artifacts from VERSION
ct2-release prepare {patch|minor|major}  # Bump VERSION, promote CHANGELOG, sync manifests, commit
```

Manual verification: `ct2-init` in a scratch directory, author a ticket, `ct2-seal`, confirm with `ct2-status`.

## Bash & Python Conventions

- Every script starts with `set -euo pipefail`.
- Bin scripts are `ct2-` prefixed. Internal functions use `snake_case`.
- Color output via `GREEN`, `YELLOW`, `RED`, `NC` variables.
- YAML/frontmatter parsing uses Python3 inline heredocs (`python3 -c "import re; ..."`). Never install pyyaml or any pip package.
- Atomic file writes go through `.ct2/.tmp/` before `mv` to destination.

## Specs (read before implementing)

| Topic | File |
|-------|------|
| Top-level CT2 protocol anchor | `spec/PROTOCOL.md` |
| Kanban state machine | `spec/state-machine.md` |
| Ticket YAML + body format | `spec/ticket-format.md` |
| Dual-review + inbox + reconciler protocol | `spec/review-protocol.md` |
| Review sidecar contract | `spec/sidecar-format.md` |
| `ct2-reconcile` contract | `spec/reconciler.md` |
| `.ct2/` directory layout | `spec/directory-structure.md` |
| Git branch/commit/PR lifecycle | `spec/git-workflow.md` |
| Host-repo cleanliness contract + `ct2-trace-lint` JSON surface | `spec/host-repo-cleanliness.md` |
| Versioned protocol surface and migration expectations | `spec/protocol-surface.md` |
| SemVer, pre-1.0 compatibility rules, release flow | `spec/versioning.md` |
| Helm planning canvas (HTML provider format) | `spec/helm-canvas.md` |
| Agent adapter markdown contract | `spec/adapter-format.md` |
| Conformance rules and verification expectations | `spec/conformance.md` |
| Claude reviewer mandate | `config/ct2-lens-cc-role.md` |
| Codex reviewer mandate | `config/ct2-lens-cx-role.md` |

## Boundaries

**Always:**
- Read the relevant spec before making changes.
- Use atomic `mv` for state transitions.
- Include `set -euo pipefail` in all bash scripts.

**Ask first:**
- Modifying any file in `spec/`.
- Changing parameters in `config/harness.yaml` (the repo-level template).
- Adding a new agent role.

**Never:**
- Add external packages or pip dependencies.
- Track `.ct2/` in git.
- Use `cp` for state transitions (must be `mv`).
- Modify frontmatter fields owned by another role (see Writer Ownership in `spec/ticket-format.md`).
