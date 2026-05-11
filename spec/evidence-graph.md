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
