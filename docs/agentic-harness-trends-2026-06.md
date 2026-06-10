---
type: field-survey
title: "Agentic Harness Trends — A Catch-Up on Harness Engineering, Agentic Engineering, and Vibe Coding (May–June 2026)"
version: "0.1.0"
authored: 2026-06-07
status: survey
composes_with:
  - docs/agent-platform-feature-radar-2026-05.md     # vendor-surface evidence base (still canonical)
  - docs/ct2-protocol-reframe-2026-05-13.md           # canonical CT2 posture this survey builds on
hands_off_to:
  - docs/ct2-dynamic-workflow-strategy-2026-06.md      # sibling strategy doc that acts on this survey
audience: CT2 maintainers, contributors, downstream adapter authors, strategy reviewers
---

# Agentic Harness Trends — May–June 2026

Survey date: 2026-06-07 KST
Target: the broader agentic-coding field as of May–June 2026, across three named currents — **Harness Engineering**, **Agentic Engineering**, and **Vibe Coding**.
Purpose: catch CT2 up on where the field moved since the 2026-05 strategy cycle, name what the field converged on, and pin the explicit implications that the sibling strategy doc (`docs/ct2-dynamic-workflow-strategy-2026-06.md`) must act on.

Role within the document set: This is the **field-trends evidence base for the 2026-06 strategy cycle**. The 2026-05 feature radar (`docs/agent-platform-feature-radar-2026-05.md`) maps *vendor surfaces*; this document maps *the discipline around those surfaces* — what practitioners, researchers, and the labs themselves are saying about how to build and verify agentic systems. It composes with the radar and the 2026-05-13 protocol reframe (`docs/ct2-protocol-reframe-2026-05-13.md`); it does **not** supersede either. Where this survey reaches a CT2 decision boundary, it states the implication and hands the decision to the sibling strategy doc rather than committing it here.

> **Verification discipline (carried from the 2026-05-13 retrospective).** Every dated/versioned claim below is graded by source confidence (A–E, per the reframe's §2.0 ladder). The reframe retrospective recorded a WebFetch date-reasoning failure that mis-flagged real future-dated arXiv entries as fabricated; accordingly, claims that could not be corroborated against a primary source are marked **unconfirmed** or **forward-looking** inline rather than asserted. Several "headline" numbers circulating in May–June 2026 (token-burn anecdotes, 750k-LOC rewrite durations, survey percentages) are explicitly flagged as marketing-grade. CT2 must not build load-bearing strategy on any of them.

---

## Executive Summary

Three currents that were distinct twelve months ago have visibly converged in May–June 2026:

1. **Harness Engineering** matured from a coined phrase (Feb 2026) into a named discipline with a canon, a formula (*Agent = Model + Harness*), academic papers, and a community list. Its central empirical claim — "the harness is half the score," i.e. scaffold variance swings leaderboard results 10–20 points on fixed model weights — reframes the harness from plumbing into product. CT2 *is* a harness in exactly this 2026 sense.

2. **Agentic Engineering** is the term the field adopted (Karpathy, Sequoia AI Ascent 2026) to replace "vibe coding" for professional work. Its operational shape converged on **planner → executor → reviewer separation**, **eval/verification-first development**, **spec-driven workflows**, and **autonomy budgets** — the exact triad CT2's helm/forge/lens encodes. The labs shipped the orchestration substrate for this: Claude Code **Dynamic Workflows** (research preview, May 28 2026) lets a single session deterministically fan out tens-to-hundreds of subagents from a JS orchestration script, with adversarial-verify and judge-panel patterns built in.

3. **Vibe Coding** did not die; it bifurcated. A **dual-track** consensus emerged (sandboxed disposable prototyping vs. spec-first production), and the loudest practitioner signal of the window is that **the bottleneck moved from generation to verification**. Faros AI's measurement (21% more tasks, +98% PRs merged, but **+91% review time**) and Willison's May 2026 admission that he "no longer reviews every line, even for production" name the review/verification bottleneck that scales *worse* as vibe coding scales.

**The single most consequential delta for CT2** is that the runtimes are now absorbing *orchestration* itself. A Claude Code session in **ultracode** mode authors and runs deterministic workflows by default. This is a functional twin of CT2's helm/forge/lens fan-out — but it is **ephemeral** (intermediate state lives in script variables, not files), its resume journal is **session-scoped** (exiting Claude Code restarts the workflow fresh), its subagents always run **acceptEdits** with no mid-run sign-off, and its budget is (per Anthropic's own docs) a **soft hint, not a hard cap**. The field's convergence on verification-first development plus these structural limits is the strongest external validation yet of CT2's bet: the runtime can own the loop, the fan-out, the pacing, and the parallel verify — but it cannot own **durable verification authority**. That is the empty layer the reframe already claimed. This survey supplies the evidence; the sibling strategy doc supplies the position.

**Cross-current themes this survey traces:** deterministic-vs-model-driven control flow · context engineering and compaction · eval/verification-first development · autonomy budgets · planner-executor-reviewer separation · the spec-driven-vs-vibe debate · and the review/verification bottleneck as vibe coding scales.

---

## How to Read This Survey

| If you have… | Read |
|---|---|
| 3 minutes | Executive Summary, the three trends tables, and "What This Means for CT2" §synthesis |
| 10 minutes | The three per-current sections' "State of the art / Converged on" rows + Second-Order Insights |
| Review time | Source Confidence note above, the maturity ratings in each table, and the "honest uncertainty" rows in the synthesis |
| Strategy hand-off | "What This Means for CT2" + the cross-reference to `docs/ct2-dynamic-workflow-strategy-2026-06.md` |

Maturity ratings used below: **stable** (documented, shipped, corroborated), **experimental** (shipped but research-preview / behind a flag / dogfood), **immature** (announced, anecdotal, or single-source).

---

## Current 1 — Harness Engineering

### 1.1 State of the Art

"Harness engineering" crystallized as a named term in **February 2026**, with the practice attributed to Mitchell Hashimoto's early-Feb blog post and the formula *Agent = Model + Harness* spread across LangChain, Addy Osmani, and Martin Fowler's site (Grade A–D mix; the one-line formula's exact authorship is mildly contested between Hashimoto and others). The discipline's load-bearing principle: **every time an agent makes a mistake, engineer a permanent fix into its environment so the mistake becomes structurally impossible to repeat** (HumanLayer's "Ratchet Principle" — "every line traceable to something that went wrong").

A harness is consistently decomposed into ~5 layers — **tool orchestration, verification loops, context/memory systems, guardrails/permissions, observability** — built atop three primitives: **filesystem** (durable storage), **code execution** (bash as a general-purpose tool), and **sandboxes** (safe execution). This is, almost line for line, CT2's own decomposition.

The empirically decisive claim of the window: **"the harness is half the score."** LangChain reported moving its deep agent from Top-30 to Top-5 on Terminal Bench 2.0 (52.8 → 66.5, **+13.7 points**) *without changing the model* (fixed GPT-5.2-Codex), via harness-only changes — a plan/build/verify/fix loop, exit-intercept verification middleware, loop-detection, and a budget strategy. Benchmark-community consensus now holds that a leaderboard number reflects *model + scaffold*, not the model alone (Grade A for LangChain's own post; the "10–20 point variance" framing is Grade D synthesis).

Context is treated as a finite, rotting resource. Anthropic frames **context engineering** as the successor to prompt engineering ("curating the optimal set of tokens during inference"), with three canonical long-horizon strategies: **compaction** (summarize a near-full window and reinitialize; ~84% token reduction reported on a 100-turn eval — vendor-reported), **structured note-taking** (persist notes to memory outside the window), and **sub-agent context isolation** (a specialized agent returns a ~1–2k-token distilled summary, not its transcript). The mental model is explicit: *context window = CPU register (fast, volatile, small); filesystem + git = persistent storage (slow, durable, unbounded)*.

**Tool Search / deferred-tool loading** productized as a first-class pattern: Anthropic's API ships regex and BM25 server-side variants (`tool_search_tool_*_20251119`); tools marked `defer_loading:true` are excluded from the cached system-prompt prefix and surfaced on demand, cutting tool-definition context by ~85% (e.g. ~55–72k tokens → ~500). In Claude Code specifically, v2.1.69 deferred the **built-in** system tools behind ToolSearch (this very session is an instance), cutting the system-tools context line from ~14–16k to ~968 tokens (Grade A: GitHub issue anthropics/claude-code#31002; note the change shipped *undocumented*, and the exact deferred set is version/config-dependent).

### 1.2 Key Debates

- **Deterministic vs. model-driven control flow.** This is now an explicit design axis. Production consensus (May–June 2026) favors **deterministic workflows wrapping non-deterministic agents**: supervisor pattern, strict phase-gating (Plan-Execute-Verify), narrow per-phase tool access, human checkpoints. The slogan: *the LLM decides the "what" (plan); deterministic code handles the "how" (execution)*. Enterprises are reported to be rejecting over-engineered multi-agent swarms (Grade D synthesis, but consistent across many sources).
- **How much harness is too much?** Two AGENTS.md studies disagree: one finds context files *reduce* task success and raise cost >20% (encouraging over-broad exploration); a parallel study finds ~28% runtime reduction. The unresolved tension forces a "minimal-and-protocol-essential" discipline rather than exhaustive role prompts.
- **Memory: instruction-file vs. memory-block runtime.** Convergence on two coexisting shapes: lightweight AGENTS.md-style files injected at startup (kept lean — HumanLayer's <60 lines) and explicit memory-block runtimes (Letta/MemGPT positioning as memory-first OSS).

### 1.3 What the Field Converged On

- **Agent = Model + Harness**; the harness is a *product surface*, not glue, and its lift over a bare model is measurable and claimable.
- **Context is engineered, not prompted**: compaction + note-taking + sub-agent isolation are the three durable techniques.
- **Filesystem + git = the externalized memory** the discipline calls for; the context window is a register.
- **Splitting generation from evaluation into distinct contexts beats self-evaluation** (Anthropic's own finding: agents grade their own work too favorably).
- **Deferred-tool loading is cache-aware context budgeting**, not just a token trick.

### 1.4 Notable Sources

- Ryan Lopopolo (OpenAI), "Harness engineering: leveraging Codex in an agent-first world" (Feb 11 2026) — the field-defining field report (1M+ LOC / ~1,500 PRs, *self-reported*; Fowler flags it omits correctness verification).
- LangChain, "The Anatomy of an Agent Harness" and "Improving Deep Agents with Harness Engineering" (rank 30→5, model frozen).
- Anthropic, "Effective context engineering for AI agents" and "Building agents with the Claude Agent SDK" (sub-agent isolation; generation-vs-evaluation).
- Anthropic, "Advanced tool use" + Tool Search Tool docs (`defer_loading`, regex/BM25 variants).
- Martin Fowler / Birgitta Böckeler, "Harness Engineering — first thoughts" (the load-bearing skeptical read).
- Community canon: `ai-boost/awesome-harness-engineering`. Academic: arXiv:2604.08224 (Externalization unified review), 2604.25850 (observability-driven harness evolution) — *titles verified on-topic; specific internal claims unverified.*

### 1.5 Trends Table — Harness Engineering

| Trend | State of the art (May–Jun 2026) | Maturity | Explicit CT2 implication |
|---|---|---|---|
| Harness as named discipline | Formula, canon, papers, community list all exist | stable | CT2 should *position itself as a harness/protocol* and adopt the field's vocabulary (primitives, compaction, verification loops, observability). Reinforces reframe §0, §4. |
| "The harness is half the score" | Scaffold-only changes move benchmarks 10–20 pts on fixed weights | stable (LangChain self-report) | CT2's credibility play is to *measure and publish its lift over a bare model* on a fixed task — the move LangChain made. Feeds the conformance suite (reframe §10.3). |
| Context engineering / compaction | Compaction + note-taking + sub-agent isolation are canonical | stable | CT2's `.ct2/` already implements register-vs-storage; CT2 should define *what survives compaction* (plan, decision trailers, ticket state) vs. what is offloaded (tool-call bodies, logs). |
| Deferred-tool loading (ToolSearch) | Built-in tools deferred behind ToolSearch (CC v2.1.69) | stable (undocumented) | CT2 role prompts that assume Task/Monitor/SendMessage/EnterWorktree are immediately callable now hit InputValidationError; adapters must instruct ToolSearch-fetch first. Upside: ~13–15k freed context for CT2's role prompts. Keep CT2's ~5 hot tools non-deferred; order the stable persona prefix first for cache reuse across helm→forge→lens. |
| Generation ≠ evaluation | Anthropic: separate-context evaluation beats self-eval | stable | Direct external validation of forge-vs-lens separation and the "never self-approve in the same context" principle. |
| Sub-agent context isolation | Distilled 1–2k-token return contract is standard | stable | CT2 should standardize the subagent *return contract* (condensed structured summary) and keep parent context lean (this subagent's StructuredOutput-only discipline is the pattern). |

---

## Current 2 — Agentic Engineering

### 2.1 State of the Art

Karpathy (who coined "vibe coding" in Feb 2025) declared the term passé in early 2026 and introduced **"agentic engineering"** at Sequoia AI Ascent 2026, pinpointing **December 2025** as his personal inflection (Nov: ~80% self-written code; Dec: ~80% delegated). His framing: agentic engineering "is about preserving the quality bar … You are still responsible for your software just as before" (Grade D — quotes via secondary coverage; verbatim transcript not retrieved).

The orchestration substrate shipped during the window:

- **Claude Code Dynamic Workflows** (research preview, **May 28 2026**, requires **CC v2.1.154+**, alongside Opus 4.8). Claude writes a deterministic **JavaScript** orchestration script that a background runtime executes while the session stays responsive. Primitives: `agent(prompt, opts?)` (spawn a subagent; `opts.schema` returns a tool-call-validated structured object; `opts.isolation:"worktree"`), `parallel(thunks)` (barrier; a throwing thunk → null), `pipeline(items, ...stages)` (per-item streaming, **no inter-stage barrier** — the default pattern for multi-stage work, per harness observation), `workflow()` (nest one level), plus `phase()` and `log()`. Hard limits: up to 16 concurrent agents (fewer on low-core machines), **1,000 agents total per run** (the run-level guard). Determinism is enforced: `Date.now()`, `Math.random()`, and argless `new Date()` throw (journaled resume requires it). Intermediate state lives in **script variables, not files**; resume is **session-scoped** (exit Claude Code → workflow restarts fresh). (Grade A: code.claude.com/docs/en/workflows.)
- **Ultracode** standing mode (`/effort ultracode` = xhigh reasoning + auto-orchestrate). With it on, Claude "plans a workflow for each substantive task," and "a single request can turn into several workflows in a row: one to understand the code, one to make the change, one to verify it." Session-scoped; the keyword `ultracode` in a prompt triggers a one-off workflow (literal trigger was `workflow` before v2.1.160). (Grade A.)
- **Codex** reached stable **0.137.0** (2026-06-04; 0.138 alpha only). Goals are default-on since 0.133; first-class **subagents TOML** (`~/.codex/agents/*.toml`, `[agents]` max_depth/max_threads/job_max_runtime_seconds); **multi-agent v2** still dogfood-default through 0.137; `app-server --stdio` + thread-resume; `tools.experimental_request_user_input` toggle (0.136, default false). Critically: **Codex shipped no CT2-style independent dual-reviewer or planner/implementer/reviewer system** — confirmed whitespace. (Grade A: GitHub Releases API.)

**Adjacent disciplines that hardened:**

- **Eval-Driven Development (EDD)** as a continuous three-phase loop: (1) define evals as specs (golden sets, regression thresholds set *before* coding); (2) optimize against evals; (3) refine evals as criteria change. Eval gates block deployment automatically, replacing "vibes-based" approval (Braintrust, Red Hat).
- **Spec-Driven Development (SDD)**: GitHub Spec-Kit's **Specify → Plan → Tasks → Implement**, each with a human checkpoint; specs are the source of truth that *generates* implementation; 30+ supported agents; coverage spiked May 2026 (Grade A for the repo; star/version figures Grade D).
- **Autonomy budgets** became concrete operational controls: named "agent owner" with budget authority; Anthropic's Agent SDK / `claude -p` usage drawing from a separate monthly credit pool (reported effective **June 15 2026**, Grade C — verify against official docs before relying on it); rate limits, retries, queues, checkpointing for long runs.

### 2.2 Key Debates

- **Orchestrate-by-default vs. minimize-cost.** Ultracode's explicit posture — "orchestrate by default, token cost is not a constraint" — is the direct opposite of the cost-minimizing, subtractive discipline production teams (and CT2's reframe anti-metric) adopted. The field has not resolved this; it has bifurcated by stakes.
- **N-of-M verification vs. fixed-pair dual review.** The documented native patterns are N-of-M: **adversarial-verify** (N skeptics prompted to refute each finding, kill on majority), **judge-panel** (N attempts scored + synthesized), **perspective-diverse verify**. Research warns single LLM-judges are fragile (ADVERSA 2026: universal triggers inflate judge scores), strengthening the case for *more than one independent perspective* — but the field is split on whether that means K same-vendor skeptics or cross-vendor independence.
- **Named single-context failure modes.** Anthropic explicitly designed workflows to counter **agentic laziness** (quitting a multi-part task early), **self-preferential bias** (grading own output too generously), and **goal drift** (loss of fidelity across many turns). Its *structural* mitigation for self-preferential bias is the same one CT2 was built on: split generation from evaluation into separate contexts. But separate contexts of the *same* model still share its blind spots; only a **different model family** on the evaluation side fully neutralizes self-preferential bias — which is exactly CT2's cross-vendor `lens-cc` (Claude) / `lens-cx` (Codex) pairing, a depth the single-vendor workflow's self-verification structurally cannot reach.
- **How far can an agent run unattended?** Long-horizon autonomy is the defining narrative ("for how long can your agent work before it breaks"). Reported ~5-hour sustained runs in early 2026, doubling roughly every ~6 months; Codex demoed a ~25-hour / ~13M-token run (all Grade C–D, illustrative not benchmarked here).

### 2.3 What the Field Converged On

- **Planner → executor → reviewer separation** is the production-favored shape (supervisor + phase-gating). Dynamic Workflows even ships an *approval gate*: it shows planned phases before launching.
- **Verification-first / "verifiable agent systems"**: the stated 2026 theme is "the field is moving from building agents to building systems that can *prove* they performed work correctly," with continuous runtime verification at the decision point (TrustBench, AgentSpec ICSE'26, VeriGuard).
- **Spec is the contract**: SDD's Specify→Plan→Tasks→Implement is the converged loop; code serves the spec.
- **Autonomy is budgeted, not unbounded**: autonomy is granted up to the next verification gate; "fully delegate" remains 0–20% of tasks per Anthropic's own 2026 data.
- **pipeline() over parallel()**: stream per item, barrier only when a stage truly needs all prior results; fan-out → reduce → synthesize; route low-stakes stages to cheaper models.

### 2.4 Notable Sources

- Anthropic, "Introducing dynamic workflows in Claude Code" + "A harness for every task" (named failure modes; the Bun Zig→Rust rewrite showcase — *~750k LOC, "11 days," 99.8% tests; duration disputed 6 vs 11 days; result called "vibe-coded Rust" by HN skeptics; treat magnitude as marketing-grade*).
- Anthropic, "How we built our multi-agent research system" (orchestrator-worker; the "50 subagents for a trivial query" failure, fixed via prompting).
- Braintrust, "What is eval-driven development"; Red Hat Developer, EDD for AI agents.
- GitHub Spec-Kit; Microsoft "Build 2026 open trust stack" (ASSERT — Grade C, GA unconfirmed).
- DigitalApplied, "Multi-Agent Orchestration: 5 Patterns That Work in 2026" (fan-out / pipeline / debate / supervisor / swarm; debate ≈2.5× single-call cost).
- Andrej Karpathy, Sequoia AI Ascent 2026 (agentic engineering; quotes via secondary coverage).
- alexop.dev, "Claude Code Workflows: Deterministic Multi-Agent Orchestration" (primitives, determinism, budget object — the best technical deep-dive).

### 2.5 Trends Table — Agentic Engineering

| Trend | State of the art (May–Jun 2026) | Maturity | Explicit CT2 implication |
|---|---|---|---|
| Dynamic Workflows (JS orchestrator over subagents) | CC v2.1.154+; agent/parallel/pipeline; variables-only state; session-scoped resume | experimental (research preview) | **Functional twin of CT2 fan-out, but ephemeral and file-less.** Core tension: the runtime absorbs *orchestration*. CT2's durable answer is the file ledger + dual-review the workflow's variables-only state and session-scoped journal cannot provide. Hand-off to strategy doc. |
| Ultracode standing mode | `/effort ultracode` = xhigh + auto-orchestrate; understand→change→verify chains | experimental (research preview) | Ultracode's "orchestrate by default" is the opposite of CT2's cost-minimizing posture. CT2 must take an explicit position: ultracode is welcome as forge's *engine*, but its understand/change/verify chain must **re-enter CT2 at the verify boundary**, where CT2 (not the runtime) owns the verdict. |
| Workflow subagents forced into acceptEdits; no mid-run sign-off | Confirmed in official docs (2026-06-07): subagents always run acceptEdits, inherit the session allowlist, file edits auto-approved; "for sign-off between stages, run each stage as its own workflow" | stable as a *documented behavior* (of a research-preview feature) | **Load-bearing for CT2's position.** A workflow will not pause for review mid-run, so review-before-merge is structurally impossible *inside* a workflow. The per-stage-workflow sign-off seam is exactly where CT2 sits. (Note: auto-approval is for *file edits*; non-allowlisted shell/MCP can still prompt interactively.) |
| Planner-executor-reviewer separation | Production-favored; workflows ship an approval gate | stable | Direct external validation of helm/forge/lens. Helm could emit an *inspectable plan artifact* that forge executes and lens gates, mirroring "show planned phases before execution." |
| Eval/verification-first (EDD) | Define-evals-as-spec → optimize → refine; eval gates block deploy | stable | Blueprint to make CT2 verification *objective*: helm produces acceptance criteria up front; lens uses eval-gate pass/fail as the oracle. Turns dual-review into an evidence loop, not subjective approval. |
| Spec-Driven Development (Spec-Kit) | Specify→Plan→Tasks→Implement, human checkpoints, 30+ agents | stable | Near-exact analog to a helm-driven flow. CT2's value sits at the *under-served review/verification end* of the SDD pipeline that Spec-Kit itself does not enforce. |
| N-of-M adversarial verify / judge panel | Native patterns: kill-on-majority skeptics, scored judge panels | stable (as patterns) | CT2's reconciler hard-codes exactly *two* reviewers. Generalizing to M-of-N quorum (keeping 2-of-2 as the floor) lets CT2 *express* these patterns without abandoning cross-vendor independence. (Engineering cost is real — see synthesis.) |
| Autonomy budgets | Named agent-owner; separate SDK credit pool (reported Jun 15, **Grade C — unverified**); per-run limits | experimental/stable mix | CT2 should make "autonomy budget" a first-class helm decision — how far forge runs before a *mandatory* lens checkpoint. But see the budget-enforcement caveat in the synthesis: CT2 cannot live-meter tokens. |
| Codex parity | 0.137.0 stable; subagents TOML; multi-agent v2 dogfood; request-input toggle | stable (CLI) / experimental (multi-agent v2) | Codex ships **no** independent dual-review system — confirmed whitespace CT2 occupies. Re-pin CT2 baselines: README still says 0.128.0+; bump documented min to **0.136** for the request-input toggle + `app-server --stdio`. |

---

## Current 3 — Vibe Coding

### 3.1 State of the Art

Vibe coding did not disappear; it **bifurcated and got a sharper definition**. Willison's line (restated across 2026 coverage): if an LLM wrote the code but you "reviewed it, tested it thoroughly, and made sure you could explain how it works to someone else, that's not vibe coding — it's software development." Vibe coding specifically means accepting AI output **without full review**.

The defining event of the window is Willison's **"Vibe coding and agentic engineering are getting closer than I'd like"** (6 May 2026), admitting the clean line blurred in his own practice: "as the coding agents get more reliable, I'm not reviewing every line of code that they write anymore, even for my production level stuff." His resolution leans on **usage-as-evidence**: a vibe-coded tool used daily for two weeks is "much more valuable" than commit-count signals.

The **bottleneck reframing** solidified: *the bottleneck shifted from writing software to verifying it.*
- Qodo's CEO: LLM coding tools "are designed to complete tasks, not to question them — making a separate governance and trust layer essential"; the market "overestimates how much these tools can be trusted in the short term and underestimates how much a trust layer is needed."
- Agoda's Leonardo Stern (via InfoQ): "coding was never the real bottleneck"; the constraint "shifted upstream to specification and verification because these areas require human judgment." Faros AI across 10,000+ developers / 1,255 teams: high-AI-adoption teams completed **21% more tasks** and merged **98% more PRs**, yet **PR review time rose 91%**. Stern's "grey box" approach: humans verify "results against evidence rather than inspecting the implementation line by line." (Grade A for InfoQ/Fortune framing; the 8.1M-PR tech-debt study and 40–62% security-flaw figures are Grade D — multiple methodologies, do not treat as one statistic.)

A **dual-track engineering strategy** emerged as the refined response (CIO, Apr 2026): **Track 1** (fast/prototype) — vibe coding "explicitly permitted," metric is "speed to feedback," runs in "heavily sandboxed environments," outputs are "disposable blueprints" that never touch production data; **Track 2** (production) — "Start over … Rewrite from the ground up," strict type safety, "rigorous human peer review," "every unit test manually reviewed." Critical rule: **"never base the timeline of the slow track on the velocity of the fast track."** A dedicated **verification-layer tooling category** (Qodo, CodeRabbit) matured to sit between AI-generated changes and production.

### 3.2 Key Debates

- **Is the line worth holding?** Willison's own drift is the debate made flesh: as agents get reliable, individuals *silently* stop reviewing, and the quality gap reappears under a more trustworthy-looking surface. The field's answer is structural, not willpower-based: a second reviewer in a fresh context.
- **Spec-driven vs. vibe.** Consensus is *complementary, not either/or* (InfoWorld, citing Cloudways): "Use vibe coding to explore and prototype, and spec-driven development with AI to harden and ship." Red Hat's "~3-month wall" narrative (without specs, "the code itself becomes the only source of truth," and functionality "flickers" as the AI fills gaps differently each generation) is the failure mode driving SDD adoption — though the 90-day figure is illustrative, not a measured constant.
- **Does throughput even help?** METR's July 2025 RCT (experienced OSS devs **19% slower** with AI tools despite believing they were faster) remains the skeptic's anchor and is consistent with the 2026 "speed isn't the bottleneck" thesis.

### 3.3 What the Field Converged On

- **The bottleneck is verification, not generation.** This is the loudest, most-corroborated signal of the window.
- **Vibe coding is a *track*, not a *practice*** — fine for disposable prototypes, demoted to "highly restricted assistant" for production.
- **Verification shifts from line-inspection to evidence-evaluation** ("grey box"): judge results against builds/tests/observed behavior, not by reading every line.
- **A separate trust/governance layer is necessary** *because the generating agent cannot be the certifying agent* — the same epistemic split CT2 enforces.
- **Usage is evidence**: a tool that survives real daily use outranks superficial commit signals (Willison).

### 3.4 Notable Sources

- Simon Willison, "Vibe coding and agentic engineering are getting closer than I'd like" (6 May 2026) — the window's defining essay.
- Fortune, "In the age of vibe coding, trust is the real bottleneck" (2 Apr 2026, Qodo).
- InfoQ, "AI Coding Assistants Haven't Sped up Delivery Because Coding Was Never the Bottleneck" (24 Mar 2026, Agoda/Faros AI).
- CIO.com, "The vibe coding crisis: Why you need a dual-track engineering strategy" (9 Apr 2026).
- InfoWorld, "Vibe coding or spec-driven development? How to choose" (5 May 2026).
- Analytics Drift / The New Stack on Karpathy's "vibe coding is passé."
- Wikipedia "Vibe coding" (timeline aggregator: METR, Y Combinator ~25% W25 cohort ~95% AI-gen, Collins WOTY Nov 2025).

### 3.5 Trends Table — Vibe Coding

| Trend | State of the art (May–Jun 2026) | Maturity | Explicit CT2 implication |
|---|---|---|---|
| Bottleneck moved to verification | Faros AI: +21% tasks, +98% PRs, **+91% review time** | stable (measured) | This is **the market validation of CT2's bet.** Lead CT2 positioning with *verification*, not throughput. Lens is the "separate governance/trust layer" the generating agent cannot ship for itself. |
| Willison "no longer reviews every line" | Public admission, even for production | stable (signal) | The precise drift CT2 guards against. Mandatory dual-review with a fresh-context reviewer is the deliberate counterweight to individual review fatigue. |
| Dual-track strategy | Sandboxed disposable vs. spec-first production; never time the slow track by the fast track | stable | CT2 should make the *track* explicit per ticket. Pure-vibe is fine for helm-scoped throwaway exploration; anything production-bound triggers helm-plan → forge → lens. |
| Spec-driven ⟂ vibe (complementary) | "Prototype with vibe, harden with spec" | stable | Validates helm-plans-first sequencing. CT2 interoperates: helm's plan artifact *is* the spec that feeds forge; lens is the verification gate Spec-Kit omits. |
| Verification-layer tooling category | Qodo 2.0 multi-agent review, CodeRabbit; review shifts earlier | stable (products) / Grade-D metrics | Confirms a market for the review layer. But these are *single-vendor* reviewers; CT2's differentiator is *two mutually-unaware* models. Don't collapse into one judge. |
| "Grey box" evidence verification | Judge results against evidence, not line-by-line | stable (practice) | Maps onto CT2's verification-evidence discipline. The evidence graph (builds/tests/observed behavior) is exactly the "grey box" oracle that scales when agents write 80% of the code. |

---

## Second-Order Insights

1. **The three currents are one story told from three angles.** Harness engineering names the *substrate* (Model + Harness); agentic engineering names the *discipline* (planner-executor-reviewer + eval-first); vibe coding names the *failure mode the discipline corrects* (unreviewed acceptance). They converge on a single conclusion: **the generating agent must not be the certifying authority, and the certifying authority must be durable.** CT2 is a literal implementation of that conclusion.

2. **The runtime is eating orchestration but cannot eat verification authority.** Dynamic Workflows absorb the fan-out, the loop, the pacing, and the parallel verify. But a workflow's intermediate state lives in script variables; its resume journal dies when Claude Code exits; its subagents are forced into acceptEdits with no mid-run sign-off; its budget is a soft hint. The thing that is *structurally* outside the workflow is **durable, independent verification that gates state**. The 2026-05-13 reframe already claimed exactly this empty layer ("the runtime owns continuation; CT2 owns the protocol continuation must satisfy", §0.1). The workflow paradigm is the strongest evidence to date that the claim was correct — *and* that the layer is still empty.

3. **"The harness is half the score" cuts toward CT2, but only if CT2 measures.** If scaffold variance moves results 10–20 points, then a verification scaffold that catches a class of errors a bare model rationalizes is a *measurable product*, not a vibe. CT2's credibility move is the LangChain move: freeze the model, measure CT2's lift (dual-independent review catch-rate, regression-block rate) over an ungated baseline, and publish the delta. The conformance suite (reframe §10.3, ex-Bet 4) is the natural home.

4. **Reviewer independence must be upgraded from a session-era rule to a prompt-construction invariant — and the field just explained why.** CT2's independence today rests on session separation + a no-peek file rule. A *parent orchestration script* now holds every child's return value, so it could anchor a verifier by injecting a sibling's output into its prompt. Anthropic's own named **self-preferential bias** and MOSAIC-Bench's finding that reviewer agents approve ~25.8% of confirmed-vulnerable diffs (reframe §2.4 row 2) are the empirical floor under "independence is the product." The invariant to state: *a verifier's prompt MUST NOT contain any sibling reviewer's output.* This is conformance-testable but not mechanically preventable inside an opaque JS script — the honest limit CT2 must acknowledge (see open question).

5. **Budget is a fan-out *width* lever in the new paradigm, not a stop condition — and CT2 cannot pretend otherwise.** Ultracode's "token cost is not a constraint" and the workflow `budget` object (which scales fan-out depth via loop-until-budget) treat budget as throughput input. Crucially, Anthropic's own Task-budgets docs say `task_budget` is a **soft hint** (only `max_tokens` is a hard per-response cap), and that feature is beta and **not supported on Claude Code surfaces**. The 1,000-agent cap is the sole hard run-level guard. **CT2 must not promise token-budget enforcement it cannot deliver** — it has no live meter. CT2 bounds blast radius by *agent count*, *scope-first slicing*, *worktree isolation*, and its existing time/round circuit breakers, and records cost *post-hoc*. (This corrects the optimistic "hard ceiling" reading of the harness brief's primary observation #6 against Anthropic's docs.)

6. **Determinism constraints draw a clean boundary CT2 should adopt as authoring discipline, not fight.** Workflows forbid `Date.now()`/`Math.random()` for journaled resume. CT2's circuit-breaker stamps (`.started`/`.in-review`) and message IDs use wall-clock/random. The rule writes itself: CT2's time/round breakers and ID generation run **outside** the deterministic script (host session / one-shot tools); any CT2-emitted workflow derives IDs from stable inputs (content hashes, ticket id, round). This preserves both resume *and* CT2's breakers — a documentation/boundary win, not a blocker.

7. **The "review bottleneck as vibe coding scales" is super-linear, and fan-out makes it worse before CT2 makes it better.** Faros AI's +98% PRs / +91% review-time was measured *before* one-session fan-out. A single ultracode session can now produce dozens of subagent edits at once. If review capacity is the constraint, multiplying generation throughput multiplies the deficit. CT2's `pipeline()`-shaped answer — *verify each finding as soon as its review completes*, rather than barriering all generation before any review — is the structurally correct response, and it is exactly the documented workflow default. CT2's job is to make that verify stage *independent* and *durable*; the runtime already makes it *fast*.

8. **Codex's whitespace is CT2's moat in miniature.** Codex shipped subagents, goals, multi-agent v2, and remote control — but *no* independent dual-reviewer and *no* planner/implementer/reviewer protocol. Neither vendor will ship cross-vendor dual-review, because dual-independent review *dilutes a single vendor's session* (the reframe §1.1 observation, now confirmed across both vendors through this window). The verification layer is empty on both sides for the same structural reason. The corollary is load-bearing for this cycle: because cross-vendor review is the only configuration that puts a *different model family* on the evaluation side, the faster one vendor self-verifies (ultracode), the **more** the independent second vendor is required — Claude's orchestration lead is a reason to *strengthen* `lens-cx`, not retire it. Down-weighting either runtime removes the mechanism, not the overhead.

---

## What This Means for CT2

This section states the implications and **hands the decisions to the sibling strategy doc** (`docs/ct2-dynamic-workflow-strategy-2026-06.md`). Nothing here ratifies a CT2 decision; it frames what that doc must resolve. Each implication is mapped to the canonical reframe so it reads as continuity, not scope creep. Per the reframe's anti-metric (§0.5) and "subtraction beats addition" (§4.7), implications that grow CT2 must land in the **content tier** (adapters, role prompts, CT2-blessed templates — explicitly free to grow), while CT2 *core* should get **thinner** where native primitives now cover old hand-rolled mechanisms.

### The one-line position the strategy doc should adopt

> **Native workflows carry the work; CT2 carries the outcome.** A dynamic workflow is an *ephemeral executor*; CT2 is the *durable verification/protocol kernel* it must re-enter for its output to count.

This is the exact LSP/git/MCP framing the reframe already uses for A2A/ACP (§2.7: "the other protocols carry the conversation; CT2 carries the outcome"), now applied to the orchestration layer. It fills confirmed whitespace — a grep of the three 2026-05 strategy docs returns **zero** hits for dynamic workflows / ultracode / budget-scaled fan-out — so the position can be claimed cleanly without contradicting a prior decision. It extends, not overrides, the reframe's Boundary Decision Table (§5.1); the natural new row is *"Runtime asks CT2 to fan out / orchestrate → Runtime workflow → author or invoke a workflow in the adapter; it re-enters CT2 at the verify/commit boundary; never give a workflow terminal authority."*

### Implications mapped to the reframe

| # | Field signal (this survey) | CT2 implication | Reframe anchor | Tier | Confidence |
|---|---|---|---|---|---|
| I-1 | Dynamic workflows absorb orchestration; state is variables-only, session-scoped | Declare CT2 the verification/protocol kernel *above* native workflows; a workflow's output is non-authoritative until it re-enters `.ct2/` and is reconciled. The file ledger is the cold-restart rehydration the runtime lacks. | §0.1, §4.1, §5.1, D-001 | content (docs + adapter rule) | high |
| I-2 | Workflow subagents forced into acceptEdits; no mid-run sign-off (confirmed in docs) | **Forward bet (Phase 1.5+):** route any CT2-spawned subagent/workflow's writes to a per-subagent worktree (`isolation:"worktree"`), and require the parent role to merge into the ticket branch; the target/default branch is touched only by the reconciler after dual-approved sidecars. Worktrees **complement** (not replace) the single-in-progress O_EXCL lifecycle lock. *Worktrees are currently unimplemented — `worktrees/` is an empty Phase-1.5 dir per `spec/directory-structure.md`; this is a roadmap bet, not present readiness.* | §4.2, §4.4, §5.1, reframe §4.4 reviewer curtain | core+content | high (signal) / medium (readiness) |
| I-3 | A parent script holds all child returns; self-preferential bias is named | Upgrade reviewer independence from a no-peek file rule to a testable **prompt-construction invariant** in `spec/conformance.md`: a verifier subagent's prompt must contain no sibling reviewer's output. Ship a CT2-blessed adversarial-verify *template* so users don't hand-roll a leaky one. Honest limit: conformance-testable, not mechanically enforceable inside an opaque script. | §4.4, §9.3, D-009, D-013 | content (spec + template) | high |
| I-4 | Native patterns are N-of-M (judge panel, kill-on-majority skeptics) | Let CT2 *express* M-of-N quorum while keeping **2-of-2 cross-vendor dual-approval as the canonical floor and sole path to `done/`**; extra skeptics are advisory unless promoted by config. **Do not claim this is LOC-neutral** — the cc/cx pair is structurally baked into sidecar naming, `discover_pairs` regex, `review-status.lens-claude/lens-codex` frontmatter, the per-reviewer validator, and `enforce-review-independence.sh` (which assumes exactly one partner). Budget it as a moderate, multi-file change. | §4.4, §8.13, D-013 | core (reconciler + hook) | medium |
| I-5 | Budget is a fan-out width lever; Anthropic budgets are soft hints | **Do not build a live token-budget enforcer** (CT2 cannot meter; budgets are soft). Bound blast radius via the 1,000-agent cap, scope-first slicing, worktree isolation, and existing time/round breakers; record cost post-hoc plus a fan-out-width input + per-run agent count on the Cost axis. | reframe Cost/Latency axis; balanced scorecard | core (scorecard) | high |
| I-6 | Determinism: `Date.now()`/`Math.random()` throw in workflows | Spec a clean boundary: CT2 time/round breakers and ID generation run **outside** the workflow; any CT2-emitted workflow derives IDs from stable inputs. Preserves resume and keeps breakers intact. | §4.2, §4.3 | content (spec/authoring rule) | high |
| I-7 | Doctor is blind to workflow/subagent/budget primitives | Extend `ct2-runtime-doctor` with a workflow-class probe so helm can choose *workflow-executor* vs *serial role loop*. **Gate on observed capability (Workflow tool / ToolSearch-deferred-tool presence), not a guessed version** — the repo baseline is CC 2.1.138; treat absence as serial fallback, never error. (No `disableWorkflows` Claude state exists; if a kill-switch is wanted, model it as CT2-local config.) | reframe §2.1, runtime-capabilities | core (network-free probe) | medium |
| I-8 | A fan-out attributes findings to dozens of subagents | Add a single optional `parent_id` / `produced_by_agent` edge to `claims.jsonl` so fan-out evidence attributes to the orchestrating role/ticket — making the workflow's variables-only state durable in `.ct2/`. The DAG lives implicitly in flat records via edges, not a graph engine. | reframe evidence-graph; "filesystem is the database" §4.1 | core (one optional field) | high |
| I-9 | Ultracode default = orchestrate-by-default; helm-auto-cx forbids fan-out for state writes | Resolve the contradiction with a rule, not a ban: native workflows may fan out for read-only discovery/analysis and for forge *implementation* in isolated worktrees, but **CT2 state writes (seal, sidecar, reconcile, ticket mv) remain parent-owned one-shot operations**; subagents are non-role-holding. (Generalizes helm-auto-cx's existing parent-owns-writes rule to all roles — already codified in `ct2-product-strategy-2026-05.md` and the forge/helm-auto-cx SKILLs.) | §8.11, §4.4 | content (adapter/role rule) | high |
| I-10 | `/code-review ultra` (cloud, off local budget) and `/deep-research` exist | Adopt native surfaces as **evidence producers, never verdict authorities**: lens-cc *may* delegate its deep pass to the cloud review and cite it in-sidecar; helm-auto-cx *may* invoke deep research for discovery. Ultra is a *third single-model opinion*, not independent dual-review — it augments lens, never replaces the cc∧cx AND. (Naming: the repo's term is `/ultrareview`; "off local budget" is an inference to confirm.) | radar P2 "must not replace dual sidecar"; §8.13 | content (adapter) | medium |

### What CT2 should subtract (honoring the anti-metric)

The new native primitives let CT2 *core* shrink, which is the reframe's win condition (§0.5, §4.7):

- **Forge pacing.** Native self-paced `/loop` (60s–3600s, stops when provably done) + `Monitor` (streams a background script, no polling) replace CT2's hand-rolled active/idle/dormant intervals (60/120/180s). Reinforces "the loop belongs to the agent" (§4.3). *Caveat:* keep duration breakers *outside* any workflow (I-6).
- **Serial-safety framing.** `isolation:"worktree"` is the community-endorsed fix for AI merge conflicts (measured 27.67% agent-PR conflict rate, reframe §2.4 row 3). It makes `max_concurrent_worktrees:1` obsolete *as a safety mechanism* — but it does **not** replace the single-in-progress O_EXCL lifecycle lock (I-2 caveat).
- **Deep passes.** Delegate optional heavy lens passes to `/code-review ultra` (off the local rolling window) instead of CT2-bespoke deep-review logic — fail-soft to the existing path, never moving a ticket.

### Non-Goals for the 2026-06 cycle

- Making any research-preview/experimental surface (Dynamic Workflows, ultracode, agent teams) **load-bearing**. They are single-session and churning; the file protocol's durability is precisely the hedge.
- Enforcing a **token/cost ceiling** CT2 cannot meter (budgets are soft; only `max_tokens` is hard).
- Emitting vendor-specific `.claude/workflows/` scripts as CT2 *core* (couples CT2 to one vendor's JS dialect; if pursued at all, it is content-tier and explicitly optional — open question below).
- Replacing the `.ct2/` inbox or Kanban with native `SendMessage`/`TaskCreate`/`TeamCreate` (experimental, non-nesting, non-resumable, loses the on-disk audit trail). `.ct2/` stays authoritative.
- Abandoning 2-of-2 cross-vendor dual-approval as the canonical floor for `done/`.

### Honest uncertainty (must be resolved before any spec freeze)

- **Is the workflow `budget` object a hard ceiling in Claude Code specifically?** The harness brief said "+500k becomes a hard shared ceiling"; Anthropic's Task-budgets docs say `task_budget` is a soft hint, not supported on Claude Code surfaces. These conflict. CT2's no-token-enforcer bet (I-5) depends on the soft reading; needs direct confirmation before any budget spec text freezes.
- **Can reviewer-independence be mechanically enforced for in-workflow verifiers, or only conformance-tested?** A parent script can inject a sibling's output; CT2 cannot inspect the opaque script. Is a blessed template + conformance test sufficient, or is a tool-layer read-block needed — and does such a hook even fire inside a background workflow runtime?
- **Do CC hooks (and CT2's heartbeat-via-hooks) fire for subagents spawned *inside* a workflow?** Determines whether CT2 can enforce plan-evidence/independence at the hook layer for fan-out work or must rely on re-entry checks only.
- **Will a major runtime ship a file-first workflow-state convention natively?** (Reframe §12.9 risk; arXiv:2603.20432 shows file-first beating SOTA by 17.3%.) If Claude/Codex adopt `.ct2`-like on-disk state, CT2's durability differentiator narrows. Name the re-evaluation trigger.

### Hand-off

The decisions framed above — the kernel-above-workflows position, the worktree-isolation Phase-1.5 bet, the prompt-construction independence invariant, the M-of-N quorum generalization, the no-token-enforcer stance, the workflow-class probe, and the evidence-edge — are resolved (with roadmap, prioritization, kill criteria, and immediate tickets) in the sibling strategy document:

→ **`docs/ct2-dynamic-workflow-strategy-2026-06.md`** — *CT2 above native dynamic workflows.*

This survey is its evidence base. The feature radar (`docs/agent-platform-feature-radar-2026-05.md`) remains the canonical vendor-surface map; the protocol reframe (`docs/ct2-protocol-reframe-2026-05-13.md`) remains the canonical CT2 posture. This document composes with both and supersedes neither.

---

## Appendix A — Source Confidence Ledger (selected load-bearing claims)

| Claim | Grade | Primary corroboration | Caveat |
|---|---|---|---|
| Dynamic Workflows shipped research preview, CC v2.1.154+, May 28 2026 | A | code.claude.com/docs/en/workflows; claude.com blog | "research preview," not GA |
| Workflow subagents always acceptEdits; no mid-run sign-off | A | code.claude.com/docs/en/workflows | behavior of a *research-preview* feature; auto-approve is file-edits only |
| Ultracode = xhigh + auto-orchestrate; understand→change→verify | A | code.claude.com/docs/en/workflows | session-scoped; keyword was `workflow` pre-v2.1.160 |
| `task_budget` is a soft hint, not a hard cap; only `max_tokens` hard | A | platform.claude.com/docs/.../task-budgets | beta; **not supported on Claude Code surfaces** — conflicts with harness obs #6 |
| ToolSearch defers built-in tools (CC v2.1.69, ~14–16k→968 tokens) | A | anthropics/claude-code#31002 | shipped *undocumented*; deferred set is version/config-dependent |
| Codex stable 0.137.0 (2026-06-04); no native dual-review system | A | GitHub Releases API; developers.openai.com/codex | 0.138 alpha only |
| Faros AI: +21% tasks, +98% PRs, +91% review time | A | InfoQ (Agoda/Faros AI), Mar 24 2026 | — |
| Willison "no longer reviews every line" (6 May 2026) | A | simonwillison.net | personal practice, not a study |
| "Harness is half the score" / rank 30→5 model-frozen | A (LangChain self-report) | langchain.com blog | benchmark self-report |
| MOSAIC-Bench: reviewers approve 25.8% of confirmed-vulnerable diffs | C | arXiv:2605.03952 (via reframe §2.4) | re-verify via direct fetch |
| Bun Zig→Rust rewrite (~750k LOC, "11 days," 99.8% tests) | D/E | Anthropic blog + secondary | duration disputed (6 vs 11 days); magnitude marketing-grade |
| Token-burn anecdotes (90-agent review, 1.7M-token loop) | D/E | HN, aiweekly.co (single-source) | rumor-level; do not build strategy on these |
| Agent SDK separate credit pool effective Jun 15 2026 | C | secondary trackers | verify against official docs |

## Appendix B — Completion Audit For This Document

| Requested element | Where delivered |
|---|---|
| Dated header block (date, target, purpose, role-within-doc-set) | Top matter + frontmatter |
| Executive Summary | "Executive Summary" |
| Per-current section (state of the art, debates, converged-on, sources, trends table) | Current 1 (Harness), Current 2 (Agentic), Current 3 (Vibe) |
| Cross-current themes (control flow, compaction, eval-first, autonomy budgets, planner-executor-reviewer, spec-vs-vibe, review bottleneck) | Executive Summary "themes" line; threaded through all three sections and Second-Order Insights |
| Second-Order Insights | "Second-Order Insights" (8 items) |
| Implications + synthesis that hands off to strategy doc | "What This Means for CT2" + Hand-off |
| Cross-reference to `docs/ct2-dynamic-workflow-strategy-2026-06.md` | Frontmatter `hands_off_to`, I-table preamble, Hand-off section |
| Builds on / cross-refs 2026-05 docs | Frontmatter `composes_with`; reframe §-anchors throughout; radar cited as vendor-surface base |
| No fabricated versions/dates/features; unconfirmed marked | Source Confidence note; inline Grade markers; Appendix A ledger; honest-uncertainty + Non-Goals |
