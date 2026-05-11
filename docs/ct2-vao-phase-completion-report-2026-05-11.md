# CT2 VAO Phase Completion Pilot Report

Date: 2026-05-11T13:34:11Z
Run ID: `vao-pilot-20260511T133411Z-b2f6f3e9`

## Result

Overall complete: `true`

| Phase / Requirement | Status |
|---|---|
| phase0_registry_baseline | complete |
| bet1_cost_telemetry | complete |
| bet2_plan_first_pilot | complete |
| bet4_role_eval_regression_harness | complete |
| bet3_advisory_bridge_pilot | complete |
| bet5_native_mirror_spike | complete |
| week6_scorecard_report | complete |
| decision_bridge_provider_adapters | complete |
| evidence_graph_extended_kinds | complete |

## Evidence

- Runtime capabilities: `.ct2/runtime/capabilities.json`
- Baseline: `.ct2/telemetry/baseline-2026-05.json`
- Cost events: `10`
- Done-ticket baseline sample: `20`
- Plan-audited tickets: `25`
- Role eval cases: `5`
- Advisory notifications: `10`
- Ticket state unchanged by bridge: `true`
- Evidence kinds: `artifact, hook_event, screenshot, verifier`

## Command Results

- `ct2-init --repair`: returncode `0`
- `ct2-role-run ct2-forge`: returncode `0`
- `ct2-role-run ct2-lens-cc`: returncode `0`
- `ct2-role-run ct2-lens-cx`: returncode `0`
- `ct2-role-run ct2-helm`: returncode `0`
- `ct2-role-run ct2-forge`: returncode `0`
- `ct2-runtime-doctor`: returncode `0`
- `ct2-policy-compile`: returncode `0`
- `ct2-evidence screenshot`: returncode `0`
- `ct2-evidence verifier`: returncode `0`
- `ct2-evidence hook-event`: returncode `0`
- `ct2-bridge notify 1`: returncode `0`
- `ct2-bridge notify 2`: returncode `0`
- `ct2-bridge notify 3`: returncode `0`
- `ct2-bridge notify 4`: returncode `0`
- `ct2-bridge notify 5`: returncode `0`
- `ct2-decision ask claude`: returncode `0`
- `ct2-decision format claude`: returncode `0`
- `ct2-decision format codex`: returncode `0`
- `ct2-decision answer`: returncode `0`
- `ct2-role-eval`: returncode `0`
- `ct2-role-eval intentional regression`: returncode `1`
- `ct2-plan-audit`: returncode `0`
- `ct2-cost`: returncode `0`
- `ct2-baseline`: returncode `0`
