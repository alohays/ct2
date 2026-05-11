import json
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


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_ticket(path, ticket_id="001", status="done", review_round=0, ac_checked=True):
    marker = "x" if ac_checked else " "
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
id: "{ticket_id}"
title: "Audit ticket"
status: {status}
priority: medium
created: 2026-05-12T00:00:00Z
updated: 2026-05-12T01:00:00Z
sealed: 2026-05-12T00:10:00Z
branch: feat/{ticket_id}-audit-ticket
pr: null
review-round: {review_round}
estimated-scope: small
touched-files:
  - README.md
review-status:
  lens-claude:
    status: approved
    sidecar: reviews/{ticket_id}-cc-r{review_round}.md
  lens-codex:
    status: approved
    sidecar: reviews/{ticket_id}-cx-r{review_round}.md
verdict: approved
---

## Requirements
- [{marker}] Exercise ticket audit.

## Constraints
- Use stdlib-only tests.

## Context
Regression fixture for ticket evidence auditing.

## Acceptance Criteria
- [{marker}] Ticket audit reports concrete readiness checks.
""",
        encoding="utf-8",
    )


def write_sidecar(path, ticket="001-audit-ticket", reviewer="ct2-lens-cx", verdict="approved"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
ticket: "{ticket}"
reviewer: {reviewer}
round: 0
verdict: {verdict}
timestamp: 2026-05-12T01:00:00Z
---

## Summary
Approved fixture.

## Acceptance Criteria Check
- [x] Ticket audit reports concrete readiness checks.

## Issues Found
(none)

## Recommendation
approved - fixture passes.
""",
        encoding="utf-8",
    )


class TicketAuditTest(unittest.TestCase):
    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project])
        self.assertEqual(init.returncode, 0, init.stderr)
        return project

    def test_ticket_audit_accepts_done_ticket_with_evidence(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "done" / "001-audit-ticket.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", reviewer="ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", reviewer="ct2-lens-cx")
        (ct2 / "plans" / "001-r0.md").write_text("# Plan\n", encoding="utf-8")
        write_jsonl(
            ct2 / "evidence" / "claims.jsonl",
            [{"id": "ev-001", "ticket": "001", "kind": "verifier", "ok": True, "path": ".ct2/evidence/verifiers/ev-001.json"}],
        )

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", project])
        self.assertEqual(audit.returncode, 0, audit.stderr)
        report = json.loads(audit.stdout)
        self.assertTrue(report["complete"])
        self.assertEqual(1, report["tickets_checked"])
        checks = {check["name"]: check["ok"] for check in report["tickets"][0]["checks"]}
        self.assertTrue(checks["status_matches_directory"])
        self.assertTrue(checks["plan_evidence"])
        self.assertTrue(checks["acceptance_criteria_checked"])
        self.assertTrue(checks["dual_approved_sidecars"])
        self.assertTrue(checks["evidence_claim"])

    def test_ticket_audit_rejects_done_ticket_missing_completion_evidence(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "done" / "001-audit-ticket.md", status="in-review", ac_checked=False)

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", project])
        self.assertEqual(audit.returncode, 1)
        report = json.loads(audit.stdout)
        self.assertFalse(report["complete"])
        checks = {check["name"]: check["ok"] for check in report["tickets"][0]["checks"]}
        self.assertFalse(checks["status_matches_directory"])
        self.assertFalse(checks["plan_evidence"])
        self.assertFalse(checks["acceptance_criteria_checked"])
        self.assertFalse(checks["dual_approved_sidecars"])
        self.assertFalse(checks["evidence_claim"])

    def test_ticket_audit_filters_by_ticket_id(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "backlog" / "001-audit-ticket.md", status="backlog")
        write_ticket(ct2 / "backlog" / "002-audit-ticket.md", ticket_id="002", status="backlog")

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", "--ticket", "002", project])
        self.assertEqual(audit.returncode, 0, audit.stderr)
        report = json.loads(audit.stdout)
        self.assertEqual(1, report["tickets_checked"])
        self.assertEqual("002-audit-ticket.md", report["tickets"][0]["ticket"])


if __name__ == "__main__":
    unittest.main()
