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

# Per-AC grade grammar in `## Acceptance Criteria Check` (spec/sidecar-format.md):
#   - AC{n}: (pass|fail) — {reason}   [optional (evidence: {claim-id})]
# AC_GRADE_RE captures a clean grade; AC_LINE_RE catches a line that looks like
# an AC grade but does not parse (warn-only, never wedges a ticket).
AC_GRADE_RE = re.compile(r"^-\s+AC(\d+):\s*(pass|fail)\b", re.IGNORECASE)
AC_LINE_RE = re.compile(r"^-\s+AC(\d+):", re.IGNORECASE)


def ticket_id_of(expected_ticket: str) -> str:
    stem = expected_ticket[:-3] if expected_ticket.endswith(".md") else expected_ticket
    return stem.split("-", 1)[0]


def accepted_ticket_values(expected_ticket: str) -> set[str]:
    stem = expected_ticket[:-3] if expected_ticket.endswith(".md") else expected_ticket
    return {ticket_id_of(expected_ticket), stem, f"{stem}.md"}


def section_body(content: str, title: str) -> str:
    match = re.search(rf"^##\s+{re.escape(title)}\s*$", content, re.MULTILINE)
    if not match:
        return ""
    return re.split(r"\n##\s+", content[match.end():], maxsplit=1)[0]


def sealed_ac_count(sidecar_path: Path, ticket_id: str) -> int | None:
    """Best-effort count of AC checkboxes in the sealed baseline, for the
    warn-only grade-count check. None when no snapshot exists (legacy ticket)."""
    snapshot = sidecar_path.parent.parent / "reviews" / f"{ticket_id}-sealed.md"
    try:
        text = snapshot.read_text(encoding="utf-8")
    except OSError:
        return None
    return len(re.findall(r"^-\s+\[[ xX]\]", section_body(text, "Acceptance Criteria"), re.MULTILINE))


def grade_ac_check(content: str) -> tuple[list[str], int, list[str]]:
    """Parse the `## Acceptance Criteria Check` section. Returns
    (fail_lines, parsed_grade_count, unparseable_ac_lines)."""
    fail_lines: list[str] = []
    parsed = 0
    unparseable: list[str] = []
    for raw in section_body(content, "Acceptance Criteria Check").splitlines():
        line = raw.strip()
        grade = AC_GRADE_RE.match(line)
        if grade:
            parsed += 1
            if grade.group(2).lower() == "fail":
                fail_lines.append(line)
        elif AC_LINE_RE.match(line):
            unparseable.append(line)
    return fail_lines, parsed, unparseable


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

    fail_lines, parsed_grades, unparseable = grade_ac_check(content)

    # HARD coherence rule — the single carve-out to "the reconciler does not
    # parse the body": a sidecar with verdict: approved that grades any AC as
    # `fail` is internally contradictory and invalid. This is a validity gate,
    # not a verdict input — `verdict` remains the only state-moving field, and
    # the rule fires only on lines that already parse cleanly.
    if fm.get("verdict") == "approved" and fail_lines:
        errors.append("verdict is approved but the body grades an AC as fail: " + "; ".join(fail_lines))

    # WARN-ONLY (never wedges the ticket): AC-grade-looking lines that do not
    # parse, and a graded-AC count that differs from the sealed baseline. The
    # count check only fires once the reviewer is actually using the grammar.
    warnings: list[str] = [
        f"unparseable AC grade line (expected `- AC{{n}}: pass|fail`): {line}" for line in unparseable
    ]
    if parsed_grades:
        baseline_count = sealed_ac_count(path, ticket_id_of(expected_ticket))
        if baseline_count is not None and parsed_grades != baseline_count:
            warnings.append(f"graded {parsed_grades} ACs but the sealed baseline has {baseline_count} AC checkbox(es)")
    for warning in warnings:
        print(f"sidecar warning: {warning}", file=sys.stderr)

    if errors:
        print("invalid sidecar:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
