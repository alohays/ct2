import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run_cmd(args, cwd, env=None):
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        [str(arg) for arg in args],
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
        env=merged,
    )


def sidecar(ticket, reviewer="ct2-lens-cx", verdict="approved"):
    return f"""---
ticket: "{ticket}"
reviewer: {reviewer}
round: 0
verdict: {verdict}
timestamp: 2026-05-24T00:00:00Z
---

## Summary
Approved fixture.

## Acceptance Criteria Check
- [x] Fixture is complete.

## Issues Found
(none)

## Recommendation
approved - fixture passes.
"""


def write_ticket(path, status="draft", issue="null"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
id: "001"
title: "Mirror GitHub issue"
status: {status}
priority: medium
created: 2026-05-24T00:00:00Z
updated: 2026-05-24T00:00:00Z
sealed: null
branch: feat/mirror-github-issue
pr: null
issue: {issue}
issue-url: null
issue-source: null
review-round: 0
duration-bounce-count: 0
total-attempts: 0
estimated-scope: small
touched-files:
  - README.md
review-status:
  lens-claude:
    status: pending
    sidecar: null
  lens-codex:
    status: pending
    sidecar: null
verdict: pending
---

## Requirements
- [ ] Mirror ticket state to GitHub.

## Constraints
- Use fail-soft GitHub commands.

## Context
GitHub users need a readable ticket mirror.

## Acceptance Criteria
- [ ] Issue labels match the CT2 state.
""",
        encoding="utf-8",
    )


class IssueMirrorTest(unittest.TestCase):
    maxDiff = None

    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        self.assertEqual(run_cmd(["git", "init"], project).returncode, 0)
        self.assertEqual(run_cmd(["git", "config", "user.name", "CT2 Test"], project).returncode, 0)
        self.assertEqual(run_cmd(["git", "config", "user.email", "ct2@example.invalid"], project).returncode, 0)
        (project / "README.md").write_text("# Host\n", encoding="utf-8")
        self.assertEqual(run_cmd(["git", "add", "README.md"], project).returncode, 0)
        self.assertEqual(run_cmd(["git", "commit", "-m", "init"], project).returncode, 0)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project], REPO_ROOT)
        self.assertEqual(init.returncode, 0, init.stderr)
        return project

    def install_fake_gh(self, project, failing=False, initial=None):
        fake_bin = project / "fake-bin"
        fake_bin.mkdir(exist_ok=True)
        state = project / "fake-gh-state.json"
        state.write_text(
            json.dumps(initial or {"next": 142, "issues": {}, "labels": [], "calls": []}),
            encoding="utf-8",
        )
        gh = fake_bin / "gh"
        if failing:
            gh.write_text("#!/usr/bin/env python3\nimport sys\nprint('gh unavailable', file=sys.stderr)\nsys.exit(1)\n", encoding="utf-8")
        else:
            gh.write_text(
                r'''#!/usr/bin/env python3
import json, os, sys

state_path = os.environ["FAKE_GH_STATE"]
with open(state_path, encoding="utf-8") as fh:
    state = json.load(fh)
args = sys.argv[1:]
state.setdefault("calls", []).append(args)

def save():
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, sort_keys=True)

def value_after(flag, default=""):
    if flag not in args:
        return default
    idx = args.index(flag)
    return args[idx + 1] if idx + 1 < len(args) else default

if args[:2] == ["label", "create"]:
    label = args[2]
    if label not in state.setdefault("labels", []):
        state["labels"].append(label)
    save()
    sys.exit(0)

if args[:2] == ["issue", "create"]:
    num = str(state.get("next", 142))
    state["next"] = int(num) + 1
    body_file = value_after("--body-file")
    label = value_after("--label")
    body = open(body_file, encoding="utf-8").read()
    url = f"https://github.com/example/repo/issues/{num}"
    state.setdefault("issues", {})[num] = {
        "number": num,
        "url": url,
        "title": value_after("--title"),
        "body": body,
        "state": "OPEN",
        "labels": [label] if label else [],
        "comments": [],
    }
    save()
    print(url)
    sys.exit(0)

if args[:2] == ["issue", "view"]:
    issue = args[2]
    item = state.setdefault("issues", {}).get(issue)
    if not item:
        print(f"issue {issue} missing", file=sys.stderr)
        save()
        sys.exit(1)
    labels = [{"name": label} for label in item.get("labels", [])]
    print(json.dumps({
        "title": item.get("title", ""),
        "body": item.get("body", ""),
        "number": int(issue),
        "url": item.get("url", f"https://github.com/example/repo/issues/{issue}"),
        "state": item.get("state", "OPEN"),
        "labels": labels,
    }))
    save()
    sys.exit(0)

if args[:2] == ["issue", "edit"]:
    issue = args[2]
    item = state.setdefault("issues", {}).setdefault(issue, {"labels": [], "comments": [], "state": "OPEN"})
    if "--body-file" in args:
        item["body"] = open(value_after("--body-file"), encoding="utf-8").read()
    if "--add-label" in args:
        label = value_after("--add-label")
        if label and label not in item.setdefault("labels", []):
            item["labels"].append(label)
    if "--remove-label" in args:
        label = value_after("--remove-label")
        item["labels"] = [existing for existing in item.get("labels", []) if existing != label]
    save()
    sys.exit(0)

if args[:2] == ["issue", "close"]:
    issue = args[2]
    item = state.setdefault("issues", {}).setdefault(issue, {"labels": [], "comments": []})
    item["state"] = "CLOSED"
    if "--comment" in args:
        item.setdefault("comments", []).append(value_after("--comment"))
    save()
    sys.exit(0)

if args[:2] == ["issue", "comment"]:
    issue = args[2]
    item = state.setdefault("issues", {}).setdefault(issue, {"labels": [], "comments": [], "state": "OPEN"})
    item.setdefault("comments", []).append(value_after("--body"))
    save()
    sys.exit(0)

print("unsupported gh call: " + " ".join(args), file=sys.stderr)
save()
sys.exit(1)
''',
                encoding="utf-8",
            )
        gh.chmod(0o755)
        env = {"PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}", "FAKE_GH_STATE": str(state)}
        return env, state

    def read_state(self, state):
        return json.loads(state.read_text(encoding="utf-8"))

    def test_issue_mirror_follows_ticket_lifecycle_and_is_idempotent(self):
        project = self.make_project()
        env, state_file = self.install_fake_gh(project)
        ticket = project / ".ct2" / "draft" / "001-mirror-github-issue.md"
        write_ticket(ticket)

        seal = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-seal", "001"], project, env=env)

        self.assertEqual(seal.returncode, 0, seal.stderr)
        backlog = project / ".ct2" / "backlog" / ticket.name
        self.assertIn("issue: 142", backlog.read_text(encoding="utf-8"))
        state = self.read_state(state_file)
        self.assertEqual(1, len(state["issues"]))
        self.assertIn("ct2/backlog", state["issues"]["142"]["labels"])
        self.assertIn("<!-- ct2-ticket-status:begin -->", state["issues"]["142"]["body"])

        for _ in range(2):
            mirror = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-issue-mirror", backlog, project, "--create"], project, env=env)
            self.assertEqual(mirror.returncode, 0, mirror.stderr)
        state = self.read_state(state_file)
        create_calls = [call for call in state["calls"] if call[:2] == ["issue", "create"]]
        self.assertEqual(1, len(create_calls))
        self.assertEqual(1, state["issues"]["142"]["body"].count("<!-- ct2-ticket-status:begin -->"))

        pickup = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pickup", project], REPO_ROOT, env=env)
        self.assertEqual(pickup.returncode, 0, pickup.stderr)
        self.assertEqual(["ct2/in-progress"], self.read_state(state_file)["issues"]["142"]["labels"])

        review = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-review-enter", "001", project], REPO_ROOT, env=env)
        self.assertEqual(review.returncode, 0, review.stderr)
        self.assertEqual(["ct2/in-review"], self.read_state(state_file)["issues"]["142"]["labels"])

        reviews = project / ".ct2" / "reviews"
        (reviews / "001-cc-r0.md").write_text(sidecar("001-mirror-github-issue", "ct2-lens-cc"), encoding="utf-8")
        (reviews / "001-cx-r0.md").write_text(sidecar("001-mirror-github-issue", "ct2-lens-cx"), encoding="utf-8")
        reconcile = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-reconcile", "001", "0", "--project-dir", project], REPO_ROOT, env=env)
        self.assertEqual(reconcile.returncode, 0, reconcile.stderr)
        issue = self.read_state(state_file)["issues"]["142"]
        self.assertEqual(["ct2/done"], issue["labels"])
        self.assertEqual("CLOSED", issue["state"])
        drift = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-issue-reconcile", project, "--json"], project, env=env)
        self.assertEqual(drift.returncode, 0, drift.stderr)
        self.assertEqual([], json.loads(drift.stdout)["findings"])

    def test_mirror_queues_on_gh_failure_and_retries(self):
        project = self.make_project()
        env, state_file = self.install_fake_gh(project, failing=True)
        ticket = project / ".ct2" / "backlog" / "001-mirror-github-issue.md"
        write_ticket(ticket, status="backlog")

        queued = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-issue-mirror", ticket, project, "--create", "--json"], project, env=env)

        self.assertEqual(queued.returncode, 0, queued.stderr)
        self.assertTrue((project / ".ct2" / ".meta" / "001.issue-mirror-pending.json").exists())

        env, state_file = self.install_fake_gh(project)
        retried = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-issue-mirror", ticket, project, "--create", "--json"], project, env=env)

        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertFalse((project / ".ct2" / ".meta" / "001.issue-mirror-pending.json").exists())
        self.assertIn("issue: 142", ticket.read_text(encoding="utf-8"))
        self.assertIn("142", self.read_state(state_file)["issues"])

    def test_issue_adopt_creates_draft_without_touching_labels(self):
        project = self.make_project()
        initial = {
            "next": 142,
            "labels": [],
            "calls": [],
            "issues": {
                "77": {
                    "number": "77",
                    "url": "https://github.com/example/repo/issues/77",
                    "title": "External request",
                    "body": "Please support the external workflow.",
                    "state": "OPEN",
                    "labels": ["enhancement"],
                    "comments": [],
                }
            },
        }
        env, state_file = self.install_fake_gh(project, initial=initial)

        adopt = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-issue-adopt", "77", project, "--json"], project, env=env)

        self.assertEqual(adopt.returncode, 0, adopt.stderr)
        result = json.loads(adopt.stdout)
        draft = project / result["path"]
        content = draft.read_text(encoding="utf-8")
        self.assertIn("issue: 77", content)
        self.assertIn("issue-source: adopted", content)
        self.assertIn("Please support the external workflow.", content)
        state = self.read_state(state_file)
        self.assertEqual(["enhancement"], state["issues"]["77"]["labels"])
        self.assertTrue(any(call[:2] == ["issue", "comment"] for call in state["calls"]))
        self.assertFalse(any(call[:2] == ["issue", "edit"] for call in state["calls"]))


if __name__ == "__main__":
    unittest.main()
