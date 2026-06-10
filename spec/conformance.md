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

## Reference Verification

The reference repository provides:

```bash
ct2-verify [project-dir]
python3 -m unittest discover -s tests
```

`ct2-verify` is a local verifier for packaging and adapter sanity. The unittest
suite is the authoritative reference-implementation regression suite.
