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
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [str(arg) for arg in args],
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
        env=merged_env,
    )


def write_ticket(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """---
id: "001"
title: "Parse nested config"
status: in-progress
priority: medium
created: 2026-05-24T00:00:00Z
updated: 2026-05-24T00:00:00Z
sealed: 2026-05-24T00:00:00Z
branch: null
pr: null
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
- [x] Parse nested config safely.

## Context
This ticket exercises clean host artifact defaults.

## Acceptance Criteria
- [x] Branch names omit CT2 ticket IDs.
""",
        encoding="utf-8",
    )


class TraceLintTest(unittest.TestCase):
    def make_repo(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = Path(tmp.name)
        self.assertEqual(run_cmd(["git", "init"], repo).returncode, 0)
        self.assertEqual(run_cmd(["git", "config", "user.name", "CT2 Test"], repo).returncode, 0)
        self.assertEqual(run_cmd(["git", "config", "user.email", "ct2@example.invalid"], repo).returncode, 0)
        (repo / "README.md").write_text("# Host\n", encoding="utf-8")
        self.assertEqual(run_cmd(["git", "add", "README.md"], repo).returncode, 0)
        self.assertEqual(run_cmd(["git", "commit", "-m", "init"], repo).returncode, 0)
        return repo

    def lint_json(self, repo, *args, env=None):
        proc = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-trace-lint", "--json", *args], repo, env=env)
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"invalid json: {exc}\nstdout={proc.stdout}\nstderr={proc.stderr}")
        return proc, data

    def categories(self, data):
        return {finding["category"] for finding in data["findings"]}

    def test_pattern_catalog_contains_expected_categories(self):
        proc = run_cmd(
            [
                PYTHON,
                "-c",
                "import _ct2_trace_patterns as p; print('\\n'.join(sorted(p.CATEGORY_DEFINITIONS)))",
            ],
            REPO_ROOT,
            env={"PYTHONPATH": str(REPO_ROOT / "bin")},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        categories = set(proc.stdout.splitlines())
        self.assertTrue(
            {
                "commit-scope-ticket-id",
                "commit-trailer-ct2-path",
                "pr-body-branded-footer",
                "pr-body-ct2-path",
                "branch-name-ticket-id",
                "tracked-ct2-dir",
                "tmp-leakage",
                "gitignore-missing-ct2",
                "hooks-committed-without-policy",
                "agents-md-mentions-ct2-internal",
                "ci-workflow-references-ct2",
            }.issubset(categories)
        )

    def test_clean_ct2_default_lifecycle_has_no_strict_findings(self):
        repo = self.make_repo()
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", repo], REPO_ROOT)
        self.assertEqual(init.returncode, 0, init.stderr)
        ticket = repo / ".ct2" / "in-progress" / "001-parse-nested-config.md"
        write_ticket(ticket)

        start = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-git-start", "001"], repo)
        self.assertEqual(start.returncode, 0, start.stderr)
        self.assertEqual("feat/parse-nested-config", run_cmd(["git", "branch", "--show-current"], repo).stdout.strip())
        (repo / "README.md").write_text("# Host\n\nClean change.\n", encoding="utf-8")
        self.assertEqual(run_cmd(["git", "add", "README.md"], repo).returncode, 0)
        commit = run_cmd(
            [
                "git",
                "commit",
                "-m",
                "feat: update host fixture",
                "-m",
                "Exercise the clean host defaults without leaking internal trace strings.",
            ],
            repo,
        )
        self.assertEqual(commit.returncode, 0, commit.stderr)

        proc, data = self.lint_json(repo, "--strict")
        self.assertEqual(proc.returncode, 0, json.dumps(data, indent=2))
        self.assertEqual([], data["findings"])

    def test_ct2_init_installs_trace_hook_only_on_explicit_flag(self):
        repo = self.make_repo()
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", "--install-trace-hook", repo], REPO_ROOT)

        self.assertEqual(init.returncode, 0, init.stderr)
        hook = repo / ".git" / "hooks" / "pre-push"
        self.assertTrue(hook.exists())
        self.assertIn("ct2-trace-lint --strict", hook.read_text(encoding="utf-8"))

    def test_linter_reports_commit_branch_file_and_ignore_leaks(self):
        repo = self.make_repo()
        self.assertEqual(run_cmd(["git", "checkout", "-b", "feat/017-leaky-ticket"], repo).returncode, 0)
        (repo / "README.md").write_text("# Host\n\nLeaky change.\n", encoding="utf-8")
        (repo / ".ct2" / ".tmp").mkdir(parents=True)
        (repo / ".ct2" / ".tmp" / "ct2-write-leak.tmp").write_text("tmp\n", encoding="utf-8")
        (repo / "AGENTS.md").write_text("Use ct2-forge for this project.\n", encoding="utf-8")
        (repo / ".github" / "workflows").mkdir(parents=True)
        (repo / ".github" / "workflows" / "ci.yml").write_text("run: bin/ct2-status\n", encoding="utf-8")
        (repo / ".githooks").mkdir()
        (repo / ".githooks" / "pre-push").write_text("#!/bin/sh\n", encoding="utf-8")
        self.assertEqual(run_cmd(["git", "add", "."], repo).returncode, 0)
        commit = run_cmd(
            [
                "git",
                "commit",
                "-m",
                "fix(t-017): add leaky fixture",
                "-m",
                "Refs: .ct2/in-progress/017-leaky-ticket.md\n\nConstraint: fixture\nRejected: clean fixture | needs leak coverage\nConfidence: high\nScope-risk: narrow",
            ],
            repo,
        )
        self.assertEqual(commit.returncode, 0, commit.stderr)

        proc, data = self.lint_json(repo, "--strict", "--fix-suggest")

        self.assertEqual(proc.returncode, 2)
        self.assertTrue(
            {
                "commit-scope-ticket-id",
                "commit-trailer-ct2-path",
                "commit-trailer-structured-uninvited",
                "branch-name-ticket-id",
                "tracked-ct2-dir",
                "tmp-leakage",
                "gitignore-missing-ct2",
                "hooks-committed-without-policy",
                "agents-md-mentions-ct2-internal",
                "ci-workflow-references-ct2",
            }.issubset(self.categories(data))
        )
        self.assertGreaterEqual(data["summary"]["error"], 4)

    def test_baseline_suppresses_legacy_findings(self):
        repo = self.make_repo()
        self.assertEqual(run_cmd(["git", "checkout", "-b", "feat/017-legacy"], repo).returncode, 0)
        (repo / "README.md").write_text("# Host\n\nLegacy leak.\n", encoding="utf-8")
        self.assertEqual(run_cmd(["git", "add", "README.md"], repo).returncode, 0)
        self.assertEqual(
            run_cmd(["git", "commit", "-m", "fix(t-017): legacy leak", "-m", "Refs: .ct2/in-progress/017.md"], repo).returncode,
            0,
        )
        first, data = self.lint_json(repo, "--strict")
        self.assertEqual(first.returncode, 2)
        baseline = repo / "legacy-baseline.json"
        baseline.write_text(json.dumps(data), encoding="utf-8")

        second, suppressed = self.lint_json(repo, "--strict", "--baseline", baseline)

        self.assertEqual(second.returncode, 0, json.dumps(suppressed, indent=2))
        self.assertEqual([], suppressed["findings"])

    def test_pr_mode_uses_gh_json_and_ignores_hidden_mapping_comments(self):
        repo = self.make_repo()
        gh_dir = repo / "fake-bin"
        gh_dir.mkdir()
        gh = gh_dir / "gh"
        gh.write_text(
            """#!/usr/bin/env python3
import json
print(json.dumps({
  "title": "fix CT2 t-017 leak",
  "body": "Ticket: `.ct2/in-review/017-leak.md`\\n\\n<!-- ct2-ticket: 017 / pr-managed -->\\n\\n---\\nOpened by ct2-forge via ct2-git-submit.",
  "url": "https://example.invalid/pull/7",
  "headRefName": "fix/017-leak"
}))
""",
            encoding="utf-8",
        )
        gh.chmod(0o755)

        proc, data = self.lint_json(repo, "--pr", "7", "--strict", env={"PATH": f"{gh_dir}{os.pathsep}{os.environ['PATH']}"})

        self.assertEqual(proc.returncode, 2)
        self.assertTrue(
            {
                "pr-title-ct2-token",
                "pr-body-branded-footer",
                "pr-body-ct2-path",
                "branch-name-ticket-id",
            }.issubset(self.categories(data))
        )
        self.assertNotIn("ct2-ticket", {finding.get("match") for finding in data["findings"]})

    def test_include_exceptions_reports_contract_exempt_markers(self):
        repo = self.make_repo()
        gh_dir = repo / "fake-bin"
        gh_dir.mkdir()
        gh = gh_dir / "gh"
        gh.write_text(
            """#!/usr/bin/env python3
import json
print(json.dumps({
  "title": "feat: publish review",
  "body": "<!-- ct2-merge-ready: true -->\\n<!-- ct2-ticket-status:begin -->\\nready\\n<!-- ct2-ticket-status:end -->",
  "url": "https://example.invalid/pull/8",
  "headRefName": "feat/publish-review"
}))
""",
            encoding="utf-8",
        )
        gh.chmod(0o755)

        proc, data = self.lint_json(
            repo,
            "--pr",
            "8",
            "--include-exceptions",
            env={"PATH": f"{gh_dir}{os.pathsep}{os.environ['PATH']}"},
        )

        self.assertEqual(proc.returncode, 0, json.dumps(data, indent=2))
        self.assertIn("exception-review-thread-marker", self.categories(data))
        self.assertIn("exception-issue-status-marker", self.categories(data))


if __name__ == "__main__":
    unittest.main()
