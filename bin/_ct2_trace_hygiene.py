#!/usr/bin/env python3
"""Helpers for host-repo-clean git and PR artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from _ct2_vao import read_frontmatter, ticket_id_from_name


CLEAN_DEFAULTS = {
    "preset": "clean",
    "branch_naming": "title-slug",
    "branch_prefix_pattern": "{type}/{title-slug}",
    "commit_scope_style": "minimal",
    "commit_trailer_style": "minimal",
    "pr_body_footer": "none",
    "pr_body_ticket_link": "hidden-html",
}

LEGACY_DEFAULTS = {
    "preset": "legacy-branded",
    "branch_naming": "ticket-id",
    "branch_prefix_pattern": "feat/{ticket-stem}",
    "commit_scope_style": "ticket-id",
    "commit_trailer_style": "refs",
    "pr_body_footer": "branded",
    "pr_body_ticket_link": "visible",
}

COMMIT_TYPES = {"feat", "fix", "docs", "test", "refactor", "perf", "build", "ci", "chore"}
EMOJI_RE = re.compile(r"[\U00002600-\U000027BF\U00010000-\U0010ffff]")
CT2_ROLE_RE = re.compile(r"\bct2-(?:helm|forge|lens-cc|lens-cx|helm-auto-cx|reconcile)\b")
CT2_PATH_RE = re.compile(r"(?:^|\s)`?\.ct2/[^\s`)]*`?")
CT2_URL_RE = re.compile(r"https?://[^\s)]+ct2[^\s)]*", re.IGNORECASE)


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _parse_inline_mapping(value: str) -> dict[str, str]:
    value = value.strip()
    if not (value.startswith("{") and value.endswith("}")):
        return {}
    result: dict[str, str] = {}
    for part in value[1:-1].split(","):
        if ":" not in part:
            continue
        key, raw = part.split(":", 1)
        result[key.strip()] = _strip_quotes(raw.strip())
    return result


def trace_hygiene_config(ct2_dir: Path) -> dict[str, str]:
    harness = ct2_dir / "config" / "harness.yaml"
    try:
        text = harness.read_text(encoding="utf-8")
    except OSError:
        return dict(LEGACY_DEFAULTS)

    match = re.search(r"^trace_hygiene:\s*(.*?)$", text, re.MULTILINE)
    if not match:
        return dict(LEGACY_DEFAULTS)

    config = dict(CLEAN_DEFAULTS)
    inline = _parse_inline_mapping(match.group(1))
    if inline:
        config.update(inline)
    else:
        start = match.end()
        tail = text[start:]
        block_lines = []
        for line in tail.splitlines():
            if not line.strip():
                block_lines.append(line)
                continue
            if re.match(r"^[A-Za-z0-9_-]+:", line):
                break
            block_lines.append(line)
        for line in block_lines:
            item = re.match(r"^\s+([A-Za-z0-9_-]+):\s*(.*?)\s*(?:#.*)?$", line)
            if item:
                config[item.group(1)] = _strip_quotes(item.group(2))

    if config.get("preset") == "legacy-branded":
        legacy = dict(LEGACY_DEFAULTS)
        # Legacy mode intentionally restores the full legacy artifact shape; it
        # does not merge clean-only customization keys.
        legacy.update({k: v for k, v in config.items() if k == "preset"})
        return legacy
    return config


def slugify(value: str, fallback: str = "work") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or fallback


def title_type(title: str) -> str:
    prefix = title.split(":", 1)[0].strip().lower()
    return prefix if prefix in COMMIT_TYPES else "feat"


def title_slug(title: str, ticket_stem: str) -> str:
    cleaned = title
    if ":" in cleaned and title.split(":", 1)[0].strip().lower() in COMMIT_TYPES:
        cleaned = cleaned.split(":", 1)[1]
    fallback = re.sub(r"^\d+-", "", ticket_stem)
    return slugify(cleaned, fallback=fallback or "work")[:60].strip("-") or "work"


def proposed_branch(ticket_path: Path, ct2_dir: Path, ticket_stem: str) -> str:
    cfg = trace_hygiene_config(ct2_dir)
    fm = read_frontmatter(ticket_path)
    title = str(fm.get("title", "") or ticket_stem)
    ticket_id = ticket_id_from_name(ticket_path)
    values = {
        "type": title_type(title),
        "title-slug": title_slug(title, ticket_stem),
        "ticket-id": ticket_id,
        "ticket-stem": ticket_stem,
    }
    if cfg.get("branch_naming") == "ticket-id":
        pattern = cfg.get("branch_prefix_pattern") or "feat/{ticket-stem}"
    else:
        pattern = cfg.get("branch_prefix_pattern") or "{type}/{title-slug}"
    branch = pattern
    for key, value in values.items():
        branch = branch.replace("{" + key + "}", value)
    return re.sub(r"/{2,}", "/", branch.strip("/")) or f"feat/{values['title-slug']}"


def strip_frontmatter(text: str) -> str:
    return re.sub(r"^---\n.*?\n---\n?", "", text, count=1, flags=re.DOTALL)


def section(body: str, title: str) -> str:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", body, flags=re.MULTILINE))
    for index, match in enumerate(matches):
        if match.group(1).strip().lower() != title.lower():
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        return body[start:end].strip()
    return ""


def visible_lines(text: str) -> list[str]:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        lines.append(line)
    return lines


def bullet_text(line: str) -> str:
    line = re.sub(r"^[-*]\s+\[[ xX]\]\s*", "", line)
    line = re.sub(r"^[-*]\s+", "", line)
    return line.strip()


def sanitize_visible_text(line: str) -> str:
    line = EMOJI_RE.sub("", line)
    line = CT2_ROLE_RE.sub("", line)
    line = CT2_PATH_RE.sub(" ", line)
    line = CT2_URL_RE.sub("", line)
    line = re.sub(r"\bCT2\b", "", line)
    line = re.sub(r"\s{2,}", " ", line)
    return line.strip(" -")


def bullets_from_section(text: str, checked: bool = False) -> list[str]:
    prefix = "- [x] " if checked else "- "
    bullets = []
    for line in visible_lines(text):
        if not re.match(r"^[-*]\s+", line):
            continue
        item = sanitize_visible_text(bullet_text(line))
        if item:
            bullets.append(prefix + item)
    return bullets


def summary_from_context(context: str, title: str) -> str:
    paragraph = " ".join(sanitize_visible_text(line) for line in visible_lines(context))
    paragraph = re.sub(r"\s+", " ", paragraph).strip()
    return paragraph or title


def render_clean_pr_body(ticket_path: Path, ticket_file: str, cfg: dict[str, str]) -> str:
    text = ticket_path.read_text(encoding="utf-8")
    fm = read_frontmatter(ticket_path)
    title = str(fm.get("title", "") or Path(ticket_file).stem)
    body = strip_frontmatter(text)
    reqs = bullets_from_section(section(body, "Requirements"))
    acs = bullets_from_section(section(body, "Acceptance Criteria"), checked=True)
    if not reqs:
        reqs = ["- See commits for implementation details."]
    if not acs:
        acs = ["- [x] Implementation is ready for review."]
    ticket_id = ticket_id_from_name(ticket_path)
    parts = [
        summary_from_context(section(body, "Context"), title),
        "",
        "## What changed",
        "",
        *reqs,
        "",
        "## Acceptance criteria",
        "",
        *acs,
        "",
    ]
    if cfg.get("pr_body_ticket_link") != "none":
        parts.extend([f"<!-- ct2-ticket: {ticket_id} / pr-managed -->", ""])
    return "\n".join(parts)


def render_legacy_pr_body(ticket_path: Path, ticket_file: str) -> str:
    body = strip_frontmatter(ticket_path.read_text(encoding="utf-8")).strip()
    return (
        f"Ticket: `.ct2/in-review/{ticket_file}` (see CT2 kanban)\n\n"
        f"{body}\n\n"
        "---\n"
        "Opened by ct2-forge via ct2-git-submit.\n"
    )


def render_pr_body(ticket_path: Path, ct2_dir: Path, ticket_file: str) -> str:
    cfg = trace_hygiene_config(ct2_dir)
    if cfg.get("preset") == "legacy-branded":
        return render_legacy_pr_body(ticket_path, ticket_file)
    return render_clean_pr_body(ticket_path, ticket_file, cfg)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render CT2 host-repo trace hygiene artifacts")
    sub = parser.add_subparsers(dest="command", required=True)

    config = sub.add_parser("config")
    config.add_argument("--ct2-dir", required=True)

    branch = sub.add_parser("branch")
    branch.add_argument("--ticket", required=True)
    branch.add_argument("--ct2-dir", required=True)
    branch.add_argument("--ticket-stem", required=True)

    pr_body = sub.add_parser("pr-body")
    pr_body.add_argument("--ticket", required=True)
    pr_body.add_argument("--ct2-dir", required=True)
    pr_body.add_argument("--ticket-file", required=True)

    args = parser.parse_args()
    ct2_dir = Path(args.ct2_dir)
    if args.command == "config":
        print(json.dumps(trace_hygiene_config(ct2_dir), indent=2, sort_keys=True))
    elif args.command == "branch":
        print(proposed_branch(Path(args.ticket), ct2_dir, args.ticket_stem))
    elif args.command == "pr-body":
        print(render_pr_body(Path(args.ticket), ct2_dir, args.ticket_file), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
