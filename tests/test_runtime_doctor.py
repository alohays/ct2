import json
import os
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def load_doctor():
    bin_dir = str(REPO_ROOT / "bin")
    if bin_dir not in sys.path:
        sys.path.insert(0, bin_dir)
    return runpy.run_path(str(REPO_ROOT / "bin" / "ct2-runtime-doctor"), run_name="ct2_test_runtime_doctor")


DOCTOR = load_doctor()
WORKFLOW_STATES = {"available", "unavailable-serial-fallback", "unknown-serial-fallback"}


def run_cmd(args, cwd=None, env=None):
    return subprocess.run(
        [str(arg) for arg in args],
        cwd=str(cwd or REPO_ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )


def write_fake_cli(path: Path, version_line: str) -> None:
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'case "${1:-}" in\n'
        f'  --version) echo "{version_line}" ;;\n'
        '  *) echo "fake $*" ;;\n'
        "esac\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


class VersionSignalTest(unittest.TestCase):
    def test_parse_version_extracts_first_triple(self):
        self.assertEqual((2, 1, 154), DOCTOR["parse_version"]("2.1.154 (Claude Code)"))
        self.assertEqual((0, 130, 0), DOCTOR["parse_version"]("codex-cli 0.130.0"))
        self.assertIsNone(DOCTOR["parse_version"]("no version here"))

    def test_version_ok_compares_against_minimum(self):
        self.assertTrue(DOCTOR["version_ok"]((2, 1, 154), (2, 1, 138)))
        self.assertTrue(DOCTOR["version_ok"]((2, 1, 138), (2, 1, 138)))
        self.assertFalse(DOCTOR["version_ok"]((2, 1, 137), (2, 1, 138)))
        self.assertFalse(DOCTOR["version_ok"](None, (2, 1, 138)))


class WorkflowClassProbeTest(unittest.TestCase):
    def probe(self, claude):
        return DOCTOR["probe_workflow_class"](claude)

    def test_claude_missing_reports_unknown_serial_fallback(self):
        probe = self.probe({"available": False, "version": None})
        self.assertEqual("unknown-serial-fallback", probe["state"])
        self.assertEqual("claude-cli-missing", probe["method"])
        self.assertEqual("hint", probe["authority"])

    def test_unparseable_version_reports_unknown_serial_fallback(self):
        probe = self.probe({"available": True, "version": "not a version"})
        self.assertEqual("unknown-serial-fallback", probe["state"])
        self.assertEqual("claude-cli-version-unparseable", probe["method"])

    def test_workflow_class_version_reports_available_hint(self):
        for version in ("2.1.154 (Claude Code)", "Claude Code 2.1.160", "3.0.0"):
            with self.subTest(version=version):
                probe = self.probe({"available": True, "version": version})
                self.assertEqual("available", probe["state"])
                self.assertEqual("claude-cli-version>=2.1.154", probe["method"])
                self.assertEqual("hint", probe["authority"])

    def test_pre_workflow_version_reports_unavailable_serial_fallback(self):
        for version in ("Claude Code 2.1.138", "2.1.153 (Claude Code)"):
            with self.subTest(version=version):
                probe = self.probe({"available": True, "version": version})
                self.assertEqual("unavailable-serial-fallback", probe["state"])
                self.assertEqual("claude-cli-version<2.1.154", probe["method"])

    def test_probe_never_raises_on_malformed_input(self):
        for claude in ({}, {"available": True}, {"available": True, "version": 12345}, {"version": "2.1.160"}):
            with self.subTest(claude=claude):
                probe = self.probe(claude)
                self.assertIn(probe["state"], WORKFLOW_STATES)
                self.assertEqual("hint", probe["authority"])


class RuntimeDoctorWorkflowProbeEndToEndTest(unittest.TestCase):
    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project])
        self.assertEqual(init.returncode, 0, init.stderr)
        return project

    def test_doctor_reports_workflow_class_available_from_version_signal(self):
        project = self.make_project()
        fake_claude = project / "fake-claude"
        write_fake_cli(fake_claude, "2.1.160 (Claude Code)")
        fake_codex = project / "fake-codex"
        write_fake_cli(fake_codex, "codex-cli 0.130.0")
        env = os.environ.copy()
        env["CT2_CLAUDE_CMD"] = str(fake_claude)
        env["CT2_CODEX_CMD"] = str(fake_codex)

        doctor = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-runtime-doctor", "--json", project], env=env)
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        report = json.loads(doctor.stdout)
        self.assertEqual("available", report["workflow_class"]["state"])
        self.assertEqual("claude-cli-version>=2.1.154", report["workflow_class"]["method"])
        self.assertEqual("hint", report["workflow_class"]["authority"])

        persisted = json.loads((project / ".ct2" / "runtime" / "capabilities.json").read_text(encoding="utf-8"))
        self.assertEqual(report["workflow_class"], persisted["workflow_class"])

        status = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-status", "--doctor", project])
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn("workflow-class: available (hint via claude-cli-version>=2.1.154)", status.stdout)

    def test_claude_absence_is_serial_fallback_and_exits_zero(self):
        project = self.make_project()
        env = os.environ.copy()
        env["CT2_CLAUDE_CMD"] = str(project / "no-such-claude")
        env["CT2_CODEX_CMD"] = str(project / "no-such-codex")

        doctor = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-runtime-doctor", "--json", project], env=env)
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        report = json.loads(doctor.stdout)
        self.assertEqual("unknown-serial-fallback", report["workflow_class"]["state"])
        self.assertEqual("claude-cli-missing", report["workflow_class"]["method"])

    def test_pre_workflow_version_is_unavailable_serial_fallback_and_exits_zero(self):
        project = self.make_project()
        fake_claude = project / "fake-claude"
        write_fake_cli(fake_claude, "Claude Code 2.1.138")
        env = os.environ.copy()
        env["CT2_CLAUDE_CMD"] = str(fake_claude)
        env["CT2_CODEX_CMD"] = str(project / "no-such-codex")

        doctor = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-runtime-doctor", "--json", project], env=env)
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        report = json.loads(doctor.stdout)
        self.assertEqual("unavailable-serial-fallback", report["workflow_class"]["state"])
        self.assertEqual("claude-cli-version<2.1.154", report["workflow_class"]["method"])


if __name__ == "__main__":
    unittest.main()
