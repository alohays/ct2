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

Both fields are append-compatible. Records that omit them remain fully valid,
readers never require them, and no migration exists: the read path is
byte-compatible with pre-edge ledgers. The evidence DAG lives implicitly in
the flat `claims.jsonl` records via these optional edges; the Evidence Graph
is explicitly not a graph engine. When a fan-out produces findings, each
finding's `produced_by_agent` labels the subagent while `parent_id` and the
record's `ticket` attribute it to the orchestrating role and ticket.

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
  claims.
