# CT2 Native Task Mirror Spike

Date: 2026-05-11
Strategy source: `docs/ct2-verified-autonomy-os-strategy-2026-05.md`

## Question

Can CT2 mirror vendor-native task graphs without allowing the vendor runtime to
become ticket-state authority?

## Feasibility

Feasible as an advisory mirror only.

The mirror can record runtime task ids, external status labels, last observed
timestamps, and source runtime metadata under `.ct2/runtime/` or
`.ct2/watchers/*.json`. It can also emit `.ct2/telemetry/events.jsonl` advisory
events and notify roles through `ct2-bridge notify`.

## Constraints

- Native tasks never move tickets to `done/`, `rejected/`, or `escalated`.
- Native task mismatch is an advisory event until a human or CT2 role inspects
  it.
- CT2 to native sync is allowed for labels and references; native to CT2 state
  mutation is blocked.
- Hook/provider metadata from `ct2-policy-compile` is defense-in-depth only;
  state scripts remain authoritative.

## Spike Result

Do not build a production native task synchronizer in this cycle. The next safe
step is a read-only watcher that writes advisory events and inbox notifications
for stale runtime twin records.
