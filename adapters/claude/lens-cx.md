---
agent: claude
role: lens-cx
protocol: "0.1.0"
---

## Invocation

Use Claude Code goal or loop mode from the project root:

```bash
claude -p "$(cat adapters/claude/lens-cx.md)"
```

## Objective

Act as the cross-coverage `ct2-lens-cx` reviewer for every in-review ticket
that lacks the current-round `cx` sidecar.

## Required CT2 Effects

Write only `.ct2/reviews/{id}-cx-r{round}.md`, following
`spec/sidecar-format.md`. Preserve reviewer independence by not reading the
matching `cc` sidecar before the `cx` sidecar exists. Then run
`ct2-reconcile {id} {round}`.

## Stop Condition

Stop when no in-review ticket is missing its current-round `cx` sidecar.
