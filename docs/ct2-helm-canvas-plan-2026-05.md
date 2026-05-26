# CT2 Direction Plan — Helm Canvas: HTML-Based Planning GUI

Authored on: 2026-05-18 KST
Author: ct2 (goal mode)
Target role: `ct2-helm`
Reference main: `78d52f0` — **incorporates protocol-adapter-reframe (PR #13, 2026-05-13)**
Related documents:
- `spec/PROTOCOL.md` — Canonical entry point for the CT2 protocol. Every decision in this plan is subordinate to that protocol's laws (especially "Atomic mv Is Commit" and "Agent Owns the Loop")
- `spec/adapter-format.md` — Strict definition of a CT2 "adapter" (`adapters/{agent}/{role}.md`). **See §4.1 for terminology caution**
- `spec/decision-bridge.md` — Data foundation of this plan (`ct2-decision` + `.ct2/decisions/`)
- `spec/plan-evidence.md` — Where canvas artifacts are stored
- `claude-plugin/skills/ct2-helm/SKILL.md` — Skill definition under change
- `docs/ct2-product-strategy-2026-05.md` — User-interface counterpart to Bet 2 "Plan-mode-first forge"

Reference techniques:
- <https://news.hada.io/topic?id=29347> — "When Claude Code emits HTML instead of Markdown, expressiveness, shareability, and bidirectional interactivity all go up"
- <https://x.com/trq212/status/2052809885763747935> — Original source for the same technique (the hada post is a summary)

---

## 0. One-page summary

### 0.1 Decision

Switch **the default planning interface of `ct2-helm` from a text conversation to an HTML page called the "Helm Canvas"**. For every planning phase, helm generates one self-contained HTML page into `.ct2/plans/`, and the user views that page in a browser and **directly manipulates scope, ticket decomposition, priority, and acceptance criteria via widgets**. The manipulation results flow back to helm through the **Decision Bridge (`.ct2/decisions/`)** that CT2 already owns.

The crux is not building a new system. It is **adding a third provider format ("html") to the Decision Bridge**. After Codex `requestUserInput` and Claude `AskUserQuestion`, HTML becomes another provider format that renders the same decision record. The single source of truth remains the JSON in `.ct2/decisions/`.

At this point the helm workflow is formalized into **five stages** (conversation → canvas generation → canvas decision/copy → token recovery + ticket drafting → seal) (§3.4), and the canvas HTML file becomes a managed artifact of *the same grade* as an md ticket — it traverses a 4-state machine (`open/answered/sealed/expired/`) via atomic `mv` between directories, so at a glance you can always tell which canvases are awaiting a decision versus finished (§4.4).

### 0.2 Why now

| Signal | Meaning |
|---|---|
| helm SKILL.md's "Clarification-First Mandate" | helm is already designed to *ask the user about all ambiguity* — the channel for asking is just impoverished |
| `AskUserQuestion` is capped at 4 questions / 4 options | Cannot present scope, decomposition, AC, priority, and dependencies *on one screen* → decisions fragment |
| Decision Bridge already exists | A provider-neutral decision schema is in place — HTML only needs to add one more "renderer" on top |
| Product Strategy Bet 2 (Plan-mode-first) | The flow of leaving plans as sidecars — the canvas is the *human-facing surface* of that plan |
| HTML-for-agentic-AI technique has matured | A validated pattern: build a "readable plan" with tables/colors/SVG/sliders, then push values back through a bidirectional loop |

### 0.3 What this document does *not* propose (anti-scope)

- ❌ Adopting Electron, React, bundlers, or npm — CT2 is bash + Python stdlib only. The canvas also has zero dependencies.
- ❌ A persistent web server or SaaS dashboard — the canvas is a single-use page that lives only for the duration of planning one ticket.
- ❌ HTML-ifying the `ct2-status` kanban — this plan is limited to the *planning* phase. Monitoring is a separate effort.
- ❌ Tracking HTML in git — the canvas is a runtime artifact under `.ct2/`. Avoids noisy diffs (the trade-off the hada post calls out).
- ❌ Having HTML become the source of truth for decisions — the source of truth is the JSON in `.ct2/decisions/`. HTML is a read-only rendering.

---

## 1. Background: current helm planning interface and its limits

helm currently agrees on a plan with the user through only two channels.

1. **Free-text conversation** — listens to requirements, shows ticket previews inside code fences.
2. **`AskUserQuestion`** — asks about ambiguity via multiple choice.

Structural limits of this approach:

| Limit | Description |
|---|---|
| **Fragmented decisions** | Scope, priority, AC, and dependencies are split into N questions and shown sequentially. The user never sees *the whole picture* in one shot |
| **Widget poverty** | `AskUserQuestion` is multiple choice only. There are no sliders (priority weights), drag interactions (ticket decomposition), or checklists (AC toggles) |
| **No comparison** | "Splitting into 2 tickets vs. 3 tickets" — you cannot view both options side by side; you can only describe them alternately in text |
| **Context evaporation** | The rationale for a decision gets buried in the conversation scroll. Later, reconstructing "why was the scope set this way?" is hard |
| **Passivity** | The user only *answers what helm throws at them*. There is no surface for the user to actively *shape* the plan |

helm SKILL.md already mandates "do not guess; ask the user about every ambiguity." The problem is not intent but **the expressiveness of the asking tool**. This plan replaces that tool.

---

## 2. Reference technique: HTML for Agentic AI

Transposing the gist of the hada/trq212 post into the CT2 context:

| Original claim | CT2 application |
|---|---|
| HTML is more expressive than Markdown thanks to tables, CSS, SVG, and scripts | Visualize the scope matrix, dependency graph (SVG), and ticket decomposition all on one screen |
| An HTML document can be opened in a browser and shared via a link → it actually gets read | `.ct2/plans/canvas/open/{id}-r{n}.canvas.html` opens instantly via `file://`. For team sharing, pass it along as-is |
| **Adjust values with sliders/controls and re-paste the changed values into the prompt** (bidirectional) | The user makes decisions on the canvas → "copy decision" button → paste back into helm (the heart of the Phase 1 loop) |
| Generate one-off editing UI on the fly per task | The canvas is dedicated to *one ticket*. It gets thrown away when done |
| Trade-off: 2–4× slower generation, diff noise | The canvas only lives under `.ct2/` (untracked by git). The generation cost is offset by "the plan actually gets agreed on" |

**Four borrowed principles** (invariant rules of canvas design):

1. **One screen = the whole plan** — scrolling is allowed, but every axis needed for a decision must be on one page.
2. **Bidirectional** — never show-only. Every panel is manipulable, and the manipulation results flow back to helm.
3. **Self-contained** — zero external CDNs, fonts, or scripts. A single `.html` file. Fully functional on `file://`.
4. **The source of truth for decisions is JSON** — HTML is a volatile view. The agreed-on result is sealed as a canonical record under `.ct2/decisions/`.

---

## 3. Core concept: Helm Canvas

### 3.1 Definition

> **Helm Canvas** — a single self-contained HTML page that helm generates for each planning phase.
> It unfolds every pending decision of the in-progress ticket draft into panels and returns the user's widget manipulations to helm through the Decision Bridge.

The canvas is *not* a new UI layer. It is **a manipulable rendering of decision records (`.ct2/decisions/`)**. That single line governs the entire design.

### 3.2 Design philosophy — five non-negotiable principles

These principles emerged from two wrong attempts. (1) The first demo was "six stacked panels of a form" — it accepted input but *did not help with decisions*. (2) The second demo overcorrected by adding a gate that "disables the confirm button until unresolved items hit zero" — and this was worse. **A tool that *requires* resolution while withholding the *means* of resolution (the ability to directly rewrite the text) only locks up the copy button.** A tool that locks the user up is not a good tool.

A good canvas observes the following five principles — all implemented in the demo (`docs/assets/helm-canvas-demo.html`).

| # | Principle | Anti-pattern | How the canvas implements it |
|---|---|---|---|
| **P1** | **The canvas is a rendering of the decision record** | UI and data live apart | A right-hand pane **mirrors the actual `.ct2/decisions/` JSON in real time**. Touching a widget changes the JSON in place and briefly highlights it — you visually confirm "this screen *is* that file" |
| **P2** | **Every decision shows its cost** | Hides the consequences of input | "Plan at a glance" — toggling a scope chip immediately refreshes the In-scope count and estimated days. You feel the *weight* of each toggle |
| **P3** | **Diverging from helm is evidence** | Only the final value is retained | Only the deltas relative to helm's draft (baseline) are shown as a "helm proposal → my decision" delta → preserved in the `overrides` field |
| **P4** | **The canvas guides but never imprisons** | Blocks submission because something is incomplete | The confirm/copy button is **always live**. Unresolved items are not disabled but shown as *advisory* ("items helm recommends confirming") and faithfully carried in the token's `open_items` for helm to pick up |
| **P5** | **The canvas is a proposal, not a form** | Cells helm filled in are fixed | Every cell is freely editable (contenteditable) — AC text, scope labels, constraint category and content, ticket title, size, and detail items. The *structure* is free too — you add/remove tickets, ACs, scope items, constraints, and details. Anything that doesn't fit goes in a "free notes" panel |

P3, P4, and P5 are the real bet of this plan.

- **P3** — Karpathy-style: the *difference* between the model's (helm's) proposed plan and the human's actual decisions is the strongest signal CT2 can capture about a single plan. It is fodder for lens audits and an eval signal for fixing the helm role definition.
- **P4** — helm SKILL.md's Clarification-First Mandate still stands. But the enforcer of that mandate is **helm itself, not a cage around the user**. The canvas does not *hide* unresolved items (advisory + `open_items`) — it passes them to helm — and helm finishes resolving them via conversation. Recording the unresolved *honestly as unresolved* fits CT2's evidence philosophy better than faking resolution.
- **P5** — If the canvas is a form, the user moves only inside helm's frame. If it is a proposal, the user edits the frame itself. Example: the user *directly rewrites* a vague AC like "login UX feels natural" into "main view renders within 2 seconds of login" — this is the real means of resolution that P4 speaks of. P5 is not just about text editing. It extends to **structural editing** — splitting or merging tickets and adding/removing ACs, scope items, constraints, and detail items. Even helm's ticket decomposition draft is *just a starting point*; every panel must remain open to the user's hand to the very end. It is not "helm makes the blanks and the user fills them in" but "helm sketches a draft and the user freely overwrites it." P4 (no imprisonment) and P5 (freedom to amend) are a pair.

### 3.3 Panel composition

The canvas consists of 7 panels. Every panel renders *only when the corresponding decision exists* (progressive disclosure). Every text cell is directly editable per P5.

| Panel | Shows | Widgets | Decision collected |
|---|---|---|---|
| **① helm's interpretation** | A one-paragraph interpretation of user intent + the original quote | Correct/needs-fix binary; free text on fix | Interpretation accuracy confirmation |
| **② Scope** | Per item: In / Out / Pending | State badge click (3-state cycle), label direct edit, add/remove items | Scope boundary |
| **③ Ticket decomposition** | Draft split into N PR-sized tickets | Card **title, size, and detail items all directly editable**, add/remove tickets and items, (Phase 3) drag-merge/split | Ticket boundaries + count |
| **④ Acceptance criteria (AC)** | Verifiable AC checklist | Item check, **direct text edit**, ⚑ambiguity flag, add/remove | AC completeness |
| **⑤ Priority & dependencies** | Position in backlog + SVG graph of dependent tickets | Priority slider, **free-text edit of dependencies**, (Phase 3) draw dependency links | Priority and dependencies |
| **⑥ Constraints & edge cases** | helm-estimated technical/performance constraints, failure modes | Direct edit of category labels and content, add/remove rows | Constraint clarification |
| **⑦ Free notes** | Anything that fits no panel | Free text | Unstructured context to send to helm |

①–⑥ correspond **1:1** with the six items of helm SKILL.md's "Clarification-First Mandate" (interpretation, scope, AC, priority, constraints, dependencies) — the canvas enforces that mandate via GUI rather than text. ⑦ is the escape hatch for unstructured opinions the mandate couldn't capture. ①②④ are panels that can raise *advisories* ("helm recommends confirming"), but per P4, those do not block confirmation.

### 3.4 helm workflow — five stages

The canvas is *not* a replacement for helm but one phase of the helm workflow. The full flow has five stages, each leaving an exact trace in `.ct2/`.

| Stage | What happens | Who | `.ct2/` state change |
|---|---|---|---|
| **S1. Conversational planning** | The user talks with helm to narrow down requirements | User ↔ helm | (no files yet — conversation) |
| **S2. Canvas consolidation** | When the user says "give me HTML", helm consolidates the decisions accumulated so far and generates the canvas HTML | helm | `decisions/pending/{dec}.json` created<br>`plans/canvas/open/{id}-r{n}.canvas.html` created |
| **S3. Canvas decision** | The user manipulates the panels in the browser to decide, then copies the decision token using the **copy button** | User | (no change — decided inside the browser) |
| **S4. Token recovery → ticketization** | The user pastes the token into helm's chat and asks "turn this into the final md ticket". helm validates/recovers the token and writes the md ticket for forge | User → helm | Canvas `open/` → `answered/`<br>`decisions/` `pending/` → `answered/`<br>`draft/{id}-{slug}.md` written |
| **S5. Ticket creation (seal)** | helm runs `ct2-seal` → and immediately after, runs `ct2-helm-canvas seal` to seal the canvas | helm | `ct2-seal`: `draft/` → `backlog/{id}-{slug}.md`<br>`ct2-helm-canvas seal`: canvas `answered/` → `sealed/{id}/` |

```
S1 conversation ──► S2 canvas gen ──► S3 user decides/copy ──► S4 token recovery + ticket draft ──► S5 seal
                    canvas/open/      (browser)                canvas/answered/                     canvas/sealed/
                    decisions/pending/                         decisions/answered/                  backlog/{id}.md
```

What the user does on the canvas in S3 — direct text editing and item add/remove (P5), instant "at-a-glance" refresh on scope toggles (P2), accumulation of deltas where choices diverge from helm's proposal (P3), and advisories shown without blocking copy (P4). The copy button works at any time, and the token carries both `overrides` and `open_items`.

Key invariant: **the canvas HTML file is managed like an md ticket — "state = directory".** You can always tell from the directory alone which canvases are awaiting a decision (`open/`), have been recovered (`answered/`), or have become tickets (`sealed/`) — the detailed lifecycle is in §4.4.

---

## 4. Architecture: a third provider on top of the Decision Bridge

### 4.1 Data flow

```
                       ┌─────────────────────────────────────┐
   helm planning phase ┤ ct2-decision new (creates decision)  │
                       └──────────────┬──────────────────────┘
                                      │  .ct2/decisions/pending/{id}.json   ← single source of truth
                                      │
                ┌─────────────────────┼─────────────────────┐
                ▼                     ▼                     ▼
       ct2-decision format     ct2-decision format    ct2-decision format
            --codex                 --claude               --html        ← this plan's new provider format
                │                     │                     │
       requestUserInput        AskUserQuestion       canvas.html (self-contained)
            (provider)            (provider)            (provider, this plan)
                                                            │
                                                  user browser interaction → token
                                                            │
                                          helm: ct2-helm-canvas recover (nonce verified)
                                                            ▼
                                             .ct2/decisions/answered/{id}.json
```

Key point: HTML is merely **the output of the provider format `ct2-decision format --html`**. `spec/decision-bridge.md` already nails down that "a provider format is one view of the same record, not a second source of truth." The canvas follows this rule verbatim.

> **Terminology caution — "provider format" ≠ "adapter".** Since PR #13's protocol-adapter-reframe, in CT2 the word **"adapter" has a strict meaning**: the `adapters/{agent}/{role}.md` defined by `spec/adapter-format.md` — i.e., the markdown contract describing *how a runtime performs a CT2 role* (currently only the lens role requires one). The HTML this plan deals with is **not** that. HTML is a **provider format** (one of Codex/Claude/HTML) that `ct2-decision` uses to render decision records. The two concepts live at different layers, so to avoid confusion this plan consistently uses **"provider format"**. (Note: `decision-bridge.md` was written before PR #13 and still uses the phrase "adapter view"; Phase 0 cleans that up too, in line with PROTOCOL.md terminology.)

### 4.2 Storage locations

| Artifact | Path | Basis |
|---|---|---|
| Decision record | `.ct2/decisions/{pending,answered,expired}/{dec}.json` | Existing Decision Bridge |
| Canvas HTML | `.ct2/plans/canvas/{open,answered,sealed,expired}/...` | §4.4 canvas lifecycle — state=directory |
| Plan evidence (JSON) | `.ct2/plans/{ticket-id}-r{round}.json` | Existing plan-evidence |

Folding the canvas HTML into `plan-evidence` has a nice side effect — **lens can later reconstruct "which plan was agreed with the user" from that HTML**. The planning canvas itself becomes audit evidence.

### 4.3 PROTOCOL.md law compliance checklist

After PR #13, CT2's invariants are canonized as the "Protocol Laws" in `spec/PROTOCOL.md`. The canvas is subordinate to each of those laws.

| Law / invariant | How the canvas complies |
|---|---|
| bash + Python stdlib only | HTML generation/recovery uses only Python stdlib — string templates, `json`, `argparse`. Zero external packages/CDNs/bundlers |
| **Filesystem Is the Database** | Source of truth is `.ct2/decisions/` and `.ct2/plans/`. HTML is an advisory rendering, runtime metadata |
| **Atomic mv Is Commit** | Canvas creation, state transitions, and decision write-back all use `.ct2/.tmp/` → `mv` |
| **Agent Owns the Loop** | `ct2-helm-canvas`'s `generate`/`recover`/`seal` are all one-shot — they do bounded work and exit immediately. No persistent processes, servers, or daemons |
| **Adapter Boundary** | Required Reference Tools like `ct2-seal` and `ct2-reconcile` are not modified. Canvas logic is isolated in `ct2-helm-canvas` |
| `.ct2/` untracked by git | The canvas lives under `.ct2/plans/` — automatically untracked |
| spec-first | New `spec/helm-canvas.md` precedes implementation, gets listed in the PROTOCOL.md Reading Order; implementation follows |
| Role boundary | The canvas is a helm-only tool. forge/lens do not use it. It only operates within helm's write scope (`draft/`) |

### 4.4 Canvas lifecycle — managed by state, like an md ticket

The first principle of CT2 is **"state transitions are atomic `mv` between directories"**. Just as kanban tickets pass through `draft/ → backlog/ → in-progress/ …`, canvas HTML follows the same discipline. If canvases just pile up anywhere under `.ct2/plans/` — making it impossible to tell which are live decisions awaiting input and which are done — they become clutter. So canvases get **their own 4-state machine**.

```
.ct2/plans/canvas/
├── open/        Right after S2 — helm created it; awaiting user decision (= "inbox")
│                  {id}-r{round}.canvas.html
├── answered/    S4 — copy token recovered to helm; awaiting ticket drafting
├── sealed/      S5 — md ticket created in backlog; sealed as planning evidence
│                  {id}/r{round}.canvas.html  (per-ticket folder, rounds accumulate)
└── expired/     Canvases left undecided by the user, or superseded by revisions
```

**State transitions** (all atomic `mv`, tmpfile-then-`mv` pattern):

| Transition | Trigger | Concurrent effect |
|---|---|---|
| (create) → `open/` | helm runs `ct2-helm-canvas` (S2) | `decisions/pending/{dec}.json` created alongside |
| `open/` → `answered/` | helm recovers the copy token (S4) | `decisions/` `pending/` → `answered/` |
| `answered/` → `sealed/{id}/` | Immediately after `ct2-seal` success, helm calls `ct2-helm-canvas seal` (S5) | (Already done by `ct2-seal`: ticket `draft/` → `backlog/`) |
| `open/`·`answered/` → `expired/` | A new round canvas is created for the same ticket, or TTL expires | The paired decision record also moves to `decisions/expired/` |

**Invariants.** (1) A canvas's state = the directory it sits in. We do not embed a status field inside the HTML (P1 — HTML is read-only). (2) One canvas ↔ one decision record always move as a pair in the same state — a state where one side is `answered` and the other is `pending` is forbidden. (3) Canvases in `open/` are "things the user has not yet decided" — `ct2-status` **counts and shows these like an inbox** ("2 canvases awaiting decision"). (4) When a ticket is revised via `ct2-revise`, that round's canvas moves to `expired/` and a new round's canvas is created in `open/` — isomorphic to the kanban sidecar archive discipline.

This way, canvases become *fully equal-grade managed artifacts* to md tickets — creation, waiting, completion, and expiration are always visible at a glance instead of piling up.

---

## 5. Feedback loop: canvas → helm

The path that sends canvas decisions back to helm. We take the hada post's "paste the values back into the prompt" pattern as the MVP. **Both methods run CT2 tools as one-shot and exit** — this complies with PROTOCOL.md's "Agent Owns the Loop" law.

| Method | How it works | Infrastructure | Adoption phase |
|---|---|---|---|
| **A. Copy-paste token** | Click "confirm" → JS generates a compressed token (one-line JSON) → user pastes into helm chat → helm runs `ct2-helm-canvas recover` to receive it | None. Works on `file://` | **Phase 1 (default)** |
| **B. File drop** | Click "confirm" → JS triggers a browser download of `decision-{id}.json` → helm runs `ct2-helm-canvas recover <file>` to receive it | None (built-in browser download). No server | **Phase 2 (optional)** |

**Why A is the default.** Zero infrastructure, complete on `file://` alone, the pattern validated in the hada post. Planning decisions in JSON are a few KB, so the clipboard suffices. Method B (file drop) is *just an option* for environments where the token is too large or the clipboard is unusable — it has more steps than A (file path coordination needed). Both finish with helm running the **one-shot tool** `recover` exactly once.

> **Rejected method — persistent local server.** Early drafts considered `ct2-helm-canvas --serve` (Python `http.server` accepting `/answer` POST for automatic write-back) as Phase 2. **Rejected.** It runs head-on into PROTOCOL.md's *"Agent Owns the Loop"* — "CT2 does not own polling or continuation. CT2 tools do bounded work and exit" — and *"Filesystem Is the Database"* — "no daemon, socket, or network service can be the authority on ticket state". PR #13 retired `ct2-lens-cx-daemon` and `ct2-lens-cx-tui` for exactly this reason. The smoothness of canvas write-back is not worth reintroducing a daemon — copy-paste/file-drop is the right answer.

**Recovery verification** (shared by methods A and B, specified in the Phase 0 spec):
- The token/file contains the decision `id` and a single-use `nonce` — helm cross-checks against in-flight `decisions/pending/` records to block tampering or confusion.
- `ct2-helm-canvas recover` rejects on `nonce` mismatch and exits non-zero.
- Only on verification success does it `.ct2/.tmp/` → `mv` into `decisions/answered/` and move the canvas to `answered/` — the recovery path only parses files, with no arbitrary command execution surface.

---

## 6. Phased roadmap

### Phase 0 — Spec settlement (1 day, 1 ticket)

- New `spec/helm-canvas.md`: canvas definition, 7-panel schema, five design principles (P1–P5), self-containment constraints, **the canvas 4-state lifecycle (`open/answered/sealed/expired/`) and transition rules**, feedback loop A/B, and recovery verification (`nonce`).
- Register `spec/helm-canvas.md` in `spec/PROTOCOL.md`'s "Reading Order" — make explicit that this spec is subordinate to PROTOCOL.md (subordinate specs realign with PROTOCOL.md on conflict).
- Add the `--html` provider format to `spec/decision-bridge.md` + reword the pre-PR-#13 phrase "adapter view" to "provider format" matching PROTOCOL.md terminology (see §4.1 terminology caution) + add the rule "canvas ↔ decision record transitions are 1:1 paired".
- Add a paragraph to `spec/plan-evidence.md` folding in the `plans/canvas/` path and states.
- Add a row to the `AGENTS.md` Specs table.

### Phase 1 — MVP: copy-paste canvas + lifecycle (3 days, 3 tickets)

- New `bin/ct2-helm-canvas`: takes the decision record + ticket draft, generates self-contained HTML (Python stdlib templates) → atomically places it at `plans/canvas/open/{id}-r{n}.canvas.html`. Also creates `decisions/pending/`.
- `bin/ct2-helm-canvas recover` (or helm calls it): validates/recovers the copy token → canvas `open/`→`answered/`, decision record `pending/`→`answered/` (S4).
- `bin/ct2-helm-canvas seal` subcommand: helm calls it *immediately after* `ct2-seal` succeeds → moves the paired canvas `answered/`→`sealed/{id}/` (S5). **`ct2-seal` itself is not modified** — `ct2-seal` is a PROTOCOL.md Required Reference Tool; injecting canvas side effects into its contract ("validate draft, then move to backlog") would make a core script take on helm-specific behavior (a PROTOCOL.md "Adapter Boundary" violation). The whole canvas lifecycle stays inside `ct2-helm-canvas`.
- Add an `--html` branch to `ct2-decision format`.
- Canvas HTML: 7 panels + right-side decision record mirror. All five principles implemented (P1 JSON mirror / P2 cost summary / P3 override delta / P4 advisory + non-blocking / P5 free editing). Inline CSS/JS, "confirm decision" button → token generation.
- Show "N canvases awaiting decision" (= `canvas/open/` count) in `ct2-status` — like an inbox.
- Add `<workflow id="plan-canvas">` to helm SKILL.md — make §3.4's five stages the *default* flow. Demote `AskUserQuestion` to a fallback for one-off questions.
  - *Outlook*: the protocol-reframe doc (`docs/ct2-protocol-reframe-2026-05-13.md` §13.7) treats helm as "the simplest form of an adapter" and signals a future `adapters/{agent}/helm.md`. This plan sits at a point where a helm adapter does not yet exist, so the workflow goes into SKILL.md — when a helm adapter arrives, the per-runtime invocation section of `plan-canvas` migrates there (the decision schema and lifecycle stay unchanged).
- New `tests/test_canvas_lifecycle.py` — automatically asserts the S1–S5 directory transitions (see "Done gate" below). Manual browser exploration only *supplements* this; it does not replace it.

### Phase 2 — File-drop recovery (1 day, 1 ticket, optional)

- Add a "download decision" button to the canvas HTML — uses the browser's native download for `decision-{id}.json` (no server).
- `ct2-helm-canvas recover <file>`: recovery path that takes a file path. Shares verification logic with Phase 1 token recovery.
- **No persistent server is introduced** (rejection rationale in §5). If Phase 1 copy-paste is enough, this Phase can be skipped entirely.

### Phase 3 — Expressiveness upgrades (gradual, follow-up)

- Ticket decomposition panel: drag-merge/split of cards, side-by-side comparison view of two options.
- Dependencies panel: link dependency lines with backlog tickets via SVG graph.
- Priority slider: real-time preview of position inside the kanban backlog.
- (Optional) Link the canvas to a read-only kanban view in `ct2-status`.

### Done gate — conditions `/goal` can directly verify

When developing this plan with `/goal`, "done" at each stage must be a **check decidable by exit code**, not manual human confirmation. `/goal`'s stop-hook only halts when condition satisfaction is decided objectively — manual verification cannot be that signal. CT2 already has a `tests/test_*.py` (stdlib-only) system, and `test_state_lifecycle.py` and `test_script_syntax.py` are direct precedents, so the canvas adds checks in the same place.

| Stage | Done gate (machine-checkable, exit code 0 = done) |
|---|---|
| **Phase 0** | `spec/helm-canvas.md` exists + referenced by `PROTOCOL.md`'s Reading Order and the `AGENTS.md` Specs table + `ct2-verify` green (0 conformance violations from the new spec) + `test_repository_hygiene.py`-style checks show 0 broken spec links |
| **Phase 1** | `tests/test_canvas_lifecycle.py` passes — on a scratch `.ct2/`, asserts: ① `ct2-helm-canvas` creates a file in `canvas/open/` along with `decisions/pending/` ② `recover` atomically transitions `open/→answered/`·`pending/→answered/` ③ `ct2-helm-canvas seal` transitions `answered/→sealed/{id}/` ④ after every transition, the canvas↔record states agree and there are 0 orphans. `test_script_syntax.py` auto-checks the new bin scripts. `ct2-verify` green (0 conformance violations from the new spec/tool). The canvas HTML must parse without error under `python3 -m html.parser` and pass `node --check` (when available) for JS |
| **Phase 2** | Add a case to `tests/test_canvas_lifecycle.py` — `ct2-helm-canvas recover <file>` rejects a nonce-mismatched file (non-zero exit) and, for a valid file, atomically records into `decisions/answered/` + moves the canvas `open/→answered/` |
| **Phase 3** | Per-panel functionality adds its own check per ticket (splittable) |

**Principle: a ticket's AC must reduce to "this gate is green".** When helm cuts tickets out of this plan, each AC maps to one line of the gates above — only then can `/goal` autonomously run "implement → run gate → if green, done". §9's success metrics are *operational outcomes* (measured after a feature has been built, over time), not dev-done conditions — conflating the two means `/goal` never halts.

Change summary by artifact:

| Category | New/Modified |
|---|---|
| spec | `spec/helm-canvas.md` new (7 panels, P1–P5, 4-state lifecycle); `decision-bridge.md`, `plan-evidence.md` enhanced |
| bin | `bin/ct2-helm-canvas` new (subcommands `generate`/`recover`/`seal`, all one-shot), `--html` branch in `bin/ct2-decision`, `open/` count in `bin/ct2-status`. **Required Reference Tools like `ct2-seal` and `ct2-reconcile` are not modified** |
| dir | `.ct2/plans/canvas/{open,answered,sealed,expired}/` — `ct2-init` creates them |
| tests | `tests/test_canvas_lifecycle.py` new (Phase 1) — the done gate. Phase 2 adds file-drop recovery cases to the same file |
| skill | Add the `plan-canvas` workflow to `claude-plugin/skills/ct2-helm/SKILL.md` (sync the codex-side `codex-plugin/skills/ct2-helm/`) |
| docs | This document; `AGENTS.md` Specs table |

---

## 7. HTML generation spec (summary)

Detailed in `spec/helm-canvas.md`; key constraints:

- **Single file** — one `.html`. Zero external resource references. SVG is inline.
- **Render budget** — generation tokens are 2–4× Markdown (hada post). Hence the canvas is generated *only when a decision actually exists*. Simple one-off questions still use `AskUserQuestion`.
- **Decision record mirror (P1)** — the right side live-renders the `.ct2/decisions/` payload. Widget manipulation updates and highlights the corresponding field. The HTML carries no separate state — widget = record field.
- **Cost summary (P2)** — ticket count, expected workload, In-scope count, and unresolved count immediately recompute on panel manipulation.
- **Override delta (P3)** — `ct2-helm-canvas` embeds helm's draft as the baseline into the HTML. The canvas shows changes relative to the baseline, and includes that delta in the recovery token's `overrides` field.
- **Advisory + non-blocking (P4)** — the confirm/copy button is never disabled in any state. Unresolved items are shown as an advisory list, and carried verbatim in the token's `open_items` array to helm. If `open_items` is non-empty, helm confirms them via conversation before seal.
- **Free editing (P5)** — AC, scope, constraints, and ticket titles are `contenteditable` text. Items can be added/removed. The canvas uses helm's proposals only as *initial values* — the user freely overwrites them.
- **State preservation** — work state is saved to `localStorage` so a refresh does not lose progress (no server needed).
- **Accessibility** — keyboard-operable, contrast-compliant, no information conveyed by color alone (scope chips use color + text + shape).
- **Determinism** — same decision record → same HTML. `ct2-helm-canvas` behaves like a pure function (modulo timestamps).
- **Recovery token verification** — the pasted token contains the decision `id` and nonce. helm cross-checks against in-flight records to block tampering or confusion.

---

## 8. Risks and anti-bets

| Risk | Mitigation |
|---|---|
| Canvas generation is slow, breaking the planning flow | Generate only when a decision actually exists. Keep one-off questions on `AskUserQuestion`. Generate in the background |
| User won't open a browser and prefers text | The canvas is the *default*, but helm always offers a text fallback. Never forced |
| HTML becoming a de facto second source of truth | Structural block — HTML is the output of `ct2-decision format --html`. The agreed result must be sealed into `.ct2/decisions/answered/` JSON via `ct2-helm-canvas recover` |
| User ignores advisories and confirms → an incomplete plan gets sealed | Core of P4 — instead of caging, *trace*. Unresolved items flow to helm via the token's `open_items`, and helm — aware of them — confirms via conversation before seal. Even if it proceeds as-is, the `open_items` record remains in plan-evidence for lens to audit. "Never blocked" is different from "never tracked" |
| Tampered token/file gets recovered | `ct2-helm-canvas recover` cross-checks decision `id`/`nonce` against in-flight `decisions/pending/` records; on mismatch, exits non-zero. The recovery path only parses files — no arbitrary command execution surface |
| Temptation to introduce a persistent server | Explicitly rejected in §5 — a PROTOCOL.md "Agent Owns the Loop" violation. Recovery is always via one-shot `recover` only |
| Canvas HTML pollutes git diffs | Lives under `.ct2/plans/` — already untracked by git |
| forge/lens mimic the canvas and breach permission boundaries | The canvas is specified as helm-only. forge/lens do not use it |

**Explicit anti-bets** (inheriting Product Strategy's anti-bet spirit):
- Do not grow the canvas into a `ct2-status` monitoring dashboard — it is limited to the planning phase.
- Do not bolt on persistent SaaS, auth, or multi-user to the canvas — it is a single-use local page.
- Do not treat HTML as the *sole* evidence — the decision JSON is canonical.

---

## 9. Success metrics

| Axis | Metric | Initial target |
|---|---|---|
| Agreement quality | Ratio of canvas-using tickets that require helm revisit (scope re-discussion) after seal | −40% vs. baseline |
| Decision visibility | Ratio of planning decisions that are recorded as canonical records in `.ct2/decisions/answered/` | ≥ 0.95 |
| Speed | Helm round-trips between canvas generation → user confirmation → seal | −30% vs. baseline |
| Adoption | Ratio of planning phases where the canvas is used as the default channel | ≥ 0.80 (excluding text fallback) |
| Auditability | Ratio of done tickets that carry `canvas-r*.html` planning evidence | ≥ 0.90 |
| Intervention signal (P3) | Ratio of sealed tickets whose records captured `overrides` (delta between helm proposal ↔ user decision) | ≥ 0.99 (zero-delta cases are also explicitly recorded as "identical") |

Mapping onto Product Strategy's balanced scorecard: directly lifts **Evidence** (decision record ratio, auditability, override capture) and **Trust** (revisit ratio reduction), while moving within bounds that do not harm **Cost/Latency** (round-trip count). The `overrides` signal in particular feeds Product Strategy Bet 4 (role eval harness) — it surfaces *where helm frequently misses* as data, making it direct material for role definition regression tests.

---

## 10. Immediate action items (candidate tickets)

If helm adopts this plan, cut tickets in the order below (1 ticket = 1 PR = 1 day):

1. Write `spec/helm-canvas.md` (7 panels, P1–P5, 4-state lifecycle) + enhance `decision-bridge.md` / `plan-evidence.md` / `AGENTS.md`. *(Phase 0)*
2. `bin/ct2-helm-canvas` MVP (create → `open/`) + `ct2-decision format --html` branch. *(Phase 1)*
3. Canvas lifecycle: `ct2-helm-canvas recover` (`open/`→`answered/`) + `ct2-helm-canvas seal` (`answered/`→`sealed/`) + `ct2-init` directory creation + `ct2-status` `open/` count + **`tests/test_canvas_lifecycle.py`** (the done gate for this ticket). *(Phase 1)*
4. Add the `plan-canvas` workflow (§3.4 five stages) to helm `SKILL.md` + sync the codex side. *(Phase 1)*
5. (Optional) File-drop recovery: canvas "download decision" button + `ct2-helm-canvas recover <file>` + add cases to `test_canvas_lifecycle.py`. *(Phase 2)*
6. Expressiveness upgrades for ticket decomposition / dependencies / priority panels. *(Phase 3, splittable)*

Every AC of every ticket must reduce to a single line in §6's "Done gate" table — that is the termination condition for `/goal`'s autonomous development. Tickets cut without checks cannot have "done" decided by `/goal`, so they are not accepted.

---

## 11. Implementation status (2026-05-19, `feat/helm-canvas`)

Phases 0–2 are implemented. Phase 3 was deliberately positioned as "gradual, follow-up" expressiveness work from the start, so it remains future work.

| Item | Artifact | Status |
|---|---|---|
| Phase 0 spec | `spec/helm-canvas.md` (new), enhancements to `PROTOCOL.md` / `decision-bridge.md` / `plan-evidence.md` / `AGENTS.md` | ✅ |
| Directories | `ct2-init` / `ensure_ct2` create `plans/canvas/{open,answered,sealed,expired}/` | ✅ |
| Canvas renderer | `bin/_ct2_canvas.py` — 7 panels, P1–P5, self-contained HTML + token parser | ✅ |
| CLI | `bin/ct2-helm-canvas` — `generate`/`recover`/`seal`/`expire` one-shot subcommands | ✅ |
| provider format | `ct2-decision format --html` | ✅ |
| Inbox display | `ct2-status` "open canvases" count | ✅ |
| Workflow | `plan-canvas` in claude- and codex-side helm SKILL.md | ✅ |
| Phase 2 file drop | Canvas "download" button + `ct2-helm-canvas recover --file` | ✅ |
| Done gate | `tests/test_canvas_lifecycle.py` (9 cases), `ct2-verify` green, full 95-test suite passing | ✅ |
| Phase 3 | Drag-merge/split, SVG dependency-line linking — follow-up | ⏸ Intentional follow-up |

Re-verification (2026-05-19): cross-checked §7 items and closed the gaps — localStorage **restore** (only save was present, no restore), **keyboard operation** for `role=button` controls, and the **dependency graph SVG** on panel ⑤ (data-driven, real-time). Full 96 tests + `ct2-verify` green.

---

## Appendix A. Helm Canvas demo

To make the concept of this plan checkable on screen rather than in prose, a working demo canvas ships alongside:

```
docs/assets/helm-canvas-demo.html
```

Open it in a browser as-is (`file://`) and a canvas for a hypothetical ticket #42 (OAuth login) appears. The initial state has 3 helm-recommended confirmations (unconfirmed interpretation + 1 pending scope + 1 ⚑ambiguous AC), but **the confirm button works from the start**. You can manipulate the panels and directly verify the five principles of §3.2:

- **P1** — Every time you touch a widget, the right-side "decision record" JSON changes in place and briefly highlights.
- **P2** — Toggling scope chips immediately refreshes the In-scope count in "Plan at a glance".
- **P3** — Choices that diverge from helm's proposal (e.g., move 'account linking' from pending → out) accumulate in the "helm proposal → my decision" delta.
- **P4** — Even when confirmation-recommended items remain, the "confirm decision" button is always clickable. Click it and the token gets copied with those items loaded into `open_items` — helm follows up to confirm. The user is not caged.
- **P5** — You can click the text of an AC marked ⚑ambiguous ("login UX feels natural") and *directly rewrite* it as "main view renders within 2 seconds of login". You can also add/remove scope items, constraints, and acceptance criteria.

The demo is self-contained (inline CSS/JS, zero external dependencies), so it doubles as a reference implementation of the technical constraints the canvas must follow.

## Appendix B. Decision record ↔ canvas mapping example

```
.ct2/decisions/pending/dec-0007.json   (summary)
  question:  "Confirm the plan for ticket #42 'OAuth login'"
  questions: [interpretation, scope, decomposition, AC, priority, constraints]   ← source of the 7 panels
        │
        │  ct2-helm-canvas generate  (= ct2-decision format --html)
        ▼
.ct2/plans/canvas/open/42-oauth-login-r0.canvas.html
        │
        │  user manipulation → "confirm decision" → copy token → paste into helm
        ▼
helm: ct2-helm-canvas recover '<token>'   (nonce verified)
        ▼
.ct2/decisions/answered/dec-0007.json     ← helm reads this and finalizes the ticket draft
.ct2/plans/canvas/answered/42-oauth-login-r0.canvas.html  ← canvas moves in tandem
```

---

*This plan is intended for helm to review with the user, then start cutting tickets from Phase 0. Per the spec-first principle, `spec/helm-canvas.md` precedes implementation.*
