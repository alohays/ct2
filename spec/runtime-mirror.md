---
type: spec
title: "CT2 - Runtime Mirror"
version: "0.1.0"
---

# CT2 Runtime Mirror

The Runtime Mirror is an advisory runtime twin for process table, native task
state, and runtime observation records such as advisory fan-out records. It
helps operators see stale sessions, goals, external tasks, and parallel-run
shape without allowing those runtimes to become source of truth.

## Storage

Runtime twin records live under `.ct2/runtime/` and watcher definitions live in
`.ct2/watchers/*.json`. Advisory fan-out observation records live under
`.ct2/runtime/fanout/` per `spec/balanced-scorecard.md` and share the same
advisory plane: never source of truth, never a mover of terminal states.

## Native Mirror Spike

The initial native task mirror is a spike report only. It may evaluate schema,
drift risks, and hook/script blocking points. It must not produce a production
state synchronizer.

## Rules

- Watchers wake or notify; they do not move terminal states.
- Stale runtime twin state is visible in status.
- Any native mismatch is an advisory event until a human reviews it.
