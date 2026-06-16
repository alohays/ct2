---
type: strategy
title: "CT2 Loop Design — Executable Completion, Structured Signals, and the Memory Outer Loop"
version: "0.2.0"
authored: 2026-06-12
status: implemented
implemented: 2026-06-16
composes_with:
  - docs/ct2-dynamic-workflow-strategy-2026-06.md   # kernel-above-workflows position; this doc fills the kernel's loop-signal whitespace
  - docs/ct2-verified-autonomy-os-strategy-2026-05.md # balanced scorecard + advisory-plane authority model (inherited)
  - docs/ct2-protocol-reframe-2026-05-13.md           # "Agent Owns the Loop" law; subtraction discipline (constrains this doc)
audience: maintainers, contributors, adapter authors
---

# CT2 Loop Design Strategy

> CT2's loop **skeleton** — cross-vendor dual review, sealed rubrics, circuit breakers, a sole-authority reconciler — is ahead of the industry's published loop-design guidance. The **signals** flowing through that skeleton are still prose and self-report: submission is unchecked, grading collapses to one bit, archives are write-only, and the planner never hears outcomes. This roadmap makes completion executable (A), grading structured (B), memory consulted (C), and multi-ticket goals closed (D) — in that dependency order.

**Authored:** 2026-06-12 KST
**External evidence:** "Designing loops with Fable 5" (R. Lance Martin, 2026-06; https://x.com/RLanceMartin/status/2064397389189071163, surfaced via GeekNews https://news.hada.io/topic?id=30390)
**Method:** This document is the synthesis of a 26-agent adversarial analysis run on 2026-06-11: 5 subsystem readers over `spec/`/`bin/`/skills, 5 concept mappers producing 15 proposals, 15 independent skeptic-maintainer verifiers instructed to kill on five grounds (already-exists, principle violation, parallel system, cost at solo scale, misunderstands agent behavior). 13 proposals survived with corrections; 2 were killed (§5.1). Every `file:line` citation below was verified against the repo by at least one verifier, and load-bearing ones were re-verified by hand on 2026-06-12.
**Role within the document set:** The 2026-06 flagship (`docs/ct2-dynamic-workflow-strategy-2026-06.md`) positions CT2 as the **verification kernel above native workflows** and defines *where* authority lives. This document defines *what the kernel's loop actually verifies* — the content of the gates, grades, memory, and goal feedback that make the kernel's verdicts machine-grounded. It composes with that document and does not revisit its position.

---

## 0. Executive Summary

### 0.1 The Thesis, in One Sentence

**The article validates CT2's verifier architecture and exposes CT2's signal poverty: every joint where the loop should consume a machine-checkable signal currently consumes an agent's self-report.**

### 0.2 What the Article Claims, and Where CT2 Stands

Lance Martin's piece argues that loop design beats prompt engineering, on three mechanisms:

1. **Self-correction loops** — give the agent a goal/rubric and an environment that grades it; let it run → collect feedback → fix → re-run. (Claude Code `/goal`, CMA Outcomes; a 6× model-over-model gap on an ML benchmark attributed to in-loop strategy diversification.)
2. **Independent verifiers** — self-critique is unreliable; a separate-context verifier grades against an explicit rubric and feeds unmet criteria back.
3. **Memory as the outer loop** — cross-session filesystem memory matures along a 5-stage ladder: **Fail → Investigate → Verify → Distill → Consult**. Weak configurations stall at stage 1 (records nobody reads); the strongest configuration verified ~73% of its memory and distilled general rules it actually consulted.

Where CT2 stands, honestly:

| Article mechanism | CT2 today | Verdict |
|---|---|---|
| Independent verifier | Cross-vendor dual review (cc AND cx), immutable sidecars, independence hooks, reconciler-only `done/` | **Ahead.** The article proposes one same-model verifier in a separate context; CT2 neutralizes same-family blind spots structurally. No investment needed. |
| Rubric integrity | Sealed baseline (SHA-256 over AC text), seal gate on ticket quality | **Ahead.** The article assumes rubric integrity; CT2 enforces it. |
| Loop termination | Round cap (3), duration cap (120 min), attempt cap (9), review SLA watchdog | **Ahead.** |
| Machine-checkable completion | Submission and `done/` transitions run on self-report (§2, holes 1–2) | **Behind. Direction A.** |
| Structured grading feedback | 7-criterion rubric collapses to one `verdict` bit (§2, hole 3) | **Behind. Direction B.** |
| Memory ladder | Stage-1 ceiling: failure records accumulate, nothing reads them (§2, hole 4) | **Behind. Direction C.** |
| Outer goal loop | Reconciler silent to the planner on done/rejected (§2, hole 5) | **Behind. Direction D.** |

### 0.3 Decision Log

These decisions were made by the maintainer on 2026-06-11/12 (AskUserQuestion rounds) and are binding for this roadmap:

| # | Decision | Choice |
|---|---|---|
| D1 | Scope | Full A→B→C→D roadmap in one standalone document |
| D2 | AC-binding syntax | A dedicated `## Verification` ticket section (rejected: inline HTML-comment directives — invisible when rendered; frontmatter list — duplicates body ACs and strains writer ownership) |
| D3 | Gate hardness | Differential: submit gate hard immediately (it enforces an already-spec'd precondition); ac-verify and done gates ship advisory and are promoted to hard by release, never by runtime config (§3.5) |
| D4 | Memory depth | Specify the lessons ledger now (not deferred), built consult-first to avoid the two killed designs' pathology |
| D5 | Lesson promotion | Recurrence-based automatic promotion (≥2 distinct tickets), over structured keys — no human approval gate in the promotion path |
| D6 | Lesson storage | Per-project `.ct2/lessons/`; schema reserves a future global tier; no tracked host-repo files |
| D7 | Scorecard | Absorb new metrics into the existing Evidence axis; no new axis |
| D8 | Goal loop substrate | Provider-neutral `ct2-goal` that **subsumes** `ct2-codex-goal` (generalize-and-migrate, not extend, not parallel) |

### 0.4 The Dependency Order Is the Strategy

A is first not because it is the flashiest but because every other direction consumes its output: unverified `done/` poisons C's lessons and D's outcome feedback, and B's structured grades are only as meaningful as the execution evidence behind them. B is second because it is the cheapest (~50 lines of validator + grammar) and converts the raw material of C from cross-model free prose — which the adversarial round showed mines as count=1 noise — into grep-able structure. C builds the ladder consult-first because both killed proposals died as reader-less ledgers. D is last because an outer loop fed by self-reported completion would automate the propagation of unverified claims into planning.

### 0.5 Implementation Status (2026-06-16)

All eleven tickets landed across 15 dependency-ordered PRs (#54–#68), each
adversarially self-reviewed to merge-ready. The sections below stand as the
authored design rationale; this subsection records what shipped, the
maintainer-approved deviations, and the corrections to the authoring-time
state-of-code claims.

**PR map (A→B→C→D):**

| Ticket | PR | What shipped |
|---|---|---|
| T0.1 | #54 | Hard submit gate (`--submit-gate`, named-check gating, `branch:null` trap designed out) |
| T0.3 | #55 | `first_pass_approval` documented **and surfaced** in `ct2-status` |
| T1.1 | #56 | Sealed `## Verification` AC→command bindings (conditional 4th section, `seal_gate_verification_binding`) |
| T1.2 | #57 | `ct2-ac-verify` iterate-until-green + `ac`/`round` claim fields + advisory review-enter backstop |
| T1.3 | #58 | Reconciler done gate (round-fresh evidence) + watchdog approved-but-unverified |
| T2.1 | #59 | Per-AC grade grammar + the one approved-but-failed coherence rule (code-fence-safe) |
| T2.2 + T0.4 | #60 | Rework-resolution accounting + `ct2-pr-respond --mark-addressed` writer |
| T0.2 / C0 | #61 | Enriched escalation messages carrying the `### [BLOCKING]` digest |
| — | #64 | Reconcile lockfile create→pid-stamp race fix (found mid-roadmap) |
| T3.1 | #62 | `ct2-lesson` ledger (append-only event log folded to state; unsupervised recurrence promotion) |
| T3.2 | #63 | Pickup-stdout consult digest + plan-audit WARN tier + `Lessons consulted` line |
| T3.3 | #65 | Advisory planning lints at the seal gate |
| T4.1a | #66 | Provider-neutral `ct2-goal` loop |
| T4.1b | #67 | `ct2-codex-goal` subsumed by lazy mirror into the neutral record |
| T4.2 | #68 | Planner pull step (`helm-auto-cx` + interactive helm) |

**Maintainer deviations from this doc (AskUserQuestion, 2026-06-16):**

- **Phase 0 rescope** — T0.1 + a widened T0.3 (which also closes the `ct2-status`
  surfacing gap §4.1 relied on) stayed in Phase 0; T0.2 was sequenced after B (it
  needs B's `[BLOCKING]` grammar) and T0.4 moved beside the rework joint.
- **Direction C** built in full with **unsupervised** recurrence promotion (D5)
  plus a documented one-line human-gate fallback (`spec/lessons.md`).
- **Direction D / D8** — the codex→goals migration ships as a **lazy in-shim
  mirror with no protocol bump**, not the protocol-bump `ct2-migrate` path:
  `ct2-codex-goal` has zero live callers, and a 0.3→0.4 bump would cascade
  through the release machinery and every project's compatibility gate. Same
  subsumption outcome, far lower blast radius.

**Authoring-time claim corrections (verified against code during execution):**

- §4.1 / §6: `first_pass_approval` was *computed* by `ct2-baseline` but **not**
  surfaced by `ct2-status` — the kill-reason's "channel exists end-to-end" was
  half-true. T0.3 closed the surfacing gap.
- §3.2 / T0.4: `ct2-pr-respond --mark-addressed` did **not** exist; only the
  read-side backend did. It is now wired.
- §4.3: the lessons ledger uses `append_jsonl` (flock append) folded to state,
  **not** the `claims.jsonl` "tmpfile + os.replace" idiom the doc named (which
  was itself a mis-citation — `claims.jsonl` already uses `append_jsonl`). The
  WARN tier the doc assumed in `ct2-plan-audit` was new work, now built.
- §2.3 / §4.3: `spec/reconciler.md` gained the Recovery section + exit code 3,
  and `spec/plan-evidence.md`'s should-include list gained the
  `## Rework Resolutions` and `Lessons consulted` lines — these were new spec
  content, not edits to existing text.

**Gate hardness (§2.5):** the submit gate is hard from day one; the `ac-verify`
and done gates ship **advisory** behind versioned code constants
(`AC_VERIFY_GATE_HARD`, `DONE_GATE_HARD`). Their promotion to hard (T1.4) is a
release-time decision gated on the §2.5 field-test criteria and is deliberately
**not** flipped here.

---

## 1. Verified Gap Analysis

Five holes survived adversarial verification. Each is stated with the evidence that pinned it.

**Hole 1 — Completion is self-reported.**
`spec/state-machine.md` (transition table, in-progress → in-review row) declares the precondition "All AC checklist items checked `[x]`", but `bin/ct2-review-enter` contains zero checks — it resolves the ticket (`:54`), renames it (`:64`), and stamps `.meta`. The reconciler runs no audit at the `done/` transition: `reconcile_one` computes the destination purely from the two sidecar frontmatter verdicts and calls `update_ticket` (`bin/ct2-reconcile:269`) with no gate. The only mechanical outcome check is post-hoc — `evidence_claim_exists` in `bin/ct2-ticket-audit` passes on **any** single `ok:true` claim with an existing path; a stale `echo ok` command record satisfies it. This is a verified spec/implementation divergence, and the largest honesty hole in the protocol.

**Hole 2 — Forge has no cheap feedback loop.**
No mechanism binds an AC to a command. Forge's only feedback channel is the most expensive grader in the system: a full dual-LLM review round, of which there are at most three. The article's iterate-until-green micro-loop — cheap, deterministic, pre-review — has no substrate. (`spec/plan-evidence.md`'s AC→command mapping is a never-parsed "should".)

**Hole 3 — The review signal collapses to one bit.**
Lenses grade a 7-criterion rubric, but the reconciler reads only `verdict: approved|rejected` (`spec/sidecar-format.md` pins "the reconciler does not parse the body"). "Rejected on AC #2" and "rejected on style" are machine-indistinguishable; a sidecar with `verdict: approved` whose body reports a failed AC is undetectable (`bin/_ct2_validate_review_sidecar.py` checks heading presence only).

**Hole 4 — The memory ladder has a stage-1 ceiling.**
Failure records accumulate — immutable rejection sidecars, `claims.jsonl`, the `total-attempts` counter — but `.ct2/reviews/.archive/` is structurally write-only (`bin/ct2-revise` moves sidecars there precisely to get them out of the lens read path, and repo-wide grep confirms no reader), and a grep for `memory|lesson|distill` across `spec/` and `config/` returns nothing. No role's session start reads any historical artifact. **There are zero paths by which ticket A's rejection pattern influences ticket B.**

**Hole 5 — The planner never hears outcomes.**
`send_escalation` is called only in the escalated branch (`bin/ct2-reconcile:281-282`); done and rejected terminal outcomes produce no signal to any planner. Ticket N's actual outcome cannot inform ticket N+1's drafting.

*Acknowledged but out of scope this round:* the article attributes its headline 6× result to **strategy diversification across loop iterations**. CT2 rework rounds are the same persona retrying the same approach on the same branch. No surviving proposal addresses this; it is recorded as an open question (§9) rather than designed prematurely.

---

## 2. Direction A — Executable Completion

Convert completion from self-report to machine verification at the two transitions that matter: in-progress → in-review (submit) and in-review → done. Three components, each independently landable, ordered cheapest-first.

### 2.1 A0 — Submit Gate (small; hard immediately)

Enforce the precondition the spec already declares.

- `bin/ct2-ticket-audit`: new `--submit-gate` mode (requires `--ticket`), symmetric with `--seal-gate`. Adds `submit_gate_state` (state == in-progress, mirroring `seal_gate_state`) and forces `acceptance_criteria_checked` regardless of `AC_STATES`, listing unchecked AC items in the check's JSON evidence. `plan_evidence` already runs for in-progress (`PLAN_STATES`) and needs no change.
- `bin/ct2-review-enter`: after `resolve_ticket` (`:54`) and before `os.rename` (`:64`), subprocess `ct2-ticket-audit --json --submit-gate --ticket {id}` — the exact `ct2-seal:76` shell-out pattern (bins are extensionless and non-importable; every existing caller shells out). **Gate only on the named checks** `submit_gate_state`, `acceptance_criteria_checked`, `plan_evidence` — *not* on the process exit code or `report["complete"]`. Rationale (verifier-caught trap): the full in-progress audit also fails `required_frontmatter` for `branch: null` tickets (legitimate under `git_strategy: direct-to-main|none`, where `ct2-git-start` exits before normalizing it) and `sealed_baseline` for legacy tickets; a verbatim exit-code gate would hard-block every submit in such projects.
- On failure: print unchecked AC items / missing plan path to stderr, exit 2, **no state move**. No `--force` flag.
- Spec first: `spec/state-machine.md` gains a "Submit Gate" subsection parallel to "Seal Gate", stating explicitly that the gate evaluates only the three named checks and why the full audit report is not the gate.
- Both forge skills (`claude-plugin/skills/ct2-forge/SKILL.md` and `codex-plugin/skills/ct2-forge/SKILL.md`): a gate failure means return to the work step — re-verify ACs, write the round's plan — not retry the command and not mechanically flip checkboxes.
- Tests: extend `tests/test_ticket_audit.py` (submit-gate semantics, AC evidence detail) and `tests/test_state_lifecycle.py` (blocks with unchecked ACs, ticket stays in in-progress/; passes with all `[x]` + plan; rework round n+1 requires the r{n+1} plan; direct-to-main ticket with `branch: null` passes).

Honest scope note: the AC-checkbox half has teeth mainly on round 1 (boxes stay `[x]` across rejection); per-round teeth on rework come from `plan_evidence` r{n} and, later, from B's rework-resolution gate (§3.2).

### 2.2 A1 — `## Verification` Section + `ct2-ac-verify` (medium; the iterate-until-green micro-loop)

Bind ACs to commands, sealed against tampering, executed cheaply, recorded as evidence.

**Grammar** (`spec/ticket-format.md`, new optional body section, helm-authored at draft time):

```markdown
## Acceptance Criteria
- [ ] AC1: all unit tests pass
- [ ] AC2: zero lint warnings

## Verification
- AC1: `python -m unittest discover -s tests`
- AC2: `ruff check src/`
```

Per decision D2, this section is the single canonical binding syntax. ACs without a binding remain manual / reviewer-judged; tickets without the section behave byte-for-byte as today.

**Sealing.** `bin/_ct2_sealed_baseline.py` hashes `## Verification` as a conditional fourth section, with explicit absent-in-both-snapshot-and-ticket = ok so legacy baselines never flag drift. Check commands become tamper-evident exactly like AC text — forge cannot weaken its own grader mid-loop; a post-seal edit surfaces as existing sealed-baseline drift. (Known limit, stated honestly: sealing freezes *commands*, not the test files they invoke. A forge can gut a test post-seal. That is why lenses still independently judge whether each bound command proves its AC — §2.4.)

**Seal-gate check.** `bin/ct2-ticket-audit` `seal_gate_checks` gains `seal_gate_verification_binding`: every entry parses as ``- AC{n}: `cmd` `` with non-empty command and `n` referencing an existing AC checkbox. (Without this, a typo'd binding silently degrades to unverified prose.)

**Runner.** New `bin/ct2-ac-verify` (python stdlib, one-shot):
- Reads bindings from the **sealed snapshot** (`.ct2/reviews/{id}-sealed.md`), not the live ticket.
- Runs each command via `subprocess` with timeout from a new optional `harness.yaml` key `verification.command_timeout_sec` (hardcoded default 300 when absent).
- Records one claim per AC through the existing `ct2-evidence verifier` path, carrying two new **append-compatible claim fields** (same precedent as `parent_id`/`produced_by_agent`, `spec/evidence-graph.md`): `ac: <ordinal>` and `round: <review-round>`. No summary-string parsing, no new evidence subdirectory, no `.meta` shadow file — `claims.jsonl` is the single record (the `round` field is also what makes the done gate staleness-safe, §2.3).
- Flags: `--json` (per-AC results), `--no-record` (run without appending claims — the lens re-run mode).
- Exit 0 iff every bound command exits 0; no bindings → exit 0.

**Gate wiring.** `bin/ct2-review-enter`, after the A0 submit gate: when a sealed `## Verification` section exists, run `ct2-ac-verify` via the subprocess pattern already inside the same file (`mirror_issue`, `:36-38`). Non-zero → print failing AC ordinals, exit non-zero, no state move. Ships **advisory** (prints, does not block) and is promoted to hard by release per §3.5 — there is deliberately **no runtime hardness knob**: `harness.yaml` is not tamper-evident, and an advisory-mode config key would let forge reconfigure its own grader (verifier-caught trap).

**Roles.**
- Forge SKILL Step 6.5 (both plugins) becomes: "run `ct2-ac-verify {id}`; iterate until exit 0; flip an AC to `[x]` only when its bound check passes." This is the article's iterate-until-green loop, running before the dual-LLM review, with the review-enter gate as the mechanical backstop. The agent still owns the loop; CT2 supplies the deterministic green/red step.
- Lens role files (`config/ct2-lens-cc-role.md`, `config/ct2-lens-cx-role.md`) criterion 1: for bound ACs the reviewer **re-runs** `ct2-ac-verify {id} --json --no-record` in its own session and treats non-zero as BLOCKING, citing the JSON in the sidecar. Reviewers must **not** substitute forge-written claims for their own run — `claims.jsonl` is forge-appendable, and per the kernel rule (`spec/conformance.md`), in-workflow self-verification re-enters CT2 as evidence, never a verdict. The re-run, not claim-reading, is what makes the grader independent.

**Specs first:** `spec/ticket-format.md` (section grammar), `spec/state-machine.md` (precondition row annotated with the enforcing tool; Seal Gate table row), `spec/evidence-graph.md` (the `ac` and `round` claim fields). No new spec file — these contracts belong to the specs that already own tickets, transitions, and evidence.

### 2.3 A2 — Done Gate in the Reconciler (small-medium; advisory → hard)

Promote the post-hoc done audit to a transition-time gate, with the traps the adversarial round caught designed out.

- `bin/ct2-ticket-audit --done-gate --ticket {id}`: applies done-readiness checks to a ticket still in `in-review/` — `acceptance_criteria_checked`, `sealed_baseline` (via `compare_ticket_to_snapshot`), `plan_evidence`, `dual_approved_sidecars` (forced required), and the tightened evidence rule below. **Excludes** `verdict_approved` and done-state frontmatter checks — those are facts the reconciler itself writes *after* the gate (`update_ticket`, `bin/ct2-reconcile:269`).
- **Evidence freshness via the `round` claim field, never timestamps.** The gate requires at least one `ok:true` claim of kind `command|verifier` whose `round` equals the ticket's current review-round and whose path exists; when a `## Verification` section is sealed, it requires round-matched `ok:true` claims covering every bound AC. (Rejected alternative, verifier-caught: comparing claim timestamps against the `.meta/{id}.in-review` stamp fails every honest ticket — forge records evidence during in-progress, before that stamp exists.) Stated honestly in the spec: round-matching kills stale-evidence reuse across rounds; it does not prevent a fresh `echo ok` — semantic binding is A1's job.
- **Wiring:** in `reconcile_one`, when both verdicts are approved, run the gate by subprocess **before** `update_ticket` (`:269`), so a failure mutates nothing. On pass: identical to today. On fail: no move, no frontmatter write, exit **3** ("approved-but-unverified"; documented in `spec/reconciler.md` Exit Codes, ranking above 0 and below hard errors in `--discover` aggregation, never blocking other pairs), plus **one** helm inbox message per ticket-round deduplicated by a `.meta/{id}-r{n}.done-gate-failed` stamp (removed when the gate passes or `ct2-revise` archives the round) — without the stamp, every `--discover` pass would re-fail and mint a new message: unbounded inbox spam (verifier-caught).
- **Watchdog backstop (mandatory, same change):** `bin/ct2-review-watchdog` today skips any ticket whose sidecars are both present (`if not missing: continue`, `:167-169`), so a gate-failed approved ticket would strand in `in-review/` forever with no SLA. Add: both sidecars present with approved verdicts AND ticket still in `in-review/` past `max_review_duration_min` → escalate to `escalated/` + helm inbox, same as the missing-sidecar path.
- **Rollout in the same change:** add an evidence-recording step to forge SKILL Step 6.5 in **both** plugins (`ct2-evidence command|verifier --ticket {id} --round {r} --exit-code $?` after running verification). No role doc currently invokes `ct2-evidence` at all — without this, the gate fails 100% of tickets on day one (verifier-caught).
- **Recovery is specified, not implied** (`spec/reconciler.md`): a gate-failed ticket stays in `in-review/`; recovery is fixing the deficiency (checking AC boxes is baseline-safe — `_ct2_sealed_baseline.py` normalizes checkbox marks; recording the missing round-tagged evidence) and re-running `ct2-reconcile {id} {round}`. Unfixable tickets exit through the existing human escape paths.
- Specs first: `spec/reconciler.md` (precondition, exit 3, recovery, discover aggregation), `spec/state-machine.md` (in-review → done precondition gains "done-gate audit passes"; watchdog row gains the approved-but-unverified condition), `spec/evidence-graph.md` (Rules: done-traceability upgraded from "should" to a gated "must" once the gate is hard).

The `done/` invariant strengthens from "dual approval" to "dual approval AND machine-verified round-fresh evidence", with no change to the mv primitive, writer ownership, or the rule that only reviewer verdicts reject — a failed gate withholds the transition; it never judges.

### 2.4 What A Deliberately Does Not Do

- **No third LLM reviewer / outcomes-grader agent.** cc/cx already are independent rubric graders in separate contexts; what was missing is structure and execution, not another opinion. A deterministic execution gate is not a reviewer and takes no verdict authority.
- **No claim-trusting.** Forge-appended claims gate transitions but never substitute for lens judgment; lenses re-run.
- **No runtime hardness knobs** (§3.5).

### 2.5 Gate-Hardness Policy (D3)

| Gate | Ships as | Promotion |
|---|---|---|
| Submit gate (A0) | **Hard** | n/a — it enforces a precondition `spec/state-machine.md` has declared since the table was written; advisory would re-create the divergence |
| ac-verify gate (A1) | Advisory (prints failures, does not block) | Promoted to hard **by release** at the next MINOR once criteria below are met |
| Done gate (A2) | Advisory (reports + dedup'd inbox message, exits 0) | Same |

Promotion criteria, checked before the flipping release: (1) at least one full ticket lifecycle (seal → done) in a real host project with the advisory gate firing zero false positives; (2) conformance tests green for every named check in the gate set; (3) the forge evidence-recording step observably present in plan evidence. Hardness lives in code and is versioned per `spec/versioning.md`; existing `.ct2/` ledgers cross the bump via the standard `ct2-migrate-<from>-<to>` path. Rejected alternative: a `harness.yaml` enable key — runtime config is not tamper-evident, and a gate the gated party can disable is not a gate.

---

## 3. Direction B — Structured Review Signal

Make the grading that lenses already perform machine-readable, without widening the malformed-sidecar wedge surface.

### 3.1 Per-AC Grade Lines in the Sidecar Body (small)

**Carrier decision (merge note):** two surviving variants proposed different carriers — a frontmatter `ac-results` list and a body-line grammar in the existing `## Acceptance Criteria Check` section. This roadmap picks the **body-line grammar** as the single carrier: the section already exists and is already written by both lenses (the grammar formalizes practice rather than adding a duplicate channel), and warn-only parsing avoids the permanent-wedge failure mode. The frontmatter list is dropped as a parallel carrier; revisiting it as a *promotion* once grammar adherence is proven is an open question (§9).

- **Spec** (`spec/sidecar-format.md` only): lines in `## Acceptance Criteria Check` SHOULD use ``- AC{n}: (pass|fail) — {reason}`` with optional `(evidence: {claim-id})` citing `.ct2/evidence/claims.jsonl`. The "reconciler does not parse the body" rule gains exactly one carve-out: **a sidecar with `verdict: approved` containing a line that parses as `- AC{n}: fail` is invalid** — a validity gate, not a verdict input; `verdict` remains the only state-moving field.
- **Validator** (`bin/_ct2_validate_review_sidecar.py`, already invoked per sidecar by the reconciler):
  - HARD-FAIL only on `verdict: approved` + any successfully-parsed `fail` line. This fires only on lines that already parse — free prose or near-miss formatting can never wedge a ticket.
  - WARN-ONLY (stderr, exit 0) on unparseable lines in the section and on AC count differing from the sealed baseline's checkbox count.
  - **No** rejected-with-all-pass rule — rejection on criteria 2–7 with all ACs passing is legitimate (verifier-caught semantic error in the original proposal: it named "rejected on style" as real, then outlawed it).
- **Recovery documented** (`spec/reconciler.md`): sidecars are immutable and the validator's hard-fail wedges the pair until human action; the procedure (inspect, `ct2-revise`) is written down *because* this change widens that failure class, and the watchdog extension from §2.3 provides the SLA backstop.
- **Authoring surfaces, minimal:** the grammar in `templates/review.md` plus one bullet in each lens prompt surface (`config/ct2-lens-cc-role.md`, `config/ct2-lens-cx-role.md`, and the lens-cx validator checklist in `spec/codex-runtime-contract.md`).
- **Dropped** (anti-parallel-system): the proposed `unmet-acs.json` feedback file — forge's mandated rework step already reads both rejection sidecars, which now yield grep-able `- AC{n}: fail` lines directly; a second channel would also survive `ct2-revise` as stale state.

Payoff: the "approved while admitting an AC failed" contradiction becomes deterministically detectable; rework feedback becomes structured; and C's distillation raw material stops being cross-model free prose.

### 3.2 Rework-Resolution Accounting (medium)

Close the reject → rework joint with existing artifacts.

- **Wire the dangling writer:** `ct2-pr-respond --mark-addressed {comment-id}` appends to `.meta/{id}.pr-addressed.json` via the existing `atomic_write_json`. (Verified 2026-06-12: `_ct2_pr.py:434` rewrites the file but only with its prior contents — nothing ever *adds* ids, so the PR TODO regenerates identically every round.)
- **Re-entry gate:** extend A0's `--submit-gate` (or a sibling named check): when `review-round` n > 0, fail if any `### [BLOCKING]` heading parsed from both round n-1 sidecars lacks a matching entry in a `## Rework Resolutions` section of the round-n plan evidence `.ct2/plans/{id}-r{n}.md`. No new tool, no new mutable JSON, no third issue ledger (verifier-caught: a `rework-todo.json` would be double bookkeeping alongside sidecar BLOCKING blocks and the pr-todo) — the resolution record lives in the already-required, already-reviewer-read plan evidence; sidecars stay immutable.
- **Verification stays independent:** one added criterion line in both lens role files — "at round n>0, verify each prior-round BLOCKING resolution claimed in the plan evidence against the diff; a false resolution claim is BLOCKING" — explicitly **additive** to the full 7-criteria pass (never a "targeted diff" substitute, which would contradict the all-criteria-every-round rule).
- **Spec:** `spec/sidecar-format.md` promotes `### [BLOCKING] {title}` from convention to machine-parsed form (one heading per blocking issue, title mandatory); `spec/review-protocol.md` gains a short Rework Resolution Contract section.

---

## 4. Direction C — Memory Outer Loop, Consult-First

### 4.1 Why the First Two Ledger Designs Died (Anti-Resurrection)

The adversarial round killed two orthodox memory designs, and the kill reasons are the design constraints for this section:

| Killed proposal | Fatal grounds |
|---|---|
| `ct2-lesson` ledger (candidate→verified→distilled, bound to evidence claims and eval cases) | Shipped Verify+Distill with **no Consult** — nothing made any role read it: a reader-less ledger, the exact pathology it diagnosed in `.archive/`. "verify --claim flips on an `ok:true` row" is **provenance, not verification** — one command exiting 0 once proves nothing about a general rule. Category mismatch: `ct2-role-eval` asserts on role-definition markdown at CT2-development time; host-repo operational lessons cannot be eval cases. Plus two false current-state claims. |
| `ct2-planning-digest` (outcome history distilled into a planning brief) | Its load-bearing metric (`first_pass_approval`) is **already computed** by `ct2-baseline` and surfaced via `ct2-status` at helm init — the channel exists end-to-end. Solo-scale buckets are n=1–3 against `MIN_DONE_SAMPLE=20`; mining cross-model free-text `[BLOCKING]` phrases yields count=1 noise; "prefer high-approval shapes" invites overfitting worse than the blank slate. |

Constraints extracted: **(i)** define the read path first and make it un-skippable; **(ii)** never claim execution-verified general rules — recurrence is corroboration, not proof; **(iii)** match keys on declared structure, never on cross-model prose; **(iv)** `.ct2/postmortems/` is reserved for VAO bet-kill records (`docs/ct2-verified-autonomy-os-strategy-2026-05.md:316`) and must not be squatted on.

### 4.2 C0 — Enriched Escalation Messages (immediate, ~15 lines)

`bin/ct2-reconcile` `send_escalation` (`:138`): include, for each current-round sidecar, its path and the verbatim `### [BLOCKING]` heading lines extracted from `## Issues Found` (best-effort; if none parse, say so — until §3.1 lands the tag is convention). Sidecars are still live at escalation time, so no copying and no new directory. `spec/reconciler.md` specifies the message body; helm SKILL escalation-response gains one sentence noting prior-round sidecars live at `.ct2/reviews/.archive/{ts}-{id}/` after `ct2-revise`. This alone makes escalations carry *why*, not just "failed after round N".

### 4.3 The Lessons Ledger (D4–D6)

**Store:** `.ct2/lessons/lessons.jsonl`, append-only, per-project (D6), written exclusively by a new `bin/ct2-lesson` (tmpfile-in-`.ct2/.tmp` + `os.replace`, the `claims.jsonl` idiom). `ct2-init` creates the directory; `spec/directory-structure.md` and the protocol surface gain rows — the migration/conformance weight of a new ledger under `spec/protocol-surface.md` is acknowledged and accepted (D4).

**Record schema** (`spec/lessons.md`, new spec):

```json
{"id": "lsn-20260612T031500Z-001", "ts": "...", "ticket": "012", "round": 2,
 "source": ".ct2/reviews/012-cx-r2.md",
 "category": "missing-regression-test",
 "rule": "Bug-fix tickets touching bin/ must bind an AC to the regression test command.",
 "scope": "role:forge", "paths": ["bin/*", "tests/*"],
 "status": "candidate", "occurrences": [{"ticket": "012", "round": 2, "source": "..."}],
 "retired_reason": null}
```

- `category` is drawn from a **spec-owned enumerated taxonomy** (initial set: `missing-regression-test`, `scope-creep`, `ac-unverifiable`, `evidence-missing`, `env-setup`, `flaky-test`, `api-contract`, `style-convention`; extended only by spec MINOR). This is constraint (iii): recurrence is computed over declared categorical keys, never over prose similarity — the direct answer to the cross-model count=1 noise that killed the digest.
- `scope` admits `repo | role:forge | role:helm`; the value set reserves `global` for a future `~/.ct2` tier without schema change (D6).
- `rule` is ≤200 chars, imperative.

**Status semantics — `candidate | corroborated | retired` (D5, with the provenance trap designed out).** On every `ct2-lesson add`, the tool deterministically checks for an existing non-retired lesson with the same `(category, scope)` from a **different ticket** (path-glob overlap refines the match when both records carry paths). If found: append an occurrence to the existing record and set `status: corroborated` — one record, no duplicates. Otherwise: append a new `candidate`. Promotion is automatic and unsupervised (D5). The status is deliberately named **corroborated**, not "verified": it asserts *this failure class recurred across ≥2 tickets and the rule is load-bearing*, never *this rule was proven by execution* — the overclaim that killed the original design. `ct2-lesson retire --id X --reason "..."` is the correction path; retired lessons leave the digest.

**Writers (capture = stages 1–2):**
- Forge, rework pickup (Step 4): after reading the rejection sidecars (whose `- AC{n}: fail` lines and `[BLOCKING]` headings are structured post-B), record one lesson per BLOCKING class it fixes — category, rule, paths.
- Helm, escalation-response: after reading the enriched escalation (C0), record the lesson; interactive helm confirms wording with the user, `helm-auto-cx` records autonomously with a ledger event.
- Single-writer discipline: roles invoke `ct2-lesson`; nothing else writes the file.

**Consult (stage 5 — built first, un-skippable):**
- `ct2-lesson digest --role forge --ticket {id} [--max 10]`: deterministic ranking — corroborated before candidates (candidates labeled `[unverified]`), scope filter (`repo` + `role:{role}`), `fnmatch` overlap of lesson paths against the ticket's `touched-files` frontmatter, recency tiebreak; hard cap ~1200 chars; clean "no lessons" line. The ranking algorithm is specified in `spec/lessons.md`, not implementation-defined.
- **The invoker is `bin/ct2-pickup`**, which prints the digest block as part of its stdout (fail-soft no-op when the ledger or tool is absent). Consult rides the existing mandatory serialized pickup path — not an optional SKILL.md "run this command" step that agents demonstrably skip (verifier-caught; this is the article's own stage-5 finding applied to CT2's design).
- Forge plan evidence gains a mandatory line `Lessons consulted: <ids or none>` in `.ct2/plans/{id}-r{round}.md`; `spec/plan-evidence.md`'s should-include list is amended. The advisory presence check lives in `bin/ct2-plan-audit` (the existing plan auditor — `ct2-ticket-audit` has no WARN tier), never blocking.
- **Lenses are excluded from lesson consumption, by design.** Forge-authored memory injected into reviewer context is precisely the anchoring channel the independence hooks (`claude-plugin/hooks/enforce-review-independence.sh`, `spec/conformance.md` prompt-construction rules) exist to prevent. Enforcement of consult quality is the deterministic plan-audit check plus the human trail — stated as such, not overclaimed as "visible in review".
- Helm-side digest wiring is deferred (at authoring time `touched-files` does not yet exist, so ranking degrades): the helm consult surface is planning lints (§4.4). Revisit only if the forge loop demonstrates lesson quality (§9).

**Ladder mapping (the article's five stages onto CT2 mechanisms):**

| Stage | CT2 mechanism |
|---|---|
| 1 Fail | Structured `- AC{n}: fail` lines + `[BLOCKING]` headings (B); enriched escalations (C0) |
| 2 Investigate | `ct2-lesson add` at rework/escalation: category + imperative rule + paths |
| 3 Verify → **Corroborate** | Automatic recurrence promotion over `(category, scope)` keys — honest about being corroboration, not proof |
| 4 Distill | Planning lints (§4.4); human promotion of corroborated lessons into helm SKILL quality principles or seal-gate hard checks (`ct2-lesson digest --status corroborated` is the review queue) — the evolution path that already demonstrably works (helm SKILL's regression-test rule) |
| 5 Consult | Pickup-stdout digest + mandatory plan-evidence line + draft-time lint advisories |

### 4.4 Planning Lints — the Distill Endpoint on the Planning Side (small)

- **Artifact:** `.ct2/config/planning-lints.json` — list of `{id, section: requirements|constraints|acceptance-criteria|any, pattern, mode: must-match|must-not-match, advice, source, added}`. A commented empty template ships in repo `config/` and is copied by `ct2-init` (the established config-template convention).
- **Enforcement:** `bin/ct2-ticket-audit` `seal_gate_checks` loads the file fail-soft (missing/invalid → zero lints) and appends one **advisory** entry per triggered lint using the existing check shape (`{name: "seal_gate_lint_{id}", ok: true, evidence: {advice, lint: id}}`) — the seven blocking checks and the gate's exit semantics stay byte-for-byte unchanged.
- **Consult-by-construction at draft time** (verifier-caught: `ct2-seal:76` discards audit output on success, and sealed tickets are immutable to helm — a post-gate warn arrives after the decision it should influence): helm's ticket-authoring workflow gains a mandatory pre-approval step — run `ct2-ticket-audit --seal-gate --ticket {id}` on the draft and surface `seal_gate_lint_*` advisories alongside the ticket preview while the draft is still editable. `ct2-seal` additionally prints (not discards) lint lines on a passing gate, as trail.
- **Curation:** lint proposals happen at the two moments helm verifiably sees a failure cause — escalation-response and `ct2-revise` — via AskUserQuestion; on approval helm appends via tmpfile + mv. A corroborated lesson with a regex-expressible pattern is the natural lint source (the lesson→lint bridge). Access matrix gains an explicit row: `.ct2/config/planning-lints.json` — helm read yes, write append-only and only after explicit user approval; the rest of `.ct2/config/` stays human-owned.
- **Spec:** an "Advisory planning lints" subsection in `spec/state-machine.md` § Seal Gate (warn-only, never blocks, blocking set remains the static seven), schema inline — no separate spec file at this size.
- Honesty note: the flagship example rule (regression-test AC for bug fixes) already exists as prose in helm's SKILL — this mechanizes the existing evolution path rather than inventing one.

---

## 5. Direction D — Provider-Neutral Goal Loop

### 5.1 Decision: Generalize and Subsume, Not Extend, Not Parallel (D8)

The adversarial round established that `bin/ct2-codex-goal` already persists a goal record (objective, status, budget), a scope record with an ordered ticket list and machine-readable completion conditions, an event ledger, and `status`/`audit` commands cross-referencing every in-scope ticket against all seven kanban dirs — nothing about it is Codex-specific except its name and `.ct2/codex/` placement. Building `.ct2/campaigns/` beside it would create a second source of truth for goal membership (kill-grade parallel system); extending it as-is entrenches the provider-flavored debt. The maintainer's decision is the third path: a **provider-neutral `ct2-goal` that subsumes it**, following the Decision Bridge precedent (`spec/decision-bridge.md`): one neutral record, provider surfaces as renders, never a second truth.

### 5.2 Design

- **Layout:** `.ct2/goals/{slug}/` — `goal.json` (objective, status `open|paused|complete|abandoned`, stopping-rule, optional `outcome-check` command, timestamps), `scope.json` (ordered tickets + completion conditions), `ledger.jsonl` (events). New `spec/goal-loop.md` owns the schemas and the loop contract.
- **Tool:** `bin/ct2-goal` — `start | add-ticket {slug} {ticket} | status | audit | pause | complete | abandon`. `add-ticket` lets production-mode goals (which start with empty scope) register each ticket as the planner seals it, making `audit` the outcome tracker. `audit` runs `outcome-check` when set and records the exit code via `ct2-evidence verifier` — **evidence, never a verdict**; goals never gate or move ticket state.
- **Migration:** `ct2-codex-goal` becomes a thin deprecated shim delegating to `ct2-goal`; existing `.ct2/codex/` goal records are migrated by the standard `ct2-migrate` path at the protocol bump (`spec/protocol-surface.md`, `spec/versioning.md`).
- **Feedback step — pull, never push** (verifier-caught: interactive helm reads its inbox only at init, and `helm-auto-cx` has no inbox-read step — a reconciler push message would land unread; "Agent Owns the Loop" puts the poll in the planner): `helm-auto-cx` SKILL gains, at the top of every planning iteration: run `ct2-goal audit`; for each in-scope ticket newly in done/rejected/escalated, read its final-round sidecars (structured per B) and append an outcome event to the ledger **before** drafting the next ticket; on an escalated in-scope ticket, `ct2-goal pause` and surface to the user; stop when the stopping rule or outcome-check is satisfied. Interactive helm gets the equivalent optional workflow. `ct2-reconcile` is untouched — escalation remains its only helm message.

D lands last (§0.4): an outer loop is only as trustworthy as the completion signal it consumes, which is A's product.

---

## 6. Scorecard Absorption (D7)

No new axis. The **Evidence** axis (`spec/balanced-scorecard.md`) gains one input once A is hard: `ac_verified_done` — the fraction of done tickets whose final round carries round-matched `ok:true` claims covering every bound AC. `ct2-baseline` computes it under the existing honesty rules (`measurement_started` below sample minimums; no live token metering claims). Consult-coverage (the article's most distinctive metric) is deliberately deferred until C produces enough `Lessons consulted` lines to measure (§9).

Salvage item from the killed digest (small, immediate): `first_pass_approval` is already computed by `ct2-baseline` and printed by `ct2-status`, but is undocumented in `spec/balanced-scorecard.md` and untested — document and test it.

---

## 7. Roadmap

Phases are dependency-ordered; tickets within a phase are independently landable. Sizes: S ≲ 1 session, M ≈ 1–2 sessions, L = multi-session.

**Phase 0 — Close the divergences (all S, all independent):**
- **T0.1** Submit gate (§2.1): spec Submit Gate section, `--submit-gate`, review-enter wiring, both forge SKILLs, tests. *Hard from day one.*
- **T0.2** Enriched escalation messages (§4.2).
- **T0.3** Document + test `first_pass_approval` in `spec/balanced-scorecard.md` (§6).
- **T0.4** `ct2-pr-respond --mark-addressed` writer (§3.2).

**Phase 1 — Executable completion (A):**
- **T1.1** `## Verification` grammar + sealed fourth section + `seal_gate_verification_binding` (M).
- **T1.2** `bin/ct2-ac-verify` + `ac`/`round` claim fields + forge iterate-until-green + evidence-recording step + advisory review-enter wiring (M).
- **T1.3** `--done-gate` + reconciler wiring (advisory) + watchdog approved-but-unverified extension (M).
- **T1.4** Hardness-promotion release once §2.5 criteria are met (S).

**Phase 2 — Structured signal (B):**
- **T2.1** Sidecar AC-line grammar + validator coherence hard-rule + warn-only checks + templates/lens prompts + documented recovery (S/M).
- **T2.2** `## Rework Resolutions` contract + round>0 re-entry check + lens resolution-verification criterion (M).

**Phase 3 — Memory (C):**
- **T3.1** `spec/lessons.md` + `bin/ct2-lesson` (add/retire/digest, recurrence promotion) + `ct2-init` dir + protocol-surface row (M).
- **T3.2** Pickup digest injection + plan-evidence `Lessons consulted` line + plan-audit advisory check (S).
- **T3.3** Planning lints: config template + seal-gate advisory entries + helm draft-time audit step + curation workflow + access-matrix row (M).

**Phase 4 — Goal loop (D):**
- **T4.1** `spec/goal-loop.md` + `bin/ct2-goal` + `ct2-codex-goal` shim + migration (L).
- **T4.2** `helm-auto-cx` pull step + interactive helm goal workflow (S/M).

---

## 8. Risks

1. **Gate bricking.** The single biggest risk; three concrete false-positive generators were caught and designed out in §2 (full-exit-code gating vs `branch: null`, timestamp-vs-stamp freshness, the watchdog skip). Implementations must follow the corrected forms in this document, not the original proposal texts. Residual mitigation: advisory phases, named-check gating, dedup stamps, documented recovery, conformance tests per gate.
2. **Tests can still be weakened.** Sealing freezes commands, not test files; a forge can gut a test post-seal and go green. The lens re-run + independent judgment requirement is the backstop; this is stated in the lens role files, not assumed.
3. **LLM grammar adherence (B).** Mitigated by warn-only parsing everywhere except the single approved+parsed-fail coherence rule, which fires only on lines that already parse.
4. **Lesson noise under unsupervised promotion (D5).** Recurrence over a closed category taxonomy bounds the false-corroboration surface, `[unverified]` labels keep candidates honest, `retire` is the correction path, and the digest cap bounds context cost. If corroborated lessons prove low-quality in practice, the fallback is re-introducing the human approval step — a one-line change to `ct2-lesson add`.
5. **Solo-scale sample sizes.** Inherited honestly from `ct2-baseline`: metrics report `measurement_started` below minimums; no planning behavior is ever keyed to n=2 statistics (the killed digest's lesson).
6. **Surface growth vs the subtraction discipline.** This roadmap adds tools (`ct2-ac-verify`, `ct2-lesson`, `ct2-goal`), one ledger, and two spec files. The tension with the reframe's shrinking-core anti-metric is real and acknowledged: the additions are kernel-tier verification surface — precisely the product the 2026-06 flagship says CT2 is — and are partially offset by D retiring a provider-specific tool (`ct2-codex-goal`) and by adding zero new agents, roles, or reviewers. Anything in this roadmap that a native runtime later absorbs (e.g., a native iterate-until-green primitive) should be deleted per the established discipline.

---

## 9. Open Questions

1. **Strategy diversification across rework rounds.** The article's headline result came from varying approach across loop iterations; CT2 rework is same-persona, same-approach retry. Candidate shapes (vary the forge prompt by round; a round-2 "different angle" directive; fresh-context rework) are all unverified — design only after A/B land and rework rounds carry structured failure data worth diversifying against.
2. **Global lessons tier.** `scope: global` is schema-reserved (D6). Whether harness-level lessons (about CT2 itself, not the host repo) belong in `~/.ct2/lessons/` and how they sync is deferred until per-project lessons demonstrate consult value.
3. **Consult-coverage metric.** Once C runs, `ct2-baseline` could measure the fraction of plans whose consulted lessons were non-empty and relevant — the article's 73% analogue. Deferred for sample-size honesty.
4. **Frontmatter `ac-results` promotion.** If B's body-line grammar shows high adherence, promoting grades into validated frontmatter (and eventually required-at-MINOR) becomes attractive; revisit with adherence data.
5. **Helm-side lesson digest.** Deferred (§4.3); planning lints are the helm consult surface for now. Revisit if forge-loop lesson quality is demonstrated.
6. **Lint pattern quality at solo scale.** Regex lints curated from a handful of failures may overfit; the warn-only ceiling bounds the damage, but whether they help at all is an empirical question the first few entries will answer.

---

## 10. Non-Goals

- **No third LLM reviewer or outcomes-grader agent.** Structure and execution were missing, not opinions; cc/cx AND remains the verdict authority.
- **No token metering or budget enforcement** (Token Honesty Rule, `spec/balanced-scorecard.md`).
- **No role self-modification.** Distillation endpoints are config (lints), human-promoted SKILL prose, and the eval plane — `spec/role-evals.md`'s prohibition stands.
- **No tracked host-repo memory.** Lessons live in untracked `.ct2/` (D6); the host-repo cleanliness contract is not weakened.
- **No lens consumption of lessons or any forge-authored context.** Reviewer independence outranks memory reach.
- **No reconciler push-notifications for routine outcomes.** The planner pulls (D, §5.2); escalation remains the only reconciler→helm push.

---

## 11. Relationship to the Document Set

- **Extends** `docs/ct2-dynamic-workflow-strategy-2026-06.md`: that document fixes CT2's position (verification kernel above native workflows) and its §10 next-tickets address the workflow boundary; this document fills the kernel's *signal* whitespace — what the gates actually check. No position taken there is revisited here.
- **Inherits** the Verified Autonomy OS balanced scorecard unchanged except one Evidence-axis input (§6) and respects the `.ct2/postmortems/` reservation (`docs/ct2-verified-autonomy-os-strategy-2026-05.md:316`).
- **Constrained by** the Protocol Reframe: "Agent Owns the Loop" shaped every loop decision here (one-shot tools, agent-driven iteration, pull-based goal feedback); the subtraction discipline is addressed honestly in §8.6.
- **External evidence** is dated 2026-06: the Lance Martin article is treated as corroborating analysis, not authority — where it and CT2's adversarial verification disagreed (e.g., evidence-claim-citing as "verification"), CT2's verification won.

---

## 12. One-Paragraph Summary for the Maintainer

The article confirms CT2's bet — independent, structurally separated verification — and exposes what CT2 has not yet built: the machine-checkable signals that verification should run on. This roadmap closes that gap in dependency order. Phase 0 lands four small, independent fixes this week (a hard submit gate that ends the spec/implementation divergence, escalation messages that carry *why*, a documented metric, a dangling writer). Phase 1 makes completion executable: helm binds ACs to commands in a sealed `## Verification` section, forge iterates against `ct2-ac-verify` until green before requesting expensive LLM review, and the reconciler refuses `done/` without round-fresh evidence — gates phased advisory→hard by release, never by tamperable config. Phase 2 makes the review signal structured: per-AC pass/fail lines with exactly one hard coherence rule, and rework re-entry gated on per-issue resolution accounting in plan evidence. Phase 3 builds memory consult-first — lessons captured at failure boundaries with categorical keys, auto-corroborated on recurrence (never overclaimed as "verified"), injected un-skippably into forge's pickup stdout, distilled into draft-time planning lints. Phase 4 closes the outer loop with a provider-neutral `ct2-goal` that subsumes `ct2-codex-goal`, where the planner pulls each terminal ticket's structured outcome before drafting the next. Two designs are explicitly dead — reader-less lesson ledgers and statistics-over-n=2 planning digests — and their kill reasons are this document's design constraints.
