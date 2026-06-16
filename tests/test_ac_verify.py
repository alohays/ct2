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
        timeout=60,
        check=False,
    )


def write_draft(path, verification=None, acs=2):
    ac_lines = "\n".join(f"- [ ] Criterion {i} is met cleanly." for i in range(1, acs + 1))
    body = f"""---
id: "001"
title: "AC verify fixture"
status: draft
priority: medium
created: 2026-06-16T00:00:00Z
updated: 2026-06-16T00:00:00Z
sealed: null
branch: null
review-round: 0
touched-files:
  - README.md
verdict: pending
---

## Requirements
- Build the verification runner correctly.

## Constraints
- Use stdlib only please.

## Context
Regression fixture exercising ct2-ac-verify sealed bindings end to end.

## Acceptance Criteria
{ac_lines}
"""
    if verification is not None:
        body += f"\n## Verification\n{verification}\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def claims(ct2):
    path = ct2 / "evidence" / "claims.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class AcVerifyTest(unittest.TestCase):
    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project])
        self.assertEqual(init.returncode, 0, init.stderr)
        return project

    def seal(self, project):
        result = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-seal", "001"], cwd=project)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_all_pass_exits_zero_and_records_ac_round_claims(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_draft(ct2 / "draft" / "001-ac.md", "- AC1: `true`\n- AC2: `true`")
        self.seal(project)

        result = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ac-verify", "001", project, "--json"], cwd=project)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(2, report["bindings"])

        recorded = claims(ct2)
        self.assertEqual({"1", "2"}, {c["ac"] for c in recorded})
        self.assertTrue(all(c["round"] == "0" and c["ok"] and c["kind"] == "command" for c in recorded))

    def test_failing_binding_exits_one(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_draft(ct2 / "draft" / "001-ac.md", "- AC1: `true`\n- AC2: `false`")
        self.seal(project)

        result = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ac-verify", "001", project], cwd=project)
        self.assertEqual(result.returncode, 1)
        self.assertIn("AC2", result.stdout)

    def test_no_record_does_not_append_claims(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_draft(ct2 / "draft" / "001-ac.md", "- AC1: `true`")
        self.seal(project)

        run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ac-verify", "001", project, "--no-record"], cwd=project)
        self.assertEqual([], claims(ct2))

    def test_no_verification_section_exits_zero(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_draft(ct2 / "draft" / "001-ac.md", verification=None)
        self.seal(project)

        result = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ac-verify", "001", project, "--json"], cwd=project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(0, json.loads(result.stdout)["bindings"])
        self.assertEqual([], claims(ct2))

    def test_reads_from_sealed_snapshot_not_live_ticket(self):
        # ct2-ac-verify must run the SEALED command, immune to a post-seal edit
        # of the live ticket's Verification section.
        project = self.make_project()
        ct2 = project / ".ct2"
        write_draft(ct2 / "draft" / "001-ac.md", "- AC1: `false`")  # sealed command fails
        self.seal(project)
        backlog = ct2 / "backlog" / "001-ac.md"
        backlog.write_text(backlog.read_text(encoding="utf-8").replace("- AC1: `false`", "- AC1: `true`"), encoding="utf-8")

        result = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ac-verify", "001", project], cwd=project)
        self.assertEqual(result.returncode, 1)  # the sealed `false`, not the live `true`

    def test_command_timeout_marks_ac_failed(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        cfg = ct2 / "config" / "harness.yaml"
        cfg.write_text(cfg.read_text(encoding="utf-8") + "\nverification:\n  command_timeout_sec: 1\n", encoding="utf-8")
        write_draft(ct2 / "draft" / "001-ac.md", "- AC1: `sleep 5`", acs=1)
        self.seal(project)

        result = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-ac-verify", "001", project, "--json"], cwd=project)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(json.loads(result.stdout)["results"][0]["timed_out"])

    def test_evidence_command_accepts_ac_round_and_omits_when_absent(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        run_cmd(
            [PYTHON, REPO_ROOT / "bin" / "ct2-evidence", "command", "--project-dir", project,
             "--ticket", "001", "--command", "true", "--exit-code", "0", "--ac", "3", "--round", "2", "--summary", "with"],
            cwd=project,
        )
        run_cmd(
            [PYTHON, REPO_ROOT / "bin" / "ct2-evidence", "command", "--project-dir", project,
             "--ticket", "001", "--command", "true", "--exit-code", "0", "--summary", "without"],
            cwd=project,
        )
        recorded = claims(ct2)
        with_fields = next(c for c in recorded if c["summary"] == "with")
        without_fields = next(c for c in recorded if c["summary"] == "without")
        self.assertEqual("3", with_fields["ac"])
        self.assertEqual("2", with_fields["round"])
        self.assertNotIn("ac", without_fields)
        self.assertNotIn("round", without_fields)

    def test_review_enter_ac_verify_backstop_is_advisory(self):
        # A failing bound AC at submit time records evidence and warns, but the
        # ticket still moves (gate is advisory until promoted).
        project = self.make_project()
        ct2 = project / ".ct2"
        write_draft(ct2 / "draft" / "001-ac.md", "- AC1: `false`", acs=1)
        self.seal(project)

        backlog = ct2 / "backlog" / "001-ac.md"
        in_progress = ct2 / "in-progress" / "001-ac.md"
        in_progress.parent.mkdir(parents=True, exist_ok=True)
        text = backlog.read_text(encoding="utf-8").replace("status: backlog", "status: in-progress").replace(
            "- [ ] Criterion 1 is met cleanly.", "- [x] Criterion 1 is met cleanly."
        )
        in_progress.write_text(text, encoding="utf-8")
        backlog.unlink()
        (ct2 / "plans" / "001-r0.md").write_text("# Plan\n", encoding="utf-8")

        enter = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-review-enter", "001", project], cwd=project)
        self.assertEqual(enter.returncode, 0, enter.stderr)  # advisory: still moves
        self.assertTrue((ct2 / "in-review" / "001-ac.md").exists())
        self.assertIn("ac-verify backstop", enter.stderr)
        self.assertIn("advisory", enter.stderr)
        recorded = claims(ct2)
        self.assertTrue(any(c.get("ac") == "1" and c.get("round") == "0" and not c["ok"] for c in recorded))


if __name__ == "__main__":
    unittest.main()
