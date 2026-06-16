import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
sys.path.insert(0, str(REPO_ROOT / "bin"))
from _ct2_sealed_baseline import compare_ticket_to_snapshot, sealed_snapshot_name, write_snapshot  # noqa: E402


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


def write_ticket(
    path,
    ticket_id="001",
    status="done",
    review_round=0,
    ac_checked=True,
    verdict="approved",
    sealed="2026-05-12T00:10:00Z",
    plan_exempt=None,
    include_id=True,
):
    marker = "x" if ac_checked else " "
    id_line = f'id: "{ticket_id}"\n' if include_id else ""
    exempt_line = f"plan-exempt: {plan_exempt}\n" if plan_exempt is not None else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
{id_line}\
title: "Audit ticket"
status: {status}
priority: medium
created: 2026-05-12T00:00:00Z
updated: 2026-05-12T01:00:00Z
sealed: {sealed}
branch: feat/{ticket_id}-audit-ticket
pr: null
review-round: {review_round}
{exempt_line}\
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
verdict: {verdict}
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
    if include_id and status != "draft":
        ct2_dir = path.parent.parent
        snapshot = ct2_dir / "reviews" / sealed_snapshot_name(path)
        write_snapshot(path, snapshot)


def write_sidecar(path, ticket="001-audit-ticket", reviewer="ct2-lens-cx", verdict="approved", round_num=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
ticket: "{ticket}"
reviewer: {reviewer}
round: {round_num}
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
        (ct2 / "evidence" / "verifiers" / "ev-001.json").write_text("{}", encoding="utf-8")
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
        self.assertTrue(checks["verdict_approved"])
        self.assertTrue(checks["evidence_claim"])

    def test_ticket_audit_rejects_done_ticket_missing_completion_evidence(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "done" / "001-audit-ticket.md", status="in-review", ac_checked=False, verdict="pending")

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", project])
        self.assertEqual(audit.returncode, 1)
        report = json.loads(audit.stdout)
        self.assertFalse(report["complete"])
        checks = {check["name"]: check["ok"] for check in report["tickets"][0]["checks"]}
        self.assertFalse(checks["status_matches_directory"])
        self.assertFalse(checks["plan_evidence"])
        self.assertFalse(checks["acceptance_criteria_checked"])
        self.assertFalse(checks["dual_approved_sidecars"])
        self.assertFalse(checks["verdict_approved"])
        self.assertFalse(checks["evidence_claim"])

    def test_ticket_audit_rejects_done_ticket_with_missing_required_frontmatter(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "done" / "001-audit-ticket.md", include_id=False)
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", reviewer="ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", reviewer="ct2-lens-cx")
        (ct2 / "plans" / "001-r0.md").write_text("# Plan\n", encoding="utf-8")
        (ct2 / "evidence" / "verifiers" / "ev-001.json").write_text("{}", encoding="utf-8")
        write_jsonl(
            ct2 / "evidence" / "claims.jsonl",
            [{"id": "ev-001", "ticket": "001", "kind": "verifier", "ok": True, "path": ".ct2/evidence/verifiers/ev-001.json"}],
        )

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", project])
        self.assertEqual(audit.returncode, 1)
        report = json.loads(audit.stdout)
        checks = {check["name"]: check for check in report["tickets"][0]["checks"]}
        self.assertFalse(checks["required_frontmatter"]["ok"])
        self.assertIn("id", checks["required_frontmatter"]["evidence"]["missing"])
        self.assertFalse(checks["id_matches_filename"]["ok"])

    def test_ticket_audit_rejects_done_ticket_with_pending_verdict(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "done" / "001-audit-ticket.md", verdict="pending")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", reviewer="ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", reviewer="ct2-lens-cx")
        (ct2 / "plans" / "001-r0.md").write_text("# Plan\n", encoding="utf-8")
        (ct2 / "evidence" / "verifiers" / "ev-001.json").write_text("{}", encoding="utf-8")
        write_jsonl(
            ct2 / "evidence" / "claims.jsonl",
            [{"id": "ev-001", "ticket": "001", "kind": "verifier", "ok": True, "path": ".ct2/evidence/verifiers/ev-001.json"}],
        )

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", project])
        self.assertEqual(audit.returncode, 1)
        checks = {check["name"]: check["ok"] for check in json.loads(audit.stdout)["tickets"][0]["checks"]}
        self.assertFalse(checks["verdict_approved"])

    def test_ticket_audit_rejects_malformed_approved_sidecar_metadata(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "done" / "001-audit-ticket.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", ticket="999-wrong-ticket", reviewer="ct2-lens-cx", round_num=99)
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", ticket="999-wrong-ticket", reviewer="ct2-lens-cc", round_num=99)
        (ct2 / "plans" / "001-r0.md").write_text("# Plan\n", encoding="utf-8")
        (ct2 / "evidence" / "verifiers" / "ev-001.json").write_text("{}", encoding="utf-8")
        write_jsonl(
            ct2 / "evidence" / "claims.jsonl",
            [{"id": "ev-001", "ticket": "001", "kind": "verifier", "ok": True, "path": ".ct2/evidence/verifiers/ev-001.json"}],
        )

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", project])
        self.assertEqual(audit.returncode, 1)
        checks = {check["name"]: check["ok"] for check in json.loads(audit.stdout)["tickets"][0]["checks"]}
        self.assertFalse(checks["dual_approved_sidecars"])

    def test_ticket_audit_rejects_rejected_sidecar_verdict(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "done" / "001-audit-ticket.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", reviewer="ct2-lens-cc", verdict="rejected")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", reviewer="ct2-lens-cx")
        (ct2 / "plans" / "001-r0.md").write_text("# Plan\n", encoding="utf-8")
        (ct2 / "evidence" / "verifiers" / "ev-001.json").write_text("{}", encoding="utf-8")
        write_jsonl(
            ct2 / "evidence" / "claims.jsonl",
            [{"id": "ev-001", "ticket": "001", "kind": "verifier", "ok": True, "path": ".ct2/evidence/verifiers/ev-001.json"}],
        )

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", project])
        self.assertEqual(audit.returncode, 1)
        checks = {check["name"]: check["ok"] for check in json.loads(audit.stdout)["tickets"][0]["checks"]}
        self.assertFalse(checks["dual_approved_sidecars"])

    def test_ticket_audit_rejects_stale_evidence_claim_path(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "done" / "001-audit-ticket.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", reviewer="ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", reviewer="ct2-lens-cx")
        (ct2 / "plans" / "001-r0.md").write_text("# Plan\n", encoding="utf-8")
        write_jsonl(
            ct2 / "evidence" / "claims.jsonl",
            [{"id": "ev-001", "ticket": "001-audit-ticket.md", "kind": "verifier", "ok": True, "path": ".ct2/evidence/verifiers/missing.json"}],
        )

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", project])
        self.assertEqual(audit.returncode, 1)
        checks = {check["name"]: check["ok"] for check in json.loads(audit.stdout)["tickets"][0]["checks"]}
        self.assertFalse(checks["evidence_claim"])

    def test_ticket_audit_requires_structured_plan_exempt_reason(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-review" / "001-audit-ticket.md"
        write_ticket(ticket, status="in-review")
        ticket.write_text(ticket.read_text(encoding="utf-8") + "\nThis is not plan-exempt.\n", encoding="utf-8")

        missing = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", project])
        self.assertEqual(missing.returncode, 1)
        checks = {check["name"]: check["ok"] for check in json.loads(missing.stdout)["tickets"][0]["checks"]}
        self.assertFalse(checks["plan_evidence"])

        ticket.unlink()
        write_ticket(ticket, status="in-review", plan_exempt="low-risk-doc-only")
        exempt = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", project])
        self.assertEqual(exempt.returncode, 0, exempt.stderr)

    def test_plan_audit_requires_structured_plan_exempt_reason(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "in-review" / "001-audit-ticket.md"
        write_ticket(ticket, status="in-review")
        ticket.write_text(ticket.read_text(encoding="utf-8") + "\nThis is not plan-exempt.\n", encoding="utf-8")

        missing = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-plan-audit", "--json", project])
        self.assertEqual(missing.returncode, 1)

        ticket.unlink()
        write_ticket(ticket, status="in-review", plan_exempt="low-risk-doc-only")
        exempt = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-plan-audit", "--json", project])
        self.assertEqual(exempt.returncode, 0, exempt.stderr)

    def test_ticket_audit_filters_by_ticket_id_stem_or_filename(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "backlog" / "001-audit-ticket.md", status="backlog")
        write_ticket(ct2 / "backlog" / "002-audit-ticket.md", ticket_id="002", status="backlog")

        for query in ("002", "002-audit-ticket", "002-audit-ticket.md"):
            with self.subTest(query=query):
                audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", "--ticket", query, project])
                self.assertEqual(audit.returncode, 0, audit.stderr)
                report = json.loads(audit.stdout)
                self.assertEqual(1, report["tickets_checked"])
                self.assertEqual("002-audit-ticket.md", report["tickets"][0]["ticket"])

    def test_ticket_audit_seal_gate_accepts_valid_draft(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "draft" / "001-audit-ticket.md", status="draft", ac_checked=False, verdict="pending")

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", "--seal-gate", "--ticket", "001", project])
        self.assertEqual(audit.returncode, 0, audit.stderr)
        report = json.loads(audit.stdout)
        self.assertTrue(report["complete"])
        checks = {check["name"]: check["ok"] for check in report["tickets"][0]["checks"]}
        self.assertTrue(checks["seal_gate_state"])
        self.assertTrue(checks["seal_gate_required_sections"])
        self.assertTrue(checks["seal_gate_acceptance_criteria_verifiable"])

    def test_ticket_audit_seal_gate_rejects_unverifiable_draft(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "draft" / "001-audit-ticket.md"
        write_ticket(ticket, status="draft", ac_checked=False, verdict="pending")
        ticket.write_text(
            ticket.read_text(encoding="utf-8").replace(
                "Ticket audit reports concrete readiness checks.",
                "TBD",
            ),
            encoding="utf-8",
        )

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", "--seal-gate", "--ticket", "001", project])
        self.assertEqual(audit.returncode, 1)
        checks = {check["name"]: check["ok"] for check in json.loads(audit.stdout)["tickets"][0]["checks"]}
        self.assertFalse(checks["seal_gate_acceptance_criteria_verifiable"])

    def test_ticket_audit_seal_gate_accepts_domain_unknown(self):
        # Regression for PR #32 review: "unknown" is real domain vocabulary
        # (provider states, error classes, etc.) and a substring match must
        # not reject otherwise valid tickets.
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "draft" / "001-audit-ticket.md"
        write_ticket(ticket, status="draft", ac_checked=False, verdict="pending")
        ticket.write_text(
            ticket.read_text(encoding="utf-8")
            .replace(
                "Exercise ticket audit.",
                "Handle unknown provider statuses without crashing the IDP integration.",
            )
            .replace(
                "Regression fixture for ticket evidence auditing.",
                "Provider responses may include `status: unknown` values when "
                "upstream tokens have not yet propagated; we currently raise "
                "instead of treating them as transient.",
            )
            .replace(
                "Ticket audit reports concrete readiness checks.",
                "Reject requests with unknown auth headers and emit a structured 401 response.",
            ),
            encoding="utf-8",
        )

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", "--seal-gate", "--ticket", "001", project])
        self.assertEqual(audit.returncode, 0, audit.stdout + audit.stderr)
        report = json.loads(audit.stdout)
        self.assertTrue(report["complete"])
        checks = {check["name"]: check["ok"] for check in report["tickets"][0]["checks"]}
        self.assertTrue(checks["seal_gate_requirements_complete"])
        self.assertTrue(checks["seal_gate_context_complete"])
        self.assertTrue(checks["seal_gate_acceptance_criteria_verifiable"])

    def test_ticket_audit_seal_gate_accepts_test_retention_constraint(self):
        # Regression for PR #32 review: "no tests may be removed" is a
        # retention constraint, not a ban on adding tests, and must not
        # be flagged as a contradiction with "tests pass".
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "draft" / "001-audit-ticket.md"
        write_ticket(ticket, status="draft", ac_checked=False, verdict="pending")
        ticket.write_text(
            ticket.read_text(encoding="utf-8")
            .replace(
                "Use stdlib-only tests.",
                "No tests may be removed during the lifecycle migration.",
            )
            .replace(
                "Ticket audit reports concrete readiness checks.",
                "Tests pass after the lifecycle change.",
            ),
            encoding="utf-8",
        )

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", "--seal-gate", "--ticket", "001", project])
        self.assertEqual(audit.returncode, 0, audit.stdout + audit.stderr)
        checks = {check["name"]: check["ok"] for check in json.loads(audit.stdout)["tickets"][0]["checks"]}
        self.assertTrue(checks["seal_gate_no_static_contradictions"])

    def test_ticket_audit_seal_gate_still_flags_explicit_no_tests_ban(self):
        # Positive control: an explicit "do not add tests" should still flag.
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "draft" / "001-audit-ticket.md"
        write_ticket(ticket, status="draft", ac_checked=False, verdict="pending")
        ticket.write_text(
            ticket.read_text(encoding="utf-8")
            .replace(
                "Use stdlib-only tests.",
                "Do not add tests for this ticket.",
            )
            .replace(
                "Ticket audit reports concrete readiness checks.",
                "Tests pass after the lifecycle change.",
            ),
            encoding="utf-8",
        )

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", "--seal-gate", "--ticket", "001", project])
        self.assertEqual(audit.returncode, 1, audit.stdout)
        checks = {check["name"]: check["ok"] for check in json.loads(audit.stdout)["tickets"][0]["checks"]}
        self.assertFalse(checks["seal_gate_no_static_contradictions"])

    def test_ticket_audit_submit_gate_accepts_ready_in_progress(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "in-progress" / "001-audit-ticket.md", status="in-progress", ac_checked=True, verdict="pending")
        (ct2 / "plans" / "001-r0.md").write_text("# Plan\n", encoding="utf-8")

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", "--submit-gate", "--ticket", "001", project])
        report = json.loads(audit.stdout)
        checks = {check["name"]: check["ok"] for check in report["tickets"][0]["checks"]}
        self.assertTrue(checks["submit_gate_state"])
        self.assertTrue(checks["acceptance_criteria_checked"])
        self.assertTrue(checks["plan_evidence"])

    def test_ticket_audit_submit_gate_lists_unchecked_acs(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "in-progress" / "001-audit-ticket.md", status="in-progress", ac_checked=False, verdict="pending")
        (ct2 / "plans" / "001-r0.md").write_text("# Plan\n", encoding="utf-8")

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", "--submit-gate", "--ticket", "001", project])
        checks = {check["name"]: check for check in json.loads(audit.stdout)["tickets"][0]["checks"]}
        self.assertFalse(checks["acceptance_criteria_checked"]["ok"])
        self.assertIn(
            "Ticket audit reports concrete readiness checks.",
            checks["acceptance_criteria_checked"]["evidence"]["unchecked"],
        )

    def test_ticket_audit_submit_gate_flags_wrong_state(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "backlog" / "001-audit-ticket.md", status="backlog", ac_checked=False, verdict="pending")

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", "--submit-gate", "--ticket", "001", project])
        checks = {check["name"]: check["ok"] for check in json.loads(audit.stdout)["tickets"][0]["checks"]}
        self.assertFalse(checks["submit_gate_state"])

    def test_ticket_audit_submit_gate_requires_ticket(self):
        project = self.make_project()
        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", "--submit-gate", project])
        self.assertEqual(audit.returncode, 1)
        self.assertIn("--submit-gate requires --ticket", json.loads(audit.stdout)["errors"])

    def test_ticket_audit_rejects_sealed_baseline_drift(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "backlog" / "001-audit-ticket.md"
        write_ticket(ticket, status="backlog")
        ticket.write_text(
            ticket.read_text(encoding="utf-8").replace(
                "Ticket audit reports concrete readiness checks.",
                "Ticket audit reports altered readiness checks.",
            ),
            encoding="utf-8",
        )

        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", project])
        self.assertEqual(audit.returncode, 1)
        self.assertIn("sealed_baseline", audit.stdout)


    # ── ## Verification: conditional 4th sealed section (T1.1) ──────────────

    def _draft_with_verification(self, ct2, verification):
        ticket = ct2 / "draft" / "001-audit-ticket.md"
        write_ticket(ticket, status="draft", ac_checked=False, verdict="pending")
        ticket.write_text(ticket.read_text(encoding="utf-8") + verification, encoding="utf-8")
        return ticket

    def test_sealed_baseline_seals_verification_and_detects_command_drift(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = self._draft_with_verification(ct2, "\n## Verification\n- AC1: `python -m unittest`\n")
        snapshot = ct2 / "reviews" / sealed_snapshot_name(ticket)
        write_snapshot(ticket, snapshot)
        self.assertIn("verification-sha256", snapshot.read_text(encoding="utf-8"))
        ok, _ = compare_ticket_to_snapshot(ticket, snapshot)
        self.assertTrue(ok)

        # Weakening the bound command after seal is sealed-baseline drift.
        ticket.write_text(
            ticket.read_text(encoding="utf-8").replace("python -m unittest", "true"),
            encoding="utf-8",
        )
        ok, evidence = compare_ticket_to_snapshot(ticket, snapshot)
        self.assertFalse(ok)
        self.assertIn("verification-sha256", evidence["mismatches"])

    def test_sealed_baseline_absent_verification_is_ok(self):
        # Legacy / no-verification tickets: absent in both ticket and snapshot.
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "backlog" / "001-audit-ticket.md"
        write_ticket(ticket, status="backlog")
        snapshot = ct2 / "reviews" / sealed_snapshot_name(ticket)
        self.assertNotIn("verification-sha256", snapshot.read_text(encoding="utf-8"))
        ok, _ = compare_ticket_to_snapshot(ticket, snapshot)
        self.assertTrue(ok)

    def test_sealed_baseline_added_verification_after_seal_is_drift(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        ticket = ct2 / "backlog" / "001-audit-ticket.md"
        write_ticket(ticket, status="backlog")
        snapshot = ct2 / "reviews" / sealed_snapshot_name(ticket)
        # Snapshot sealed WITHOUT a Verification section; adding one after = drift.
        ticket.write_text(ticket.read_text(encoding="utf-8") + "\n## Verification\n- AC1: `pytest`\n", encoding="utf-8")
        ok, evidence = compare_ticket_to_snapshot(ticket, snapshot)
        self.assertFalse(ok)
        self.assertIn("verification-sha256", evidence["mismatches"])

    def test_seal_gate_accepts_well_formed_verification_binding(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        self._draft_with_verification(ct2, "\n## Verification\n- AC1: `python -m unittest discover`\n")
        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", "--seal-gate", "--ticket", "001", project])
        self.assertEqual(audit.returncode, 0, audit.stdout + audit.stderr)
        checks = {check["name"]: check["ok"] for check in json.loads(audit.stdout)["tickets"][0]["checks"]}
        self.assertTrue(checks["seal_gate_verification_binding"])

    def test_seal_gate_rejects_malformed_verification_binding(self):
        cases = {
            "out-of-range-ac": "\n## Verification\n- AC2: `pytest`\n",  # only AC1 exists
            "unparseable-line": "\n## Verification\n- run the tests please\n",
            "empty-command": "\n## Verification\n- AC1: ``\n",
        }
        for name, verification in cases.items():
            with self.subTest(case=name):
                project = self.make_project()
                ct2 = project / ".ct2"
                self._draft_with_verification(ct2, verification)
                audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", "--seal-gate", "--ticket", "001", project])
                self.assertEqual(audit.returncode, 1, audit.stdout)
                checks = {check["name"]: check["ok"] for check in json.loads(audit.stdout)["tickets"][0]["checks"]}
                self.assertFalse(checks["seal_gate_verification_binding"])

    def test_seal_gate_passes_without_verification_section(self):
        # Tickets with no ## Verification section are unaffected (vacuous pass).
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "draft" / "001-audit-ticket.md", status="draft", ac_checked=False, verdict="pending")
        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ticket-audit", "--json", "--seal-gate", "--ticket", "001", project])
        self.assertEqual(audit.returncode, 0, audit.stdout + audit.stderr)
        checks = {check["name"]: check["ok"] for check in json.loads(audit.stdout)["tickets"][0]["checks"]}
        self.assertTrue(checks["seal_gate_verification_binding"])


if __name__ == "__main__":
    unittest.main()
