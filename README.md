# CT2: Context Control Protocol

**Multi-session AI orchestration harness with dual-review workflow.**

![CT2 four-panel comic: chaos becomes file-backed tickets, dual review, and evidence-backed done](docs/assets/ct2-four-panel-comic.png)

CT2 enables multiple AI agent sessions to divide responsibilities and perform long-running autonomous development on a shared codebase. Three role-based sessions — planner, engineer, and reviewer — communicate through a shared `.ct2/` directory, following a Kanban-style ticket state machine and a dual-approval review protocol.

![CT2 filesystem switchyard](docs/assets/ct2-hero-switchyard-labeled.png)

While the user is away, engineer and reviewer sessions autonomously process tickets. The user can plan new work or inspect results at any time through a planner session.

## Architecture

![CT2 protocol map](docs/assets/ct2-protocol-map.svg)

CT2 treats the project-local `.ct2/` directory as the coordination protocol:
tickets move between state directories with atomic `mv`, agents write durable
sidecar files, and the reconciler is the only automatic path into terminal
states.

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

# Session 3: Claude reviewer (autonomous)
claude
/ct2:lens-cc

# Session 4: Codex reviewer (visible TUI)
cd /path/to/your/project
ct2-lens-cx-tui
```

See [Running the Codex TUI reviewer](#running-the-codex-tui-reviewer) below
for attach/detach, tuning, and known Codex quirks.

For Codex-first operation, run the preflight after initialization:

```bash
ct2-codex-doctor
```

It verifies the installed Codex CLI, `/goal` feature flag, app-server schema,
request-input support, MCP list, skill installation, and TUI fallback
requirements. Use `ct2-codex-doctor --enable-request-input` when you want CT2
to enable Codex's `default_mode_request_user_input` feature through the Codex
feature command surface.

### Workflow

1. **Plan** — `/ct2:helm` helps you author tickets in `.ct2/draft/`
2. **Seal** — `ct2-seal 001` validates and moves the ticket to `backlog/`
3. **Build** — `ct2-forge` picks up the ticket and implements it autonomously
4. **Review** — `ct2-lens-cc` and `ct2-lens-cx` review independently
5. **Reconcile** — when both approve, the ticket moves to `done/`

### Running the Codex TUI reviewer

`ct2-lens-cx-tui` is the primary lens-cx path. It launches a tmux session
with two panes:

- **Main pane** — interactive Codex TUI where reviews happen live
- **Bottom pane (10 rows)** — scheduler log with tick timing, heartbeat
  probes, and context resets

The scheduler reads `lens_cx.poll_interval_sec` from
`.ct2/config/harness.yaml` (default 180s) and injects a `ct2:lens-cx` review
tick into the Codex pane every interval, so you can watch each scan and
review iteration happen in real time.

**Operational basics**

From a plain terminal, `ct2-lens-cx-tui` attaches to the CT2 tmux session. If
you run it from inside an existing tmux client, it switches that client to the
CT2 session instead of nesting tmux. Use `--no-attach` to start or reuse the
session without attaching or switching.

```bash
# Detach (leave the session running in the background)
Ctrl-B d

# Re-attach — the same command re-attaches an existing session
ct2-lens-cx-tui /path/to/your/project

# Stop cleanly (session name prints on startup; or use tmux ls)
tmux kill-session -t ct2-lens-cx-<slug>-<hash>
```

**Tunable environment variables**

| Variable | Default | Purpose |
|---|---|---|
| `CT2_LENS_CX_TUI_INTERVAL` | harness / `180` | Tick interval in seconds |
| `CT2_LENS_CX_TUI_INITIAL_DELAY` | `8` | Wait before first tick (lets Codex TUI finish starting) |
| `CT2_LENS_CX_TUI_MAX_TICKS` | `500` | Driver exits after N ticks to bound Codex context growth (`0` disables) |
| `CT2_LENS_CX_TUI_CLEAR_EVERY` | `50` | Inject `/clear` every Nth tick to recycle context (`0` disables) |
| `CT2_CODEX_CMD` | `codex` | Codex CLI executable |
| `CT2_CODEX_ARGS` | `--sandbox workspace-write` | Codex startup flags |

**Codex 0.128.0 notes**

- `/ct2:lens-cx` is not a native Codex slash command. The driver pastes
  `$ct2:lens-cx` as a skill mention plus inline fallback instructions, so
  the reviewer works whether or not skill dispatch fires.
- Codex 0.128.0 includes persisted `/goal` workflows and app-server
  `thread/goal/*` schemas. CT2 stores local scope, thread, and ledger metadata
  under `.ct2/codex/`; CT2 ticket state remains authoritative.
- The TUI defaults to `workspace-write`; the reviewer role forbids source-file
  edits at the text-policy level because lens-cx needs to write `.ct2/`
  sidecars and heartbeat files.
- `ct2-lens-cx-daemon` remains available for unattended operation (launchd
  or `nohup`) and invokes `codex exec --sandbox read-only` non-interactively
  with post-run sidecar validation.

**Verify Codex skill installation**

After `install.sh`, confirm the skill symlinks:

```bash
ls -la ~/.codex/skills/ct2-helm
ls -la ~/.codex/skills/ct2-forge
ls -la ~/.codex/skills/ct2-lens-cx
ls -la ~/.codex/skills/ct2-helm-auto-cx
ls -la ~/.codex/skills/ct2-status
```

If missing, re-run `bash ~/.ct2/install.sh` — it's idempotent.

CT2 also ships local Codex plugin metadata at
`codex-plugin/.codex-plugin/plugin.json` and marketplace metadata at
`.agents/plugins/marketplace.json` for Codex plugin workflows.

### Codex goals

Use `ct2-codex-goal` to create CT2-local goal metadata before starting a
long-running Codex role. This captures the ticket scope that makes phrases like
"current tickets" auditable after terminal restarts.

```bash
ct2-codex-goal start ct2-forge "Complete the current CT2 ticket set"
ct2-codex-goal status
ct2-codex-goal pause <goal-slug> ct2-forge
ct2-codex-goal resume <goal-slug> ct2-forge
ct2-codex-goal clear <goal-slug> ct2-forge
```

Then start Codex, set the matching `/goal` objective, and invoke the relevant
skill (`$ct2:helm`, `$ct2:forge`, `$ct2:lens-cx`, `$ct2:helm-auto-cx`, or
`$ct2:status`). Codex goal completion is advisory only; tickets reach `done/`
only through dual approval and the CT2 reconciler.

For app-server control, `ct2-codex-app-driver` can start, resume, or fork a
Codex thread over `stdio://`, set/read/clear the thread goal, optionally start
one turn, fail closed on approvals, map `requestUserInput` to supplied answers
or CT2 inbox fallback, and persist thread/goal metadata under `.ct2/codex/`.

```bash
ct2-codex-app-driver ct2-status "Inspect current CT2 state" --sandbox read-only
ct2-codex-app-driver ct2-forge "Complete current tickets" --resume --turn '$ct2:forge'
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `ct2-init [dir]` | Initialize `.ct2/` in a project directory (prompts for git strategy on first run) |
| `ct2-seal <ticket>` | Validate and move a draft ticket to backlog |
| `ct2-revise <ticket>` | Archive past sidecars and return an escalated/rejected ticket to `draft/` |
| `ct2-status [dir]` | Display Kanban board, agent heartbeats, and inbox |
| `ct2-codex-doctor [dir]` | Preflight installed Codex capabilities and write `.ct2/codex/preflight.json` |
| `ct2-runtime-doctor [dir]` | Probe Codex/Claude/local runtime capabilities and write `.ct2/runtime/capabilities.json` |
| `ct2-baseline [dir]` | Compute the Trust/Evidence/Autonomy/Cost balanced scorecard baseline |
| `ct2-role-run --role <role> -- <cmd>` | Run a role command and append cost/latency telemetry |
| `ct2-cost [dir]` | Summarize `.ct2/telemetry/cost.jsonl` |
| `ct2-evidence ...` | Record stable command, artifact, screenshot, verifier, and hook-event evidence claims |
| `ct2-decision ...` | Create, format, and answer provider-neutral decision bridge records |
| `ct2-policy-compile [dir]` | Emit provider hook declarations and shell validator metadata |
| `ct2-bridge notify ...` | Send notify-only external advisory messages into CT2 inboxes |
| `ct2-plan-audit [dir]` | Verify tickets in active/review/done states have plan evidence or plan-exempt reason |
| `ct2-role-eval [dir]` | Run fixed role-definition eval cases and record role regression results |
| `ct2-vao-pilot [--report-file <path>]` | Run the local VAO phase-completion pilot and preserve runtime evidence |
| `ct2-vao-self-verify [--run-checks]` | Measure VAO completion gates from the self-verification criteria |
| `ct2-codex-goal ...` | Create, inspect, pause, resume, and clear CT2-local Codex goal metadata |
| `ct2-codex-app-driver ...` | Drive Codex app-server thread, goal, turn, request-input, approvals, logs, and metadata |
| `ct2-lens-cx-tui <dir>` | Start the visible Codex TUI reviewer loop |
| `ct2-lens-cx-daemon <dir>` | Start the legacy headless Codex reviewer polling daemon |
| `ct2-git-start <ticket>` | Internal. Create/checkout the ticket's branch (called by forge on pickup) |
| `ct2-git-submit <ticket>` | Internal. Push the branch and open/update the PR (called by forge at in-review) |
| `ct2-git-finalize <verdict> <ticket>` | Internal. Merge/comment on PR per reconciler verdict |
| `ct2-git-cleanup <ticket>` | Internal. Close PR and delete the branch (called by `ct2-revise`) |

## Development Checks

Codex support has stdlib-only regression tests that exercise the CT2/Codex
contract without requiring a live Codex app-server:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 bin/ct2-vao-self-verify --run-checks --json --repo .
python3 -m unittest discover -s tests
python3 -m unittest discover -s tests -p 'test_script_syntax.py'
python3 -m json.tool codex-plugin/.codex-plugin/plugin.json >/dev/null
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
git diff --check
```

The self-verifier and `test_script_syntax.py` discover Python helpers and Bash
entrypoints dynamically, so new scripts are automatically covered without
updating a copied command list.

The unittest suite covers Codex goal scope/audit behavior, request-input
fallbacks, fake-Codex preflight parsing, sidecar validation, `ct2-status`
Codex metadata output, and plugin/skill contract shape.

## Agent Skills

| Skill | Role | Loop | Description |
|-------|------|------|-------------|
| `/ct2:helm` | Planner | OFF | Interactive ticket authoring and management |
| `/ct2:forge` | Engineer | ON | Autonomous backlog processing |
| `/ct2:lens-cc` | Reviewer | ON | Idempotent review scan and verdict writing |
| `$ct2:helm` | Codex planner | OFF | Codex-native ticket authoring and clarification |
| `$ct2:forge` | Codex engineer | ON | Codex-native ticket implementation and goal-scope draining |
| `ct2:lens-cx` / `$ct2:lens-cx` | Codex reviewer | ON | Codex TUI review scan and verdict writing |
| `$ct2:helm-auto-cx` | Codex planner | ON | Goal-driven autonomous repository-improvement ticket planning |
| `/ct2:status` / `$ct2:status` | Monitor | — | One-shot state query |

## State Machine

![CT2 ticket state machine](docs/assets/ct2-state-machine.svg)

- **`done`** is reachable only when both reviewers approve.
- **`escalated`** triggers when `max_review_rounds` is exceeded — requires human
  intervention via `ct2-revise`, which archives past review sidecars and
  returns the ticket to `draft/` for rework.
- **Duration circuit breaker**: if forge holds a ticket longer than
  `max_ticket_duration_min`, it is bounced back to `backlog/` automatically.
  Timer is driven by `.ct2/.meta/{id}.started`, not the ticket file's mtime.
- All transitions are atomic `mv` operations.

## Specifications

Full protocol specifications are in [`spec/`](spec/):

| Document | Description |
|----------|-------------|
| [`spec/directory-structure.md`](spec/directory-structure.md) | `.ct2/` layout |
| [`spec/ticket-format.md`](spec/ticket-format.md) | Ticket YAML frontmatter and body format |
| [`spec/state-machine.md`](spec/state-machine.md) | Kanban state transition rules |
| [`spec/review-protocol.md`](spec/review-protocol.md) | Dual-approval, inbox, and reconciler protocol |
| [`spec/git-workflow.md`](spec/git-workflow.md) | Git branch, commit, PR, and merge lifecycle |
| [`spec/codex-full-support-prd.md`](spec/codex-full-support-prd.md) | Product requirements for first-class Codex support |
| [`spec/codex-runtime-contract.md`](spec/codex-runtime-contract.md) | Technical contract for Codex CLI, `/goal`, app-server, skills, MCP, and request-input integration |

## Product Planning

| Document | Description |
|----------|-------------|
| [`docs/agent-platform-feature-radar-2026-05.md`](docs/agent-platform-feature-radar-2026-05.md) | 2026-05 Codex CLI and Claude Code feature radar, release-note analysis, and CT2 product roadmap proposals |
| [`docs/ct2-product-strategy-2026-05.md`](docs/ct2-product-strategy-2026-05.md) | Bet/risk strategy for CT2 product direction |
| [`docs/ct2-verified-autonomy-os-strategy-2026-05.md`](docs/ct2-verified-autonomy-os-strategy-2026-05.md) | Canonical Verified Autonomy OS integrated plan |
| [`docs/ct2-phase0-bet1-readiness-2026-05.md`](docs/ct2-phase0-bet1-readiness-2026-05.md) | Phase 0 readiness and Bet 1 go/no-go report |
| [`docs/ct2-native-task-mirror-spike-2026-05.md`](docs/ct2-native-task-mirror-spike-2026-05.md) | Advisory-only native task mirror spike result |
| [`docs/ct2-vao-completion-audit-2026-05-11.md`](docs/ct2-vao-completion-audit-2026-05-11.md) | Prompt-to-artifact completion audit for the VAO implementation |
| [`docs/ct2-vao-self-verification-criteria-2026-05-11.md`](docs/ct2-vao-self-verification-criteria-2026-05-11.md) | Measurable checklist and metrics for judging VAO completion/documentation quality |
| [`docs/ct2-vao-full-implementation-self-review-criteria-2026-05-11.md`](docs/ct2-vao-full-implementation-self-review-criteria-2026-05-11.md) | Strict multi-layer self-review checklist and measurable metrics for full VAO implementation claims |
| [`docs/ct2-vao-self-verification-report-2026-05-11.md`](docs/ct2-vao-self-verification-report-2026-05-11.md) | Executed self-verification report with gate scores and caveats |
| [`docs/ct2-verified-autonomy-os-full-phase-audit-2026-05-11.md`](docs/ct2-verified-autonomy-os-full-phase-audit-2026-05-11.md) | Full strategy phase audit confirming local phase-exit evidence and separating it from production claims |
| [`docs/ct2-vao-phase-completion-report-2026-05-11.md`](docs/ct2-vao-phase-completion-report-2026-05-11.md) | Local pilot report showing every VAO phase gate completed with runtime evidence |

## Requirements

- macOS (primary target) or Linux
- Python 3.9+
- Git 2.5+
- tmux (for the visible Codex reviewer loop)
- [Claude Code](https://claude.ai/claude-code) (for helm, forge, lens-cc roles)
- [Codex CLI](https://github.com/openai/codex) 0.128.0+ (for Codex role skills, `/goal`, app-server preflight, and lens-cx)

## License

[MIT](LICENSE)
