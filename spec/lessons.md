---
type: spec
title: "CT2 — Lessons Ledger"
since: "0.3.0"
---

# CT2 Lessons Ledger

The lessons ledger is CT2's cross-ticket operational memory: the outer loop that
turns failure boundaries (rework, escalation) into rules a later ticket consults.
It is built **consult-first** — the read path is defined and un-skippable before
any promotion logic — to avoid the reader-less-ledger pathology that killed two
earlier designs (`docs/ct2-loop-design-strategy-2026-06.md` §4.1).

## Store

```
.ct2/lessons/lessons.jsonl
```

Append-only, per-project, written **exclusively** by `bin/ct2-lesson` through the
concurrency-safe `append_jsonl` (flock) append — never a read-modify-write. Roles
invoke `ct2-lesson`; nothing else writes the file. `ct2-init` creates the
directory. The store is untracked `.ct2/` state; no host-repo files are tracked
(`spec/host-repo-cleanliness.md`). A future `~/.ct2/lessons/` global tier is
reserved (see *Scope*) but not yet writable.

## Event log and fold

The ledger is an **event log**, not a mutable record set. Two event kinds:

| Event | Fields |
|---|---|
| `add` | `id`, `event: add`, `ts`, `ticket`, `round`, `source`, `category`, `rule`, `scope`, `paths` |
| `retire` | `id`, `event: retire`, `ts`, `target` (an `add` id), `reason` |

Current state is **folded** from the events at read time, so there is no
read-modify-write race and concurrent role writers are safe. The fold:

1. Groups `add` events by `(category, scope)`.
2. Within a group, clusters by **path overlap** (single-linkage `fnmatch`; two
   adds with disjoint paths are different lessons, so a forge regression-test
   lesson in `bin/` does not falsely corroborate one in `docs/`). Path-absence
   on either side never splits a cluster.
3. A cluster's canonical `id` is its earliest member's id; its `rule` is the
   latest member's rule; its `occurrences` are all members.
4. A cluster is `retired` if any member id is a `retire` target; else
   `corroborated` if its members span **≥ 2 distinct tickets**; else `candidate`.

## Record fields

- `category` — drawn from the spec-owned enumerated taxonomy below. Extended
  **only by a spec MINOR**, never free text: recurrence is computed over a closed
  set of categorical keys, never prose similarity. This is the direct answer to
  the cross-model count=1 noise that killed the planning digest.

  ```
  missing-regression-test  scope-creep        ac-unverifiable   evidence-missing
  env-setup                flaky-test         api-contract      style-convention
  ```

- `scope` — `repo | role:forge | role:helm`. The value set reserves `global` for
  a future `~/.ct2` tier without a schema change.
- `rule` — imperative, ≤ 200 chars.
- `paths` — optional path globs the lesson applies to; used both to refine
  corroboration clusters and to rank the digest against a ticket's
  `touched-files`.

## Status semantics (D5)

Promotion is **automatic and unsupervised**: a `(category, scope)` cluster seen
across ≥ 2 distinct tickets becomes `corroborated` with no human approval gate.
The status word is deliberately **`corroborated`, not `verified`**: it asserts
*this failure class recurred across ≥ 2 tickets and the rule is load-bearing*,
never *this rule was execution-proven*. `candidate` clusters (a single ticket)
are surfaced but labelled `[unverified]`.

**Human-gate fallback.** If corroborated lessons prove low-quality at solo scale,
the documented one-line fallback is to gate promotion behind human confirmation —
require a `ct2-lesson confirm --id X` event before the fold treats a cluster as
`corroborated`. The recurrence-over-closed-taxonomy design, the `[unverified]`
labels, the `retire` correction path, and the digest cap bound the
false-corroboration surface in the meantime (Risk #4).

## Commands

```bash
ct2-lesson add --ticket {id} --round {r} --source {path} \
  --category {cat} --rule "…" --scope {scope} [--path glob …]
ct2-lesson retire --id {lesson-id} --reason "…"
ct2-lesson digest --role {forge|helm} [--ticket {id}] [--touched-files a,b] [--max N]
ct2-lesson list            # folded state as JSON
```

## Consult digest

`ct2-lesson digest --role {role}` renders the consult block:

- excludes retired lessons; filters to scope `repo` + `role:{role}`;
- ranks `corroborated` before `candidate`, then by `fnmatch` overlap of lesson
  `paths` against the ticket's `touched-files`, then by recency;
- caps output at ~1200 chars with a clean "none recorded" line when empty;
- labels candidates `[unverified]`.

The ranking is specified here, not implementation-defined. The digest is consumed
on the **mandatory serialized pickup path** (`bin/ct2-pickup`), not an optional
SKILL step agents skip. **Lenses are excluded from lesson consumption by design**:
forge-authored memory in reviewer context is exactly the anchoring channel the
independence hooks exist to prevent.

## Ladder mapping

The article's five-stage memory ladder onto CT2 mechanisms:

| Stage | CT2 mechanism |
|---|---|
| 1 Fail | structured `- AC{n}: fail` lines + `### [BLOCKING]` headings; enriched escalations |
| 2 Investigate | `ct2-lesson add` at rework/escalation: category + imperative rule + paths |
| 3 Verify → **Corroborate** | automatic recurrence promotion over `(category, scope)` keys — corroboration, not proof |
| 4 Distill | planning lints; human promotion of corroborated lessons into helm SKILL principles or seal-gate checks (`ct2-lesson digest --role …` is the review queue) |
| 5 Consult | pickup-stdout digest + mandatory plan-evidence `Lessons consulted` line + draft-time lint advisories |

## Writers

- **Forge**, rework pickup: after reading the rejection sidecars, record one
  lesson per BLOCKING class it fixes (category, rule, paths).
- **Helm**, escalation-response: after reading the enriched escalation, record the
  lesson; interactive helm confirms wording with the user, `helm-auto-cx` records
  autonomously.
