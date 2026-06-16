import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
GOAL = REPO_ROOT / "bin" / "ct2-goal"


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


def write_ticket(ct2, state, ticket_id, slug="t"):
    path = ct2 / state / f"{ticket_id}-{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'---\nid: "{ticket_id}"\nreview-round: 0\n---\n\nbody\n', encoding="utf-8")
    return path


class GoalLoopTest(unittest.TestCase):
    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project])
        self.assertEqual(init.returncode, 0, init.stderr)
        return project

    def start(self, project, *extra, slug="demo", objective=("Improve", "the", "thing")):
        args = [PYTHON, GOAL, "start", *objective, "--project-dir", project, "--slug", slug, *extra]
        result = run_cmd(args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def audit(self, project, slug="demo"):
        result = run_cmd([PYTHON, GOAL, "audit", slug, "--project-dir", project])
        return result, json.loads(result.stdout)

    def test_init_creates_goals_dir(self):
        project = self.make_project()
        self.assertTrue((project / ".ct2" / "goals").is_dir())

    def test_start_snapshot_captures_matching_tickets(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2, "done", "001")
        write_ticket(ct2, "backlog", "002")
        write_ticket(ct2, "draft", "003")
        self.start(project, "--ticket-state", "done", "--ticket-state", "backlog")
        scope = json.loads((ct2 / "goals" / "demo" / "scope.json").read_text(encoding="utf-8"))
        self.assertEqual({"001-t.md", "002-t.md"}, {ticket["filename"] for ticket in scope["tickets"]})

    def test_audit_incomplete_until_all_terminal(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2, "done", "001")
        write_ticket(ct2, "backlog", "002")
        self.start(project, "--ticket-state", "done", "--ticket-state", "backlog")
        result, report = self.audit(project)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["complete"])

        (ct2 / "done" / "002-t.md").write_text((ct2 / "backlog" / "002-t.md").read_text(encoding="utf-8"), encoding="utf-8")
        (ct2 / "backlog" / "002-t.md").unlink()
        result2, report2 = self.audit(project)
        self.assertEqual(result2.returncode, 0)
        self.assertTrue(report2["complete"])

    def test_audit_never_moves_ticket_state(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2, "backlog", "002")
        self.start(project, "--ticket-state", "backlog")
        self.audit(project)
        self.assertTrue((ct2 / "backlog" / "002-t.md").exists(), "audit must never move ticket state")

    def test_outcome_check_records_evidence_and_gates_completeness(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2, "done", "001")
        self.start(project, "--ticket-state", "done", "--outcome-check", "false")
        result, report = self.audit(project)
        self.assertEqual(result.returncode, 1, "a failing outcome-check makes the goal incomplete")
        self.assertFalse(report["outcome_check"]["ok"])

        claims = [json.loads(line) for line in (ct2 / "evidence" / "claims.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        outcome = [c for c in claims if c.get("ticket") == "demo" and c.get("kind") == "verifier"]
        self.assertTrue(outcome and outcome[0]["ok"] is False, "outcome-check exit recorded as a verifier claim, never a verdict")

    def test_production_mode_starts_empty_and_add_ticket(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2, "backlog", "001")
        self.start(project, "--mode", "production", "--ticket-state", "backlog")
        scope = json.loads((ct2 / "goals" / "demo" / "scope.json").read_text(encoding="utf-8"))
        self.assertEqual([], scope["tickets"], "production mode starts with an empty scope")

        added = run_cmd([PYTHON, GOAL, "add-ticket", "demo", "001", "--project-dir", project])
        self.assertEqual(added.returncode, 0, added.stderr)
        scope2 = json.loads((ct2 / "goals" / "demo" / "scope.json").read_text(encoding="utf-8"))
        self.assertEqual(["001-t.md"], [ticket["filename"] for ticket in scope2["tickets"]])

    def test_start_rejects_duplicate_slug(self):
        project = self.make_project()
        self.start(project)
        again = run_cmd([PYTHON, GOAL, "start", "Improve", "--project-dir", project, "--slug", "demo"])
        self.assertEqual(again.returncode, 1, "a second start with the same slug must error")

    def test_status_and_lifecycle_transitions(self):
        project = self.make_project()
        self.start(project)
        for command, expected in (("pause", "paused"), ("complete", "complete"), ("abandon", "abandoned")):
            result = run_cmd([PYTHON, GOAL, command, "demo", "--project-dir", project])
            self.assertEqual(result.returncode, 0, result.stderr)
            goal = json.loads((project / ".ct2" / "goals" / "demo" / "goal.json").read_text(encoding="utf-8"))
            self.assertEqual(expected, goal["status"])
        status = run_cmd([PYTHON, GOAL, "status", "--project-dir", project, "--json"])
        self.assertEqual("demo", json.loads(status.stdout)["goals"][0]["slug"])

    def test_ledger_records_events(self):
        project = self.make_project()
        self.start(project)
        run_cmd([PYTHON, GOAL, "complete", "demo", "--project-dir", project])
        ledger = [json.loads(line) for line in (project / ".ct2" / "goals" / "demo" / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        kinds = {event["type"] for event in ledger}
        self.assertIn("goal_started", kinds)
        self.assertIn("status_changed", kinds)


class CodexGoalShimTest(unittest.TestCase):
    CODEX = REPO_ROOT / "bin" / "ct2-codex-goal"

    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project])
        self.assertEqual(init.returncode, 0, init.stderr)
        return project

    def test_codex_goal_lazily_migrates_existing_goal_to_neutral(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        (ct2 / "codex" / "goals").mkdir(parents=True, exist_ok=True)
        (ct2 / "codex" / "scopes").mkdir(parents=True, exist_ok=True)
        slug = "old-goal-forge-20260101T000000Z"
        (ct2 / "codex" / "goals" / f"{slug}.json").write_text(
            json.dumps({"goal_slug": slug, "scope_id": "old", "role": "ct2-forge", "objective": "Old objective", "status": "active", "created": "2026-01-01T00:00:00Z"}),
            encoding="utf-8",
        )
        (ct2 / "codex" / "scopes" / "old.json").write_text(
            json.dumps({"scope_id": "old", "mode": "snapshot", "ticket_states": ["backlog"],
                        "tickets": [{"id": "007", "state_at_capture": "backlog", "path_at_capture": ".ct2/backlog/007-x.md"}],
                        "completion_conditions": ["all done"]}),
            encoding="utf-8",
        )

        result = run_cmd([PYTHON, self.CODEX, "status", "--project-dir", project])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("deprecated", result.stderr)
        goal = json.loads((ct2 / "goals" / slug / "goal.json").read_text(encoding="utf-8"))
        scope = json.loads((ct2 / "goals" / slug / "scope.json").read_text(encoding="utf-8"))
        self.assertEqual("open", goal["status"], "codex active -> neutral open")
        self.assertEqual("codex", goal["provider"])
        self.assertEqual(["007-x.md"], [ticket["filename"] for ticket in scope["tickets"]])
        self.assertEqual(["all done"], scope["completion_conditions"])

    def test_codex_goal_start_creates_neutral_record(self):
        project = self.make_project()
        start = run_cmd([PYTHON, self.CODEX, "start", "ct2-forge", "Fresh", "objective", "--project-dir", project])
        self.assertEqual(start.returncode, 0, start.stderr)
        status = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-goal", "status", "--project-dir", project, "--json"])
        slugs = [goal["slug"] for goal in json.loads(status.stdout)["goals"]]
        self.assertTrue(any(slug.startswith("fresh-objective") for slug in slugs), "codex start mirrors into a neutral ct2-goal record")

    def test_codex_goal_mirror_is_idempotent(self):
        project = self.make_project()
        run_cmd([PYTHON, self.CODEX, "start", "ct2-forge", "Once", "--project-dir", project])
        before = len(list((project / ".ct2" / "goals").glob("*/goal.json")))
        run_cmd([PYTHON, self.CODEX, "status", "--project-dir", project])
        after = len(list((project / ".ct2" / "goals").glob("*/goal.json")))
        self.assertEqual(before, after, "re-running must not duplicate the neutral record")


if __name__ == "__main__":
    unittest.main()
