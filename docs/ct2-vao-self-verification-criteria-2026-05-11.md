# CT2 VAO Self-Verification Criteria

Date: 2026-05-11
Scope: `docs/ct2-verified-autonomy-os-strategy-2026-05.md` implementation

This document defines the standard for judging whether the VAO implementation
was actually completed. A green test suite is required but not sufficient.

## Completion Standard

The work is complete only if all P0 gates pass and no checklist item is marked
unknown. If evidence is missing, the correct status is incomplete, even when the
implementation looks plausible.

## P0 Gates

| Gate | Metric | Pass threshold | Measurement |
|---|---:|---:|---|
| Artifact coverage | Required strategy artifacts present / required artifacts | 100% | `docs/ct2-vao-completion-audit-2026-05-11.md` checklist plus file existence |
| Test coverage | Required regression/syntax checks passing | 100% pass | `python3 -m unittest discover -s tests`, inline `compile()` with `PYTHONDONTWRITEBYTECODE=1`, `bash -n`, JSON parse, `git diff --check` |
| Spec coverage | New behavior with matching spec or existing spec update | 100% | `spec/runtime-capabilities.md`, `balanced-scorecard.md`, `role-contracts.md`, `plan-evidence.md`, `role-evals.md`, `decision-bridge.md`, `evidence-graph.md`, `external-channels.md`, `runtime-mirror.md`, `directory-structure.md` |
| User/operator documentation coverage | New user-facing commands documented in README | 100% | Command list in `README.md` contains every new `ct2-*` command |
| Safety invariant coverage | Advisory/evidence planes cannot replace ticket state authority | 100% | Specs, tests, and bridge negative case |
| Measurement honesty | Insufficient empirical samples marked as measurement, not success | 100% | `ct2-baseline` emits `measurement_started` below thresholds |

## Documentation Checklist

Every new implemented surface must have:

| Surface | Required docs | Evidence |
|---|---|---|
| CLI command | README command row; test or audit row | `README.md`, `tests/test_vao_strategy.py`, completion audit |
| Runtime directory | `spec/directory-structure.md` entry; authority rule | `spec/directory-structure.md` |
| Behavior contract | Dedicated spec or updated existing spec | `spec/*.md` |
| Operator workflow | Report or README entry explaining when to run it | readiness report and README |
| Safety boundary | Statement of what the feature must not do | specs plus tests |
| Verification method | Concrete command/test/check | completion audit and test suite |
| Full phase audit | Explicit distinction between static implementation completion and real pilot completion | `docs/ct2-verified-autonomy-os-full-phase-audit-2026-05-11.md` |
| Full implementation self-review | Strict multi-layer review gates, metrics, and hard fail conditions | `docs/ct2-vao-full-implementation-self-review-criteria-2026-05-11.md` |

## VAO Command Documentation Coverage

The following commands must remain documented in `README.md` and covered by
tests or audit evidence:

- `ct2-runtime-doctor`
- `ct2-baseline`
- `ct2-role-run`
- `ct2-cost`
- `ct2-evidence`
- `ct2-decision`
- `ct2-policy-compile`
- `ct2-bridge`
- `ct2-plan-audit`
- `ct2-role-eval`
- `ct2-vao-pilot`
- `ct2-vao-self-verify`

Documentation coverage score:

```text
documented_commands / implemented_user_facing_commands
```

Pass threshold: `1.0`.

## Metric Interpretation

Some VAO scorecard metrics require real project history. Those are not allowed
to pass by synthetic fixture alone.

| Metric | Synthetic test proves | Real project data needed for |
|---|---|---|
| Trust ratio | Calculation and insufficient-sample status work | Claiming target `>= 0.92` |
| Evidence coverage | Evidence claims are counted and surfaced | Claiming target `>= 0.90` |
| Cost/latency | Telemetry sink and summarizer work | Claiming cost reduction |
| Advisory bridge | Notify-only and no ticket mutation | Product pilot success |
| Plan-first flow | Plan audit catches missing plans | First-pass approval improvement |
| Role evals | Fixed cases and intentional regression detection work | Long-running prompt quality trend |

## Current Evidence Snapshot

Latest verified result:

- `python3 -m unittest discover -s tests` passed 29 tests.
- Python compile, bash syntax, JSON parse, and `git diff --check` passed.
- Completion audit maps each strategy requirement to a concrete artifact.
- `ct2-vao-self-verify --run-checks --json` reports all P0 gates complete.
- `docs/ct2-vao-self-verification-report-2026-05-11.md` records the executed
  gate scores and the traceability gap fixed during verification.
- `docs/ct2-verified-autonomy-os-full-phase-audit-2026-05-11.md` records full
  phase status after the local pilot evidence is generated.
- `docs/ct2-vao-full-implementation-self-review-criteria-2026-05-11.md`
  defines stricter layered self-review gates and hard fail conditions.

Current caveat: production scorecard targets are not claimed from synthetic
fixtures. Local pilot completion is valid for phase-exit mechanics only;
production claims still require production ticket history.
