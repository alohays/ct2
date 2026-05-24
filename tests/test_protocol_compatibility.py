import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run_cmd(args, cwd=None, env=None):
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [str(arg) for arg in args],
        cwd=str(cwd or REPO_ROOT),
        env=merged_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )


def write_ticket(path, ticket_id="001", status="draft", sealed="null", include_duration=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    duration = "duration-bounce-count: 0\ntotal-attempts: 0\n" if include_duration else ""
    path.write_text(
        f"""---
id: "{ticket_id}"
title: "Protocol smoke"
status: {status}
priority: medium
created: 2026-05-24T00:00:00Z
updated: 2026-05-24T00:00:00Z
sealed: {sealed}
branch: feat/{ticket_id}-protocol-smoke
pr: null
review-round: 0
{duration}estimated-scope: small
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
- [ ] Exercise protocol compatibility.

## Constraints
- Use stdlib-only tests.

## Context
Regression fixture for protocol migrations and guards.

## Acceptance Criteria
- [ ] Protocol behavior is observable.
""",
        encoding="utf-8",
    )


class ProtocolCompatibilityTest(unittest.TestCase):
    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project])
        self.assertEqual(init.returncode, 0, init.stderr)
        return project

    def fixture_project(self, rel):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        fixture = REPO_ROOT / "tests" / "migrations" / rel / "before" / "ct2"
        shutil.copytree(fixture, project / ".ct2")
        return project

    def test_ct2_init_writes_and_repairs_protocol_marker(self):
        project = self.make_project()
        marker = project / ".ct2" / ".protocol-version"
        self.assertEqual("0.2", marker.read_text(encoding="utf-8").strip())

        marker.unlink()
        repair = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", "--repair", project])
        self.assertEqual(repair.returncode, 0, repair.stderr)
        self.assertEqual("0.2", marker.read_text(encoding="utf-8").strip())

    def test_state_mutating_helper_refuses_missing_marker_with_migration_command(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        (ct2 / ".protocol-version").unlink()
        write_ticket(ct2 / "draft" / "001-protocol-smoke.md")

        status = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-status", project])
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn("status:  migrate", status.stdout)
        self.assertIn("ct2-migrate-0.1-0.2", status.stdout)

        seal = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-seal", "001"], cwd=project)

        self.assertEqual(seal.returncode, 2)
        self.assertIn("ct2-migrate-0.1-0.2", seal.stderr)
        self.assertTrue((ct2 / "draft" / "001-protocol-smoke.md").exists())
        self.assertFalse((ct2 / "backlog" / "001-protocol-smoke.md").exists())

    def test_state_mutating_helper_refuses_older_marker_with_migration_command(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        (ct2 / ".protocol-version").write_text("0.3\n", encoding="utf-8")
        write_ticket(
            ct2 / "backlog" / "001-protocol-smoke.md",
            status="backlog",
            sealed="2026-05-24T00:00:00Z",
            include_duration=True,
        )

        pickup = run_cmd(
            [PYTHON, REPO_ROOT / "bin" / "ct2-pickup", project],
            env={"CT2_PROTOCOL_CURRENT": "0.4"},
        )

        self.assertEqual(pickup.returncode, 2)
        self.assertIn("ct2-migrate-0.3-0.4", pickup.stderr)
        self.assertTrue((ct2 / "backlog" / "001-protocol-smoke.md").exists())

    def test_state_mutating_helper_refuses_newer_project_marker(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        (ct2 / ".protocol-version").write_text("0.9\n", encoding="utf-8")
        write_ticket(
            ct2 / "backlog" / "001-protocol-smoke.md",
            status="backlog",
            sealed="2026-05-24T00:00:00Z",
            include_duration=True,
        )

        pickup = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-pickup", project])

        self.assertEqual(pickup.returncode, 2)
        self.assertIn("newer than this CT2 install", pickup.stderr)

    def test_migrate_0_1_to_0_2_adds_fields_backup_log_and_stamp(self):
        project = self.fixture_project("0.1-to-0.2")
        ct2 = project / ".ct2"
        ticket = ct2 / "backlog" / "001-legacy.md"
        self.assertNotIn("duration-bounce-count", ticket.read_text(encoding="utf-8"))

        migrate = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-migrate-0.1-0.2", "--json", project])

        self.assertEqual(migrate.returncode, 0, migrate.stderr)
        report = json.loads(migrate.stdout)
        self.assertEqual("migrated", report["state"])
        self.assertEqual("0.2", (ct2 / ".protocol-version").read_text(encoding="utf-8").strip())
        text = ticket.read_text(encoding="utf-8")
        self.assertIn("duration-bounce-count: 0", text)
        self.assertIn("total-attempts: 0", text)
        self.assertTrue((ct2 / "reviews" / "001-sealed.md").exists())
        self.assertEqual(1, len(list((ct2 / ".migrations").glob("*-0.1-to-0.2.tar.gz"))))
        self.assertEqual(1, len(list((ct2 / ".migrations").glob("*-0.1-to-0.2.log"))))

        rerun = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-migrate-0.1-0.2", "--json", project])
        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        self.assertEqual("already-current", json.loads(rerun.stdout)["state"])

    def test_migrate_0_2_to_0_3_is_idempotent_noop_stamp(self):
        project = self.fixture_project("0.2-to-0.3")
        ct2 = project / ".ct2"

        migrate = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-migrate-0.2-0.3", "--json", project])

        self.assertEqual(migrate.returncode, 0, migrate.stderr)
        self.assertEqual("0.3", (ct2 / ".protocol-version").read_text(encoding="utf-8").strip())
        self.assertEqual(1, len(list((ct2 / ".migrations").glob("*-0.2-to-0.3.tar.gz"))))
        self.assertEqual(1, len(list((ct2 / ".migrations").glob("*-0.2-to-0.3.log"))))

        rerun = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-migrate-0.2-0.3", "--json", project])
        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        self.assertEqual("already-current", json.loads(rerun.stdout)["state"])

    def test_protocol_audit_covers_cataloged_fields(self):
        audit = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-protocol-audit", "--json", REPO_ROOT])
        self.assertEqual(audit.returncode, 0, audit.stderr)
        self.assertTrue(json.loads(audit.stdout)["ok"])

    def test_runtime_doctor_includes_protocol_status(self):
        project = self.make_project()

        doctor = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-runtime-doctor", "--json", project])

        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        report = json.loads(doctor.stdout)
        self.assertEqual("0.2", report["protocol"]["project_protocol"])
        self.assertEqual("0.2", report["protocol"]["current_protocol"])
        self.assertTrue(report["protocol"]["compatible"])
        self.assertEqual("none", report["protocol"]["suggested_action"])
        saved = json.loads((project / ".ct2" / "runtime" / "capabilities.json").read_text(encoding="utf-8"))
        self.assertEqual(report["protocol"], saved["protocol"])


if __name__ == "__main__":
    unittest.main()
