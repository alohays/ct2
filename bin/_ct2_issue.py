#!/usr/bin/env python3
"""Shared GitHub Issue mirror helpers."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from _ct2_vao import atomic_write_json, atomic_write_text, now, read_frontmatter, relative_to_project, ticket_id_from_name


STATUS_BEGIN = "<!-- ct2-ticket-status:begin -->"
STATUS_END = "<!-- ct2-ticket-status:end -->"
COLUMN_STATES = ("draft", "backlog", "in-progress", "in-review", "rejected", "escalated", "done")
DEFAULT_CONFIG = {
    "enabled": "true",
    "issue_mirror": "pr-and-issue",
    "issue_labels_prefix": "ct2/",
    "issue_create_on_seal": "true",
    "pr_closes_issue": "true",
    "fallback_mode": "queue",
    "graphql_token_env": "GH_TOKEN",
}
LABEL_COLORS = {
    "draft": "6B7280",
    "backlog": "1D4ED8",
    "in-progress": "D97706",
    "in-review": "7C3AED",
    "rejected": "DC2626",
    "escalated": "B91C1C",
    "done": "15803D",
}


class IssueMirrorError(RuntimeError):
    pass


def is_null(value: object) -> bool:
    return str(value or "").strip() in {"", "null", "~", "None"}


def clean_scalar(value: object) -> str:
    return str(value or "").strip().strip('"')


def parse_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def read_config(ct2_dir: Path) -> dict[str, str]:
    harness = ct2_dir / "config" / "harness.yaml"
    try:
        text = harness.read_text(encoding="utf-8")
    except OSError:
        return {"enabled": "false"}
    match = re.search(r"^github_integration:\s*(.*?)$", text, re.MULTILINE)
    if not match:
        disabled = dict(DEFAULT_CONFIG)
        disabled["enabled"] = "false"
        return disabled
    config = dict(DEFAULT_CONFIG)
    inline = match.group(1).strip()
    if inline.startswith("{") and inline.endswith("}"):
        for item in inline[1:-1].split(","):
            if ":" not in item:
                continue
            key, value = item.split(":", 1)
            config[key.strip()] = value.strip().strip('"')
        return config
    block = text[match.end() :]
    for line in block.splitlines():
        if not line.strip():
            continue
        if re.match(r"^[A-Za-z0-9_-]+:", line):
            break
        item = re.match(r"^\s+([A-Za-z0-9_-]+):\s*(.*?)\s*(?:#.*)?$", line)
        if item:
            config[item.group(1)] = item.group(2).strip().strip('"')
    return config


def integration_enabled(ct2_dir: Path) -> bool:
    cfg = read_config(ct2_dir)
    return parse_bool(cfg.get("enabled", "false")) and cfg.get("issue_mirror", "pr-and-issue") != "off"


def label_for_state(ct2_dir: Path, state: str) -> str:
    prefix = read_config(ct2_dir).get("issue_labels_prefix", "ct2/")
    return f"{prefix}{state}"


def all_column_labels(ct2_dir: Path) -> list[str]:
    prefix = read_config(ct2_dir).get("issue_labels_prefix", "ct2/")
    return [f"{prefix}{state}" for state in COLUMN_STATES]


def run_gh(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    if shutil.which("gh") is None:
        raise IssueMirrorError("gh CLI unavailable")
    proc = subprocess.run(
        ["gh", *args],
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "gh command failed"
        raise IssueMirrorError(detail)
    return proc


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


def visible_checkbox_lines(text: str) -> list[str]:
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if re.match(r"^[-*]\s+\[[ xX]\]\s+", line):
            lines.append(re.sub(r"^[-*]\s+", "- ", line))
    return lines


def nested_reviewer_status(text: str, lens: str) -> str:
    match = re.search(rf"{re.escape(lens)}:\s*\n\s*status:\s*([^\n]+)", text)
    return clean_scalar(match.group(1)) if match else "pending"


def status_block(ticket: Path) -> str:
    text = ticket.read_text(encoding="utf-8")
    fm = read_frontmatter(ticket)
    body = strip_frontmatter(text)
    status = clean_scalar(fm.get("status", "unknown"))
    round_num = clean_scalar(fm.get("review-round", "0"))
    verdict = clean_scalar(fm.get("verdict", "pending"))
    branch = clean_scalar(fm.get("branch", ""))
    pr = clean_scalar(fm.get("pr", ""))
    acs = visible_checkbox_lines(section(body, "Acceptance Criteria"))
    if not acs:
        acs = ["- [ ] No acceptance criteria found in the ticket."]
    links = []
    if not is_null(branch):
        links.append(f"- Branch: `{branch}`")
    if not is_null(pr):
        links.append(f"- PR: {pr}")
    if not links:
        links.append("- PR: not opened yet")
    reviewers = [
        f"- lens-cc: {nested_reviewer_status(text, 'lens-claude')}",
        f"- lens-cx: {nested_reviewer_status(text, 'lens-codex')}",
    ]
    lines = [
        STATUS_BEGIN,
        f"**Status:** `{status}` - round {round_num} - verdict `{verdict}`",
        "",
        "**Links:**",
        *links,
        "",
        "**Reviewers:**",
        *reviewers,
        "",
        "**Acceptance Criteria:**",
        *acs,
        "",
        f"_Last synced: {now()}. Source ticket: `{ticket.name}`._",
        STATUS_END,
    ]
    return "\n".join(lines)


def replace_status_block(existing_body: str, block: str) -> str:
    pattern = re.compile(rf"{re.escape(STATUS_BEGIN)}.*?{re.escape(STATUS_END)}", re.DOTALL)
    if pattern.search(existing_body):
        return pattern.sub(block, existing_body, count=1)
    return f"{block}\n\n{existing_body}".rstrip() + "\n"


def rendered_issue_body(ticket: Path, existing_body: str | None = None) -> str:
    block = status_block(ticket)
    if existing_body is not None:
        return replace_status_block(existing_body, block)
    body = strip_frontmatter(ticket.read_text(encoding="utf-8")).strip()
    return f"{block}\n\n{body}\n"


def set_frontmatter_value(text: str, key: str, value: str) -> str:
    pattern = rf"^({re.escape(key)}:\s*).*$"
    if re.search(pattern, text, re.MULTILINE):
        return re.sub(pattern, rf"\g<1>{value}", text, count=1, flags=re.MULTILINE)
    if re.search(r"^pr:.*$", text, re.MULTILINE):
        return re.sub(r"^(pr:.*\n)", rf"\g<1>{key}: {value}\n", text, count=1, flags=re.MULTILINE)
    return re.sub(r"^(---\n)", rf"\g<1>{key}: {value}\n", text, count=1)


def update_ticket_issue_fields(ct2_dir: Path, ticket: Path, issue: str, issue_url: str, source: str) -> None:
    text = ticket.read_text(encoding="utf-8")
    text = set_frontmatter_value(text, "issue", issue)
    text = set_frontmatter_value(text, "issue-url", issue_url)
    text = set_frontmatter_value(text, "issue-source", source)
    atomic_write_text(ct2_dir, ticket, text, "issue-ticket-")


def issue_number_from_url(url: str) -> str:
    match = re.search(r"/issues/(\d+)(?:$|[?#])", url)
    if not match:
        raise IssueMirrorError(f"could not parse issue number from URL: {url}")
    return match.group(1)


def pending_path(ct2_dir: Path, ticket: Path) -> Path:
    return ct2_dir / ".meta" / f"{ticket_id_from_name(ticket)}.issue-mirror-pending.json"


def write_pending(ct2_dir: Path, ticket: Path, data: dict[str, Any]) -> None:
    payload = dict(data)
    payload["ticket"] = ticket.name
    payload["updated"] = now()
    atomic_write_json(ct2_dir, pending_path(ct2_dir, ticket), payload, "issue-pending-")


def clear_pending(ct2_dir: Path, ticket: Path) -> None:
    try:
        pending_path(ct2_dir, ticket).unlink()
    except FileNotFoundError:
        pass


def ticket_issue(fm: dict[str, Any]) -> str:
    issue = clean_scalar(fm.get("issue", ""))
    return "" if is_null(issue) else issue


def issue_view(project_dir: Path, issue: str) -> dict[str, Any]:
    proc = run_gh(["issue", "view", issue, "--json", "body,url,state,labels"], project_dir)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise IssueMirrorError(f"gh issue view returned invalid JSON: {exc}") from exc


def create_temp_body(ct2_dir: Path, body: str) -> str:
    (ct2_dir / ".tmp").mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="issue-body-", suffix=".md", dir=str(ct2_dir / ".tmp"))
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(body)
    return tmp_name


def ensure_labels(project_dir: Path, ct2_dir: Path) -> None:
    prefix = read_config(ct2_dir).get("issue_labels_prefix", "ct2/")
    for state in COLUMN_STATES:
        run_gh(
            [
                "label",
                "create",
                f"{prefix}{state}",
                "--color",
                LABEL_COLORS[state],
                "--description",
                f"CT2 {state} ticket state",
                "--force",
            ],
            project_dir,
            check=False,
        )


def rotate_label(project_dir: Path, ct2_dir: Path, issue: str, state: str) -> None:
    current = label_for_state(ct2_dir, state)
    for label in all_column_labels(ct2_dir):
        if label != current:
            run_gh(["issue", "edit", issue, "--remove-label", label], project_dir, check=False)
    run_gh(["issue", "edit", issue, "--add-label", current], project_dir)


def create_issue(project_dir: Path, ct2_dir: Path, ticket: Path, state: str) -> tuple[str, str]:
    ensure_labels(project_dir, ct2_dir)
    fm = read_frontmatter(ticket)
    title = clean_scalar(fm.get("title", ticket.stem)) or ticket.stem
    body_tmp = create_temp_body(ct2_dir, rendered_issue_body(ticket))
    try:
        proc = run_gh(
            ["issue", "create", "--title", title, "--body-file", body_tmp, "--label", label_for_state(ct2_dir, state)],
            project_dir,
        )
    finally:
        try:
            os.unlink(body_tmp)
        except FileNotFoundError:
            pass
    issue_url = proc.stdout.strip().splitlines()[-1].strip()
    issue = issue_number_from_url(issue_url)
    update_ticket_issue_fields(ct2_dir, ticket, issue, issue_url, "created")
    return issue, issue_url


def update_issue(project_dir: Path, ct2_dir: Path, ticket: Path, issue: str, close: bool = False, comment: str | None = None) -> None:
    ensure_labels(project_dir, ct2_dir)
    view = issue_view(project_dir, issue)
    body = rendered_issue_body(ticket, str(view.get("body", "") or ""))
    body_tmp = create_temp_body(ct2_dir, body)
    try:
        run_gh(["issue", "edit", issue, "--body-file", body_tmp], project_dir)
    finally:
        try:
            os.unlink(body_tmp)
        except FileNotFoundError:
            pass
    state = clean_scalar(read_frontmatter(ticket).get("status", "backlog"))
    if state in COLUMN_STATES:
        rotate_label(project_dir, ct2_dir, issue, state)
    if comment:
        run_gh(["issue", "comment", issue, "--body", comment], project_dir, check=False)
    if close:
        run_gh(["issue", "close", issue, "--comment", "CT2 marked this ticket done."], project_dir, check=False)


def mirror_ticket(
    project_dir: Path,
    ticket: Path,
    create: bool = False,
    close: bool = False,
    comment: str | None = None,
) -> dict[str, Any]:
    ct2_dir = project_dir / ".ct2"
    cfg = read_config(ct2_dir)
    if not integration_enabled(ct2_dir):
        return {"ok": True, "status": "disabled", "ticket": ticket.name}
    fm = read_frontmatter(ticket)
    if parse_bool(fm.get("private", "false")):
        return {"ok": True, "status": "private-skipped", "ticket": ticket.name}
    issue = ticket_issue(fm)
    state = clean_scalar(fm.get("status", "backlog"))
    pending = pending_path(ct2_dir, ticket)
    may_create = create or pending.exists()
    if not issue and not may_create:
        write_pending(ct2_dir, ticket, {"reason": "missing-issue", "create": False, "state": state})
        return {"ok": True, "status": "queued", "ticket": ticket.name}
    try:
        if not issue:
            if not parse_bool(cfg.get("issue_create_on_seal", "true")):
                return {"ok": True, "status": "create-disabled", "ticket": ticket.name}
            issue, _issue_url = create_issue(project_dir, ct2_dir, ticket, state)
        update_issue(project_dir, ct2_dir, ticket, issue, close=close, comment=comment)
        clear_pending(ct2_dir, ticket)
        return {"ok": True, "status": "mirrored", "ticket": ticket.name, "issue": issue}
    except Exception as exc:
        if cfg.get("fallback_mode", "queue") == "queue":
            write_pending(
                ct2_dir,
                ticket,
                {
                    "reason": "gh-failure",
                    "error": str(exc),
                    "create": bool(create or not issue),
                    "state": state,
                    "close": close,
                    "comment": comment,
                },
            )
            return {"ok": True, "status": "queued", "ticket": ticket.name, "error": str(exc)}
        raise


def find_ticket(ct2_dir: Path, arg: str) -> Path | None:
    candidate = Path(arg)
    if candidate.is_file():
        return candidate
    for state in COLUMN_STATES:
        root = ct2_dir / state
        if (root / arg).is_file():
            return root / arg
        if (root / f"{arg}.md").is_file():
            return root / f"{arg}.md"
        matches = sorted(root.glob(f"{arg}-*.md"))
        if len(matches) == 1:
            return matches[0]
    return None


def issue_labels(view: dict[str, Any]) -> set[str]:
    labels = view.get("labels") or []
    found = set()
    for label in labels:
        if isinstance(label, dict):
            name = label.get("name")
        else:
            name = str(label)
        if name:
            found.add(str(name))
    return found


def reconcile_findings(project_dir: Path, ticket: Path) -> list[dict[str, str]]:
    ct2_dir = project_dir / ".ct2"
    fm = read_frontmatter(ticket)
    issue = ticket_issue(fm)
    if not issue:
        return []
    try:
        view = issue_view(project_dir, issue)
    except Exception as exc:
        return [{"ticket": ticket.name, "issue": issue, "kind": "unavailable", "detail": str(exc)}]
    findings = []
    status = clean_scalar(fm.get("status", ""))
    issue_state = clean_scalar(view.get("state", ""))
    if issue_state.upper() == "CLOSED" and status not in {"done", "escalated"}:
        findings.append({"ticket": ticket.name, "issue": issue, "kind": "closed-externally", "detail": status})
    if status == "done" and issue_state.upper() != "CLOSED":
        findings.append({"ticket": ticket.name, "issue": issue, "kind": "ticket-done-issue-open", "detail": issue_state})
    expected = label_for_state(ct2_dir, status)
    labels = issue_labels(view)
    if status in COLUMN_STATES and expected not in labels:
        findings.append({"ticket": ticket.name, "issue": issue, "kind": "label-mismatch", "detail": expected})
    return findings


def rel_ticket(project_dir: Path, ticket: Path) -> str:
    return relative_to_project(project_dir, ticket)
