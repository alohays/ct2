---
agent: claude
role: lens-cc
protocol: "0.1.0"
---

## Invocation

Use Claude Code goal or loop mode from the project root:

```bash
claude -p "$(cat adapters/claude/lens-cc.md)"
```

## Objective

Review every `.ct2/in-review/*.md` ticket that lacks the current-round
`.ct2/reviews/{id}-cc-r{round}.md` sidecar.

## Required CT2 Effects

Write only the `cc` sidecar, using `spec/sidecar-format.md`. Do not read the
matching `cx` sidecar until the `cc` sidecar exists. After writing the sidecar,
run `ct2-reconcile {id} {round}`.

## Stop Condition

Stop when every current in-review ticket has a matching `cc` sidecar or a
blocking reason has been recorded in a rejecting sidecar.
