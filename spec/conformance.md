---
type: spec
title: "CT2 Conformance"
version: "0.1.0"
---

# CT2 Conformance

An implementation conforms to CT2 protocol `0.1.0` when it satisfies the
required filesystem layout, state transition rules, sidecar contract,
reconciler behavior, and adapter format.

## Conforming Lens Reviewer

A lens reviewer conforms when it:

1. Writes exactly one own-side sidecar per ticket round.
2. Does not read the partner sidecar before its own sidecar exists.
3. Uses the path `.ct2/reviews/{id}-{cc|cx}-r{round}.md`.
4. Emits required sidecar frontmatter and body sections.
5. Calls `ct2-reconcile {id} {round}` after writing its sidecar when the
   partner sidecar exists, or leaves discovery mode able to complete it.
6. Never edits source files, tickets, or partner sidecars during review.

## Conforming Reconciler

The reconciler conforms when the black-box fixture suite proves:

- Missing partner sidecar does not move a ticket.
- Dual approvals move a ticket to `done/`.
- One rejection moves a ticket to `rejected/` while rounds remain.
- One rejection moves a ticket to `escalated/` when the round cap is reached.
- Concurrent invocations produce exactly one terminal move.
- Stale locks are recovered.
- Malformed sidecar verdicts do not move tickets.

## Conforming Adapter

An adapter conforms when it follows `spec/adapter-format.md`, declares the CT2
protocol version, identifies the agent and role, and gives the runtime a clear
objective and stop condition without project-specific implementation advice.

## Native-Workflow Re-Entry Contract

A native runtime workflow (for example a Claude Code dynamic workflow, or any
future vendor orchestration analog) is an ephemeral executor. Its output counts
in CT2 only after it re-enters the protocol through this contract. The contract
names no vendor; the same rules apply unchanged to every orchestration runtime.
A native workflow never holds terminal authority over CT2 state.

A CT2-wrapped workflow run conforms when it satisfies every numbered rule:

1. **Named ticket.** The run MUST name an existing CT2 ticket at launch.
   Output from a run that names no ticket is advisory evidence only and
   MUST NOT move ticket state.
2. **Isolated write target.** Workflow edits MUST land only in a per-run
   isolated branch. The worktree form of this rule (`.ct2/worktrees/`,
   per-run worktree isolation) is gated on Phase-1.5 worktree support, which
   is unimplemented today (see `spec/directory-structure.md`); until worktrees
   ship, the equivalent guard is forge's branch-per-ticket plus the single
   `in-progress/` slot.
3. **Single recognized return channel.** Output MUST re-enter CT2 through
   exactly one of: a patch, a PR, an inbox message, or an evidence artifact
   (a `claims.jsonl` row). Output MUST NOT re-enter by mutating ticket state
   directly.
4. **Non-role-holding subagents.** A workflow subagent MUST NOT write
   `.ct2/.meta/ct2-active-role`, MUST NOT claim the `in-progress/` slot, and
   MUST NOT hold ticket authority.
5. **Parent-owns-writes.** Only the parent role MAY perform authoritative CT2
   state writes (seal, sidecar, reconcile, ticket `mv`).

On the kernel side, three rules are unchanged by any workflow run:

6. A workflow's self-verification is evidence, not a verdict.
7. Independent dual review (`lens-cc` AND `lens-cx`, cross-vendor) stays
   terminal authority; either reviewer rejecting means rejected.
8. The reconciler is the sole automatic mover to `done/`.

An adapter that wraps or invokes a native workflow documents this contract
following `spec/adapter-format.md`.

## Prompt-Construction Independence

The lens no-peek rule (Conforming Lens Reviewer, rule 2) constrains
independence at file-read time. That is a session-era mechanism: it assumes a
reviewer can only see a sibling's conclusion by reading a file. In the
fan-out era a parent orchestrator script holds every child subagent's return
value, so it can leak one reviewer's conclusion into another reviewer's
prompt without any file read occurring. Independence must therefore also be
constrained at prompt-construction time:

1. A verifier subagent's prompt MUST NOT contain any sibling reviewer's
   output — not the verdict, not the sidecar text, not the findings.
2. A verifier prompt MAY contain the work product under review (ticket text,
   the diff or patch, worker-subagent output). The boundary is what a
   sibling reviewer concluded, not what the work produced.
3. The rule is vendor-neutral and applies to in-workflow verifier subagents
   and to lens reviewers alike. For lens reviewers it extends — it does not
   replace — the file-read no-peek rule.

CT2 cannot mechanically block a non-conforming orchestration script (the
script is opaque to the protocol). The rule is conformance-tested after the
fact through the workflow-run manifest below.

## Vendor Symmetry

CT2 is a protocol that leverages Claude and Codex as co-equal runtimes, not a
wrapper around either. Reviewers that share one model family share that
family's blind spots; only a different model family evaluating neutralizes
self-preferential bias, which is why dual review is cross-vendor by
construction and not "any two reviewers". Three rules keep the protocol
vendor-symmetric:

1. **The re-entry contract is vendor-neutral by construction.** The
   Native-Workflow Re-Entry Contract above names no vendor and MUST resolve
   identically for any conforming runtime orchestration surface, present or
   future. If a future revision of the contract needs a vendor name to work,
   the philosophy has been violated and that revision is non-conforming.
2. **The quorum floor is cross-vendor 2, not any-2.** The immovable floor for
   `done/` is `lens-cc` (Claude) AND `lens-cx` (Codex). Extra same-vendor
   skeptics are advisory: they MAY inform a verdict but MUST NOT override the
   cross-vendor disagreement rule. A same-vendor majority never outvotes a
   single cross-vendor rejection — "either reviewer rejects means rejected"
   dominates every configuration. The normative quorum rules (anchors,
   skeptics, binding set, promotion) live in `spec/reconciler.md`
   ("Review Quorum (M-of-N)"); this section is their conformance surface.
3. **`lens-cx` is first-class at parity with `lens-cc`.** The Codex side is
   maintained at feature parity with the Claude side across adapters
   (`adapters/claude/`, `adapters/codex/` each carry both lens variants),
   plugin skills (`claude-plugin/skills/`, `codex-plugin/skills/` each retain
   their lens role), the runtime doctor (both runtimes probed; both lens
   degradations reported), and role config (`config/ct2-lens-cc-role.md`,
   `config/ct2-lens-cx-role.md`). A change that removes or degrades a
   `lens-cx` surface without an equivalent `lens-cc` change is Claude-primary
   drift and fails conformance.

The one-line litmus: if you can delete every Codex reference from CT2 and the
protocol still makes sense, CT2 has become a single-vendor harness and lost
its moat. The conformance suite operationalizes this litmus and rule 3 as the
Claude-primary drift checks in `tests/test_conformance.py`, and rules 1–2 as
the quorum violation codes of the workflow-run manifest below.

## Workflow-Run Manifest

A workflow-run record is one JSON document, parseable with the Python stdlib
`json` module, describing a finished CT2-wrapped workflow run so the
conformance suite can validate the re-entry contract and the
prompt-construction independence invariant. It is declarative evidence about
a run, never a control surface: a manifest MUST NOT move ticket state.

Top-level fields:

- `manifest` (string, required): format identifier; this revision is
  `ct2-workflow-run/v1`.
- `ticket` (string, required): the CT2 ticket id the run was launched for.
  A missing or empty value makes the run non-conforming (re-entry rule 1).
- `subagents` (array, required, may be empty): one record per spawned
  subagent.
- `quorum` (object, optional): the review quorum the run was launched under,
  declared in the terms of `spec/reconciler.md` ("Review Quorum (M-of-N)").
  Absence means the protocol default — the cross-vendor 2-of-2 anchors
  (`cc` AND `cx`) — which always conforms. Like the rest of the manifest,
  a `quorum` declaration is evidence about a run, never a control surface.

Each `subagents` record:

- `id` (string, required): identifier unique within the run.
- `kind` (string, required): `worker` or `verifier`.
- `prompt` (string, required): the exact prompt the parent orchestrator
  composed for this subagent.
- `output` (string, optional): the text the subagent returned to the parent
  (for a verifier: its verdict and findings).
- `writes` (array of strings, optional): repo-relative paths the subagent
  wrote.

A `quorum` object:

- `binding` (array, required): one record per binding reviewer. Each record
  has `key` (string; the sidecar key — `cc` and `cx` are the anchors) and
  `vendor` (string; for example `claude` or `codex`).
- `advisory` (array, optional): advisory skeptics, same record shape.
  Advisory reviewers never affect the verdict.
- `rejection_rule` (string, optional): MUST be `any-binding-rejects` when
  present; that value is also the default when absent. Rejection is a
  disjunction over the binding set, never a vote.

A manifest fails conformance when any of the following holds, each reported
as a stable violation code:

1. `missing-ticket` — `ticket` is absent, not a string, or empty.
2. `sibling-output-in-verifier-prompt` — a verifier record's `prompt`
   contains the non-empty `output` of any other verifier record.
3. `subagent-wrote-active-role` — any record's `writes` contains a path
   whose final component is `ct2-active-role` (the canonical path is
   `.ct2/.meta/ct2-active-role`; re-entry rule 4).
4. `quorum-single-vendor-satisfiable` — the declared binding set omits
   either anchor key (`cc`, `cx`) or spans fewer than two distinct non-empty
   `vendor` values. Such a configuration is satisfiable by a single vendor
   and breaks the cross-vendor floor (Vendor Symmetry rule 2). A missing or
   empty `vendor` fails closed: a reviewer whose vendor cannot be determined
   never counts toward cross-vendor coverage.
5. `quorum-overrides-cross-vendor-rejection` — the quorum declares a
   `rejection_rule` other than `any-binding-rejects`, or declares any
   `threshold`. Vote or threshold semantics is exactly the mechanism that
   would let a same-vendor majority outvote a single cross-vendor rejection
   (`spec/reconciler.md`, Verdict Rule Under A Quorum).

The reference validator and fixture manifests live in the conformance suite
(`tests/test_conformance.py`, `tests/fixtures/`).

## Reference Verification

The reference repository provides:

```bash
ct2-verify [project-dir]
python3 -m unittest discover -s tests
```

`ct2-verify` is a local verifier for packaging and adapter sanity. The unittest
suite is the authoritative reference-implementation regression suite.
