# CT2 Agent Platform Feature Radar — May–June 2026

Survey date: 2026-06-07 KST / 2026-06-07 US
Target: Anthropic Claude Code (CLI / Agent SDK / Workflows runtime), OpenAI Codex (CLI / app-server / desktop) — the May–June 2026 release window.
Purpose: Map the new agent-native **orchestration surface** (dynamic workflows, ultracode, self-paced loops, budget directives, worktree isolation, native Task/Team, ToolSearch/deferred tools, code-review ultra, deep-research) and the Codex post-0.130.0 line, then translate each into a CT2 opportunity and priority.

Role within the document set: This is the **vendor-surface delta map** that succeeds [`docs/agent-platform-feature-radar-2026-05.md`](agent-platform-feature-radar-2026-05.md) (the prior baseline; this document covers what changed **since** it). The 2026-05 radar anchored CT2 to Codex `0.130.0` and Claude Code `2.1.138`; that baseline is now stale on both fronts and is re-pinned below. This radar **composes with** — does not supersede — the canonical strategic posture in [`docs/ct2-protocol-reframe-2026-05-13.md`](ct2-protocol-reframe-2026-05-13.md), and feeds the candidate backlog that the reframe's adapter/spec tiers will absorb. The two retired-but-foundational strategy docs ([`ct2-verified-autonomy-os-strategy-2026-05.md`](ct2-verified-autonomy-os-strategy-2026-05.md), [`ct2-product-strategy-2026-05.md`](ct2-product-strategy-2026-05.md)) remain the source of the balanced scorecard and the bet/anti-bet vocabulary used here.

> **One-line thesis.** The May–June 2026 window is when the runtimes started **absorbing orchestration itself** — the fan-out, the loop, the pacing, the parallel verify. They did **not** absorb durable verification authority. CT2's durable job is therefore not to orchestrate; it is to be the file-first verification/protocol kernel **above** native workflows: the ledger, the independent dual-review, and the reconciler with sole terminal authority that a workflow must re-enter for its output to count. **Native workflows carry the work; CT2 carries the outcome.**

---

## Executive Summary

Three things changed since the 2026-05 baseline.

1. **Claude Code shipped a deterministic multi-agent orchestrator as a research preview.** "Dynamic workflows" (Claude Code `v2.1.154+`, announced 2026-05-28) let Claude author a deterministic JavaScript orchestration script that a background runtime executes over tens-to-hundreds of subagents, with primitives `agent()` / `parallel()` / `pipeline()` / `phase()` / `log()` / `workflow()`. This is a direct functional twin of CT2's helm/forge/lens fan-out — but **ephemeral and file-less**: intermediate state lives in script variables, the resume journal is session-scoped (exit Claude Code and the workflow restarts fresh), and workflow subagents always run `acceptEdits` with **no mid-run sign-off**. The standing-mode opt-in **ultracode** (`/effort ultracode`) pins `xhigh` reasoning and makes Claude orchestrate by default, with token cost explicitly de-prioritized. This is the central event of the window and the central tension for CT2.

2. **The surrounding Claude Code surface filled in.** Self-paced `/loop` + `Monitor` + scheduled-task cron (`CronCreate/List/Delete`) now own autonomous cadence natively. `ToolSearch`-deferred built-in tools (`v2.1.69`) cut the system-tools context line from ~14–16k to ~968 tokens, so role prompts that assume `Task`/`Monitor`/`SendMessage`/`EnterWorktree` are immediately callable now hit `InputValidationError`. First-class per-subagent `isolation:"worktree"` with auto-cleanup is the community-endorsed fix for parallel-edit merge conflicts. Agent teams (`v2.1.32+`, experimental, default-off) and `/code-review ultra` (cloud multi-agent review, off the local usage window) round out the orchestration menu.

3. **Codex kept its rapid stable cadence but shipped no CT2-style dual-review.** The Codex stable line advanced from `0.130.0` to `0.137.0` (2026-06-04; `0.138.0` still alpha). The most consequential change for CT2 is the `tools.experimental_request_user_input` toggle (`0.136.0`, default false) plus `app-server --stdio`, thread-resume, goals default-on (`0.133.0`), first-class subagents TOML, and a still-dogfood multi-agent v2. Confirmed whitespace: Codex is **not** shipping an independent dual-reviewer or a planner/implementer/reviewer system natively. Read correctly this is not a deficiency on Codex's side but the **shape of CT2's moat**: with the orchestration race running on the Claude side, the cross-vendor pairing becomes a *more* independent check on Claude's fast self-verification, not a less relevant one — Claude's lead is a reason to keep `lens-cx` first-class, never to drift Claude-primary (strategy §3.5).

**The strategic read.** The single loudest May–June 2026 practitioner signal is "speed isn't the bottleneck, correctness is." Anthropic itself names the failure modes its workflows are designed to counter — agentic laziness, self-preferential bias, goal drift — and its **structural** mitigation for self-preferential bias is the one CT2 was built on: split generation from evaluation into separate contexts — and CT2's version is *deeper* than the vendor's own, because separate contexts of the **same** model still share its blind spots, while CT2's `lens-cc` (Claude) AND `lens-cx` (Codex) puts a **different model family** on the evaluation side, the only configuration that actually neutralizes self-preferential bias. CT2 should lead positioning with **verification**, not throughput, because cross-vendor dual-independent review is the trust layer a single vendor structurally cannot ship for itself. The reframe's anti-metric (shrinking reference-implementation LOC) is **not** in conflict with embracing workflows: the embrace lives in the content tier (adapters, role prompts, CT2-blessed workflow templates — explicitly free to grow), while CT2 core gets thinner by retiring hand-rolled loop pacing and serial-safety logic in favor of native primitives. Grow by being adopted; shrink by being unnecessary.

Three invariants survive the fan-out era and **are** CT2's product:

- **State moves only on verified evidence** (the reconciler is the sole terminal authority) — reinforced, not threatened, by the forced-`acceptEdits` / no-sign-off reality.
- **Reviewer independence** — must be upgraded from a session-era no-peek rule to a **prompt-construction invariant** ("a verifier's prompt contains no sibling reviewer's output"), because a parent script now holds every child's return value.
- **The filesystem is the database** — directly answers the workflow's variables-only ephemerality and session-scoped journal; `.ct2/` is the cold-restart rehydration the runtime lacks.
- **Cross-vendor independence is the mechanism, not a parity preference** — dual review is cc (Claude) AND cx (Codex) *by construction*; only a different model family on the evaluation side neutralizes self-preferential bias, so the faster one vendor self-verifies (ultracode), the *more* the independent second vendor is required. This is CT2's founding identity and its moat (strategy **T0** / §3.5), and any M-of-N generalization must keep the floor **cross-vendor**, not any-2.

Recommended order from this document alone: **P0** Declare CT2-above-workflows position + re-pin baselines → **P0** Mandate worktree isolation as the workflow write target (Phase 1.5+) + non-role-holding subagent rule → **P0** Upgrade reviewer independence to a conformance-testable prompt invariant → **P1** Generalize the reconciler to an M-of-N quorum with 2-of-2 as the floor → **P1** Add workflow-class capability detection + an evidence parent/child edge → **P2** Adopt `/code-review ultra` and `/deep-research` as evidence producers (never verdict authorities).

---

## Evidence Base

CT2 distinguishes three confidence tiers throughout: **primary-source-verified** (observed live in the harness or in this repo on 2026-06-07), **official-source-corroborated** (Anthropic/OpenAI docs, GitHub releases/API), and **web-unconfirmed** (secondary blogs, single anecdotes, or claims contradicted by a primary source).

### Primary-source harness observations (Claude Code, observed live 2026-06-07)

Treated as high-confidence ground truth for **capability facts**; version/date anchoring is corroborated separately below. These are observed behaviors, not vendor-published numbers.

| Observation | What was seen | Confidence |
|---|---|---|
| Workflow tool exists | A tool that runs a deterministic JS orchestration script in the background over many subagents; primitives `agent(prompt, opts?)`, `parallel(thunks)` (barrier), `pipeline(items, ...stages)` (per-item streaming, no inter-stage barrier), `phase()`, `log()`, `workflow()` (nested one level). `agent()` returns final text, or a schema-validated object when `opts.schema` is given. | Primary |
| Determinism constraints | `Date.now()` / `Math.random()` / argless `new Date()` disabled (journaled resume); meta block must be a pure literal; plain JS, not TS. Concurrency cap and a lifetime agent cap apply. Resume via `runId` journal (longest unchanged prefix returns cached). | Primary |
| Ultracode standing mode | Typing `ultracode` (or enabling it) makes the assistant author + run a workflow for substantive tasks by default; token cost explicitly not a constraint; multi-phase work → several workflows in sequence (understand → change → verify). | Primary |
| Self-paced loop | Recurring execution that self-paces and can stop itself; distinct from a fixed-interval `/loop` and from remote `/schedule`. | Primary |
| Agent tool (interactive) | Spawn named/addressable subagents; `run_in_background`; `isolation:"worktree"` (own git worktree, auto-cleaned); `SendMessage` to continue an agent with context intact; per-call model override; permission mode; team_name. Subagent types include Explore (read-only), Plan, general-purpose, plus plugin agents. | Primary |
| ToolSearch / deferred tools | Large tool registry deferred; only names appear until `ToolSearch` fetches schemas on demand. Deferred set observed in **this session** includes `CronCreate/List/Delete`, `Monitor`, `Task{Create,Get,List,Output,Stop,Update}`, `Team{Create,Delete}`, `EnterWorktree/ExitWorktree`, `SendMessage`, `WebSearch/WebFetch`, plus many MCP server tools. | Primary |
| Native Task/Team + ultra + deep-research | Native `Task*`/`Team*` primitives, a `/code-review` skill with an `ultra` "deep multi-agent review in the cloud" tier, and a `/deep-research` harness skill are first-class surfaces (visible in the live skill list this session). | Primary |
| Budget object | A workflow `budget` object exposes a token target for loop-until-budget scaling. **See correction below** — whether a directive is a hard run ceiling on Claude Code is *not* primary-confirmed. | Primary (capability) / Unconfirmed (semantics) |

### Official-source corroboration (version & date anchoring)

| Fact | Source | Confidence |
|---|---|---|
| Dynamic workflows shipped as a research preview, announced 2026-05-28, require Claude Code `v2.1.154+`; runtime executes a Claude-authored JS script in the background; intermediate results live in script variables. | `claude.com/blog/introducing-dynamic-workflows-in-claude-code`; `code.claude.com/docs/en/workflows` | Official |
| `pipeline()` streams items through stages with no inter-stage barrier; `parallel()` is a barrier (throwing thunk → null); `workflow()` nests one level. Documented quality patterns: adversarial-verify (N skeptics), judge-panel (N attempts scored + synthesized), loop-until-dry. | `code.claude.com/docs/en/workflows` | Official |
| Workflow subagents **always** run `acceptEdits`, inherit the session tool allowlist regardless of session permission mode, file edits auto-approved; **"No mid-run user input — for sign-off between stages, run each stage as its own workflow."** In `claude -p` / Agent SDK the run starts with no interactive confirmation. | `code.claude.com/docs/en/workflows` | Official |
| `/effort ultracode` = `xhigh` + auto-orchestrate; session-scoped, resets on new session; a single request can become several workflows in a row; keyword trigger was `workflow` before `v2.1.160`, now `ultracode`; disable via `/config`. | `code.claude.com/docs/en/workflows` | Official |
| Self-paced `/loop` (delay chosen dynamically ~1 min–1 hr, can end itself when provably done); fixed interval runs cron; scheduled tasks (`CronCreate/List/Delete`, 5-field cron, 8-char IDs, ≤50/session, 7-day recurring expiry) require `v2.1.72+`; `Monitor` streams a background script's output lines without polling. | `code.claude.com/docs/en/scheduled-tasks` | Official |
| Built-in system tools deferred behind `ToolSearch` as of `v2.1.69`, cutting the system-tools context line from ~14–16k to ~968 tokens; deferred tools appear by name, schemas fetched on demand. (Shipped undocumented; reported via GitHub issue.) | `github.com/anthropics/claude-code/issues/31002` | Official (shipped, undocumented) |
| Agent teams require `v2.1.32+`, experimental, default-off (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`); shared task list with file-locked claiming + dependency markers; `SendMessage` mailbox; `TeammateIdle/TaskCreated/TaskCompleted` hooks; one team per lead, no nesting, no in-process resume. | `code.claude.com/docs/en/agent-teams` | Official |
| Per-subagent `isolation:"worktree"` with auto-cleanup; `EnterWorktree` in-session; worktrees default to `.claude/worktrees/<name>` branching from `origin/HEAD`, configurable via `worktree.baseRef`. | `code.claude.com/docs/en/worktrees` | Official |
| `/code-review ultra` runs deep multi-agent review on Anthropic cloud with dedicated compute that does **not** draw from the local rolling usage window; `--fix` applies findings. | `code.claude.com/docs/en/code-review` | Official |
| Codex stable line: `0.131.0` (2026-05-18) … `0.137.0` (2026-06-04); `0.138.0` alpha-only as of 2026-06-06. `tools.experimental_request_user_input` toggle (default false) added in `0.136.0`; `app-server --stdio` + thread-resume in `0.136.0`; goals default-on since `0.133.0`; first-class subagents TOML (`~/.codex/agents/*.toml`); multi-agent v2 still dogfood defaults through `0.137.0`. | `api.github.com/repos/openai/codex/releases`; `developers.openai.com/codex/{changelog,subagents,config-reference}` | Official |

### Corrections to the primary-source brief (honored)

| Brief claim | Correction | Source |
|---|---|---|
| "`+500k`-style budget directives become a **hard ceiling** shared across the main loop and all workflows." | **Contradicted at the API level.** Anthropic's Task budgets docs state `task_budget` is a **soft hint, not a hard cap**; only `max_tokens` is the enforced per-response ceiling. The Task-budgets feature is in **beta** (Opus 4.8/4.7 only) and **not supported on Claude Code/Cowork surfaces**. The in-harness workflow `budget` object (token target for `loop-until-budget`) is a **distinct** construct; whether a Claude Code workflow treats a token target as a hard run ceiling is **web-unconfirmed and possibly contradicted**. CT2 must **not** promise token-budget enforcement it cannot deliver. | `platform.claude.com/docs/en/build-with-claude/task-budgets` |
| "Workflows / ultracode are stable." | **Research preview / experimental**, not stable. Agent teams are explicitly experimental and default-off. | Official docs above |
| "Workflow subagents may run any permission mode." | Workflow subagents are forced to `acceptEdits` with auto-approved file edits; `acceptEdits` for the **interactive** Agent tool is one selectable mode among several — do not conflate the two surfaces. | Official docs above |

### What remains unconfirmed or web-only (do not freeze spec text on these)

- The literal tool name `ScheduleWakeup`, the `delaySeconds` clamp `[60,3600]`, and the `<<autonomous-loop-dynamic>>` / `<<autonomous-loop>>` sentinels were **not** found verbatim in official docs. The *capability* (self-paced loop choosing a 1-min–1-hr delay, ending itself) **is** confirmed; the literal names are not.
- The exact concurrency formula (`min(16, cores-2)`), the `4096`-items-per-call limit, and `agentType`/`team_name` `agent()` options were not found in official docs. Docs confirm "up to 16 concurrent agents, fewer on limited cores" and "1,000 agents total" only.
- Runaway-token anecdotes (a 90-agent review hitting Max limits; a rumored ~1.7M-token ultracode loop "no refunds") are **single-source / rumor-level**. They are *directionally consistent* with the soft-budget reading but are not corroborated.
- The Bun Zig→Rust rewrite showcase (~750k LOC, "11 days", 99.8% tests green) is widely repeated but reported inconsistently (some sources say 6 days). Treat the headline number as **marketing-grade**.
- Codex desktop app version numbers (`26.527` / `26.601` / `26.602`) come from secondary changelog trackers, not the `openai/codex` GitHub releases (which track the CLI/runtime only). **Medium confidence.**

### Re-pinned CT2 baselines

| Runtime | 2026-05 baseline (prior radar) | 2026-06 re-pin | Rationale |
|---|---|---|---|
| Claude Code | `2.1.138` (`MIN_CLAUDE` in `bin/ct2-runtime-doctor:20`) | Document `v2.1.154` as the **dynamic-workflows feature gate** (and `v2.1.160` for the `ultracode` keyword rename). **Do not** raise `MIN_CLAUDE` to it — prefer **capability-probing** the Workflow/ToolSearch surface over a version assertion (see G6). | Workflows require `v2.1.154`; that is the first release where the orchestration surface exists. |
| Codex | `0.130.0` (`MIN_CODEX` in doctor; README still says `0.128.0+` at `README.md:480`) | Bump the documented minimum to `0.136.0` (for `tools.experimental_request_user_input` + `app-server --stdio` + thread-resume); note `0.137.0` is current stable. | README baseline (`0.128.0+`) is two stable-minor lines behind reality; `0.136.0` is the floor where the request-input toggle is consistent. |

> **Decision 2026-06-10** — kept `0.130.0` per capability-not-version gating (`spec/runtime-capabilities.md`); the `0.136.0` surfaces are tracked as capabilities, not a version gate.

> **Verification caveat carried forward** (per [`ct2-session-retrospective-2026-05-13.md`](ct2-session-retrospective-2026-05-13.md)): the version/date facts above were corroborated against GitHub release timestamps and official docs directly, **not** via WebFetch date-reasoning (which previously mis-flagged a real citation as fabricated). Every capability fact is tagged Primary / Official / Web-unconfirmed; nothing in the radar tables below depends on a web-only number.

---

## Second-Order Insights

1. **The runtime now owns orchestration, but not authority.** A workflow's intermediate state lives in script variables; its resume journal dies when Claude Code exits; its subagents are forced into `acceptEdits` with no mid-run sign-off; its budget is (at best) a soft hint. Each of these is precisely the seam CT2 occupies — durable file state, an explicit re-entry-for-review boundary, and an evidence ledger that outlives the session.
2. **Forced-`acceptEdits` + no mid-run sign-off makes review-before-merge structurally impossible *inside* a workflow.** This is not a bug to route around; it is the load-bearing reason CT2 exists. The per-stage-workflow sign-off pattern Anthropic documents ("run each stage as its own workflow") is exactly the boundary where CT2's file-first dual-review re-enters.
3. **Reviewer independence was written for *session* boundaries; a parent script breaks that assumption.** `agent()`/`parallel()`/`pipeline()` let one orchestrator hold every subagent's return. The old defense (separate sessions + no-peek of the sibling sidecar) does not constrain a parent that could inject a sibling's output into a verifier's prompt. Independence must become a prompt-construction rule, not a file-access rule.
4. **Budget is a fan-out *width* lever, not a stop condition.** A budget-scaled fleet does not self-halt on a token target. CT2's honest position: it cannot live-meter tokens and should not pretend to. Blast radius is bounded by the agent-count cap, scope-first slicing, worktree isolation, and CT2's existing **time/round** circuit breakers — which work without token metering.
5. **Subtraction still wins.** Native self-paced `/loop` + `Monitor` can retire CT2's hand-rolled active/idle/dormant forge pacing (60/120/180s); native `isolation:"worktree"` makes `max_concurrent_worktrees:1` obsolete as a *safety* mechanism (it remains a serial-throughput choice). The market validates the bet: Faros AI measured +91% review time against +98% merged PRs across high-AI-adoption teams — generation outran review capacity. Verification is the under-served layer.
6. **Honest uncertainty shapes the bets.** Workflows / teams / ultracode are all research-preview/experimental and single-session, so CT2 must not make any of them **load-bearing**. The file protocol's durability is precisely the hedge against these surfaces churning — which is the 6–18 month window the reframe already bet on.

---

## Claude Code Feature Radar

Maturity: **stable** (GA, documented), **experimental** (preview/flagged/default-off), **immature** (undocumented, anecdotal, or contradicted by a primary source).

| Capability | Current state | Maturity | CT2 opportunity | Priority |
|---|---|---|---|---|
| **Dynamic workflows** (JS orchestrator: `agent`/`parallel`/`pipeline`/`phase`/`log`/`workflow`) | `v2.1.154+`, research preview, 2026-05-28. Background runtime; intermediate state in script variables; resume journal **session-scoped** (exit → restart fresh). Functional twin of CT2 fan-out. | experimental | **Claim the whitespace** (grep confirms zero prior hits): declare CT2 the verification/protocol kernel **above** workflows — a workflow is an ephemeral executor whose output is non-authoritative until it re-enters `.ct2/` for dual-review + reconcile. "Workflows carry the work; CT2 carries the outcome." Content-tier only (adapters + spec), no new core daemon. | **P0** |
| **Workflow forced `acceptEdits` + no mid-run sign-off** | Confirmed in official docs: subagents always `acceptEdits`, inherit allowlist, edits auto-approved; no mid-run user input — per-stage sign-off needs per-stage workflows. | stable (a documented limitation of an experimental surface) | Make worktree isolation the **mandatory write target** for any CT2-wrapped workflow: forge-as-workflow edits land only in a per-run worktree branch; the target branch is touched **only** by the reconciler after dual-approval. Turns the runtime's limitation into CT2's reason to exist. | **P0** |
| **Ultracode** (`/effort ultracode` = xhigh + auto-orchestrate) | `v2.1.154+`; session-scoped; one request → several workflows (understand→change→verify); keyword rename `workflow`→`ultracode` at `v2.1.160`; disable via `/config`. | experimental | Welcome ultracode as **forge's engine** for understand/change, but its verify phase **re-enters CT2** at the verify/commit boundary where CT2 (not the runtime) owns the verdict. Resolve the direct conflict with `helm-auto-cx`'s "no subagent fan-out for state writes" via the rule in G9. | **P0** |
| **Self-paced `/loop` + cron + `Monitor`** | `/loop` self-paces 1 min–1 hr and can stop itself; fixed interval runs cron; scheduled tasks `v2.1.72+` (≤50/session, 7-day recurring expiry); `Monitor` streams without polling. | stable | Retire CT2's hand-rolled active/idle/dormant forge pacing and adapter-owned continuation; reinforces the reframe's "the loop belongs to the agent." **Caveat:** workflow determinism disables `Date.now()`/`Math.random()`, which breaks CT2's timestamp circuit-breaker stamps **if** run inside a workflow — keep duration breakers outside workflow scope (G8). | **P1** |
| **Budget object / directive** | Workflow `budget` exposes a token target for `loop-until-budget`. API `task_budget` is a **soft hint** (only `max_tokens` is hard) and **not supported on Claude Code/Cowork**. No per-run circuit breaker beyond the agent cap. | experimental / contradicted | **Do not** build a token-budget enforcer CT2 cannot honor. Treat budget as a fan-out **width** input recorded in the evidence ledger (advisory); bound blast radius by the agent cap + scope-first slicing + worktree isolation + existing time/round breakers; record cost **post-hoc** on the Cost axis. | **P1** |
| **`isolation:"worktree"` + `EnterWorktree`** | First-class per-subagent git worktree, auto-cleaned; `worktree.baseRef` selects base; community-endorsed fix for AI-generated merge conflicts. | stable | Adopt worktree isolation as the **default write target** so a forced-`acceptEdits` workflow can never touch the working branch before lens approves. Currently **Phase 1.5+** in CT2 (`spec/directory-structure.md:46` marks per-ticket worktrees future; `ct2-init` makes an empty `worktrees/` dir) — this is a roadmap bet, not present readiness. **Complements** (does not replace) the single in-progress `O_EXCL` lifecycle lock in `ct2-pickup`. | **P0** |
| **ToolSearch / deferred built-in tools** | `v2.1.69`; built-ins deferred (same mechanism as MCP); system-tools context ~14–16k → ~968 tokens; schemas fetched on demand. Deferred set is version/config-dependent. | stable (shipped undocumented) | CT2 role prompts that assume `Task`/`Monitor`/`SendMessage`/`EnterWorktree` are immediately callable now hit `InputValidationError`; adapters must instruct agents to `ToolSearch`-fetch deferred schemas first. Upside: frees ~13–15k context for larger role prompts; keep CT2's hot tools non-deferred and order the stable persona prefix first for cache reuse across helm→forge→lens. | **P1** |
| **Native `Task*` / `Team*` + agent teams** | Agent teams `v2.1.32+`, experimental, default-off; shared task list (file-locked claims + dependency markers), `SendMessage` mailbox, idle/created/completed hooks; one team per lead, no nesting, no in-process resume. | experimental | Closest native analogue to CT2's role messaging, but non-nesting, non-resumable, and it loses the on-disk human-inspectable audit trail. Treat as a candidate **transport** for `SendMessage`-style hints, **not** load-bearing infrastructure; keep `.ct2/` inbox authoritative (consistent with the 2026-05 anti-bet "TeamCreate/SendMessage replacing inbox → refused"). | **P2** |
| **`/code-review ultra`** (cloud multi-agent review) | Deep "ultrareview" on Anthropic cloud, off the local usage window; `--fix` applies findings. | stable | A ready-made heavy lens pass **off** local budget — but a **third single-vendor opinion**, not independent dual-review. Let `lens-cc` **delegate** its deep pass to ultra and cite it in-sidecar (independence preserved; ultra is one model's input), keeping the cc/cx AND intact. Naming note: this repo's docs call the cloud third-opinion `/ultrareview`; align before implementation. | **P2** |
| **`/deep-research` harness** | Bundled adversarial-verify research workflow: fan-out web search, cross-check, vote per claim, cited report with unsupported claims filtered. | stable | `helm-auto-cx` may invoke `/deep-research` for discovery and seal tickets from cited findings (it already must cite every external source). Fail-soft to the bespoke discovery path when unavailable; never let it move a ticket. | **P2** |
| **`agent(opts.schema)` structured output** | Subagent returns a JSON-Schema-validated object at the tool-call layer. | stable | CT2 sidecars are free-form markdown parsed by regex; a native fan-out naturally produces JSON verdicts. Opportunity to define a CT2-blessed structured verdict shape that maps cleanly to sidecar frontmatter without abandoning the immutable-sidecar contract. | **P2** |

---

## Codex Feature Radar

| Capability | Current state | Maturity | CT2 opportunity | Priority |
|---|---|---|---|---|
| **Stable release line** | `0.130.0` → `0.137.0` (2026-06-04); `0.138.0` alpha-only. Seven stable minors in the window. | stable | Re-pin documented Codex minimum to `0.136.0` (README still says `0.128.0+` at `README.md:480`; `MIN_CODEX` in doctor is `0.130.0`). Version-gate everything below. | **P0 maintain** |
| **`tools.experimental_request_user_input` toggle** | `0.136.0`, default false; gates `request_user_input` in Default mode; the older `default_mode_request_user_input` feature flag remains experimental/opt-in. | experimental | Update CT2's preflight that enables `default_mode_request_user_input` (`README` / `spec/codex-runtime-contract.md`): on `0.136.0+` set/verify **both** flags and keep `request_user_input` opt-in, retaining the graceful fallback to app-server/plan-mode/`.ct2/` inbox as the default path. | **P1** |
| **`app-server --stdio` + thread-resume** | `0.136.0` adds a stdio launch mode, thread resume with an initial turns page, richer MCP server status; `0.137.0` adds remote-control v2 RPCs + environment-scoped approvals. | stable | Revisit `ct2-codex-app-driver` against `0.136/0.137`: prefer `--stdio` launch, summary/unloaded thread reads, thread-resume; the camelCase-vs-snake_case payload note still holds. | **P1** |
| **Goals default-on** | `0.133.0`: goals enabled by default, dedicated storage, progress tracking; `0.134.0` adds budget-limited goal steering and better ephemeral-session errors. | stable | CT2's optional goal-based continuation can assume goals exist by default on `0.133.0+` rather than gating behind a preflight check, but must still handle sessions where goals are disabled. | **P1** |
| **Subagents TOML** | First-class `~/.codex/agents/*.toml` (`name`/`description`/`developer_instructions`; `[agents]` `max_depth`/`max_threads`/`job_max_runtime_seconds`); spawn only when explicitly requested; Codex waits for all and returns a consolidated response. | stable | Optionally expose CT2 helm/forge/lens personas as Codex agent TOMLs for users who want native spawning, but keep them distinct from the file-backed dual-review protocol (which gives stronger guarantees than ad-hoc spawning). | **P2** |
| **Multi-agent v2** | Still "dogfood defaults" through `0.137.0`; tool namespace configurable/in-flux. v1 `features.multi_agent` (`spawn_agent`/`send_input`/`resume_agent`/`wait_agent`/`close_agent`) stable/on-by-default. | experimental | **Do not** migrate helm/forge/lens orchestration onto v2 in this window. CT2's existing stance (`forge` forbids subagents unless opted in; `helm-auto-cx` parent-owns-writes) remains correct vs dogfood v2. | **P2** |
| **Plugin hooks de-flagged + hook subagent identity** | `plugin-hooks` flag removed in `0.134.0` (stable default); hook/extension inputs carry subagent identity + conversation history (`0.133/0.134`). | stable | Validate CT2's heartbeat-via-hooks against the de-flagged behavior; subagent-identity-in-hooks could let CT2 attribute heartbeats/activity per role more precisely if it ever uses native subagents. | **P2** |
| **MCP robustness** | `0.134.0`: per-server env targeting, OAuth for streamable HTTP, concurrent read-only tools (`readOnlyHint`); `0.136.0`: `rmcp 1.7.0`, richer status. Config `mcp_servers.<id>.enabled` / `startup_timeout_sec`. | stable | Note new config keys in CT2's Codex MCP references; relevant if CT2 wraps review tooling as MCP servers (read-only review tools can run concurrently). | **P2** |
| **Remote-control auth change** | `0.136.0`: short-lived server tokens (not ChatGPT access tokens) + `CODEX_API_KEY` for approved hosts; `0.137.0`: pairing start + controller grant/revoke RPCs. | stable | If CT2 ever drives Codex remotely, do not assume long-lived ChatGPT tokens; account for v2 pairing/grant-revocation. | **P2** |
| **Independent dual-review / planner-implementer-reviewer system** | **Not shipped.** Closest analogues (multi-agent v2 spawn+consolidate, Goals progress tracking) are single-vendor and not a dual-independent reviewer. | (whitespace) | **Confirmed differentiator.** Codex provides no CT2-style independent dual-review; CT2's cross-vendor cc/cx AND has no native equivalent on either runtime. | n/a (positioning) |

---

## Strategic Gaps And Proposed Product Bets

Each gap states the new capability, CT2's current state (repo-verified), the opportunity, and the honest risk. All bets are **content-tier** (docs, adapters, role prompts, spec, CT2-blessed templates) unless explicitly noted — none add a daemon, and none make an experimental surface load-bearing.

### P0 — Declare the position: CT2 above native workflows

**New capability.** A deterministic JS orchestrator over dozens-to-hundreds of subagents, with `pipeline`/`parallel`/adversarial-verify/judge-panel patterns built in.

**CT2 current state.** Grep confirms **zero** hits for `ultracode` / `dynamic workflow` / `budget-scaled` / `fan-out` across all three 2026-05 strategy docs and `spec/`. The reframe's "the loop belongs to the agent" covers **single-agent** continuation only. CT2 has **no committed stance** — clean whitespace, no prior decision to contradict.

**Opportunity.** Declare CT2 the verification/protocol kernel **above** native workflows: a workflow is an ephemeral executor; its output is non-authoritative until it re-enters CT2's file-first dual-review and reconciler. Add a **Boundary Decision Table** row mirroring the reframe's existing layer-disambiguation pattern (the same one it uses for the runtime loop): *"Runtime asks CT2 to fan out / orchestrate → Runtime workflow → author or invoke a workflow in the adapter; the workflow re-enters CT2 at the verify/commit boundary; never give a workflow terminal authority."* Ship this as a new strategy note that **composes_with** (does not supersede) the 2026-05-13 reframe.

**Risk.** Reads as scope creep unless argued strictly as adapter/role-prompt content (the "free to grow" tier), not CT2 core code. Site the position in adapters + spec with zero new daemons.

**Effort:** medium. **Impact:** high. **Confidence:** high.

### P0 — Mandate worktree isolation as the workflow write target (Phase 1.5+)

**New capability.** Workflow subagents always run `acceptEdits` with auto-approved edits and **no mid-run sign-off** — the runtime literally cannot pause for lens between forge and merge.

**CT2 current state.** CT2's whole epistemic model is review-before-state-moves. `max_concurrent_worktrees:1` is a serial **safety** default, not isolation. Per-ticket worktrees are **unimplemented** today: `spec/directory-structure.md:46` marks them Phase 1.5+; `ct2-init` creates only an empty `worktrees/` dir; the live model is branch-per-ticket (`spec/git-workflow.md`). The 2026-05 radar already conceded "subagent worktree isolation has not yet been absorbed into the CT2 protocol."

**Opportunity (forward bet, not present readiness).** When a CT2 role spawns subagents/workflows, route their writes to a per-subagent worktree (`isolation:"worktree"`, `baseRef` chosen from ticket frontmatter); the parent role merges results into the ticket branch; the target/default branch is touched **only** by the reconciler after dual-approved lens sidecars (already true: `spec/git-workflow.md:16` restricts git to forge + reconciler). This turns the runtime's "no mid-run sign-off" limitation into CT2's reason to exist — the sign-off happens at **workflow re-entry**, owned by CT2.

**Honest scoping.** Worktree isolation **complements** serial-safety logic; it does not delete it. The single in-progress `O_EXCL` lifecycle lock in `ct2-pickup` and the reconciler lock still prevent two pickups into one slot — worktrees add filesystem disjointness, not lock-freedom.

**Risk.** If CT2 fails to mandate isolation, a single ultracode session can auto-merge unreviewed edits onto the branch, silently defeating dual-review — the precise "stops reviewing every line" drift the reframe research warns about.

**Effort:** medium. **Impact:** high. **Confidence:** medium (depends on Phase-1.5 worktree implementation landing).

### P0 — Upgrade reviewer independence to a prompt-construction invariant

**New capability.** `agent()`/`parallel()`/`pipeline()` let one orchestrator script hold every subagent's return value; a judge/skeptic subagent's prompt is composed by the parent.

**CT2 current state.** Independence rests on three session-era mechanisms: separate sessions (cc Claude vs cx Codex), per-reviewer sidecar files, and a no-peek rule (`spec/conformance.md:18` — "does not read the partner sidecar before its own sidecar exists"; enforced by `claude-plugin/hooks/enforce-review-independence.sh`, which hard-codes the binary lens-cc↔lens-cx partner relationship). None of these constrain a parent script that could inject a sibling's output into a verifier's prompt.

**Opportunity.** Elevate independence to a testable rule in `spec/conformance.md`: *"a verifier subagent's prompt MUST NOT contain any sibling reviewer's output."* A workflow that violates it is non-conforming. Ship a **CT2-blessed adversarial-verify workflow template** that wires cc/cx independence (and optional K skeptics) by construction, so users don't hand-roll a leaky one. This is the reframe's "reviewer independence elevated from convention to protocol law" made precise for the fan-out era. (Note: a CT2-owned template on the Claude-specific Workflow surface is content-tier and vendor-coupled — keep it an adapter artifact, not core.)

**Strongest external backing.** Anthropic's own self-preferential-bias finding (it grades its own output too generously) and its structural mitigation (split generation from evaluation into separate contexts); broader LLM-as-judge fragility research warns single judges are gameable.

**Risk.** Hard to **mechanically** enforce inside an opaque JS script — CT2 can specify and conformance-test the rule but cannot prevent a non-conforming script. Open question (below): do CC hooks even fire for subagents spawned **inside** a workflow? If not, re-entry checks, not hooks, are the only enforcement point.

**Effort:** medium. **Impact:** high. **Confidence:** medium.

### P1 — Generalize the reconciler to an M-of-N quorum (2-of-2 stays the floor)

**New capability.** Documented workflow patterns are N-of-M (adversarial-verify kills on majority; judge-panel scores + synthesizes), not a fixed pair.

**CT2 current state.** The reconciler is **Python**, not a JS workflow: `bin/ct2-reconcile` ANDs exactly two sidecars (`cc_v == "approved" and cx_v == "approved"`, `ct2-reconcile:251`), `discover_pairs` regexes `(cc|cx)` and gates on `sides != {"cc","cx"}` (`:298`, `:305`), and `_ct2_update_verdict.py` writes fixed `review-status.lens-claude` / `lens-codex` frontmatter (`:76`, `:81`). The cc/cx pair is structurally baked into ~12 spec files and the independence hook (which assumes exactly one partner to block).

**Opportunity.** Generalize the verdict schema to an M-of-N quorum **without** breaking the 2-of-2 default: keep dual-approval (cc AND cx) as the canonical floor and sole path to `done/`; add an optional quorum policy where extra adversarial verifiers are **advisory** evidence unless explicitly promoted by config. Express via a parsed reviewer list + policy function and sidecar naming `{id}-{reviewer}-r{n}.md`.

**Honest scoping correction.** This is **not** net-LOC-neutral. Generalizing touches the verdict logic, the sidecar filename scheme, `discover_pairs` regex, the fixed `lens-claude`/`lens-codex` frontmatter keys, the per-reviewer validator, and especially `enforce-review-independence.sh` (which must move from "block the one partner" to "block all N-1 partners"). Budget it as a **moderate, multi-file** change, not a refactor that magically deletes as much as it adds.

**Risk.** Adding N-of-M is exactly the "thicker" addition the reframe resists. Keep the reference reconciler small (parse a list, apply a policy fn) and keep the cross-vendor AND as the trust anchor: **either reviewer rejects → rejected** must survive any quorum extension.

**Effort:** medium. **Impact:** medium. **Confidence:** medium.

### P1 — Extend capability detection + the evidence graph for the fan-out era

**New capability.** Native Workflow runtime, `Task`/`Agent`/`Monitor`/`SendMessage` tools, worktree isolation, ultracode mode — none of which CT2 can currently detect; and fan-out attributes findings to dozens of subagents that need to roll up to a parent role/ticket.

**CT2 current state.** `ct2-runtime-doctor` probes only codex/claude/git/python versions + Codex feature flags (`MIN_CLAUDE = (2,1,138)` at `:20`); it has **no** Workflow/Task/Monitor detection. `claims.jsonl` is a **flat** per-ticket list — `bin/ct2-evidence`'s `write_claim` emits only `id`/`timestamp`/`ticket`/`kind`/`verifier`/`ok`/`path`/`summary` (no `parent_id`, no `produced_by_agent`); despite the name "Evidence Graph" there are no edges.

**Opportunity.**
- **Detection:** add a workflow-class probe to `ct2-runtime-doctor`. **Gate on observed capability, not a guessed version** — probe for Workflow-tool / ToolSearch-deferred-tool presence directly (the doctor already capability-probes), and treat absence as "serial fallback," never as error. (Do **not** hard-code `CC>=2.1.154` as a gate, and do **not** invent a `disableWorkflows` state name — the only runtime fan-out flag observable today is Codex's `enable_fanout`, under development/disabled in `capabilities.json`.) Network-free, no state mutation — fits the existing doctor contract.
- **Evidence edge:** add a single optional `parent_id` / `produced_by_agent` field to claim records so a fan-out's per-finding evidence attributes to the orchestrating role and ticket. This makes the workflow's variables-only intermediate state **durable** in `.ct2/` — the most concrete instantiation of "CT2 = the durable evidence graph above ephemeral workflows." One field, not a graph engine.

**Risk.** Version/flag surface is volatile and partly undocumented; the probe must degrade gracefully. Keep the evidence change a single optional append-compatible field (stdlib/file-first).

**Effort:** low. **Impact:** medium. **Confidence:** high.

### P1 — Resolve the helm-auto-cx ↔ ultracode contradiction (G9) and protect single-agent markers (G10)

**New capability.** Ultracode expects the planner to author + run workflows over many subagents by default; `agent()`/`parallel()` spawn many peer subagents in one orchestration.

**CT2 current state.** `ct2-helm-auto-cx` explicitly **forbids** subagent fan-out for CT2 state writes (`SKILL.md:76-77`: "explorers are read-only and parent helm-auto-cx owns all CT2 state writes"). `.ct2/.meta/ct2-active-role` is a single-value last-writer-wins file; `ct2-pickup`'s singleton in-progress slot + lifecycle lock assume one forge; the inbox is per-role-name (one consumer). Naive fan-out races these.

**Opportunity.** One clean rule, not a contradiction: native workflows may **fan out for read-only discovery/analysis and for forge implementation inside isolated worktrees**, but CT2 **state writes** (seal, sidecar, reconcile, ticket `mv`) remain parent-owned one-shot operations. Codify that fan-out subagents are **non-role-holding workers**: a subagent never writes the active-role marker, never holds ticket authority, never claims the in-progress slot — only the parent role does. (This generalizes the parent-owns-writes rule already in `ct2-forge` and `ct2-helm-auto-cx` to all roles; it is the least-overstated, mostly-already-codified part of this radar.) Ultracode's understand/change phases are welcome; the verify/commit phase re-enters CT2.

**Risk.** Conformance-testable but not mechanically preventable in an opaque workflow; mitigate via CT2-blessed templates that wire parent-owns-writes by construction.

**Effort:** low. **Impact:** medium. **Confidence:** high.

### P2 — Adopt native heavy surfaces as evidence producers, never verdict authorities

**New capability.** `/code-review ultra` (cloud multi-agent, off local budget) and `/deep-research` (bundled adversarial-verify research) are first-class native surfaces.

**CT2 current state.** CT2 reimplements bespoke versions: `helm-auto-cx` discovery overlaps `/deep-research`; lens dual-review overlaps `/code-review ultra`. The reframe already **rejected** ultrareview as a lens **replacement** (`ct2-product-strategy-2026-05.md` §11.4: "Ultrareview is only a third opinion").

**Opportunity.** Adopt native surfaces as **evidence producers**, not verdict authorities, and subtract bespoke code: `lens-cc` may delegate its deep pass to `/code-review ultra` (off local budget) and cite the result in its sidecar (independence preserved — ultra is one model's input); `helm-auto-cx` may invoke `/deep-research` for discovery. All fail-soft to the bespoke path when unavailable; **none can move a ticket** (terminal-authority rule).

**Honest guardrail.** ultra is a **third single-model opinion**, not independent dual-review, so it **augments** lens, never replaces the cc/cx AND. Confirm whether cloud ultra actually escapes any shared budget ceiling before relying on it for budget relief (the "off local budget" claim is an official doc statement about the *usage window*, not about workflow token budgets). Naming drift: this repo calls the cloud review `/ultrareview`; align before implementation.

**Effort:** low. **Impact:** medium. **Confidence:** medium.

### P2 — Determinism boundary for CT2-emitted workflows (G8)

**New capability.** Workflow scripts forbid `Date.now()`/`Math.random()`/argless `new Date()`; meta block must be a pure literal; plain JS not TS.

**CT2 current state.** CT2 circuit-breaker stamps (`.started`/`.in-review`) and message IDs use wall-clock timestamps and random IDs; `ct2-duration-check`/`ct2-review-watchdog` are time-based.

**Opportunity.** Spec a clean boundary: CT2's time/round breakers and ID generation run **outside** the workflow (host session / one-shot tools), never inside the deterministic script; any CT2-emitted workflow derives IDs from stable inputs (content hashes, ticket id, round). Preserves resume **and** keeps CT2's breakers intact — an authoring-discipline win, not a blocker.

**Effort:** low. **Impact:** low. **Confidence:** high.

---

## Roadmap

| Phase | Timebox | Deliverables | Exit criteria |
|---|---:|---|---|
| 0 | 1 week | New strategy note "CT2 above native workflows" (composes_with the reframe) + Boundary Decision Table row + re-pinned baselines in README/doctor docs | Position is written; Codex min documented at `0.136.0`, Claude workflow gate documented at `v2.1.154`; no core code changed. *Decision 2026-06-10 — kept `0.130.0` per capability-not-version gating (`spec/runtime-capabilities.md`); `0.136.0` surfaces are tracked as capabilities, not a version gate.* |
| 1 | 1–2 weeks | Reviewer-independence prompt-construction invariant in `spec/conformance.md` + CT2-blessed adversarial-verify workflow template (adapter artifact) | A leaky verifier-prompt is flagged non-conforming by the conformance check; the blessed template wires cc/cx independence by construction. |
| 2 | 2–3 weeks | Non-role-holding subagent rule (G9/G10) across role specs/adapters; helm-auto-cx vs ultracode rule codified | Fan-out for discovery/implementation is allowed; CT2 state writes remain parent-owned; active-role marker / in-progress slot cannot be claimed by a subagent. |
| 3 | 3–4 weeks | Workflow-class capability probe in `ct2-runtime-doctor` (capability-gated, network-free); optional `parent_id`/`produced_by_agent` edge in `claims.jsonl` | Doctor reports workflow availability and degrades to "serial fallback"; fan-out evidence attributes to parent role/ticket. |
| 4 | 4–6 weeks | Worktree isolation as workflow write target (Phase 1.5+ worktree lifecycle) + re-entry contract | A forced-`acceptEdits` workflow lands edits only in a per-run worktree; target branch touched only by the reconciler after dual-approval. |
| 5 | 6–8 weeks | M-of-N quorum (2-of-2 floor) in reconciler + `enforce-review-independence.sh` N-partner rewrite | Optional K skeptics are advisory; cc AND cx remains the sole path to `done/`; "either rejects → rejected" preserved. |
| 6 | 8+ weeks | `/code-review ultra` + `/deep-research` adopted as fail-soft evidence producers; native `/loop`+`Monitor` retire hand-rolled forge pacing | Bespoke pacing deleted (net core shrink); ultra/deep-research cited as evidence, never moving a ticket. |

---

## Prioritization

| Bet | Impact | Confidence | Effort | Why now |
|---|---:|---:|---:|---|
| CT2-above-workflows position + re-pin | High | High | Medium | Clean whitespace (zero prior hits); baselines are two lines stale on both runtimes; pure content-tier. |
| Reviewer-independence prompt invariant | High | Medium | Medium | A parent script now holds all child returns; session-era no-peek no longer binds; Anthropic's own self-preferential-bias finding backs it. |
| Worktree isolation as write target | High | Medium | Medium | Forced-`acceptEdits` + no mid-run sign-off makes this the structural defense; depends on Phase-1.5 worktree implementation. |
| Non-role-holding subagent rule (G9/G10) | Medium | High | Low | Mostly already codified (forge/helm-auto-cx parent-owns-writes); generalizing prevents marker/slot corruption under ultracode. |
| Capability probe + evidence edge | Medium | High | Low | Lowest-effort, highest-leverage; network-free probe + one optional field; makes "durable evidence above workflows" concrete. |
| M-of-N quorum (2-of-2 floor) | Medium | Medium | Medium | Lets CT2 *express* native judge-panel/adversarial patterns without abandoning dual-independent; multi-file, not net-zero. |
| Native ultra/deep-research as evidence | Medium | Medium | Low | Reuses vendor compute and subtracts bespoke logic; must stay advisory (third single-model opinion). |
| Determinism boundary (G8) | Low | High | Low | Documentation/boundary rule; prevents naive in-workflow timestamps from breaking resume. |

---

## Non-Goals

- **A token-budget enforcer.** CT2 does not (and cannot reliably) meter tokens or hard-stop on a budget directive — Anthropic budgets are soft hints; only `max_tokens` is hard, and it is not even supported on Claude Code surfaces. CT2 bounds blast radius by the agent-count cap, scope-first slicing, worktree isolation, and existing time/round breakers; it records cost **post-hoc**.
- **Making workflows / teams / ultracode load-bearing.** All are research-preview/experimental and single-session. CT2 must remain fully functional with them absent. The file protocol's durability is the hedge against churn.
- **Giving a workflow terminal authority.** No workflow, ultracode session, agent team, or `/code-review ultra` pass may move a ticket to `done/`. The reconciler remains the sole automatic terminal authority after dual-approval.
- **Replacing the `.ct2/` inbox with native `SendMessage`/`TaskCreate`/`TeamCreate`.** Consistent with the 2026-05 anti-bet. Native team messaging may be an advisory fast-path; the inbox stays authoritative.
- **Migrating CT2 orchestration onto Codex multi-agent v2.** Dogfood-default and in-flux; the existing "no forge subagents unless opted in" stance is correct for this window.
- **Emitting vendor-locked workflow scripts as CT2 core.** CT2-blessed workflow templates are adapter/content-tier artifacts, not part of the protocol kernel — coupling CT2 core to one vendor's JS dialect would violate the no-external-deps / subtraction principles.

---

## Open Questions

1. **Is the workflow budget object a hard ceiling on Claude Code specifically?** The primary-source brief says a `+500k` directive becomes a hard shared ceiling; Anthropic's Task-budgets docs say it is a soft hint, only `max_tokens` is hard, and the feature is **not supported on Claude Code/Cowork**. CT2's no-token-enforcer Non-Goal depends on the soft reading being correct for CC workflows — confirm before freezing any budget-related spec text.
2. **Can reviewer independence be mechanically enforced for in-workflow verifiers, or only conformance-tested?** A parent JS script can inject a sibling's output and CT2 cannot inspect the opaque script. Is a blessed template + conformance test sufficient, or is a tool-layer hook needed — and does such a hook even fire inside a background workflow?
3. **Do CC hooks (and CT2's heartbeat-via-hooks) fire for subagents spawned *inside* a workflow, or only for top-level/interactive agents?** Determines whether CT2 can enforce plan-evidence/independence at the hook layer for fan-out work or must rely on re-entry checks only.
4. **What is the cold-restart rehydration contract when a workflow dies mid-run** (session exit restarts it fresh)? CT2's file ledger should let a new workflow resume from the last durable `.ct2/` state rather than the lost `runId` journal — but which `.ct2/` artifacts a re-launched workflow reads to skip completed work is unspecified.
5. **Will a major runtime ship a file-first workflow-state convention natively** (the reframe's §12.9 risk)? If Claude/Codex adopt `.ct2`-like on-disk state, CT2's durability differentiator narrows. What is the trigger to re-evaluate?
6. **How should the M-of-N quorum treat a cc-vs-cx split when adding K same-vendor skeptics?** The default must preserve "either independent reviewer rejects → rejected"; the promotion rule for advisory skeptics needs a precise spec.

---

## Appendix A — Sources

**Primary (Anthropic / Claude Code, official).**

- Introducing dynamic workflows in Claude Code — `claude.com/blog/introducing-dynamic-workflows-in-claude-code`
- A harness for every task: dynamic workflows in Claude Code (engineering deep-dive) — `claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code`
- Orchestrate subagents at scale with dynamic workflows (docs) — `code.claude.com/docs/en/workflows`
- Run prompts on a schedule (`/loop`, Cron, Monitor) — `code.claude.com/docs/en/scheduled-tasks`
- Orchestrate teams of Claude Code sessions (agent teams) — `code.claude.com/docs/en/agent-teams`
- Run parallel sessions with worktrees (isolation, EnterWorktree) — `code.claude.com/docs/en/worktrees`
- Code Review (`/code-review`, ultra cloud review) — `code.claude.com/docs/en/code-review`
- Task budgets (soft-hint correction; beta; not on Claude Code/Cowork) — `platform.claude.com/docs/en/build-with-claude/task-budgets`
- Tool search tool / deferred loading — `platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool`
- Built-in system tools deferred behind ToolSearch (v2.1.69) — `github.com/anthropics/claude-code/issues/31002`

**Primary (OpenAI / Codex, official).**

- Codex GitHub Releases (REST API; `published_at` timestamps) — `api.github.com/repos/openai/codex/releases`
- Codex Changelog — `developers.openai.com/codex/changelog`
- Codex Subagents (TOML) — `developers.openai.com/codex/subagents`
- Codex Configuration Reference — `developers.openai.com/codex/config-reference`
- Codex `0.136.0` / `0.137.0` release notes — `github.com/openai/codex/releases/tag/rust-v0.136.0`, `…/rust-v0.137.0`
- PR #24541 `experimental_request_user_input` toggle — `github.com/openai/codex/pull/24541`

**Secondary / context (treat as directional; not used to anchor any version or capability fact).**

- InfoQ — Claude Code Adds Dynamic Workflows for Parallel Agent Coordination
- alexop.dev — Claude Code Workflows: Deterministic Multi-Agent Orchestration (budget object, determinism deep-dive)
- Hacker News item 48311705 — Dynamic Workflows discussion (cost/correctness critiques)
- Fortune (2026-04-02) — "trust is the real bottleneck"; InfoQ (2026-03-24) — "coding was never the bottleneck" (Faros AI: +21% tasks / +98% PRs / +91% review time)
- Simon Willison (2026-05-06) — "Vibe coding and agentic engineering are getting closer than I'd like"

**CT2 repository (primary, verified live 2026-06-07).**

- `bin/ct2-runtime-doctor` (`MIN_CODEX = (0,130,0)`, `MIN_CLAUDE = (2,1,138)`), `README.md:480` (`Codex 0.128.0+`)
- `bin/ct2-reconcile` (cc/cx AND at `:251`; `discover_pairs` at `:298`/`:305`), `bin/_ct2_update_verdict.py` (`lens-claude`/`lens-codex` frontmatter)
- `bin/ct2-evidence` (`write_claim` fields — flat ledger, no parent edge)
- `claude-plugin/hooks/enforce-review-independence.sh` (binary cc↔cx partner)
- `spec/conformance.md` (no-peek rule), `spec/git-workflow.md:16` (git restricted to forge + reconciler), `spec/directory-structure.md:46` (worktrees Phase 1.5+), `config/harness.yaml` (`budget_usd: null` ×5; `max_concurrent_worktrees: 1`)
- `codex-plugin/skills/ct2-helm-auto-cx/SKILL.md:76-77` (parent-owns-writes)

**Cross-referenced CT2 docs.** [`agent-platform-feature-radar-2026-05.md`](agent-platform-feature-radar-2026-05.md) (prior baseline), [`ct2-protocol-reframe-2026-05-13.md`](ct2-protocol-reframe-2026-05-13.md) (canonical posture), [`ct2-verified-autonomy-os-strategy-2026-05.md`](ct2-verified-autonomy-os-strategy-2026-05.md), [`ct2-product-strategy-2026-05.md`](ct2-product-strategy-2026-05.md), [`ct2-session-retrospective-2026-05-13.md`](ct2-session-retrospective-2026-05-13.md).

---

## Appendix B — Completion Audit For This Document

| User request | Evidence in this document | Confidence tier |
|---|---|---|
| Lead with the new orchestration surface | Executive Summary §1 + Claude Code Feature Radar rows 1–3; Strategic Gaps P0×3 lead the bets. | Primary + Official |
| Workflow tool / dynamic workflows | Evidence Base (primary obs + official rows); Claude radar row 1; Gap "CT2 above native workflows." | Primary + Official |
| Ultracode mode | Evidence Base; Claude radar row 3; Gap G9 (helm-auto-cx vs ultracode). | Primary + Official |
| ScheduleWakeup / dynamic `/loop` | Claude radar row 4; Evidence Base **explicitly flags** `ScheduleWakeup`/sentinel names as web-unconfirmed while the self-paced-loop capability is official. | Primary (capability) / Unconfirmed (names) |
| Budget directives | Evidence Base correction table + "what remains unconfirmed"; Claude radar row 5; Gap P1; Non-Goal "no token enforcer." Marked **contradicted** vs Anthropic Task-budgets docs. | Official correction |
| Agent worktree isolation | Claude radar row 6; Gap P0 "worktree as write target" (scoped Phase 1.5+, complements serial-safety). | Official + Primary (repo) |
| Native Task/Team | Evidence Base (deferred-tool set); Claude radar row "Native Task*/Team* + agent teams"; Non-Goal (inbox stays authoritative). | Primary + Official |
| ToolSearch / deferred tools | Evidence Base; Claude radar row "ToolSearch"; Gap context (role prompts hit `InputValidationError`). | Primary + Official |
| Code-review ultra | Claude radar row "/code-review ultra"; Gap P2; naming-drift note (repo calls it `/ultrareview`). | Official + Primary (repo) |
| Deep-research harness | Claude radar row "/deep-research"; Gap P2. | Official |
| Codex post-0.130.0 updates | Codex Feature Radar (9 rows, `0.131`→`0.137`); re-pin table; baseline note. | Official (GitHub API) |
| Dated header block | Header: Survey date 2026-06-07, Target, Purpose, Role-within-doc-set, one-line thesis. | n/a |
| Executive Summary | Present (3 changes + strategic read + 3 invariants + recommended order). | n/a |
| Evidence Base table (primary + official + unconfirmed) | Evidence Base: 8-row primary table, official corroboration table, corrections table, unconfirmed list, re-pin table. | n/a |
| Claude Code feature radar table (capability/state/maturity/CT2 opportunity/priority) | Claude Code Feature Radar (11 rows, all five columns). | n/a |
| Codex feature radar table (same columns) | Codex Feature Radar (9 rows + whitespace row, all five columns). | n/a |
| Appendix of sources | Appendix A (primary Anthropic, primary OpenAI, secondary, CT2 repo, cross-refs). | n/a |
| Appendix B completion-audit mapping request→evidence | This table. | n/a |
| Explicit primary-verified vs web-unconfirmed | Three-tier scheme stated at top of Evidence Base; every table cell tagged; corrections + unconfirmed lists separate contradicted/rumor claims. | n/a |
| Build on / cross-reference 2026-05 docs; don't duplicate | Header role-in-doc-set; cross-refs throughout; "since the prior baseline" framing; Non-Goals echo 2026-05 anti-bets. | n/a |
| Honor adversarial verifications | Versions re-pinned to corroborated values; budget-hard-ceiling marked contradicted; worktree mandate scoped as Phase-1.5 forward bet; "net LOC-neutral" dropped for M-of-N; invented `G2`/`G10`/`disableWorkflows` fact-labels avoided (G-labels used only as this doc's own framing); workflow maturity marked research-preview. | n/a |
