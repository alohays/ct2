---
type: spec
title: "CT2 Adapter Format"
version: "0.1.0"
---

# CT2 Adapter Format

Adapters describe how an agent runtime participates in CT2 without changing
the protocol. The canonical adapter is markdown.

## Path

```
adapters/{agent}/{role}.md
```

Required lens roles:

- `adapters/claude/lens-cc.md`
- `adapters/claude/lens-cx.md`
- `adapters/codex/lens-cc.md`
- `adapters/codex/lens-cx.md`

## Required Sections

Each adapter must include:

```markdown
---
agent: codex
role: lens-cx
protocol: "0.1.0"
---

## Invocation
## Objective
## Required CT2 Effects
## Stop Condition
```

`Invocation` documents the host-agent command shape or native goal primitive.
`Objective` states the role task. `Required CT2 Effects` lists the files and
commands the agent must produce. `Stop Condition` states when the native loop
may finish.

## Prompt Discipline

Adapters describe invariants and outputs. They must not prescribe the
implementation approach for the project under review.

Hard caps for lens adapters:

- Invariant header: 500 characters or fewer.
- Role context: 1,500 characters or fewer.

The reference verifier treats these caps as guardrails rather than markdown
rendering rules: it checks for concise required sections and fails obviously
bloated adapters.

## Optional Executables

An adapter may include a sibling `run.sh`, but markdown is authoritative. The
reference dispatchers read markdown adapters and invoke the selected runtime.
