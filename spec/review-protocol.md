---
type: spec
title: "CT2 — Review Protocol"
version: "0.1.0"
---

# CT2 Review Protocol

## Dual-Approval Rule

```
verdict = approved  iff  lens-claude.status = approved
                    AND  lens-codex.status  = approved

verdict = rejected  iff  lens-claude.status = rejected
                    OR   lens-codex.status  = rejected
```

Both reviewers complete their reviews **independently**. Neither reviewer has visibility into the other's result at the time of their review. Independence is enforced by the session separation and by the sidecar file format (each reviewer writes only their own file).

## Review Work (Adapter-Owned Continuation)

The agent runtime owns continuation. Each lens adapter uses the runtime's native
goal, loop, or one-shot command to scan `in-review/` directly — no sentinel
trigger files are used:

```
review iteration:
  1. Check inbox — claim and process pending messages
  2. Scan in-review/
     → For each ticket: if my sidecar (reviews/{id}-{cc|cx}-r{n}.md) does not exist → perform review
  3. On review completion → write sidecar file to reviews/
  4. Reconciler check: run ct2-reconcile {id} {round}
```

Tickets for which a sidecar already exists are **skipped** (idempotency guaranteed). No duplicate reviews occur even after a session restart.

## Sidecar File

Sidecars are specified in `spec/sidecar-format.md`. They remain immutable after
creation. A re-review after rework produces a new file under an incremented
round number.

## Reconciler Protocol

The reconciler is the one-shot `ct2-reconcile` command. After writing a sidecar,
each lens runs:

```bash
ct2-reconcile {ticket-id} {round}
```

See `spec/reconciler.md` for lock semantics, discovery mode, exit codes, and
terminal-state rules.

## Inbox Protocol

### Message File Path
```
.ct2/inbox/{to}/msg-{ISO8601-compact}-{pid}-{uuid8}.md
```

### Atomic Write
Messages are written to `.ct2/.tmp/` first, then atomically renamed into the inbox:

```bash
ct2_send_message() {
  local to="$1" from="$2" type="$3" ticket="$4" subject="$5" body="$6"
  local ts; ts=$(date -u +%Y%m%dT%H%M%S%3NZ 2>/dev/null || date -u +%Y%m%dT%H%M%SZ)
  # Note: some Linux distros ship `xxd` only with `vim-common`; try `od` first
  # so scripts still start on minimal images.
  local uid; uid=$(uuidgen 2>/dev/null | tr -d '-' | head -c 8 || true)
  [[ -z "$uid" ]] && uid=$(od -An -tx1 -N4 /dev/urandom 2>/dev/null | tr -d ' \n' || true)
  [[ -z "$uid" ]] && uid=$(head -c 8 /dev/urandom | xxd -p | head -c 8 || true)
  local msgid="msg-${ts}-$$-${uid}"
  local tmp; tmp=$(mktemp ".ct2/.tmp/${msgid}.XXXXXX") || return 1
  local dest=".ct2/inbox/${to}/${msgid}.md"
  cat > "$tmp" <<MSGEOF
---
id: $msgid
from: $from
to: $to
type: $type
ticket: $ticket
timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)
---

## Subject
$subject

## Body
$body
MSGEOF
  mv -n "$tmp" "$dest" || { rm -f "$tmp"; echo "ERROR: inbox write failed" >&2; return 1; }
}
```

### Claim and Acknowledge (Atomic, Duplicate-Prevention)

```bash
ct2_claim_message() {
  local role="$1" msgfile="$2"
  ct2-inbox claim "$role" "$msgfile"
}

ct2_ack_message() {
  local role="$1" msgfile="$2"
  ct2-inbox ack "$role" "$msgfile"
}
```

Inbox claims must not rely on shell `mv -n` as a no-clobber primitive. `ct2-inbox`
uses an `O_EXCL` claim lock plus same-filesystem `rename(2)` so exactly one role
loop can claim a message on macOS and Linux.

### Message Types

| Type              | Direction      | Trigger                                              |
|-------------------|----------------|------------------------------------------------------|
| `escalation`      | forge → helm   | Circuit breaker triggered                            |
| `blocked`         | forge → helm   | forge cannot proceed (unclear requirements)          |
| `blocked`         | lens-cc → helm | Reviewer cannot validate ACs (requirement error)     |
| `blocked`         | lens-cx → helm | Same                                                 |
| `clarification`   | helm → forge   | Additional context or correction for in-progress     |
| `priority-override` | helm → forge | Backlog reorder or interrupt request               |
| `info`            | any → any      | Non-blocking general notification                    |

## Review Criteria (loaded from config/ct2-lens-cc-role.md)

1. **Acceptance Criteria satisfaction** — mandatory; any unchecked AC = rejection
2. **Constraint violations** — any constraint violated = automatic rejection
3. **Plan evidence** — missing required plan evidence is **BLOCKING** unless
   the ticket has an explicit, valid `plan-exempt` reason
4. **Code quality** — readability, maintainability, naming
5. **Test coverage** — sufficient coverage for the change; tests are correct and meaningful
6. **Security** — OWASP Top 10; secrets not hardcoded; input validated at boundaries
7. **Scope creep** — implementation does not exceed ticket scope; over-engineering flagged
