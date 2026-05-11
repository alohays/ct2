---
type: spec
title: "CT2 - Runtime Capabilities"
version: "0.1.0"
---

# CT2 Runtime Capabilities

The Capability Registry records local runtime facts without granting runtimes
authority over CT2 state. Codex, Claude Code, tmux, git, MCP servers, app-server
schema, and feature flags are device-driver inputs behind the `.ct2/` protocol
kernel.

## Capability Registry

`ct2-runtime-doctor` writes:

- `.ct2/runtime/capabilities.json`
- `.ct2/runtime/degradations.md`
- optional runtime artifacts under `.ct2/runtime/artifacts/`

The report must include schema version, check timestamp, minimum supported
versions, available runtimes, feature flags when locally observable, and
degradation notes.

## Rules

- Probing must not move tickets or write review sidecars.
- Basic local probing must not require network access.
- Under-development vendor features are never silently used for core state
  transitions.
- Runtime state is advisory; `.ct2/{draft,backlog,in-progress,in-review,
  rejected,escalated,done}/` remains authoritative.

## Status Surface

`ct2-status --doctor` renders a one-screen summary of
`.ct2/runtime/capabilities.json`, including Codex and Claude availability and
degraded paths.
