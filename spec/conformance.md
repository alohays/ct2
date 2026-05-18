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

## Reference Verification

The reference repository provides:

```bash
ct2-verify [project-dir]
python3 -m unittest discover -s tests
```

`ct2-verify` is a local verifier for packaging and adapter sanity. The unittest
suite is the authoritative reference-implementation regression suite.
