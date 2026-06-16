import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
LESSON = REPO_ROOT / "bin" / "ct2-lesson"


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


class LessonsTest(unittest.TestCase):
    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project])
        self.assertEqual(init.returncode, 0, init.stderr)
        return project

    def add(self, project, ticket, category, rule, scope="role:forge", paths=(), round_num="0"):
        args = [PYTHON, LESSON, "add", "--project-dir", project, "--ticket", ticket, "--round", round_num,
                "--category", category, "--rule", rule, "--scope", scope, "--json"]
        for path in paths:
            args += ["--path", path]
        result = run_cmd(args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def digest(self, project, role, touched=None, as_json=True):
        args = [PYTHON, LESSON, "digest", "--project-dir", project, "--role", role]
        if touched:
            args += ["--touched-files", touched]
        if as_json:
            args += ["--json"]
        result = run_cmd(args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout) if as_json else result.stdout

    def _backlog_ticket(self, project, touched="bin/ct2-x"):
        path = project / ".ct2" / "backlog" / "009-pickup.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\nid: \"009\"\ntitle: t\nstatus: backlog\npriority: medium\n"
            "created: 2026-06-16T00:00:00Z\nupdated: 2026-06-16T00:00:00Z\nsealed: 2026-06-16T00:00:00Z\n"
            f"branch: null\nreview-round: 0\ntouched-files:\n  - {touched}\nverdict: pending\n---\n\n"
            "## Requirements\n- r\n\n## Acceptance Criteria\n- [ ] one\n",
            encoding="utf-8",
        )

    def test_pickup_injects_lessons_digest(self):
        project = self.make_project()
        self.add(project, "005", "missing-regression-test", "Bind a regression AC for bin/.", paths=["bin/*"])
        self.add(project, "006", "missing-regression-test", "Bind a regression AC for bin/.", paths=["bin/*"])
        self._backlog_ticket(project)
        pickup = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pickup", project])
        self.assertEqual(pickup.returncode, 0, pickup.stderr)
        self.assertIn("Lessons (forge):", pickup.stdout)
        self.assertIn("corroborated", pickup.stdout)

    def test_pickup_digest_is_fail_soft_when_ledger_empty(self):
        project = self.make_project()
        self._backlog_ticket(project)
        pickup = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pickup", project])
        self.assertEqual(pickup.returncode, 0, pickup.stderr)
        self.assertIn("none recorded", pickup.stdout)

    def test_init_creates_lessons_dir(self):
        project = self.make_project()
        self.assertTrue((project / ".ct2" / "lessons").is_dir())

    def test_add_candidate_then_corroborated_across_tickets(self):
        project = self.make_project()
        first = self.add(project, "012", "missing-regression-test", "Bind a regression AC for bin/.", paths=["bin/*"])
        self.assertEqual("candidate", first["status"])
        second = self.add(project, "018", "missing-regression-test", "Bind a regression AC for bin/.", paths=["bin/*", "tests/*"])
        self.assertEqual("corroborated", second["status"])

    def test_same_ticket_twice_stays_candidate(self):
        project = self.make_project()
        self.add(project, "012", "scope-creep", "Stay in scope.", scope="repo")
        again = self.add(project, "012", "scope-creep", "Stay in scope.", scope="repo")
        self.assertEqual("candidate", again["status"], "recurrence needs ≥2 DISTINCT tickets")

    def test_disjoint_paths_do_not_corroborate(self):
        project = self.make_project()
        self.add(project, "012", "missing-regression-test", "bin lesson.", paths=["bin/*"])
        other = self.add(project, "018", "missing-regression-test", "docs lesson.", paths=["docs/*"])
        self.assertEqual("candidate", other["status"], "disjoint path areas are different lessons")

    def test_retire_removes_from_digest(self):
        project = self.make_project()
        added = self.add(project, "012", "flaky-test", "Quarantine flaky tests.", scope="repo")
        retire = run_cmd([PYTHON, LESSON, "retire", "--project-dir", project, "--id", added["id"], "--reason", "obsolete"])
        self.assertEqual(retire.returncode, 0, retire.stderr)
        self.assertEqual([], self.digest(project, "forge")["lessons"])

    def test_retire_unknown_id_fails(self):
        project = self.make_project()
        retire = run_cmd([PYTHON, LESSON, "retire", "--project-dir", project, "--id", "lsn-nope", "--reason", "x"])
        self.assertEqual(retire.returncode, 1)

    def test_digest_scope_filter_excludes_other_role(self):
        project = self.make_project()
        self.add(project, "012", "scope-creep", "helm-only lesson.", scope="role:helm")
        self.add(project, "013", "evidence-missing", "repo lesson.", scope="repo")
        forge = {lesson["category"] for lesson in self.digest(project, "forge")["lessons"]}
        self.assertIn("evidence-missing", forge)
        self.assertNotIn("scope-creep", forge, "a role:helm lesson must not appear in the forge digest")

    def test_digest_ranks_corroborated_first(self):
        project = self.make_project()
        self.add(project, "001", "style-convention", "candidate only.", scope="repo")
        self.add(project, "002", "api-contract", "corroborated A.", scope="repo")
        self.add(project, "003", "api-contract", "corroborated A.", scope="repo")
        lessons = self.digest(project, "forge")["lessons"]
        self.assertEqual("corroborated", lessons[0]["status"])

    def test_invalid_category_and_scope_rejected(self):
        project = self.make_project()
        bad_cat = run_cmd([PYTHON, LESSON, "add", "--project-dir", project, "--ticket", "1", "--category", "nope", "--rule", "x", "--scope", "repo"])
        self.assertEqual(bad_cat.returncode, 2)
        bad_scope = run_cmd([PYTHON, LESSON, "add", "--project-dir", project, "--ticket", "1", "--category", "scope-creep", "--rule", "x", "--scope", "role:lens"])
        self.assertEqual(bad_scope.returncode, 2)

    def test_digest_rejects_invalid_role(self):
        project = self.make_project()
        result = run_cmd([PYTHON, LESSON, "digest", "--project-dir", project, "--role", "lens"])
        self.assertEqual(result.returncode, 2)

    def test_digest_char_cap_truncates_long_output(self):
        project = self.make_project()
        categories = list(
            ("missing-regression-test", "scope-creep", "ac-unverifiable", "evidence-missing",
             "env-setup", "flaky-test", "api-contract", "style-convention")
        )
        long_rule = ("Always verify the boundary condition carefully and add the matching regression coverage " * 3)[:195]
        for index, category in enumerate(categories):
            self.add(project, str(100 + index), category, long_rule, scope="repo")
        out = self.digest(project, "forge", as_json=False)
        self.assertIn("more (raise --max", out)
        self.assertLessEqual(len(out), 1400, "human digest must stay near the ~1200 char cap")

    def test_rule_length_limit(self):
        project = self.make_project()
        long_rule = "x" * 201
        result = run_cmd([PYTHON, LESSON, "add", "--project-dir", project, "--ticket", "1", "--category", "env-setup", "--rule", long_rule, "--scope", "repo"])
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
