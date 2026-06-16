import importlib.machinery
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
sys.path.insert(0, str(REPO_ROOT / "bin"))
from _ct2_sealed_baseline import sealed_snapshot_name, write_snapshot  # noqa: E402


def run_cmd(args, cwd=None):
    return subprocess.run(
        [str(arg) for arg in args],
        cwd=str(cwd or REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )


def write_in_review(path, verification=None, ac_checked=True, review_round=0):
    marker = "x" if ac_checked else " "
    body = f"""---
id: "001"
title: "Done gate fixture"
status: in-review
priority: medium
created: 2026-06-16T00:00:00Z
updated: 2026-06-16T01:00:00Z
sealed: 2026-06-16T00:10:00Z
branch: null
pr: null
review-round: {review_round}
estimated-scope: small
touched-files:
  - README.md
review-status:
  lens-claude:
    status: approved
    sidecar: reviews/001-cc-r{review_round}.md
  lens-codex:
    status: approved
    sidecar: reviews/001-cx-r{review_round}.md
verdict: pending
---

## Requirements
- Build the done gate correctly.

## Constraints
- Use stdlib only here.

## Context
Regression fixture exercising the reconciler done gate end to end.

## Acceptance Criteria
- [{marker}] First criterion is met.
- [{marker}] Second criterion is met.
"""
    if verification is not None:
        body += f"\n## Verification\n{verification}\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    snapshot = path.parent.parent / "reviews" / sealed_snapshot_name(path)
    write_snapshot(path, snapshot)


def write_sidecar(path, reviewer, round_num=0, verdict="approved"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
ticket: "001-done-gate-fixture"
reviewer: {reviewer}
round: {round_num}
verdict: {verdict}
timestamp: 2026-06-16T01:00:00Z
---

## Summary
Approved fixture.

## Acceptance Criteria Check
- [x] First criterion is met.

## Issues Found
(none)

## Recommendation
approved - fixture passes.
""",
        encoding="utf-8",
    )


def write_evidence(ct2, ev_id, round_num, ac=None, ok=True):
    artifact = ct2 / "evidence" / "commands" / f"{ev_id}.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("{}", encoding="utf-8")
    row = {
        "id": ev_id,
        "ticket": "001",
        "kind": "command",
        "ok": ok,
        "path": f".ct2/evidence/commands/{ev_id}.json",
        "round": str(round_num),
    }
    if ac is not None:
        row["ac"] = str(ac)
    claims = ct2 / "evidence" / "claims.jsonl"
    claims.parent.mkdir(parents=True, exist_ok=True)
    with claims.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def load_reconcile_module():
    loader = importlib.machinery.SourceFileLoader("ct2_reconcile_mod", str(REPO_ROOT / "bin" / "ct2-reconcile"))
    spec = importlib.util.spec_from_loader("ct2_reconcile_mod", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class DoneGateAuditTest(unittest.TestCase):
    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project])
        self.assertEqual(init.returncode, 0, init.stderr)
        return project

    def ready_ticket(self, project, verification=None, bound_ac_evidence=True):
        ct2 = project / ".ct2"
        write_in_review(ct2 / "in-review" / "001-done-gate-fixture.md", verification=verification)
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", "ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", "ct2-lens-cx")
        (ct2 / "plans" / "001-r0.md").write_text("# Plan\n", encoding="utf-8")
        if verification and bound_ac_evidence:
            write_evidence(ct2, "ev-ac1", 0, ac=1)
            write_evidence(ct2, "ev-ac2", 0, ac=2)
        elif not verification:
            write_evidence(ct2, "ev-generic", 0)
        return ct2

    def done_gate_checks(self, project):
        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", "--done-gate", "--ticket", "001", project])
        return {c["name"]: c for c in json.loads(audit.stdout)["tickets"][0]["checks"]}, audit.returncode

    def test_done_gate_passes_when_ready_no_bindings(self):
        project = self.make_project()
        self.ready_ticket(project)
        checks, _ = self.done_gate_checks(project)
        for name in ("done_gate_state", "acceptance_criteria_checked", "sealed_baseline", "plan_evidence", "dual_approved_sidecars", "done_gate_evidence"):
            self.assertTrue(checks[name]["ok"], f"{name} should pass: {checks[name]}")

    def test_done_gate_fails_without_round_fresh_evidence(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_in_review(ct2 / "in-review" / "001-done-gate-fixture.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", "ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", "ct2-lens-cx")
        (ct2 / "plans" / "001-r0.md").write_text("# Plan\n", encoding="utf-8")
        # No evidence claims at all.
        checks, _ = self.done_gate_checks(project)
        self.assertFalse(checks["done_gate_evidence"]["ok"])

    def test_done_gate_requires_evidence_for_every_bound_ac(self):
        project = self.make_project()
        ct2 = self.ready_ticket(project, verification="- AC1: `true`\n- AC2: `true`", bound_ac_evidence=False)
        write_evidence(ct2, "ev-ac1", 0, ac=1)  # AC2 has no round-fresh evidence
        checks, _ = self.done_gate_checks(project)
        self.assertFalse(checks["done_gate_evidence"]["ok"])
        self.assertIn("2", checks["done_gate_evidence"]["evidence"]["missing_acs"])

    def test_done_gate_evidence_is_round_keyed(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_in_review(ct2 / "in-review" / "001-done-gate-fixture.md", review_round=1)
        write_sidecar(ct2 / "reviews" / "001-cc-r1.md", "ct2-lens-cc", round_num=1)
        write_sidecar(ct2 / "reviews" / "001-cx-r1.md", "ct2-lens-cx", round_num=1)
        (ct2 / "plans" / "001-r1.md").write_text("# Plan\n", encoding="utf-8")
        write_evidence(ct2, "ev-stale", 0)  # round 0 evidence, ticket is round 1
        checks, _ = self.done_gate_checks(project)
        self.assertFalse(checks["done_gate_evidence"]["ok"])

        write_evidence(ct2, "ev-fresh", 1)  # now round 1 evidence exists
        checks, _ = self.done_gate_checks(project)
        self.assertTrue(checks["done_gate_evidence"]["ok"])

    def test_done_gate_requires_ticket(self):
        project = self.make_project()
        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", "--done-gate", project])
        self.assertEqual(audit.returncode, 1)
        self.assertIn("--done-gate requires --ticket", json.loads(audit.stdout)["errors"])


class ReconcilerDoneGateTest(DoneGateAuditTest):
    def helm_messages(self, ct2):
        return sorted((ct2 / "inbox" / "ct2-helm").glob("msg-*.md"))

    def test_advisory_moves_to_done_and_sends_one_message_on_gate_failure(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_in_review(ct2 / "in-review" / "001-done-gate-fixture.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", "ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", "ct2-lens-cx")
        (ct2 / "plans" / "001-r0.md").write_text("# Plan\n", encoding="utf-8")
        # No round-fresh evidence -> gate fails, but advisory still moves.

        reconcile = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-reconcile", "001", "0", "--project-dir", project])
        self.assertEqual(reconcile.returncode, 0, reconcile.stderr)
        self.assertTrue((ct2 / "done" / "001-done-gate-fixture.md").exists())
        self.assertIn("done gate failing (advisory", reconcile.stderr)
        messages = self.helm_messages(ct2)
        self.assertEqual(1, len(messages))
        self.assertIn("done gate failed", messages[0].read_text(encoding="utf-8"))

    def test_no_done_gate_message_when_gate_passes(self):
        project = self.make_project()
        ct2 = self.ready_ticket(project)
        reconcile = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-reconcile", "001", "0", "--project-dir", project])
        self.assertEqual(reconcile.returncode, 0, reconcile.stderr)
        self.assertTrue((ct2 / "done" / "001-done-gate-fixture.md").exists())
        self.assertEqual([], self.helm_messages(ct2))

    def test_hard_gate_withholds_done_and_dedups_message(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_in_review(ct2 / "in-review" / "001-done-gate-fixture.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", "ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", "ct2-lens-cx")
        (ct2 / "plans" / "001-r0.md").write_text("# Plan\n", encoding="utf-8")

        module = load_reconcile_module()
        module.DONE_GATE_HARD = True
        rc1 = module.reconcile_one(project.resolve(), "001", "0", "ct2-reconcile")
        self.assertEqual(3, rc1)
        self.assertTrue((ct2 / "in-review" / "001-done-gate-fixture.md").exists())
        self.assertFalse((ct2 / "done" / "001-done-gate-fixture.md").exists())
        self.assertTrue((ct2 / ".meta" / "001-r0.done-gate-failed").exists())
        self.assertEqual(1, len(self.helm_messages(ct2)))

        rc2 = module.reconcile_one(project.resolve(), "001", "0", "ct2-reconcile")
        self.assertEqual(3, rc2)
        self.assertEqual(1, len(self.helm_messages(ct2)), "second run must not mint a duplicate message")

    def test_advisory_failure_leaves_no_orphan_stamp(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_in_review(ct2 / "in-review" / "001-done-gate-fixture.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", "ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", "ct2-lens-cx")
        (ct2 / "plans" / "001-r0.md").write_text("# Plan\n", encoding="utf-8")

        run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-reconcile", "001", "0", "--project-dir", project])
        self.assertTrue((ct2 / "done" / "001-done-gate-fixture.md").exists())
        self.assertFalse((ct2 / ".meta" / "001-r0.done-gate-failed").exists(), "stamp must be cleared after the move")

    def test_discover_aggregation_ranks_hard_errors_above_withhold(self):
        module = load_reconcile_module()
        self.assertEqual(1, module.discover_worst(3, 1), "a hard arg error must dominate a done-gate withhold")
        self.assertEqual(2, module.discover_worst(3, 2), "an invalid-sidecar error must dominate a withhold")
        self.assertEqual(2, module.discover_worst(1, 2))
        self.assertEqual(3, module.discover_worst(0, 3), "a withhold outranks clean success")
        self.assertEqual(3, module.discover_worst(3, 0), "success must not lower a withhold")


class WatchdogApprovedUnverifiedTest(DoneGateAuditTest):
    def test_watchdog_escalates_approved_but_unverified_overdue(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        cfg = ct2 / "config" / "harness.yaml"
        cfg.write_text("circuit_breaker:\n  max_review_duration_min: 1\n", encoding="utf-8")
        write_in_review(ct2 / "in-review" / "001-done-gate-fixture.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", "ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", "ct2-lens-cx")
        overdue = (datetime.now(timezone.utc) - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        (ct2 / ".meta" / "001.in-review").write_text(overdue + "\n", encoding="utf-8")

        watchdog = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-review-watchdog", "--json", project])
        self.assertEqual(watchdog.returncode, 0, watchdog.stderr)
        self.assertTrue((ct2 / "escalated" / "001-done-gate-fixture.md").exists())
        report = json.loads(watchdog.stdout)
        self.assertEqual("approved-but-unverified", report["escalations"][0]["reason"])
        message = sorted((ct2 / "inbox" / "ct2-helm").glob("msg-*.md"))[0].read_text(encoding="utf-8")
        self.assertIn("dual-approved but unverified", message)

    def test_watchdog_ignores_dual_approved_not_overdue(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        cfg = ct2 / "config" / "harness.yaml"
        cfg.write_text("circuit_breaker:\n  max_review_duration_min: 1000\n", encoding="utf-8")
        write_in_review(ct2 / "in-review" / "001-done-gate-fixture.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", "ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", "ct2-lens-cx")
        recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        (ct2 / ".meta" / "001.in-review").write_text(recent + "\n", encoding="utf-8")

        watchdog = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-review-watchdog", "--json", project])
        self.assertEqual(watchdog.returncode, 0, watchdog.stderr)
        self.assertFalse((ct2 / "escalated" / "001-done-gate-fixture.md").exists())

    def test_watchdog_ignores_partial_rejection(self):
        # Both sidecars present but one rejected is NOT approved-but-unverified —
        # the reconciler routes it to rework, not the watchdog escalation path.
        project = self.make_project()
        ct2 = project / ".ct2"
        cfg = ct2 / "config" / "harness.yaml"
        cfg.write_text("circuit_breaker:\n  max_review_duration_min: 1\n", encoding="utf-8")
        write_in_review(ct2 / "in-review" / "001-done-gate-fixture.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", "ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", "ct2-lens-cx", verdict="rejected")
        overdue = (datetime.now(timezone.utc) - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        (ct2 / ".meta" / "001.in-review").write_text(overdue + "\n", encoding="utf-8")

        watchdog = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-review-watchdog", "--json", project])
        self.assertEqual(watchdog.returncode, 0, watchdog.stderr)
        self.assertFalse((ct2 / "escalated" / "001-done-gate-fixture.md").exists())


if __name__ == "__main__":
    unittest.main()
