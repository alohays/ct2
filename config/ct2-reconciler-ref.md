# CT2 Reconciler Reference

This file contains the reconciler implementation loaded by ct2-lens-cc (and ct2-lens-cx) during Step 5 of the review loop. Load this file when both sidecars are present and reconciliation is needed.

## perform_reconcile

```bash
perform_reconcile() {
  local ticket="$1" ticket_id="$2" round="$3"

  # O_EXCL lockfile — exactly one reconciler instance wins
  local lockfile=".ct2/.meta/${ticket_id}-r${round}-reconcile.lock"
  ( set -C; echo "$$" > "$lockfile" ) 2>/dev/null || return 0

  local cc_v; cc_v=$(python3 -c "
import re; c=open('.ct2/reviews/${ticket_id}-cc-r${round}.md').read()
m=re.search(r'verdict:\s*(\w+)', c); print(m.group(1) if m else 'pending')")

  local cx_v; cx_v=$(python3 -c "
import re; c=open('.ct2/reviews/${ticket_id}-cx-r${round}.md').read()
m=re.search(r'verdict:\s*(\w+)', c); print(m.group(1) if m else 'pending')")

  local max_rounds; max_rounds=$(python3 -c "
import re
try:
    c=open('.ct2/config/harness.yaml').read()
    m=re.search(r'max_review_rounds:\s*(\d+)', c); print(m.group(1) if m else '3')
except: print('3')")

  local ticket_file; ticket_file=$(basename "$ticket")

  if [[ "$cc_v" == "approved" && "$cx_v" == "approved" ]]; then
    _update_verdict "$ticket_file" "approved" "$ticket_id" "$round"
    mv ".ct2/in-review/${ticket_file}" ".ct2/done/${ticket_file}"
    echo "Reconciler: ${ticket_file} -> done (cc=approved, cx=approved)"

  elif (( round + 1 >= max_rounds )); then
    _update_verdict "$ticket_file" "escalated" "$ticket_id" "$round"
    mv ".ct2/in-review/${ticket_file}" ".ct2/escalated/${ticket_file}"
    echo "Reconciler: ${ticket_file} -> escalated (max rounds)"
    _send_escalation "${ticket_file}" "${round}" "${max_rounds}"

  else
    _update_verdict "$ticket_file" "rejected" "$ticket_id" "$round"
    mv ".ct2/in-review/${ticket_file}" ".ct2/rejected/${ticket_file}"
    echo "Reconciler: ${ticket_file} -> rejected (cc=${cc_v}, cx=${cx_v})"
  fi

  rm -f "$lockfile"
}
```

## _update_verdict

```bash
_update_verdict() {
  local ticket_file="$1" verdict="$2" ticket_id="$3" round="$4"
  python3 - ".ct2/in-review/${ticket_file}" "$verdict" \
    ".ct2/reviews/${ticket_id}-cc-r${round}.md" \
    ".ct2/reviews/${ticket_id}-cx-r${round}.md" <<'PYEOF'
import sys, re
path, verdict, cc_sc, cx_sc = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
def get_v(p):
    try:
        m=re.search(r'verdict:\s*(\w+)', open(p).read())
        return m.group(1) if m else 'pending'
    except: return 'pending'
c = open(path).read()
c = re.sub(r'^(verdict:\s*).*$', rf'\g<1>{verdict}', c, flags=re.MULTILINE)
c = re.sub(r'(lens-claude:\n\s*status:\s*).*', rf'\g<1>{get_v(cc_sc)}', c)
c = re.sub(r'(lens-codex:\n\s*status:\s*).*', rf'\g<1>{get_v(cx_sc)}', c)
c = re.sub(r'^(updated:\s*).*$', rf'\g<1>{__import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}', c, flags=re.MULTILINE)
open(path, 'w').write(c)
PYEOF
}
```

## _send_escalation

```bash
_send_escalation() {
  local ticket="$1" round="$2" max="$3"
  local ts; ts=$(date -u +%Y%m%dT%H%M%S%3NZ 2>/dev/null || date -u +%Y%m%dT%H%M%SZ)
  local uid; uid=$(uuidgen 2>/dev/null | tr -d '-' | head -c 8 || \
                   head -c 8 /dev/urandom | xxd -p | head -c 8)
  local msgid="msg-${ts}-$$-${uid}"
  local tmp; tmp=$(mktemp ".ct2/.tmp/${msgid}.XXXXXX")
  cat > "$tmp" <<MSGEOF
---
id: $msgid
from: ct2-lens-cc
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
  mv -n "$tmp" ".ct2/inbox/ct2-helm/${msgid}.md"
}
```
