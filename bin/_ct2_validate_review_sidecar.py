#!/usr/bin/env python3
"""Validate a CT2 review sidecar before it becomes authoritative."""

import re
import sys
from pathlib import Path


REQUIRED_SECTIONS = (
    "## Summary",
    "## Acceptance Criteria Check",
    "## Issues Found",
    "## Recommendation",
)


def accepted_ticket_values(expected_ticket: str) -> set[str]:
    stem = expected_ticket[:-3] if expected_ticket.endswith(".md") else expected_ticket
    ticket_id = stem.split("-", 1)[0]
    return {ticket_id, stem, f"{stem}.md"}


def read_frontmatter(content: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        raise ValueError("missing YAML frontmatter")

    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        kv = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*?)\s*$", line)
        if kv:
            values[kv.group(1)] = kv.group(2).strip().strip('"')
    return values


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "Usage: _ct2_validate_review_sidecar.py <sidecar> <reviewer> <round> <ticket-stem>",
            file=sys.stderr,
        )
        return 2

    path = Path(sys.argv[1])
    expected_reviewer = sys.argv[2]
    expected_round = sys.argv[3]
    expected_ticket = sys.argv[4]

    try:
        content = path.read_text(encoding="utf-8")
        fm = read_frontmatter(content)
    except Exception as exc:
        print(f"invalid sidecar: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []
    accepted_tickets = accepted_ticket_values(expected_ticket)
    if fm.get("ticket") not in accepted_tickets:
        errors.append(f"ticket must be one of {sorted(accepted_tickets)!r}")
    if fm.get("reviewer") != expected_reviewer:
        errors.append(f"reviewer must be {expected_reviewer!r}")
    if fm.get("round") != expected_round:
        errors.append(f"round must be {expected_round!r}")
    if fm.get("verdict") not in {"approved", "rejected"}:
        errors.append("verdict must be approved or rejected")
    if not fm.get("timestamp"):
        errors.append("timestamp is required")

    for section in REQUIRED_SECTIONS:
        if section not in content:
            errors.append(f"missing section: {section}")

    if errors:
        print("invalid sidecar:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
