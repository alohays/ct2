import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


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


class ReleaseWorkflowTest(unittest.TestCase):
    def test_version_file_and_plugin_manifests_match(self):
        version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual("0.2.0", version)
        for rel in (
            "claude-plugin/.claude-plugin/plugin.json",
            "codex-plugin/.codex-plugin/plugin.json",
        ):
            with self.subTest(rel=rel):
                data = json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))
                self.assertEqual(version, data["version"])

    def test_ct2_status_version_output_is_project_independent(self):
        proc = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-status", "--version"], cwd=REPO_ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ct2 0.2.0", proc.stdout)
        self.assertIn("plugin (claude): 0.2.0", proc.stdout)
        self.assertIn("plugin (codex):  0.2.0", proc.stdout)
        self.assertIn("protocol:        0.2", proc.stdout)

    def test_changelog_bootstrap_sections_exist(self):
        text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## [Unreleased]", text)
        self.assertIn("## [0.2.0]", text)
        self.assertIn("## [0.1.0]", text)

    def test_prepare_patch_updates_derived_artifacts_and_creates_one_commit(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = Path(tmp.name) / "repo"
        for rel in (
            "bin/ct2-release",
            "bin/_ct2_version.py",
            "VERSION",
            "CHANGELOG.md",
            "install.sh",
            "claude-plugin/.claude-plugin/plugin.json",
            "codex-plugin/.codex-plugin/plugin.json",
        ):
            src = REPO_ROOT / rel
            dest = repo / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

        self.assertEqual(run_cmd(["git", "init"], cwd=repo).returncode, 0)
        self.assertEqual(run_cmd(["git", "add", "."], cwd=repo).returncode, 0)
        self.assertEqual(
            run_cmd(
                [
                    "git",
                    "-c",
                    "user.name=CT2 Test",
                    "-c",
                    "user.email=ct2@example.invalid",
                    "commit",
                    "-m",
                    "init",
                ],
                cwd=repo,
            ).returncode,
            0,
        )

        before = run_cmd(["git", "rev-list", "--count", "HEAD"], cwd=repo)
        self.assertEqual(before.stdout.strip(), "1")
        proc = run_cmd([PYTHON, repo / "bin" / "ct2-release", "prepare", "patch"], cwd=repo)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual("0.2.1", (repo / "VERSION").read_text(encoding="utf-8").strip())
        for rel in (
            "claude-plugin/.claude-plugin/plugin.json",
            "codex-plugin/.codex-plugin/plugin.json",
        ):
            data = json.loads((repo / rel).read_text(encoding="utf-8"))
            self.assertEqual("0.2.1", data["version"])
        changelog = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## [0.2.1]", changelog)
        after = run_cmd(["git", "rev-list", "--count", "HEAD"], cwd=repo)
        self.assertEqual(after.stdout.strip(), "2")

    def test_release_workflow_and_installer_pin_are_documented(self):
        workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("python3 bin/ct2-release prepare", workflow)
        self.assertIn("gh release create", workflow)
        install = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("--version", install)
        self.assertIn("CT2_INSTALL_VERSION=\"0.2.0\"", install)


if __name__ == "__main__":
    unittest.main()
