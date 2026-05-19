---
type: spec
title: "CT2 - Decision Bridge"
version: "0.1.0"
---

# CT2 Decision Bridge

The Decision Bridge maps runtime-specific user questions, approvals, and policy
exceptions into a provider-neutral `.ct2/decisions/` schema.

## Layout

```
.ct2/decisions/
├── pending/
├── answered/
├── expired/
└── audit/
```

## Record Schema

Decision records include id, status, provider, role, ticket, question, bounded
options, timestamps, and final choice when answered.

## Provider Formats

`ct2-decision format` renders a pending or audited decision into the provider
surface expected by the runtime:

- Codex: `item/tool/requestUserInput` payload with one bounded `questions`
  entry.
- Claude Code: `AskUserQuestion` payload with question, options, and metadata.
- HTML: a self-contained `canvas.html` render of the record, used by the helm
  planning canvas (see `spec/helm-canvas.md`).

A provider format is a render of the same `.ct2/decisions/` record; it is not a
second source of truth. "Provider format" is distinct from a CT2 *adapter*
(`spec/adapter-format.md`), which is a runtime-and-role markdown contract.

A canvas record carries a single-use `nonce`. The helm canvas returns its
answer through `ct2-helm-canvas recover`, which validates the `nonce` against
the pending record before writing `answered/`.

## Rules

- Lens roles cannot use decisions to waive review criteria.
- Hooks are defense-in-depth; scripts still enforce invariants when hooks are
  missing.
- Decision state moves by atomic same-filesystem rename or equivalent
  tmpfile-then-replace.

## Policy Compiler

`ct2-policy-compile` emits provider hook declarations and shell validator
metadata under `.ct2/runtime/provider-hooks/`. The generated files are an
operational mirror of the hook package, not a substitute for script-level
validation.
