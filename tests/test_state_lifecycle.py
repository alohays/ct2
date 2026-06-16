import hashlib
import json
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
        self.assertTrue((ct2 / "reviews" / "001-sealed.md").exists())
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

    def test_ct2_seal_rejects_low_quality_draft_without_move(self):
        cases = {
            "placeholder-ac": lambda text: text.replace("Draft moves to backlog.", "TBD"),
            "prechecked-ac": lambda text: text.replace("- [ ] Draft moves to backlog.", "- [x] Draft moves to backlog."),
            "contradictory-tests": lambda text: text.replace(
                "Use stdlib-only tests.",
                "No tests may be added.",
            ).replace("Draft moves to backlog.", "Tests pass."),
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
                self.assertIn("ticket quality gate failed", seal.stderr)
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

    @staticmethod
    def make_submittable(ticket, ct2, round_num=0):
        """Flip the fixture's AC to [x] and lay down this round's plan evidence
        so the in-progress -> in-review submit gate passes."""
        ticket.write_text(
            ticket.read_text(encoding="utf-8").replace(
                "- [ ] Draft moves to backlog.", "- [x] Draft moves to backlog."
            ),
            encoding="utf-8",
        )
        (ct2 / "plans" / f"001-r{round_num}.md").write_text("# Plan\n", encoding="utf-8")

    def test_ct2_review_enter_stamps_review_timer(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-progress" / "001-seal-smoke.md"
        write_ticket(ticket, status="in-progress", sealed="2026-05-12T00:00:00Z")
        self.make_submittable(ticket, ct2)
        (ct2 / ".meta" / "001.started").write_text("2026-05-12T00:00:00Z\n", encoding="utf-8")

        enter = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-review-enter", "001", project], cwd=REPO_ROOT)
        self.assertEqual(enter.returncode, 0, enter.stderr)

        reviewed = ct2 / "in-review" / "001-seal-smoke.md"
        self.assertTrue(reviewed.exists())
        self.assertFalse(ticket.exists())
        self.assertIn("status: in-review", reviewed.read_text(encoding="utf-8"))
        self.assertFalse((ct2 / ".meta" / "001.started").exists())
        self.assertRegex((ct2 / ".meta" / "001.in-review").read_text(encoding="utf-8"), r"20\d\d-\d\d-\d\dT")

    def test_ct2_review_enter_submit_gate_blocks_unchecked_acs(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-progress" / "001-seal-smoke.md"
        write_ticket(ticket, status="in-progress", sealed="2026-05-12T00:00:00Z")
        (ct2 / "plans" / "001-r0.md").write_text("# Plan\n", encoding="utf-8")
        # AC stays "- [ ]" — the gate must refuse the move.

        enter = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-review-enter", "001", project], cwd=REPO_ROOT)
        self.assertEqual(enter.returncode, 2, enter.stdout)
        self.assertIn("submit gate failed", enter.stderr)
        self.assertIn("acceptance_criteria_checked", enter.stderr)
        self.assertTrue(ticket.exists())
        self.assertFalse((ct2 / "in-review" / "001-seal-smoke.md").exists())

    def test_ct2_review_enter_submit_gate_blocks_missing_plan(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-progress" / "001-seal-smoke.md"
        write_ticket(ticket, status="in-progress", sealed="2026-05-12T00:00:00Z")
        ticket.write_text(
            ticket.read_text(encoding="utf-8").replace(
                "- [ ] Draft moves to backlog.", "- [x] Draft moves to backlog."
            ),
            encoding="utf-8",
        )
        # No plan evidence for r0 — the gate must refuse the move.

        enter = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-review-enter", "001", project], cwd=REPO_ROOT)
        self.assertEqual(enter.returncode, 2, enter.stdout)
        self.assertIn("plan_evidence", enter.stderr)
        self.assertTrue(ticket.exists())

    def test_ct2_review_enter_submit_gate_requires_round_plan_on_rework(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-progress" / "001-seal-smoke.md"
        write_ticket(ticket, status="in-progress", sealed="2026-05-12T00:00:00Z")
        ticket.write_text(
            ticket.read_text(encoding="utf-8")
            .replace("review-round: 0", "review-round: 1")
            .replace("- [ ] Draft moves to backlog.", "- [x] Draft moves to backlog."),
            encoding="utf-8",
        )
        # Only the r0 plan exists; rework round 1 must supply its own plan.
        (ct2 / "plans" / "001-r0.md").write_text("# Plan r0\n", encoding="utf-8")

        blocked = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-review-enter", "001", project], cwd=REPO_ROOT)
        self.assertEqual(blocked.returncode, 2, blocked.stdout)
        self.assertIn("plan_evidence", blocked.stderr)

        (ct2 / "plans" / "001-r1.md").write_text("# Plan r1\n", encoding="utf-8")
        passed = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-review-enter", "001", project], cwd=REPO_ROOT)
        self.assertEqual(passed.returncode, 0, passed.stderr)
        self.assertTrue((ct2 / "in-review" / "001-seal-smoke.md").exists())

    def test_ct2_review_enter_submit_gate_passes_direct_to_main_null_branch(self):
        # branch: null is legitimate under git_strategy direct-to-main|none and
        # must NOT brick the submit: the gate ignores required_frontmatter.
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-progress" / "001-seal-smoke.md"
        write_ticket(ticket, status="in-progress", sealed="2026-05-12T00:00:00Z")
        ticket.write_text(
            ticket.read_text(encoding="utf-8")
            .replace("branch: feat/001-seal-smoke", "branch: null")
            .replace("- [ ] Draft moves to backlog.", "- [x] Draft moves to backlog."),
            encoding="utf-8",
        )
        (ct2 / "plans" / "001-r0.md").write_text("# Plan\n", encoding="utf-8")

        enter = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-review-enter", "001", project], cwd=REPO_ROOT)
        self.assertEqual(enter.returncode, 0, enter.stderr)
        self.assertTrue((ct2 / "in-review" / "001-seal-smoke.md").exists())

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

    def test_ct2_duration_check_bounces_once_to_backlog(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-progress" / "001-seal-smoke.md"
        write_ticket(ticket, status="in-progress", sealed="2026-05-12T00:00:00Z")
        (ct2 / ".meta" / "001.started").write_text("2020-01-01T00:00:00Z\n", encoding="utf-8")

        check = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-duration-check", "--json", project], cwd=REPO_ROOT)
        self.assertEqual(check.returncode, 0, check.stderr)

        bounced = ct2 / "backlog" / "001-seal-smoke.md"
        self.assertTrue(bounced.exists())
        text = bounced.read_text(encoding="utf-8")
        self.assertIn("status: backlog", text)
        self.assertIn("duration-bounce-count: 1", text)
        self.assertIn("total-attempts: 1", text)
        self.assertFalse((ct2 / ".meta" / "001.started").exists())

    def test_ct2_duration_check_escalates_after_bounce_cap(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-progress" / "001-seal-smoke.md"
        write_ticket(ticket, status="in-progress", sealed="2026-05-12T00:00:00Z")
        content = ticket.read_text(encoding="utf-8")
        ticket.write_text(
            content.replace("review-round: 0\n", "review-round: 0\nduration-bounce-count: 2\ntotal-attempts: 7\n"),
            encoding="utf-8",
        )
        (ct2 / ".meta" / "001.started").write_text("2020-01-01T00:00:00Z\n", encoding="utf-8")

        check = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-duration-check", "--json", project], cwd=REPO_ROOT)
        self.assertEqual(check.returncode, 0, check.stderr)

        escalated = ct2 / "escalated" / "001-seal-smoke.md"
        self.assertTrue(escalated.exists())
        text = escalated.read_text(encoding="utf-8")
        self.assertIn("status: escalated", text)
        self.assertIn("verdict: escalated", text)
        self.assertIn("duration-bounce-count: 3", text)
        self.assertIn("total-attempts: 8", text)
        self.assertEqual(1, len(list((ct2 / "inbox" / "ct2-helm").glob("msg-*.md"))))

    def test_ct2_duration_check_escalates_after_total_attempt_cap(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-progress" / "001-seal-smoke.md"
        write_ticket(ticket, status="in-progress", sealed="2026-05-12T00:00:00Z")
        content = ticket.read_text(encoding="utf-8")
        ticket.write_text(
            content.replace("review-round: 0\n", "review-round: 0\nduration-bounce-count: 0\ntotal-attempts: 8\n"),
            encoding="utf-8",
        )
        (ct2 / ".meta" / "001.started").write_text("2020-01-01T00:00:00Z\n", encoding="utf-8")

        check = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-duration-check", "--json", project], cwd=REPO_ROOT)
        self.assertEqual(check.returncode, 0, check.stderr)

        escalated = ct2 / "escalated" / "001-seal-smoke.md"
        self.assertTrue(escalated.exists())
        text = escalated.read_text(encoding="utf-8")
        self.assertIn("duration-bounce-count: 1", text)
        self.assertIn("total-attempts: 9", text)

    def test_ct2_duration_check_honors_nested_max_ticket_duration_min(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        cfg = ct2 / "config" / "harness.yaml"
        cfg.write_text(
            "circuit_breaker:\n"
            "  max_ticket_duration_min: 1\n"
            "  max_duration_bounces: 3\n"
            "  max_total_attempts: 9\n",
            encoding="utf-8",
        )
        ticket = ct2 / "in-progress" / "001-seal-smoke.md"
        write_ticket(ticket, status="in-progress", sealed="2026-05-12T00:00:00Z")
        from datetime import datetime, timedelta, timezone
        recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        (ct2 / ".meta" / "001.started").write_text(recent + "\n", encoding="utf-8")

        check = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-duration-check", "--json", project], cwd=REPO_ROOT)
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertTrue((ct2 / "backlog" / "001-seal-smoke.md").exists())
        self.assertFalse(ticket.exists())

    def test_ct2_duration_check_honors_nested_max_total_attempts(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        cfg = ct2 / "config" / "harness.yaml"
        cfg.write_text(
            "circuit_breaker:\n"
            "  max_ticket_duration_min: 1\n"
            "  max_duration_bounces: 5\n"
            "  max_total_attempts: 2\n",
            encoding="utf-8",
        )
        ticket = ct2 / "in-progress" / "001-seal-smoke.md"
        write_ticket(ticket, status="in-progress", sealed="2026-05-12T00:00:00Z")
        content = ticket.read_text(encoding="utf-8")
        ticket.write_text(
            content.replace("review-round: 0\n", "review-round: 0\nduration-bounce-count: 0\ntotal-attempts: 1\n"),
            encoding="utf-8",
        )
        from datetime import datetime, timedelta, timezone
        recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        (ct2 / ".meta" / "001.started").write_text(recent + "\n", encoding="utf-8")

        check = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-duration-check", "--json", project], cwd=REPO_ROOT)
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertTrue((ct2 / "escalated" / "001-seal-smoke.md").exists())
        self.assertIn('"total_attempts": 2', check.stdout)
        self.assertFalse(ticket.exists())

    def test_ct2_duration_check_missing_stamp_starts_timer_without_move(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-progress" / "001-seal-smoke.md"
        write_ticket(ticket, status="in-progress", sealed="2026-05-12T00:00:00Z")

        check = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-duration-check", "--json", project], cwd=REPO_ROOT)
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertTrue(ticket.exists())
        self.assertTrue((ct2 / ".meta" / "001.started").exists())

    def test_ct2_revise_resets_duration_bounces_but_preserves_total_attempts(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "escalated" / "001-seal-smoke.md"
        write_ticket(ticket, status="escalated", sealed="2026-05-12T00:00:00Z")
        content = ticket.read_text(encoding="utf-8")
        ticket.write_text(
            content.replace("review-round: 0\n", "review-round: 2\nduration-bounce-count: 3\ntotal-attempts: 8\n"),
            encoding="utf-8",
        )

        revise = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-revise", "001"], cwd=project)
        self.assertEqual(revise.returncode, 0, revise.stderr)

        draft = ct2 / "draft" / "001-seal-smoke.md"
        text = draft.read_text(encoding="utf-8")
        self.assertIn("review-round: 0", text)
        self.assertIn("duration-bounce-count: 0", text)
        self.assertIn("total-attempts: 8", text)

    def test_ct2_verify_rejects_sealed_acceptance_text_drift(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        draft = ct2 / "draft" / "001-seal-smoke.md"
        backlog = ct2 / "backlog" / "001-seal-smoke.md"
        write_ticket(draft)
        seal = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-seal", "001"], cwd=project)
        self.assertEqual(seal.returncode, 0, seal.stderr)

        checkbox_only = backlog.read_text(encoding="utf-8").replace("- [ ] Draft moves to backlog.", "- [x] Draft moves to backlog.")
        backlog.write_text(checkbox_only, encoding="utf-8")
        verify_ok = run_cmd([sys.executable, REPO_ROOT / "bin" / "ct2-verify", "--json", project], cwd=REPO_ROOT)
        self.assertEqual(verify_ok.returncode, 0, verify_ok.stdout + verify_ok.stderr)

        drift = checkbox_only.replace("Draft moves to backlog.", "Draft moves safely to backlog.")
        backlog.write_text(drift, encoding="utf-8")
        verify_drift = run_cmd([sys.executable, REPO_ROOT / "bin" / "ct2-verify", "--json", project], cwd=REPO_ROOT)
        self.assertEqual(verify_drift.returncode, 1)
        self.assertIn("sealed-baseline:001-seal-smoke.md", verify_drift.stdout)

    def test_ct2_verify_treats_missing_legacy_baseline_as_advisory(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        legacy = ct2 / "done" / "900-legacy.md"
        write_ticket(legacy, ticket_id="900", status="done", sealed="2024-01-01T00:00:00Z")

        verify = run_cmd([sys.executable, REPO_ROOT / "bin" / "ct2-verify", "--json", project], cwd=REPO_ROOT)
        self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
        self.assertIn("sealed-baseline:900-legacy.md", verify.stdout)
        report = json.loads(verify.stdout)
        baseline_entry = next(c for c in report["checks"] if c["name"] == "sealed-baseline:900-legacy.md")
        self.assertTrue(baseline_entry["ok"])
        self.assertTrue(baseline_entry.get("advisory"))

    def test_ct2_verify_strict_sealed_baseline_fails_missing(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        legacy = ct2 / "done" / "900-legacy.md"
        write_ticket(legacy, ticket_id="900", status="done", sealed="2024-01-01T00:00:00Z")

        verify = run_cmd(
            [sys.executable, REPO_ROOT / "bin" / "ct2-verify", "--strict-sealed-baseline", "--json", project],
            cwd=REPO_ROOT,
        )
        self.assertEqual(verify.returncode, 1, verify.stdout)
        report = json.loads(verify.stdout)
        baseline_entry = next(c for c in report["checks"] if c["name"] == "sealed-baseline:900-legacy.md")
        self.assertFalse(baseline_entry["ok"])

    def test_ct2_sealed_baseline_backfill_creates_missing_snapshots(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "done" / "900-legacy.md", ticket_id="900", status="done", sealed="2024-01-01T00:00:00Z")
        write_ticket(ct2 / "done" / "901-legacy.md", ticket_id="901", status="done", sealed="2024-01-02T00:00:00Z")

        backfill = run_cmd(
            [sys.executable, REPO_ROOT / "bin" / "ct2-sealed-baseline", "backfill", "--json", project],
            cwd=REPO_ROOT,
        )
        self.assertEqual(backfill.returncode, 0, backfill.stderr)
        self.assertTrue((ct2 / "reviews" / "900-sealed.md").exists())
        self.assertTrue((ct2 / "reviews" / "901-sealed.md").exists())

        verify = run_cmd(
            [sys.executable, REPO_ROOT / "bin" / "ct2-verify", "--strict-sealed-baseline", "--json", project],
            cwd=REPO_ROOT,
        )
        self.assertEqual(verify.returncode, 0, verify.stdout)

        rerun = run_cmd(
            [sys.executable, REPO_ROOT / "bin" / "ct2-sealed-baseline", "backfill", "--json", project],
            cwd=REPO_ROOT,
        )
        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        report = json.loads(rerun.stdout)
        self.assertEqual([], report["created"])
        self.assertIn("900-sealed.md", report["skipped"])

    def test_ct2_verify_still_fails_on_drift_when_baseline_exists(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        draft = ct2 / "draft" / "001-seal-smoke.md"
        backlog = ct2 / "backlog" / "001-seal-smoke.md"
        write_ticket(draft)
        seal = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-seal", "001"], cwd=project)
        self.assertEqual(seal.returncode, 0, seal.stderr)

        drift = backlog.read_text(encoding="utf-8").replace("Draft moves to backlog.", "Draft moves safely to backlog.")
        backlog.write_text(drift, encoding="utf-8")

        verify = run_cmd([sys.executable, REPO_ROOT / "bin" / "ct2-verify", "--json", project], cwd=REPO_ROOT)
        self.assertEqual(verify.returncode, 1, verify.stdout)
        self.assertIn("sealed-baseline:001-seal-smoke.md", verify.stdout)

    def test_ct2_revise_archives_sealed_baseline(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        draft = ct2 / "draft" / "001-seal-smoke.md"
        backlog = ct2 / "backlog" / "001-seal-smoke.md"
        escalated = ct2 / "escalated" / "001-seal-smoke.md"
        write_ticket(draft)
        seal = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-seal", "001"], cwd=project)
        self.assertEqual(seal.returncode, 0, seal.stderr)
        text = backlog.read_text(encoding="utf-8").replace("status: backlog", "status: escalated")
        backlog.rename(escalated)
        escalated.write_text(text, encoding="utf-8")

        revise = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-revise", "001"], cwd=project)
        self.assertEqual(revise.returncode, 0, revise.stderr)
        self.assertFalse((ct2 / "reviews" / "001-sealed.md").exists())
        archived = list((ct2 / "reviews" / ".archive").glob("*-001/001-sealed.md"))
        self.assertEqual(1, len(archived))


if __name__ == "__main__":
    unittest.main()
