---
type: strategy
title: "CT2 Above Native Workflows — The Verification Kernel That Workflows Re-Enter"
version: "0.1.0"
authored: 2026-06-07
status: proposal
composes_with:
  - docs/ct2-protocol-reframe-2026-05-13.md         # canonical posture; this doc extends, does not supersede it
  - docs/ct2-verified-autonomy-os-strategy-2026-05.md # balanced scorecard + advisory-driver authority model
  - docs/agent-platform-feature-radar-2026-06.md     # sibling 2026-06 vendor-surface map (companion radar)
  - docs/agentic-harness-trends-2026-06.md           # sibling 2026-06 discipline survey (harness engineering)
audience: maintainers, contributors, adapter authors, downstream packagers
---

# CT2 Above Native Workflows

> Native dynamic workflows and ultracode mean the agent runtimes now absorb **orchestration** itself. CT2's durable value is no longer the fan-out — it is the **verification/protocol kernel** that an ephemeral workflow run must **re-enter** before its output can count.

**Survey date:** 2026-06-07 KST / 2026-06-07 US
**Target runtimes:** Claude Code (dynamic workflows / ultracode, research preview, requires v2.1.154+); OpenAI Codex CLI (current stable 0.137.0, 2026-06-04; 0.138.0 alpha-only)
**Purpose:** Take an explicit CT2 position on agent-native dynamic workflows and ultracode — the central 2026-06 whitespace — without contradicting the 2026-05-13 Protocol Reframe or violating its subtraction discipline.
**Role within the document set:** This is the **flagship strategy note for the dynamic-workflow era**. It *composes with* (does not supersede) the Protocol Reframe (`docs/ct2-protocol-reframe-2026-05-13.md`), reuses the Verified Autonomy OS balanced scorecard (`docs/ct2-verified-autonomy-os-strategy-2026-05.md`), and draws its dated vendor evidence from the two sibling 2026-06 documents (`docs/agent-platform-feature-radar-2026-06.md`, `docs/agentic-harness-trends-2026-06.md`). Where those siblings own a fact, this doc cites rather than re-derives it.

---

## 0. Executive Summary

### 0.1 The Thesis, in One Sentence

**Native dynamic workflows carry the work; CT2 carries the outcome.**

In May 2026 Anthropic shipped *dynamic workflows* (research preview, Claude Code v2.1.154+): Claude authors a deterministic JavaScript orchestration script that a background runtime executes over tens-to-hundreds of subagents, with built-in `agent()`/`parallel()`/`pipeline()` primitives and documented quality patterns (adversarial-verify, judge-panel, loop-until-dry). `ultracode` makes this the default: it pins `xhigh` reasoning and turns every substantive request into one or more workflows (understand → change → verify). The runtime now does — natively, deterministically, and at scale — exactly what CT2's helm/forge/lens triad was hand-rolling: fan-out, pipelining, parallel verification, self-paced loops, budget-scaled fleets.

This is the inflection the 2026-05-13 Protocol Reframe anticipated in the abstract ("the runtime increasingly owns continuation; CT2 owns the protocol continuation must satisfy", reframe §0.1) but did **not** name concretely. A grep of all three 2026-05 strategy docs returns zero hits for "dynamic workflow", "ultracode", "fan-out", or "budget-scaled". The reframe's "the loop belongs to the agent" (§4.3) was written for *single-agent* continuation (`/goal`, Codex `goals`) and treats it as a daemon replacement — not as a programmable, multi-agent runtime. **This document fills that whitespace** with a committed position.

### 0.2 Why CT2 Must Not Compete As An Orchestrator

A dynamic workflow is an extraordinary **executor** and a **non-durable judge**. Four facts (sourced in the sibling radar, `docs/agent-platform-feature-radar-2026-06.md`, and corroborated against official Claude Code docs as of 2026-06-07) bound exactly what it can and cannot be:

| Workflow property | Source | Consequence for CT2 |
|---|---|---|
| **Intermediate state lives in script variables, not files.** | code.claude.com/docs/en/workflows ("Where intermediate results live → Script variables") | A workflow has no durable cross-session ledger. CT2's `.ct2/` filesystem is the cold-restart rehydration the runtime lacks. |
| **Resume is session-scoped.** Exit Claude Code mid-run and the next session restarts the workflow *fresh* (the `runId` journal does not survive a CC exit). | official docs, verbatim | CT2's file-first journal is strictly more durable than the workflow journal. The workflow is ephemeral acceleration; `.ct2/` is the system of record. |
| **Workflow subagents run in `acceptEdits` with auto-approved file edits; there is no mid-run user input.** The docs are explicit: "for sign-off between stages, run each stage as its own workflow." | official docs, verbatim | Review-before-merge is **structurally impossible inside a single workflow**. The per-stage sign-off seam the docs describe is exactly the seam CT2 occupies. (Note: `acceptEdits` is the *forced* mode for in-workflow subagents specifically; in interactive sessions `acceptEdits` is one selectable permission mode among several.) |
| **The budget object is a fan-out lever, not a circuit breaker.** It exposes a token target for `loop-until-budget` scaling and is `null` without one. The 1,000-agent lifetime cap and a concurrency cap of *up to 16* agents (the `cores-2` refinement appears in the harness tool description but not the public docs; treat 16 as the ceiling) are the only hard run-level guards. | sibling radar; corrected against Anthropic Task-budgets docs (task budgets are a *soft hint*, only `max_tokens` is hard, and task budgets are *not supported on Claude Code surfaces*) | CT2 must **not** promise token-budget enforcement it cannot deliver. It bounds blast radius by agent count and isolation, and records cost post-hoc. |

A workflow can understand, change, and self-verify at very high speed and very high token cost. But its result is **non-authoritative** until it lands in `.ct2/`, is reviewed by two independent reviewers whose prompts contain no sibling output, and is moved by the reconciler. The runtime's own named failure modes — *agentic laziness*, *self-preferential bias*, *goal drift* (Anthropic's stated motivation for workflows; see `docs/agentic-harness-trends-2026-06.md`) — are precisely the failures a single vendor's session cannot certify away for itself, because the structural fix (split generation from evaluation into independent contexts) dilutes that vendor's session. And the fix has a depth the vendor's own version cannot reach: splitting generation from evaluation into separate *contexts of the same model* still shares that model family's blind spots; only a **different model family evaluating** truly neutralizes self-preferential bias. That is exactly CT2's cross-vendor pairing — `lens-cc` (Claude) AND `lens-cx` (Codex). Cross-vendor independence is therefore not a parity preference but the mechanism that makes verification real (developed as **T0**, §5), and the faster one vendor self-verifies, the more a structurally-independent second vendor is required. That fix is CT2's entire product.

### 0.3 The Position

CT2 declares itself the **verification/protocol kernel above native workflows**, not a competing orchestrator. Concretely:

1. **A native workflow is a sanctioned executor for forge implementation and for read-only discovery/analysis.** Ultracode is *welcome* as forge's engine. CT2 does not forbid fan-out for work.
2. **A workflow run must re-enter CT2 at the verify/commit boundary.** It must name a CT2 ticket, return as a patch / PR / inbox message / evidence artifact, and (once worktrees ship, Phase 1.5+) write *only* into an isolated worktree — until then, into a branch-per-ticket. It never holds terminal authority.
3. **CT2's terminal authority is unchanged and reinforced**: independent dual-review (cc AND cx), reviewer-independence-as-protocol-law, and the reconciler as the sole automatic path to `done/`. These three invariants survive the fan-out era and *are* CT2's product.

This is the LSP/git framing the reframe already applied to A2A/ACP/MCP (reframe §2.7), extended one layer: **the workflow is the disposable implementation; CT2 is the protocol the workflow must satisfy.**

### 0.4 What This Costs CT2 (Subtraction, Not Addition)

This position is consistent with the reframe's anti-metric (monotonically shrinking reference-implementation LOC, reframe §0.5) and "subtraction beats addition" (§4.7), because the embrace lives in the **content tier** (adapters, role prompts, a forward-looking CT2-blessed workflow *template*) which is explicitly free to grow, while CT2 **core gets thinner**:

- Native self-paced `/loop` + `Monitor` can replace forge's hand-rolled active/idle/dormant pacing (60s/120s/180s in `config/harness.yaml`).
- Native `isolation:"worktree"` can replace `max_concurrent_worktrees:1`-as-safety once worktrees ship (today they are an empty `Phase 1.5+` directory; see §3.2 and §5.G2).
- `lens-cc` may delegate its deep pass to `/code-review ultra` (cloud, off the local usage window), *augmenting* not replacing the cc/cx AND.

Net direction: **a smaller protocol sitting above a more capable runtime** — the reframe's "grow by being adopted, shrink by being unnecessary" applied to orchestration.

### 0.5 North Star and Scorecard (Inherited, Not Replaced)

This document introduces **no new north star**. It inherits the reframe's north star (days for a new conforming agent to reach review-eligible status; reframe §0.5) and the Verified Autonomy OS **balanced scorecard** (Trust / Evidence / Autonomy / Cost-Latency; VAO strategy §4). The only scorecard adjustment proposed here is on the **Cost-Latency axis**: add a fan-out-width input and a per-run agent count so the scorecard can *see* parallelism, since a budget-scaled fleet is currently invisible to `ct2-baseline` (§6, Thesis T6).

---

## 1. Maturity Snapshot — The Surfaces This Strategy Reacts To

This is a decision-relevant subset, not a full radar; the sibling `docs/agent-platform-feature-radar-2026-06.md` owns the complete dated surface map. Maturity uses the house rating (stable / experimental / immature). Where a fact is unconfirmed it is marked explicitly.

| Surface | What it is | Maturity | Load-bearing fact for this strategy |
|---|---|---|---|
| **Dynamic workflows** | JS orchestration script over subagents; `agent()`/`parallel()`/`pipeline()`/`phase()`/`log()`/`workflow()` | **experimental** (research preview, CC v2.1.154+) | Intermediate state in variables; resume session-scoped; the functional twin of CT2 fan-out, but file-less and ephemeral. |
| **Forced `acceptEdits` + no mid-run sign-off** | In-workflow subagents auto-approve edits; sign-off requires splitting into per-stage workflows | **stable** (documented runtime behavior) | Review-before-merge cannot happen *inside* a workflow. This is the seam CT2 occupies. |
| **ultracode standing mode** | `/effort ultracode` pins `xhigh` + auto-authors a workflow per substantive task; keyword `ultracode` triggers a one-off | **experimental** (research preview; keyword was `workflow` before v2.1.160) | Default = "orchestrate by default, token cost not a constraint" — the exact inverse of CT2's cost-minimizing posture. |
| **Budget object / directive** | `budget {total, spent(), remaining()}`; scales `loop-until-budget` | **stable surface; soft semantics** | Soft hint, not a hard cap; `null` without a target. CT2 cannot live-meter and must not pretend to. |
| **`isolation:"worktree"` subagents + `EnterWorktree`** | Per-subagent git worktree, auto-cleanup; community fix for AI merge conflicts | **stable** (in the runtime) | The mandated write target for any CT2-wrapped workflow — *once CT2 implements worktrees* (Phase 1.5+, unimplemented today). |
| **`/code-review ultra`** | Cloud multi-agent "ultrareview"; dedicated compute off the local usage window | **stable** | A heavy single-vendor pass. An *evidence source* for lens, never an independent dual-review. |
| **Self-paced `/loop` + `Monitor` + Cron** | `/loop` self-paces 60–3600s and stops when provably done; `Monitor` streams a background script without polling | **stable** (CC v2.1.72+) | Native replacement for forge's hand-rolled pacing. Caveat: workflow determinism disables `Date.now()`/`Math.random()`. |
| **Agent teams** | Lead + teammates, shared file-locked task list, `SendMessage` mailbox | **experimental** (default-off, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) | Closest native analogue to CT2 role messaging, but non-nesting, non-resumable, no on-disk audit trail. Candidate transport only; `.ct2/` inbox stays authoritative. |
| **ToolSearch-deferred built-in tools** | `Bash`/`Read`/`Edit`/`Agent`/`Task`/`Monitor`/`SendMessage`/`EnterWorktree` deferred by name; schemas fetched on demand | **stable** (CC v2.1.69) | CT2 adapters that assume `Task`/`Monitor`/`SendMessage` are immediately callable now hit `InputValidationError`; must `ToolSearch`-fetch first. |
| **Codex multi-agent v2 / subagents TOML** | `~/.codex/agents/*.toml`; multi-agent v2 still "dogfood defaults" | **experimental** | Codex is **not** shipping a CT2-style independent dual-reviewer (confirmed whitespace). Re-pin documented min to a capability, not a guessed version (§7.2). |

**Confidence note.** Per the reframe's source-confidence ladder (reframe §2.0) and the 2026-05-13 retrospective's WebFetch-date caveat: the *capability* facts above are Grade A (official docs, corroborated 2026-06-07). The *budget-as-soft-hint* correction is Grade A and **overrides** the earlier primary-source observation that a `+500k` directive is a hard ceiling. Vendor *version numbers* are pinned only where a sibling doc or the repo already carries them; this document gates CT2 behavior on observed capability, not on guessed versions (§5.G6, §7.2).

---

## 2. Gap Analysis

Eleven gaps separate CT2's current state from the dynamic-workflow era. The `G#` labels below are **this document's own gap framing**, not pre-existing repo gate IDs (the repo's `G1..G6` in `docs/ct2-open-pr-merge-readiness-2026-05-13.md` are unrelated PR-merge gates). Priorities use P0 (foundational, this cycle) / P1 / P2. Effort is low / medium relative to the stdlib-and-bash reference implementation.

| ID | New capability | CT2 current state | Opportunity | Risk | Priority | Effort |
|---|---|---|---|---|---|---|
| **G1** | Dynamic workflows: a deterministic JS orchestrator over dozens-to-hundreds of subagents with built-in verify patterns. | Zero committed stance. Grep returns no hits for "dynamic workflow / ultracode / fan-out" across the three 2026-05 docs. Reframe §4.3 covers single-agent continuation only. | Claim the whitespace cleanly: declare CT2 the verification kernel **above** native workflows (`workflows carry the work; CT2 carries the outcome`). Pure content-tier (a strategy note + one adapter Boundary row). | Reads as scope-creep against the reframe's subtraction principle **unless** sited in adapters + a strategy note, with zero new core code and zero daemons. | **P0** | medium |
| **G2** | In-workflow subagents are forced into `acceptEdits` with no mid-run sign-off; the runtime cannot pause for review between forge and merge. | CT2's epistemic model is review-before-state-moves. `max_concurrent_worktrees:1` is a *serial-safety* default (single in-progress slot via `O_EXCL` lock), **not** isolation. Worktrees are an empty `Phase 1.5+` dir (`spec/directory-structure.md`); the live model is branch-per-ticket. | Make worktree isolation the mandatory write target for any CT2-wrapped workflow: forge-as-workflow edits land *only* in a per-run worktree branch; the target branch is touched *only* by the reconciler after dual-approval. The runtime's "no mid-run sign-off" becomes CT2's reason to exist. | Worktrees are **not implemented today**; this is a roadmap bet, not a present mandate. Isolation *complements* the serial-safety lock (filesystem disjointness), it does **not** replace the `O_EXCL` lifecycle lock in `ct2-pickup` or the reconciler lock. | **P0** | medium |
| **G3** | One orchestrator script holds *every* subagent's return; a verifier subagent's prompt is composed by the parent. | Independence rests on session-era mechanisms: separate cc/cx sessions, per-reviewer sidecars, and a no-peek rule (`spec/conformance.md:18`; `enforce-review-independence.sh`). None constrains a parent script that could inject a sibling's output into a verifier prompt. | Elevate independence from "don't read the sibling sidecar" to a **prompt-construction invariant**: "a verifier subagent's prompt MUST NOT contain any sibling reviewer's output." Encode in `spec/conformance.md` as a testable rule. | Not mechanically preventable inside an opaque JS script; CT2 can specify and conformance-test it but cannot block a non-conforming script. Mitigate with a CT2-blessed verify template (forward-looking, content-tier). | **P0** | medium |
| **G4** | Native verify patterns are N-of-M (adversarial-verify kills on majority; judge-panel scores N attempts). | The reconciler hard-codes exactly two reviewers: `cc_v` AND `cx_v` (`bin/ct2-reconcile` lines 245–251), the `(cc|cx)` sidecar regex (line 298), and fixed `review-status.lens-claude`/`lens-codex` frontmatter. | Generalize the verdict to an optional **M-of-N quorum** while keeping 2-of-2 as the canonical floor: cc AND cx remain the trust anchor; extra K skeptics are *advisory* unless explicitly promoted by config. | This touches more than the verdict line: the sidecar naming scheme, `discover_pairs` regex, the fixed lens frontmatter keys, the per-reviewer validator, and `enforce-review-independence.sh` (which assumes exactly one partner to block). **Not** LOC-neutral; budget as a moderate multi-file change. | **P1** | medium |
| **G5** | Budget is a fan-out lever (`loop-until-budget`); directives are soft hints; the 1,000-agent cap is the only hard run guard. | `budget_usd` is `null` for all five roles and read by nothing. `ct2-role-run` records usd/tokens **post-hoc** from env vars; CT2 never counts tokens live. | Split the concept: (a) budget as a fan-out **width** input the planner records in the evidence ledger (advisory); (b) the real circuit breaker stays the 1,000-agent cap + scope-first slicing + CT2's existing time/round breakers. Add a Cost-axis metric for parallelism. | Tempting to over-build a token meter CT2 cannot honor (no live metering; budget is soft). Honest position: **CT2 does not enforce token budgets**; it bounds blast radius by agent count and isolation. | **P1** | low |
| **G6** | Native Workflow runtime, `Task`/`Agent`/`Monitor` tools, worktree isolation, budget object, ultracode mode. | `ct2-runtime-doctor` probes only codex/claude/git/python versions (`MIN_CODEX=0.130.0`, `MIN_CLAUDE=2.1.138`) + `codex features list`. It cannot tell the planner whether native fan-out exists. | Add a network-free "workflow-class" probe: detect the Workflow tool / ToolSearch-deferred-tool presence (capability, not a guessed version) so helm can choose workflow-executor vs serial role loop. Fits the existing doctor contract. | The flag surface is volatile and partly undocumented. Probe must degrade gracefully and treat absence as "serial fallback", never error. Do **not** invent a `disableWorkflows` state or a version gate the repo cannot corroborate. | **P1** | low |
| **G7** | A fan-out attributes findings to dozens of subagents; results must roll up to a parent role/ticket. | `claims.jsonl` is a flat per-ticket list keyed by `id/ticket/kind` (`bin/ct2-evidence`). No parent/child edge, no DAG, no rollup — "Evidence Graph" is effectively a flat ledger. | Add a single optional `parent_id` / `produced_by_agent` field to claim records so a fan-out's per-finding evidence attributes to the orchestrating role and ticket. This is the most concrete instantiation of "CT2 = the durable evidence graph above ephemeral workflows." | Schema growth. Keep it one optional, append-compatible field — not a graph engine. The DAG lives implicitly in the flat records via edges. | **P1** | low |
| **G8** | Workflow scripts forbid `Date.now()`/`Math.random()`/argless `new Date()`; `meta` must be a pure literal; plain JS not TS. | CT2 circuit-breaker stamps (`.started`/`.in-review`) and IDs use wall-clock timestamps; `ct2-duration-check`/`ct2-review-watchdog` are time-based. | Spec a clean boundary: CT2's time/round breakers and ID generation run **outside** the workflow (host session / one-shot tools); any CT2-emitted workflow derives IDs from stable inputs (content hash, ticket id, round). Preserves resume *and* keeps breakers intact. | Low. Mostly a documentation/boundary rule. Risk is a forge agent naively calling a CT2 script that uses timestamps inside a workflow and breaking resume. | **P2** | low |
| **G9** | Ultracode expects the planner to author + run workflows over many subagents by default. | `ct2-helm-auto-cx` explicitly *forbids* subagent fan-out for CT2 state writes (parent owns all writes; explorers read-only). The two paradigms give the planner contradictory defaults. | Resolve with a rule, not a contradiction: native workflows may fan out for **read-only discovery/analysis** and for **forge implementation inside isolated worktrees**, but CT2 **state writes** (seal, sidecar, reconcile, ticket `mv`) remain parent-owned one-shot operations. | If left unstated, ultracode-on planners spawn fan-outs that race the single-value `ct2-active-role` marker and the singleton in-progress slot, corrupting state. | **P1** | low |
| **G10** | `agent()` / `parallel()` spawn many peer subagents in one orchestration. | `.ct2/.meta/ct2-active-role` is a single-value last-writer-wins file; `ct2-pickup`'s singleton in-progress slot + lifecycle lock assume one forge; the inbox is per-role-name (one consumer). | Codify that fan-out subagents are **non-role-holding workers**: a subagent never writes the active-role marker, never claims the in-progress slot, never holds ticket authority. Only the parent role performs the authoritative CT2 write. (Generalizes `helm-auto-cx`'s existing "explorers read-only, parent owns writes" rule to all roles — already codified for forge/helm-auto-cx in their SKILLs.) | Conformance-testable but not mechanically preventable in an opaque workflow. Mitigate via CT2-blessed templates that wire parent-owns-writes by construction. | **P1** | low |
| **G11** | `/deep-research` (bundled adversarial-verify research) and `/code-review ultra` (cloud multi-agent review, off local budget) are first-class native surfaces. | CT2 reimplements bespoke versions: `helm-auto-cx` discovery overlaps `/deep-research`; lens dual-review overlaps ultra. No bridge; the reframe already rejected ultrareview as a lens *replacement*. | Adopt native surfaces as **evidence producers, not verdict authorities**: `lens-cc` may delegate its deep pass to `/code-review ultra` and cite it in-sidecar; `helm-auto-cx` may invoke `/deep-research` for discovery. Keeps CT2 thin (delete bespoke logic) while reusing vendor compute. | Vendor coupling and cloud latency/cost; must fail-soft to the bespoke path. Ultra is a *third single-model opinion*, not independent dual-review, and must never auto-move a ticket. The repo's own term for the cloud third-opinion is `/ultrareview`; align naming before implementation. "Off the local budget" is an inference (cloud compute) pending direct confirmation. | **P2** | low |

---

## 3. Workflow As Executor, CT2 As Kernel

### 3.1 The Two-Layer Model

```text
  ┌───────────────────────────────────────────────────────────┐
  │  EPHEMERAL EXECUTOR  (the runtime owns this entirely)      │
  │                                                           │
  │  ultracode → dynamic workflow:                            │
  │    pipeline(items, understand, change, self-verify)       │
  │    parallel(adversarial skeptics)                         │
  │    state in script variables · resume = session-scoped    │
  │    subagents forced acceptEdits · no mid-run sign-off     │
  │    write target = isolation:"worktree"  ← MANDATED by CT2 │
  └───────────────────────────┬───────────────────────────────┘
                              │  RE-ENTRY CONTRACT (§3.3)
                              ▼
  ┌───────────────────────────────────────────────────────────┐
  │  PERSISTENT KERNEL  (CT2 owns this entirely)              │
  │                                                           │
  │  .ct2/ file ledger  ·  durable across sessions/vendors    │
  │  independent dual-review (cc AND cx, no sibling output)   │
  │  reconciler = sole automatic path to done/                │
  │  evidence graph  ·  inbox  ·  decisions  ·  telemetry     │
  └───────────────────────────────────────────────────────────┘
```

The important asymmetry, mirroring reframe Figure 2: the workflow points *into* `.ct2/`; `.ct2/` does not hand terminal authority back up to the workflow. A workflow that never re-enters has produced an interesting transcript and nothing that CT2 considers done.

### 3.2 Why The Executor Cannot Be The Kernel

Each row of §0.2 maps to a CT2 invariant the workflow structurally cannot satisfy:

| Workflow limitation | CT2 invariant it cannot satisfy | Reframe anchor |
|---|---|---|
| State in variables; resume dies on CC exit | "The filesystem is the database" — `.ct2/` survives vendor outage, crash, price hike | §4.1 |
| Forced `acceptEdits`, no mid-run sign-off | "Only verified evidence can move state" — review must precede merge | VAO §0; reframe §0.4 |
| Parent script holds all child returns | "Reviewer independence is sacred" — must now be a prompt-construction invariant | §4.4 |
| Budget is a soft fan-out lever | CT2 cannot meter live; the real breaker is agent-count + isolation + time/round | this doc §6, T6 |

CT2 has *already* arrived at the file-first model the long-context-agent literature finds beats SOTA (reframe §2.5, arXiv:2603.20432). The dynamic workflow is the strongest 2026 evidence that the runtime is eating orchestration — *and* the strongest evidence that the durable verification layer above it is still empty.

### 3.3 The Re-Entry Contract

A native workflow run that wants its output to count in CT2 must satisfy a **re-entry contract**. This lives in the content tier — an adapter rule plus a forward-looking CT2-blessed workflow template — not in new core code.

A conforming CT2-wrapped workflow run **MUST**:

1. **Name a CT2 ticket.** The workflow is launched for a specific `{ticket-id}` in `backlog/` or `rejected/`; its output is attributed to that ticket. A workflow that names no ticket produces advisory evidence only and can never move state.
2. **Write only into an isolated worktree.** Forced-`acceptEdits` edits land *only* in a per-run worktree branch (`isolation:"worktree"`, `baseRef` derived from ticket frontmatter). The working/target branch is never touched by the workflow. *(Depends on CT2 worktree support — Phase 1.5+, unimplemented today; see §5.G2. Until then, the equivalent guard is forge's branch-per-ticket plus the single in-progress slot.)*
3. **Return through a CT2-recognized channel.** Output re-enters as exactly one of: a **patch** (worktree branch), a **PR**, an **inbox message**, or an **evidence artifact** (`claims.jsonl` row). It never re-enters by mutating ticket state directly. (This is the VAO advisory-runtime rule — "cloud/remote outputs return as patch, PR, inbox message, evidence artifact, or advisory report"; VAO §6.5 — generalized to workflows.)
4. **Keep its subagents non-role-holding (§5.G10).** No subagent writes `ct2-active-role`, claims the in-progress slot, or holds ticket authority. Only the parent role performs the authoritative CT2 write.
5. **Construct verifier prompts without sibling output (§5.G3).** Any in-workflow reviewer/skeptic subagent's prompt contains no other reviewer's verdict or sidecar.

And the kernel side is **non-negotiable**:

6. **Dual-review stays terminal authority.** The workflow's self-verification (its own adversarial-verify pass) is *evidence*, not a verdict. The ticket still requires cc AND cx independent sidecars.
7. **The reconciler is the sole automatic mover.** `ct2-reconcile` — not the workflow, not ultracode, not `/code-review ultra` — performs the `done/` / `rejected/` / `escalated/` transition, under its `O_EXCL` lock, after dual-approval.

### 3.4 Boundary Decision Table (Extending Reframe §5.1)

The reframe's Boundary Decision Table gains one row. This is the canonical adapter rule for the dynamic-workflow era:

| Runtime feature asks CT2 to… | Classification | CT2 response |
|---|---|---|
| **Fan out / orchestrate a multi-agent task** | **Runtime workflow** | **Author or invoke a workflow in the adapter. The workflow runs in an isolated worktree, names a CT2 ticket, and re-enters CT2 at the verify/commit boundary (§3.3). Never give a workflow terminal authority. Today this is a Claude Code dynamic workflow; when Codex ships an orchestration analog the *same* contract applies unchanged — the contract names no vendor (§3.5).** |

(Existing reframe rows — runtime loop → adapter; tool layer → MCP; protocol authority → `.ct2/`; advisory metadata → `.ct2/runtime/`; decision → `.ct2/decisions/`; terminal state → reconciler — are unchanged.)

### 3.5 Vendor Symmetry And The Codex Trajectory

The re-entry contract above **names no vendor by design**, and that is the test of whether CT2's founding philosophy survives this cycle. CT2's strongest identity has always been a *protocol that leverages Claude **and** Codex as co-equal runtimes*, not a wrapper around either. The dynamic-workflow era does not weaken that identity; read correctly, it sharpens it.

**Why this cycle reads Claude-heavy — and why that is an argument *for* Codex, not against it.** The May–June 2026 change happened on the Claude side: dynamic workflows and ultracode are Claude Code surfaces, while Codex 0.137.0 ships subagents / multi-agent v2 as "dogfood defaults" with **no** independent dual-reviewer (sibling radar; trends "Codex parity"). A "what changed and how should CT2 respond" note is therefore necessarily Claude-weighted. But the correct inference is the *inverse* of vendor-primacy: when one runtime races ahead on fast, autonomous self-verification (ultracode's adversarial-verify pass), its output is *most* exposed to self-preferential bias (T0) — so a structurally-independent **second-vendor** check becomes *more* necessary, not less. Claude's acceleration is a reason to **strengthen `lens-cx`, not retire it.**

Three rules keep the protocol vendor-symmetric:

1. **The re-entry contract is vendor-neutral.** Today the orchestrator that re-enters CT2 is a Claude workflow. When Codex ships an orchestration analog (multi-agent v2 graduating from dogfood, or a future app-server workflow surface), the *same* §3.3 contract applies with no edit — name a ticket, write into isolation, return as patch/PR/inbox/evidence, non-role-holding subagents, parent-owns-writes. *If a future contract revision needs a vendor name to work, the philosophy has been violated.*
2. **The quorum floor is *cross-vendor* 2, not any-2.** When the reconciler generalizes to M-of-N (§5.G4, B5), the immovable floor stays cc (Claude) AND cx (Codex). Extra same-vendor skeptics (a Claude judge-panel, a Codex skeptic swarm) are advisory: they may *inform* a verdict but never override the cross-vendor disagreement rule ("either reviewer rejects ⇒ rejected"). A Claude majority must not outvote a single cx rejection — that would re-introduce exactly the self-preferential bias the pairing exists to remove (Open Question §9.6).
3. **Parity is maintained and drift is flagged.** `lens-cx` stays first-class: the Codex adapter, app-driver, doctor, and skills are kept at feature parity with the Claude side, and a conformance check flags configurations that would quietly make CT2 Claude-primary (B9). Vendor neutrality is also the durability hedge (§9.7): a CT2 symmetric across vendors survives any single vendor's roadmap churn, price change, or outage; a Claude-primary CT2 is hostage to one runtime and collapses into "a Claude Code workflow wrapper" — the very commodity §0.2 warns against.

**The one-line test.** *If you can delete every Codex reference from CT2 and the protocol still makes sense, CT2 has become a single-vendor harness and lost its moat.* The dynamic-workflow era does not change this rule; it raises the stakes, because the faster the lead vendor self-verifies, the more the independent second vendor is the only thing standing between "the model says it's done" and "it is verifiably done."

---

## 4. Reconciling Ultracode's "Token Cost Is Not A Constraint" With CT2's Cost Scorecard

This is the sharpest philosophical collision in the document, and it must be resolved honestly rather than waved away.

### 4.1 The Collision

| Ultracode default | CT2 posture |
|---|---|
| "Orchestrate by default; token cost is explicitly **not** a constraint." | Anti-metric = shrink reference-implementation LOC; VAO Cost axis = "$/ticket p50 −30%"; `helm-auto-cx` forbids subagent fan-out for state writes. |
| Lean toward many subagents; scale fan-out width to a token target (`loop-until-budget`). | `budget_usd` is a per-role `hard_deny`/`bounce` ceiling (and is currently `null` for every role). |

Taken naively, ultracode says "spend more to parallelize" and CT2 says "spend less and stay serial." Read carefully, **they are about different things**, and CT2's honest position is sharper for admitting where it has no lever.

### 4.2 The Resolution — Three Honest Moves

**Move 1: CT2 does not, and cannot, enforce a token budget.** This corrects the earlier primary-source belief that a `+500k` directive is a hard shared ceiling. Anthropic's own Task-budgets docs state task budgets are a **soft hint** (only `max_tokens` is hard) and are **not supported on Claude Code surfaces**; the in-harness workflow `budget` object is a *scaling lever*, not a stop condition, and is `null` without a target. CT2 has no live token meter (`ct2-role-run` reads usd/tokens post-hoc from env vars; `bin/ct2-cost` merely summarizes). **CT2 will not promise a stop-on-budget mechanism it cannot honor.** The runaway anecdotes circulating in May–June 2026 (a 90-agent review hitting Max limits; a rumored multi-million-token ultracode loop with no useful output) are *consistent* with this soft reading and are exactly why CT2 must not advertise an enforcement it lacks.

**Move 2: CT2 bounds blast radius by the levers it actually controls.** These work without token metering:
- The **1,000-agent lifetime cap** and a **concurrency cap of up to 16 agents** (the `cores-2` refinement is from the harness tool description, not the public docs) — the runtime-enforced hard guards.
- **Scope-first slicing**: helm authors PR-sized tickets; a tightly scoped ticket caps how wide any workflow can reasonably fan out. This is the community-converged mitigation ("scope tightly — run on one directory first").
- **Worktree isolation** (§5.G2): a runaway fan-out can corrupt a per-run worktree, never the working branch.
- CT2's existing **time/round circuit breakers** (`ct2-duration-check`, `ct2-review-watchdog`, `max_review_rounds`) — which bound wall-clock and rework, not tokens, and *do* work today.

**Move 3: budget becomes a fan-out WIDTH input, not a stop condition.** The reconciled model treats a budget directive as a *planning input* the planner records, not a ceiling CT2 enforces:
- Budget directive → recorded in the evidence ledger as the fan-out width the workflow was authorized to use (advisory metadata under `.ct2/runtime/`, never a ticket mutation).
- The Cost-Latency scorecard axis gains two inputs (§6, T6): **per-run agent count** and a **fan-out-vs-serial speedup** signal, so the scorecard can finally *see* a parallel run instead of summing serial durations blind to it.

### 4.3 Why The Two Postures Actually Compose

Ultracode optimizes **throughput within a single executor session**; CT2 optimizes **trust across sessions and vendors**. The reframe and the harness-trends sibling both land on the same empirical signal: *speed is not the bottleneck, correctness is* (Faros AI: +91% review time despite 91% more PRs; the HN refrain "my limiting factor is whether Claude does the task correctly"; Willison's admission he no longer reviews every line). Ultracode makes the executor faster and more expensive; that is the vendor's axis to optimize. CT2's axis — the one the vendor structurally cannot ship for itself — is whether the fast, expensive output is *correct and certified*. The Cost axis in CT2 is therefore not "minimize ultracode's tokens" (CT2 cannot and should not); it is "keep cost-per-*verified*-ticket visible, and never let a Cost-axis gain collapse Trust or Evidence" (VAO §4 cross-axis rule).

---

## 5. Strategic Theses

**T0 — Cross-vendor independence is the mechanism, not a preference.** Anthropic's own motivation for workflows names *self-preferential bias* as a failure mode and prescribes splitting generation from evaluation into separate contexts. But separate *contexts of the same model* still share that model family's blind spots; only a **different model family evaluating** truly neutralizes self-preferential bias. CT2's `lens-cc` (Claude) AND `lens-cx` (Codex) pairing *is* that different-family evaluation — which is why dual review is **cross-vendor by construction**, not "any two reviewers." This is CT2's founding identity (a protocol that leverages Claude **and** Codex as co-equals; §3.5) and the load-bearing reason every other thesis here holds: the faster one vendor self-verifies (ultracode), the more a structurally-independent second vendor is required. Down-weighting either runtime does not simplify CT2 — it removes the one mechanism that makes "verified" mean more than "the generator approved of itself."

**T1 — Native workflows absorb orchestration; they cannot absorb durable verification authority.** The fan-out, the loop, the pacing, the parallel verify all move into the runtime. What does not move: the durable cross-session ledger, the independent dual-review, the reconciler's sole terminal authority, the evidence graph. CT2's durable role is the kernel a workflow re-enters, not the orchestrator it replaces.

**T2 — The workflow is an ephemeral executor; CT2 is the persistent judge.** One line, mirroring the reframe's A2A/ACP disambiguation: *native workflows carry the work; CT2 carries the outcome.* A workflow's result is non-authoritative until it lands in `.ct2/`, is dual-reviewed by reviewers whose prompts contain no sibling output, and is moved by the reconciler. LSP/git applied to the orchestration layer: workflows are the disposable implementation; CT2 is the protocol they satisfy.

**T3 — The market bottleneck validates CT2's bet.** The loudest May–June 2026 practitioner signal is "speed isn't the bottleneck, correctness is." Anthropic's *own* named failure modes (agentic laziness, self-preferential bias, goal drift) and its *own* structural mitigation (split generation from evaluation into separate contexts) are the model CT2 was built on. CT2 should lead positioning with **verification**, not throughput — because dual-independent review is precisely the thing a single vendor will not ship, since it dilutes that vendor's session.

**T4 — CT2 absorbs workflows without violating subtraction.** The embrace lives in the content tier (adapters, role prompts, a CT2-blessed workflow template) which is free to grow; CT2 core gets *thinner* (retire hand-rolled pacing via native `/loop`; retire `max_concurrent_worktrees`-as-safety via native isolation once shipped; optionally delegate deep lens passes to `/code-review ultra`). Net: a smaller protocol above a more capable runtime.

**T5 — Three invariants survive fan-out, and they are CT2's product.** (1) *State moves only on verified evidence* — reinforced by the forced-`acceptEdits`/no-sign-off reality. (2) *Reviewer independence* — must be **upgraded** from a session-era no-peek rule to a prompt-construction invariant, because a parent script now holds all child returns. (3) *The filesystem is the database* — directly answers the workflow's variables-only ephemerality and session-scoped journal. Everything else (the loop, the pacing, the fan-out width) can and should move into the runtime.

**T6 — Cost must become visible to parallelism, not enforced against it.** CT2 cannot live-meter tokens and must not pretend to. It bounds blast radius by agent count + worktree isolation + scope-first slicing + existing time/round breakers, records cost post-hoc, and adds per-run agent count and a fan-out-vs-serial speedup signal to the Cost-Latency scorecard axis so a budget-scaled fleet stops being invisible.

**T7 — Honest uncertainty shapes the bets (do not make experimental surfaces load-bearing).** Dynamic workflows, ultracode, and agent teams are all research-preview/experimental and single-session. The budget-as-hard-ceiling claim is contradicted by Anthropic's own docs. Therefore CT2 makes **none** of them load-bearing; the file protocol's durability is the hedge against these surfaces churning. This is the same 6–18 month ecosystem window the reframe bet on (reframe §12.9) — now with workflows as the strongest evidence both that the runtime is eating orchestration and that the verification layer above it is empty.

---

## 6. Prioritization (Impact / Confidence / Effort)

Impact and Confidence are High / Medium / Low. Effort is medium / low relative to the stdlib+bash reference implementation. Ordering follows the reframe's discipline: content-tier positioning first (P0, zero core LOC), then the lowest-effort/highest-leverage detection and evidence work.

| # | Bet | Gaps | Impact | Confidence | Effort | Priority |
|---|---|---|---|---|---|---|
| B1 | Ship this strategy note + add the Boundary Decision Table row (§3.4); declare CT2 the verification kernel above workflows. | G1 | High | High | low | **P0** |
| B2 | Codify the re-entry contract (§3.3): worktree-isolated write target, named ticket, return-as-patch/PR/inbox/evidence, non-role-holding subagents, parent-owns-writes — as an adapter rule (worktree clause gated on Phase-1.5 implementation). | G2, G9, G10 | High | Medium | medium | **P0** |
| B3 | Upgrade reviewer independence to a prompt-construction invariant in `spec/conformance.md`; ship a forward-looking CT2-blessed adversarial-verify template. | G3 | High | Medium | medium | **P0** |
| B4 | Add a network-free "workflow-class" probe to `ct2-runtime-doctor` (capability detection, not a guessed version) + an optional `parent_id`/`produced_by_agent` edge in `claims.jsonl`. | G6, G7 | Medium | High | low | **P1** |
| B5 | Generalize the reconciler verdict to an optional M-of-N quorum with **cross-vendor 2-of-2 (cc AND cx) as the immovable floor** (multi-file change; explicitly not LOC-neutral). | G4 | Medium | Medium | medium | **P1** |
| B6 | Reconcile budget honestly: no token enforcer; budget as recorded fan-out width; add per-run agent count + speedup to the Cost-Latency axis. | G5 | Medium | High | low | **P1** |
| B7 | Spec the determinism boundary: CT2 breakers/IDs run outside the workflow; CT2-emitted scripts derive IDs from stable inputs. | G8, G9 | Medium | High | low | **P2** |
| B8 | Adopt native surfaces as evidence producers (lens delegates deep pass to `/code-review ultra`; helm-auto-cx invokes `/deep-research`); replace hand-rolled forge pacing with native `/loop`+`Monitor`. All fail-soft; none can move a ticket. | G11 | Medium | Medium | low | **P2** |
| B9 | **Vendor-symmetry guard** (§3.5): make the re-entry contract and quorum floor vendor-neutral (cross-vendor 2 is the floor, not any-2), keep `lens-cx` first-class at parity with `lens-cc`, and add a conformance check that flags Claude-primary drift. Protects T0 — the moat. | G3, G4 (+T0) | High | High | low | **P0** |

---

## 7. Roadmap

Sequencing honors the reframe's principle that spec/positioning precedes code, and that detection (network-free, no state mutation) is the cheapest highest-leverage work. Dates are forward-looking targets, not commitments; everything past doc authoring is **not started** (consistent with the 2026-05-13 retrospective's status discipline).

| Phase | Window (target) | Deliverable | Exit criteria |
|---|---|---|---|
| **W0 — Position** | 2026-06 | This strategy note merged; Boundary Decision Table row added to the reframe / adapter format (§3.4). | A contributor can read §3 and answer "what must a native workflow do to land work in CT2?" without reading code. |
| **W1 — Re-entry contract spec** | 2026-06 → 2026-07 | `spec/conformance.md` gains the re-entry contract (§3.3) and the prompt-construction independence invariant (§5.G3); adapter rule documents named-ticket + return-channel + non-role-holding subagents. | Conformance suite has a test that fails a workflow which (a) omits a ticket id, (b) injects a sibling sidecar into a verifier prompt, or (c) has a subagent write `ct2-active-role`. |
| **W2 — Detection + evidence edge** | 2026-07 | `ct2-runtime-doctor` workflow-class probe (capability-gated, graceful absence → serial fallback); optional `parent_id`/`produced_by_agent` field in `claims.jsonl`. | Doctor reports workflow availability without network; a fan-out's per-finding claims attribute to the orchestrating role/ticket; absence never errors. |
| **W3 — Quorum generalization** | 2026-07 → 2026-08 | Reconciler verdict accepts an optional M-of-N quorum; 2-of-2 cc-AND-cx remains the default floor; K skeptics advisory unless promoted. | 2-of-2 default behavior is byte-for-byte unchanged; an opt-in quorum config passes new tests; `enforce-review-independence.sh` updated for the >1-partner case. |
| **W4 — Cost visibility + native-surface adoption** | 2026-08 | Cost-Latency axis gains per-run agent count + fan-out-vs-serial speedup; lens-cc may cite `/code-review ultra`; helm-auto-cx may cite `/deep-research`; forge pacing migrates to native `/loop`+`Monitor`. | Scorecard renders a parallel run's width; an ultra/deep-research citation appears in a sidecar/ledger as evidence (never as a verdict); all native-surface calls fail-soft to bespoke paths. |
| **W5 — Worktree write target** | gated on CT2 worktree support (Phase 1.5+) | The re-entry contract's worktree clause (§3.3.2) becomes a hard requirement once `worktrees/` has a lifecycle driver. | A CT2-wrapped workflow's forced-`acceptEdits` edits provably cannot touch the working branch; reconciler is the only thing that merges. |

---

## 8. Non-Goals

CT2 explicitly **refuses** the following in this cycle. Each is a refusal a maintainer may invoke without further debate (reframe §8 discipline).

| Non-goal | Why refused |
|---|---|
| **Become an orchestrator / re-implement fan-out in CT2 core.** | The runtime now owns orchestration deterministically and at scale. Re-implementing it is the path back to a harness and violates subtraction (reframe §4.7). CT2 owns the kernel, not the loop. |
| **Enforce a live token budget / ship a stop-on-tokens circuit breaker.** | CT2 cannot live-meter tokens; Anthropic budgets are soft hints. Promising enforcement would be both thicker *and* false (§4.2, T6). |
| **Let a workflow, ultracode, or `/code-review ultra` move a ticket to `done/`.** | Terminal authority is the reconciler's alone, after independent dual-approval. A workflow's self-verification is evidence, not a verdict. |
| **Replace dual-independent review with N-of-M same-vendor judges.** | M-of-N is *additive and advisory*; cc AND cx (cross-vendor) stays the trust anchor. A Claude judge-panel majority must not override a single cx rejection ("either reviewer rejects ⇒ rejected"). Same-model judges share the generator's blind spots; only a different model family neutralizes self-preferential bias (T0). |
| **Make agent teams / `SendMessage` / `TaskCreate` load-bearing inbox transport.** | Experimental, non-nesting, non-resumable, no on-disk audit trail. `.ct2/` inbox stays authoritative; a native fast-path may be advisory only. |
| **Emit a vendor-locked `.claude/workflows/` script as CT2 core.** | Couples CT2 to one vendor's JS dialect and workflow format. A CT2-blessed *template* is content-tier and optional; it is not protocol surface. (Open question §9.5.) |
| **Run any CT2 daemon, poller, or heartbeat to babysit workflows.** | Reframe §4.3 / §8.1. The loop belongs to the agent; native `/loop`+`Monitor` cover pacing. |
| **Adopt the runaway-token anecdotes as facts.** | The 1.7M-token incident is single-source/low-confidence; cite the *soft-budget* mechanism that makes such runaways plausible, not the unverified number. |

---

## 9. Open Questions

These must be resolved before the corresponding spec text is frozen. They are honest unknowns, not rhetorical.

1. **Is the Claude Code workflow `budget` object a hard ceiling in CC specifically?** A primary-source harness observation said `+500k` becomes a hard shared ceiling; Anthropic's Task-budgets docs say task budgets are a soft hint and *not supported on Claude Code*. The no-token-enforcer bet (T6) depends on the soft reading being correct for CC workflows. **Confirm directly before freezing any budget-related spec text.**
2. **Can reviewer independence be mechanically enforced for in-workflow verifiers, or only conformance-tested?** A parent JS script can inject a sibling's output into a verifier prompt, and CT2 cannot inspect the opaque script. Is a CT2-blessed template + conformance test sufficient, or is a tool-layer read-block needed — and does such a hook even fire inside a background workflow runtime?
3. **Do CC hooks (and CT2's heartbeat-via-hooks) fire for subagents spawned *inside* a workflow, or only for top-level/interactive agents?** This determines whether CT2 can enforce independence/plan-evidence at the hook layer for fan-out work, or must rely on re-entry checks only.
4. **What is the cold-restart rehydration contract when a workflow dies mid-run?** Since a CC exit restarts the workflow fresh, CT2's ledger should let a *new* workflow resume from the last durable `.ct2/` state rather than the lost `runId` journal. Which `.ct2/` artifacts must a re-launched workflow read to skip completed work? (Unspecified today.)
5. **Should CT2 emit/consume `.claude/workflows/` scripts directly, or stay strictly at the file-protocol layer?** Emitting scripts is powerful interop but couples CT2 to one vendor's format. Default is to stay at the protocol layer and let users author workflows that re-enter CT2.
6. **How does the M-of-N quorum treat a cross-vendor split when K same-vendor skeptics are added?** The default must preserve "either reviewer rejects ⇒ rejected"; the promotion rule that lets an advisory skeptic become binding needs a precise spec so cross-vendor disagreement still dominates.
7. **Will a major runtime ship a file-first workflow-state convention natively (reframe §12.9 risk)?** If Claude/Codex adopt `.ct2`-like on-disk state, CT2's durability differentiator narrows. The trigger to re-evaluate is the first vendor announcement of durable, cross-session, on-disk workflow state.
8. **Sibling-doc reconciliation (resolved 2026-06-07).** The sibling 2026-06 docs (`docs/agent-platform-feature-radar-2026-06.md`, `docs/agentic-harness-trends-2026-06.md`) exist and were reconciled against this note: the concurrency-cap wording (up to 16; `cores-2` as harness-description-only), the budget-as-soft-hint correction, and the US survey date are aligned across all three. Re-confirm this row if any sibling is later revised.

---

## 10. Immediate Next Tickets

Concrete `ct2-*` deliverables, scoped PR-sized, ordered by §6 priority. Each is content-tier or low-effort detection unless noted; none adds a daemon; none gives a workflow terminal authority.

1. **`ct2-workflow-position-note`** (P0, this doc) — Merge this strategy note. Add the §3.4 Boundary Decision Table row to the reframe and/or the adapter-format spec. *Zero core LOC.*
2. **`ct2-reentry-contract-spec`** (P0) — Add the re-entry contract (§3.3) to `spec/conformance.md`: named ticket, worktree-isolated write target (worktree clause gated on Phase-1.5), return-as-patch/PR/inbox/evidence, non-role-holding subagents, parent-owns-writes. Adapter rule documents the same for forge/helm under ultracode.
3. **`ct2-independence-prompt-invariant`** (P0) — Add to `spec/conformance.md` the testable rule: "a verifier subagent's prompt MUST NOT contain any sibling reviewer's output." Add a conformance fixture that fails a leaky verify workflow.
4. **`ct2-blessed-verify-template`** (P0, content-tier, forward-looking) — A reference adversarial-verify workflow template that wires cc/cx independence (and optional K skeptics) by construction, so users do not hand-roll a leaky one. Lives under a new `templates/workflows/` directory (content-tier), not core.
5. **`ct2-runtime-doctor-workflow-probe`** (P1) — Extend `ct2-runtime-doctor` with a network-free workflow-class probe (Workflow tool / ToolSearch-deferred-tool presence). Capability-gated, not version-gated; absence ⇒ serial fallback, never error. Surface in `ct2-status --doctor`.
6. **`ct2-evidence-parent-edge`** (P1) — Add a single optional `parent_id` / `produced_by_agent` field to `claims.jsonl` records (`bin/ct2-evidence`) so fan-out evidence attributes to the orchestrating role/ticket. Append-compatible; no graph engine.
7. **`ct2-reconciler-quorum-spec`** (P1) — Spec PR generalizing the reconciler verdict to an optional M-of-N quorum, 2-of-2 cc-AND-cx as the canonical floor. Explicitly budget as a multi-file change (sidecar naming, `discover_pairs` regex, lens frontmatter keys, validator, `enforce-review-independence.sh`); **not** LOC-neutral.
8. **`ct2-cost-axis-fanout`** (P1) — Extend `ct2-baseline`/the Cost-Latency scorecard with per-run agent count and a fan-out-vs-serial speedup signal; record budget directive as advisory fan-out width under `.ct2/runtime/`. No token enforcement.
9. **`ct2-workflow-determinism-boundary`** (P2) — Spec the rule that CT2 time/round breakers and ID generation run *outside* the deterministic workflow; CT2-emitted scripts derive IDs from content hash + ticket id + round.
10. **`ct2-native-surface-bridge`** (P2) — Document and wire fail-soft delegation: `lens-cc` may cite `/code-review ultra` in-sidecar (evidence, never verdict); `helm-auto-cx` may invoke `/deep-research` for discovery; forge pacing migrates to native `/loop`+`Monitor`. Confirm naming (`/ultrareview` vs `/code-review ultra`) and the "off local budget" claim before relying on either.
11. **`ct2-codex-baseline-repin`** (P2) — Re-pin documented runtime baselines to *observed capability* rather than guessed versions; note Codex stable is 0.137.0 (2026-06-04) and CT2's serial-by-default / no-fan-out-for-state-writes stance remains correct against Codex multi-agent v2's "dogfood defaults". Coordinate the exact min with the sibling 2026-06 radar.
12. **`ct2-vendor-symmetry-guard`** (P0, protects T0) — Make the re-entry contract (§3.3) and the quorum floor (§5.G4) vendor-neutral in `spec/conformance.md`: the canonical floor is **cross-vendor 2** (cc AND cx), not any-2; `lens-cx` stays first-class at parity with `lens-cc`. Add a conformance check/lint that flags "Claude-primary drift" — e.g. a config that would let a same-vendor judge-panel override a single cx rejection, or a re-entry rule that only resolves for one vendor. Pure spec + conformance fixture; zero core LOC beyond a validator.

---

## 11. Relationship To The Document Set

| Document | Relationship |
|---|---|
| `docs/ct2-protocol-reframe-2026-05-13.md` | **Canonical posture. This note composes with it, does not supersede it.** Extends §5.1 (one new row), §4.4 (independence → prompt-construction invariant), §4.3 (the loop belongs to the agent → now also the *fan-out* belongs to the agent). |
| `docs/ct2-verified-autonomy-os-strategy-2026-05.md` | Reused wholesale: the Trust/Evidence/Autonomy/Cost balanced scorecard, the advisory-driver authority model (§6.5 return-channel rule), and the cross-axis "one axis must not collapse another" rule. |
| `docs/agent-platform-feature-radar-2026-06.md` | Sibling 2026-06 vendor-surface map. Owns the full dated surface evidence; this note cites a decision-relevant subset (§1) and defers version/date authority to it. |
| `docs/agentic-harness-trends-2026-06.md` | Sibling 2026-06 discipline survey. Owns the harness-engineering / verification-first / vibe-coding-maturation narrative; this note cites its market signals (T3) rather than re-deriving them. |
| `docs/agent-platform-feature-radar-2026-05.md`, `docs/ct2-product-strategy-2026-05.md` | Foundational predecessors. Cited for continuity; not re-litigated. |

---

## 12. One-Paragraph Summary For The Maintainer

The runtimes now do orchestration natively, deterministically, and at scale — dynamic workflows plus ultracode are a direct functional twin of CT2's helm/forge/lens fan-out. CT2 should not compete on that axis. A workflow is an ephemeral executor: its state lives in script variables, its resume dies when Claude Code exits, its subagents are forced into `acceptEdits` with no mid-run sign-off, and its budget is a soft fan-out lever, not a stop. None of that is durable verification authority. CT2's durable product is the kernel a workflow must **re-enter**: the file-first `.ct2/` ledger, independent dual-review with prompts that contain no sibling output, and the reconciler as the sole automatic path to `done/`. CT2 embraces workflows in the content tier (adapters, a blessed template, native `/loop`/`/code-review ultra` as evidence) while its core gets thinner — and it stays honest about what it cannot do: it does not meter tokens, it does not enforce a budget, and it makes no experimental surface load-bearing. *Native workflows carry the work; CT2 carries the outcome.*
