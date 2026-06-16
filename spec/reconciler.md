---
type: spec
title: "CT2 Reconciler"
version: "0.1.0"
---

# CT2 Reconciler

`ct2-reconcile` is the only automatic tool that moves tickets from
`in-review/` to `done/`, `rejected/`, or `escalated/`.

## Forms

```bash
ct2-reconcile {ticket-id} {round}
ct2-reconcile --discover [project-dir]
ct2-reconcile --project-dir {dir} {ticket-id} {round}
```

Explicit mode reconciles one ticket round. Discovery mode scans
`.ct2/reviews/` for `{id}-cc-r{round}.md` and `{id}-cx-r{round}.md` pairs, then
attempts explicit reconciliation for every pair whose ticket is still in
`in-review/`.

## Preconditions

For ticket id `003` and round `1`, the reconciler requires:

- `.ct2/in-review/003-*.md` exists.
- `.ct2/reviews/003-cc-r1.md` exists.
- `.ct2/reviews/003-cx-r1.md` exists.
- Both sidecars have `verdict: approved` or `verdict: rejected`.

If either sidecar is missing, explicit mode exits successfully without a state
change. If a sidecar verdict is malformed, explicit mode exits non-zero without
a state change. The per-sidecar validator (`_ct2_validate_review_sidecar.py`)
also rejects a coherence violation — a `verdict: approved` sidecar that grades an
AC as `fail` (`spec/sidecar-format.md`) — which likewise exits non-zero without a
state change. Because sidecars are immutable, such a pair wedges until a human
acts: inspect the contradictory sidecar, and either re-review the round or
`ct2-revise` the ticket back to `draft/`. `ct2-review-watchdog`'s review-SLA
escalation is the backstop so a wedged pair never strands silently.

## Locking

The reconciler creates `.ct2/.meta/{id}-r{round}-reconcile.lock` with
`O_EXCL`. If the lock exists and is owned by a live process with recent mtime,
the reconciler exits successfully without changing state. If the lock is stale,
it may be removed and reacquired.

The lock is removed after a successful or failed reconciliation attempt by the
process that acquired it.

## Verdict Logic

| Sidecar verdicts | Ticket result |
|---|---|
| `cc=approved` and `cx=approved` | `verdict: approved`, `status: done`, move to `.ct2/done/` |
| either sidecar `rejected`, and `round + 1 < max_review_rounds` | `verdict: rejected`, `status: rejected`, move to `.ct2/rejected/` |
| either sidecar `rejected`, and `round + 1 >= max_review_rounds` | `verdict: escalated`, `status: escalated`, move to `.ct2/escalated/`, send helm escalation |

Single-reviewer approval is never enough for `done/`.

## Escalation Message

When the round cap escalates a ticket, the helm inbox message body carries, for
each current-round sidecar, its path and the verbatim `### [BLOCKING]` heading
lines extracted from that sidecar's `## Issues Found` section. The sidecars are
still live at escalation time, so this copies nothing and creates no new
directory — it makes the escalation carry *why* the ticket failed, not only
"failed after round N". Prior-round sidecars remain in `.ct2/reviews/` until
`ct2-revise` archives them to `.ct2/reviews/.archive/{ts}-{id}/`.

## Done Gate

Dual approval is necessary but no longer sufficient for `done/`. When both
sidecars approve, the reconciler runs `ct2-ticket-audit --done-gate --ticket
{id}` against the ticket **still in `in-review/`**, before any state mutation,
and gates on these named checks (never the audit exit code — the full in-review
audit also fails `required_frontmatter` for legitimate `branch: null` tickets,
which is not a done-readiness condition):

| Check | Pass condition |
|---|---|
| `done_gate_state` | The ticket is in `in-review/`. |
| `acceptance_criteria_checked` | Every `## Acceptance Criteria` checkbox is `[x]`. |
| `sealed_baseline` | The ticket matches its sealed snapshot (no post-seal text drift). |
| `plan_evidence` | This round's plan evidence exists (or a valid `plan-exempt` reason). |
| `dual_approved_sidecars` | Both round-matched sidecars exist, approved, well-formed. |
| `done_gate_evidence` | At least one `ok:true` claim of kind `command`/`verifier` whose `round` equals the ticket's current review-round and whose path exists; when the ticket has sealed `## Verification` bindings, one such round-matched claim for **every** bound AC. |

Freshness is keyed on the claim's `round` field, never a timestamp: forge records
evidence during `in-progress`, before the `.meta/{id}.in-review` stamp exists, so
a timestamp comparison would fail every honest ticket. Round-matching kills
stale-evidence reuse across rework rounds; it does not prevent a fresh `echo ok`
— semantic binding is `ct2-ac-verify`'s job (`spec/ticket-format.md`).

The `done/` invariant therefore strengthens from "dual approval" to "dual
approval AND machine-verified round-fresh evidence", with no change to the `mv`
primitive, writer ownership, or the rule that only reviewer verdicts reject — a
failed gate **withholds** the transition; it never judges.

### Hardness and recovery

The gate ships **advisory** (the `DONE_GATE_HARD` code constant is `false`): on
failure it records the verdict, sends **one** deduplicated helm inbox message per
ticket-round (stamped `.meta/{id}-r{n}.done-gate-failed`, removed when the gate
later passes or the ticket leaves `in-review/`), and still allows the approved
ticket to move to `done/` (exit 0).
A release promotes it to **hard** (withhold the transition, exit 3) per the
gate-hardness policy in `spec/balanced-scorecard.md`, never by runtime config.

Under a hard gate a failing ticket stays in `in-review/`. Recovery is fixing the
deficiency — checking AC boxes (baseline-safe: the sealed baseline normalizes
checkbox marks) and recording the missing round-tagged evidence via
`ct2-ac-verify` / `ct2-evidence` — then re-running `ct2-reconcile {id} {round}`.
A ticket that cannot pass exits through the existing human escape paths
(`ct2-revise`), and `ct2-review-watchdog` escalates an approved-but-unverified
ticket that strands in `in-review/` past `max_review_duration_min` so it never
hangs without an SLA. In `--discover` aggregation, exit 3 ranks above 0 and
below the hard errors (1, 2) and never blocks reconciliation of other pairs.

## Frontmatter Writes

The reconciler updates:

- `status`
- `updated`
- `verdict`
- `review-status.lens-claude.status`
- `review-status.lens-claude.sidecar`
- `review-status.lens-codex.status`
- `review-status.lens-codex.sidecar`

`ct2-revise` is the only non-reconciler tool that resets these review fields.

## Exit Codes

| Code | Meaning |
|---:|---|
| 0 | Reconciled, skipped because incomplete, skipped because already moved, skipped because another live reconciler owns the lock, or moved despite an advisory done-gate failure. |
| 1 | Argument or project error. |
| 2 | Invalid sidecar verdict or ambiguous ticket state. |
| 3 | Approved but the **hard** done gate withheld the transition (approved-but-unverified). No state change. In `--discover`, ranks above 0 and below 1/2; other pairs still reconcile. |

Git finalization is fail-soft: `ct2-git-finalize` failures must not undo a
completed ticket state transition.

## Review Quorum (M-of-N) — Proposed, Not Implemented

> **Status: proposed / not implemented (roadmap W3).** Nothing in this section
> describes current behavior. It is the normative target for the quorum
> generalization in `docs/ct2-dynamic-workflow-strategy-2026-06.md` (gap G4,
> bet B5, open question 9.6, roadmap W3). Until W3 ships, the Verdict Logic
> above is the complete and only reconciler behavior.

### Terms

- **Anchors** — the two cross-vendor reviewers that exist today: `cc`
  (`ct2-lens-cc`, Claude) and `cx` (`ct2-lens-cx`, Codex). Anchors are always
  binding and cannot be removed, replaced, or demoted by any configuration.
- **Skeptics** — up to K extra reviewers registered by opt-in configuration.
  Each skeptic has a sidecar key (never `cc` or `cx`), a declared vendor, and
  a `binding` flag. Skeptics are **advisory by default** (`binding: false`).
- **Binding set** — the anchors plus every skeptic promoted with
  `binding: true`. The binding set always contains both anchors; its minimum
  and default value is exactly `{cc, cx}`.

### Default Behavior Is Frozen

With no quorum configuration present, reconciler behavior is byte-for-byte
identical to the Verdict Logic above: two sidecars, `cc` AND `cx` approval
for `done/`, either rejection for `rejected/` or `escalated/`. The quorum is
strictly opt-in; absence of configuration means absence of the feature, and
the cross-vendor 2-of-2 pair remains the canonical floor in every
configuration that does exist.

### Quorum Configuration (Illustrative)

An opt-in `review_quorum` block in `.ct2/config/harness.yaml` registers
skeptics:

```yaml
review_quorum:
  skeptics:
    - key: sk1                # sidecar key; never cc or cx
      reviewer: ct2-lens-sk1  # role identity validated per sidecar
      vendor: claude          # claude | codex — required, lint target
      binding: false          # advisory by default
```

The exact schema is fixed at W3 implementation time; the rules below are
normative regardless of the final shape.

### Verdict Rule Under A Quorum

The verdict is a conjunction over the binding set, never a vote:

```
verdict = approved  iff  every binding reviewer's verdict = approved
verdict = rejected  iff  any  binding reviewer's verdict = rejected
```

1. **Cross-vendor 2 is the immovable floor.** `cc` AND `cx` approval is a
   necessary condition for `done/` in every configuration. No configuration
   may demote an anchor, substitute a skeptic for an anchor, or make the
   binding set satisfiable by a single vendor.
2. **Either-reviewer-rejects-means-rejected dominates every configuration.**
   Rejection is a disjunction over the binding set. A single `cc` or `cx`
   rejection rejects (or escalates, per the round rules above) regardless of
   how many other reviewers approved. A same-vendor majority — for example
   a panel of promoted same-vendor (Claude) skeptics voting `approved` —
   can never override one `cx` rejection, because approvals and rejections
   are not commensurable votes: there is no threshold under which approvals
   offset a rejection.
3. **M is not configurable.** In CT2's instantiation of "M-of-N", N is
   `2 + K` registered reviewers and M is always the full binding set. CT2
   deliberately rejects free-threshold voting (any-M-of-N); threshold
   semantics is exactly the mechanism that would let a same-vendor majority
   outvote a cross-vendor rejection and re-introduce the self-preferential
   bias the cc/cx pairing exists to remove.
4. **Advisory skeptics never affect the verdict.** An advisory skeptic's
   sidecar is evidence: it may be cited, recorded, and surfaced to helm, but
   the reconciler's verdict computation must produce the same result with
   every advisory sidecar deleted.
5. **Round and escalation rules are unchanged.** `max_review_rounds`,
   escalation, and the helm escalation message apply to the quorum verdict
   exactly as to the 2-of-2 verdict.
6. **The reconciler remains the sole automatic mover.** A quorum changes who
   reviews, never who moves state. No quorum configuration grants any
   reviewer, workflow, or native surface the authority to move a ticket.

### Promotion Rule (Resolves Open Question 9.6)

A skeptic is promoted from advisory to binding only by all of the following,
conservatively:

1. **Explicit static configuration.** Promotion is `binding: true` on the
   registered skeptic in the live config, `.ct2/config/harness.yaml` —
   which is git-excluded, so the mechanism is an explicit human edit to
   the registered skeptic entry, not a config commit. There is no runtime,
   per-ticket, or agent-initiated promotion, and no tool may flip the
   flag.
2. **Full sidecar contract.** A promoted skeptic is held to the same contract
   as the anchors: an immutable sidecar per round, per-reviewer validation,
   and reviewer independence — its prompt contains no sibling reviewer's
   output, and it reads no sibling sidecar before writing its own.
3. **Out-of-band reviewers only.** A quorum reviewer — advisory or binding —
   is a CT2 reviewer session that writes a sidecar through the review path.
   An in-workflow self-verification pass (adversarial-verify, judge-panel)
   is never a quorum member; it re-enters CT2 as evidence only.

Promotion grants rejection authority and adds an approval precondition. It
grants nothing else:

- A promoted skeptic **can add a rejection**: its `rejected` verdict rejects
  the ticket exactly like an anchor rejection.
- A promoted skeptic **can never veto a rejection**: no reviewer's approval —
  anchor or skeptic, in any number — converts another binding reviewer's
  `rejected` into `approved`.
- A promoted skeptic's approval is **necessary but never sufficient**: it
  cannot substitute for either anchor's approval.

### Why Cross-Vendor Disagreement Still Dominates After Promotion

Promotion is monotone toward rejection. Adding a binding skeptic adds one
conjunct to the approval condition and one disjunct to the rejection
condition; it cannot remove either anchor from the conjunction. A quorum can
therefore only make `done/` harder to reach than 2-of-2, never easier, and a
single cross-vendor rejection (`cc` or `cx`) determines the terminal outcome
in every reachable configuration. This is the property the vendor-symmetry
conformance guard must lint for: a configuration that (a) marks an anchor
non-binding, (b) introduces threshold or vote-counting semantics, or
(c) makes the binding set satisfiable by one vendor's reviewers alone is
non-conforming and must be rejected before the reconciler runs.

### Sidecar Preconditions Under A Quorum

| Sidecar | Missing | Malformed verdict |
|---|---|---|
| Anchor (`cc`, `cx`) | Wait; exit 0 without state change (unchanged) | Exit 2 without state change (unchanged) |
| Binding skeptic | Wait; exit 0 without state change | Exit 2 without state change |
| Advisory skeptic | Never blocks; reconciliation proceeds | Warn; ignore for verdict; never exit 2 |

`ct2-review-watchdog` liveness rules extend to binding skeptic sidecars. An
advisory skeptic can never delay reconciliation or trigger escalation.

### Implementation Inventory (Non-Normative, W3)

This is a **moderate multi-file change and explicitly not LOC-neutral**
(strategy gap G4). The 2-of-2 assumption is load-bearing in at least:

- **Sidecar naming scheme** — `.ct2/reviews/{id}-{cc|cx}-r{round}.md`
  (`spec/sidecar-format.md`) reserves exactly two reviewer keys; skeptic keys
  must be added to the path grammar and must never collide with `cc`/`cx`.
- **Discovery regex** — `discover_pairs` in `bin/ct2-reconcile` matches
  `(\d+)-(cc|cx)-r(\d+)\.md` and requires the side set to equal `{cc, cx}`;
  it must generalize so binding skeptics join completeness while advisory
  skeptics never delay discovery.
- **Verdict conjunction** — the two-variable `cc_v`/`cx_v` conjunction in
  `bin/ct2-reconcile` becomes a fold over the binding set.
- **Fixed lens frontmatter keys** — the reconciler writes exactly
  `review-status.lens-claude.*` and `review-status.lens-codex.*` (via
  `_ct2_update_verdict.py`); skeptic entries require an append-compatible
  schema extension.
- **Per-reviewer validator** — `_ct2_validate_review_sidecar.py` checks one
  expected reviewer identity per call; skeptic identities must be derived
  from the quorum configuration and validated per sidecar.
- **Independence hook** — `enforce-review-independence.sh` assumes exactly
  one partner suffix per lens role; with K skeptics every reviewer has N-1
  siblings, and the guard must block reading any sibling sidecar before the
  reviewer's own exists (named in the W3 exit criteria).
- **Tests** — quorum tests must sit beside tests proving the no-config
  default is byte-for-byte unchanged.
