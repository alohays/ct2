---
type: spec
title: "CT2 - Codex Full Support PRD"
version: "0.1.0"
---

# CT2 Codex Full Support PRD

This document defines the product direction for making CT2 a first-class
Codex CLI protocol participant, not merely a Claude-first workflow with a Codex
reviewer.
Implementation details that affect protocol behavior are specified in
`spec/codex-runtime-contract.md`.

## Source Evidence

This PRD is grounded in the current repository state and the Codex CLI
capabilities verified on 2026-05-07:

| Evidence | Result |
|----------|--------|
| `codex --version` | `codex-cli 0.128.0` |
| `codex features list` | `goals` enabled, `multi_agent`, `plugins`, `tool_search`, `tool_suggest`, `tool_call_mcp_elicitation`, `browser_use`, `image_generation`, and `apps` available; `default_mode_request_user_input` is not enabled, so request-input must be runtime-gated |
| `codex app-server generate-json-schema --experimental --out <tmpdir>` | includes `thread/goal/*`, `ToolRequestUserInput*`, `item/tool/requestUserInput`, thread, turn, command, fs, model, config, feature, skill, plugin, and MCP schemas |
| OpenAI Codex 0.128.0 release | added persisted `/goal` workflows, app-server APIs, model tools, and runtime continuation controls |
| OpenAI Codex issue #10384 | request-input was reported unavailable in code mode in Codex 0.93; CT2 must therefore preflight and enable the relevant feature when available instead of assuming every local Codex exposes it |
| OpenAI Codex docs | document CLI skills, MCP, app-server, non-interactive mode, subagents, slash commands, sandboxing, and command-line options |

Primary references:

- https://github.com/openai/codex/releases/tag/rust-v0.128.0
- https://github.com/openai/codex/issues/10384
- https://developers.openai.com/codex/skills
- https://developers.openai.com/codex/app-server
- https://developers.openai.com/codex/noninteractive
- https://developers.openai.com/codex/mcp
- https://developers.openai.com/codex/subagents
- https://developers.openai.com/codex/cli/slash-commands
- https://developers.openai.com/codex/cli/reference

## Product Thesis

CT2 should become a file-backed protocol layer that lets Codex run structured,
auditable engineering workflows across interactive, headless, and app-server
runtimes while preserving CT2's core invariants:

- `spec/` remains the source of truth.
- `.ct2/` remains the local runtime state directory.
- State transitions use atomic `mv`.
- Sidecars, tickets, and messages use tmpfile-then-`mv`.
- No external package dependencies are added to CT2 itself.
- Dual review remains independent; no Codex capability may bypass review.

Codex support is successful when a user can choose Codex for planning,
implementation, review, monitoring, long-running goal pursuit, and human
clarification without leaving the CT2 protocol.

## Current State

CT2 already supports Codex in a narrow lane:

- `codex-plugin/skills/ct2-lens-cx/SKILL.md` defines the Codex reviewer role.
- `install.sh` symlinks Codex skills into `$CODEX_HOME/skills`.
- `ct2-lens-cx` dispatches the Codex reviewer through
  `adapters/codex/lens-cx.md`.
- `ct2-reconcile` is the one-shot terminal-state authority after sidecars are
  present.
- `README.md` documents the Codex reviewer path and known limitations.

Gaps:

- Codex does not yet have native `ct2:helm`, `ct2:forge`,
  `ct2:helm-auto-cx`, or `ct2:status` skills.
- CT2 does not yet model Codex thread ids, goal ids, token budgets, or goal
  completion audits.
- Codex goal invocation syntax remains version-sensitive and adapter-owned.
- The Codex "ask user" path is not normalized into CT2's inbox and blocked
  protocols.
- CT2 does not yet package a full Codex plugin with role skills, metadata,
  dependencies, and permission expectations.
- No compatibility gate checks that the installed Codex supports the required
  feature set before starting a Codex role.

## Users And Jobs

| User | Job |
|------|-----|
| Solo engineer | Run CT2 with Codex as planner, implementer, reviewer, or all roles on a local project. |
| Harness operator | Keep long-running ticket execution visible, resumable, and auditable. |
| Reviewer | Use Codex as an independent second opinion without reading Claude's review first. |
| Maintainer | Ship CT2 as an installable Codex plugin with clear preflight and fallback behavior. |
| Enterprise admin | Restrict sandbox, MCP, plugin, network, and app-server transport behavior without breaking CT2. |

## Capability Model

| Codex capability | CT2 use | Guardrail |
|------------------|---------|-----------|
| Skills | Provide `ct2:helm`, `ct2:forge`, `ct2:lens-cx`, `ct2:helm-auto-cx`, and `ct2:status` workflows with progressive disclosure. | Role skills must repeat CT2 writer ownership and atomic write rules. |
| Plugins | Package CT2 as an installable Codex distribution unit with role skills and optional metadata. | Plugin install must not track `.ct2/` or mutate project source. |
| `/goal` | Keep a long-running Codex role focused on a concrete CT2 objective until audited complete, paused, or budget-limited. | Goal completion never moves a ticket to `done`; CT2 state machine remains authoritative. |
| App-server | Drive JSON-RPC thread, turn, goal, approval, input, model, feature, skill, and fs APIs when available. | Prefer stdio or unix socket transports; websocket requires explicit auth. |
| `request_user_input` / `item/tool/requestUserInput` | Ask bounded clarification questions from Codex-driven helm or app-server clients. | Reviewers do not ask humans for approval; unclear review criteria become blocked/rejected sidecars. |
| `codex exec` | Headless one-shot or CI-safe role actions, especially sidecar generation and summaries. | Use least-privilege sandbox; output must be schema-validated for machine writes. |
| `codex review` | Optional extra review aid for diffs or PR-quality checks. | Advisory only; CT2 sidecar verdict remains the authoritative review artifact. |
| MCP | Give Codex access to official docs, GitHub, or project-approved tools. | MCP setup must be explicit and inspectable through config or preflight. |
| Subagents | Optional parallel exploration or implementation inside a Codex role. | Only when explicitly requested or encoded in the ticket; write sets must be disjoint. |
| Images and web search | Support multimodal tickets, docs lookup, screenshots, and current references. | Source attribution is required for external facts; no hidden network dependency in core CT2 scripts. |
| Permissions and sandbox profiles | Run different roles with read-only, workspace-write, or isolated full-access profiles. | Role access rules override convenience; lens roles remain source-read-only. |
| Feature flags | Detect whether `goals`, plugins, tool search, app-server features, and request-input support exist. | Missing features must degrade explicitly rather than silently changing semantics. |

## Product Requirements

### CFS-1: Codex Role Parity

CT2 must provide Codex-native skills for every CT2 role:

- `ct2:helm`: interactive ticket authoring, clarification, sealing guidance,
  inbox triage, and status interpretation.
- `ct2:forge`: backlog pickup, implementation, test execution, AC checking,
  git helper invocation, review waiting, and rework after rejection.
- `ct2:lens-cx`: independent Codex review, sidecar writing, and reconciliation
  after its own sidecar exists.
- `ct2:helm-auto-cx`: Codex-powered autonomous planning that turns an initial
  repository-improvement objective into a bounded set of high-quality sealed
  tickets.
- `ct2:status`: one-shot status report.

Acceptance:

- Each Codex skill has a `SKILL.md` with name, description, role identity,
  allowed writes, forbidden writes, and verification steps.
- Codex skills are installable through `install.sh` and usable from
  `$skill` mentions or implicit invocation.
- Codex roles preserve all writer ownership rules in `spec/ticket-format.md`.

### CFS-2: Goal-Aware CT2 Operation

CT2 must support Codex `/goal` workflows as a role execution accelerator.
A goal is a runtime objective for a Codex thread, not a CT2 state.

Required mappings:

- Helm goal: produce or revise one or more sealed tickets, asking bounded
  user questions whenever product intent, scope, priority, or acceptance
  criteria are unclear.
- Forge goal: drain the goal-scoped ticket set, not just one ticket. It keeps
  running until every in-scope ticket is `done/`, or until a ticket is blocked,
  escalated, paused, or budget-limited with evidence. Tickets already in
  `in-review/` remain part of the goal; forge waits for both reviews and the
  reconciler, then reworks rejected tickets until the CT2 state machine reaches
  a real terminal outcome.
- Lens-cx goal: drain all goal-scoped Codex review work without violating
  independence. Empty `in-review/` is not completion while upstream helm/forge
  work in the same goal scope can still create reviewable tickets; lens-cx waits
  with an `upstream_work_pending` wait record instead of declaring early
  success.
- Helm-auto-cx goal: continuously plan repository-improvement tickets until the
  initial `/goal` completion conditions for ticket count, ticket quality, and
  total planning scope are satisfied.
- Maintenance goal: run an explicit repo-level objective, then produce an
  evidence audit before completion.

Acceptance:

- CT2 documents how to start, inspect, pause, resume, and clear a goal.
- CT2 records enough thread metadata to reconnect a Codex role to its active
  goal.
- CT2 records a goal scope snapshot for multi-ticket goals so "current tickets"
  is auditable and resumable.
- Goal completion requires an audit that maps objective requirements to files,
  commands, tests, PRs, or sidecars.
- Forge and lens-cx goals have explicit wait states for "review pending",
  "upstream work pending", "blocked by clarification", and "budget-limited".
- `update_goal(status=complete)` or `/goal` success never replaces CT2's
  `done/` transition.

### CFS-3: Codex Clarification Bridge

CT2 must normalize Codex user-question capability into the CT2 communication
model.

Acceptance:

- Helm launched by Codex must prefer `request_user_input` for user
  clarification over free-form chat whenever the active runtime exposes it.
- CT2 setup and Codex preflight must detect `default_mode_request_user_input`.
  If it is available but disabled, CT2 enables it for the Codex profile used by
  CT2, or clearly records that the operator declined or policy blocked the
  change.
- App-server clients must implement `item/tool/requestUserInput` handling.
- If request-input is unavailable, Codex roles fall back to `.ct2/inbox/`
  `blocked` or `clarification` messages.
- Lens roles do not ask users to waive review criteria. If a requirement is
  unverifiable, they write a blocking sidecar and optionally message helm.

### CFS-4: Native App-Server Control Plane

CT2 should use app-server control for Codex role sessions when that surface is
available, while keeping CT2 state changes in one-shot protocol tools.

Acceptance:

- A driver can start/resume/fork a Codex thread, set or read a goal, start
  turns, stream events, answer approval/input requests, and update advisory
  runtime metadata.
- The driver stores thread metadata under `.ct2/` using tmpfile-then-`mv`.
- Stdio or unix socket is the default transport. Websocket requires explicit
  token or signed bearer auth.
### CFS-5: Headless And CI-Safe Codex

CT2 must retain a non-interactive path for automated environments.

Acceptance:

- `codex exec` invocations use explicit sandbox flags.
- Machine-written artifacts use `--output-schema` or a post-run validator.
- `codex review` may be used for advisory diff review, but only CT2 sidecars
  can drive CT2 verdicts.
- Headless failures are fail-soft: they log, leave CT2 state intact, and retry
  or escalate through the inbox.

### CFS-6: Review Independence Is Non-Negotiable

All Codex support must preserve the dual-review rule.

Acceptance:

- Lens-cx cannot read `*-cc-r{n}.md` before its own `*-cx-r{n}.md` exists.
- Codex app-server or subagent workflows must not leak partner sidecars into
  the model-visible context before lens-cx writes its sidecar.
- Any future Codex hooks must enforce the same independence rule currently
  enforced for Claude where possible.

### CFS-7: Capability Preflight

CT2 must provide a Codex preflight that explains what is available, degraded,
or unsupported.

Checks:

- `codex --version`
- `codex features list`
- `codex app-server generate-json-schema --experimental --out <tmpdir>`
- `codex mcp list`
- required skill links under `$CODEX_HOME/skills` or repo-scoped skill roots
- sandbox/profile compatibility for the requested role

Acceptance:

- Preflight output names the exact missing capability and the fallback.
- A missing `/goal` feature disables goal mode but does not disable core CT2.
- A disabled `default_mode_request_user_input` feature triggers setup-time
  enablement for the CT2 Codex profile when policy allows it.
- A missing app-server falls back to `codex exec`.

### CFS-8: Controlled Subagent Use

CT2 should use Codex subagents only when there is a clear, bounded parallel
benefit.

Acceptance:

- Subagent usage is opt-in through explicit prompt, ticket field, or future
  protocol configuration.
- Worker write scopes are disjoint.
- Explorer tasks are read-only.
- Parent roles integrate results and remain responsible for CT2 state writes.

### CFS-9: Codex Plugin Packaging

CT2 should be packaged as a Codex plugin when role coverage is complete.

Acceptance:

- Plugin metadata presents CT2 as a protocol, not a generic code assistant.
- Bundled skills declare clear trigger conditions and dependencies.
- Optional `agents/openai.yaml` metadata is used where it improves install,
  display, or dependency handling.
- The plugin does not require external Python packages, databases, or services.

### CFS-10: Observability And Recovery

Codex support must make long-running work inspectable and recoverable.

Acceptance:

- `ct2-status` reports CT2 filesystem state, Codex runtime mode, active thread,
  active goal status, and degraded capability warnings when metadata exists.
- App-server drivers write compact logs under `.ct2/logs/`.
- Paused, budget-limited, failed, and interrupted goals produce actionable
  next steps.
- Recovery never relies on hidden Codex state alone; `.ct2/` remains the
  audit root.

### CFS-11: Helm-Auto-CX Planning Mode

CT2 must add a Codex-native `ct2:helm-auto-cx` role for autonomous planning.
This is not an implementer and not a reviewer. Its job is to improve the target
codebase by continuously discovering valuable work, decomposing it into CT2
tickets, and sealing only tickets that meet the user's initial completion
conditions.

The role starts only from an explicit user `/goal` objective. The initial
objective must define, or the role must elicit:

- the target codebase or subsystem;
- the desired planning horizon;
- the number of tickets to produce, or a measurable stopping rule;
- the quality bar for each ticket;
- allowed and forbidden research sources;
- whether tickets should be sealed automatically or left in `draft/`.

Quality bar:

- each ticket has bounded `touched-files`, testable acceptance criteria, and
  explicit constraints;
- each ticket is small enough for forge to complete and review independently;
- duplicated, overlapping, or speculative tickets are rejected before sealing;
- evidence from code inspection, docs, tests, or user answers is captured in
  the ticket context;
- high-risk or broad ideas are split into investigation tickets before
  implementation tickets.

Acceptance:

- `ct2:helm-auto-cx` has its own Codex skill with role identity, allowed
  writes, forbidden writes, and a goal-completion checklist.
- The role writes a planning ledger under `.ct2/codex/` that maps the user's
  initial `/goal` conditions to produced ticket ids and evidence.
- The role may use request-input for missing strategic constraints, but it
  should continue autonomously once the user's completion conditions are clear.
- The role never edits project source, never writes review sidecars, and never
  moves tickets outside helm-owned draft/seal paths.
- Goal completion requires a final audit showing ticket count, ticket quality
  checks, duplicate/overlap checks, and the exact CT2 state path for every
  produced ticket.

## Roadmap

| Phase | Deliverable | Exit criteria |
|-------|-------------|---------------|
| 0 | Specs and compatibility audit | This PRD plus runtime contract are merged and indexed. |
| 1 | Codex role parity | Helm, forge, lens-cx, helm-auto-cx, and status Codex skills exist and pass scratch CT2 workflow checks. |
| 2 | Goal-aware adapter support | Docs and scripts can start Codex roles with goal guidance, record thread metadata, and preserve multi-ticket goal scope manually or semi-automatically. |
| 3 | Request-input setup | `ct2-init` or `ct2-codex-doctor` can enable `default_mode_request_user_input` for the CT2 Codex profile when available and policy allows it. |
| 4 | App-server driver | CT2 can drive Codex threads, turns, goals, request-input, approvals, and waits while preserving one-shot state mutation. |
| 5 | Plugin distribution | CT2 installs as a Codex plugin with role skills and preflight checks. |
| 6 | Advanced orchestration | Optional subagent work, MCP dependency flows, helm-auto-cx planning ledgers, and richer status surfaces are stable. |

## Success Metrics

- A new project can run CT2 with Codex-only roles for helm, forge, lens-cx,
  helm-auto-cx, and status.
- A long-running Codex `/goal` can survive interruption and resume without
  losing the CT2 ticket objective.
- A forge `/goal` can start with multiple current tickets and keep running
  across implementation, review wait, rejection, rework, and approval until
  every in-scope ticket has a CT2 terminal outcome.
- A lens-cx `/goal` can keep waiting when upstream work is still active and
  complete only after all in-scope Codex reviews are written and reconciled.
- A Codex clarification request reaches a human and records the resulting
  decision in CT2 state.
- `ct2:helm` uses request-input for bounded Q&A when the active Codex runtime
  exposes it.
- `ct2:helm-auto-cx` can produce the requested number and quality of sealed
  repository-improvement tickets from a single initial goal.
- A Codex reviewer sidecar can be generated without reading the Claude sidecar
  first.
- Preflight catches missing or disabled Codex features before work starts.
- No CT2 state transition relies on a non-atomic write.

## Non-Goals

- Replacing the CT2 Kanban state machine with Codex thread status.
- Using `/goal` as a substitute for ticket acceptance criteria or dual review.
- Adding a database, message queue, or external Python dependency.
- Letting `ct2:helm-auto-cx` implement source changes or approve its own plan
  quality without an evidence audit.
- Making the app-server websocket transport the default.
- Letting lens-cx modify project source files.

## Open Questions

- Which Codex thread metadata belongs in `.ct2/codex/` versus advisory
  `.ct2/runtime/` records?
- Should `ct2-init` offer a Codex-only installation profile?
- Should goal token budgets be ticket frontmatter, protocol config, or an
  operator-supplied runtime choice?
- Should multi-ticket forge goals default to a start-time ticket snapshot or a
  live queue that includes tickets added while the goal is active?
- Should `ct2:helm-auto-cx` seal tickets automatically by default, or require
  one final user confirmation before `ct2-seal`?
- Can future Codex hooks enforce lens-cx write boundaries as strongly as
  Claude hooks do today?
- Should Codex app-server control be a bash/Python stdlib script or remain
  an external optional companion?
