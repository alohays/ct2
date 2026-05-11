# CT2 Phase 0 Readiness Report

Date: 2026-05-11
Strategy source: `docs/ct2-verified-autonomy-os-strategy-2026-05.md`

## Scope

Phase 0 establishes the admission layer required before Cost-aware Role
Contracts. It covers runtime capability probing, baseline scorecard collection,
evidence directories, role contract defaults, decision records, and advisory
bridge constraints.

## Implemented Artifacts

| Gate | Artifact |
|---|---|
| Capability registry | `ct2-runtime-doctor`, `.ct2/runtime/capabilities.json`, `.ct2/runtime/degradations.md`, `.ct2/runtime/codex-flags-actual.md` |
| Baseline scorecard | `ct2-baseline`, `.ct2/telemetry/baseline-2026-05.json`, `ct2-status` scorecard rendering |
| Runtime status | `ct2-status --doctor` |
| Cost telemetry | `ct2-role-run`, `ct2-cost`, `.ct2/telemetry/cost.jsonl` |
| Evidence graph seed | `ct2-evidence command`, `.ct2/evidence/claims.jsonl`, `.ct2/evidence/commands/` |
| Decision bridge seed | `ct2-decision`, `.ct2/decisions/{pending,answered,expired,audit}/`, Codex app-server pending decision records |
| Hook guardrail compiler | `ct2-policy-compile`, `.ct2/runtime/provider-hooks/` |
| Advisory bridge | `ct2-bridge notify`, `.ct2/telemetry/events.jsonl` |
| Role contracts | `spec/role-contracts.md`, `config/harness.yaml` `role_contracts` block |
| Plan/eval specs | `spec/plan-evidence.md`, `ct2-plan-audit`, `spec/role-evals.md`, `.ct2/plans/`, `.ct2/evals/*/` |

## Readiness Decision

Bet 1 is ready to start only after a project runs:

```bash
ct2-init --repair
ct2-runtime-doctor
ct2-policy-compile
ct2-baseline
```

If the baseline has fewer than 20 done tickets, metrics must remain marked
`measurement_started`. Bet 1 can still start instrumentation, but product claims
must not report target attainment until the sample threshold is reached.

## Go / No-Go

Go for Bet 1 implementation mechanics: yes.

Go for public trust/cost claims: no until local projects collect sufficient
baseline samples.
