"""Helpers for immutable sealed ticket baselines."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from _ct2_vao import read_frontmatter, ticket_id_from_name


SECTION_TITLES = ("Requirements", "Constraints", "Acceptance Criteria")
HASH_KEYS = {
    "Requirements": "requirements-sha256",
    "Constraints": "constraints-sha256",
    "Acceptance Criteria": "acceptance-criteria-sha256",
}

# `## Verification` is sealed as a *conditional* fourth section: it is hashed
# only when the ticket carries it, and a snapshot records its hash key only when
# the sealed ticket carried it. The drift rule is "absent-in-both = ok" so the
# millions of legacy baselines sealed before this section existed never flag
# drift, while one-sided presence (added or removed after seal) is caught.
VERIFICATION_TITLE = "Verification"
VERIFICATION_HASH_KEY = "verification-sha256"
RECOGNIZED_TITLES = SECTION_TITLES + (VERIFICATION_TITLE,)


VERIFICATION_BINDING_RE = re.compile(r"^-\s+AC(\d+):\s*`([^`]+)`\s*$")


def verification_lines(section: str):
    """Yield (line, regex-match-or-None) for each non-blank, non-comment line of
    a ## Verification section, so callers can validate (seal gate) or extract
    (ct2-ac-verify) from one place."""
    for raw in section.splitlines():
        line = raw.strip()
        if not line or line.startswith("<!--"):
            continue
        yield line, VERIFICATION_BINDING_RE.match(line)


def parse_verification_bindings(section: str) -> list[tuple[int, str]]:
    """Extract well-formed ``(ac_ordinal, command)`` bindings from a
    ## Verification section, skipping malformed lines (their rejection is the
    seal gate's job, not the runner's)."""
    bindings: list[tuple[int, str]] = []
    for _line, match in verification_lines(section):
        if match:
            command = match.group(2).strip()
            if command:
                bindings.append((int(match.group(1)), command))
    return bindings


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_section(text: str) -> str:
    lines = []
    for line in text.strip().splitlines():
        normalized = re.sub(r"^(\s*-\s*)\[[ xX]\]", r"\1[ ]", line.rstrip())
        lines.append(normalized)
    return "\n".join(lines).strip() + "\n"


def section_hash(text: str) -> str:
    return hashlib.sha256(normalize_section(text).encode("utf-8")).hexdigest()


def extract_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        if title not in RECOGNIZED_TITLES:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[title] = text[start:end].strip("\n")
    return sections


def ticket_hashes(ticket_path: Path) -> dict[str, str]:
    sections = extract_sections(ticket_path.read_text(encoding="utf-8"))
    hashes = {HASH_KEYS[title]: section_hash(sections.get(title, "")) for title in SECTION_TITLES}
    # Conditional: only present when the ticket actually carries the section.
    if VERIFICATION_TITLE in sections:
        hashes[VERIFICATION_HASH_KEY] = section_hash(sections[VERIFICATION_TITLE])
    return hashes


def sealed_snapshot_name(ticket_path: Path) -> str:
    return f"{ticket_id_from_name(ticket_path)}-sealed.md"


def write_snapshot(ticket_path: Path, dest: Path) -> None:
    text = ticket_path.read_text(encoding="utf-8")
    sections = extract_sections(text)
    hashes = {HASH_KEYS[title]: section_hash(sections.get(title, "")) for title in SECTION_TITLES}
    titles = list(SECTION_TITLES)
    if VERIFICATION_TITLE in sections:
        hashes[VERIFICATION_HASH_KEY] = section_hash(sections[VERIFICATION_TITLE])
        titles.append(VERIFICATION_TITLE)
    fm = read_frontmatter(ticket_path)
    ticket_stem = ticket_path.stem
    body = [
        "---",
        f"ticket: {ticket_stem}",
        f"timestamp: {now()}",
        f"source-sealed: {fm.get('sealed', 'pending')}",
    ]
    for key, value in hashes.items():
        body.append(f"{key}: {value}")
    body.append("---\n")
    for title in titles:
        body.append(f"## {title}\n")
        body.append((sections.get(title, "")).strip() + "\n")
    dest.write_text("\n".join(body), encoding="utf-8")


def snapshot_hashes(snapshot_path: Path) -> dict[str, str]:
    fm = read_frontmatter(snapshot_path)
    hashes = {key: str(fm.get(key, "")) for key in HASH_KEYS.values()}
    # Conditional: only present when the snapshot was sealed with the section.
    if fm.get(VERIFICATION_HASH_KEY) is not None:
        hashes[VERIFICATION_HASH_KEY] = str(fm.get(VERIFICATION_HASH_KEY))
    return hashes


def _compare_keys(live: dict[str, str], sealed: dict[str, str]) -> list[str]:
    """Keys to compare: the three required, plus Verification only when present
    in the ticket or the snapshot. Absent-in-both = no Verification check."""
    keys = list(HASH_KEYS.values())
    if VERIFICATION_HASH_KEY in live or VERIFICATION_HASH_KEY in sealed:
        keys.append(VERIFICATION_HASH_KEY)
    return [key for key in keys if live.get(key) != sealed.get(key)]


def compare_ticket_to_snapshot(ticket_path: Path, snapshot_path: Path) -> tuple[bool, dict[str, object]]:
    if not snapshot_path.exists():
        return False, {"snapshot": str(snapshot_path), "missing": True}
    live = ticket_hashes(ticket_path)
    sealed = snapshot_hashes(snapshot_path)
    mismatches = _compare_keys(live, sealed)
    return not mismatches, {"snapshot": str(snapshot_path), "mismatches": mismatches, "live": live, "sealed": sealed}


def baseline_status(ticket_path: Path, snapshot_path: Path) -> tuple[str, dict[str, object]]:
    """Classify a ticket vs its sealed baseline.

    Returns one of:
      - "ok":      baseline exists and live ticket matches.
      - "missing": baseline file does not exist (legacy ticket, needs backfill).
      - "drift":   baseline exists but live ticket section hashes diverge.
    """
    if not snapshot_path.exists():
        return "missing", {"snapshot": str(snapshot_path), "missing": True}
    live = ticket_hashes(ticket_path)
    sealed = snapshot_hashes(snapshot_path)
    mismatches = _compare_keys(live, sealed)
    if mismatches:
        return "drift", {"snapshot": str(snapshot_path), "mismatches": mismatches, "live": live, "sealed": sealed}
    return "ok", {"snapshot": str(snapshot_path)}
