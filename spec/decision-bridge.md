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

The provider format is an adapter view over the same `.ct2/decisions/` record;
it is not a second source of truth.

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
