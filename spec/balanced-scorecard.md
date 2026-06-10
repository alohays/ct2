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
| Cost/Latency | Role-run cost, token, duration, and ticket latency summaries, plus advisory fan-out inputs | sprint baseline |

## Cost-Latency Fan-Out Inputs

The Cost/Latency axis accepts two additional inputs so a parallel run is
visible instead of being summed as if it were serial:

- **Per-run agent count** — how many subagents a single orchestrated run
  actually used.
- **Fan-out-vs-serial speedup** — the ratio of summed per-agent work time to
  observed wall-clock time for the same run; a value above 1.0 means the
  fan-out was faster than running the same work serially.

Both inputs are advisory observations. They never gate a verdict and never
move ticket state.

## Token Honesty Rule

CT2 does not meter tokens live and does not enforce token budgets. A budget
directive given to a native workflow is recorded as an advisory fan-out
width, not enforced as a ceiling. The real blast-radius bounds are agent
count, isolation, scope-first slicing, and the existing time and round
circuit breakers.

## Advisory Fan-Out Records

Fan-out observations live under `.ct2/runtime/fanout/` as one JSON file per
run, named `fanout-<ticket>-<compact-utc-timestamp>.json` (for example
`fanout-001-20260610T120000Z.json`). Per `spec/runtime-mirror.md`, records
under `.ct2/runtime/` are an advisory runtime twin: they never become source
of truth and never move terminal states.

The producer is the orchestrating parent role — normally the planner
(`ct2-helm`, including `ct2-helm-auto-cx`). When that role authorizes a
native-workflow fan-out or receives a budget directive, it writes one record
per run with a plain file write or bash heredoc; there is no dedicated bin
tool. Fan-out subagents never write these records, consistent with the
parent-owns-writes rule in `spec/role-contracts.md`.

| Field | Required | Meaning |
|-------|----------|---------|
| `schema_version` | yes | `"1"` |
| `ticket` | yes | Ticket id the run was launched for |
| `fanout_width` | yes | Advisory width the run was authorized to use; a budget directive is recorded here, never enforced |
| `agent_count` | yes | Subagents the run actually used |
| `source_directive` | no | Verbatim directive that suggested the width, or `null` |
| `recorded_at` | yes | UTC timestamp, `YYYY-MM-DDTHH:MM:SSZ` |
| `wall_ms` | no | Observed wall-clock duration of the run |
| `agent_ms_total` | no | Sum of per-agent durations; with `wall_ms`, yields the speedup signal |

`ct2-baseline` folds these records into the Cost/Latency section as a
`fanout` summary and `ct2-cost` surfaces a fan-out summary when records
exist. When no records exist, both outputs are unchanged. Skipping is never
fatal: files that are unreadable, unparseable, or not JSON objects are
skipped; records carrying neither `fanout_width` nor `agent_count`, or
carrying non-numeric values (booleans included) in any of the numeric fields
(`fanout_width`, `agent_count`, `wall_ms`, `agent_ms_total`), are skipped;
individually missing optional fields are tolerated as absent. Both tools
load records through the shared `read_fanout_records` helper in
`bin/_ct2_vao.py`.

The two summaries intentionally expose different aggregates. Both set
`advisory: true` and `runs`:

| Tool | Location | Additional fields |
|------|----------|-------------------|
| `ct2-baseline` | `scorecard.cost_latency.fanout` | `agent_count_p50`, `agent_count_max`, `fanout_width_max`, `speedup_vs_serial_p50` |
| `ct2-cost` | top-level `fanout` | `agent_count_total`, `fanout_width_max` |

## Baseline Rules

`ct2-baseline` writes `.ct2/telemetry/baseline-2026-05.json`. If sample sizes
are below the configured minimums, the metric status is `measurement_started`
instead of an over-claimed measurement.

## Status Surface

`ct2-status` renders the latest scorecard when a baseline file exists. Passing
tests, a completed manifest, or a green verifier is not sufficient by itself;
the scorecard is evidence only when the measured inputs cover the objective.
