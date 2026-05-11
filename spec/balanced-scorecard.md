---
type: spec
title: "CT2 - Balanced Scorecard"
version: "0.1.0"
---

# CT2 Balanced Scorecard

CT2 does not use a single north-star metric. The Balanced Scorecard tracks four
axes that must remain healthy together: Trust, Evidence, Autonomy, and
Cost/Latency.

## Metrics

| Axis | Definition | Target |
|------|------------|--------|
| Trust | Done tickets with dual approved sidecars divided by done tickets | `trust_ratio_min` |
| Evidence | Done tickets with stable evidence claims and verifier records | `evidence_coverage_min` |
| Autonomy | Review and blocked/unblocked latency from local telemetry | `lens_latency_p95_sec` |
| Cost/Latency | Role-run cost, token, duration, and ticket latency summaries | sprint baseline |

## Baseline Rules

`ct2-baseline` writes `.ct2/telemetry/baseline-2026-05.json`. If sample sizes
are below the configured minimums, the metric status is `measurement_started`
instead of an over-claimed measurement.

## Status Surface

`ct2-status` renders the latest scorecard when a baseline file exists. Passing
tests, a completed manifest, or a green verifier is not sufficient by itself;
the scorecard is evidence only when the measured inputs cover the objective.
