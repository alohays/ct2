# CT2 Workflow Templates

Optional, content-tier reference material for users who run native dynamic
workflows against CT2 tickets. **CT2 core never depends on this directory.**
No `bin/` tool, spec rule, hook, or test reads anything here; deleting
`templates/workflows/` changes nothing about the CT2 protocol. Emitting a
vendor-locked workflow script as core is an explicit non-goal
(`docs/ct2-dynamic-workflow-strategy-2026-06.md` §8); a blessed *template* is
the sanctioned alternative.

## What `ct2-adversarial-verify.workflow.js` Is

A reference Claude Code dynamic-workflow script (research preview,
`v2.1.154+`) that runs an adversarial self-verification pass over one CT2
ticket artifact: parallel skeptic subagents, a fail-soft cross-vendor pass
through the Codex CLI, and re-entry of all findings into CT2 as evidence plus
an advisory inbox message.

Its output is **evidence, never a verdict**. Whatever the workflow concludes,
the ticket still requires independent cross-vendor dual review (lens-cc AND
lens-cx sidecars; either reviewer rejecting means rejected), and only
`ct2-reconcile` moves a ticket to `done/`. The script returns
`sufficientForCt2DualReview: false` unconditionally.

To use it, copy the script into your project's `.claude/workflows/` directory
and launch it with a ticket id and an artifact path or git ref:

```text
args: { ticket: "042-fix-reconciler-lock", artifact: "src/reconciler.py", round: "1" }
```

## Independence Wiring, By Construction

The template exists because a workflow orchestrator script holds every
subagent's return value, so the session-era no-peek rule (do not read the
partner sidecar) no longer constrains prompt construction: a careless script
can inject one reviewer's output into another reviewer's prompt. The template
makes that leak structurally impossible rather than merely discouraged:

- **One prompt builder, sealed signature.** `buildVerifierPrompt(artifactText,
  ticketText, lens)` is the only function that produces a verifier prompt. Its
  inputs are the artifact under review, the ticket text, and a lens row from a
  static literal table — there is no parameter through which a sibling
  verifier's findings or any other subagent return value can flow in.
- **Lenses are static literals.** Skeptic charges live in a constant table.
  Adding a skeptic means adding a row, never adding a prompt input.
- **Sibling results exist only downstream.** Every verifier prompt is fully
  constructed before `parallel()` returns any result to the orchestrator.
  Results meet for the first time in the synthesis step, where they merge into
  evidence; nothing flows back into a verifier.
- **The cross-vendor prompt is built by the same function.** The Codex pass
  receives a `buildVerifierPrompt` output verbatim, so it is exactly as
  isolated from siblings as every Claude-side skeptic.

## Cross-Vendor Advisory Pass (Fail-Soft)

A Bash-running subagent delivers the lens-cx-equivalent prompt to the Codex
CLI in a read-only sandbox (`codex exec --sandbox read-only -`, prompt on
stdin). If `codex` is not on `PATH`, the runner does not improvise a
substitute: it reports the pass as `not-run`, the script logs the absence, and
the run is explicitly marked **NON-SUFFICIENT for CT2 dual review (advisory
only)** in the evidence record, the inbox message, and the return value.

Even when the pass runs, it is advisory cross-vendor *evidence* — it is not a
lens-cx sidecar and never substitutes for one. The authoritative cross-vendor
check happens at review time, outside any workflow.

## Re-Entry Contract Compliance Checklist

The re-entry contract (`docs/ct2-dynamic-workflow-strategy-2026-06.md` §3.3)
is what makes a workflow's output count in CT2. Use this checklist for any
workflow you author; the right column shows where this template satisfies each
clause.

| Clause | Requirement | Where this template satisfies it |
|---|---|---|
| Named ticket | The run is launched for a specific ticket id; unattributed output is advisory noise that can never move state. | `args.ticket` is required; the run throws without it, and every evidence record and inbox message carries the ticket id. |
| Isolated writes | Workflow edits land only in an isolated write target, never on the working/target branch (worktree clause gated on Phase 1.5+; today the guard is forge's branch-per-ticket plus the single in-progress slot). | Satisfied by writing nothing: every verifier and the ingest step are read-only, so there are no edits to isolate. A workflow that *does* edit must route edits per this clause. |
| Return channels | Output re-enters as exactly one of patch, PR, inbox message, or evidence artifact — never by mutating ticket state. | Findings re-enter via `bin/ct2-evidence verifier` (a `claims.jsonl` row) and `bin/ct2-bridge notify` (an advisory inbox message). The script contains no ticket `mv` and no state write. |
| Non-role-holding subagents | No subagent writes `ct2-active-role`, claims the in-progress slot, or holds ticket authority. | All subagents are read-only except the re-entry writer; its prompt restates the forbidden list (no ticket moves, no `ct2-active-role`, no in-progress claim, no reconciler/seal/revise calls). |
| Parent-owns-writes | Only one designated writer performs the CT2 write; fan-out workers never write CT2 state. | Exactly one re-entry subagent writes, serially, at the end of the run, and only through the two sanctioned return channels above. |

The kernel-side clauses need no checklist because no workflow can satisfy or
waive them: dual review (cc AND cx) stays terminal authority, a workflow's
self-verification is evidence rather than a verdict, and the reconciler is the
sole automatic mover into terminal states. `spec/` remains authoritative for
all conformance rules.

## Determinism Notes

Dynamic workflows disable the nondeterministic time and random builtins and
require `meta` to be a pure literal in plain JavaScript. The template
therefore derives its run identifier from stable inputs only — ticket id +
FNV-1a content hash + round counter — and takes the round via `args` instead
of reading clocks. Keep CT2's time-based breakers (`ct2-duration-check`,
`ct2-review-watchdog`) outside workflow scope; they are host-session tools.

## What This Directory Is Not

- Not protocol surface: no spec rule references it, and conformance does not
  require it.
- Not a reviewer: it cannot approve, reject, or move tickets, and its output
  must never be cited as a verdict.
- Not vendor-neutral core: the script targets one vendor's experimental
  workflow format. The re-entry contract it implements names no vendor; when
  another runtime ships an orchestration analog, the same contract applies and
  a sibling template can live here beside this one.
