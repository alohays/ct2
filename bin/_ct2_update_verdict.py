#!/usr/bin/env python3
# _ct2_update_verdict.py — Single source of truth for ticket frontmatter
# updates performed by the reconciler.
#
# Callers: ct2-lens-cx (TUI/daemon) and ct2-lens-cc (via reconciler-ref).
# Keeping this logic in one place prevents the regex drift we hit when each
# reconciler had its own copy (a subtle bug where the `sidecar:` nested key
# was never updated because the pattern could not span the intermediate
# `status:` line).
#
# Usage:
#   _ct2_update_verdict.py <ticket_path> <verdict> <cc_sidecar> <cx_sidecar>
#
# Where:
#   ticket_path   Absolute or project-relative path to the ticket currently in
#                 .ct2/in-review/. Frontmatter is rewritten in place.
#   verdict       approved | rejected | escalated (the ticket-level verdict)
#   cc_sidecar    Path to .ct2/reviews/{id}-cc-r{n}.md
#   cx_sidecar    Path to .ct2/reviews/{id}-cx-r{n}.md
#
# What gets written:
#   - top-level `verdict:`    <- argument
#   - top-level `updated:`    <- now (UTC, second precision)
#   - review-status.lens-claude.status   <- verdict field parsed from cc_sidecar
#   - review-status.lens-claude.sidecar  <- cc_sidecar path
#   - review-status.lens-codex.status    <- verdict field parsed from cx_sidecar
#   - review-status.lens-codex.sidecar   <- cx_sidecar path
#
# Exit codes:
#   0  success (frontmatter written)
#   1  argument error
#   2  ticket file missing or unparseable
import re
import sys
from datetime import datetime, timezone


def extract_verdict(path: str) -> str:
    try:
        with open(path) as f:
            m = re.search(r"verdict:\s*(\w+)", f.read())
        return m.group(1) if m else "pending"
    except OSError:
        return "pending"


def rewrite(ticket_path: str, verdict: str, cc_sidecar: str, cx_sidecar: str) -> None:
    with open(ticket_path) as f:
        c = f.read()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Top-level scalar fields — anchored to line start via re.MULTILINE.
    c = re.sub(r"^(verdict:\s*).*$", rf"\g<1>{verdict}", c, flags=re.MULTILINE)
    c = re.sub(r"^(updated:\s*).*$", rf"\g<1>{now}", c, flags=re.MULTILINE)

    cc_v = extract_verdict(cc_sidecar)
    cx_v = extract_verdict(cx_sidecar)

    # Nested review-status block.
    # Match the 2-line block (status + sidecar) under each lens in one pass so we
    # do not have to reason about the intermediate `status:` line separately —
    # that is the bug the previous per-key regex had.
    c = re.sub(
        r"(lens-claude:\s*\n\s*status:\s*)[^\n]*(\n\s*sidecar:\s*)[^\n]*",
        rf"\g<1>{cc_v}\g<2>{cc_sidecar}",
        c,
    )
    c = re.sub(
        r"(lens-codex:\s*\n\s*status:\s*)[^\n]*(\n\s*sidecar:\s*)[^\n]*",
        rf"\g<1>{cx_v}\g<2>{cx_sidecar}",
        c,
    )

    with open(ticket_path, "w") as f:
        f.write(c)


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "Usage: _ct2_update_verdict.py <ticket> <verdict> <cc_sidecar> <cx_sidecar>",
            file=sys.stderr,
        )
        return 1

    ticket, verdict, cc_sc, cx_sc = sys.argv[1:5]

    if verdict not in {"approved", "rejected", "escalated"}:
        print(f"_ct2_update_verdict: invalid verdict '{verdict}'", file=sys.stderr)
        return 1

    try:
        rewrite(ticket, verdict, cc_sc, cx_sc)
    except OSError as e:
        print(f"_ct2_update_verdict: {e}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
