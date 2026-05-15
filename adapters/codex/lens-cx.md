---
agent: codex
role: lens-cx
protocol: "0.1.0"
---

## Invocation

Use the installed Codex continuation surface. Stable fallback:

```bash
codex exec --sandbox workspace-write - < adapters/codex/lens-cx.md
```

## Objective

Drain Codex review work: for every `.ct2/in-review/*.md` ticket missing the
current-round `cx` sidecar, perform an independent review.

## Required CT2 Effects

Write `.ct2/reviews/{id}-cx-r{round}.md` atomically through `.ct2/.tmp/`.
Never read the matching `cc` sidecar before the `cx` sidecar exists. After the
sidecar exists, run `ct2-reconcile {id} {round}`.

## Stop Condition

Stop only when all current in-review tickets have current-round `cx` sidecars
or have explicit rejecting sidecars explaining why review could not validate.
