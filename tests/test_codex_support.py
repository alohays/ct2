import json
import os
import re
import runpy
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


def load_script(name):
    return runpy.run_path(str(REPO_ROOT / "bin" / name), run_name=f"ct2_test_{name}")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_ticket(path, ticket_id="001", title="Audit smoke", review_round=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
id: "{ticket_id}"
title: "{title}"
status: backlog
priority: medium
created: 2026-05-07T00:00:00Z
updated: 2026-05-07T00:00:00Z
sealed: 2026-05-07T00:00:00Z
branch: null
pr: null
review-round: {review_round}
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
- [ ] Exercise Codex support.

## Constraints
- Use stdlib-only tests.

## Context
Regression fixture for Codex support.

## Acceptance Criteria
- [ ] Completion is backed by CT2 state evidence.
""",
        encoding="utf-8",
    )


def sidecar(ticket, reviewer="ct2-lens-cx", verdict="approved", round_num="0"):
    return f"""---
ticket: "{ticket}"
reviewer: {reviewer}
round: {round_num}
verdict: {verdict}
timestamp: 2026-05-07T00:00:00Z
---

## Summary
Valid review sidecar for regression tests.

## Acceptance Criteria Check
- [x] Completion is backed by CT2 state evidence.

## Issues Found
(none)

## Recommendation
approved - regression fixture is complete.
"""


class CodexSupportTest(unittest.TestCase):
    maxDiff = None

    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        ct2 = project / ".ct2"
        for rel in (
            "draft",
            "backlog",
            "in-progress",
            "in-review",
            "rejected",
            "escalated",
            "done",
            "reviews",
            "reviews/.archive",
            "worktrees",
            "logs",
            "config",
            "codex/threads",
            "codex/goals",
            "codex/scopes",
            "codex/ledgers",
            "inbox/ct2-helm/processing",
            "inbox/ct2-helm/done",
            "inbox/ct2-forge/processing",
            "inbox/ct2-forge/done",
            "inbox/ct2-lens-cx/processing",
            "inbox/ct2-lens-cx/done",
            ".meta",
            ".tmp",
        ):
            (ct2 / rel).mkdir(parents=True, exist_ok=True)
        (ct2 / "config" / "harness.yaml").write_text("max_review_rounds: 3\n", encoding="utf-8")
        return project

    def test_forge_goal_audit_requires_terminal_state_and_dual_sidecars(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "backlog" / "001-audit-smoke.md", "001", "Audit smoke")

        start = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-codex-goal",
                "start",
                "ct2-forge",
                "Complete captured tickets",
                "--project-dir",
                project,
                "--goal-slug",
                "forge-smoke",
            ]
        )
        self.assertEqual(start.returncode, 0, start.stderr)

        scope = json.loads((ct2 / "codex" / "scopes" / "forge-smoke.json").read_text(encoding="utf-8"))
        self.assertEqual([".ct2/backlog/001-audit-smoke.md"], [ticket["path_at_capture"] for ticket in scope["tickets"]])

        before = run_cmd(
            [PYTHON, REPO_ROOT / "bin" / "ct2-codex-goal", "audit", "forge-smoke", "ct2-forge", "--project-dir", project]
        )
        self.assertEqual(before.returncode, 1)
        self.assertFalse(json.loads(before.stdout)["complete"])

        (ct2 / "reviews" / "001-cc-r0.md").write_text(
            sidecar("001-audit-smoke", reviewer="ct2-lens-cc"), encoding="utf-8"
        )
        (ct2 / "reviews" / "001-cx-r0.md").write_text(sidecar("001-audit-smoke"), encoding="utf-8")
        (ct2 / "backlog" / "001-audit-smoke.md").rename(ct2 / "done" / "001-audit-smoke.md")

        after = run_cmd(
            [PYTHON, REPO_ROOT / "bin" / "ct2-codex-goal", "audit", "forge-smoke", "ct2-forge", "--project-dir", project]
        )
        self.assertEqual(after.returncode, 0, after.stderr)
        audit = json.loads(after.stdout)
        self.assertTrue(audit["complete"])
        self.assertEqual(
            ["terminal_state", "dual_sidecars_exist"],
            [check["name"] for check in audit["tickets"][0]["checks"]],
        )

        pause = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-codex-goal",
                "pause",
                "forge-smoke",
                "ct2-forge",
                "--project-dir",
                project,
                "--wait-state",
                "review_pending",
            ]
        )
        self.assertEqual(pause.returncode, 0, pause.stderr)
        paused_goal = json.loads((ct2 / "codex" / "goals" / "forge-smoke-ct2-forge.json").read_text(encoding="utf-8"))
        paused_thread = json.loads((ct2 / "codex" / "threads" / "ct2-forge.json").read_text(encoding="utf-8"))
        self.assertEqual("paused", paused_goal["status"])
        self.assertEqual("review_pending", paused_thread["wait_state"])

        resume = run_cmd(
            [PYTHON, REPO_ROOT / "bin" / "ct2-codex-goal", "resume", "forge-smoke", "ct2-forge", "--project-dir", project]
        )
        self.assertEqual(resume.returncode, 0, resume.stderr)
        resumed_goal = json.loads((ct2 / "codex" / "goals" / "forge-smoke-ct2-forge.json").read_text(encoding="utf-8"))
        self.assertEqual("active", resumed_goal["status"])
        self.assertIsNone(resumed_goal["wait_state"])

        clear = run_cmd(
            [PYTHON, REPO_ROOT / "bin" / "ct2-codex-goal", "clear", "forge-smoke", "ct2-forge", "--project-dir", project]
        )
        self.assertEqual(clear.returncode, 0, clear.stderr)
        self.assertFalse((ct2 / "codex" / "goals" / "forge-smoke-ct2-forge.json").exists())
        self.assertTrue((ct2 / "codex" / "ledgers" / "forge-smoke-ct2-forge.cleared.json").exists())

    def test_lens_cx_audit_requires_own_sidecar_for_review_snapshot(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "in-review" / "002-review-smoke.md", "002", "Review smoke")

        start = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-codex-goal",
                "start",
                "ct2-lens-cx",
                "Drain current reviews",
                "--project-dir",
                project,
                "--goal-slug",
                "lens-smoke",
                "--ticket-state",
                "in-review",
            ]
        )
        self.assertEqual(start.returncode, 0, start.stderr)

        missing = run_cmd(
            [PYTHON, REPO_ROOT / "bin" / "ct2-codex-goal", "audit", "lens-smoke", "ct2-lens-cx", "--project-dir", project]
        )
        self.assertEqual(missing.returncode, 1)
        self.assertFalse(json.loads(missing.stdout)["complete"])

        (ct2 / "reviews" / "002-cx-r0.md").write_text(sidecar("002-review-smoke"), encoding="utf-8")
        present = run_cmd(
            [PYTHON, REPO_ROOT / "bin" / "ct2-codex-goal", "audit", "lens-smoke", "ct2-lens-cx", "--project-dir", project]
        )
        self.assertEqual(present.returncode, 0, present.stderr)
        self.assertTrue(json.loads(present.stdout)["complete"])

    def test_app_driver_request_input_maps_answers_and_missing_questions_to_ct2(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        app_driver = load_script("ct2-codex-app-driver")

        response = app_driver["response_for_server_request"](
            ct2,
            "ct2-forge",
            "item/tool/requestUserInput",
            {"questions": [{"id": "scope", "question": "Which scope should be implemented?"}]},
            {},
        )
        self.assertIsNone(response)
        inbox_messages = list((ct2 / "inbox" / "ct2-helm").glob("*.md"))
        self.assertEqual(1, len(inbox_messages))
        self.assertIn("Which scope", inbox_messages[0].read_text(encoding="utf-8"))
        pending_decisions = list((ct2 / "decisions" / "pending").glob("*.json"))
        self.assertEqual(1, len(pending_decisions))
        decision = json.loads(pending_decisions[0].read_text(encoding="utf-8"))
        self.assertEqual("codex", decision["provider"])
        self.assertEqual("requestUserInput", decision["kind"])

        answered = app_driver["response_for_server_request"](
            ct2,
            "ct2-helm-auto-cx",
            "item/tool/requestUserInput",
            {"questions": [{"id": "secret_token", "question": "Token?", "isSecret": True}]},
            {"secret_token": ["super-secret"]},
        )
        self.assertEqual({"answers": {"secret_token": {"answers": ["super-secret"]}}}, answered)
        ledger_text = (ct2 / "codex" / "ledgers" / "app-server-ct2-helm-auto-cx.json").read_text(encoding="utf-8")
        self.assertIn("[redacted]", ledger_text)
        self.assertNotIn("super-secret", ledger_text)

        self.assertEqual(
            {"decision": "decline"},
            app_driver["response_for_server_request"](ct2, "ct2-forge", "item/commandExecution/requestApproval", {}, {}),
        )
        tool_call = app_driver["response_for_server_request"](ct2, "ct2-forge", "item/tool/call", {}, {})
        self.assertFalse(tool_call["success"])
        self.assertIsNone(app_driver["response_for_server_request"](ct2, "ct2-forge", "unknown/request", {}, {}))

    def test_doctor_with_fake_codex_reports_schema_features_and_request_input_fallback(self):
        project = self.make_project()
        fake = project / "fake-codex"
        fake.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
cmd="${1:-}"
shift || true
case "$cmd" in
  --version)
    echo "codex-cli 0.128.0"
    ;;
  exec)
    echo "Usage: codex exec --sandbox <SANDBOX_MODE>"
    ;;
  review|plugin)
    echo "Usage: codex ${cmd}"
    ;;
  mcp)
    if [[ "${1:-}" == "list" ]]; then
      echo "Name Status"
      echo "context7 enabled"
    else
      echo "Usage: codex mcp"
    fi
    ;;
  features)
    sub="${1:-}"
    if [[ "$sub" == "list" ]]; then
      cat <<'FEATURES'
goals under development true
plugins stable true
tool_search stable true
tool_suggest stable true
tool_call_mcp_elicitation stable true
default_mode_request_user_input under development false
multi_agent stable true
apps stable true
FEATURES
    elif [[ "$sub" == "enable" ]]; then
      exit 0
    else
      echo "Usage: codex features"
    fi
    ;;
  app-server)
    sub="${1:-}"
    shift || true
    if [[ "$sub" == "generate-json-schema" ]]; then
      out=""
      while [[ $# -gt 0 ]]; do
        case "$1" in
          --out)
            out="$2"
            shift 2
            ;;
          *)
            shift
            ;;
        esac
      done
      mkdir -p "$out"
      cat > "$out/schema.json" <<'SCHEMA'
{"methods":["thread/goal/set","thread/goal/get","thread/goal/clear","item/tool/requestUserInput"],"types":["ToolRequestUserInputParams"]}
SCHEMA
    else
      echo "Usage: codex app-server"
    fi
    ;;
  *)
    echo "unexpected command: $cmd" >&2
    exit 2
    ;;
esac
""",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        env = os.environ.copy()
        env["CT2_CODEX_CMD"] = str(fake)

        doctor = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-codex-doctor",
                "--no-enable-request-input",
                "--json",
                project,
            ],
            env=env,
        )
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        report = json.loads(doctor.stdout)
        self.assertTrue(report["codex_version_ok"])
        self.assertTrue(report["schema"]["goal_api"])
        self.assertTrue(report["schema"]["request_input"])
        self.assertEqual("declined", report["request_input_setup"]["state"])
        self.assertTrue(report["sandbox_profile_compatibility"]["exec_sandbox_flags"]["supported"])
        self.assertTrue(all(skill["plugin_source"] for skill in report["skills"]["required"].values()))
        self.assertTrue(any("default_mode_request_user_input disabled" in item for item in report["degradations"]))

        persisted = json.loads((project / ".ct2" / "codex" / "preflight.json").read_text(encoding="utf-8"))
        self.assertEqual(report["codex_version"], persisted["codex_version"])

    def test_sidecar_validator_accepts_complete_sidecars_and_rejects_incomplete_ones(self):
        project = self.make_project()
        valid = project / "valid.md"
        invalid = project / "invalid.md"
        valid.write_text(sidecar("001-audit-smoke"), encoding="utf-8")
        invalid.write_text(
            """---
ticket: "001-audit-smoke"
reviewer: ct2-lens-cx
round: 0
verdict: approved
timestamp: 2026-05-07T00:00:00Z
---

## Summary
Missing required sections.
""",
            encoding="utf-8",
        )

        ok = run_cmd(
            [PYTHON, REPO_ROOT / "bin" / "_ct2_validate_review_sidecar.py", valid, "ct2-lens-cx", "0", "001-audit-smoke"]
        )
        self.assertEqual(ok.returncode, 0, ok.stderr)

        bad = run_cmd(
            [PYTHON, REPO_ROOT / "bin" / "_ct2_validate_review_sidecar.py", invalid, "ct2-lens-cx", "0", "001-audit-smoke"]
        )
        self.assertEqual(bad.returncode, 1)
        self.assertIn("missing section", bad.stderr)

    def test_status_reports_codex_goal_thread_and_degraded_preflight(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_json(
            ct2 / "codex" / "goals" / "status-smoke-maintenance.json",
            {
                "goal_slug": "status-smoke",
                "role": "maintenance",
                "status": "active",
                "scope_id": "status-smoke",
                "wait_state": "review_pending",
                "updated": "2026-05-07T00:00:00Z",
            },
        )
        write_json(
            ct2 / "codex" / "threads" / "maintenance.json",
            {
                "role": "maintenance",
                "mode": "app-server",
                "thread_id": "thr_test",
                "goal": {"status": "active"},
                "wait_state": "review_pending",
            },
        )
        write_json(
            ct2 / "codex" / "preflight.json",
            {
                "codex_version": "codex-cli 0.128.0",
                "checked_at": "2026-05-07T00:00:00Z",
                "request_input_setup": {"state": "declined"},
                "degradations": ["default_mode_request_user_input disabled; fallback: inbox"],
            },
        )

        status = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-status", project])
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn("CODEX", status.stdout)
        self.assertIn("goal status-smoke role=maintenance status=active wait=review_pending", status.stdout)
        self.assertIn("thread maintenance mode=app-server thread=thr_test goal=active wait=review_pending", status.stdout)
        self.assertIn("degraded: 1 warning(s)", status.stdout)

    def test_codex_plugin_and_role_skills_expose_required_contract_sections(self):
        plugin = json.loads((REPO_ROOT / "codex-plugin" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertIn("protocol", plugin["description"].lower())
        self.assertEqual("./skills/", plugin["skills"])

        expected = {
            "ct2-helm": "ct2:helm",
            "ct2-forge": "ct2:forge",
            "ct2-lens-cx": "ct2:lens-cx",
            "ct2-helm-auto-cx": "ct2:helm-auto-cx",
            "ct2-status": "ct2:status",
        }
        for dirname, skill_name in expected.items():
            path = REPO_ROOT / "codex-plugin" / "skills" / dirname / "SKILL.md"
            text = path.read_text(encoding="utf-8")
            self.assertRegex(text, rf'(?m)^name:\s+"?{re.escape(skill_name)}"?$', msg=path.name)
            self.assertRegex(text, r"(?m)^description:\s+", msg=path.name)
            for section in ("Identity", "Allowed", "Forbidden", "Verification", "Fallback"):
                self.assertIn(section, text, f"{path} missing {section}")


if __name__ == "__main__":
    unittest.main()
