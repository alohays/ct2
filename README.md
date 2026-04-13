# CT2: Context Control Protocol

**Multi-session AI orchestration harness with dual-review workflow.**

CT2 enables multiple AI agent sessions to divide responsibilities and perform long-running autonomous development on a shared codebase. Three role-based sessions — planner, engineer, and reviewer — communicate through a shared `.ct2/` directory, following a Kanban-style ticket state machine and a dual-approval review protocol.

While the user is away, engineer and reviewer sessions autonomously process tickets. The user can plan new work or inspect results at any time through a planner session.

## Architecture

```
User
  │
  ▼
ct2-helm (planner)            ← Interactive: dialogue with user, author tickets
  │ ct2-seal
  ▼
.ct2/backlog/                 ← Shared filesystem (single source of truth)
  │
  ▼
ct2-forge (engineer)          ← Autonomous: picks up tickets, implements, submits
  │
  ▼
.ct2/in-review/
  │
  ├─────────────────────┐
  ▼                     ▼
ct2-lens-cc           ct2-lens-cx
(Claude Code)         (Codex CLI)
  │                     │
  ▼                     ▼
reviews/{id}-cc.md    reviews/{id}-cx.md
  │                     │
  └────────┬────────────┘
           ▼
     reconciler
           │
     ┌─────┼──────────┐
     ▼     ▼          ▼
   done  rejected  escalated
```

**Key design decisions:**

- **File as source of truth** — all state lives in `.ct2/`; no databases, sockets, or message queues
- **Atomic `mv` for state transitions** — eliminates race conditions between concurrent sessions
- **Dual-approval review** — Claude and Codex review independently; both must approve
- **Immutable sidecar verdicts** — reviewers write to `reviews/`, never modify ticket files
- **Zero git footprint** — `.ct2/` is excluded via `.git/info/exclude`, not `.gitignore`

## Quickstart

### Install

```bash
git clone https://github.com/alohays/ct2 ~/.ct2
bash ~/.ct2/install.sh
source ~/.zshrc
```

### Initialize a project

```bash
cd /path/to/your/project
ct2-init
```

### Start sessions

Open separate terminal sessions for each role:

```bash
# Session 1: Planner (interactive)
claude
/ct2:helm

# Session 2: Engineer (autonomous)
claude
/ct2:forge

# Session 3: Reviewer (autonomous)
claude
/ct2:lens-cc

# Session 4: Codex reviewer (daemon)
ct2-lens-cx-daemon /path/to/your/project
```

### Workflow

1. **Plan** — `/ct2:helm` helps you author tickets in `.ct2/draft/`
2. **Seal** — `ct2-seal 001` validates and moves the ticket to `backlog/`
3. **Build** — `ct2-forge` picks up the ticket and implements it autonomously
4. **Review** — `ct2-lens-cc` and `ct2-lens-cx` review independently
5. **Reconcile** — when both approve, the ticket moves to `done/`

## CLI Commands

| Command | Description |
|---------|-------------|
| `ct2-init [dir]` | Initialize `.ct2/` in a project directory |
| `ct2-seal <ticket>` | Validate and move a draft ticket to backlog |
| `ct2-status [dir]` | Display Kanban board, agent heartbeats, and inbox |
| `ct2-lens-cx-daemon <dir>` | Start the Codex reviewer polling daemon |

## Claude Code Skills

| Skill | Role | Loop | Description |
|-------|------|------|-------------|
| `/ct2:helm` | Planner | OFF | Interactive ticket authoring and management |
| `/ct2:forge` | Engineer | ON | Autonomous backlog processing |
| `/ct2:lens-cc` | Reviewer | ON | Idempotent review scan and verdict writing |
| `/ct2:status` | Monitor | — | One-shot state query |

## State Machine

```
draft → backlog → in-progress → in-review → done
                                    │
                              ┌─────┴──────┐
                              ▼            ▼
                          rejected → in-progress  (rework cycle)
                          escalated               (circuit breaker)
```

- **`done`** is reachable only when both reviewers approve
- **`escalated`** triggers when `max_review_rounds` is exceeded — requires human intervention
- All transitions are atomic `mv` operations

## Specifications

Full protocol specifications are in [`spec/`](spec/):

| Document | Description |
|----------|-------------|
| [`spec/directory-structure.md`](spec/directory-structure.md) | `.ct2/` layout |
| [`spec/ticket-format.md`](spec/ticket-format.md) | Ticket YAML frontmatter and body format |
| [`spec/state-machine.md`](spec/state-machine.md) | Kanban state transition rules |
| [`spec/review-protocol.md`](spec/review-protocol.md) | Dual-approval, inbox, and reconciler protocol |

## Requirements

- macOS (primary target) or Linux
- Python 3.9+
- Git 2.5+
- [Claude Code](https://claude.ai/claude-code) (for helm, forge, lens-cc roles)
- [Codex CLI](https://github.com/openai/codex) (for lens-cx daemon, optional)

## License

[MIT](LICENSE)
