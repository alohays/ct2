---
type: spec
title: "CT2 - Evidence Graph"
version: "0.1.0"
---

# CT2 Evidence Graph

The Evidence Graph gives tickets and sidecars stable evidence ids for commands,
artifacts, verifier output, hook events, and advisory records.

## Layout

```
.ct2/evidence/
├── claims.jsonl
├── commands/
├── screenshots/
├── verifiers/
├── hooks/
└── artifacts/
```

## Claim Model

Each claim has an id, ticket, kind, verifier, ok flag, path, timestamp, and short
summary. Command evidence records live in `.ct2/evidence/commands/`; screenshot,
verifier, hook-event, and artifact records live in their matching subdirectories
and are referenced by `claims.jsonl`.

## Rollup Edges

Claim records support two optional edge fields:

- `parent_id`: the claim or role record this finding rolls up to.
- `produced_by_agent`: a free-form label for the fan-out subagent that
  produced the finding.

Both fields are append-compatible. Records that omit them remain fully valid
and readers never require them: records written without the flags are
byte-identical to the pre-edge format, and the read path is unchanged —
legacy ledgers parse as-is, with no migration. `ct2-evidence` treats an
empty `--parent-id` or `--produced-by-agent` value as absent: the field is
omitted from the record. The evidence DAG lives implicitly in
the flat `claims.jsonl` records via these optional edges; the Evidence Graph
is explicitly not a graph engine. When a fan-out produces findings, each
finding's `produced_by_agent` labels the subagent while `parent_id` and the
record's `ticket` attribute it to the orchestrating role and ticket.

## AC and Round Attribution

Claim records support two further optional fields, written by `ct2-ac-verify`
(and available on `ct2-evidence command|verifier` via `--ac` / `--round`):

- `ac`: the 1-indexed acceptance-criterion ordinal this claim verifies.
- `round`: the review round the evidence belongs to.

Both are append-compatible in exactly the same sense as `parent_id` /
`produced_by_agent`: omitted when empty, byte-identical to the prior format when
absent, and never required by the read path. `ct2-ac-verify` records one
`ok`-flagged claim per bound AC carrying both fields, so a downstream gate can
ask "does this ticket's *current* round carry an `ok:true` claim for every bound
AC?" without parsing summaries or timestamps. The `round` field — not a claim
timestamp — is the staleness key: evidence is fresh for a round iff its `round`
equals the ticket's current `review-round`.

## Evidence Kinds

`ct2-evidence` supports:

- `command`: command string, exit code, and summary.
- `artifact`: external or CT2-generated artifact path.
- `screenshot`: screenshot path or rendered visual evidence path.
- `verifier`: machine verifier name, exit code, and summary.
- `hook-event`: provider hook event name and outcome.

## Rules

- Prompt and tool contents are not stored by default.
- Image-only evidence does not satisfy verifier coverage by itself.
- Every done transition should be traceable to sidecar verdicts and evidence
  claims. The reconciler's done gate makes this enforceable: an approved ticket
  must carry at least one `ok:true` `command`/`verifier` claim whose `round`
  matches its current review-round (and, when it has sealed `## Verification`
  bindings, one per bound AC). This is advisory until the gate is promoted to
  hard, at which point "should be traceable" becomes a gated "must" — see
  `spec/reconciler.md` § *Done Gate*.
