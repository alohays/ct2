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

## Review Loop (Idempotent Scan)

Every loop iteration scans `in-review/` directly — no sentinel trigger files are used:

```
loop iteration:
  1. Check inbox — claim and process pending messages
  2. Scan in-review/
     → For each ticket: if my sidecar (reviews/{id}-{cc|cx}-r{n}.md) does not exist → perform review
  3. On review completion → write sidecar file to reviews/
  4. Reconciler check: if the other reviewer's sidecar also exists → issue verdict
```

- **lens-cc**: `/loop`-based, 60-second interval idempotent scan
- **lens-cx**: visible Codex TUI loop driven by `ct2-lens-cx-tui`, using
  `lens_cx.poll_interval_sec` (default 180 seconds). The legacy headless
  `ct2-lens-cx-daemon` uses the same interval source.

Tickets for which a sidecar already exists are **skipped** (idempotency guaranteed). No duplicate reviews occur even after a session restart.

## Sidecar File

**Path**: `.ct2/reviews/{ticket-id}-{cc|cx}-r{n}.md`  
(where `n` = the ticket's current `review-round`)

```markdown
---
ticket: 003-refactor-db-pool
reviewer: ct2-lens-cc          # ct2-lens-cc | ct2-lens-cx
round: 1
verdict: rejected              # approved | rejected
timestamp: 2026-04-13T15:00:00Z
---

## Summary
One-paragraph summary of the review finding.

## Acceptance Criteria Check
- [x] Pool size configurable via environment variable
- [x] Error message on pool exhaustion is clear
- [ ] Existing integration tests pass  ← FAILED

## Issues Found

### [BLOCKING] Integration test failures
Detailed description of the blocking issue.

### [WARNING] Minor style inconsistency (non-blocking)
Description of non-blocking finding.

## Recommendation
rejected — integration tests must be fixed before approval.
Suggested remediation: ...
```

**Sidecar files are immutable after creation.** A re-review after rework produces a new file under an incremented round number.

## Reconciler Protocol

The reconciler is embedded in both lens loops. After writing a sidecar, each lens runs:

```bash
ct2_reconcile() {
  local ticket="$1"   # path to ticket file in in-review/
  local id; id=$(basename "$ticket" .md | grep -oE '^[0-9]+')
  local round; round=$(python3 -c "
import re; c=open('$ticket').read()
m=re.search(r'review-round:\s*(\d+)', c); print(m.group(1) if m else '0')")

  local cc_sidecar=".ct2/reviews/${id}-cc-r${round}.md"
  local cx_sidecar=".ct2/reviews/${id}-cx-r${round}.md"

  [[ -f "$cc_sidecar" && -f "$cx_sidecar" ]] || return 0

  # O_EXCL lockfile — exactly one reconciler wins
  local lockfile=".ct2/.meta/${id}-r${round}-reconcile.lock"
  ( set -C; echo "$$" > "$lockfile" ) 2>/dev/null || return 0

  local cc_v; cc_v=$(python3 -c "
import re; c=open('$cc_sidecar').read()
m=re.search(r'verdict:\s*(\w+)', c); print(m.group(1) if m else 'pending')")
  local cx_v; cx_v=$(python3 -c "
import re; c=open('$cx_sidecar').read()
m=re.search(r'verdict:\s*(\w+)', c); print(m.group(1) if m else 'pending')")

  local max_rounds; max_rounds=$(python3 -c "
import re
try:
    c=open('.ct2/config/harness.yaml').read()
    m=re.search(r'max_review_rounds:\s*(\d+)', c); print(m.group(1) if m else '3')
except: print('3')")

  if [[ "$cc_v" == "approved" && "$cx_v" == "approved" ]]; then
    _ct2_update_ticket_verdict "$ticket" "approved" "$round" "$cc_sidecar" "$cx_sidecar"
    mv ".ct2/in-review/$(basename "$ticket")" ".ct2/done/$(basename "$ticket")"
  elif (( round + 1 >= max_rounds )); then
    _ct2_update_ticket_verdict "$ticket" "escalated" "$round" "$cc_sidecar" "$cx_sidecar"
    mv ".ct2/in-review/$(basename "$ticket")" ".ct2/escalated/$(basename "$ticket")"
    # Send escalation to helm inbox
    ct2_send_message "ct2-helm" "reconciler" "escalation" "$(basename "$ticket")" \
      "Ticket $(basename "$ticket") — Circuit Breaker Triggered" \
      "Max review rounds (${max_rounds}) exceeded. Human intervention required."
  else
    _ct2_update_ticket_verdict "$ticket" "rejected" "$round" "$cc_sidecar" "$cx_sidecar"
    mv ".ct2/in-review/$(basename "$ticket")" ".ct2/rejected/$(basename "$ticket")"
  fi

  rm -f "$lockfile"
}
```

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
  mv -n ".ct2/inbox/${role}/${msgfile}" \
        ".ct2/inbox/${role}/processing/${msgfile}" 2>/dev/null && \
    echo ".ct2/inbox/${role}/processing/${msgfile}"
}

ct2_ack_message() {
  local role="$1" msgfile="$2"
  mv -n ".ct2/inbox/${role}/processing/${msgfile}" \
        ".ct2/inbox/${role}/done/${msgfile}"
}
```

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
3. **Code quality** — readability, maintainability, naming
4. **Test coverage** — sufficient coverage for the change; tests are correct and meaningful
5. **Security** — OWASP Top 10; secrets not hardcoded; input validated at boundaries
6. **Scope creep** — implementation does not exceed ticket scope; over-engineering flagged
