import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


class CiWorkflowTest(unittest.TestCase):
    def test_ci_workflow_runs_repository_validation_gates(self):
        workflow = CI_WORKFLOW.read_text(encoding="utf-8")

        required_snippets = (
            "name: CI",
            "pull_request:",
            "push:",
            "workflow_dispatch:",
            "permissions:",
            "contents: read",
            "concurrency:",
            "cancel-in-progress: true",
            "fail-fast: false",
            'python-version: ["3.10", "3.11", "3.13"]',
            "actions/checkout@v6",
            "actions/setup-python@v6",
            "persist-credentials: false",
            "PYTHONDONTWRITEBYTECODE: \"1\"",
            "python3 -m unittest discover -s tests",
            "python3 bin/ct2-vao-self-verify --run-checks --json --repo .",
            "bash -n",
            "install.sh",
            "python3 -m json.tool codex-plugin/.codex-plugin/plugin.json",
            "git diff --check",
        )

        for snippet in required_snippets:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, workflow)

        self.assertRegex(workflow, re.compile(r"bash -n\s+\\\s+install\.sh", re.MULTILINE))


if __name__ == "__main__":
    unittest.main()
