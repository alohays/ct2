---
type: spec
title: "CT2 - Role Contracts"
version: "0.1.0"
---

# CT2 Role Contracts

Role contracts make runtime choices explicit before CT2 adds any automatic
router. Contracts are static defaults, not a self-optimizing policy.

## Contract Fields

Each role contract in `config/harness.yaml` may define:

- `model`
- `reasoning_effort`
- `max_latency_sec`
- `budget_usd`
- `personality`

The required roles are `ct2-helm`, `ct2-forge`, `ct2-lens-cc`,
`ct2-lens-cx`, and `ct2-helm-auto-cx`.

## Execution

`ct2-role-run` records role, command entrypoint, exit code, duration, tokens, and
cost to `.ct2/telemetry/cost.jsonl`. It must not store prompt text, tool
payloads, secrets, or full model transcripts by default.

## Orchestrate-By-Default Runtimes

When `ct2-helm` or `ct2-forge` runs under an orchestrate-by-default runtime
(for example ultracode), native fan-out is sanctioned for exactly two uses:

- Read-only discovery and analysis, for any role.
- Forge implementation, inside the isolated branch required by the
  native-workflow re-entry contract (`spec/conformance.md`).

CT2 state writes (seal, sidecar, reconcile, ticket `mv`) remain parent-owned
one-shot operations. Fan-out subagents are non-role-holding workers: they
never write `.ct2/.meta/ct2-active-role`, never claim the `in-progress/`
slot, and never hold ticket authority.

## Rules

- Static contracts first; no automatic LLM router.
- Contract degradation must be visible in status or telemetry.
- Eval budget is separate from ticket budget.
