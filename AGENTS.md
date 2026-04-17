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
bash install.sh               # Install: adds to PATH, symlinks skills
ct2-init [dir]                 # Initialize .ct2/ in a project directory
ct2-seal {ticket-id}           # Validate ticket, move draft -> backlog
ct2-revise {ticket-id}         # Archive past sidecars, reset escalated/rejected ticket -> draft
ct2-status [dir]               # Display kanban board + agent state
ct2-lens-cx-tui [dir]           # Start visible Codex reviewer loop
ct2-lens-cx-daemon {project}   # Start legacy headless Codex reviewer daemon
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
| Kanban state machine | `spec/state-machine.md` |
| Ticket YAML + body format | `spec/ticket-format.md` |
| Dual-review + inbox + reconciler | `spec/review-protocol.md` |
| `.ct2/` directory layout | `spec/directory-structure.md` |
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
