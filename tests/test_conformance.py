import json
import importlib.machinery
import importlib.util
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


class ConformanceTest(unittest.TestCase):
    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project])
        self.assertEqual(init.returncode, 0, init.stderr)
        return project

    def test_protocol_specs_exist_and_are_indexed(self):
        for rel in (
            "spec/PROTOCOL.md",
            "spec/sidecar-format.md",
            "spec/reconciler.md",
            "spec/adapter-format.md",
            "spec/conformance.md",
        ):
            with self.subTest(rel=rel):
                self.assertTrue((REPO_ROOT / rel).is_file())
                self.assertIn(rel, (REPO_ROOT / "README.md").read_text(encoding="utf-8"))

    def test_required_adapters_have_required_sections(self):
        required_sections = ("## Invocation", "## Objective", "## Required CT2 Effects", "## Stop Condition")
        for rel in (
            "adapters/claude/lens-cc.md",
            "adapters/claude/lens-cx.md",
            "adapters/codex/lens-cc.md",
            "adapters/codex/lens-cx.md",
        ):
            with self.subTest(rel=rel):
                text = (REPO_ROOT / rel).read_text(encoding="utf-8")
                self.assertIn("protocol: \"0.1.0\"", text)
                for section in required_sections:
                    self.assertIn(section, text)
                self.assertLess(len(text), 3000)

    def test_lens_dispatchers_dry_run_without_agent_runtime(self):
        project = self.make_project()
        for script, agent in (("ct2-lens-cx", "codex"), ("ct2-lens-cc", "claude")):
            with self.subTest(script=script):
                proc = run_cmd(["bash", REPO_ROOT / "bin" / script, "--dry-run", project])
                self.assertEqual(proc.returncode, 0, proc.stderr)
                report = json.loads(proc.stdout)
                self.assertEqual(agent, report["agent"])
                self.assertTrue(report["adapter"].endswith(f"{report['role']}.md"))
                self.assertEqual(str(project.resolve()), report["project_dir"])

    def test_ct2_verify_accepts_repo_and_initialized_project(self):
        project = self.make_project()
        proc = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-verify", "--json", project])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(proc.stdout)
        self.assertTrue(report["ok"])
        self.assertGreaterEqual(len(report["checks"]), 10)
        check_names = {item["name"] for item in report["checks"]}
        self.assertIn("protocol:no-manual-done-bypass", check_names)

    def test_manual_done_bypass_checker_rejects_role_doc_override(self):
        bin_path = str(REPO_ROOT / "bin")
        loader = importlib.machinery.SourceFileLoader(
            "ct2_verify_for_test",
            str(REPO_ROOT / "bin" / "ct2-verify"),
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, bin_path)
        self.addCleanup(lambda: sys.path.remove(bin_path) if bin_path in sys.path else None)
        loader.exec_module(module)

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = Path(tmp.name)
        role_doc = repo / "claude-plugin" / "skills" / "ct2-helm" / "SKILL.md"
        role_doc.parent.mkdir(parents=True)
        role_doc.write_text(
            "- **Close the ticket**: Move to `done/` with a manual override note.\n",
            encoding="utf-8",
        )

        ok, evidence = module.role_docs_no_done_bypass(repo)
        self.assertFalse(ok)
        self.assertIn("ct2-helm/SKILL.md:1", evidence)


if __name__ == "__main__":
    unittest.main()
