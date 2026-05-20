---
type: spec
title: "CT2 Protocol"
version: "0.1.0"
---

# CT2 Protocol

CT2 is a file-first protocol for multi-agent code operations. The reference
implementation is intentionally small: `.ct2/` is the state ledger, bin scripts
perform one-shot mutations, and agent runtimes own all continuation loops.

## Reading Order

1. `spec/directory-structure.md` defines the `.ct2/` ledger.
2. `spec/state-machine.md` defines ticket states and atomic transitions.
3. `spec/ticket-format.md` defines ticket frontmatter and body sections.
4. `spec/sidecar-format.md` defines reviewer verdict sidecars.
5. `spec/reconciler.md` defines `ct2-reconcile`.
6. `spec/adapter-format.md` defines agent adapter markdown.
7. `spec/conformance.md` defines conformance gates.

Existing role, git, evidence, runtime, decision, helm-canvas, and eval specs
compose with this protocol. When a lower-level spec and this document disagree,
this document is the entry point and the lower-level spec must be aligned.

## Protocol Laws

### Filesystem Is the Database

All authoritative CT2 state lives under `.ct2/`. Runtime metadata is advisory.
No daemon, database, socket, queue, or network service may become authoritative
for ticket state.

### Atomic `mv` Is Commit

State transitions are same-filesystem renames between `.ct2/{state}/`
directories. If a transition has a global precondition, the corresponding
one-shot tool must hold the lifecycle lock while rechecking that precondition.
File creation that produces CT2 artifacts uses `.ct2/.tmp/` and a final rename
into place.

### Agent Owns the Loop

CT2 does not own polling or continuation. Agents, shells, cron, CI, or other
external schedulers may invoke CT2 one-shot tools. CT2 tools perform bounded
work and exit.

### Reviewer Independence

`ct2-lens-cc` and `ct2-lens-cx` write independent sidecars for the same ticket
round. A reviewer must not read the matching partner sidecar until after its own
sidecar for that round exists. The reconciler is the only normal component that
needs both sidecars at the same time.

### Reconciler Authority

`done/`, `rejected/`, and `escalated/` are automatic outcomes of
`ct2-reconcile`. No reviewer or engineer moves a ticket to `done/` directly.
`ct2-revise` is the manual human recovery path for terminal review states.

### Adapter Boundary

Agent-specific invocation details live under `adapters/{agent}/{role}.md`.
Core scripts do not grow agent-specific workflow behavior except for the thin
`ct2-lens-cc` and `ct2-lens-cx` dispatchers that read those adapters.

## Required Reference Tools

| Tool | Contract |
|---|---|
| `ct2-init` | Creates `.ct2/`, copies default config, and excludes `.ct2/` through `.git/info/exclude`. |
| `ct2-seal` | Validates draft tickets and moves them to `backlog/`. |
| `ct2-reconcile` | One-shot or discovery-mode reconciler for review sidecars. |
| `ct2-revise` | Human-triggered reset from `rejected/` or `escalated/` to `draft/`. |
| `ct2-status` | Filesystem-derived state query. |
| `ct2-verify` | Local conformance verifier for the reference implementation and adapters. |

## Versioning

Protocol versions use SemVer. Breaking changes include directory renames,
state-transition semantic changes, required sidecar field changes,
`ct2-reconcile` exit-code or side-effect changes, and adapter-format changes
that existing conforming adapters cannot satisfy.

Adding an optional field, adding a one-shot tool that does not change existing
contracts, or refactoring the reference implementation without behavior changes
is not protocol-breaking.
