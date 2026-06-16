import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run_cmd(args, cwd=None):
    return subprocess.run(
        [str(arg) for arg in args],
        cwd=str(cwd or REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )


def write_ticket(path, ticket_id="001", status="in-review", review_round=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
id: "{ticket_id}"
title: "Reconcile smoke"
status: {status}
priority: medium
created: 2026-05-13T00:00:00Z
updated: 2026-05-13T00:00:00Z
sealed: 2026-05-13T00:00:00Z
branch: feat/{ticket_id}-reconcile-smoke
pr: null
review-round: {review_round}
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
- [x] Exercise reconciliation.

## Constraints
- Use stdlib-only tests.

## Context
Regression fixture.

## Acceptance Criteria
- [x] Reconciler moves the ticket correctly.
""",
        encoding="utf-8",
    )


def write_sidecar(
    path,
    ticket="001-reconcile-smoke",
    reviewer="ct2-lens-cc",
    verdict="approved",
    round_num=0,
    include_timestamp=True,
    include_sections=True,
):
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = "timestamp: 2026-05-13T00:10:00Z\n" if include_timestamp else ""
    body = (
        f"""
## Summary
Fixture review.

## Acceptance Criteria Check
- [x] Reconciler moves the ticket correctly.

## Issues Found
(none)

## Recommendation
{verdict} - fixture.
"""
        if include_sections
        else """
## Summary
Fixture review without the full required body.
"""
    )
    path.write_text(
        f"""---
ticket: {ticket}
reviewer: {reviewer}
round: {round_num}
verdict: {verdict}
{timestamp}---

{body}""",
        encoding="utf-8",
    )


def load_update_verdict_module():
    spec = importlib.util.spec_from_file_location("ct2_update_verdict", REPO_ROOT / "bin" / "_ct2_update_verdict.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def read_frontmatter_value(path, key):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    return None


class ReconcileTest(unittest.TestCase):
    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project])
        self.assertEqual(init.returncode, 0, init.stderr)
        return project

    def reconcile(self, project, ticket_id="001", round_num=0):
        return run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-reconcile", "--project-dir", project, ticket_id, str(round_num)])

    def test_missing_partner_sidecar_is_idempotent_noop(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "in-review" / "001-reconcile-smoke.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md")

        proc = self.reconcile(project)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((ct2 / "in-review" / "001-reconcile-smoke.md").exists())
        self.assertFalse((ct2 / "done" / "001-reconcile-smoke.md").exists())

    def test_dual_approval_moves_to_done_and_updates_frontmatter(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-review" / "001-reconcile-smoke.md"
        write_ticket(ticket)
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", reviewer="ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", reviewer="ct2-lens-cx")

        proc = self.reconcile(project)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        done = ct2 / "done" / "001-reconcile-smoke.md"
        self.assertTrue(done.exists())
        self.assertFalse(ticket.exists())
        text = done.read_text(encoding="utf-8")
        self.assertIn("status: done", text)
        self.assertIn("verdict: approved", text)
        self.assertIn("lens-claude:\n    status: approved\n    sidecar: .ct2/reviews/001-cc-r0.md", text)
        self.assertIn("lens-codex:\n    status: approved\n    sidecar: .ct2/reviews/001-cx-r0.md", text)

    def test_rejection_moves_to_rejected_when_rounds_remain(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "in-review" / "001-reconcile-smoke.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", reviewer="ct2-lens-cc", verdict="approved")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", reviewer="ct2-lens-cx", verdict="rejected")

        proc = self.reconcile(project)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        rejected = ct2 / "rejected" / "001-reconcile-smoke.md"
        self.assertTrue(rejected.exists())
        self.assertIn("status: rejected", rejected.read_text(encoding="utf-8"))
        self.assertIn("verdict: rejected", rejected.read_text(encoding="utf-8"))

    def test_rejection_at_round_cap_escalates_and_notifies_helm(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "in-review" / "001-reconcile-smoke.md", review_round=2)
        write_sidecar(ct2 / "reviews" / "001-cc-r2.md", reviewer="ct2-lens-cc", verdict="rejected", round_num=2)
        write_sidecar(ct2 / "reviews" / "001-cx-r2.md", reviewer="ct2-lens-cx", verdict="approved", round_num=2)

        proc = self.reconcile(project, round_num=2)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        escalated = ct2 / "escalated" / "001-reconcile-smoke.md"
        self.assertTrue(escalated.exists())
        self.assertIn("status: escalated", escalated.read_text(encoding="utf-8"))
        inbox = list((ct2 / "inbox" / "ct2-helm").glob("*.md"))
        self.assertEqual(1, len(inbox))
        self.assertIn("type: escalation", inbox[0].read_text(encoding="utf-8"))

    def test_escalation_message_carries_blocking_digest(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "in-review" / "001-reconcile-smoke.md", review_round=2)
        for side, reviewer in (("cc", "ct2-lens-cc"), ("cx", "ct2-lens-cx")):
            (ct2 / "reviews" / f"001-{side}-r2.md").write_text(
                f'---\nticket: 001-reconcile-smoke\nreviewer: {reviewer}\nround: 2\n'
                "verdict: rejected\ntimestamp: 2026-05-13T00:10:00Z\n---\n\n"
                "## Summary\ns\n\n## Acceptance Criteria Check\n- AC1: fail\n\n"
                "## Issues Found\n### [BLOCKING] Missing input validation on upload\nreject oversized\n\n"
                "## Recommendation\nrejected - fixture.\n",
                encoding="utf-8",
            )

        proc = self.reconcile(project, round_num=2)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        message = list((ct2 / "inbox" / "ct2-helm").glob("*.md"))[0].read_text(encoding="utf-8")
        self.assertIn(".ct2/reviews/001-cc-r2.md", message)
        self.assertIn("### [BLOCKING] Missing input validation on upload", message)

    def test_invalid_sidecar_verdict_does_not_move_ticket(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "in-review" / "001-reconcile-smoke.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", reviewer="ct2-lens-cc", verdict="approved")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", reviewer="ct2-lens-cx", verdict="maybe")

        proc = self.reconcile(project)

        self.assertEqual(proc.returncode, 2)
        self.assertTrue((ct2 / "in-review" / "001-reconcile-smoke.md").exists())
        self.assertFalse((ct2 / "done" / "001-reconcile-smoke.md").exists())

    def test_sidecar_metadata_mismatch_does_not_move_ticket(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-review" / "001-reconcile-smoke.md"
        write_ticket(ticket)
        write_sidecar(
            ct2 / "reviews" / "001-cc-r0.md",
            ticket="999-other-ticket",
            reviewer="ct2-lens-cx",
            round_num=99,
        )
        write_sidecar(
            ct2 / "reviews" / "001-cx-r0.md",
            ticket="999-other-ticket",
            reviewer="ct2-lens-cx",
            round_num=99,
        )

        proc = self.reconcile(project)

        self.assertEqual(proc.returncode, 2)
        self.assertIn("invalid sidecar", proc.stderr)
        self.assertTrue(ticket.exists())
        self.assertFalse((ct2 / "done" / "001-reconcile-smoke.md").exists())

    def test_missing_sidecar_timestamp_or_sections_does_not_move_ticket(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-review" / "001-reconcile-smoke.md"
        write_ticket(ticket)
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", reviewer="ct2-lens-cc", include_timestamp=False)
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", reviewer="ct2-lens-cx", include_sections=False)

        proc = self.reconcile(project)

        self.assertEqual(proc.returncode, 2)
        self.assertIn("timestamp is required", proc.stderr)
        self.assertIn("missing section", proc.stderr)
        self.assertTrue(ticket.exists())
        self.assertFalse((ct2 / "done" / "001-reconcile-smoke.md").exists())

    def test_discover_reconciles_complete_sidecar_pair(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "in-review" / "001-reconcile-smoke.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", reviewer="ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", reviewer="ct2-lens-cx")

        proc = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-reconcile", "--discover", project])

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((ct2 / "done" / "001-reconcile-smoke.md").exists())

    def test_discover_skips_stale_previous_round_pairs(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "in-review" / "001-reconcile-smoke.md", review_round=1)
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", reviewer="ct2-lens-cc", verdict="rejected")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", reviewer="ct2-lens-cx", verdict="rejected")
        write_sidecar(ct2 / "reviews" / "001-cc-r1.md", reviewer="ct2-lens-cc", round_num=1)
        write_sidecar(ct2 / "reviews" / "001-cx-r1.md", reviewer="ct2-lens-cx", round_num=1)

        proc = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-reconcile", "--discover", project])

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((ct2 / "done" / "001-reconcile-smoke.md").exists())

    def test_destination_collision_does_not_mutate_in_review_ticket(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-review" / "001-reconcile-smoke.md"
        done = ct2 / "done" / "001-reconcile-smoke.md"
        write_ticket(ticket)
        write_ticket(done, status="done")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", reviewer="ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", reviewer="ct2-lens-cx")

        proc = self.reconcile(project)

        self.assertEqual(proc.returncode, 2)
        self.assertIn("ambiguous ticket state", proc.stderr)
        self.assertEqual("in-review", read_frontmatter_value(ticket, "status"))
        self.assertEqual("pending", read_frontmatter_value(ticket, "verdict"))
        self.assertTrue(done.exists())

    def test_update_verdict_stages_ticket_rewrite_under_ct2_tmp(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-review" / "001-reconcile-smoke.md"
        write_ticket(ticket)
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", reviewer="ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", reviewer="ct2-lens-cx")
        module = load_update_verdict_module()
        original_mkstemp = module.tempfile.mkstemp
        staging_dirs = []

        def spy_mkstemp(*args, **kwargs):
            staging_dirs.append(Path(kwargs["dir"]).resolve())
            return original_mkstemp(*args, **kwargs)

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            module.tempfile.mkstemp = spy_mkstemp
            module.rewrite(str(ticket), "approved", ".ct2/reviews/001-cc-r0.md", ".ct2/reviews/001-cx-r0.md")
        finally:
            module.tempfile.mkstemp = original_mkstemp
            os.chdir(old_cwd)

        self.assertEqual([(ct2 / ".tmp").resolve()], staging_dirs)
        self.assertEqual([], list((ct2 / "in-review").glob(".*.tmp")))

    def test_stale_lock_is_recovered(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "in-review" / "001-reconcile-smoke.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", reviewer="ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", reviewer="ct2-lens-cx")
        lock = ct2 / ".meta" / "001-r0-reconcile.lock"
        lock.write_text("999999\n", encoding="utf-8")
        os.utime(lock, (0, 0))

        proc = self.reconcile(project)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((ct2 / "done" / "001-reconcile-smoke.md").exists())
        self.assertFalse(lock.exists())

    def test_concurrent_invocations_leave_one_terminal_ticket(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "in-review" / "001-reconcile-smoke.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", reviewer="ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", reviewer="ct2-lens-cx")
        cmd = [PYTHON, str(REPO_ROOT / "bin" / "ct2-reconcile"), "--project-dir", str(project), "001", "0"]

        p1 = subprocess.Popen(cmd, cwd=str(REPO_ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p2 = subprocess.Popen(cmd, cwd=str(REPO_ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out1, err1 = p1.communicate(timeout=30)
        out2, err2 = p2.communicate(timeout=30)

        self.assertEqual(p1.returncode, 0, err1)
        self.assertEqual(p2.returncode, 0, err2)
        self.assertEqual([ct2 / "done" / "001-reconcile-smoke.md"], list((ct2 / "done").glob("001-*.md")))
        self.assertEqual([], list((ct2 / "in-review").glob("001-*.md")))
        self.assertFalse((ct2 / ".meta" / "001-r0-reconcile.lock").exists())
        self.assertTrue(out1 or out2)


if __name__ == "__main__":
    unittest.main()
