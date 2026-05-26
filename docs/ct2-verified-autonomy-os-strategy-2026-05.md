# CT2 Verified Autonomy OS Strategy

Survey date: 2026-05-10 KST / 2026-05-09 US
Synthesis sources: `docs/agent-platform-feature-radar-2026-05.md`, `docs/ct2-product-strategy-2026-05.md`, user interview agreement
Target runtimes: Codex CLI 0.130.0, Claude Code 2.1.138

## 0. Executive Decision

CT2's next product identity is **Verified Autonomy OS**.

However, the OS here is not a universal agent OS. CT2 does not become Cursor, Devin, AutoGen, Jira/Linear, or a cloud SaaS orchestrator. What CT2 aims for is a **protocol kernel for a file-first dual-review engineering workflow**. The tickets, sidecars, inbox, ledger, evidence, and runtime mirror under `.ct2/` are the authority, and the Claude/Codex runtimes participate only as drivers, observers, advisors, and executors.

In one sentence:

> Any agent can act, but only verified evidence can move state.

The core decisions of this integrated strategy are the following six.

| Decision | Agreement |
|---|---|
| Canonical name | Verified Autonomy OS |
| Scope | Protocol kernel for a file-first dual-review workflow |
| Document structure | Feature Radar is a vendor-surface map, Product Strategy is the bet/risk document, this document is the canonical strategy |
| Measurement | Not a single north star but a Trust, Evidence, Autonomy, Cost/Latency balanced scorecard |
| First execution | Capability Registry + empirical baseline comes before Bet 1 |
| Runtime authority | Native scheduler, task, cloud, and remote-control are advisory-only |

## 1. Document Set

The three documents have different roles.

| Document | Role | Reason to keep |
|---|---|---|
| `agent-platform-feature-radar-2026-05.md` | Vendor-surface map | Tracks the latest features, stability, and adoption candidates of Codex/Claude broadly. |
| `ct2-product-strategy-2026-05.md` | Bet/risk strategy | Decides what to do first, what not to do, and under what conditions to stop. |
| `ct2-verified-autonomy-os-strategy-2026-05.md` | Canonical integrated plan | Combines the two documents and the interview agreement to set the final product direction, scorecard, and release train. |

Reading order:

1. Use §0-§5 of this document to set the final direction.
2. Check vendor evidence and capability details in the Feature Radar.
3. Check per-bet risk, kill criteria, and implementation sketch in the Product Strategy.
4. Code or spec changes follow the release train of this document and the existing `spec/` authority principle.

## 2. Product Identity

### 2.1 What CT2 Is

CT2 is not a tool for producing more agent executions; it is a protocol kernel that ensures agent execution culminates in **verifiable state transitions**.

CT2's product promise:

- Agent work starts from a ticket and acceptance criteria.
- Execution results are recorded as sidecars, command evidence, verifier output, and review verdicts.
- State transitions occur only through atomic `mv`.
- Reviewer independence takes priority over convenience.
- Vendor runtime state does not replace `.ct2/` state.

### 2.2 What CT2 Is Not

| Not | Reason |
|---|---|
| Universal agent OS | If the scope broadens, the `.ct2/` authority and dual-review invariant become blurred. |
| Cloud SaaS orchestrator | CT2's core is local file authority and git-adjacent evidence. |
| Jira/Linear replacement | Tickets must live next to the code; a PM database must not become the authority. |
| Single LLM framework | Independent review by Claude and Codex is the differentiator. |
| Automatic LLM router | It increases variance before static role contracts have stabilized. |

### 2.3 Relationship with Reliability Platform

`Reliability Platform` is not discarded. It is simply not the canonical name.

In summary:

- **Verified Autonomy OS**: product identity.
- **Protocol kernel**: implementation scope.
- **Reliability platform**: operational value as users perceive it.

That is, CT2 is a Verified Autonomy OS, and as a result it delivers multi-agent engineering reliability.

## 3. OS Primitives

Verified Autonomy OS realigns existing CT2 primitives from an operating-system perspective.

| OS primitive | CT2 equivalent | Productization within 6-12 weeks |
|---|---|---|
| Filesystem | `.ct2/` ticket, sidecar, inbox, ledger, artifacts | Maintain existing authority, clarify evidence/artifact paths |
| Commit/syscall | `ct2-seal`, `ct2-revise`, `ct2-status`, reconciler, atomic `mv` | Strengthened with decision bridge and policy compiler |
| Process table | active roles, Codex threads, Claude sessions, tmux, goals | Runtime twin and capability registry |
| Scheduler | reviewer loops, watchers, monitor/cron adapters | Advisory watcher plane |
| Permission model | role ownership, hook guardrails, sandbox/approval policy | Provider hook package + script-level enforcement |
| Flight recorder | command logs, sidecars, hook events, OTel correlation | Evidence graph + observability ledger |
| Device drivers | Codex app-server/remote-control, Claude CLI/SDK/remote-control | Runtime driver hardening |

Authority always flows downward.

```text
Vendor runtime events
  -> CT2 adapter/driver
  -> .ct2/inbox | .ct2/runtime | .ct2/evidence
  -> script/spec verifier
  -> atomic state transition
```

Conversely, flows where native tasks, the scheduler, remote-control, or Slack/Discord commands directly change ticket state are forbidden.

## 4. Balanced Scorecard

A single north star is not used. Verified Autonomy OS requires all four axes to be healthy at the same time.

| Axis | 90-day goal | Failure signal |
|---|---:|---|
| Trust | Trust ratio ≥ 0.92; first-pass approval baseline +15pp | revise/revert/reopen increases after done |
| Evidence | Evidence coverage ≥ 0.90; 0 uncited verifiers | sidecar contains only prose, with no command/evidence ids |
| Autonomy | lens latency p95 ≤ 90s; blocked->unblocked p95 baseline -70%; 0 stale runtime twins | watcher exists but fails to wake a stale role |
| Cost/Latency | $/ticket p50 baseline -30%; p50 ticket latency at or below baseline | cost dropped but trust/evidence fell |

We do not claim targets without a baseline. The first deliverable of Phase 0 is `ct2-baseline` and `.ct2/telemetry/baseline-2026-05.json`.

Required baselines:

| Baseline | Collection method | Minimum sample |
|---|---|---:|
| Trust ratio | Whether revise/revert/reopen occurs after reaching `done/` | 20 done tickets |
| First-pass approval | Round 0 review sidecar verdict | 20 review events |
| Evidence coverage | Whether each done transition links sidecar/evidence/verifier | 20 done tickets |
| Ticket latency | sealed -> done time | 20 tickets |
| Review latency | in-review entry -> reconciler verdict | 20 reviews |
| Blocked latency | blocked inbox -> answer/retry | 5 events |
| Cost | Start collection from the new telemetry sink | full sprint |

If samples are insufficient, do not inflate numbers. Mark that metric as "measurement started" and refresh with sprint data after six weeks.

## 5. Release Train

### 5.1 Sequence

The execution order is fixed as follows.

```text
Phase 0: Registry + Baseline
  -> Bet 1: Cost-aware Role Contracts
  -> Bet 2: Plan-mode-first Forge
  -> Bet 4: Eval Harness for Roles
  -> Bet 3: Ambient CT2 Advisory Bridge
  -> Bet 5: Native Task Graph Mirror (advisory spike only)
```

Reasoning for this order:

- Registry+Baseline is the admission gate for every bet.
- Cost contracts make cost/latency measurable.
- Plan evidence directly raises trust and evidence coverage.
- The eval harness prevents regressions in role/prompt changes.
- The ambient bridge has a large UX impact but carries external-channel risk, so it comes later.
- The native task mirror is the most enticing but has the highest state-authority forking risk, so it comes last.

### 5.2 Six-week Plan

| Week | Deliverable | Exit criteria |
|---|---|---|
| 0-1 | `ct2-runtime-doctor`, `ct2-baseline`, capability schema | Codex/Claude capabilities and scorecard baselines recorded; no state mutation |
| 1 | Codex flag empirical check, role contract draft | Drafts of 5 role contracts; config surface confirmed |
| 2 | `ct2-role-run`, `ct2-cost`, telemetry sink | cost.jsonl recorded from real ticket runs |
| 3 | `.ct2/plans/`, plan-evidence rule, forge flow | Plan-first handling on 5 tickets with review comparison |
| 4 | `.ct2/evals/` role eval baseline | Eval catches 1 intentional role MD regression |
| 5 | `ct2-bridge` notify-only pilot | 5 external notifications; 0 direct ticket edits |
| 6 | Retro, scorecard report, Bet 5 spike report | Scorecard refreshed; native mirror judged for advisory feasibility only |

### 5.3 First Seven Days

| Day | Task | Output |
|---|---|---|
| 1 | Design capability probe | `ct2-runtime-doctor` spec/ticket draft |
| 1 | Design baseline script | `bin/ct2-baseline` draft |
| 2 | Codex/Claude runtime capability schema | `.ct2/runtime/capabilities.json` schema draft |
| 3 | Scorecard baseline dry run | `.ct2/telemetry/baseline-2026-05.json` sample |
| 4 | Codex config surface spike | `.ct2/runtime/codex-flags-actual.md` |
| 5 | Role contract spec PR draft | `spec/role-contracts.md` proposal |
| 6 | Validate cost telemetry wrapper sketch | sample `cost.jsonl` |
| 7 | Go/no-go review | Phase 0 report and Bet 1 readiness decision |

## 6. Workstreams

### 6.1 Kernel Admission Layer

Source documents: Feature Radar P0, Product Strategy Phase 0.

Deliverables:

- `ct2-runtime-doctor`
- `.ct2/runtime/capabilities.json`
- `.ct2/runtime/degradations.md`
- `ct2-status --doctor` one-screen output

Rules:

- No state mutation.
- No network required for basic local probe.
- Under-development vendor features are never silently used for core transitions.

### 6.2 Decision and Permission Layer

Deliverables:

- `.ct2/decisions/{pending,answered,expired,audit}/`
- provider adapters for Codex requestUserInput and Claude AskUserQuestion
- hook guardrails for state transition, sidecar independence, reviewer source writes
- policy compiler that emits provider hook declarations and shell validators

Rules:

- Lens roles cannot use decisions to waive review criteria.
- Hooks are defense-in-depth, not sole authority.
- Scripts still enforce invariants when hooks are missing.

### 6.3 Evidence and Observability Layer

Deliverables:

- `.ct2/evidence/claims.jsonl`
- `.ct2/evidence/commands/`
- `.ct2/evidence/artifacts/`
- `.ct2/telemetry/events.jsonl`
- scorecard summary in `ct2-status`

Rules:

- Prompt/tool contents are not stored by default.
- Every done transition should be traceable to sidecar verdicts and evidence claims.
- Missing evidence is visible before review, not discovered only by lens roles.

### 6.4 Role Contract and Eval Layer

Deliverables:

- `spec/role-contracts.md`
- role contract block in `config/harness.yaml`
- `ct2-role-run`
- `ct2-cost`
- `.ct2/evals/{ct2-helm,ct2-forge,ct2-lens-cc,ct2-lens-cx}/`

Rules:

- Static contracts first; no automatic LLM router.
- Eval is regression defense, not self-improving role evolution.
- Eval budget is separate from ticket budget.

### 6.5 Advisory Runtime Layer

Deliverables:

- `.ct2/watchers/*.json`
- notify-only `ct2-bridge`
- remote re-entry protocol
- native task mirror spike report

Rules:

- Watchers wake or notify; they do not move terminal states.
- External channels never write ticket files directly.
- Cloud/remote outputs return as patch, PR, inbox message, evidence artifact, or advisory report.
- Native task graph is CT2 -> native only; native -> CT2 state mutation is blocked.

## 7. Spec PR Plan

CT2 is spec-first. Code PRs should follow spec PRs for behavior changes.

| Order | Spec PR | Purpose |
|---:|---|---|
| 1 | `spec/runtime-capabilities.md` | Capability registry, degraded paths, local version gates |
| 2 | `spec/balanced-scorecard.md` | Trust/Evidence/Autonomy/Cost definitions and baseline rules |
| 3 | `spec/role-contracts.md` | model/effort/budget/personality/latency contract per role |
| 4 | `spec/plan-evidence.md` | plan-first forge and plan adherence review rule |
| 5 | `spec/role-evals.md` | role MD/skill regression tests and pass criteria |
| 6 | `spec/decision-bridge.md` | user question, approval, policy exception schema |
| 7 | `spec/evidence-graph.md` | claim/evidence/verifier/verdict model |
| 8 | `spec/external-channels.md` | advisory bridge, notification, external command whitelist |
| 9 | `spec/runtime-mirror.md` | runtime twin, process table, native mirror advisory-only |

Existing specs likely touched:

- `spec/state-machine.md`
- `spec/ticket-format.md`
- `spec/review-protocol.md`
- `spec/directory-structure.md`
- `spec/git-workflow.md`

Per project rule, changes to `spec/` require explicit approval before implementation.

## 8. Anti-bets

These are explicitly rejected for this cycle.

| Anti-bet | Rejection |
|---|---|
| Vendor scheduler moves ticket to `done` | Breaks dual-review authority. |
| Image-only evidence | Cannot reconstruct why approval happened. |
| Cloud routine owns ticket lifecycle | `.ct2/` authority is lost. |
| TeamCreate/SendMessage replaces inbox | Runtime-instance persistence is weaker than file inbox. |
| Automatic LLM router | Adds unexplained variance before static contracts are stable. |
| LLM self-evolves roles | Role definitions must remain human-readable and reviewable. |
| Broad agent OS expansion | Dilutes CT2's file-first dual-review kernel. |

## 9. Kill Criteria

| Workstream | Kill or reshape trigger |
|---|---|
| Registry+Baseline | Capability report cannot run offline or mutates state. |
| Cost contracts | $/ticket reduction fails and Trust/Evidence fall together. |
| Plan-mode-first | first-pass approval fails to improve and p50 latency rises >20%. |
| Eval harness | runner cost exceeds budget or catches no real regression over four weeks. |
| Ambient bridge | any external channel directly edits ticket state. |
| Native task mirror | native task mismatch occurs daily or metadata cannot be blocked by hooks/scripts. |

Kill decisions produce `.ct2/postmortems/bet-{n}-kill-{date}.md`.

## 10. Product Requirements

### VAO-1 Capability Registry

CT2 must detect local Codex/Claude runtime capabilities, record degraded paths, and expose them in `ct2-status`.

### VAO-2 Balanced Scorecard

CT2 must collect enough local evidence to compute Trust, Evidence, Autonomy, and Cost/Latency metrics.

### VAO-3 Role Contracts

Each role must have explicit model/effort/budget/latency/personality policy, with enforcement or degradation visible.

### VAO-4 Plan Evidence

Forge must produce plan evidence before execution unless a ticket is explicitly plan-exempt.

### VAO-5 Role Evals

Role definitions and skills must be regression-testable with fixed inputs and machine-readable expected outputs.

### VAO-6 Decision Bridge

Human questions, approvals, and policy exceptions must map to a provider-neutral `.ct2/decisions/` schema.

### VAO-7 Hook Guardrails

Provider hooks should block or warn on invariant violations, while core scripts remain authoritative.

### VAO-8 Evidence Graph

Tickets and sidecars must be able to cite stable evidence ids for commands, screenshots, verifier output, and hook events.

### VAO-9 Advisory Runtime

Watchers, native tasks, cloud routines, Slack/Discord/Gmail/Notion bridges, and remote-control sessions may create advisory records only.

## 11. Decision Log

| Decision | Outcome |
|---|---|
| Use `Verified Autonomy OS` as canonical name | Accepted |
| Limit OS scope to protocol kernel | Accepted |
| Keep `Reliability Platform` as value framing | Accepted as secondary |
| Use a single north star metric | Rejected |
| Use balanced scorecard | Accepted |
| Start with Cost Contracts before measurement | Rejected |
| Start with Registry+Baseline | Accepted |
| Allow native/cloud runtime to mutate ticket state | Rejected |
| Keep runtime/cloud integrations advisory-only | Accepted |
| Rewrite Product Strategy around OS primitives | Accepted |

## 12. Immediate Next Tickets

1. `ct2-runtime-doctor`: probe Codex/Claude versions, features, app-server schema, MCP lists, and role compatibility.
2. `ct2-baseline`: compute initial Trust/Evidence/Autonomy baselines from `.ct2/` and git history.
3. `ct2-balanced-scorecard`: add scorecard rendering to `ct2-status`.
4. `ct2-role-contracts-spec`: draft `spec/role-contracts.md` and `config/harness.yaml` role contract block.
5. `ct2-cost-telemetry`: add `ct2-role-run`, `ct2-cost`, and cost JSONL sink.
6. `ct2-plan-evidence-spec`: define `.ct2/plans/` and plan adherence review requirements.
7. `ct2-role-evals-baseline`: create first eval fixtures for helm, forge, lens-cc, lens-cx.
8. `ct2-decision-bridge-spec`: define `.ct2/decisions/` schema and provider mappings.
9. `ct2-hook-guardrails`: implement hook scripts and script-level validators for core invariants.
10. `ct2-evidence-graph-spec`: define claim/evidence/verifier/verdict records.
11. `ct2-ambient-bridge-notify`: notify-only external bridge with strict whitelist.
12. `ct2-native-task-mirror-spike`: advisory feasibility spike, no production mirror.

## 13. Final Position

CT2 should not chase every new Claude or Codex feature as a product feature. The correct move is to treat vendor capabilities as device drivers behind a stable protocol kernel. The product is not "more agents." The product is **verified autonomy**: every role can act, every action leaves evidence, every state transition is auditable, and no runtime outside `.ct2/` can silently become authority.

The next six weeks should therefore optimize for one thing: proving that this kernel can measure and improve Trust, Evidence, Autonomy, and Cost/Latency at the same time. If that works, CT2 has a defensible product category. If it does not, more automation will only make the system harder to trust.
