import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run_cmd(args, cwd=None):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [str(arg) for arg in args],
        cwd=str(cwd or REPO_ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )


def popen_cmd(args, cwd=None):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.Popen(
        [str(arg) for arg in args],
        cwd=str(cwd or REPO_ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_ticket(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """---
id: "001"
title: "Watcher immutability smoke"
status: backlog
priority: medium
created: 2026-05-12T00:00:00Z
updated: 2026-05-12T00:00:00Z
sealed: 2026-05-12T00:00:00Z
branch: null
pr: null
review-round: 0
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
- [ ] Confirm watcher safety.

## Constraints
- Watchers must not move ticket state.

## Context
Regression fixture for notify-only external channels.

## Acceptance Criteria
- [ ] Ticket content remains unchanged.
""",
        encoding="utf-8",
    )


class WatchersTest(unittest.TestCase):
    maxDiff = None

    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project])
        self.assertEqual(init.returncode, 0, init.stderr)
        watchers = project / ".ct2" / "watchers"
        for path in watchers.glob("*.json"):
            path.unlink()
        return project

    def test_run_once_sends_one_advisory_message_and_dedupes_replay(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_json(
            ct2 / "watchers" / "local-review.json",
            {
                "schema_version": "1",
                "id": "local-review",
                "mode": "notify-only",
                "source": "local-test",
                "to": "ct2-helm",
                "ticket": "001",
                "subject": "Review watcher fired",
                "body": "External advisory input is available.",
                "allowed_actions": ["notify"],
                "forbidden_actions": ["state-move", "ticket-write"],
            },
        )

        first = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-watchers", "run-once", "--json", project])
        self.assertEqual(first.returncode, 0, first.stderr)
        report = json.loads(first.stdout)
        self.assertTrue(report["complete"])
        self.assertEqual(1, report["watchers_checked"])
        self.assertEqual(1, report["notifications_sent"])
        self.assertEqual(0, report["duplicates_skipped"])

        inbox_messages = sorted((ct2 / "inbox" / "ct2-helm").glob("*.md"))
        self.assertEqual(1, len(inbox_messages))
        self.assertRegex(inbox_messages[0].name, r"^msg-\d{8}T\d{6}Z-\d+-[0-9a-f]{8}\.md$")
        self.assertIn("Review watcher fired", inbox_messages[0].read_text(encoding="utf-8"))
        events = read_jsonl(ct2 / "telemetry" / "events.jsonl")
        self.assertEqual(1, len(events))
        self.assertEqual("advisory_notification", events[0]["type"])
        self.assertFalse(events[0]["state_mutation"])
        self.assertEqual("local-review", events[0]["watcher"])

        state = json.loads((ct2 / "runtime" / "watchers" / "local-review.json").read_text(encoding="utf-8"))
        self.assertEqual("sent", state["status"])

        second = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-watchers", "run-once", "--json", project])
        self.assertEqual(second.returncode, 0, second.stderr)
        replay = json.loads(second.stdout)
        self.assertTrue(replay["complete"])
        self.assertEqual(0, replay["notifications_sent"])
        self.assertEqual(1, replay["duplicates_skipped"])
        self.assertEqual(1, len(sorted((ct2 / "inbox" / "ct2-helm").glob("*.md"))))
        self.assertEqual(1, len(read_jsonl(ct2 / "telemetry" / "events.jsonl")))

        status = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-status", project])
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn("WATCHERS", status.stdout)
        self.assertIn("local-review", status.stdout)
        self.assertIn("status=sent", status.stdout)

    def test_concurrent_run_once_does_not_duplicate_advisory_message(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_json(
            ct2 / "watchers" / "parallel.json",
            {
                "schema_version": "1",
                "id": "parallel",
                "mode": "notify-only",
                "source": "parallel-test",
                "to": "ct2-helm",
                "ticket": "001",
                "allowed_actions": ["notify"],
            },
        )

        procs = [
            popen_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-watchers", "run-once", "--json", project])
            for _ in range(4)
        ]
        reports = []
        for proc in procs:
            stdout, stderr = proc.communicate(timeout=30)
            self.assertEqual(proc.returncode, 0, stderr)
            reports.append(json.loads(stdout))

        self.assertEqual(1, sum(report["notifications_sent"] for report in reports))
        self.assertEqual(3, sum(report["duplicates_skipped"] for report in reports))
        self.assertEqual(1, len(sorted((ct2 / "inbox" / "ct2-helm").glob("*.md"))))
        self.assertEqual(1, len(read_jsonl(ct2 / "telemetry" / "events.jsonl")))

    def test_state_mutating_watcher_is_rejected_without_touching_ticket(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "backlog" / "001-watcher-immutability-smoke.md"
        write_ticket(ticket)
        before = ticket.read_text(encoding="utf-8")
        write_json(
            ct2 / "watchers" / "unsafe.json",
            {
                "schema_version": "1",
                "id": "unsafe",
                "mode": "notify-only",
                "source": "unsafe-test",
                "to": "ct2-helm",
                "ticket": "001",
                "allowed_actions": ["state-move"],
            },
        )

        result = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-watchers", "run-once", "--json", project])
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["complete"])
        self.assertEqual(1, report["invalid_watchers"])
        self.assertEqual(0, report["notifications_sent"])
        self.assertIn("allowed_actions must be notify-only", report["results"][0]["errors"])
        self.assertEqual(before, ticket.read_text(encoding="utf-8"))
        self.assertFalse(list((ct2 / "inbox" / "ct2-helm").glob("*.md")))
        self.assertFalse((ct2 / "telemetry" / "events.jsonl").exists())
