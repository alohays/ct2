import json
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CANVAS = REPO_ROOT / "bin" / "ct2-helm-canvas"

SPEC = {
    "ticket": "001-demo-plan",
    "canvas": {
        "round": 0,
        "title": "Demo plan",
        "interpretation": {"summary": "Add OAuth login", "quote": "add social login"},
        "scope": [
            {"label": "Google OAuth", "state": "in"},
            {"label": "Account linking", "state": "hold"},
        ],
        "tickets": [{"title": "#1 infra", "size": "small", "items": ["callback route"]}],
        "acceptance_criteria": [{"text": "Google login works", "accepted": True, "flagged": False}],
        "priority": "high",
        "dependency": "no blockers",
        "constraints": [{"label": "tech", "text": "secrets in env"}],
    },
}


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


class CanvasLifecycleTest(unittest.TestCase):
    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project], cwd=REPO_ROOT)
        self.assertEqual(init.returncode, 0, init.stderr)
        return project

    def generate(self, project):
        spec_path = project / "spec.json"
        spec_path.write_text(json.dumps(SPEC), encoding="utf-8")
        res = run_cmd(["python3", CANVAS, "generate", "--spec", "spec.json"], cwd=project)
        self.assertEqual(res.returncode, 0, res.stderr)
        pending = list((project / ".ct2" / "decisions" / "pending").glob("*.json"))
        self.assertEqual(1, len(pending), "exactly one pending decision expected")
        return json.loads(pending[0].read_text(encoding="utf-8"))

    def token_for(self, record, nonce=None, answer=None, open_items=None):
        payload = {
            "decision": record["id"],
            "ticket": record["ticket"],
            "nonce": nonce if nonce is not None else record["nonce"],
            "round": 0,
            "answer": answer or {"priority": "critical"},
            "overrides": ["priority: high -> critical"],
            "open_items": open_items or [],
        }
        return "CT2-DECISION " + json.dumps(payload)

    def put_backlog_ticket(self, project, ticket="001-demo-plan"):
        """Simulate a post-ct2-seal ticket sitting in backlog/."""
        path = project / ".ct2" / "backlog" / f"{ticket}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('---\nid: "001"\nstatus: backlog\n---\n', encoding="utf-8")

    # ── generate ──────────────────────────────────────────────────────────
    def test_generate_creates_open_canvas_and_pending_record(self):
        project = self.make_project()
        record = self.generate(project)
        ct2 = project / ".ct2"
        self.assertEqual("html", record["provider"])
        self.assertEqual("pending", record["status"])
        self.assertTrue(record.get("nonce"))
        canvas = ct2 / "plans" / "canvas" / "open" / "001-demo-plan-r0.canvas.html"
        self.assertTrue(canvas.exists(), "open canvas HTML should exist")
        self.assertEqual([], list((ct2 / ".tmp").iterdir()))

    def test_generated_canvas_html_is_self_contained_and_parses(self):
        project = self.make_project()
        self.generate(project)
        html = (project / ".ct2" / "plans" / "canvas" / "open"
                / "001-demo-plan-r0.canvas.html").read_text(encoding="utf-8")
        HTMLParser().feed(html)  # raises on malformed markup
        for marker in ("window.CANVAS", 'id="commitBtn"', "p-interpret",
                       "p-scope", "p-ac", "p-note"):
            self.assertIn(marker, html)
        for external in ("http://", "https://", "src="):
            self.assertNotIn(external, html, "canvas must reference no external resources")

    def test_generated_canvas_js_parses_when_node_available(self):
        import re
        import shutil

        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        project = self.make_project()
        self.generate(project)
        html = (project / ".ct2" / "plans" / "canvas" / "open"
                / "001-demo-plan-r0.canvas.html").read_text(encoding="utf-8")
        scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
        js_path = project / "canvas.js"
        js_path.write_text(scripts[-1], encoding="utf-8")
        res = run_cmd([node, "--check", js_path], cwd=project)
        self.assertEqual(res.returncode, 0, res.stderr)

    # ── recover ───────────────────────────────────────────────────────────
    def test_recover_moves_open_to_answered(self):
        project = self.make_project()
        record = self.generate(project)
        ct2 = project / ".ct2"
        res = run_cmd(["python3", CANVAS, "recover", self.token_for(record)], cwd=project)
        self.assertEqual(res.returncode, 0, res.stderr)

        self.assertFalse((ct2 / "decisions" / "pending" / f"{record['id']}.json").exists())
        answered = ct2 / "decisions" / "answered" / f"{record['id']}.json"
        self.assertTrue(answered.exists())
        answered_record = json.loads(answered.read_text(encoding="utf-8"))
        self.assertEqual("answered", answered_record["status"])
        self.assertEqual("critical", answered_record["answer"]["priority"])

        self.assertEqual([], list((ct2 / "plans" / "canvas" / "open").iterdir()))
        self.assertTrue((ct2 / "plans" / "canvas" / "answered"
                         / "001-demo-plan-r0.canvas.html").exists())
        self.assertEqual([], list((ct2 / ".tmp").iterdir()))

    def test_recover_rejects_bad_nonce_without_state_change(self):
        project = self.make_project()
        record = self.generate(project)
        ct2 = project / ".ct2"
        res = run_cmd(
            ["python3", CANVAS, "recover", self.token_for(record, nonce="WRONG")],
            cwd=project,
        )
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("nonce", res.stderr)
        # pending record and open canvas untouched
        self.assertTrue((ct2 / "decisions" / "pending" / f"{record['id']}.json").exists())
        self.assertTrue((ct2 / "plans" / "canvas" / "open"
                         / "001-demo-plan-r0.canvas.html").exists())
        self.assertEqual([], list((ct2 / "decisions" / "answered").iterdir()))

    def test_recover_rejects_malformed_token(self):
        project = self.make_project()
        self.generate(project)
        res = run_cmd(["python3", CANVAS, "recover", "CT2-DECISION not-json"], cwd=project)
        self.assertNotEqual(res.returncode, 0)

    def test_recover_aborts_when_open_canvas_missing(self):
        project = self.make_project()
        record = self.generate(project)
        ct2 = project / ".ct2"
        (ct2 / "plans" / "canvas" / "open" / "001-demo-plan-r0.canvas.html").unlink()
        res = run_cmd(["python3", CANVAS, "recover", self.token_for(record)], cwd=project)
        self.assertNotEqual(res.returncode, 0)
        # the decision record must not be answered without its canvas
        self.assertTrue((ct2 / "decisions" / "pending" / f"{record['id']}.json").exists())
        self.assertEqual([], list((ct2 / "decisions" / "answered").iterdir()))

    def test_recover_carries_open_items(self):
        project = self.make_project()
        record = self.generate(project)
        token = self.token_for(record, open_items=["scope 'Account linking' on hold"])
        res = run_cmd(["python3", CANVAS, "recover", token], cwd=project)
        self.assertEqual(res.returncode, 0, res.stderr)
        answered = json.loads((project / ".ct2" / "decisions" / "answered"
                               / f"{record['id']}.json").read_text(encoding="utf-8"))
        self.assertEqual(1, len(answered["open_items"]))

    # ── recover from file (Phase 2) ───────────────────────────────────────
    def test_recover_from_downloaded_file(self):
        project = self.make_project()
        record = self.generate(project)
        drop = project / "decision.json"
        drop.write_text(self.token_for(record), encoding="utf-8")
        res = run_cmd(["python3", CANVAS, "recover", "--file", "decision.json"], cwd=project)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue((project / ".ct2" / "decisions" / "answered"
                         / f"{record['id']}.json").exists())

    def test_recover_from_bare_json_file(self):
        # the canvas download button writes a bare JSON object (no token prefix)
        project = self.make_project()
        record = self.generate(project)
        payload = json.loads(self.token_for(record)[len("CT2-DECISION "):])
        drop = project / "decision.json"
        drop.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        res = run_cmd(["python3", CANVAS, "recover", "--file", "decision.json"], cwd=project)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue((project / ".ct2" / "decisions" / "answered"
                         / f"{record['id']}.json").exists())

    # ── seal ──────────────────────────────────────────────────────────────
    def test_seal_moves_answered_canvas_to_sealed(self):
        project = self.make_project()
        record = self.generate(project)
        ct2 = project / ".ct2"
        run_cmd(["python3", CANVAS, "recover", self.token_for(record)], cwd=project)
        self.put_backlog_ticket(project)
        res = run_cmd(["python3", CANVAS, "seal", "001-demo-plan"], cwd=project)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual([], list((ct2 / "plans" / "canvas" / "answered").iterdir()))
        sealed = ct2 / "plans" / "canvas" / "sealed" / "001-demo-plan" / "001-demo-plan-r0.canvas.html"
        self.assertTrue(sealed.exists())

    def test_seal_rejects_when_ticket_not_sealed(self):
        # seal must not fabricate plan evidence when ct2-seal never ran
        project = self.make_project()
        record = self.generate(project)
        ct2 = project / ".ct2"
        run_cmd(["python3", CANVAS, "recover", self.token_for(record)], cwd=project)
        res = run_cmd(["python3", CANVAS, "seal", "001-demo-plan"], cwd=project)
        self.assertNotEqual(res.returncode, 0)
        self.assertTrue((ct2 / "plans" / "canvas" / "answered"
                         / "001-demo-plan-r0.canvas.html").exists())
        self.assertFalse((ct2 / "plans" / "canvas" / "sealed" / "001-demo-plan").exists())

    # ── expire ────────────────────────────────────────────────────────────
    def test_expire_moves_open_canvas_and_decision_together(self):
        project = self.make_project()
        record = self.generate(project)
        ct2 = project / ".ct2"
        res = run_cmd(["python3", CANVAS, "expire", "001-demo-plan"], cwd=project)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue((ct2 / "plans" / "canvas" / "expired"
                         / "001-demo-plan-r0.canvas.html").exists())
        self.assertEqual([], list((ct2 / "plans" / "canvas" / "open").iterdir()))
        # the paired decision record must not stay actionable in pending/
        self.assertFalse((ct2 / "decisions" / "pending" / f"{record['id']}.json").exists())
        self.assertTrue((ct2 / "decisions" / "expired" / f"{record['id']}.json").exists())

    def test_expire_after_recover_moves_answered_decision(self):
        project = self.make_project()
        record = self.generate(project)
        ct2 = project / ".ct2"
        run_cmd(["python3", CANVAS, "recover", self.token_for(record)], cwd=project)
        res = run_cmd(["python3", CANVAS, "expire", "001-demo-plan"], cwd=project)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue((ct2 / "plans" / "canvas" / "expired"
                         / "001-demo-plan-r0.canvas.html").exists())
        self.assertFalse((ct2 / "decisions" / "answered" / f"{record['id']}.json").exists())
        self.assertTrue((ct2 / "decisions" / "expired" / f"{record['id']}.json").exists())

    # ── lifecycle pairing: no orphans ─────────────────────────────────────
    def test_canvas_and_record_move_together(self):
        project = self.make_project()
        record = self.generate(project)
        ct2 = project / ".ct2"

        def states():
            canvas_states = {
                s for s in ("open", "answered")
                if list((ct2 / "plans" / "canvas" / s).glob("*.canvas.html"))
            }
            record_states = {
                s for s in ("pending", "answered")
                if (ct2 / "decisions" / s / f"{record['id']}.json").exists()
            }
            return canvas_states, record_states

        canvas_states, record_states = states()
        self.assertEqual({"open"}, canvas_states)
        self.assertEqual({"pending"}, record_states)

        run_cmd(["python3", CANVAS, "recover", self.token_for(record)], cwd=project)
        canvas_states, record_states = states()
        self.assertEqual({"answered"}, canvas_states)
        self.assertEqual({"answered"}, record_states)


if __name__ == "__main__":
    unittest.main()
