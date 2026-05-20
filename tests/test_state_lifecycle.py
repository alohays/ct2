import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run_cmd(args, cwd):
    return subprocess.run(
        [str(arg) for arg in args],
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )


def write_ticket(path, ticket_id="001", status="draft", sealed="null"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
id: "{ticket_id}"
title: "Seal smoke"
status: {status}
priority: medium
created: 2026-05-12T00:00:00Z
updated: 2026-05-12T00:00:00Z
sealed: {sealed}
branch: feat/{ticket_id}-seal-smoke
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
- [ ] Exercise sealing.

## Constraints
- Use stdlib-only tests.

## Context
Regression fixture for state transitions.

## Acceptance Criteria
- [ ] Draft moves to backlog.

## Notes
```text
status: quoted-body-value
updated: quoted-body-value
```
""",
        encoding="utf-8",
    )


class StateLifecycleTest(unittest.TestCase):
    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project], cwd=REPO_ROOT)
        self.assertEqual(init.returncode, 0, init.stderr)
        return project

    def test_ct2_seal_moves_valid_draft_to_backlog(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        draft = ct2 / "draft" / "001-seal-smoke.md"
        backlog = ct2 / "backlog" / "001-seal-smoke.md"
        write_ticket(draft)

        seal = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-seal", "001"], cwd=project)
        self.assertEqual(seal.returncode, 0, seal.stderr)

        self.assertFalse(draft.exists())
        self.assertTrue(backlog.exists())
        content = backlog.read_text(encoding="utf-8")
        self.assertIn("status: backlog", content)
        self.assertRegex(content, r"sealed: 20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ")
        self.assertRegex(content, r"updated: 20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ")
        self.assertNotIn("updated: 2026-05-12T00:00:00Z", content)
        self.assertIn("status: quoted-body-value", content)
        self.assertIn("updated: quoted-body-value", content)
        self.assertEqual([], list((ct2 / ".tmp").iterdir()))

    def test_ct2_seal_collision_leaves_draft_and_tmp_clean(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        draft = ct2 / "draft" / "001-seal-smoke.md"
        backlog = ct2 / "backlog" / "001-seal-smoke.md"
        write_ticket(draft)
        write_ticket(backlog, status="backlog", sealed="2026-05-12T00:00:00Z")
        original_backlog = backlog.read_text(encoding="utf-8")
        original_backlog_hash = hashlib.sha256(original_backlog.encode("utf-8")).hexdigest()

        seal = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-seal", "001"], cwd=project)
        self.assertNotEqual(seal.returncode, 0)

        self.assertTrue(draft.exists())
        self.assertEqual(original_backlog, backlog.read_text(encoding="utf-8"))
        self.assertEqual(original_backlog_hash, hashlib.sha256(backlog.read_bytes()).hexdigest())
        self.assertEqual([], list((ct2 / ".tmp").iterdir()))

    def test_ct2_seal_rejects_missing_required_fields_without_move(self):
        cases = {
            "title": lambda text: text.replace('title: "Seal smoke"\n', ""),
            "priority": lambda text: text.replace("priority: medium\n", ""),
            "touched-files": lambda text: text.replace("touched-files:\n  - README.md\n", ""),
            "acceptance": lambda text: text.replace("## Acceptance Criteria", "## Done Criteria"),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                project = self.make_project()
                ct2 = project / ".ct2"
                draft = ct2 / "draft" / "001-seal-smoke.md"
                backlog = ct2 / "backlog" / "001-seal-smoke.md"
                write_ticket(draft)
                draft.write_text(mutate(draft.read_text(encoding="utf-8")), encoding="utf-8")

                seal = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-seal", "001"], cwd=project)
                self.assertNotEqual(seal.returncode, 0)
                self.assertTrue(draft.exists())
                self.assertFalse(backlog.exists())

    def test_ct2_pickup_serializes_single_in_progress_slot(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "backlog" / "001-seal-smoke.md", status="backlog", sealed="2026-05-12T00:00:00Z")
        write_ticket(ct2 / "backlog" / "002-seal-smoke.md", ticket_id="002", status="backlog", sealed="2026-05-12T00:01:00Z")

        first = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pickup", project], cwd=REPO_ROOT)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertTrue((ct2 / "in-progress" / "001-seal-smoke.md").exists())
        self.assertIn("status: in-progress", (ct2 / "in-progress" / "001-seal-smoke.md").read_text(encoding="utf-8"))
        self.assertTrue((ct2 / ".meta" / "001.started").exists())

        second = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pickup", project], cwd=REPO_ROOT)
        self.assertEqual(second.returncode, 2)
        self.assertTrue((ct2 / "backlog" / "002-seal-smoke.md").exists())
        self.assertEqual(1, len(list((ct2 / "in-progress").glob("*.md"))))

    def test_ct2_pickup_recovers_stale_lifecycle_lock(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "backlog" / "001-seal-smoke.md", status="backlog", sealed="2026-05-12T00:00:00Z")

        meta = ct2 / ".meta"
        meta.mkdir(parents=True, exist_ok=True)
        stale_lock = meta / "lifecycle.lock"
        stale_lock.write_text("pid: 999999\ntimestamp: 2026-05-12T00:00:00Z\n", encoding="utf-8")
        old = 1700000000.0
        import os as _os
        _os.utime(stale_lock, (old, old))

        result = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pickup", project], cwd=REPO_ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((ct2 / "in-progress" / "001-seal-smoke.md").exists())
        self.assertFalse(stale_lock.exists())

    def test_ct2_pickup_rejects_live_lifecycle_lock(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "backlog" / "001-seal-smoke.md", status="backlog", sealed="2026-05-12T00:00:00Z")

        meta = ct2 / ".meta"
        meta.mkdir(parents=True, exist_ok=True)
        live_lock = meta / "lifecycle.lock"
        import os as _os
        live_lock.write_text(f"pid: {_os.getpid()}\ntimestamp: 2026-05-12T00:00:00Z\n", encoding="utf-8")

        result = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pickup", project], cwd=REPO_ROOT)
        self.assertEqual(result.returncode, 2)
        self.assertIn("lifecycle lock already held", result.stderr)
        self.assertTrue(live_lock.exists())

    def test_ct2_verify_rejects_multiple_in_progress_tickets(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "in-progress" / "001-seal-smoke.md", status="in-progress")
        write_ticket(ct2 / "in-progress" / "002-seal-smoke.md", ticket_id="002", status="in-progress")

        verify = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-verify", "--json", project], cwd=REPO_ROOT)
        self.assertEqual(verify.returncode, 1)
        self.assertIn("kanban:single-in-progress", verify.stdout)

    def test_ct2_inbox_claim_is_single_consumer(self):
        project = self.make_project()
        inbox = project / ".ct2" / "inbox" / "ct2-forge"
        msg = inbox / "msg-20260520T000000Z-1-deadbeef.md"
        msg.write_text("---\nid: msg\n---\n\n## Body\nhello\n", encoding="utf-8")

        claim = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-inbox", "claim", "ct2-forge", msg.name, "--project-dir", project], cwd=REPO_ROOT)
        self.assertEqual(claim.returncode, 0, claim.stderr)
        self.assertFalse(msg.exists())
        self.assertTrue((inbox / "processing" / msg.name).exists())

        duplicate = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-inbox", "claim", "ct2-forge", msg.name, "--project-dir", project], cwd=REPO_ROOT)
        self.assertEqual(duplicate.returncode, 2)

        ack = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-inbox", "ack", "ct2-forge", msg.name, "--project-dir", project], cwd=REPO_ROOT)
        self.assertEqual(ack.returncode, 0, ack.stderr)
        self.assertTrue((inbox / "done" / msg.name).exists())

    def test_ct2_review_enter_stamps_review_timer(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-progress" / "001-seal-smoke.md"
        write_ticket(ticket, status="in-progress", sealed="2026-05-12T00:00:00Z")
        (ct2 / ".meta" / "001.started").write_text("2026-05-12T00:00:00Z\n", encoding="utf-8")

        enter = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-review-enter", "001", project], cwd=REPO_ROOT)
        self.assertEqual(enter.returncode, 0, enter.stderr)

        reviewed = ct2 / "in-review" / "001-seal-smoke.md"
        self.assertTrue(reviewed.exists())
        self.assertFalse(ticket.exists())
        self.assertIn("status: in-review", reviewed.read_text(encoding="utf-8"))
        self.assertFalse((ct2 / ".meta" / "001.started").exists())
        self.assertRegex((ct2 / ".meta" / "001.in-review").read_text(encoding="utf-8"), r"20\d\d-\d\d-\d\dT")

    def test_ct2_review_watchdog_escalates_overdue_missing_sidecar(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-review" / "001-seal-smoke.md"
        write_ticket(ticket, status="in-review", sealed="2026-05-12T00:00:00Z")
        (ct2 / ".meta" / "001.in-review").write_text("2020-01-01T00:00:00Z\n", encoding="utf-8")

        watchdog = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-review-watchdog", "--json", project], cwd=REPO_ROOT)
        self.assertEqual(watchdog.returncode, 0, watchdog.stderr)

        escalated = ct2 / "escalated" / "001-seal-smoke.md"
        self.assertTrue(escalated.exists())
        text = escalated.read_text(encoding="utf-8")
        self.assertIn("status: escalated", text)
        self.assertIn("verdict: escalated", text)
        self.assertFalse(ticket.exists())
        self.assertEqual(1, len(list((ct2 / "inbox" / "ct2-helm").glob("msg-*.md"))))

    def test_ct2_review_watchdog_honors_nested_max_review_duration_min(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        cfg = ct2 / "config" / "harness.yaml"
        cfg.write_text(
            "circuit_breaker:\n"
            "  max_review_rounds: 3\n"
            "  max_review_duration_min: 1\n"
            "  max_ticket_duration_min: 120\n",
            encoding="utf-8",
        )
        ticket = ct2 / "in-review" / "001-seal-smoke.md"
        write_ticket(ticket, status="in-review", sealed="2026-05-12T00:00:00Z")
        stamp = ct2 / ".meta" / "001.in-review"
        from datetime import datetime, timedelta, timezone
        recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        stamp.write_text(recent + "\n", encoding="utf-8")

        watchdog = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-review-watchdog", "--json", project], cwd=REPO_ROOT)
        self.assertEqual(watchdog.returncode, 0, watchdog.stderr)
        self.assertTrue((ct2 / "escalated" / "001-seal-smoke.md").exists())
        self.assertIn('"max_review_duration_min": 1', watchdog.stdout)

    def test_ct2_review_watchdog_ignores_unconfigured_default_when_under_limit(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        cfg = ct2 / "config" / "harness.yaml"
        cfg.write_text(
            "circuit_breaker:\n"
            "  max_review_duration_min: 1000\n",
            encoding="utf-8",
        )
        ticket = ct2 / "in-review" / "001-seal-smoke.md"
        write_ticket(ticket, status="in-review", sealed="2026-05-12T00:00:00Z")
        stamp = ct2 / ".meta" / "001.in-review"
        from datetime import datetime, timedelta, timezone
        recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        stamp.write_text(recent + "\n", encoding="utf-8")

        watchdog = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-review-watchdog", "--json", project], cwd=REPO_ROOT)
        self.assertEqual(watchdog.returncode, 0, watchdog.stderr)
        self.assertFalse((ct2 / "escalated" / "001-seal-smoke.md").exists())
        self.assertTrue(ticket.exists())

    def test_ct2_status_reports_overdue_review_wait(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-review" / "001-seal-smoke.md"
        write_ticket(ticket, status="in-review", sealed="2026-05-12T00:00:00Z")
        (ct2 / ".meta" / "001.in-review").write_text("2020-01-01T00:00:00Z\n", encoding="utf-8")

        status = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-status", project], cwd=REPO_ROOT)
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn("overdue reviews:     1", status.stdout)

    def test_ct2_status_reports_unstamped_review_wait(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-review" / "001-seal-smoke.md"
        write_ticket(ticket, status="in-review", sealed="2026-05-12T00:00:00Z")

        status = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-status", project], cwd=REPO_ROOT)
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn("unstamped reviews:   1", status.stdout)

    def test_ct2_sidecar_publish_fails_loudly_on_collision(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        tmp = ct2 / ".tmp" / "review.tmp"
        tmp.write_text("---\nverdict: approved\n---\n", encoding="utf-8")

        publish = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-sidecar-publish", tmp, "001-cc-r0.md", "--project-dir", project], cwd=REPO_ROOT)
        self.assertEqual(publish.returncode, 0, publish.stderr)
        self.assertTrue((ct2 / "reviews" / "001-cc-r0.md").exists())
        self.assertFalse(tmp.exists())

        tmp2 = ct2 / ".tmp" / "review-again.tmp"
        tmp2.write_text("---\nverdict: rejected\n---\n", encoding="utf-8")
        duplicate = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-sidecar-publish", tmp2, "001-cc-r0.md", "--project-dir", project], cwd=REPO_ROOT)
        self.assertEqual(duplicate.returncode, 2)
        self.assertTrue(tmp2.exists())


if __name__ == "__main__":
    unittest.main()
