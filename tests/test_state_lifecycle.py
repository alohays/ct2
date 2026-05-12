import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


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


if __name__ == "__main__":
    unittest.main()
