import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
sys.path.insert(0, str(REPO_ROOT / "bin"))
from _ct2_sealed_baseline import write_snapshot  # noqa: E402

VALIDATOR = REPO_ROOT / "bin" / "_ct2_validate_review_sidecar.py"


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


def sidecar_text(verdict, ac_check, reviewer="ct2-lens-cc", round_num=0):
    return f"""---
ticket: "001-grammar"
reviewer: {reviewer}
round: {round_num}
verdict: {verdict}
timestamp: 2026-06-16T00:00:00Z
---

## Summary
Review summary.

## Acceptance Criteria Check
{ac_check}

## Issues Found
(none)

## Recommendation
{verdict}
"""


class SidecarGrammarTest(unittest.TestCase):
    def validate(self, text, reviewer="ct2-lens-cc", round_num="0", ticket="001-grammar", in_dir=None):
        directory = in_dir or Path(tempfile.mkdtemp())
        path = directory / "sidecar.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return run_cmd([PYTHON, VALIDATOR, path, reviewer, round_num, ticket])

    def test_approved_with_failed_ac_is_invalid(self):
        result = self.validate(sidecar_text("approved", "- AC1: pass\n- AC2: fail — regression still red"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("approved but the body grades an AC as fail", result.stderr)

    def test_rejected_with_failed_ac_is_valid(self):
        result = self.validate(sidecar_text("rejected", "- AC1: pass\n- AC2: fail — regression still red"))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_approved_all_pass_is_valid(self):
        result = self.validate(sidecar_text("approved", "- AC1: pass\n- AC2: pass — config validates"))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejected_all_pass_is_valid_no_such_rule(self):
        # Rejecting on a non-AC criterion (style/scope/security) with all ACs
        # passing is legitimate — there is no rejected-with-all-pass rule.
        result = self.validate(sidecar_text("rejected", "- AC1: pass\n- AC2: pass"))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unparseable_ac_line_warns_only(self):
        result = self.validate(sidecar_text("approved", "- AC1: done (typo)\n- AC2: pass"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("unparseable AC grade line", result.stderr)

    def test_checkbox_style_sidecar_unchanged(self):
        # Legacy checkbox-style AC check has no grade lines: no hard rule, no warn.
        result = self.validate(sidecar_text("approved", "- [x] First criterion met.\n- [x] Second criterion met."))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("warning", result.stderr)

    def test_graded_count_mismatch_warns_against_sealed_baseline(self):
        project = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(project, ignore_errors=True))
        reviews = project / ".ct2" / "reviews"
        reviews.mkdir(parents=True, exist_ok=True)
        ticket = project / ".ct2" / "backlog" / "001-grammar.md"
        ticket.parent.mkdir(parents=True, exist_ok=True)
        ticket.write_text(
            "---\nid: \"001\"\nsealed: 2026-06-16T00:00:00Z\n---\n\n"
            "## Requirements\n- r\n\n## Constraints\n- c\n\n"
            "## Acceptance Criteria\n- [ ] one\n- [ ] two\n- [ ] three\n",
            encoding="utf-8",
        )
        write_snapshot(ticket, reviews / "001-sealed.md")
        # Grade only 2 of the baseline's 3 ACs.
        result = self.validate(
            sidecar_text("approved", "- AC1: pass\n- AC2: pass"),
            in_dir=reviews,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("graded 2 ACs but the sealed baseline has 3", result.stderr)

    def test_code_fence_example_does_not_wedge(self):
        # A reviewer pasting the documented grammar example inside a fence must
        # NOT trip the hard rule (free prose can never wedge a ticket).
        ac_check = "- AC1: pass — ok\nExample:\n```\n- AC2: fail — example only\n```"
        result = self.validate(sidecar_text("approved", ac_check))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_indented_code_block_example_does_not_wedge(self):
        ac_check = "- AC1: pass — ok\n    - AC2: fail — indented example"
        result = self.validate(sidecar_text("approved", ac_check))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_hyphenated_word_does_not_trip_hard_rule(self):
        # `fail-safe` / `pass-like` are not clean grades; they warn, never wedge.
        result = self.validate(sidecar_text("approved", "- AC1: fail-safe behaviour verified"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("unparseable AC grade line", result.stderr)

    def test_reconciler_wedges_approved_with_failed_ac(self):
        project = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(project, ignore_errors=True))
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project])
        self.assertEqual(init.returncode, 0, init.stderr)
        ct2 = project / ".ct2"
        ticket = ct2 / "in-review" / "001-grammar.md"
        ticket.parent.mkdir(parents=True, exist_ok=True)
        ticket.write_text(
            "---\nid: \"001\"\ntitle: \"Grammar\"\nstatus: in-review\npriority: medium\n"
            "created: 2026-06-16T00:00:00Z\nupdated: 2026-06-16T00:00:00Z\nsealed: 2026-06-16T00:00:00Z\n"
            "branch: null\nreview-round: 0\ntouched-files:\n  - README.md\nverdict: pending\n---\n\n"
            "## Requirements\n- r\n\n## Constraints\n- c\n\n## Context\nctx\n\n"
            "## Acceptance Criteria\n- [x] one\n- [x] two\n",
            encoding="utf-8",
        )
        write_snapshot(ticket, ct2 / "reviews" / "001-sealed.md")
        (ct2 / "reviews" / "001-cc-r0.md").write_text(
            sidecar_text("approved", "- AC1: pass\n- AC2: fail — regression red", reviewer="ct2-lens-cc"),
            encoding="utf-8",
        )
        (ct2 / "reviews" / "001-cx-r0.md").write_text(
            sidecar_text("approved", "- AC1: pass\n- AC2: pass", reviewer="ct2-lens-cx"),
            encoding="utf-8",
        )

        reconcile = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-reconcile", "001", "0", "--project-dir", project])
        self.assertEqual(reconcile.returncode, 2)
        self.assertTrue(ticket.exists(), "no state move on a coherence-invalid sidecar")
        self.assertFalse((ct2 / "done" / "001-grammar.md").exists())


if __name__ == "__main__":
    unittest.main()
