#!/usr/bin/env bash
# CT2 Hook: Role-Based Write Access Guard
# Event: PreToolUse on Edit|Write|Bash
# Enforces the access matrix defined in each role's SKILL.md.
# Blocks writes to .ct2/ paths that violate the current role's permissions.
set -euo pipefail

INPUT=$(cat)
CT2="${CT2_DIR:-.ct2}"

# ── Parse hook input ──────────────────────────────────────────────────────────
eval "$(python3 -c "
import json, sys, shlex
d = json.load(sys.stdin)
tool = d.get('tool_name', '')
ti = d.get('tool_input', {})
print(f'TOOL={shlex.quote(tool)}')
print(f'FILE={shlex.quote(ti.get(\"file_path\", \"\"))}')
print(f'CMD={shlex.quote(ti.get(\"command\", \"\"))}')
print(f'CWD={shlex.quote(d.get(\"cwd\", \"\"))}')
" <<< "$INPUT" 2>/dev/null)" || true
: "${TOOL:=}" "${FILE:=}" "${CMD:=}" "${CWD:=}"

# ── Determine role ────────────────────────────────────────────────────────────
ROLE="${CT2_ROLE:-}"
if [ -z "$ROLE" ] && [ -f "${CT2}/.meta/ct2-active-role" ]; then
  ROLE=$(cat "${CT2}/.meta/ct2-active-role" 2>/dev/null || true)
fi
# Unknown role → fail-open (allow)
[ -z "$ROLE" ] && exit 0

# ── Normalize file path to relative ──────────────────────────────────────────
if [ -n "$FILE" ] && [[ "$FILE" == /* ]]; then
  FILE="${FILE#${CWD}/}"
fi

deny() {
  echo "ct2-guard [$ROLE]: $1" >&2
  exit 2
}

state_path_re="${CT2}/(draft|backlog|in-progress|in-review|rejected|escalated|done)/"

# ── Edit / Write guard ────────────────────────────────────────────────────────
if { [ "$TOOL" = "Edit" ] || [ "$TOOL" = "Write" ]; } && [ -n "$FILE" ]; then
  if [[ "$FILE" == "${CT2}"/reviews/*.md && -e "$FILE" ]]; then
    deny "cannot overwrite existing review sidecar (sidecars are immutable)"
  fi
  case "$ROLE" in
    forge)
      [[ "$FILE" == "${CT2}"/reviews/* ]]   && deny "cannot write to reviews/ (verdicts are read-only for forge)"
      [[ "$FILE" == "${CT2}"/done/* ]]       && deny "cannot write to done/ (immutable terminal state)"
      [[ "$FILE" == "${CT2}"/draft/* ]]      && deny "cannot write to draft/ (helm's domain)"
      [[ "$FILE" == "${CT2}"/escalated/* ]]  && deny "cannot write to escalated/ (reconciler's domain)"
      ;;
    helm)
      [[ "$FILE" == "${CT2}"/reviews/* ]]      && deny "cannot write to reviews/ (lens's domain)"
      [[ "$FILE" == "${CT2}"/done/* ]]         && deny "cannot write to done/ (immutable)"
      [[ "$FILE" == "${CT2}"/in-progress/* ]]  && deny "cannot write to in-progress/ (forge's domain)"
      [[ "$FILE" == "${CT2}"/in-review/* ]]    && deny "cannot write to in-review/ (lens's domain)"
      ;;
    lens-cc)
      [[ "$FILE" == "${CT2}"/in-review/* ]]    && deny "cannot modify in-review/ tickets (read-only for reviewers)"
      [[ "$FILE" == "${CT2}"/in-progress/* ]]  && deny "cannot write to in-progress/ (forge's domain)"
      [[ "$FILE" == "${CT2}"/draft/* ]]        && deny "cannot write to draft/ (helm's domain)"
      [[ "$FILE" == "${CT2}"/backlog/* ]]      && deny "cannot write to backlog/ (helm's domain)"
      [[ "$FILE" == "${CT2}"/reviews/*-cx-* ]] && deny "cannot write cx sidecars (only cc)"
      ;;
    lens-cx)
      [[ "$FILE" == "${CT2}"/in-review/* ]]    && deny "cannot modify in-review/ tickets (read-only for reviewers)"
      [[ "$FILE" == "${CT2}"/in-progress/* ]]  && deny "cannot write to in-progress/ (forge's domain)"
      [[ "$FILE" == "${CT2}"/draft/* ]]        && deny "cannot write to draft/ (helm's domain)"
      [[ "$FILE" == "${CT2}"/backlog/* ]]      && deny "cannot write to backlog/ (helm's domain)"
      [[ "$FILE" == "${CT2}"/reviews/*-cc-* ]] && deny "cannot write cc sidecars (only cx)"
      ;;
  esac
fi

# ── Bash guard (best-effort write detection) ──────────────────────────────────
# Catches obvious patterns: redirect (>), mv, cp targeting protected paths.
# Not exhaustive — defense-in-depth layer, not airtight.
if [ "$TOOL" = "Bash" ] && [ -n "$CMD" ]; then
  if echo "$CMD" | grep -qE "\bcp\b" && echo "$CMD" | grep -qE "$state_path_re"; then
    deny "state transitions must use mv, never cp"
  fi
  if echo "$CMD" | grep -qE "(>|>>)[[:space:]]*['\"]?${CT2}/reviews/|\\btee\\b.*${CT2}/reviews/"; then
    deny "write review sidecars through .ct2/.tmp/ then mv; do not redirect directly into reviews/"
  fi

  PROTECTED=()
  case "$ROLE" in
    forge)   PROTECTED=("${CT2}/reviews/" "${CT2}/done/" "${CT2}/draft/" "${CT2}/escalated/") ;;
    helm)    PROTECTED=("${CT2}/reviews/" "${CT2}/done/" "${CT2}/in-progress/" "${CT2}/in-review/") ;;
    # lens: in-review/ excluded from Bash guard — reconciler legitimately runs
    # "mv .ct2/in-review/X .ct2/done/X" where in-review/ is the SOURCE.
    # Edit/Write guard still blocks lens from modifying in-review/ files.
    lens-cc) PROTECTED=("${CT2}/in-progress/" "${CT2}/draft/" "${CT2}/backlog/") ;;
    lens-cx) PROTECTED=("${CT2}/in-progress/" "${CT2}/draft/" "${CT2}/backlog/") ;;
  esac

  for path in "${PROTECTED[@]}"; do
    if echo "$CMD" | grep -qF "$path"; then
      if echo "$CMD" | grep -qE '(>|>>|\bmv\b|\bcp\b|\btee\b)'; then
        deny "bash command appears to write to protected path: $path"
      fi
    fi
  done

  # Cross-sidecar check for lens roles
  if [ "$ROLE" = "lens-cc" ] && echo "$CMD" | grep -qE '(>|>>|\bmv\b|\bcp\b)' && echo "$CMD" | grep -qF "${CT2}/reviews/" && echo "$CMD" | grep -qE '\-cx\-'; then
    deny "bash command writes cx sidecar (only cc allowed)"
  fi
  if [ "$ROLE" = "lens-cx" ] && echo "$CMD" | grep -qE '(>|>>|\bmv\b|\bcp\b)' && echo "$CMD" | grep -qF "${CT2}/reviews/" && echo "$CMD" | grep -qE '\-cc\-'; then
    deny "bash command writes cc sidecar (only cx allowed)"
  fi
fi

exit 0
