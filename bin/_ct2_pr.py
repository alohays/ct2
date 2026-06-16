#!/usr/bin/env python3
"""Shared GitHub PR review publication helpers."""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from _ct2_vao import atomic_write_json, atomic_write_text, now, read_frontmatter, ticket_id_from_name


DEFAULT_CONFIG = {
    "mode": "pr-and-sidecar",
    "inline_comments": "true",
    "approval_maps_to_pr_review": "true",
    "merge_ready_comment_marker": "<!-- ct2-merge-ready",
    "fallback_when_gh_unavailable": "sidecar-only",
}


class PrPublicationError(RuntimeError):
    pass


def clean_scalar(value: object) -> str:
    return str(value or "").strip().strip('"')


def is_null(value: object) -> bool:
    return clean_scalar(value) in {"", "null", "~", "None"}


def parse_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def read_config(ct2_dir: Path) -> dict[str, str]:
    harness = ct2_dir / "config" / "harness.yaml"
    try:
        text = harness.read_text(encoding="utf-8")
    except OSError:
        disabled = dict(DEFAULT_CONFIG)
        disabled["mode"] = "sidecar-only"
        return disabled
    match = re.search(r"^review_publication:[ \t]*(.*?)$", text, re.MULTILINE)
    if not match:
        disabled = dict(DEFAULT_CONFIG)
        disabled["mode"] = "sidecar-only"
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
    for line in text[match.end() :].splitlines():
        if not line.strip():
            continue
        if re.match(r"^[A-Za-z0-9_-]+:", line):
            break
        item = re.match(r"^\s+([A-Za-z0-9_-]+):\s*(.*?)\s*(?:#.*)?$", line)
        if item:
            config[item.group(1)] = item.group(2).strip().strip('"')
    return config


def publication_enabled(ct2_dir: Path) -> bool:
    return read_config(ct2_dir).get("mode", "sidecar-only") != "sidecar-only"


def run_gh(args: list[str], cwd: Path, check: bool = True, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    if shutil.which("gh") is None:
        raise PrPublicationError("gh CLI unavailable")
    proc = subprocess.run(
        ["gh", *args],
        cwd=str(cwd),
        text=True,
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "gh command failed"
        raise PrPublicationError(detail)
    return proc


def fallback_result(ct2_dir: Path, ticket: Path, error: str) -> dict[str, Any]:
    cfg = read_config(ct2_dir)
    if cfg.get("fallback_when_gh_unavailable", "sidecar-only") == "sidecar-only":
        return {"ok": True, "status": "sidecar-only", "ticket": ticket.name, "error": error}
    raise PrPublicationError(error)


def pr_selector(ticket: Path) -> str:
    pr = clean_scalar(read_frontmatter(ticket).get("pr", ""))
    return "" if is_null(pr) else pr


def pr_number(selector: str) -> str:
    match = re.search(r"/pull/(\d+)(?:$|[?#])", selector)
    if match:
        return match.group(1)
    if re.fullmatch(r"\d+", selector):
        return selector
    return selector


def repo_slug_from_pr(selector: str) -> str:
    match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/\d+", selector)
    if match:
        return f"{match.group('owner')}/{match.group('repo')}"
    raise PrPublicationError("pr must be a full github.com PR URL for inline review publication")


def sidecar_meta(sidecar: Path) -> dict[str, str]:
    fm = read_frontmatter(sidecar)
    return {key: clean_scalar(value) for key, value in fm.items()}


def sidecar_body(sidecar: Path) -> str:
    text = sidecar.read_text(encoding="utf-8")
    return re.sub(r"^---\n.*?\n---\n?", "", text, count=1, flags=re.DOTALL).strip()


def review_side(meta: dict[str, str]) -> str:
    reviewer = meta.get("reviewer", "")
    if reviewer.endswith("lens-cc"):
        return "lens-cc"
    if reviewer.endswith("lens-cx"):
        return "lens-cx"
    return reviewer or "lens"


def review_event(ct2_dir: Path, verdict: str) -> tuple[str, str]:
    cfg = read_config(ct2_dir)
    if verdict == "approved" and parse_bool(cfg.get("approval_maps_to_pr_review", "true")):
        return "APPROVE", "--approve"
    if verdict == "rejected":
        return "REQUEST_CHANGES", "--request-changes"
    return "COMMENT", "--comment"


def parse_inline_comments(text: str) -> list[dict[str, str]]:
    comments: list[dict[str, str]] = []
    blocks = re.split(r"(?m)^###\s+", text)
    for block in blocks[1:]:
        lines = block.splitlines()
        if not lines:
            continue
        title = lines[0].strip()
        file_path = ""
        line_num = ""
        body_lines: list[str] = []
        suggestion_lines: list[str] = []
        in_suggestion = False
        for raw_line in lines[1:]:
            if in_suggestion:
                if raw_line.startswith("  "):
                    suggestion_lines.append(raw_line[2:])
                    continue
                if not raw_line.strip():
                    suggestion_lines.append("")
                    continue
                in_suggestion = False
            file_match = re.match(r"^file:\s*(\S+)", raw_line)
            if file_match:
                file_path = file_match.group(1)
                continue
            line_match = re.match(r"^line:\s*(\d+)", raw_line)
            if line_match:
                line_num = line_match.group(1)
                continue
            if re.match(r"^suggestion:\s*\|\s*$", raw_line):
                in_suggestion = True
                continue
            if raw_line.startswith("## "):
                break
            body_lines.append(raw_line)
        if not file_path or not line_num:
            continue
        body = "\n".join(body_lines).strip()
        suggestion = "\n".join(suggestion_lines).rstrip("\n")
        comment_body = f"### {title}\n\n{body or title}".strip()
        if suggestion:
            comment_body += f"\n\n```suggestion\n{suggestion}\n```"
        comments.append({"path": file_path, "line": line_num, "body": comment_body})
    return comments


def review_body(sidecar: Path, meta: dict[str, str], comments: list[dict[str, str]]) -> str:
    side = review_side(meta)
    round_num = meta.get("round", "0")
    verdict = meta.get("verdict", "pending")
    lines = [
        f"## CT2 Review - {side}",
        f"<!-- ct2-review: {side} round={round_num} -->",
        "",
        f"verdict: {verdict}",
        f"inline-comments: {len(comments)}",
        "",
        sidecar_body(sidecar),
        "",
    ]
    return "\n".join(lines)


def temp_body(ct2_dir: Path, body: str) -> str:
    (ct2_dir / ".tmp").mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="pr-review-", suffix=".md", dir=str(ct2_dir / ".tmp"))
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(body)
    return tmp_name


def publish_inline_comments(project_dir: Path, selector: str, event: str, body: str, comments: list[dict[str, str]]) -> None:
    if not comments:
        return
    repo = repo_slug_from_pr(selector)
    number = pr_number(selector)
    payload = {
        "event": event,
        "body": body,
        "comments": [
            {"path": comment["path"], "line": int(comment["line"]), "body": comment["body"]}
            for comment in comments
        ],
    }
    run_gh(
        ["api", f"repos/{repo}/pulls/{number}/reviews", "--method", "POST", "--input", "-"],
        project_dir,
        input_text=json.dumps(payload),
    )


def review_marker(side: str, round_num: str) -> str:
    return f"<!-- ct2-review: {side} round={round_num} -->"


def reviews_for_pr(project_dir: Path, selector: str) -> list[dict[str, Any]]:
    proc = run_gh(["pr", "view", selector, "--json", "reviews"], project_dir)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise PrPublicationError(f"gh pr view returned invalid reviews JSON: {exc}") from exc
    reviews = data.get("reviews") or []
    return reviews if isinstance(reviews, list) else []


def review_already_present(project_dir: Path, selector: str, marker: str) -> bool:
    for review in reviews_for_pr(project_dir, selector):
        if marker in str(review.get("body", "")):
            return True
    return False


def publish_review(project_dir: Path, ticket: Path, sidecar: Path) -> dict[str, Any]:
    ct2_dir = project_dir / ".ct2"
    if not publication_enabled(ct2_dir):
        return {"ok": True, "status": "disabled", "ticket": ticket.name}
    selector = pr_selector(ticket)
    if not selector:
        return {"ok": True, "status": "no-pr", "ticket": ticket.name}
    meta = sidecar_meta(sidecar)
    comments = parse_inline_comments(sidecar_body(sidecar))
    event, flag = review_event(ct2_dir, meta.get("verdict", "pending"))
    body = review_body(sidecar, meta, comments)
    marker = review_marker(review_side(meta), meta.get("round", "0"))
    try:
        if review_already_present(project_dir, selector, marker):
            return {"ok": True, "status": "already-present", "ticket": ticket.name, "comments": len(comments), "event": event}
        if parse_bool(read_config(ct2_dir).get("inline_comments", "true")) and comments:
            publish_inline_comments(project_dir, selector, event, body, comments)
        else:
            body_tmp = temp_body(ct2_dir, body)
            try:
                run_gh(["pr", "review", selector, flag, "--body-file", body_tmp], project_dir)
            finally:
                try:
                    os.unlink(body_tmp)
                except FileNotFoundError:
                    pass
        return {"ok": True, "status": "published", "ticket": ticket.name, "comments": len(comments), "event": event}
    except Exception as exc:
        return fallback_result(ct2_dir, ticket, str(exc))


def merge_ready_marker(reviewer: str, round_num: str) -> str:
    return f"<!-- ct2-merge-ready: {reviewer} round={round_num} -->"


def comments_for_pr(project_dir: Path, selector: str) -> list[dict[str, Any]]:
    proc = run_gh(["pr", "view", selector, "--json", "comments"], project_dir)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise PrPublicationError(f"gh pr view returned invalid JSON: {exc}") from exc
    comments = data.get("comments") or []
    return comments if isinstance(comments, list) else []


def post_pr_comment(project_dir: Path, selector: str, body: str) -> None:
    run_gh(["pr", "comment", selector, "--body", body], project_dir)


def publish_merge_ready(project_dir: Path, ticket: Path, reviewer: str) -> dict[str, Any]:
    ct2_dir = project_dir / ".ct2"
    if not publication_enabled(ct2_dir):
        return {"ok": True, "status": "disabled", "ticket": ticket.name}
    selector = pr_selector(ticket)
    if not selector:
        return {"ok": True, "status": "no-pr", "ticket": ticket.name}
    round_num = clean_scalar(read_frontmatter(ticket).get("review-round", "0"))
    marker = merge_ready_marker(reviewer, round_num)
    try:
        for comment in comments_for_pr(project_dir, selector):
            if marker in str(comment.get("body", "")):
                return {"ok": True, "status": "already-present", "ticket": ticket.name, "reviewer": reviewer}
        body = "\n".join(
            [
                "## CT2 Merge-Ready Verdict",
                marker,
                "",
                "verdict: approved",
                "remaining-blockers: 0",
                "remaining-warnings: 0",
                f"round: {round_num}",
                "",
            ]
        )
        post_pr_comment(project_dir, selector, body)
        return {"ok": True, "status": "published", "ticket": ticket.name, "reviewer": reviewer}
    except Exception as exc:
        return fallback_result(ct2_dir, ticket, str(exc))


def publish_reconciler_summary(project_dir: Path, ticket: Path, verdict: str) -> dict[str, Any]:
    ct2_dir = project_dir / ".ct2"
    if not publication_enabled(ct2_dir):
        return {"ok": True, "status": "disabled", "ticket": ticket.name}
    selector = pr_selector(ticket)
    if not selector:
        return {"ok": True, "status": "no-pr", "ticket": ticket.name}
    try:
        body = "\n".join(
            [
                "<!-- ct2-reconciler -->",
                f"CT2 reconciler result: `{verdict}` for `{ticket.name}`.",
                "Both sidecar verdicts were evaluated before this comment was posted.",
                "",
            ]
        )
        for comment in comments_for_pr(project_dir, selector):
            existing = str(comment.get("body", ""))
            if "<!-- ct2-reconciler -->" in existing and f"`{verdict}`" in existing and f"`{ticket.name}`" in existing:
                return {"ok": True, "status": "already-present", "ticket": ticket.name, "verdict": verdict}
        post_pr_comment(project_dir, selector, body)
        return {"ok": True, "status": "published", "ticket": ticket.name, "verdict": verdict}
    except Exception as exc:
        return fallback_result(ct2_dir, ticket, str(exc))


def pr_review_comments(project_dir: Path, selector: str) -> list[dict[str, Any]]:
    repo = repo_slug_from_pr(selector)
    number = pr_number(selector)
    proc = run_gh(["api", f"repos/{repo}/pulls/{number}/comments", "--paginate"], project_dir)
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise PrPublicationError(f"gh api comments returned invalid JSON: {exc}") from exc
    return data if isinstance(data, list) else []


def addressed_path(ct2_dir: Path, ticket: Path) -> Path:
    return ct2_dir / ".meta" / f"{ticket_id_from_name(ticket)}.pr-addressed.json"


def todo_path(ct2_dir: Path, ticket: Path) -> Path:
    return ct2_dir / ".meta" / f"{ticket_id_from_name(ticket)}.pr-review-todo.md"


def load_addressed(ct2_dir: Path, ticket: Path) -> set[str]:
    path = addressed_path(ct2_dir, ticket)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    return {str(item) for item in data.get("addressed", [])}


def mark_addressed(project_dir: Path, ticket: Path, comment_ids: list[str]) -> dict[str, Any]:
    """Record one or more PR review comment ids as addressed so the next
    `build_response_todo` drops them. The previous wiring only ever rewrote the
    file with its prior contents — nothing added ids, so the TODO regenerated
    identically every round. This is the missing writer."""
    ct2_dir = project_dir / ".ct2"
    addressed = load_addressed(ct2_dir, ticket)
    added = [str(cid) for cid in comment_ids if str(cid) and str(cid) not in addressed]
    addressed.update(added)
    atomic_write_json(
        ct2_dir, addressed_path(ct2_dir, ticket), {"addressed": sorted(addressed), "updated": now()}, "pr-addressed-"
    )
    return {
        "ok": True,
        "status": "marked-addressed",
        "ticket": ticket.name,
        "added": added,
        "addressed_count": len(addressed),
    }


def render_response_todo(comments: list[dict[str, Any]]) -> str:
    lines = ["# CT2 PR Review TODO", ""]
    if not comments:
        lines.append("No unresolved review comments found.")
        lines.append("")
        return "\n".join(lines)
    for comment in comments:
        cid = str(comment.get("id") or comment.get("databaseId") or "?")
        path = comment.get("path") or "summary"
        line = comment.get("line") or comment.get("originalLine") or "-"
        body = html.escape(" ".join(str(comment.get("body", "")).replace("`", "").split())[:180], quote=False)
        lines.append(f"- [ ] comment {cid} `{path}:{line}` - {body}")
    lines.append("")
    return "\n".join(lines)


def build_response_todo(project_dir: Path, ticket: Path) -> dict[str, Any]:
    ct2_dir = project_dir / ".ct2"
    if not publication_enabled(ct2_dir):
        return {"ok": True, "status": "disabled", "ticket": ticket.name}
    selector = pr_selector(ticket)
    if not selector:
        return {"ok": True, "status": "no-pr", "ticket": ticket.name}
    try:
        addressed = load_addressed(ct2_dir, ticket)
        comments = [
            comment
            for comment in pr_review_comments(project_dir, selector)
            if str(comment.get("id") or comment.get("databaseId") or "") not in addressed
            and not comment.get("in_reply_to_id")
        ]
        atomic_write_text(ct2_dir, todo_path(ct2_dir, ticket), render_response_todo(comments), "pr-review-todo-")
        atomic_write_json(ct2_dir, addressed_path(ct2_dir, ticket), {"addressed": sorted(addressed), "updated": now()}, "pr-addressed-")
        return {"ok": True, "status": "todo-written", "ticket": ticket.name, "comments": len(comments)}
    except Exception as exc:
        return fallback_result(ct2_dir, ticket, str(exc))
