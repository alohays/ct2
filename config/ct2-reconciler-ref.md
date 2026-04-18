# CT2 Reconciler Reference

This file contains the reconciler implementation loaded by ct2-lens-cc (and ct2-lens-cx) during Step 5 of the review loop. Load this file when both sidecars are present and reconciliation is needed.

## perform_reconcile

```bash
perform_reconcile() {
  local ticket="$1" ticket_id="$2" round="$3"

  # O_EXCL lockfile — exactly one reconciler instance wins.
  # Stale detection combines liveness (`kill -0`) with mtime age, since PID reuse
  # on long-running systems can mask a dead owner. Reconcile runs in seconds, so
  # any lockfile older than ~10 min is almost certainly abandoned.
  local lockfile=".ct2/.meta/${ticket_id}-r${round}-reconcile.lock"
  if ! ( set -C; echo "$$" > "$lockfile" ) 2>/dev/null; then
    local lock_pid lock_mtime lock_age
    lock_pid=$(cat "$lockfile" 2>/dev/null || echo "")
    lock_mtime=$(stat -f %m "$lockfile" 2>/dev/null || stat -c %Y "$lockfile" 2>/dev/null || echo 0)
    lock_age=$(( $(date +%s) - lock_mtime ))
    if [[ -n "$lock_pid" ]] && kill -0 "$lock_pid" 2>/dev/null && (( lock_age < 600 )); then
      return 0  # Owner alive and lock recent — skip.
    fi
    rm -f "$lockfile"
    ( set -C; echo "$$" > "$lockfile" ) 2>/dev/null || return 0
  fi

  local cc_v; cc_v=$(python3 -c "
import re, sys; c=open(sys.argv[1]).read()
m=re.search(r'verdict:\s*(\w+)', c); print(m.group(1) if m else 'pending')" \
    ".ct2/reviews/${ticket_id}-cc-r${round}.md")

  local cx_v; cx_v=$(python3 -c "
import re, sys; c=open(sys.argv[1]).read()
m=re.search(r'verdict:\s*(\w+)', c); print(m.group(1) if m else 'pending')" \
    ".ct2/reviews/${ticket_id}-cx-r${round}.md")

  local max_rounds; max_rounds=$(python3 -c "
import re, sys
try:
    c=open(sys.argv[1]).read()
    m=re.search(r'max_review_rounds:\s*(\d+)', c); print(m.group(1) if m else '3')
except: print('3')" ".ct2/config/harness.yaml")

  local ticket_file; ticket_file=$(basename "$ticket")

  # Guard: ticket may have been moved by the other reconciler
  if [[ ! -f ".ct2/in-review/${ticket_file}" ]]; then
    echo "Reconciler: ${ticket_file} already moved from in-review/; skipping"
    rm -f "$lockfile"
    return 0
  fi

  local src=".ct2/in-review/${ticket_file}"
  if [[ "$cc_v" == "approved" && "$cx_v" == "approved" ]]; then
    _update_verdict "$ticket_file" "approved" "$ticket_id" "$round"
    mv -n "$src" ".ct2/done/${ticket_file}" 2>/dev/null
    if [[ -f "$src" ]]; then
      echo "Reconciler: ERROR — failed to move ${ticket_file} to done/" >&2
    else
      echo "Reconciler: ${ticket_file} -> done (cc=approved, cx=approved)"
      _git_finalize "approved" "${ticket_id}"
    fi

  elif (( round + 1 >= max_rounds )); then
    _update_verdict "$ticket_file" "escalated" "$ticket_id" "$round"
    mv -n "$src" ".ct2/escalated/${ticket_file}" 2>/dev/null
    if [[ -f "$src" ]]; then
      echo "Reconciler: ERROR — failed to move ${ticket_file} to escalated/" >&2
    else
      echo "Reconciler: ${ticket_file} -> escalated (max rounds)"
      _send_escalation "${ticket_file}" "${round}" "${max_rounds}"
      _git_finalize "escalated" "${ticket_id}"
    fi

  else
    _update_verdict "$ticket_file" "rejected" "$ticket_id" "$round"
    mv -n "$src" ".ct2/rejected/${ticket_file}" 2>/dev/null
    if [[ -f "$src" ]]; then
      echo "Reconciler: ERROR — failed to move ${ticket_file} to rejected/" >&2
    else
      echo "Reconciler: ${ticket_file} -> rejected (cc=${cc_v}, cx=${cx_v})"
      _git_finalize "rejected" "${ticket_id}"
    fi
  fi

  rm -f "$lockfile"
}
```

## _git_finalize

Thin wrapper around `ct2-git-finalize` that makes the call explicitly fail-soft:
the reconciler must never block on git/PR failures, because the ticket state
has already advanced by the time this is called.

```bash
_git_finalize() {
  local verdict="$1" ticket_id="$2"
  if command -v ct2-git-finalize &>/dev/null; then
    ct2-git-finalize "$verdict" "$ticket_id" 2>&1 | sed 's/^/  /' || true
  fi
}
```

## _update_verdict

Frontmatter rewrite is delegated to the shared helper `bin/_ct2_update_verdict.py`
so both reconcilers (lens-cc and lens-cx) produce
identical output. Any logic change to ticket frontmatter mutation must happen in
the Python helper only — the previous per-reconciler Python heredocs drifted and
silently broke the `sidecar:` nested key (the regex could not span the
intermediate `status:` line).

```bash
_update_verdict() {
  local ticket_file="$1" verdict="$2" ticket_id="$3" round="$4"
  "${HOME}/.ct2/bin/_ct2_update_verdict.py" \
    ".ct2/in-review/${ticket_file}" \
    "$verdict" \
    ".ct2/reviews/${ticket_id}-cc-r${round}.md" \
    ".ct2/reviews/${ticket_id}-cx-r${round}.md"
}
```

## _send_escalation

```bash
_send_escalation() {
  local ticket="$1" round="$2" max="$3"
  local actor="${CT2_RECONCILER_ACTOR:-ct2-lens-cc}"
  local ts; ts=$(date -u +%Y%m%dT%H%M%SZ)
  local uid
  uid=$(uuidgen 2>/dev/null | tr -d '-' | head -c 8 || true)
  [[ -z "$uid" ]] && uid=$(od -An -tx1 -N4 /dev/urandom 2>/dev/null | tr -d ' \n' || true)
  [[ -z "$uid" ]] && uid=$(head -c 8 /dev/urandom | xxd -p | head -c 8 || true)
  local msgid="msg-${ts}-$$-${uid}"
  local tmp; tmp=$(mktemp ".ct2/.tmp/${msgid}-XXXXXX")
  cat > "$tmp" <<MSGEOF
---
id: $msgid
from: $actor
to: ct2-helm
type: escalation
ticket: $ticket
timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)
---

## Subject
Ticket ${ticket} — Circuit Breaker Triggered (max_review_rounds=${max})

## Body
Ticket ${ticket} failed to pass review after ${max} rounds.
Please inspect the ticket manually and either revise requirements or close it.
MSGEOF
  mv -n "$tmp" ".ct2/inbox/ct2-helm/${msgid}.md" 2>/dev/null
  if [[ -f "$tmp" ]]; then rm -f "$tmp"; echo "ERROR: escalation message send failed" >&2; fi
}
```
