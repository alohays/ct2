---
type: spec
title: "CT2 - Codex Runtime Contract"
version: "0.1.0"
---

# CT2 Codex Runtime Contract

This document specifies how CT2 should integrate with current Codex CLI
capabilities while preserving CT2's file-backed protocol. It is the technical
counterpart to `spec/codex-full-support-prd.md`.

## Compatibility Baseline

Target baseline:

- Codex CLI: `0.128.0` or newer.
- Required core commands: `codex`, `codex exec`, `codex review`,
  `codex app-server`, `codex features`, `codex mcp`, `codex plugin`.
- Required CT2 scripts: bash plus Python stdlib only.
- Required project state: initialized `.ct2/` directory.

Feature expectations for full support:

| Feature | Required for | Degrade path |
|---------|--------------|--------------|
| `goals` | `/goal` and app-server goal workflows | Run role without goal continuation; keep CT2 ticket state unchanged. |
| `plugins` | Codex plugin packaging | Install skills directly under `$CODEX_HOME/skills` or repo skill roots. |
| `tool_search` | Deferred tool discovery | Continue with explicit tools and MCP list. |
| `tool_suggest` | Optional connector/plugin installation UX | Print manual installation guidance. |
| `tool_call_mcp_elicitation` | MCP/user elicitation flows | Fall back to CT2 inbox blocked messages. |
| `default_mode_request_user_input` | Helm Q&A in ordinary Codex role sessions | During CT2 setup, enable it for the CT2 Codex profile when available and policy allows; otherwise use app-server or plan-mode request-input only when exposed. |
| `multi_agent` | Optional subagent workflows | Single-agent execution. |
| `apps` | Connector/app-backed workflows | Disable app-dependent CT2 enhancements. |

Preflight should treat missing full-support features as degraded capability,
not as corruption. The only hard failures are missing `codex` for a Codex
role, missing `.ct2/`, incompatible sandbox for a required write, or a CT2
state invariant violation.

## Runtime Modes

CT2 recognizes two Codex runtime modes.

| Mode | Current status | Use case | Control surface |
|------|----------------|----------|-----------------|
| `exec` | implemented through adapters | Headless one-shot review or automation | `ct2-lens-cx`, `codex exec`, adapter markdown, schema validation |
| `app-server` | implemented for thread/goal control where available | Local controller without CT2-owned polling | JSON-RPC over stdio or unix socket |

The runtime mode is an execution detail. The CT2 ticket state machine, sidecar
format, inbox protocol, and git workflow do not change by mode.

## Codex Thread Metadata

Future app-server and goal-aware adapter integrations SHOULD persist Codex thread
metadata under `.ct2/` so CT2 can recover after terminal restarts.

Recommended layout:

```
.ct2/
`-- codex/
    |-- threads/
    |   |-- ct2-helm.json
    |   |-- ct2-forge.json
    |   |-- ct2-lens-cx.json
    |   `-- ct2-helm-auto-cx.json
    |-- goals/
    |   `-- {goal-slug}-{role}.json
    |-- scopes/
    |   `-- {goal-slug}.json
    `-- ledgers/
        `-- {goal-slug}-{role}.json
```

Recommended thread record:

```json
{
  "role": "ct2-forge",
  "mode": "app-server",
  "thread_id": "thr_...",
  "cwd": "/absolute/project/path",
  "scope_id": "forge-20260507-current",
  "tickets": ["003-refactor-db-pool.md", "004-fix-cache-tests.md"],
  "goal": {
    "objective": "Complete the current CT2 ticket set through real terminal outcomes.",
    "status": "active",
    "token_budget": 200000,
    "tokens_used": 0,
    "time_used_seconds": 0
  },
  "wait_state": "review_pending",
  "updated": "2026-05-07T00:00:00Z"
}
```

Recommended goal scope record:

```json
{
  "scope_id": "forge-20260507-current",
  "role": "ct2-forge",
  "mode": "snapshot",
  "created": "2026-05-07T00:00:00Z",
  "tickets": [
    {
      "id": "003",
      "path_at_capture": ".ct2/backlog/003-refactor-db-pool.md",
      "terminal_required": "done"
    }
  ],
  "completion_conditions": [
    "all tickets have terminal CT2 state",
    "no in-scope ticket remains in backlog, in-progress, in-review, or rejected"
  ]
}
```

All metadata writes MUST use `.ct2/.tmp/` followed by `mv -n` or `mv` to the
final path. Metadata loss must not corrupt ticket state.

## Goal Contract

Codex 0.128.0 added persisted goal workflows with app-server APIs, model tools,
and runtime continuation. CT2 uses this as a role-local
continuation mechanism.

### Goal API Mapping

App-server goal methods:

- `thread/goal/set`: create, replace, or update a thread goal.
- `thread/goal/get`: read the current persisted goal.
- `thread/goal/clear`: clear the current goal.
- `thread/goal/updated`: goal changed notification.
- `thread/goal/cleared`: goal removed notification.

Observed status enum from the 0.128.0 generated schema:

- `active`
- `paused`
- `budgetLimited`
- `complete`

`thread/goal/set` accepts `threadId` and optional `objective`, `status`, and
`tokenBudget`. `thread/goal/get` returns `objective`, `status`, `tokenBudget`,
`tokensUsed`, `timeUsedSeconds`, `createdAt`, and `updatedAt`. CT2 metadata
uses snake_case for local files, but app-server payloads use Codex's camelCase
schema names.

### Role Objective Templates

Helm:

```
Create or revise CT2 tickets until the user's objective is represented by
sealed, testable tickets. Use CT2 ticket format and ask bounded clarification
questions with request_user_input when requirements are missing.
```

Forge:

```
Complete the CT2 goal scope {scope_id}. Pick up each in-scope backlog or
rejected ticket, implement only the touched-files scope unless a necessary
transitive dependency is discovered, check every acceptance criterion with real
evidence, submit for review, wait for both reviews and reconciliation, and
rework rejected tickets until every in-scope ticket reaches done or an explicit
blocked/escalated/budget-limited outcome is recorded.
```

Lens-cx:

```
Drain Codex reviews for CT2 goal scope {scope_id}. Write independent cx
sidecars for every in-scope ticket that reaches .ct2/in-review/. Do not read cc
sidecars before the matching cx sidecar exists. If no reviewable ticket is
present but upstream in-scope helm/forge work is still active, record
`upstream_work_pending` instead of completing the goal. Reconcile after writing
your own sidecar.
```

Helm-auto-cx:

```
Autonomously plan repository-improvement work for CT2 goal scope {scope_id}.
Continue until the user's initial /goal completion conditions for ticket count,
ticket quality, and total planning coverage are satisfied. Produce a planning
ledger, avoid duplicate or overlapping tickets, ask bounded request_user_input
questions only when the stopping rule or strategic constraints are unclear, and
never edit source files or review sidecars.
```

Maintenance:

```
Complete the stated repository maintenance objective. Before marking the goal
complete, map every requirement to concrete file, command, test, or PR
evidence.
```

### Goal Scope Modes

Multi-ticket roles MUST define whether the goal scope is a snapshot or live
queue.

| Mode | Meaning | Default roles |
|------|---------|---------------|
| `snapshot` | Capture the current matching tickets at goal start; new tickets are ignored unless the user expands the scope. | forge, lens-cx |
| `live` | Continue including tickets that enter the matching state while the goal remains active. | operator-selected forge/lens-cx campaigns |
| `production` | Continue generating new helm-owned tickets until the initial planning completion rule is met. | helm-auto-cx |

The scope file is the audit source for phrases like "current tickets" and
"current reviews". Without a scope file, a driver must reconstruct scope from
the goal transcript before marking completion.

### Goal Supervisor Loop

A CT2 Codex role running with `/goal` behaves as a supervisor:

1. Load or create the role thread and scope metadata.
2. Set or resume the Codex goal.
3. Observe CT2 state directly from `.ct2/`.
4. If work is actionable, start a Codex turn with the next bounded action.
5. If work is not actionable, enter a named wait state and persist metadata.
6. After every turn or wait interval, refresh the goal, CT2 state, and ledger.
7. Before marking goal complete, run a prompt-to-artifact audit against the
   scope completion conditions.

Named wait states:

| Wait state | Applies to | Exit condition |
|------------|------------|----------------|
| `user_input_pending` | helm, helm-auto-cx, forge | request-input answer or inbox clarification arrives |
| `review_pending` | forge | both review sidecars exist and reconciler has moved or updated the ticket |
| `upstream_work_pending` | lens-cx | an in-scope ticket enters `in-review/` or upstream scope becomes terminal |
| `blocked_by_policy` | any | operator changes policy, pauses, or clears the goal |
| `budget_limited` | any | token budget is increased, scope is reduced, or the goal is closed with incomplete evidence |

The supervisor loop must not busy-wait. App-server drivers may use event
notifications plus a bounded sleep; external schedulers may reinvoke one-shot
adapter commands.

### Forge Multi-Ticket Completion

For a forge goal, "complete the current tickets" means:

- every ticket captured in the scope is in `.ct2/done/`, `.ct2/escalated/`, or
  another explicit terminal path approved by the user's initial goal;
- no in-scope ticket remains in `.ct2/backlog/`, `.ct2/in-progress/`,
  `.ct2/in-review/`, or `.ct2/rejected/`;
- every submitted ticket has evidence for acceptance criteria and tests;
- every `rejected/` ticket has either been reworked into review again or
  converted to a documented blocked/escalated outcome.

`in-review/` is not a forge success state for a multi-ticket `/goal`. Forge
must wait for lens-cc and lens-cx to finish, then act on the reconciler result.

### Lens-CX Drain Completion

For a lens-cx goal, "drain the current reviews" means:

- every in-scope ticket that reaches `.ct2/in-review/` has a
  `reviews/{id}-cx-r{round}.md` sidecar;
- the sidecar was written before reading the matching cc sidecar;
- if both sidecars exist, the reconciler has been invoked or the reason it
  could not run is recorded;
- upstream in-scope tickets are terminal, or the goal scope explicitly says
  lens-cx should review only the snapshot already in `in-review/`.

An empty `in-review/` directory is only completion when the scope file proves no
more in-scope upstream work can enter review.

### Helm-Auto-CX Planning Completion

For `ct2:helm-auto-cx`, completion requires a ledger entry for each produced
ticket:

- ticket id and final path;
- which initial goal condition it satisfies;
- touched-files overlap check result;
- quality rubric result;
- source evidence consulted;
- whether the ticket was sealed or left in draft by policy.

The role must stop before sealing if the user's initial goal omitted a ticket
count or stopping rule and request-input is unavailable.

### Goal Completion Rule

Codex goal completion is advisory to CT2. It may end a Codex runtime loop, but
it MUST NOT:

- move a ticket to `done/`;
- mark an AC complete without evidence;
- bypass `ct2-seal`, `ct2-git-submit`, or reconciler logic;
- overwrite ticket frontmatter owned by another role.

For a ticket, the only terminal success remains:

```
cc sidecar verdict = approved
AND
cx sidecar verdict = approved
AND
reconciler moves ticket to .ct2/done/
```

## Human Clarification Contract

Codex has an app-server request-input surface represented by
`ToolRequestUserInputParams` and `ToolRequestUserInputResponse` in the generated
0.128.0 schema. The generated app-server request method is
`item/tool/requestUserInput`, an experimental prompt for one to three short
questions that returns answers.

### Allowed Use

| Role | May ask? | Use |
|------|----------|-----|
| `ct2-helm` | Yes | Clarify product intent, acceptance criteria, priority, touched files, or scope. |
| `ct2-helm-auto-cx` | Yes | Clarify planning horizon, ticket count, quality bar, forbidden areas, or auto-seal policy. |
| `ct2-forge` | Rarely | Only when implementation is blocked by missing requirements; otherwise send inbox `blocked`. |
| `ct2-lens-cx` | No for waivers; yes for operator-level runtime failure only | Review uncertainty becomes a blocking finding, not a user override. |
| `ct2-status` | No | Reports state only. |

### Setup-Time Enablement

Issue openai/codex#10384 documented that `request_user_input` was unavailable
in code mode in older Codex versions. CT2 therefore cannot assume the tool is
globally exposed.

Setup and preflight behavior:

1. Run `codex features list`.
2. If `default_mode_request_user_input` is present and false, enable it for the
   CT2 Codex profile with `codex features enable default_mode_request_user_input`
   or an equivalent app-server `config/batchWrite` edit.
3. If an enterprise requirements file or managed policy forbids the feature,
   record the policy block and continue with inbox fallback.
4. If the feature key is absent, treat request-input as runtime-gated and use
   app-server schema detection or plan-mode availability.
5. Never edit a user's global Codex config by ad hoc text manipulation; use the
   Codex feature/config command surface.

For unattended setup, CT2 may auto-enable the feature for a CT2-specific Codex
profile. For a shared user profile, CT2 should print the exact config change and
record whether it was applied, declined, or blocked.

### Question Shape

CT2-generated questions SHOULD be:

- one to three questions per request;
- short enough for a terminal UI;
- keyed by stable snake_case ids;
- accompanied by two or three mutually exclusive options when possible;
- capable of free-form fallback when the runtime supports it;
- marked secret only for credentials or sensitive input.

### Fallback

When request-input is unavailable, CT2 uses the existing inbox protocol:

- forge -> helm: `blocked`
- lens-cx -> helm: `blocked`
- helm -> forge: `clarification`
- helm-auto-cx -> helm: `blocked`

The fallback message must include the question, why work is blocked, and what
answer shape is expected.

## App-Server Control Contract

The Codex driver uses `codex app-server` where available. The app-server docs
state that schema output is version-specific; CT2 preflight therefore generates
or inspects schemas from the installed Codex binary.

### Transport

Preferred transports:

1. `stdio://` for short-lived local drivers.
2. `unix://` for a local long-lived control socket.
3. `ws://127.0.0.1:PORT` only for localhost or SSH-forwarded development.

Non-loopback websocket MUST NOT be used unless configured with capability-token
or signed bearer-token auth.

### Lifecycle

Minimum app-server sequence:

1. Start `codex app-server --listen stdio://`.
2. Send `initialize` with CT2 client metadata and experimental capability when
   needed.
3. Start or resume a thread with `thread/start` or `thread/resume`.
4. Set the role goal with `thread/goal/set` when goal mode is enabled.
5. Start work with `turn/start`.
6. Stream notifications until `turn/completed`.
7. Respond to approval and `item/tool/requestUserInput` server requests
   according to role policy.
8. Persist wait-state and ledger updates through `.ct2/.tmp/`.
9. Read `thread/goal/get` before deciding whether to continue, pause, or stop.
10. Run the role-specific completion audit before setting status `complete`.

### Request Handling

The driver must handle these request classes explicitly:

- command approval;
- file change approval;
- apply patch approval;
- permissions approval;
- MCP elicitation;
- dynamic tool call;
- `item/tool/requestUserInput`.

Unknown server requests are denied or failed closed unless the driver is in an
operator-interactive mode.

### Request-Input Response Mapping

For app-server request-input, CT2 maps each response to both Codex and CT2:

- reply to Codex with `answers.{question_id}.answers[]`;
- append a compact decision note to the active ticket or planning ledger when
  the answer changes scope, priority, acceptance criteria, or auto-seal policy;
- send inbox `clarification` messages to downstream roles affected by the
  answer;
- redact answers marked `isSecret` from tickets, ledgers, logs, and sidecars.

## Non-Interactive Contract

`codex exec` remains the simplest headless integration.

Required defaults for CT2 scripts:

- Use explicit `--sandbox read-only` for reviewer-only flows.
- Use explicit `--sandbox workspace-write` only for roles allowed to write.
- Avoid `--dangerously-bypass-approvals-and-sandbox` except inside an external
  sandbox controlled by the operator.
- Prefer `--output-schema` for any artifact that CT2 will parse or move.
- Use `--output-last-message` when downstream scripts need a stable final
  response file.
- Use `--json` only when the caller consumes JSONL events robustly.

For lens-cx sidecars, the output validator must check:

- YAML frontmatter exists.
- `reviewer: ct2-lens-cx`.
- `round` equals the ticket's `review-round`.
- `verdict` is `approved` or `rejected`.
- all required markdown sections exist.

Only after validation may the sidecar be moved into `.ct2/reviews/`.

## Skills And Plugin Contract

Codex loads skills from user, repo, system, and admin roots, and skills use
progressive disclosure. CT2 should exploit this by keeping role instructions
small at discovery time and detailed in the role `SKILL.md`.

Required skill fields:

- frontmatter `name`;
- frontmatter `description`;
- identity;
- workflow;
- allowed reads and writes;
- forbidden operations;
- verification steps;
- fallback behavior.

Recommended Codex role skill names:

- `ct2:helm`
- `ct2:forge`
- `ct2:lens-cx`
- `ct2:helm-auto-cx`
- `ct2:status`

Plugin packaging is the distribution layer. The plugin should include role
skills first; optional metadata can be added later for display, dependencies,
and policy hints.

## MCP Contract

CT2 may use Codex MCP servers for documentation, GitHub, or project-specific
tools. MCP configuration belongs to Codex config, not CT2 ticket state.

Rules:

- Preflight reports `codex mcp list`.
- A role skill may recommend an MCP dependency but must have a no-MCP fallback.
- Official docs lookup should prefer Context7 or OpenAI docs when available.
- MCP tool output used as evidence must be cited or summarized in the sidecar
  or ticket notes.

## Subagent Contract

Codex subagents are useful for parallel exploration and bounded implementation,
but they are not CT2 roles. The parent CT2 role owns all CT2 state writes.

Allowed patterns:

- Explorer subagent reads a module and reports risks.
- Worker subagent edits a disjoint file set explicitly assigned by the parent.
- Reviewer subagent performs an advisory review that is not a CT2 sidecar.

Forbidden patterns:

- Subagent writes a review sidecar for lens-cx unless it is the active
  lens-cx runtime and obeys independence.
- Multiple subagents write the same ticket or sidecar path.
- Subagent moves tickets between state directories.
- Subagent reads partner review sidecars before the active reviewer writes its
  own sidecar.

## Sandbox And Permission Profiles

Role defaults:

| Role | Sandbox | Writes |
|------|---------|--------|
| `ct2-helm` | `workspace-write` | `.ct2/draft/`, `.ct2/backlog/` through `ct2-seal`, inbox |
| `ct2-forge` | `workspace-write` | project source, tests, `.ct2/in-progress/`, `.ct2/in-review/`, git helpers |
| `ct2-lens-cx` | `workspace-write` minimum for `.ct2/reviews/`; source-read-only by policy | own cx sidecar, inbox, reconciler-triggered state move |
| `ct2-helm-auto-cx` | `workspace-write` | `.ct2/draft/`, `.ct2/backlog/` through `ct2-seal`, `.ct2/codex/ledgers/`, inbox |
| `ct2-status` | `read-only` | none |

`ct2-lens-cx` needs write access to `.ct2/` but not to source files. If Codex
does not support a split writable-root profile, the role instructions and
future hooks must enforce source-read-only behavior.

`ct2-helm-auto-cx` may read project source and tests for planning evidence, but
it MUST NOT write source files, test files, review sidecars, or git branches.

## Capability Preflight Contract

Future command: `ct2-codex-doctor [project-dir]`.

Minimum checks:

```bash
codex --version
codex features list
codex app-server generate-json-schema --experimental --out <tmpdir>
codex mcp list
test -d .ct2
test -d "${CODEX_HOME:-$HOME/.codex}/skills"
```

Reported fields:

- Codex version.
- Runtime mode support: exec, app-server.
- Goal support and current feature flag state.
- Request-input schema presence and `default_mode_request_user_input` state.
- Whether request-input setup was applied, declined, policy-blocked, or absent.
- Installed CT2 skills.
- Active MCP servers.
- Sandbox/profile compatibility.
- Known degradation path.

## Verification Matrix

| Requirement | Evidence |
|-------------|----------|
| Codex CLI installed | `codex --version` succeeds. |
| Goal support present | `codex features list` contains `goals`; schema contains `ThreadGoal*`. |
| Request-input support present | generated schema contains `ToolRequestUserInput*` and `item/tool/requestUserInput`; feature list reports whether `default_mode_request_user_input` is enabled. |
| Request-input setup works | `ct2-codex-doctor` or setup records applied/declined/policy-blocked state for `default_mode_request_user_input`. |
| App-server protocol available | `codex app-server generate-json-schema --experimental --out <tmpdir>` succeeds. |
| Skills discoverable | CT2 skills visible under `$CODEX_HOME/skills` or repo skill roots. |
| Forge goal drains current tickets | Scratch project has two scoped tickets; forge goal record stays active through `in-review/`, waits for reviews, reworks a rejection, and completes only after terminal CT2 state. |
| Lens-cx goal drains and waits | Scratch project has one immediate review and one upstream in-progress ticket; lens-cx writes independent cx sidecars and does not complete while upstream in-scope work is pending. |
| Helm-auto-cx planning completes | Scratch project goal requests N tickets with a quality bar; planning ledger maps N produced tickets to conditions, overlap checks, and final paths. |
| Lens-cx current path works | `ct2-lens-cx --dry-run` validates adapter dispatch, and `ct2-reconcile` passes sidecar fixtures. |
| No state corruption | scratch `ct2-init`, ticket seal, review sidecar write, and `ct2-status` preserve state invariants. |
| Docs indexed | README spec table links this document and the PRD. |

## Open Implementation Decisions

- Whether CT2 should add `.ct2/codex/` in Phase 1 or wait for app-server
  implementation.
- Whether goal budgets live in ticket frontmatter, protocol config, or runtime
  prompts.
- Whether setup should always create a CT2-specific Codex profile before
  enabling `default_mode_request_user_input`, or mutate the active profile after
  operator confirmation.
- Whether multi-ticket forge and lens-cx goals default to snapshot scope or live
  queue scope.
- Whether `ct2:helm-auto-cx` should auto-seal tickets by default or stop at
  draft plus ledger for human confirmation.
- Whether app-server control should be a Python stdlib client, a bash JSONL
  client, or an optional external package outside CT2 core.
- Whether CT2 should add Codex-specific hooks once plugin-bundled hooks become
  stable enough for role-boundary enforcement.
- Whether Codex lens adapters should move from free-form output validation to
  `--output-schema` first, before the app-server driver exists.
