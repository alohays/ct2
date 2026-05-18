---
agent: codex
role: lens-cc
protocol: "0.1.0"
---

## Invocation

Use the installed Codex continuation surface. Stable fallback:

```bash
codex exec --sandbox workspace-write - < adapters/codex/lens-cc.md
```

## Objective

Act as `ct2-lens-cc` using Codex, reviewing every in-review ticket missing the
current-round `cc` sidecar.

## Required CT2 Effects

Write `.ct2/reviews/{id}-cc-r{round}.md` atomically through `.ct2/.tmp/`.
Never read the matching `cx` sidecar before the `cc` sidecar exists. After the
sidecar exists, run `ct2-reconcile {id} {round}`.

## Stop Condition

Stop when no in-review ticket is missing its current-round `cc` sidecar.
