---
type: spec
title: "CT2 - Runtime Mirror"
version: "0.1.0"
---

# CT2 Runtime Mirror

The Runtime Mirror is an advisory runtime twin for process table and native task
state. It helps operators see stale sessions, goals, and external tasks without
allowing those runtimes to become source of truth.

## Storage

Runtime twin records live under `.ct2/runtime/` and watcher definitions live in
`.ct2/watchers/*.json`.

## Native Mirror Spike

The initial native task mirror is a spike report only. It may evaluate schema,
drift risks, and hook/script blocking points. It must not produce a production
state synchronizer.

## Rules

- Watchers wake or notify; they do not move terminal states.
- Stale runtime twin state is visible in status.
- Any native mismatch is an advisory event until a human reviews it.
