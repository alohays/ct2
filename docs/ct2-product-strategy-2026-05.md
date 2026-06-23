# CT2 Product Strategy — From Kanban Harness to Verified Autonomy OS

Survey date: 2026-05-10 KST / 2026-05-09 US
Target runtimes: Codex CLI 0.130.0 (measured), Claude Code 2.1.138 (measured, latest)
Authoring intent: A **companion document read side-by-side with** `docs/agent-platform-feature-radar-2026-05.md` (hereafter "Feature Radar"). Where Feature Radar catalogs vendor surfaces and normalizes the adoption protocol, this document decides **what we will *not* do and what we will *bet* on for the next 6–12 weeks under the product identity of Verified Autonomy OS**. The final canonical plan converges in `docs/ct2-verified-autonomy-os-strategy-2026-05.md`.

## 0. One-page summary

### 0.1 Difference from Feature Radar at a glance

| Axis | Feature Radar | This document |
|---|---|---|
| Essence | **Catalog** — maps every surface exhaustively | **Decision** — 5 bets + 6 anti-bets for Verified Autonomy OS |
| Recommendation form | P0/P1/P2 menu (9 items) | Sequenced bets after Registry+Baseline (5 bets, with kill criteria) |
| Measurement | OTel/Observability Ledger infrastructure proposal | Trust, Evidence, Autonomy, Cost/Latency balanced scorecard |
| Cost | Mentioned in passing | Elevated to *the product's #1 lever* via Bet 1 |
| User experience | Emphasizes "verifiability" | Extends to "verifiability + still-OK-when-you-wake-up" (Bet 3) |
| Plan-mode | Not mentioned | Core of Bet 2 (workflow rearrangement) |
| Regression defense | hook guardrails | Reinforced by Bet 4 eval harness (treats the role MD itself like code) |
| Competition | Not addressed | Explicit comparison against 8+ adjacent systems in §10.5 |
| Concrete deliverables | 8 candidate tickets | spec PR list + 7-day plan + actual wrapper sketches (Appendices C/D/E) |
| Authority divergence | Recognizes risk when absorbing native task/scheduler | Deliberately last as the *5th* bet (most seductive, most dangerous) |

Recommended reading order: **the final integrated document §0–§5 first (canonical direction) → Feature Radar §1–§3 (evidence base) → this document §4–§6 (bets/anti-bets) → Feature Radar §4 (P0/P1/P2)** — all three documents reviewed as a single bundle.

### 0.2 Decision

**Conclusion.** The next evolution of CT2 is not to absorb more new features but to raise its *product identity* one level. Until now CT2 has been a protocol harness — "atomic `mv` kanban + dual-review." In the next round, CT2 must become **Verified Autonomy OS** — i.e., a file-first protocol kernel that manages `.ct2/` state, review independence, evidence, budget, schedule, and permissions as OS primitives across multiple agent runtimes.

This framing makes five product bets follow naturally:

1. **Cost-aware role contracts** — bundle the surfaces "vendors shipped as stable but CT2 has barely touched," like `--max-budget-usd`, `--effort`, `enable_request_compression`, `fast_mode`, and `personality`, into SLO/error-budget form to make per-role cost, latency, and quality a *measurable contract*. *(2026-06-23: the measurable-contract half shipped; the budget-**enforcement** half is superseded — see the Bet 1 status note.)*
2. **Plan-mode-first forge** — combine Claude `EnterPlanMode/ExitPlanMode` with Codex `goals` + `tool_search` to flip the structure so that forge *always seals a plan first* and that plan lives as part of the ticket sidecar.
3. **Ambient CT2 over async channels** — using Discord/Slack/MCP channels + `PushNotification`/`RemoteTrigger`, lift CT2 from "a tool that starts only when you open a terminal" to "an always-on background colleague that flows in like email and can be delegated to."
4. **Eval harness for roles** — using `skill-creator`'s evals pattern + `claude --json-schema` + `/ultrareview`, treat role definitions (skill MD, role MD, prompt) themselves as regression-testable code.
5. **Native task graph mirror (advisory)** — mirror Claude `TaskCreate`/`TaskUpdate` (with `blockedBy` dependencies) and Codex `multi_agent` against CT2 tickets *not one-to-one but one-to-N*, lifting runtime visibility while preserving the authority of `.ct2/`.

**Priority order.** Phase 0 Registry+Baseline → Bet 1 → Bet 2 → Bet 4 → Bet 3 → Bet 5. Bet 5 is deliberately last — it is the *shiniest and most dangerous* bet (detailed rationale in §5).

**What we drop.** §6 names 6 anti-bets — attempts that look glamorous but break CT2's verifiability (delegating ticket lifecycle to cloud routing, adopting images as sole evidence, handing over done authority to a vendor scheduler, etc.).

**Difference from Feature Radar.** Feature Radar prioritized **comprehensiveness** (Capability Registry, Decision Bridge, Hook Guardrails, Watch Plane, Plugin Distribution …). This document prioritizes **decisions** (where to bet and where not to). Adopt both and Feature Radar's "P0 Capability Registry / Decision Bridge / Hook Guardrails" join as the *foundational infrastructure* of this document's five bets — not negated, layered under.

## 1. Scorecard and first principles

### 1.1 Balanced scorecard

It is risky to operate CT2 against a single north star. Looking only at Trust can explode cost and latency; looking only at cost can degrade review quality; and looking only at autonomy can quietly erode state authority via misguided automation. Hence Verified Autonomy OS's success looks at the following four axes together.

| Axis | Key metric | Meaning |
|---|---|---|
| **Trust** | Ratio of `done` tickets with no revise/revert/reopen within 90 days, first-pass approval | Does what is done once stay done? |
| **Evidence** | Ratio of state transitions carrying an evidence id and verifier | Can we reconstruct after the fact why approved/done was granted? |
| **Autonomy** | Heartbeat freshness, blocked→unblocked latency, review latency p95 | Does autonomous execution avoid stalling or going quietly stale? |
| **Cost/Latency** | $/ticket p50, ticket latency p50/p95, budget violations | Does it control cost and time while preserving reliability? |

Trust ratio is the first axis on the scorecard but not the sole north star. Definition:

```
Trust ratio (90d rolling) =
  count(tickets that reached `done` and were not revised/reverted/reopened within 90d)
  ──────────────────────────────────────────────────────────────────────────
  count(tickets that reached `done` in window)
```

Initial targets: Trust ratio ≥ 0.92, Evidence coverage ≥ 0.90, 0 autonomy SLA violations, $/ticket p50 baseline -30%. We count this as product improvement only when all four axes improve together, or at minimum when an improvement on one axis does not collapse another.

### 1.2 Restating first principles

- **Tickets are *programs*, not *conversations*.** A ticket body + frontmatter + sidecar is a declarative spec; the role is the *runtime* that executes it. Any vendor feature that blurs this separation is refused.
- **`mv` is commit.** Modeling state transitions as atomic file renames is the equivalent of *commit in a distributed system*. This simplicity means: "Don't rub vendor-added features against this."
- **Reviewer independence ≥ reviewer convenience.** Dual-review's value is that the two reviewers conclude *without seeing each other's results*. Any productivity feature that breaks this invariant is rejected.
- **`spec/` is authoritative.** Even if a vendor ships a hot feature, it does not enter CT2 unless the spec is amended. The bets this document makes *all* eventually resolve to spec PRs.
- **Zero external dependencies.** bash + python stdlib. No bet in this document breaks this rule (a JSON schema validator can be built from stdlib `json` + hand-rolled checks).

### 1.3 What CT2 is *not*

- ❌ "Universal agent OS" — the territory Cursor, Aider, Claude Project, etc. aim at. CT2 is an *opinionated dual-review pipeline*.
- ❌ Cloud SaaS — `.ct2/` is local, single-user, file-system-first.
- ❌ A Linear/Jira replacement — tickets live next to code. We do not mimic human PM tools.
- ❌ A framework bound to a single LLM — the *simultaneous use* of Codex and Claude is the essence of dual-review.

## 2. Frame shift — Verified Autonomy OS as protocol kernel

Verified Autonomy OS is not "a universal OS that covers every agent." It is **a protocol kernel that makes the `.ct2/`, spec-first tickets, atomic `mv`, dual-review sidecar, inbox, and reconciler that CT2 already has operable as OS primitives**. Reliability Platform is the operational value this kernel delivers to the user.

The SRE analogy still holds. Only the top-level name is Verified Autonomy OS rather than Reliability Platform.

> SRE insight: "A complex distributed system is ultimately operated as a cycle of *SLO + error budget + observability + postmortem*."
> CT2's next step: "Complex multi-agent collaboration is also operated as a cycle of *kernel authority + SLO + budget + evidence + postmortem*."

This analogy is not mere marketing framing. It forces five concrete product decisions:

| SRE concept | CT2 mapping | Decision it forces |
|---|---|---|
| **Service** | Role (helm/forge/lens-cc/lens-cx/status/reconciler) | Each role has its own description, owner, change procedure, and eval suite |
| **SLO** | Latency/cost/quality targets defined per role | Add SLO fields to `harness.yaml`; auto-escalate on violation |
| **Error budget** | *Permitted violations* accumulated daily/weekly | When budget is exhausted, block auto-mode; proceed manually only |
| **On-call** | *Waiting time* for inbox messages that need a human to clear | After a threshold, send a PushNotification/Discord ping |
| **Postmortem** | Post-hoc analysis of escalated/rejected tickets | `.ct2/postmortems/` directory, monthly summary |

Accept this framing and Feature Radar's three P0s (Capability Registry, Decision Bridge, Hook Guardrails) naturally take the place of *foundational infrastructure* — capacity inventory, request mediator, admission control — and this document's five bets layer the *service operations* tier on top. The two documents do not fight; they stack.

### 2.1 Layered architecture — how the two documents stack

```
        Layer 4 — Visibility (advisory only, no authority)
        ┌────────────────────────────────────────────────────┐
        │  Bet 5: Native task graph mirror (Claude Task*)    │
        │         "ticket → native task" advisory sync       │
        └────────────────────────────────────────────────────┘
        Layer 3 — Operations (UX + quality safety net)
        ┌──────────────────────────┬─────────────────────────┐
        │ Bet 3: Ambient channels  │ Bet 4: Eval harness     │
        │  Discord/Slack bridge,   │  fixed-input regression │
        │  Push/RemoteTrigger,     │  for role MDs / skills  │
        │  inbox amplification     │  (--bare + --json-schema)│
        └──────────────────────────┴─────────────────────────┘
        Layer 2 — Service contract (the SRE-style core)
        ┌──────────────────────────┬─────────────────────────┐
        │ Bet 2: Plan-mode-first   │ Bet 1: Cost contracts   │
        │  EnterPlanMode + goals;  │  per-role model/effort/ │
        │  plans become evidence;  │  budget; SLO violation  │
        │  forge-pre-execution     │  → bounce / hard_deny   │
        └──────────────────────────┴─────────────────────────┘
        Layer 1 — Admission control (Feature Radar P0/P1)
        ┌────────────────────────────────────────────────────┐
        │ Capability Registry · Decision Bridge ·            │
        │ Hook Guardrails · Watch Plane · Observability      │
        └────────────────────────────────────────────────────┘
        Layer 0 — Authority (unchanged, foundational)
        ┌────────────────────────────────────────────────────┐
        │   .ct2/  ·  spec/  ·  AGENTS.md  ·  CLAUDE.md       │
        │       (atomic mv kanban + dual review)              │
        └────────────────────────────────────────────────────┘
```

Reading rules:

- **Upper layers depend on lower layers, but lower layers do not depend on upper.** Even if Bets 1–5 all die, Layers 0–1 keep working.
- **Authority flows one way — it cannot climb up.** Whatever Bet 5 writes to native tasks cannot change a Layer 0 ticket (a rule jointly pinned by §4.5 and §6's anti-bet 4).
- **Traffic is bidirectional — information flows both ways.** Layer 0 ticket state change → Layer 4 mirror update. Layer 3 external messages → Layer 1 Decision Bridge → Layer 0 inbox.

## 3. Vendor surface re-audit — what Feature Radar didn't cover enough

Feature Radar touched almost every vendor surface. But on the *cost/quality trade-off* axis, five surfaces are stable yet untouched by CT2. This document's bets depend directly on these five.

| Surface | Current state | Why Feature Radar treated it lightly | How this document uses it |
|---|---|---|---|
| Codex `personality` (stable) | feature flag stable enabled | Easy to think "tone" is unrelated to protocol | Bet 1: enforce a personality preset per role (e.g., lens as "skeptical/short", helm as "interrogative") — reduces *style variance* in outputs, raising evaluability ↑ |
| Codex `fast_mode` (stable) | flag stable enabled | Easy to think latency optimization is not a product decision | Bet 1: pin `fast_mode` on *judgment-light roles* like status/reconciler |
| Codex `enable_request_compression` (stable) | flag stable enabled | "Token compression" looks like internal optimization | Bet 1: force it on long-thread roles (like helm-auto-cx) — the single largest lever on token cost |
| Codex `guardian_approval` (stable) + Claude `auto-mode hard_deny` (2.1.136) | both stable | Covered under Hook Guardrails, but coupling with *role policy* is undefined | Bet 1: lens role *always* hard_deny on auto admin actions; ~~helm hard_deny on budget overrun~~ *(budget enforcement superseded — see Bet 1 status note)* |
| Claude `--max-budget-usd` (CLI) + Claude `--effort` (CLI/`/effort` slash) | both stable | Easy to think "cost is the user's problem" | Bet 1: map ticket priority (p0/p1/p2) to effort/budget pins |
| Claude `--bare` (CLI) | stable since 2.1.x | Looks like a debug mode | Bet 4: the eval harness runs every regression with `--bare` — isolates experiments from external variables like hooks and auto-memory |
| Claude `EnterPlanMode/ExitPlanMode` (tool) | stable | "Plan mode looks like an optional UX" | Core of Bet 2 — make plan mode the *default forge entrypoint* |
| Claude `Monitor` (tool, v2.1.98+) | stable but unsupported in some environments | Covered as the Watch Plane, but its use as a *role lifecycle signal* is undefined | Bet 3: monitor → inbox message → role wakeup chain |
| Claude `TaskCreate/TaskUpdate` (tool) | stable, supports `blockedBy` dependency graph | Easy to see as a "todo-list imitation" | Bet 5: mirror tickets as native tasks — runtime visibility, *authority stays with the ticket* |
| Claude `--brief` + `SendUserMessage` (tool) | stable, opt-in | Looks like a simple chat channel | Bet 3: forge pushes short progress messages directly to the user (not bypassing inbox — an *additional* channel) |
| Codex `tool_search`, `tool_suggest` (stable) | flag stable enabled | "Discovery is the LLM's job" looks reasonable | Bet 4: fix `tool_search` results deterministically so the eval suite can regression-test them |
| Codex `unified_exec` (stable) | flag stable enabled | "Exec mode is one thing" — unified into invisibility | The cost-SLO unit of Bet 1 — token/latency standardized per exec call |
| Claude `worktree.baseRef` (2.1.133) | stable | Covered by Feature Radar, but coupling to ticket lifecycle is undefined | Bet 2: forge creates a worktree only after plan-mode; `baseRef` decided from ticket frontmatter |
| Claude `--from-pr` (CLI) | stable | A simple convenience feature | Bet 4: auto-load PR context for ultrareview evals |

(Note: `personality`/`fast_mode`/`enable_request_compression` show up as stable enabled in 0.130.0's `codex features list`, with their exact CLI surfaces controlled by `~/.codex/config.toml` profile/flag. This document's bets only go to the level of "make a config" and do not depend on undocumented internal APIs.)

## 3.5 Subagent + memory subsystems — two surfaces to call out once more

### 3.5.1 Subagent (Agent tool, multi_agent flag)

Claude's `Agent` tool and Codex's `multi_agent` (stable) both spawn *workers*. CT2's current model is "lens-cc is the Claude session itself, lens-cx is the Codex session itself" — i.e., *process-level isolation*. But when forge handles a large ticket, it is possible — and increasingly common — to internally summon explorer/reviewer helper subagents.

Rules to apply to CT2 immediately:

- **A subagent cannot hold ticket authority.** Subagents *do not write* ticket frontmatter, sidecar, or inbox messages. The parent role writes the aggregated result.
- **A subagent's budget is included in the parent's budget envelope** (paired with Bet 1). I.e., if forge spawns 3 subagents, their token cost adds to forge's ticket budget.
- **Subagent isolation is via worktree** (Claude `isolation: worktree`, Codex `multi_agent` cap). Verifying disjoint write sets is the parent role's responsibility.
- **lens roles do not spawn subagents.** Since independence is essential, a reviewer summoning a helper LLM is itself *external signal injection*. This rule is codified in `spec/review-protocol.md`.

### 3.5.2 Memory subsystem — given we already have one, what more?

Claude has *project-scoped auto-memory* via `~/.claude/projects/<encoded-cwd>/memory/MEMORY.md` plus individual memory files. Codex has `memories` (experimental) + Chronicle. CT2 is a protocol with `spec/`, `CLAUDE.md`, and `AGENTS.md` as *explicit authority documents*, so there is potential for conflict with vendor memory.

CT2's explicit stance:

| Information type | Where it lives | Why |
|---|---|---|
| Project facts (architecture, file locations, coding conventions) | `spec/`, `AGENTS.md`, `CLAUDE.md` | Authority documents, PR-trackable |
| User preferences (manual/automatic) | Vendor memory (Claude `MEMORY.md`, Codex memories) | Per-user, portable across projects |
| User ↔ CT2 collaboration rules (e.g., "lens is always skeptical-short") | role-contract YAML (Bet 1), eval rubric (Bet 4) | Measurable, regression-detectable |
| In-progress ticket/sidecar/inbox | `.ct2/` | Single source of truth |
| Cross-session *traces of an agent's prior reasoning* | *Allowed* to be recorded into vendor memory — but ticket decisions do not depend on it | "What the agent saw yesterday" must not become ticket authority |

**Additional spec rule (alongside the Bet 1 PR):** "Information read from vendor memory cannot be cited as *evidence source* in ticket frontmatter/sidecar. A ticket's decision basis is only the ticket body, the spec, and code hunks explicitly cited."

This is also verifiable via the Bet 4 eval: given the same input + same role MD, if results diverge substantially between two environments with *different memory states* → it is a signal that the role MD depends on implicit memory.

## 4. Five product bets

Each bet uses the following format: **problem → hypothesis → shape → success metrics → scope-out → dependencies → risks.**

---

### Bet 1: Cost-aware role contracts

> **Status update (2026-06-23) — partially superseded.** The *measurable contract* portion of Bet 1 shipped: per-role contracts in `config/harness.yaml`, the `bin/ct2-role-run` cost-telemetry wrapper, and `bin/ct2-cost` folded into `ct2-status`. The **automatic budget-violation enforcement** described below — passing `--max-budget-usd`/`--effort` to the provider and acting on `on_budget_exceeded: hard_deny`/`bounce` — was **not implemented, and is now superseded** by the later [dynamic-workflow strategy (2026-06)](ct2-dynamic-workflow-strategy-2026-06.md) §4, which adopts the position that *CT2 does not enforce a token budget*: a budget directive is recorded only as an **advisory fan-out width**, and blast radius is bounded by the existing time/round circuit breakers (`ct2-duration-check`, `ct2-review-watchdog`, `max_review_rounds`) plus agent-count/isolation/scope — not by a cost gate. Treat the `budget_per_*_usd` / `on_budget_exceeded` design below as historical (won't-do), and the cost axis as advisory observability only.

#### 4.1.1 Problem

CT2 currently has all roles using (effectively) *the same model, the same effort, and the same personality*. This creates four problems at once: (a) cost inefficiency, (b) quality variance, (c) latency blowups, (d) impossibility of post-hoc measurement.

Concrete evidence:

- helm does *generative/exploratory* work (breaking requirements into tickets). On the cost-vs-quality trade-off, you should buy quality → Opus-class / `xhigh` effort / `personality: interrogative`.
- forge does *convergent/executive* work (spec → patch). Cost efficiency comes first → Sonnet/Haiku-class / `high` effort / `personality: terse`.
- lens does *judgment/verification* work. Consistency of decisions comes first → personality fixed, effort medium, `fast_mode` forbidden.
- status is *pure read*. → pin `fast_mode`, low effort, the cheapest model possible.
- reconciler is *deterministic*. → Ideally no LLM, just bash. It already is (keep it).

Right now all these differences are *implicit*, scattered across English prompts inside the role MDs. Nothing is measured.

#### 4.1.2 Hypothesis

If we explicitly declare a *contract* per role — `(model, effort, personality, budget_per_ticket_usd, latency_slo_seconds, fast_mode, request_compression)` — then (a) $/ticket becomes measurable, (b) violations enable automatic blocking/escalation, and (c) changes become PR-trackable.

#### 4.1.3 Shape

A new `role_contracts` block in `harness.yaml`:

```yaml
role_contracts:
  ct2-helm:
    model: opus
    effort: xhigh
    personality: interrogative   # codex; for claude this maps to skill prompt preamble
    budget_per_session_usd: 2.50
    latency_slo_seconds: 120
    request_compression: false
    fast_mode: false
    on_budget_exceeded: hard_deny  # block further LLM calls; require manual /unblock
  ct2-forge:
    model: sonnet
    effort: high
    personality: terse
    budget_per_ticket_usd: 1.50
    latency_slo_seconds: 600
    request_compression: true       # large thread tolerance
    fast_mode: false
    on_budget_exceeded: bounce      # send budget-exceeded inbox; ticket → backlog
  ct2-lens-cc:
    model: opus                     # judgment over speed
    effort: high
    personality: skeptical-short
    budget_per_review_usd: 0.40
    latency_slo_seconds: 90
    fast_mode: false                 # never on review
    request_compression: true
  ct2-lens-cx:
    model: gpt-5.4-default
    effort: high
    personality: skeptical-short
    budget_per_review_usd: 0.40
    latency_slo_seconds: 90
    fast_mode: false
  ct2-status:
    model: haiku
    effort: low
    personality: terse
    budget_per_run_usd: 0.05
    latency_slo_seconds: 8
    fast_mode: true
    request_compression: false
```

CLI integration (example — Claude side):

```bash
# Wrapper called by claude-plugin/skills/ct2-forge/SKILL.md
claude \
  --agent ct2-forge \
  --model "${CT2_FORGE_MODEL:-sonnet}" \
  --effort "${CT2_FORGE_EFFORT:-high}" \
  --max-budget-usd "${CT2_FORGE_BUDGET:-1.50}" \
  --include-hook-events \
  -p "$(cat .ct2/in-progress/${TICKET}.md)"
```

Codex side: a profile per role:

```toml
# ~/.codex/profiles/ct2-forge.toml
model = "gpt-5-codex"
effort = "high"
personality = "terse"
fast_mode = false
enable_request_compression = true
```

New tool: `bin/ct2-cost` — reads `.ct2/telemetry/cost.jsonl` and outputs (a) cumulative cost by role × ticket, (b) SLO violation events, (c) remaining budget. Folded into `ct2-status` as a single line.

#### 4.1.4 Success metrics

- **$/ticket (p50)** drops 30% vs. baseline (when forge is properly demoted to sonnet/haiku)
- **lens latency p95** ≤ 90 seconds
- Budget hard_deny firings within a quarter ≥ 0 (i.e., budget *worked* as an SLO gate and blocked unconverged work)
- Achieve the above cost effect *without* dropping Trust ratio

#### 4.1.5 Scope-out

- An LLM router (automatic model selection) is *not* included in this bet. Decisions start with static contracts. Revisit a router in 6 months.
- Per-user caps and organization-level limits are out of scope (single-user product).

#### 4.1.6 Dependencies

- Feature Radar's P0 Capability Registry — knowing in which roles `--max-budget-usd`/effort is actually available is required to enforce a contract.
- Confirming the exact config surface of Codex's `personality`, `fast_mode`, and `enable_request_compression` — they show stable in `codex` 0.130.0, but at the time of writing they are not explicitly documented on the spec page, so a **1-day spike** measures them empirically before finalizing contract shape.

#### 4.1.7 Risks

| Risk | Mitigation |
|---|---|
| Trust ratio drops after demoting forge to Sonnet | A/B: process 50 tickets under the new contract and compare Trust ratio; on regression, model-upgrade option |
| `--max-budget-usd` cuts off *mid-work*, mass-producing partially complete tickets | When the budget cuts, forge `bounce`s (in-progress → backlog); *never commit a partial patch* |
| Codex personality preset affects lens's reviewer-independence | Use personality only as a *style* layer; keep decision logic in the spec/role MD |

---

### Bet 2: Plan-mode-first forge

#### 4.2.1 Problem

Currently, when forge receives a ticket, it dives *straight into coding*. The result:

- Ticket ambiguity surfaces in forge's first patch → lens rejection → rework
- forge's plan (which functions to modify how) survives only as a commit message or sidecar response *after the fact*. Post-hoc verification is impossible.
- This is the exact opposite of the LLM cost curve, which says "planning is free, coding is expensive."

#### 4.2.2 Hypothesis

If we force the structure so that forge *always* starts with `EnterPlanMode` and only enters `ExitPlanMode` after sealing the plan, then (a) ambiguity surfaces *before* code is written, and (b) the plan itself is preserved as a ticket sidecar (`.ct2/plans/{id}-r{n}.md`) so lens can review the plan and patch *together*.

#### 4.2.3 Shape

Ticket lifecycle extension:

```
backlog → in-progress(planning) → in-progress(executing) → in-review
              │                          ▲
              │ EnterPlanMode →          │ ExitPlanMode (plan approved)
              │ plan written to          │ + plan saved to .ct2/plans/{id}-r{n}.md
              │ .ct2/.tmp/plan-...md     │
              ▼                          │
          plan-stale?  ──No──────────────┘
              │ Yes
              ▼
         abort, bounce to backlog
```

New spec rule (review-protocol.md addition):

> **Plan-evidence rule.** A lens sidecar must satisfy one of:
> (a) `.ct2/plans/{id}-r{n}.md` exists and the sidecar's "Plan adherence" section has evaluated how well the patch aligns with the plan.
> (b) The ticket has `plan-exempt: true` and is a simple ticket with 3 or fewer Acceptance Criteria.

Codex-side mapping: `goals` + `tool_search`. On ticket entry, forge creates a `/goal` → uses `tool_search` to explore candidate surfaces → the goal note is converted into a plan and saved under `.ct2/plans/`.

#### 4.2.4 Success metrics

- review-round=1 first-pass approval rate rises by ≥ +15pp
- p50 ticket completion time *does not increase* vs. baseline (the plan phase offsets code rework time)
- frequency of "scope creep" callouts in lens sidecars −50%

#### 4.2.5 Scope-out

- Do not force plan-mode on helm/lens (these are inherently plan-shaped work).
- "Have an LLM auto-validate the plan" is out of scope. The plan is part of the ticket and reviewed by a lens human/model.

#### 4.2.6 Dependencies

- Claude 2.1.136's plan-mode write-block fix (earlier versions had a bug where file writes leaked in plan mode — local 2.1.138 is OK).
- Stabilization of Codex `goals` (currently experimental); when `goals` GAs, the mapping becomes more robust.

#### 4.2.7 Risks

| Risk | Mitigation |
|---|---|
| Forcing plan-mode is too heavy and creates friction for simple tickets | `plan-exempt: true` flag in ticket frontmatter |
| When plan and patch diverge, lens mistakenly treats the plan as *truth* | Specify in the spec: "Acceptance Criteria are truth; the plan is trace" |
| Codex `goals` is experimental | Adopt Claude plan-mode first; allow Codex to fall back (goal-less plan note) |

---

### Bet 3: Ambient CT2 — async agents over channels

#### 4.3.1 Problem

CT2 only starts when the user *opens a terminal*. Result:

- A PR comment that arrived at midnight goes unnoticed by forge until next morning.
- If a colleague (or a future multi-person user) says "raise the priority of this ticket" on Slack, it cannot get in.
- Even when helm writes "I need this clarification" into the inbox, if the user doesn't look, it stalls.

This is less a "collaboration tool" and more the limit of a "command-line assistant."

#### 4.3.2 Hypothesis

If we place a *thin bidirectional bridge* between the CT2 inbox and external channels (Discord/Slack/Gmail/Notion), CT2 starts working *outside the terminal*. The key is: "Outside parties *do not modify* tickets — `.ct2/` is still the single source of truth — but messages/notifications/delegation requests flow freely."

#### 4.3.3 Shape

```
                ┌──────────────────────────────────┐
                │       External channels          │
                │ Discord / Slack / Gmail / Notion │
                └──────────────────────────────────┘
                          ▲              │
                  (notify)│              │(command)
                          │              ▼
                ┌──────────────────────────────────┐
                │       ct2-bridge                 │
                │  - PushNotification on inbox new │
                │  - RemoteTrigger on /ct2 command │
                │  - SendMessage→inbox             │
                │  - filter: never modifies tickets│
                └──────────────────────────────────┘
                          ▲              │
                          │              ▼
                ┌──────────────────────────────────┐
                │        .ct2/inbox/{role}/        │
                │   (single source of truth)       │
                └──────────────────────────────────┘
```

Supported external actions (whitelist):

| External command | Effect | Permission |
|---|---|---|
| `/ct2 status` | Posts a one-line `ct2-status` summary in the channel | Everyone |
| `/ct2 priority {id} {p0|p1|p2}` | Writes a priority-override message to the helm inbox | Explicit ALLOW users |
| `/ct2 unblock {id}` | Clears blocked in inbox, resumes forge | Explicit ALLOW |
| `/ct2 clarify {id}: <text>` | helm → forge clarification message | Explicit ALLOW |
| (anything else) | Rejected. Direct ticket editing is *permanently* impossible from outside | — |

Notification triggers (PushNotification):

- escalated reached (human intervention required)
- a blocked message arrived in the helm inbox → unresolved for a threshold (e.g., 30 minutes)
- ultrareview finds a critical issue
- ~~budget hard_deny fires~~ *(superseded — CT2 does not enforce token budgets; see Bet 1 status note)*
- nightly summary (optional)

#### 4.3.4 Success metrics

- p95 "blocked → unblocked" wallclock time drops 70% vs. baseline
- *0* attempts to change tickets directly via external channels (= invariant preserved)
- User survey: "I can hand work to forge before bed and things are fine when I wake up" response ≥ 4/5

#### 4.3.5 Scope-out

- Multi-user ticket editing / ownership split is out of scope (single-user assumption retained).
- Do not bind the bridge to either Claude or Codex — implement it as a separate bash daemon (to obey the zero-external-deps rule, use only the `gh`, `discord`/`slack` MCPs).

#### 4.3.6 Dependencies

- Stability of the Discord MCP / Slack MCP (currently connected).
- `PushNotification`/`RemoteTrigger` permissions — under a Claude `--remote-control` session.

#### 4.3.7 Risks

| Risk | Mitigation |
|---|---|
| The "edit tickets from outside" temptation → invariant collapse | Strict whitelist inside the bridge; direct writes to ticket files are *impossible* in code |
| Notification flood (noise) | Per-channel daily/hourly cap; dedup window for same-kind notifications |
| Secret leakage to Slack/Discord | The bridge *never* sends ticket body/sidecar content outward — only id/title/state |

---

### Bet 4: Eval harness for roles

#### 4.4.1 Problem

CT2 role definitions (`config/ct2-lens-cc-role.md`, `config/ct2-lens-cx-role.md`, plugin SKILL.md) are *code* but have *no tests*. Change a role MD by one line and:

- forge can become more conservative/aggressive
- lens can grade the same patch differently than yesterday
- helm can change how it handles ambiguity

But we have no way to *measure* this. As a result, role MD edits run on "vibes", and regressions go uncaught.

#### 4.4.2 Hypothesis

Using `skill-creator`'s evals pattern + `claude --json-schema` + `claude --bare`, build a *fixed-input regression suite* per role so that the impact of changes to role MD/skill MD/role config can be captured *numerically*.

#### 4.4.3 Shape

```
.ct2/evals/
├── ct2-helm/
│   ├── case-001-vague-feature-request/
│   │   ├── input.md         # Raw user request thrown at helm
│   │   ├── expected.json    # Expected ticket frontmatter (subset match)
│   │   └── rubric.md        # Qualitative criteria a human can read and score
│   └── case-002-...
├── ct2-forge/
│   ├── case-001-clear-spec/
│   │   ├── repo-snapshot.tar  # Mini repo forge will work in
│   │   ├── ticket.md
│   │   ├── expected-files/    # Expected patch result
│   │   └── rubric.md
│   └── ...
├── ct2-lens-cc/
│   └── case-001-buggy-patch/
│       ├── ticket.md
│       ├── patch.diff
│       └── expected-sidecar.json  # Expected verdict, expected issue keywords
└── runner.sh
```

For each case, `runner.sh`:

1. Unfurls case materials into a clean temp directory.
2. Runs `claude --bare --agent ct2-{role} --json-schema <schema> -p <input>` — `--bare` removes external variables (auto-memory, hooks, plugin sync).
3. Compares results against `expected-*.json` via deep-subset match + qualitative LLM-as-judge scoring (`/ultrareview`?? — no, too much dependency; just call a separate cheap claude for scoring).
4. Accumulates score rows per role × case × commit into `.ct2/evals/results.jsonl`.

New ticket type: `eval-regression` — when a role-MD edit PR comes in, this ticket is auto-created and reports regression vs. baseline.

#### 4.4.4 Success metrics

- Ratio of role-MD-change PRs blocked by eval regression ≥ 1 per quarter (= the harness is actually catching regressions)
- ≥ 5 eval cases per role land within 6 weeks
- Cost of one runner invocation ≤ $0.50 / role (combined with Bet 1)

#### 4.4.5 Scope-out

- "Have an LLM auto-optimize a role" — out of scope. Evals are *defensive*; evolution is human.
- helm/forge evals stay on small fixture repos only — real-repo regressions are too expensive and non-deterministic.

#### 4.4.6 Dependencies

- Stable behavior of `--bare` mode.
- `--json-schema` (currently stable).
- (Optional) the `skill-creator` skill — we don't build it, we fold it in.

#### 4.4.7 Risks

| Risk | Mitigation |
|---|---|
| LLM-as-judge non-determinism → noisy evals | Prefer rubric-based quantitative metrics; LLM scoring is a secondary metric |
| Eval suite *overfits* to prompts | Source new cases from *real-ticket samples* rather than just chasing a specific PR regression |
| Eval cost breaks the contract budget | Runner has a separate budget envelope; isolated from ticket budgets |

---

### Bet 5: Native task graph mirror (advisory)

#### 4.5.1 Problem

CT2 tickets are files, and runtimes (Claude `TaskList`, Codex `multi_agent`) have their own task representations. The two are *completely separate*, so:

- Inside a Claude session, "what is CT2 doing right now?" is invisible — it doesn't show in `TaskList`.
- Even when the runtime is making background progress on tasks, it does not reflect in ticket progress.
- The user has to look at tasks in the runtime UI, then at tickets in `ct2-status` again — cognitive load ↑.

Claude `TaskCreate` natively supports `blockedBy` dependencies. This maps naturally onto CT2 ticket dependencies (currently absent).

#### 4.5.2 Hypothesis

If we *advisorily* mirror tickets to native tasks on state change — but block native tasks from *changing* ticket state — we gain cognitive unity without losing authority.

Why this is the *last* bet: it carries the greatest risk of flowing backwards. Native tasks may feel so convenient that the user starts working on them and the sync with tickets breaks.

#### 4.5.3 Shape

Direction: **CT2 → native = OK, native → CT2 = blocked**.

```
ct2-status / ticket transition:
  → for each ticket in {backlog, in-progress, in-review}:
       TaskCreate (if not present) with metadata:
         {ct2_ticket_id: "001", ct2_state: "in-progress", ct2_round: 0}
       TaskUpdate (if present) status to mirror ticket state:
         backlog → pending
         in-progress → in_progress
         in-review → in_progress (with note "in review")
         done → completed
         rejected → pending (with note)
         escalated → completed (with note "escalated, needs human")

native TaskUpdate hook (PreToolUse):
  → if task has ct2_ticket_id metadata and update is from non-CT2 source:
       block with message "CT2 tickets are authoritative; edit .ct2/{id}.md"
```

CT2 ticket frontmatter extension (optional):

```yaml
depends_on: ["003-refactor-pool", "008-migration"]
```

→ Mapped to `TaskCreate(addBlockedBy=[task_id_of_003, task_id_of_008])`.

#### 4.5.4 Success metrics

- User survey: "Are tickets and native tasks in agreement?" → ≥ 4/5
- "Cases where ticket state was changed incorrectly via a native task" → 0
- Mirror sync latency p95 < 5 seconds

#### 4.5.5 Scope-out

- Bidirectional sync — *permanently* out of scope. Authority divergence breaks CT2 identity.
- TeamCreate/SendMessage integration — sits behind the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` gate and is not depended on by this branch. Monitor.

#### 4.5.6 Dependencies

- Claude `TaskCreate/TaskUpdate` (stable).
- Need a spike to confirm whether the PreToolUse hook can inspect metadata (can be checked in the same environment as Bet 4 evals).

#### 4.5.7 Risks

| Risk | Mitigation |
|---|---|
| Sync between native task and ticket breaks | When the reconciler detects mismatches on each loop, force sync with ticket as *primary*; log mismatch events |
| User directly edits native tasks to change the dependency graph | Block with a hook; show a friendly message on block |
| TaskCreate API change | Claude version pin (folds naturally into the Capability Registry — Feature Radar P0) |

---

## 5. Priority and sequencing

### 5.1 Why this order

**Phase 0 (Registry+Baseline) first** — Without knowing which runtime features are actually available and what the current trust/evidence/autonomy/cost baselines are, no bet's product impact can be judged. Capability Registry and empirical baselines are not bets; they are admission gates.

**Bet 1 (Cost contracts) second** — Cost/latency must be *measurable* before the impact of other bets can be evaluated. The ROI denominator of every other bet.

**Bet 2 (Plan-mode-first) third** — Directly affects Trust ratio and Evidence coverage. Reducing forge rework improves lens latency, $/ticket, and p50 latency all at once.

**Bet 4 (Eval) fourth** — Locks in the changes that Bets 1 and 2 produce so they *don't regress*. Safety net before stepping into Bets 3 and 5.

**Bet 3 (Ambient) fifth** — A UX improvement, but carries invariant risk. Adopt after eval/contracts are in place.

**Bet 5 (Task mirror) last** — The *most seductive and most dangerous*. The temptation to create authority divergence because native tasks look nicer. Only experiment with it after the other four are stable.

### 5.2 6-week sprint plan

| Week | Bet | Deliverables | Exit criteria |
|---|---|---|---|
| 0-1 | Phase 0 Registry+Baseline | `ct2-runtime-doctor`, `bin/ct2-baseline`, `.ct2/telemetry/baseline-2026-05.json` | Codex/Claude capability and balanced-scorecard baseline recorded; no state mutation |
| 1 | Bet 1 spike | Empirical report on Codex `personality`/`fast_mode`/`enable_request_compression`; `harness.yaml` `role_contracts` draft | All 5 roles sit inside a contract; CLI dry-run verifies it |
| 2 | Bet 1 impl | Role wrapper scripts, `bin/ct2-cost`, telemetry sink | Over 1 week of real ticket processing, cost.jsonl is recorded and surfaces in `ct2-status` |
| 3 | Bet 2 spike + impl | Plan-mode integration, `.ct2/plans/` directory, spec update PR | 5 tickets processed plan-mode-first; first-pass approval compared |
| 4 | Bet 4 baseline | 3-case eval suite per helm/forge/lens, runner.sh, baseline measurement | A deliberate one-line role MD change gets caught by the eval |
| 5 | Bet 3 phase-1 | `ct2-bridge` daemon, Discord/Slack notify-only (read-only), notification policy | Logs of 5 PushNotification sends; 0 ticket-modification attempts |
| 6 | Buffer + retro | Postmortem, first balanced-scorecard measurement, Bet 5 spike (no actual mirroring) | Trust/Evidence/Autonomy/Cost scorecard report; next 6-week plan |

### 5.2.1 Empirical baseline plan — "do not bet without measurement"

Every metric in this document is expressed *relative to baseline*. But CT2 currently has no measurement infrastructure for cost/latency/trust/evidence/autonomy. To start betting, *at minimum* the following baselines are needed. Run this first in Phase 0 and parallelize only the items compatible with the Bet 1 spike.

| Baseline | Collection method | Window | Target sample |
|---|---|---|---|
| Trust ratio (current) | `git log --grep "ct2-revise"` + regression analysis of the `done/` directory. Count whether tickets that reached done were revised/reverted/reopened by timepoint. | Past 90 days of git history retrospect | ≥ 20 done tickets |
| First-pass approval rate | Distribution of `*-r0` sidecar verdicts in `.ct2/reviews/` (where present) | Past 90 days | ≥ 20 review events |
| Evidence coverage | Ratio of `done/` transition tickets that have a sidecar, command evidence, and verifier result attached | Past 90 days | ≥ 20 done tickets |
| $/ticket | **No collection infrastructure** — included in the Bet 1 spike deliverables. Baseline is constructed after week 0. | Weeks 1–2, in parallel | All tickets processed in this sprint |
| Ticket latency (sealed → done) | Difference between ticket frontmatter `sealed` and `updated` (when verdict=approved) | Past 90 days | ≥ 20 |
| Review latency (in-review entry → reconciler verdict) | Cross of `.ct2/reviews/` mtime and ticket mtime | Past 90 days | ≥ 20 |
| Blocked → unblocked latency | mtime of `.ct2/inbox/{role}/done/` blocked messages → mtime of the next helm reply message | Past 90 days | ≥ 5 (rare event) |

**Deliverables**: `bin/ct2-baseline` (one-off Python script, stdlib only), `.ct2/telemetry/baseline-2026-05.json`. Every "vs. baseline" number in §9's success metrics references this file. For metrics where no baseline can be obtained (especially $/ticket), *starting measurement* within this sprint is itself the deliverable — record it as "starting from baseline 0".

**Important honesty.** When real data is scarce (e.g., only 5 done tickets), p50/p95 statistics are meaningless. In that case, simplify metrics into *ratios* (like win rate), and replace with fresh sprint data at the end of 6 weeks. We do not claim "trust ratio 0.92" before the statistics gain meaning.

### 5.3 90-day vision

- Bet 3 phase-2 (activate external command whitelist)
- Activate Bet 5 mirror (advisory only)
- 30+ eval cases per role
- Automatic eval CI on every PR
- A `.ct2/runtime/sessions.json` registry for multi-machine use

### 5.4 12-month vision

- Cloud delegation pilot (folds with Feature Radar's P2) — *advisory only, ticket authority preserved*
- Multi-tenant experiment — how two people share tickets in the same repo *without* breaking the single-user rule
- Multimodal evidence (Feature Radar P2)
- "CT2 as plugin marketplace" — other teams build and share their own roles

## 6. Anti-bets — seductive but refused

The following 6 we consciously *do not* do. Each comes with an explicit refusal reason — so future PRs/proposals can be refused by citing this section.

| Anti-bet | Seduction | Refusal reason |
|---|---|---|
| **A vendor scheduler marks tickets done** | The ultimate automation | Dual-review authority forks into a vendor cron. CT2 identity collapses. |
| **An image is sole evidence** | UI tickets close fast | Without a verifiable text trace, "why was it approved" cannot be reconstructed after the fact |
| **Delegating the ticket lifecycle to the cloud (Codex Cloud, Claude Routines)** | Continuously running background automation | Breaks the rule that `.ct2/` is authority. Cloud is *executor* only, never *judge*. |
| **TeamCreate/SendMessage replaces the inbox** | Runtime-native primitives | 1) Behind an experimental flag, 2) message *per-instance persistence* is weaker than the inbox's simplicity |
| **An auto LLM router** | Auto-optimize cost/quality per role | Without even static contracts in place, a router adds undebuggable variance |
| **Have an LLM auto-evolve roles** | "Self-improving CT2" | Breaks the design rule that humans must be able to *read* roles. Evals are regression *defense*; evolution is human. |

## 6.5 Kill criteria — *when do we cut a bet*

Pinning only success metrics is risky. The "stay in because of sunk cost even though it isn't working" trap. *Kill criteria* per bet — at the 3-week mid-point, if any trigger below fires, the bet is halted or reshaped.

| Bet | 3-week kill trigger | 6-week kill trigger |
|---|---|---|
| **1 Cost contracts** | At the spike, ≥ 2 of `personality`/`fast_mode`/`request_compression` do not actually work (docs say stable but measurements disagree) | $/ticket failed to drop 30% *and* trust ratio also dropped — both failed, scrap the contracts entirely |
| **2 Plan-mode-first** | In the first 3 tickets, the plan→patch flow blows up user friction (i.e., helm/forge cannot exit plan mode) | First-pass approval rate misses +15pp *and* p50 ticket latency rose 20%+ — only cost went up |
| **3 Ambient bridge** | Of the first 5 notifications, ≥ 1 is a false alarm or duplicate noise | Even one external ticket-modification attempt occurs — invariant broken |
| **4 Eval harness** | A single runner invocation costs $5+ (per-case cost explodes) | 4-week cumulative regression detections = 0 — the eval suite is catching only noise |
| **5 Task mirror** | At the spike, PreToolUse hook cannot inspect metadata — no blocking mechanism | Mismatch events (tickets diverging from native tasks) occur more than once per day/run — sync cost exceeds visibility ROI |

When killing, leave the following trail: `.ct2/postmortems/bet-{n}-kill-{date}.md` — reason, measurements, alternatives. A killed bet is *not retried in the same shape within 3 months* (a different shape is OK).

### 6.6 Per-bet spec PR list — what we pin to spec

The spec changes each bet will create. Code PRs are separate; this is only *authority document* PRs.

| Bet | New spec file | Existing spec edits |
|---|---|---|
| 1 Cost contracts | `spec/role-contracts.md` (new) | Budget-bounce transition in `spec/state-machine.md`; `role_contracts` block in the `config/harness.yaml` template |
| 2 Plan-mode-first | `spec/plan-evidence.md` (new) | Plan-evidence rule in `spec/review-protocol.md`; `plan-exempt` field in `spec/ticket-format.md`; in-progress split in `spec/state-machine.md` |
| 3 Ambient bridge | `spec/external-channels.md` (new) | Handling of external-origin messages in the inbox section of `spec/review-protocol.md` |
| 4 Eval harness | `spec/role-evals.md` (new) | Eval-application obligation in `config/ct2-lens-*-role.md`; `AGENTS.md` requires eval pass on role-MD changes |
| 5 Task mirror | `spec/runtime-mirror.md` (new) | Mirror-sync rules in `spec/state-machine.md`; `.ct2/runtime/mirror/` in `spec/directory-structure.md` |

To preserve the consistency of CT2's spirit ("spec is authoritative"), **code PRs proceed only after the corresponding spec PR is merged**. If the spec PR fails to land in the intended shape, the bet itself is reshaped.

## 7. Hidden primitives — where they are buried

This section indexes surfaces that Feature Radar *omitted or treated lightly* and that are not used directly by these bets but may be raw material for follow-up bets. Index only.

- **Codex `tool_call_mcp_elicitation` (stable).** MCP tools can elicit from the user — a candidate for verifying external-channel commands in Bet 3.
- **Codex `enable_request_compression` (stable).** Partially used by Bet 1. Forcing it on long-thread roles like helm-auto-cx yields large token savings.
- **Codex `image_generation` + `image_input` + `view_image` (stable).** For *visual specs* on UI tickets. Folds in with Feature Radar P2 multimodality.
- **Claude `--exclude-dynamic-system-prompt-sections` (CLI).** Improves prompt cache hit rate — auxiliary cost lever for Bet 1.
- **Claude `--include-hook-events` (CLI).** Used in Bet 4 evals to verify hook-firing traces.
- **Claude `--fork-session` (CLI).** When lens reviews the same ticket from two angles (e.g., security + perf) — a follow-up bet candidate.
- **Claude `LSP` tool.** forge *automatically* notices type errors after a patch. Helps lens sidecars verify "AC: tests pass".
- **Codex `child_agents_md` (under development).** Per-subagent AGENTS.md separation — once stable, very strong for *complete isolation* of lens-cc/lens-cx. Revisit in 6 months.
- **Claude `claude project purge` (2.1.126+).** Cleanup of temporary ticket workspaces.
- **Claude `--from-pr`.** lens loads PR context into the review.

## 8. Risk register

| ID | Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| R-01 | Bet 1 contract drops the trust ratio | High | Mid | A/B with a 50-ticket window; model-upgrade by one notch on regression |
| R-02 | Forced plan-mode creates user friction | Mid | Mid | `plan-exempt` flag; measure user NPS after 6 weeks |
| R-03 | Secret leakage from the Discord/Slack bridge | High | Low | Never send bodies outward; only id/title/state |
| R-04 | Eval cost breaks the cost contract | Mid | Mid | Separate budget envelope; daily cap |
| R-05 | Native task mirror authority divergence | High | Mid | Place Bet 5 last; advisory-only; blocking hook |
| R-06 | Deep dependence on a Codex experimental feature (`goals`) | Mid | Mid | Adopt Claude plan-mode first; Codex is fallback |
| R-07 | Vendor version drift | Mid | High | Folds into the Capability Registry (Feature Radar P0); min-version gate |
| R-08 | "Always-on" Bet 3 explodes cognitive load (notification hell) | Mid | Mid | Per-channel cap, dedup, snooze |
| R-09 | Role-MD-change PR *overfits* to pass evals | Low | Mid | Source cases from real-ticket samples; rotate cases quarterly |
| R-10 | Single-user assumption breaks in real use (shared repo, 2-person use) | Mid | Low | Defer to the 12-month vision; explicit refusal before then |

## 9. Success metrics — how we know "things went well"

Self-grade after 90 days against the following balanced scorecard:

1. **Trust:** Trust ratio (90d) ≥ 0.92; first-pass approval rate baseline +15pp
2. **Evidence:** Evidence coverage ≥ 0.90; 0 uncited verifiers among `done/` transitions
3. **Autonomy:** lens latency p95 ≤ 90 seconds; blocked → unblocked p95 wallclock baseline −70%; 0 stale runtime twins
4. **Cost/Latency:** $/ticket p50 baseline −30%; p50 ticket latency does not rise vs. baseline
5. **Safety:** eval suite size ≥ 5 cases × 4 roles = 20+; 0 external ticket modifications; 0 dual-review bypasses; 0 done-issuances by a vendor scheduler

We do not call it success if a gain on one axis collapses another. For example, even if cost drops 30%, if Trust or Evidence falls, Bet 1 is reshaped.

## 10. Relationship to Feature Radar — exactly how they merge

| Feature Radar item | Treatment in this document |
|---|---|
| P0 Capability Registry | **Adopt as-is**. Prerequisite for Bet 1 contract enforcement. |
| P0 Decision Bridge | **Adopt as-is**. The path Bet 3 external commands take to become internal decisions. |
| P0 Hook Guardrails | **Adopt as-is**. Reused as the PreToolUse blocking hook in Bet 5 mirror. |
| P1 Watch/Monitor Plane | **Redefined**. Repositioned as "wakeup infrastructure" — folds into Bet 3's *notification policy engine*. |
| P1 Runtime Driver Hardening | **Adopt as-is**. Bet 1 depends on the driver's cost-measurement path. |
| P1 Dual Plugin Distribution | **Defer**. After the 6-week sprint, within the 90-day vision. Protocol stability comes before plugin stability. |
| P1 Observability Ledger | **Adopt as-is**. Same infrastructure as Bet 1's telemetry sink. |
| P2 Multimodal Evidence | **Retain**. After 90 days. Low priority until UI work increases. |
| P2 Cloud Delegation | **Skeptical retain**. Close to Anti-bet 3 — *executor only*. |

Summary: Feature Radar's three P0s are the *kernel admission layer* of Verified Autonomy OS, one or two P1s are *direct dependencies* of this document's bets, and the rest of P1 and P2 are *re-evaluated after 6 weeks*. The final integrated document rebundles this relationship in terms of OS primitives and a release train.

## 10.5 Competitive landscape — other systems solving similar problems

To define *where CT2 will sit*, we explicitly contrast against adjacent product families. This comparison is the standard of a frontier-tech PRD ("we are different from X, and that is why we have a place of our own"). The table below is not a general evaluation but *a comparison through CT2's frame*.

| System | Main position | Largest commonality with us | Largest difference from us | What CT2 might borrow |
|---|---|---|---|---|
| **Cursor** | IDE-embedded single-agent assistant | Ticket-like context beside code | No review independence, not dual-LLM | None — different place |
| **Aider** | git-aware single-agent CLI | git-workflow integration, file-system-first | No dual-review, not plan-mode-first | The partial-commit flow is compatible with ct2-git-* |
| **AutoGen** (MS) | Multi-agent conversation framework | Multi-agent | "Conversation" is authority — not files; verifiability is weak | Role definition patterns (in a different shape) |
| **CrewAI** | Task graph orchestration | Task graph | Python-bound (external dependency), violates our rule | Graph dependency visualization at most |
| **Smol Developer / GPT-Engineer** | Start-to-end auto-generation | Delegating LLM work | No review/iteration, 1-shot | Useful as a 1-shot baseline in Bet 4 evals |
| **Devin (Cognition)** | Autonomous SWE | Autonomous | No dual-review, opaque verification, SaaS only | Bet 3 ambient — async style |
| **OpenHands (formerly OpenDevin)** | Open-source SWE agent | Open, file-based | Single-agent centric, no dual-review | The sandboxing model (compare with Codex `unified_exec`) |
| **Claude Projects / OpenAI Projects** | Vendor-internal context store | Reuse within the same vendor | Authority is the vendor cloud, not files | User-memory integration (§3.5.2) |
| **Linear / Jira + Copilot** | PM tool + AI helper | Ticket concept | Spec/code separated, far from dev workflow | None — different place |
| **Anthropic Computer Use / OpenAI Operator** | OS-level automation | Attempts a verifiable trail | GUI tasks, not code review | Screenshot evidence (Feature Radar P2) |

**CT2's one-line differentiator**: "A single-user, file-system-first harness where two *mutually unaware* LLMs *each* validate the same patch and the trace is preserved as an immutable file." None of the above occupy this position exactly. "Differential testing for LLM patches" — i.e., *dual-LLM regression validation* — is the market segment we will earnestly claim.

As long as this differentiation does not waver, this document's bets must not get dragged in a "make it like Cursor / make it like Devin" direction. §6's anti-bets are the line of defense.

## 11. Decision log — major forks adopted/rejected during authoring

| Fork | Adopted? | Reason |
|---|---|---|
| "Adopt Verified Autonomy OS as the canonical name" | Adopted | Elevates Feature Radar's strong protocol framing into product identity |
| "Expand OS into a universal agent OS" | Refused | Scope is restricted to a file-first dual-review protocol kernel |
| "SaaS-ify CT2" | Refused | Local file authority is the identity. SaaS is a different product. |
| "Make CT2 fully multi-tenant" | After 12 months | Unleashing it now breaks five invariants at once. |
| "Adopt the Reliability Platform analogy" | Adopted as sub-framing | Retain it as the operational value the OS provides, not as the canonical name |
| "Adopt TeamCreate/SendMessage immediately" | Refused | Experimental flag, instance-coupling cost |
| "Make Native task mirror Bet #1" | Refused | Most seductive, most dangerous. Last. |
| "Add external dependencies (e.g., redis)" | Refused | Keep the zero-external rule. File system + bash + python stdlib. |
| "Use /ultrareview as a lens replacement" | Refused | Dual-review independence is lens's essence. Ultrareview is only a *third opinion*. |
| "Adopt an LLM router" | After 12 months | Without settled static contracts, a router is a noise multiplier |

## 11.5 Stakeholder map — who this document is for

This document must satisfy the following 4 stakeholders simultaneously. Specify what we promise each.

| Stakeholder | What gets better in this sprint | How we measure |
|---|---|---|
| **Solo dev (current user)** | $/ticket −30%; first-pass approval +15pp; "still-OK-after-sleep" UX | §9 balanced scorecard |
| **Early adopters (other multi-agent users)** | Role-contract pattern pinned to spec, enabling vendor swap in their own environments | Forks and plugin-install counts after spec PRs merge |
| **CT2 plugin authors / spec contributors** | Spec-PR-driven change procedure; regressions caught by evals; PR burden ↓ | §6.6 spec PR list, eval-suite case count |
| **(Future) enterprise users** | Budget hard_deny, OTel integration, strengthened audit trail | §9 metric 7 (0 invariant violations) + Feature Radar P0 Capability Registry |

**Refusals** to each:

- To Solo dev: We do not promise "faster ticket processing" — we promise *trustworthy* ticket processing.
- To plugin authors: We do not promise "my plugin auto-surfaces in ct2-status" — it surfaces only when *registered* in the Capability Registry.
- To enterprise: We do not promise "SaaS multi-tenant" — we preserve local file authority.

## 12. Open questions — things to resolve via spike

Each is a 1–2 day spike, parallelized in week 1:

1. **Codex `personality` config surface.** Docs say stable, but where the actual CLI/profile handle lives. Measure `~/.codex/config.toml` + re-read the 0.130.0 release notes.
2. **Observing `enable_request_compression`.** Process the same real ticket twice (on/off) and compare tokens.
3. **`--max-budget-usd` behavior mode.** Does it cut *mid-work*, or refuse *before start* via estimation? Verify with a test ticket.
4. **`--bare` mode skill availability.** Do SKILL files fully resolve? Does it work without plugin sync?
5. **Whether `PreToolUse` hook can inspect `TaskUpdate` metadata.** If not, Bet 5 shape needs to be revised.
6. **`Monitor` tool caps (unsupported on Bedrock/Vertex/Foundry).** Need a fallback if CT2 users live in those environments.
7. **The path where `AskUserQuestion` multi-select falls back to the inbox.** Direct coupling with Feature Radar P0 Decision Bridge.

## 13. Anti-pattern catalog — traps that could appear within 6 weeks

Why we pin them in the document: at the 6-week retro, to avoid wrongly marking bets as "successes" while sitting in a trap.

- **Cost dropped 30% but trust ratio dropped too.** → forge model demoted too far. Roll back.
- **First-pass rate rose, but plan-mode is only producing helm boilerplate.** → Lower the plan-exempt threshold; add a "plan signal-to-noise" rubric to the eval.
- **Discord pings get used as an inbox replacement.** → Spec into bridge policy: "external channels cannot be authority over ticket lifecycle"; measure violation metrics.
- **The eval suite raises false regressions on minor wording changes.** → Inspect judge determinism; simplify the rubric.
- **In the native task mirror, the user works directly on the native side.** → Block via hook; count mismatch events.

## 14. Closing — one paragraph

CT2's next round is not *feature addition* but *identity clarification*. By bundling the five vendor-stable surfaces (`personality`, `fast_mode`, `enable_request_compression`, `--max-budget-usd`, `EnterPlanMode`) into OS primitives, role contracts, plan evidence, evals, and an ambient advisory bridge, CT2 upgrades from a simple protocol harness called "atomic mv + dual review" into **Verified Autonomy OS**. At this stage, the most important decision is not *what to add* but *what to ultimately refuse*. §6's six anti-bets are how we pre-pin those refusals. So that CT2 does not overflow into a universal agent OS but remains a file-first dual-review protocol kernel.

---

## Appendix A — index of surfaces this document treated as *primary* data

What we directly verified during authoring, and how. Use this index as the starting point for re-verification later.

| Item | Verification method | Result |
|---|---|---|
| `codex --version` | local CLI | `codex-cli 0.130.0` |
| `claude --version` | local CLI | `2.1.138 (Claude Code)` |
| Codex stable feature flags | `codex features list` | `apps`, `browser_use`, `browser_use_external`, `computer_use`, `enable_request_compression`, `fast_mode`, `guardian_approval`, `hooks`, `image_generation`, `in_app_browser`, `multi_agent`, `personality`, `plugins`, `tool_call_mcp_elicitation`, `tool_search`, `tool_suggest`, `unified_exec` |
| Codex experimental flags | `codex features list` | `goals`, `external_migration`, `prevent_idle_sleep` |
| Claude CLI surface | `claude --help` | `--agent`, `--agents`, `--bare`, `--brief`, `--effort`, `--fork-session`, `--from-pr`, `--include-hook-events`, `--include-partial-messages`, `--input-format`, `--json-schema`, `--max-budget-usd`, `--no-session-persistence`, `--plugin-dir`, `--plugin-url`, `--remote-control`, `--resume`, `--session-id`, `--system-prompt`, `--tmux`, `--tools`, `--worktree` |
| Claude built-in tools | docs (tools-reference) | Agent, AskUserQuestion, Bash, CronCreate/List/Delete, Edit, EnterPlanMode/ExitPlanMode, EnterWorktree/ExitWorktree, Glob, Grep, ListMcpResourcesTool, LSP, Monitor, NotebookEdit, PowerShell, Read, ReadMcpResourceTool, SendMessage, ShareOnboardingGuide, Skill, TaskCreate/Get/List/Update/Stop/Output, TeamCreate/Delete, TodoWrite, ToolSearch, WebFetch, WebSearch, Write |
| Claude 2.1.136 changes | docs changelog | OTel feedback survey, autoMode hard_deny, plan-mode write-block fix, AskUserQuestion multi-select, CronList output |
| Claude 2.1.133 changes | docs changelog | `worktree.baseRef`, hook effort metadata, subagent skill discovery fix, sandbox bwrap/socat path |
| Claude 2.1.129 changes | docs changelog | `--plugin-url`, `skillOverrides`, `claude_code.pull_request.count` OTel, `experimental` plugin manifest |
| Claude 2.1.128 changes | docs changelog | EnterWorktree from local HEAD, `--channels` console auth, MCP tool counts |
| Claude 2.1.126 changes | docs changelog | `claude project purge`, `--dangerously-skip-permissions` extensions, OAuth code paste |
| Codex 0.130 changes | docs changelog | `codex remote-control`, app-server thread paging, plugin sharing metadata, multi-env `view_image` |
| Codex 0.129 changes | docs changelog | TUI vim, `/goal` discovery/pause/resume, plugin workspace sharing, hook pre/post-compaction |
| Codex 0.128 changes | docs changelog | First implementation of `/goal`, plugin marketplace install, multi-agent v2 caps |

## Appendix B — consistency check vs. Feature Radar (diff summary)

| Fact | Feature Radar | This document | Cause of divergence |
|---|---|---|---|
| Local Claude version | 2.1.138 | 2.1.138 | Both documents now align on the latest measured value |
| Claude 2.1.138–2.1.132 gap | Gone | Gone | Stale diffs from old drafts removed |
| `--bare` mode | Not covered | Core dependency of Bet 4 | Added in this document |
| `personality`, `fast_mode`, `enable_request_compression` | Lightly surfaced | Direct handles in Bet 1 | Added in this document |
| `--max-budget-usd`, `--effort` | Lightly surfaced | Core of Bet 1 | Added in this document |
| EnterPlanMode | Not covered | Core of Bet 2 | Added in this document |
| Balanced scorecard | Only candidate infrastructure | Adopted as Trust/Evidence/Autonomy/Cost | Reflects user interview |
| Verified Autonomy OS framing | Proposed as North Star | Adopted as canonical product identity | Reflects user interview |
| Anti-bets | 6 "non-goals" | 6 anti-bets in a dedicated §6 | Emphasis differs |

This document does *not* replace Feature Radar. Feature Radar's catalog/protocol absorption work remains valid, and its three P0s are the foundation of this document's bets. Review both as a single bundle with stakeholders.

## Appendix C — Bet 1 implementation sketch (actual wrappers)

The following sketch shows *concretely* how to begin Bet 1. We pin it in to keep this document from being "just abstract strategy." Real code will merge after the spec PR as `bin/ct2-forge-run` (Claude-side wrapper) and friends.

`bin/ct2-role-run` (provider-agnostic, new script):

```bash
#!/usr/bin/env bash
set -euo pipefail
# ct2-role-run <role> <provider> <ticket-id>
# Loads role contract from .ct2/config/harness.yaml, invokes provider,
# emits cost telemetry to .ct2/telemetry/cost.jsonl.

role="$1"; provider="$2"; ticket_id="$3"
contract_yaml=".ct2/config/harness.yaml"
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Parse contract via python stdlib (yaml-free regex; consistent with CT2 conventions).
contract=$(python3 - "$role" "$contract_yaml" <<'PY'
import re, sys
role, path = sys.argv[1], sys.argv[2]
content = open(path).read()
# Locate role_contracts: <role>: block (regex-only)
block = re.search(rf'role_contracts:.*?{re.escape(role)}:(.*?)(?=^\S|\Z)',
                  content, re.S | re.M)
if not block:
    print("MISSING"); sys.exit(0)
out = {}
for k in ("model", "effort", "personality",
         "budget_per_ticket_usd", "budget_per_session_usd",
         "budget_per_review_usd", "budget_per_run_usd",
         "latency_slo_seconds", "request_compression",
         "fast_mode", "on_budget_exceeded"):
    m = re.search(rf'^\s*{k}:\s*(.+?)\s*$', block.group(1), re.M)
    if m: out[k] = m.group(1).strip()
import json; print(json.dumps(out))
PY
)
[[ "$contract" == "MISSING" ]] && { echo "no contract for $role" >&2; exit 2; }

model=$(echo "$contract" | python3 -c "import json,sys;print(json.loads(sys.stdin.read()).get('model',''))")
effort=$(echo "$contract" | python3 -c "import json,sys;print(json.loads(sys.stdin.read()).get('effort','medium'))")
budget=$(echo "$contract" | python3 -c "
import json,sys; c=json.loads(sys.stdin.read())
for k in ('budget_per_ticket_usd','budget_per_session_usd','budget_per_review_usd','budget_per_run_usd'):
  if k in c: print(c[k]); break")

case "$provider" in
  claude)
    # Claude wrapper. --include-hook-events keeps hook trace for eval correlation.
    exec claude \
      --agent "$role" \
      --model "${model:-sonnet}" \
      --effort "${effort}" \
      ${budget:+--max-budget-usd "$budget"} \
      --include-hook-events \
      -p "$(cat .ct2/in-progress/${ticket_id}-*.md 2>/dev/null || cat .ct2/in-review/${ticket_id}-*.md)"
    ;;
  codex)
    # Codex profile is the primary surface for personality/fast_mode/compression.
    # Profile name convention: ct2-<role> in ~/.codex/config.toml
    profile="ct2-${role#ct2-}"
    exec codex --profile "$profile" exec "$(cat .ct2/in-progress/${ticket_id}-*.md 2>/dev/null || cat .ct2/in-review/${ticket_id}-*.md)"
    ;;
  *)
    echo "unknown provider: $provider" >&2; exit 2 ;;
esac
```

Codex side `~/.codex/config.toml` profile per role:

```toml
[profiles.ct2-forge]
model = "gpt-5-codex"
effort = "high"
personality = "terse"
fast_mode = false
enable_request_compression = true
# Budget is a separate surface on the Codex side — no direct cap as of 0.130.0.
# CT2 measures it indirectly via `tool_call_mcp_elicitation` event counts in the wrapper,
# then records into .ct2/telemetry/cost.jsonl.

[profiles.ct2-lens-cx]
model = "gpt-5-codex"
effort = "high"
personality = "skeptical-short"
fast_mode = false
enable_request_compression = true

[profiles.ct2-status]
model = "gpt-5-codex-fast"
effort = "low"
personality = "terse"
fast_mode = true
```

Telemetry sink (`bin/ct2-cost-record`, post-run, called via hook):

```bash
#!/usr/bin/env bash
set -euo pipefail
# Reads $CLAUDE_TOOL_LOG / Codex stdout, parses cost summary, appends jsonl.
role="$1"; ticket_id="$2"; provider="$3"; outcome="$4"; duration_s="$5"; cost_usd="$6"
mkdir -p .ct2/telemetry
python3 - <<PY
import json, time
rec = {
  "ts": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "role": "$role",
  "ticket": "$ticket_id",
  "provider": "$provider",
  "outcome": "$outcome",
  "duration_s": float("$duration_s"),
  "cost_usd": float("$cost_usd") if "$cost_usd" else None,
}
with open(".ct2/telemetry/cost.jsonl", "a") as f:
    f.write(json.dumps(rec) + "\n")
PY
```

`bin/ct2-cost` (status integration):

```bash
#!/usr/bin/env bash
set -euo pipefail
# Aggregates .ct2/telemetry/cost.jsonl into a one-screen summary.
python3 - <<'PY'
import json, sys, os
from collections import defaultdict
path = ".ct2/telemetry/cost.jsonl"
if not os.path.exists(path):
    print("(no telemetry yet)"); sys.exit(0)
by_role = defaultdict(lambda: {"n": 0, "cost": 0.0, "violations": 0})
with open(path) as f:
    for line in f:
        r = json.loads(line)
        b = by_role[r["role"]]
        b["n"] += 1
        if r.get("cost_usd"): b["cost"] += r["cost_usd"]
        if r["outcome"] == "budget_exceeded": b["violations"] += 1
print(f"{'role':24} {'runs':>6} {'$total':>10} {'budget violations':>20}")
for role, b in sorted(by_role.items()):
    print(f"{role:24} {b['n']:>6} {b['cost']:>10.2f} {b['violations']:>20}")
PY
```

`ct2-status` integration: the final line is a single `bin/ct2-cost --brief`. *Supplementary* information that does not break the existing status output shape.

## Appendix D — Bet 4 eval case example (full)

The following is the *complete* shape of one eval case for the lens-cc role. An appendix pinned in to show this document is not *only* a sketch of Bet 4.

`.ct2/evals/ct2-lens-cc/case-001-missing-test/` directory:

`ticket.md`:

```markdown
---
id: "001"
title: "Add user authentication endpoint"
status: in-review
priority: high
review-round: 0
review-status:
  lens-claude:
    status: pending
    sidecar: null
  lens-codex:
    status: pending
    sidecar: null
verdict: pending
---

## Requirements
- [x] POST /auth/login endpoint accepts email + password
- [x] Returns JWT on success, 401 on failure
- [x] Password hashing with bcrypt

## Constraints
- No new dependencies beyond bcrypt
- Must follow existing FastAPI patterns

## Acceptance Criteria
- [ ] Endpoint added with correct request/response shape
- [ ] Unit tests cover success and 401 cases
- [ ] Existing test suite passes
```

`patch.diff`:

```diff
diff --git a/app/auth.py b/app/auth.py
new file mode 100644
--- /dev/null
+++ b/app/auth.py
@@ -0,0 +1,28 @@
+from fastapi import APIRouter, HTTPException
+from pydantic import BaseModel
+import bcrypt, jwt, os
+
+router = APIRouter()
+
+class LoginRequest(BaseModel):
+    email: str
+    password: str
+
+@router.post("/auth/login")
+async def login(req: LoginRequest):
+    user = await get_user(req.email)
+    if not user:
+        raise HTTPException(401, "Invalid credentials")
+    if not bcrypt.checkpw(req.password.encode(), user.password_hash):
+        raise HTTPException(401, "Invalid credentials")
+    token = jwt.encode({"sub": user.id}, os.environ["JWT_SECRET"])
+    return {"token": token}
```

`expected-sidecar.json` (subset matcher; the lens-cc sidecar must *at minimum* satisfy):

```json
{
  "verdict": "rejected",
  "issues_must_contain_keywords": [
    "test",                   // AC 2 is unchecked but the patch has no tests
    "unit test",
    "missing"
  ],
  "blocking_issues_count_min": 1,
  "ac_check_must_have_failed": ["Unit tests cover success and 401 cases", "Existing test suite passes"],
  "must_not_contain_phrases": [
    "approved",            // verdict must be rejected
    "looks good"
  ]
}
```

`rubric.md` (qualitative scoring criteria; used by LLM-as-judge):

```markdown
## Rubric — case-001 (lens-cc rejecting an obvious AC miss)

### Must (binary, 0/1 each)
1. verdict == "rejected"
2. sidecar identifies missing tests as a blocking issue
3. sidecar references AC 2 ("Unit tests cover success and 401 cases") explicitly
4. sidecar does NOT recommend approval despite the patch shape

### Should (graded 0–2)
5. sidecar suggests specific test cases (success path, wrong password, missing user)
6. sidecar notes JWT_SECRET env var lookup is brittle (no fallback / no validation)
7. sidecar tone is "skeptical-short" per role-contract personality

### Nice-to-have (0–1)
8. sidecar flags `get_user` is called but not defined/imported in this patch — incomplete
9. sidecar suggests using FastAPI's HTTPException with `WWW-Authenticate` header

### Pass condition
- All Must items = 1
- Should sum ≥ 4/6
```

`runner.sh` invocation (simplified):

```bash
case_dir="$1"
out=$(claude --bare \
  --agent ct2-lens-cc \
  --model "${CT2_LENS_CC_MODEL:-opus}" \
  --effort high \
  --max-budget-usd 0.50 \
  --json-schema '{"type":"object","properties":{"verdict":{"type":"string"},"summary":{"type":"string"},"issues":{"type":"array"}}}' \
  -p "$(cat "$case_dir/ticket.md" "$case_dir/patch.diff")")

# Subset match against expected-sidecar.json
python3 bin/_eval_subset_match.py "$case_dir/expected-sidecar.json" <<<"$out"

# Rubric judge (separate cheaper claude call)
judge_out=$(claude --bare --model haiku --max-budget-usd 0.10 \
  -p "$(cat "$case_dir/rubric.md")\n\nReview:\n$out\n\nReturn JSON: {must:[0|1,...], should:[0..2,...], nice:[0|1,...], pass:true|false}")
echo "$judge_out" | tee -a "$case_dir/results-$(date +%s).json"
```

Interpretation:

- `--bare` cuts hooks/auto-memory to get the result of *only the role MD in question* (external-variable isolation).
- `--max-budget-usd 0.50` is a different envelope from the Bet 1 contract (separate eval).
- `--json-schema` fixes the result structure so the subset matcher works.
- The judge LLM uses a cheaper model (haiku) — it grades only the *plausibility* of the decision.
- Results accumulate in the case directory to trace regression over time.

## Appendix E — concrete next 7 days

What to start *right after* reading this document.

| Day | Task | Deliverable |
|---|---|---|
| 1 | Bet 1 spike: measure `personality`/`fast_mode`/`enable_request_compression` | `.ct2/runtime/codex-flags-actual.md` (measurement report) |
| 1 | Write the one-off `bin/ct2-baseline` script | `.ct2/telemetry/baseline-2026-05.json` |
| 2 | First draft of the `role_contracts` block in `harness.yaml` | spec PR draft (`spec/role-contracts.md`) |
| 3 | First implementation of `bin/ct2-role-run` (Claude only) | Process 1 real ticket; verify cost.jsonl recording |
| 4 | Write Codex profiles, add codex branch to `bin/ct2-role-run` | Process the same ticket via both providers for comparison |
| 5 | Bet 4 baseline: 1 case each for lens-cc/lens-cx | `.ct2/evals/ct2-lens-{cc,cx}/case-001-...` |
| 6 | First-working runner.sh, baseline measurement | `.ct2/evals/results-2026-05-XX.jsonl` |
| 7 | Retro + spec-PR merge decision | spec/role-contracts.md PR open or revise |

What to bring to the stakeholder review after 7 days: (a) baseline numbers, (b) cost.jsonl samples ≥ 5, (c) eval cases ≥ 4, (d) Codex flag measurement report. Without these four, defer entering the 6-week sprint.

---

*Authored: 2026-05-10. v3 — three iterative turns:*
*  v1: 5 bets + 6 anti-bets + framing + roadmap (turn 1)*
*  v2: empirical baseline, kill criteria, spec PR list, subagent/memory, competitive comparison, stakeholders, Bet 1 wrapper, Bet 4 eval case, 7-day plan (turn 2)*
*  v3: Feature Radar diff at a glance (§0.1), Layered architecture diagram (§2.1) (turn 3)*
*Next update: after the Bet 1 spike completes (estimated week 1).*
