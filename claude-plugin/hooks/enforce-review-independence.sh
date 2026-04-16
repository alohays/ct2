#!/usr/bin/env bash
# CT2 Hook: Reviewer Independence Guard
# Event: PreToolUse on Read
# Prevents lens-cc from reading cx sidecars (and vice versa) before
# writing their own. This enforces the independence assumption that
# makes dual-review meaningful — without it, anchoring bias defeats
# the purpose of having two independent reviewers.
set -euo pipefail

INPUT=$(cat)
CT2="${CT2_DIR:-.ct2}"

# ── Parse hook input ──────────────────────────────────────────────────────────
eval "$(python3 -c "
import json, sys, shlex
d = json.load(sys.stdin)
ti = d.get('tool_input', {})
print(f'FILE={shlex.quote(ti.get(\"file_path\", \"\"))}')
print(f'CWD={shlex.quote(d.get(\"cwd\", \"\"))}')
" <<< "$INPUT" 2>/dev/null)" || true
: "${FILE:=}" "${CWD:=}"

# ── Determine role ────────────────────────────────────────────────────────────
ROLE="${CT2_ROLE:-}"
if [ -z "$ROLE" ] && [ -f "${CT2}/.meta/ct2-active-role" ]; then
  ROLE=$(cat "${CT2}/.meta/ct2-active-role" 2>/dev/null || true)
fi

# Only applies to lens roles
case "$ROLE" in
  lens-cc|lens-cx) ;;
  *) exit 0 ;;
esac

# ── Normalize path ────────────────────────────────────────────────────────────
if [ -z "$FILE" ]; then
  exit 0
fi
if [[ "$FILE" == /* ]]; then
  FILE="${FILE#${CWD}/}"
fi

# ── Independence check ────────────────────────────────────────────────────────
# Determine which partner suffix to watch and own suffix
if [ "$ROLE" = "lens-cc" ]; then
  PARTNER="-cx-r"
  OWN="-cc-r"
else
  PARTNER="-cc-r"
  OWN="-cx-r"
fi

# Is the agent reading a partner's sidecar?
if [[ "$FILE" == "${CT2}"/reviews/*${PARTNER}* ]]; then
  BASENAME=$(basename "$FILE" .md)
  # Extract ticket_id (leading digits) and round (trailing r{N})
  TICKET_ID=$(echo "$BASENAME" | grep -oE '^[0-9]+' || true)
  ROUND=$(echo "$BASENAME" | grep -oE 'r[0-9]+$' | sed 's/r//' || true)

  if [ -n "$TICKET_ID" ] && [ -n "$ROUND" ]; then
    OWN_SIDECAR="${CT2}/reviews/${TICKET_ID}${OWN}${ROUND}.md"
    if [ ! -f "$OWN_SIDECAR" ]; then
      echo "ct2-guard [$ROLE]: independence violation — cannot read partner's sidecar before writing your own. Write ${OWN_SIDECAR} first." >&2
      exit 2
    fi
    # Own sidecar exists → reading partner is allowed (reconciler phase)
  fi
fi

exit 0
