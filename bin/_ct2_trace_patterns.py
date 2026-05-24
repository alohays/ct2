#!/usr/bin/env python3
"""Shared host-repo trace hygiene patterns."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


PATTERN_VERSION = 1

SEVERITY_RANK = {"info": 1, "warn": 2, "error": 3}

COMMIT_TYPES = "feat|fix|docs|test|refactor|perf|build|ci|chore"

CATEGORY_DEFINITIONS: dict[str, dict[str, str]] = {
    "commit-scope-ticket-id": {
        "severity": "error",
        "surface": "commit",
        "message": "Commit subject exposes a CT2 ticket-id scope.",
        "fix": "Rewrite the commit subject without the t-NNN scope, or baseline accepted legacy history.",
    },
    "commit-trailer-ct2-path": {
        "severity": "error",
        "surface": "commit",
        "message": "Commit body exposes a .ct2 path.",
        "fix": "Remove the .ct2 trailer or replace it with a host-visible issue or PR reference.",
    },
    "commit-trailer-structured-uninvited": {
        "severity": "warn",
        "surface": "commit",
        "message": "Commit body contains CT2 structured decision trailers in a host repo.",
        "fix": "Keep structured trailers only when the host project explicitly wants them.",
    },
    "pr-title-ct2-token": {
        "severity": "error",
        "surface": "pull-request",
        "message": "PR title exposes a CT2 token.",
        "fix": "gh pr edit {pr} --title '<host-visible title>'",
    },
    "pr-body-branded-footer": {
        "severity": "error",
        "surface": "pull-request",
        "message": "PR body contains a CT2 branded footer.",
        "fix": "gh pr edit {pr} --body-file <clean-body.md>",
    },
    "pr-body-ct2-path": {
        "severity": "error",
        "surface": "pull-request",
        "message": "PR body exposes a .ct2 path.",
        "fix": "gh pr edit {pr} --body-file <clean-body.md>",
    },
    "branch-name-ticket-id": {
        "severity": "warn",
        "surface": "branch",
        "message": "Branch name appears to include a numeric CT2 ticket id.",
        "fix": "Rename the branch to a title-derived host-visible name.",
    },
    "tracked-ct2-dir": {
        "severity": "error",
        "surface": "tracked-file",
        "message": "A CT2 internal path is tracked by git.",
        "fix": "git rm -r --cached .ct2 && echo '.ct2/' >> .gitignore",
    },
    "tmp-leakage": {
        "severity": "error",
        "surface": "tracked-file",
        "message": "A CT2 temporary file appears to be tracked.",
        "fix": "Remove the temporary file from git and regenerate the artifact through CT2.",
    },
    "gitignore-missing-ct2": {
        "severity": "info",
        "surface": "ignore",
        "message": "Neither .gitignore nor .git/info/exclude lists .ct2/.",
        "fix": "echo '.ct2/' >> .gitignore",
    },
    "hooks-committed-without-policy": {
        "severity": "info",
        "surface": "tracked-file",
        "message": "A hook-like file is tracked without an ownership policy.",
        "fix": "Document hook ownership in OWNERS or .github/CODEOWNERS, or remove the hook.",
    },
    "agents-md-mentions-ct2-internal": {
        "severity": "warn",
        "surface": "tracked-file",
        "message": "AGENTS.md or CLAUDE.md mentions CT2 internal role names or paths.",
        "fix": "Move CT2-internal guidance into .ct2/config or document the host opt-in.",
    },
    "ci-workflow-references-ct2": {
        "severity": "warn",
        "surface": "tracked-file",
        "message": "Host CI workflow references CT2 commands.",
        "fix": "Remove CT2 from host CI unless the project explicitly opted in.",
    },
    "exception-review-thread-marker": {
        "severity": "info",
        "surface": "pull-request",
        "message": "PR body contains a contract-exempt CT2 review thread marker.",
        "fix": "Disable review publication if this audit trail should be invisible.",
    },
    "exception-issue-status-marker": {
        "severity": "info",
        "surface": "pull-request",
        "message": "PR body contains a contract-exempt CT2 issue status marker.",
        "fix": "Disable issue mirroring if this audit trail should be invisible.",
    },
}

COMMIT_SCOPE_TICKET_RE = re.compile(rf"\b(?:{COMMIT_TYPES})\(t-\d{{1,6}}\):")
COMMIT_CT2_PATH_RE = re.compile(
    r"(?im)(?:^Refs:\s+`?\.ct2/|^Ticket:\s+`?\.ct2/|\.ct2/(?:draft|backlog|in-progress|in-review|rejected|escalated|done|reviews|\.tmp)\b)"
)
STRUCTURED_TRAILER_RE = re.compile(r"(?m)^(?:Constraint|Rejected|Confidence|Scope-risk):\s+\S")
PR_TITLE_CT2_RE = re.compile(r"(?i)(?:\bct2\b|\.ct2/|\bt-\d{2,}\b)")
ROBOT_FACE = chr(0x1F916)
PR_BRANDED_FOOTER_RE = re.compile(
    r"(?i)(?:opened by ct2-(?:forge|helm|lens-[a-z]+|reconciler).*ct2-git-submit|"
    + re.escape(ROBOT_FACE)
    + r"\s*opened by)"
)
PR_CT2_PATH_RE = re.compile(r"(?im)(?:^Ticket:\s+`?\.ct2/|\.ct2/(?:draft|backlog|in-progress|in-review|rejected|escalated|done|reviews|\.tmp)\b)")
BRANCH_TICKET_ID_RE = re.compile(r"(?i)(?:^|/)(?:[a-z][a-z0-9]*[-/])?(?:t-)?\d{2,4}[-_][a-z0-9]")
TMP_LEAK_PATH_RE = re.compile(r"(?i)(?:^|/)(?:\.ct2/\.tmp/|\.tmp/.*(?:ct2|trace-hygiene)|.*(?:ct2-write|ct2-json|trace-hygiene)-.*)")
HOOK_PATH_RE = re.compile(
    r"(?i)(?:^|/)(?:\.githooks|\.github/hooks|hooks)/(?:pre-|post-|commit-msg|prepare-commit-msg|applypatch-msg|fsmonitor-watchman|pre-push|pre-commit|post-merge|post-checkout|[^/]+\.sh$)"
)
AGENT_INTERNAL_RE = re.compile(r"(?i)(?:\bct2-(?:forge|helm|lens-cc|lens-cx|reconciler|review-enter|git-submit)\b|\.ct2/)")
CI_CT2_REFERENCE_RE = re.compile(r"(?i)(?:\bbin/ct2-[a-z0-9-]+\b|\bct2-[a-z0-9-]+\b)")
REVIEW_THREAD_EXCEPTION_RE = re.compile(r"(?i)<!--\s*(?:ct2-review|ct2-merge-ready|ct2-reconciler)\b.*?-->", re.DOTALL)
ISSUE_STATUS_EXCEPTION_RE = re.compile(r"(?i)<!--\s*ct2-ticket-status:(?:begin|end)\s*-->", re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def hidden_ticket_comment(ticket_id: str) -> str:
    return f"<!-- ct2-ticket: {ticket_id} / pr-managed -->"


def visible_pr_text(text: str) -> str:
    """Return PR text with HTML comments removed for human-visible scans."""

    return HTML_COMMENT_RE.sub("", text)


def severity_at_or_above(severity: str, threshold: str) -> bool:
    return SEVERITY_RANK[severity] >= SEVERITY_RANK[threshold]


def format_fix(category: str, **values: object) -> str:
    template = CATEGORY_DEFINITIONS[category].get("fix", "")
    defaults = {"pr": "<number>", "path": "<path>", "ref": "<ref>", "branch": "<branch>"}
    defaults.update({key: str(value) for key, value in values.items() if value is not None})
    try:
        return template.format(**defaults)
    except KeyError:
        return template


def finding_fingerprint(finding: dict[str, Any]) -> str:
    parts = [
        str(finding.get("category", "")),
        str(finding.get("ref", "")),
        str(finding.get("path", "")),
        str(finding.get("line", "")),
        str(finding.get("match", "")),
    ]
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:16]


def baseline_fingerprints(path: str) -> set[str]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        rows = data.get("findings", [])
    else:
        rows = data
    fingerprints: set[str] = set()
    for row in rows:
        if isinstance(row, str):
            fingerprints.add(row)
        elif isinstance(row, dict):
            fingerprints.add(str(row.get("fingerprint") or finding_fingerprint(row)))
    return fingerprints
