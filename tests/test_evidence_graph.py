import json
import importlib.util
import importlib.machinery
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


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


def load_script_module(name, relpath):
    path = REPO_ROOT / relpath
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    old_path = list(sys.path)
    sys.path.insert(0, str(REPO_ROOT / "bin"))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
    return module


LEGACY_CLAIM = {
    "id": "cmd-20260501T000000Z-deadbeef",
    "timestamp": "2026-05-01T00:00:00Z",
    "ticket": "001",
    "kind": "command",
    "verifier": "command",
    "ok": True,
    "path": ".ct2/evidence/commands/cmd-20260501T000000Z-deadbeef.json",
    "summary": "legacy claim without edge fields",
}


class EvidenceGraphEdgeTest(unittest.TestCase):
    maxDiff = None

    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project])
        self.assertEqual(init.returncode, 0, init.stderr)
        return project

    def record_command(self, project, extra_args=()):
        return run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-evidence",
                "command",
                "--project-dir",
                project,
                "--ticket",
                "001",
                "--command",
                "true",
                "--exit-code",
                "0",
                "--summary",
                "edge fixture",
                "--json",
                *extra_args,
            ]
        )

    def read_claims(self, project):
        claims_path = project / ".ct2" / "evidence" / "claims.jsonl"
        return [
            json.loads(line)
            for line in claims_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_legacy_records_without_edge_fields_still_parse(self):
        project = self.make_project()
        claims_path = project / ".ct2" / "evidence" / "claims.jsonl"
        claims_path.write_text(json.dumps(LEGACY_CLAIM, sort_keys=True) + "\n", encoding="utf-8")
        legacy_bytes = claims_path.read_bytes()

        appended = self.record_command(project, ("--parent-id", "helm-run-7"))
        self.assertEqual(appended.returncode, 0, appended.stderr)

        self.assertTrue(claims_path.read_bytes().startswith(legacy_bytes))
        helpers = load_script_module("ct2_evidence_graph_helpers", "bin/_ct2_vao.py")
        rows = helpers.read_jsonl(claims_path)
        self.assertEqual(2, len(rows))
        for row in rows:
            self.assertNotIn("_invalid", row)
        legacy, fresh = rows
        self.assertEqual(LEGACY_CLAIM, legacy)
        self.assertNotIn("parent_id", legacy)
        self.assertNotIn("produced_by_agent", legacy)
        self.assertEqual("helm-run-7", fresh["parent_id"])

    def test_parent_edge_fields_round_trip_through_write_and_read(self):
        project = self.make_project()
        result = self.record_command(
            project,
            (
                "--parent-id",
                "cmd-20260501T000000Z-deadbeef",
                "--produced-by-agent",
                "skeptic-3",
            ),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        claim = json.loads(result.stdout)
        self.assertEqual("cmd-20260501T000000Z-deadbeef", claim["parent_id"])
        self.assertEqual("skeptic-3", claim["produced_by_agent"])
        self.assertEqual("001", claim["ticket"])

        persisted = self.read_claims(project)
        self.assertEqual(1, len(persisted))
        self.assertEqual(claim, persisted[0])

    def test_flags_absent_means_fields_absent(self):
        project = self.make_project()
        result = self.record_command(project)
        self.assertEqual(result.returncode, 0, result.stderr)
        claim = json.loads(result.stdout)
        self.assertNotIn("parent_id", claim)
        self.assertNotIn("produced_by_agent", claim)

        persisted = self.read_claims(project)
        self.assertEqual(1, len(persisted))
        self.assertNotIn("parent_id", persisted[0])
        self.assertNotIn("produced_by_agent", persisted[0])

    def test_all_structured_subcommands_accept_edge_flags(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        source = ct2 / "evidence" / "artifacts" / "source.txt"
        source.write_text("edge fixture\n", encoding="utf-8")

        commands = (
            [
                "artifact",
                "--path",
                ".ct2/evidence/artifacts/source.txt",
                "--summary",
                "artifact edge",
            ],
            [
                "screenshot",
                "--path",
                ".ct2/evidence/artifacts/source.txt",
                "--summary",
                "screenshot edge",
            ],
            [
                "verifier",
                "--name",
                "unit",
                "--exit-code",
                "0",
                "--summary",
                "verifier edge",
            ],
            [
                "hook-event",
                "--hook",
                "PreToolUse",
                "--event",
                "allowed",
                "--summary",
                "hook edge",
            ],
        )
        for command in commands:
            result = run_cmd(
                [
                    PYTHON,
                    REPO_ROOT / "bin" / "ct2-evidence",
                    *command,
                    "--project-dir",
                    project,
                    "--ticket",
                    "001",
                    "--parent-id",
                    "helm-run-7",
                    "--produced-by-agent",
                    "fanout-worker-1",
                    "--json",
                ]
            )
            self.assertEqual(result.returncode, 0, result.stderr)

        claims = self.read_claims(project)
        self.assertEqual(
            {"artifact", "screenshot", "verifier", "hook-event"},
            {claim["kind"] for claim in claims},
        )
        for claim in claims:
            self.assertEqual("helm-run-7", claim["parent_id"])
            self.assertEqual("fanout-worker-1", claim["produced_by_agent"])


if __name__ == "__main__":
    unittest.main()
