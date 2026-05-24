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


def write_ticket(path, pr="https://github.com/example/repo/pull/5", round_num="0"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
id: "001"
title: "Publish PR review"
status: in-review
priority: medium
created: 2026-05-24T00:00:00Z
updated: 2026-05-24T00:00:00Z
sealed: 2026-05-24T00:00:00Z
branch: feat/publish-pr-review
pr: {pr}
issue: null
issue-url: null
issue-source: null
review-round: {round_num}
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
- [x] Publish review to the PR thread.

## Constraints
- Keep sidecars authoritative.

## Context
The PR thread should show review decisions.

## Acceptance Criteria
- [x] Review publication is visible on GitHub.
""",
        encoding="utf-8",
    )


def write_sidecar(path, reviewer="ct2-lens-cc", verdict="approved", line="1", suggestion_extra=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
ticket: "001-publish-pr-review"
reviewer: {reviewer}
round: 0
verdict: {verdict}
timestamp: 2026-05-24T00:00:00Z
---

## Summary
Review summary.

## Acceptance Criteria Check
- [x] Review publication is visible on GitHub.

## Issues Found

### [BLOCKING] Tighten validation
file: README.md
line: {line}
suggestion: |
  # Host
{suggestion_extra}

The heading needs to remain present.

## Recommendation
approved - fixture passes.
""",
        encoding="utf-8",
    )


class PrReviewPublicationTest(unittest.TestCase):
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
        write_ticket(project / ".ct2" / "in-review" / "001-publish-pr-review.md")
        write_sidecar(project / ".ct2" / "reviews" / "001-cc-r0.md")
        return project

    def install_fake_gh(self, project, failing=False, reject_inline=False, review_comment_body="Please address this blocking comment."):
        fake_bin = project / "fake-bin"
        fake_bin.mkdir(exist_ok=True)
        state = project / "fake-gh-pr-state.json"
        state.write_text(
            json.dumps(
                {
                    "calls": [],
                    "reviews": [],
                    "comments": [],
                    "review_api": [],
                    "review_comments": [
                        {
                            "id": 100,
                            "path": "README.md",
                            "line": 1,
                            "body": review_comment_body,
                        }
                    ],
                    "reject_inline": reject_inline,
                }
            ),
            encoding="utf-8",
        )
        gh = fake_bin / "gh"
        if failing:
            gh.write_text("#!/usr/bin/env python3\nimport sys\nprint('gh down', file=sys.stderr)\nsys.exit(1)\n", encoding="utf-8")
        else:
            gh.write_text(
                r'''#!/usr/bin/env python3
import json, os, sys

state_path = os.environ["FAKE_GH_PR_STATE"]
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

if args[:2] == ["pr", "review"]:
    body = ""
    if "--body-file" in args:
        body = open(value_after("--body-file"), encoding="utf-8").read()
    state.setdefault("reviews", []).append({"args": args, "body": body})
    save()
    sys.exit(0)

if args[:2] == ["pr", "comment"]:
    state.setdefault("comments", []).append({"selector": args[2], "body": value_after("--body")})
    save()
    sys.exit(0)

if args[:2] == ["pr", "view"]:
    print(json.dumps({"comments": state.get("comments", []), "reviews": state.get("reviews", [])}))
    save()
    sys.exit(0)

if args and args[0] == "api":
    if "pulls/5/reviews" in args[1]:
        payload = json.loads(sys.stdin.read() or "{}")
        if state.get("reject_inline") or any(comment.get("line") == 999 for comment in payload.get("comments", [])):
            save()
            print("Validation Failed", file=sys.stderr)
            sys.exit(1)
        state.setdefault("review_api", []).append({"args": args, "payload": payload})
        state.setdefault("reviews", []).append({"args": args, "body": payload.get("body", ""), "comments": payload.get("comments", [])})
        save()
        print(json.dumps({"id": 555}))
        sys.exit(0)
    if "pulls/5/comments" in args[1]:
        print(json.dumps(state.get("review_comments", [])))
        save()
        sys.exit(0)

print("unsupported gh call: " + " ".join(args), file=sys.stderr)
save()
sys.exit(1)
''',
                encoding="utf-8",
            )
        gh.chmod(0o755)
        return {"PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}", "FAKE_GH_PR_STATE": str(state)}, state

    def read_state(self, state):
        return json.loads(state.read_text(encoding="utf-8"))

    def test_pr_review_merge_ready_reconciler_and_response_todo(self):
        project = self.make_project()
        env, state_file = self.install_fake_gh(project)
        ticket = project / ".ct2" / "in-review" / "001-publish-pr-review.md"
        sidecar = project / ".ct2" / "reviews" / "001-cc-r0.md"

        review = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pr-review", ticket, sidecar, project, "--json"], project, env=env)
        self.assertEqual(review.returncode, 0, review.stderr)
        result = json.loads(review.stdout)
        self.assertEqual("published", result["status"])
        self.assertEqual("APPROVE", result["event"])
        state = self.read_state(state_file)
        self.assertEqual(1, len(state["review_api"]) + len([r for r in state["reviews"] if r["args"][:2] == ["pr", "review"]]))
        self.assertEqual("APPROVE", state["review_api"][0]["payload"]["event"])
        self.assertIn("<!-- ct2-review: lens-cc round=0 -->", state["reviews"][0]["body"])

        for _ in range(2):
            ready = run_cmd(
                [PYTHON, REPO_ROOT / "bin" / "ct2-pr-merge-ready", ticket, project, "--reviewer", "lens-cc", "--json"],
                project,
                env=env,
            )
            self.assertEqual(ready.returncode, 0, ready.stderr)
        state = self.read_state(state_file)
        merge_ready = [comment for comment in state["comments"] if "ct2-merge-ready: lens-cc round=0" in comment["body"]]
        self.assertEqual(1, len(merge_ready))

        summary = run_cmd(
            [PYTHON, REPO_ROOT / "bin" / "ct2-pr-merge-ready", ticket, project, "--reconciler-summary", "--verdict", "approved", "--json"],
            project,
            env=env,
        )
        self.assertEqual(summary.returncode, 0, summary.stderr)
        summary_again = run_cmd(
            [PYTHON, REPO_ROOT / "bin" / "ct2-pr-merge-ready", ticket, project, "--reconciler-summary", "--verdict", "approved", "--json"],
            project,
            env=env,
        )
        self.assertEqual(summary_again.returncode, 0, summary_again.stderr)
        self.assertEqual("already-present", json.loads(summary_again.stdout)["status"])
        self.assertTrue(any("ct2-reconciler" in comment["body"] for comment in self.read_state(state_file)["comments"]))

        respond = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pr-respond", ticket, project, "--json"], project, env=env)
        self.assertEqual(respond.returncode, 0, respond.stderr)
        todo = project / ".ct2" / ".meta" / "001.pr-review-todo.md"
        self.assertIn("comment 100", todo.read_text(encoding="utf-8"))

    def test_pr_review_is_idempotent_and_does_not_double_publish(self):
        project = self.make_project()
        env, state_file = self.install_fake_gh(project)
        ticket = project / ".ct2" / "in-review" / "001-publish-pr-review.md"
        sidecar = project / ".ct2" / "reviews" / "001-cc-r0.md"

        first = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pr-review", ticket, sidecar, project, "--json"], project, env=env)
        second = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pr-review", ticket, sidecar, project, "--json"], project, env=env)

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual("already-present", json.loads(second.stdout)["status"])
        state = self.read_state(state_file)
        rest_reviews = len(state["review_api"])
        cli_reviews = len([review for review in state["reviews"] if review["args"][:2] == ["pr", "review"]])
        self.assertEqual(1, rest_reviews + cli_reviews)

    def test_inline_review_api_failure_degrades_to_sidecar_only(self):
        project = self.make_project()
        env, _state_file = self.install_fake_gh(project, reject_inline=True)
        ticket = project / ".ct2" / "in-review" / "001-publish-pr-review.md"
        sidecar = project / ".ct2" / "reviews" / "001-cc-r0.md"

        review = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pr-review", ticket, sidecar, project, "--json"], project, env=env)

        self.assertEqual(review.returncode, 0, review.stderr)
        result = json.loads(review.stdout)
        self.assertEqual("sidecar-only", result["status"])
        self.assertIn("Validation Failed", result["error"])

    def test_plain_pr_number_reports_full_url_requirement_for_inline_comments(self):
        project = self.make_project()
        write_ticket(project / ".ct2" / "in-review" / "001-publish-pr-review.md", pr="5")
        env, _state_file = self.install_fake_gh(project)
        ticket = project / ".ct2" / "in-review" / "001-publish-pr-review.md"
        sidecar = project / ".ct2" / "reviews" / "001-cc-r0.md"

        review = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pr-review", ticket, sidecar, project, "--json"], project, env=env)

        self.assertEqual(review.returncode, 0, review.stderr)
        result = json.loads(review.stdout)
        self.assertEqual("sidecar-only", result["status"])
        self.assertIn("full github.com PR URL", result["error"])

    def test_pr_respond_strips_backticks_and_escapes_angle_brackets(self):
        project = self.make_project()
        env, _state_file = self.install_fake_gh(project, review_comment_body="```bad``` <script> & details")
        ticket = project / ".ct2" / "in-review" / "001-publish-pr-review.md"

        respond = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pr-respond", ticket, project, "--json"], project, env=env)

        self.assertEqual(respond.returncode, 0, respond.stderr)
        todo = (project / ".ct2" / ".meta" / "001.pr-review-todo.md").read_text(encoding="utf-8")
        self.assertNotIn("`bad`", todo)
        self.assertIn("&lt;script&gt; &amp; details", todo)

    def test_pr_only_mode_is_not_advertised(self):
        self.assertNotIn("pr-only", (REPO_ROOT / "config" / "harness.yaml").read_text(encoding="utf-8"))
        self.assertNotIn("pr-only", (REPO_ROOT / "spec" / "protocol-surface.yaml").read_text(encoding="utf-8"))

    def test_merge_ready_new_round_posts_fresh_marker(self):
        project = self.make_project()
        env, state_file = self.install_fake_gh(project)
        ticket = project / ".ct2" / "in-review" / "001-publish-pr-review.md"

        first = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pr-merge-ready", ticket, project, "--reviewer", "lens-cc", "--json"], project, env=env)
        self.assertEqual(first.returncode, 0, first.stderr)
        write_ticket(ticket, round_num="1")
        second = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pr-merge-ready", ticket, project, "--reviewer", "lens-cc", "--json"], project, env=env)

        self.assertEqual(second.returncode, 0, second.stderr)
        bodies = [comment["body"] for comment in self.read_state(state_file)["comments"]]
        self.assertTrue(any("ct2-merge-ready: lens-cc round=0" in body for body in bodies))
        self.assertTrue(any("ct2-merge-ready: lens-cc round=1" in body for body in bodies))

    def test_multiline_suggestion_preserves_paragraphs(self):
        project = self.make_project()
        sidecar = project / ".ct2" / "reviews" / "001-cc-r0.md"
        write_sidecar(sidecar, suggestion_extra="\n  second line\n\n  third paragraph")
        env, state_file = self.install_fake_gh(project)
        ticket = project / ".ct2" / "in-review" / "001-publish-pr-review.md"

        review = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pr-review", ticket, sidecar, project, "--json"], project, env=env)

        self.assertEqual(review.returncode, 0, review.stderr)
        body = self.read_state(state_file)["review_api"][0]["payload"]["comments"][0]["body"]
        self.assertIn("second line", body)
        self.assertIn("third paragraph", body)
        suggestion = body.split("```suggestion", 1)[1]
        self.assertNotIn("The heading needs to remain present.", suggestion)

    def test_pr_review_falls_back_to_sidecar_only_when_gh_fails(self):
        project = self.make_project()
        env, _state_file = self.install_fake_gh(project, failing=True)
        ticket = project / ".ct2" / "in-review" / "001-publish-pr-review.md"
        sidecar = project / ".ct2" / "reviews" / "001-cc-r0.md"

        review = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pr-review", ticket, sidecar, project, "--json"], project, env=env)

        self.assertEqual(review.returncode, 0, review.stderr)
        self.assertEqual("sidecar-only", json.loads(review.stdout)["status"])


if __name__ == "__main__":
    unittest.main()
