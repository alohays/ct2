---
type: spec
title: "CT2 Helm Canvas"
version: "0.1.0"
---

# CT2 Helm Canvas

The Helm Canvas is a self-contained HTML page that `ct2-helm` generates so a
user can review and decide a plan visually, then return the decision to helm.

This spec composes with `spec/PROTOCOL.md`; when the two disagree, PROTOCOL.md
is authoritative and this spec must be aligned. The canvas is **not** a CT2
"adapter" (`spec/adapter-format.md`): it is a `provider format` — one of the
render targets of `ct2-decision`, alongside Codex `requestUserInput` and Claude
`AskUserQuestion`. The `.ct2/decisions/` JSON record stays the single source of
truth; the HTML is an advisory render.

## Design Principles

- **P1 — The canvas renders a decision record.** The HTML has no authoritative
  state of its own. The right-hand panel mirrors the `.ct2/decisions/` payload.
- **P2 — Every decision shows its cost.** Toggling a panel updates a live
  summary (ticket count, scope size, advisory count).
- **P3 — Divergence from helm is evidence.** The canvas embeds helm's proposal
  as a baseline and records the delta in the answer's `overrides` field.
- **P4 — The canvas guides, it does not imprison.** The confirm/copy action is
  never disabled. Unresolved items are advisory and travel back in the answer's
  `open_items` array for helm to follow up.
- **P5 — The canvas is a proposal, not a form.** Every text cell is editable;
  tickets, acceptance criteria, scope items, and constraints can be added or
  removed.

## Decision Record

A canvas decision record is a standard `.ct2/decisions/` record (see
`spec/decision-bridge.md`) with `provider: html`, `kind: plan-canvas`, a
single-use `nonce`, and a `canvas` object:

```json
{
  "id": "decision-...",
  "schema_version": "1",
  "status": "pending",
  "provider": "html",
  "role": "ct2-helm",
  "kind": "plan-canvas",
  "ticket": "{ticket-slug}",
  "nonce": "{hex}",
  "canvas": {
    "round": 0,
    "title": "string",
    "interpretation": {"summary": "string", "quote": "string"},
    "scope": [{"key": "string", "label": "string", "state": "in|out|hold"}],
    "tickets": [{"title": "string", "size": "string", "items": ["string"]}],
    "acceptance_criteria": [
      {"id": "string", "text": "string", "accepted": true, "flagged": false}
    ],
    "priority": "low|medium|high|critical",
    "dependency": "string",
    "constraints": [{"label": "string", "text": "string"}]
  }
}
```

The answered record adds `status: answered`, `answered_at`, an `answer` object
(the user's decided canvas, same shape as `canvas`), `overrides` (string list,
the P3 delta), and `open_items` (string list, the P4 advisory items).

## Panels

The canvas renders seven panels, each mapping to a helm Clarification-First
concern: interpretation, scope, ticket split, acceptance criteria, priority and
dependency, constraints, and a free-form note. Panels interpretation, scope,
and acceptance criteria can raise advisory items; none of them block confirm.

## Self-Containment

The generated HTML is a single file with inline CSS and JavaScript and no
external references (no CDN, font, or script URLs). It works from `file://`.
Generation uses Python standard library only.

## Lifecycle

Canvas files live under `.ct2/plans/canvas/` and their state is the directory
they occupy — the same "state is the directory" rule as kanban tickets.

```
.ct2/plans/canvas/
├── open/        generated, awaiting the user's decision
├── answered/    decision token recovered into the record
├── sealed/      {ticket}/ — the ticket reached backlog
└── expired/     superseded or abandoned canvases
```

File name: `open/`, `answered/`, `expired/` use `{ticket}-r{round}.canvas.html`;
`sealed/` uses `{ticket}/{ticket}-r{round}.canvas.html`.

### Transitions

All transitions are atomic same-filesystem renames (tmpfile-then-`mv` for
creation).

| Transition | Trigger |
|---|---|
| (create) → `open/` | `ct2-helm-canvas generate` |
| `open/` → `answered/` | `ct2-helm-canvas recover` accepts a decision token |
| `answered/` → `sealed/{ticket}/` | `ct2-helm-canvas seal` after `ct2-seal` succeeds |
| `open/`,`answered/` → `expired/` | `ct2-helm-canvas expire` (new round or abandonment) |

### Invariants

- A canvas and its decision record move together: never one `answered` while
  the other is `pending`.
- `ct2-seal` is not modified — canvas bookkeeping lives entirely in
  `ct2-helm-canvas` (PROTOCOL.md "Adapter Boundary").
- `ct2-status` counts `canvas/open/` as decision-awaiting work.

## Feedback Loop

The user returns the decision by a copy-paste token (the default) or, optionally,
a downloaded JSON file. CT2 introduces no persistent server or daemon — every
`ct2-helm-canvas` subcommand performs bounded work and exits (PROTOCOL.md
"Agent Owns the Loop").

The token is the string `CT2-DECISION ` followed by one-line JSON containing
`decision`, `ticket`, `nonce`, `answer`, `overrides`, and `open_items`.
`ct2-helm-canvas recover` rejects (non-zero exit) a token whose `decision` is
not pending or whose `nonce` does not match the pending record.

## Tool

`ct2-helm-canvas` is a one-shot tool with subcommands `generate`, `recover`,
`seal`, and `expire`. It is helm-only; forge and lens do not use it.
