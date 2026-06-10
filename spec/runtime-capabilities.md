---
type: spec
title: "CT2 - Runtime Capabilities"
version: "0.1.0"
---

# CT2 Runtime Capabilities

The Capability Registry records local runtime facts without granting runtimes
authority over CT2 state. Codex, Claude Code, git, MCP servers, app-server
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

## Capability Gating, Not Version Gating

Minimum-version pins are a proxy for **observed capability**, never a goal in
themselves. The documented minimum for a runtime is the oldest version that
delivers the capabilities CT2 actually requires — not the newest version the
vendor ships. A pin is raised only when the protocol starts requiring a
capability that older versions lack, never to track the upstream release
cadence.

- Version numbers in pins, docs, and reports are observation-dated: they
  record what was verified on a stated date, and go stale without invalidating
  the capability they stood for.
- Where a capability is directly observable (for example `codex features
  list`), the observation outranks the version number. The workflow-class
  probe is not yet in this class: it is a version-derived hint
  (`authority: hint`) pending a directly observable workflow surface.
- A newer vendor surface with a graceful fallback to a CT2-supported path
  never raises the minimum.

Observation (2026-06, per `docs/agent-platform-feature-radar-2026-06.md`):
Codex stable `0.137.0` (2026-06-04) ships first-class subagents TOML and a
multi-agent v2 that remains dogfood-default, with **no** independent
dual-reviewer. CT2's serial-by-default, no-fan-out-for-state-writes stance
therefore remains correct: native Codex spawning is an executor surface, not a
review authority, and the cross-vendor cc/cx dual review keeps terminal
authority. The Codex minimum stays at the observation-verified baseline
(`0.130.0` in `ct2-runtime-doctor`, at or above the `0.128.0` capability
floor) because nothing CT2 requires moved above it.

## Status Surface

`ct2-status --doctor` renders a one-screen summary of
`.ct2/runtime/capabilities.json`, including Codex and Claude availability and
degraded paths.
