import json
import os
import argparse
import importlib.util
import importlib.machinery
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
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


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
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


def write_ticket(path, ticket_id="001", status="done", review_round=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
id: "{ticket_id}"
title: "VAO smoke ticket"
status: {status}
priority: medium
created: 2026-05-01T00:00:00Z
updated: 2026-05-01T01:00:00Z
sealed: 2026-05-01T00:10:00Z
branch: null
pr: null
review-round: {review_round}
estimated-scope: small
touched-files:
  - README.md
review-status:
  lens-claude:
    status: approved
    sidecar: reviews/{ticket_id}-cc-r{review_round}.md
  lens-codex:
    status: approved
    sidecar: reviews/{ticket_id}-cx-r{review_round}.md
verdict: approved
---

## Requirements
- [x] Exercise the VAO baseline.

## Constraints
- No external packages.

## Context
Regression fixture for Verified Autonomy OS metrics.

## Acceptance Criteria
- [x] Completion has sidecar and evidence records.
""",
        encoding="utf-8",
    )


def write_sidecar(path, ticket="001-vao-smoke-ticket", reviewer="ct2-lens-cx", verdict="approved"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
ticket: "{ticket}"
reviewer: {reviewer}
round: 0
verdict: {verdict}
timestamp: 2026-05-01T01:00:00Z
---

## Summary
Approved fixture.

## Acceptance Criteria Check
- [x] Completion has sidecar and evidence records.

## Issues Found
(none)

## Recommendation
approved - fixture passes.
""",
        encoding="utf-8",
    )


class VaoStrategyTest(unittest.TestCase):
    maxDiff = None

    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project])
        self.assertEqual(init.returncode, 0, init.stderr)
        return project

    def test_init_creates_vao_runtime_directories_and_config_contracts(self):
        project = self.make_project()
        ct2 = project / ".ct2"

        for rel in (
            "runtime",
            "runtime/artifacts",
            "runtime/provider-hooks",
            "telemetry",
            "evidence",
            "evidence/commands",
            "evidence/artifacts",
            "evidence/screenshots",
            "evidence/verifiers",
            "evidence/hooks",
            "decisions/pending",
            "decisions/answered",
            "decisions/expired",
            "decisions/audit",
            "plans",
            "watchers",
            "postmortems",
            "evals/ct2-helm",
            "evals/ct2-forge",
            "evals/ct2-lens-cc",
            "evals/ct2-lens-cx",
            "evals/ct2-forge/cases",
        ):
            self.assertTrue((ct2 / rel).is_dir(), rel)

        self.assertTrue((ct2 / "evals" / "ct2-forge" / "cases" / "plan-evidence-codex.json").is_file())
        self.assertTrue((ct2 / "watchers" / "advisory-local.json").is_file())

        harness = (ct2 / "config" / "harness.yaml").read_text(encoding="utf-8")
        self.assertIn("role_contracts:", harness)
        self.assertIn("ct2-forge:", harness)
        self.assertIn("evidence_coverage_min:", harness)

    def test_runtime_doctor_records_capabilities_and_status_doctor(self):
        project = self.make_project()
        fake_codex = project / "fake-codex"
        fake_codex.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  --version) echo "codex-cli 0.130.0" ;;
  features) echo "goals stable true"; echo "apps stable true" ;;
  *) echo "fake codex $*" ;;
esac
""",
            encoding="utf-8",
        )
        fake_claude = project / "fake-claude"
        fake_claude.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  --version) echo "Claude Code 2.1.138" ;;
  *) echo "fake claude $*" ;;
esac
""",
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)
        fake_claude.chmod(0o755)
        env = os.environ.copy()
        env["CT2_CODEX_CMD"] = str(fake_codex)
        env["CT2_CLAUDE_CMD"] = str(fake_claude)

        doctor = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-runtime-doctor", "--json", project], env=env)
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        report = json.loads(doctor.stdout)
        self.assertEqual("1", report["schema_version"])
        self.assertTrue(report["runtimes"]["codex"]["available"])
        self.assertIn("0.130.0", report["runtimes"]["codex"]["version"])
        self.assertTrue(report["runtimes"]["claude"]["available"])

        persisted = json.loads((project / ".ct2" / "runtime" / "capabilities.json").read_text(encoding="utf-8"))
        self.assertEqual(report["checked_at"], persisted["checked_at"])
        degradations = (project / ".ct2" / "runtime" / "degradations.md").read_text(encoding="utf-8")
        self.assertIn("# CT2 Runtime Degradations", degradations)
        flags = (project / ".ct2" / "runtime" / "codex-flags-actual.md").read_text(encoding="utf-8")
        self.assertIn("goals", flags)
        self.assertIn("apps", flags)

        status = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-status", "--doctor", project])
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn("DOCTOR", status.stdout)
        self.assertIn("capabilities: codex=available claude=available", status.stdout)

    def test_baseline_scorecard_evidence_coverage_and_status_rendering(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "done" / "001-vao-smoke-ticket.md")
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", reviewer="ct2-lens-cc")
        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", reviewer="ct2-lens-cx")
        write_jsonl(
            ct2 / "evidence" / "claims.jsonl",
            [
                {
                    "id": "ev-001",
                    "ticket": "001",
                    "kind": "artifact",
                    "verifier": "unit",
                    "ok": True,
                    "path": ".ct2/evidence/artifacts/ev-001.json",
                }
            ],
        )
        write_jsonl(
            ct2 / "telemetry" / "cost.jsonl",
            [{"role": "ct2-forge", "usd": 0.25, "duration_ms": 1500, "exit_code": 0}],
        )

        baseline = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-baseline", "--json", project])
        self.assertEqual(baseline.returncode, 0, baseline.stderr)
        report = json.loads(baseline.stdout)
        self.assertEqual("measurement_started", report["scorecard"]["trust"]["status"])
        self.assertEqual(1, report["scorecard"]["trust"]["sample_size"])
        self.assertEqual(0.0, report["scorecard"]["evidence"]["observed_ratio"])
        self.assertEqual(1, report["scorecard"]["evidence"]["uncited_verifier_count"])
        self.assertEqual(0.25, report["scorecard"]["cost_latency"]["cost_usd_total"])

        write_jsonl(
            ct2 / "evidence" / "claims.jsonl",
            [
                {
                    "id": "ev-001",
                    "ticket": "001",
                    "kind": "artifact",
                    "verifier": "unit",
                    "ok": True,
                    "path": ".ct2/evidence/artifacts/ev-001.json",
                },
                {
                    "id": "verify-001",
                    "ticket": "001",
                    "kind": "verifier",
                    "verifier": "unit",
                    "ok": True,
                    "path": ".ct2/evidence/verifiers/verify-001.json",
                },
            ],
        )
        baseline = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-baseline", "--json", project])
        self.assertEqual(baseline.returncode, 0, baseline.stderr)
        report = json.loads(baseline.stdout)
        self.assertEqual(1.0, report["scorecard"]["evidence"]["observed_ratio"])
        self.assertEqual(0, report["scorecard"]["evidence"]["uncited_verifier_count"])

        persisted = json.loads((ct2 / "telemetry" / "baseline-2026-05.json").read_text(encoding="utf-8"))
        self.assertEqual(report["generated_at"], persisted["generated_at"])

        status = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-status", project])
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn("SCORECARD", status.stdout)
        self.assertIn("Trust", status.stdout)
        self.assertIn("Evidence", status.stdout)

    def test_role_run_records_cost_and_ct2_cost_summarizes(self):
        project = self.make_project()
        env = os.environ.copy()
        env["CT2_COST_USD"] = "0.125"
        env["CT2_INPUT_TOKENS"] = "100"
        env["CT2_OUTPUT_TOKENS"] = "25"
        role_run = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-role-run",
                "--project-dir",
                project,
                "--role",
                "ct2-forge",
                "--",
                PYTHON,
                "-c",
                "print('role-ok')",
            ],
            env=env,
        )
        self.assertEqual(role_run.returncode, 0, role_run.stderr)
        self.assertIn("role-ok", role_run.stdout)

        cost_lines = (project / ".ct2" / "telemetry" / "cost.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(1, len(cost_lines))
        event = json.loads(cost_lines[0])
        self.assertEqual("ct2-forge", event["role"])
        self.assertEqual(0.125, event["usd"])
        self.assertEqual(0, event["exit_code"])

        cost = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-cost", "--json", project])
        self.assertEqual(cost.returncode, 0, cost.stderr)
        summary = json.loads(cost.stdout)
        self.assertEqual(1, summary["events"])
        self.assertEqual(0.125, summary["total_usd"])
        self.assertEqual(100, summary["roles"]["ct2-forge"]["input_tokens"])

    def test_role_run_preserves_failure_exit_and_records_telemetry(self):
        project = self.make_project()
        env = os.environ.copy()
        env["CT2_COST_USD"] = "0.5"
        role_run = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-role-run",
                "--project-dir",
                project,
                "--role",
                "ct2-lens-cx",
                "--",
                PYTHON,
                "-c",
                "import sys; sys.exit(7)",
            ],
            env=env,
        )
        self.assertEqual(role_run.returncode, 7)
        event = json.loads((project / ".ct2" / "telemetry" / "cost.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(7, event["exit_code"])
        self.assertEqual("ct2-lens-cx", event["role"])
        self.assertNotIn("prompt", event)
        self.assertNotIn("tool_input", event)

    def test_evidence_command_records_claim_and_command_artifact(self):
        project = self.make_project()
        evidence = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-evidence",
                "command",
                "--project-dir",
                project,
                "--ticket",
                "001",
                "--command",
                "python3 -m unittest",
                "--exit-code",
                "0",
                "--summary",
                "unit tests passed",
                "--json",
            ]
        )
        self.assertEqual(evidence.returncode, 0, evidence.stderr)
        event = json.loads(evidence.stdout)
        self.assertTrue(event["id"].startswith("cmd-"))
        artifact = project / event["path"]
        self.assertTrue(artifact.is_file())

        claims = (project / ".ct2" / "evidence" / "claims.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(1, len(claims))
        claim = json.loads(claims[0])
        self.assertEqual(event["id"], claim["id"])
        self.assertEqual("001", claim["ticket"])
        self.assertEqual("command", claim["kind"])
        self.assertTrue(claim["ok"])

    def test_evidence_records_artifact_screenshot_verifier_and_hook_event(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        source = ct2 / "evidence" / "artifacts" / "source.txt"
        source.write_text("visual evidence placeholder\n", encoding="utf-8")

        commands = (
            [
                "artifact",
                "--path",
                ".ct2/evidence/artifacts/source.txt",
                "--summary",
                "artifact evidence",
            ],
            [
                "screenshot",
                "--path",
                ".ct2/evidence/artifacts/source.txt",
                "--summary",
                "screenshot evidence",
            ],
            [
                "verifier",
                "--name",
                "unit",
                "--exit-code",
                "0",
                "--summary",
                "verifier evidence",
            ],
            [
                "hook-event",
                "--hook",
                "PreToolUse",
                "--event",
                "allowed",
                "--summary",
                "hook evidence",
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
                    "--json",
                ]
            )
            self.assertEqual(result.returncode, 0, result.stderr)

        claims = [
            json.loads(line)
            for line in (ct2 / "evidence" / "claims.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual({"artifact", "screenshot", "verifier", "hook-event"}, {claim["kind"] for claim in claims})
        self.assertTrue((ct2 / "evidence" / "screenshots").is_dir())
        self.assertTrue((ct2 / "evidence" / "verifiers").is_dir())
        self.assertTrue((ct2 / "evidence" / "hooks").is_dir())

    def test_evidence_verifier_failed_exit_defaults_to_failed_claim(self):
        project = self.make_project()
        result = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-evidence",
                "verifier",
                "--project-dir",
                project,
                "--ticket",
                "001",
                "--name",
                "unit",
                "--exit-code",
                "7",
                "--summary",
                "verifier failed",
                "--json",
            ]
        )
        self.assertEqual(result.returncode, 1)
        claim = json.loads(result.stdout)
        self.assertFalse(claim["ok"])
        persisted = json.loads((project / ".ct2" / "evidence" / "claims.jsonl").read_text(encoding="utf-8"))
        self.assertFalse(persisted["ok"])

    def test_append_jsonl_is_not_read_modify_replace(self):
        module = load_script_module("ct2_vao_helpers", "bin/_ct2_vao.py")
        import inspect

        source = inspect.getsource(module.append_jsonl)
        self.assertNotIn("read_text", source)
        self.assertNotIn("atomic_write_text", source)

    def test_append_jsonl_preserves_parallel_writer_rows(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        dest = ct2 / "telemetry" / "events.jsonl"
        script = (
            "import pathlib, sys\n"
            f"sys.path.insert(0, {str(REPO_ROOT / 'bin')!r})\n"
            "from _ct2_vao import append_jsonl\n"
            "ct2 = pathlib.Path(sys.argv[1])\n"
            "dest = pathlib.Path(sys.argv[2])\n"
            "append_jsonl(ct2, dest, {'idx': int(sys.argv[3])})\n"
        )
        procs = [
            subprocess.Popen(
                [PYTHON, "-c", script, str(ct2), str(dest), str(idx)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for idx in range(30)
        ]
        for proc in procs:
            stdout, stderr = proc.communicate(timeout=30)
            self.assertEqual(proc.returncode, 0, stderr or stdout)
        rows = [json.loads(line) for line in dest.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(set(range(30)), {row["idx"] for row in rows})

    def test_decision_bridge_uses_pending_answered_atomic_dirs(self):
        project = self.make_project()
        ask = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-decision",
                "ask",
                "--project-dir",
                project,
                "--provider",
                "codex",
                "--role",
                "ct2-forge",
                "--ticket",
                "001",
                "--question",
                "Proceed with plan evidence?",
                "--option",
                "yes",
                "--option",
                "no",
                "--json",
            ]
        )
        self.assertEqual(ask.returncode, 0, ask.stderr)
        pending = json.loads(ask.stdout)
        decision_id = pending["id"]
        self.assertTrue((project / ".ct2" / "decisions" / "pending" / f"{decision_id}.json").is_file())

        answer = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-decision",
                "answer",
                decision_id,
                "--project-dir",
                project,
                "--choice",
                "yes",
                "--json",
            ]
        )
        self.assertEqual(answer.returncode, 0, answer.stderr)
        answered = json.loads(answer.stdout)
        self.assertEqual("answered", answered["status"])
        self.assertFalse((project / ".ct2" / "decisions" / "pending" / f"{decision_id}.json").exists())
        self.assertTrue((project / ".ct2" / "decisions" / "answered" / f"{decision_id}.json").is_file())
        self.assertTrue((project / ".ct2" / "decisions" / "audit" / f"{decision_id}.json").is_file())

    def test_decision_answer_audit_failure_does_not_leave_duplicate_states(self):
        project = self.make_project()
        ask = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-decision",
                "ask",
                "--project-dir",
                project,
                "--provider",
                "codex",
                "--role",
                "ct2-forge",
                "--ticket",
                "001",
                "--question",
                "Proceed?",
                "--option",
                "yes",
                "--json",
            ]
        )
        self.assertEqual(ask.returncode, 0, ask.stderr)
        decision_id = json.loads(ask.stdout)["id"]
        module = load_script_module("ct2_decision_atomic", "bin/ct2-decision")
        original = module.atomic_write_json

        def fail_audit(ct2_dir, dest, data, prefix="ct2-json-"):
            if dest.parent.name == "audit":
                raise RuntimeError("simulated audit failure")
            return original(ct2_dir, dest, data, prefix)

        args = argparse.Namespace(project_dir=str(project), decision_id=decision_id, choice="yes", json=True)
        with mock.patch.object(module, "atomic_write_json", fail_audit):
            with self.assertRaises(RuntimeError):
                module.cmd_answer(args)
        pending = project / ".ct2" / "decisions" / "pending" / f"{decision_id}.json"
        answered = project / ".ct2" / "decisions" / "answered" / f"{decision_id}.json"
        self.assertFalse(pending.exists() and answered.exists())
        self.assertFalse(pending.exists())
        self.assertTrue(answered.exists())

    def test_decision_bridge_formats_codex_and_claude_provider_payloads(self):
        project = self.make_project()
        ask = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-decision",
                "ask",
                "--project-dir",
                project,
                "--provider",
                "claude",
                "--role",
                "ct2-helm",
                "--ticket",
                "001",
                "--question",
                "Approve provider format?",
                "--option",
                "approve",
                "--option",
                "decline",
                "--json",
            ]
        )
        self.assertEqual(ask.returncode, 0, ask.stderr)
        decision_id = json.loads(ask.stdout)["id"]

        claude = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-decision",
                "format",
                decision_id,
                "--project-dir",
                project,
                "--provider",
                "claude",
                "--json",
            ]
        )
        self.assertEqual(claude.returncode, 0, claude.stderr)
        claude_payload = json.loads(claude.stdout)
        self.assertEqual("AskUserQuestion", claude_payload["tool"])
        self.assertEqual(["approve", "decline"], claude_payload["arguments"]["options"])

        codex = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-decision",
                "format",
                decision_id,
                "--project-dir",
                project,
                "--provider",
                "codex",
                "--json",
            ]
        )
        self.assertEqual(codex.returncode, 0, codex.stderr)
        codex_payload = json.loads(codex.stdout)
        self.assertEqual("item/tool/requestUserInput", codex_payload["method"])
        self.assertEqual("choice", codex_payload["params"]["questions"][0]["id"])

    def test_app_driver_decision_records_format_and_validate_choices(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        module = load_script_module("ct2_codex_app_driver_decisions", "bin/ct2-codex-app-driver")
        decision_id = module.write_decision_record(
            ct2,
            "ct2-forge",
            [
                {
                    "id": "scope",
                    "question": "Which scope?",
                    "options": [{"label": "narrow", "description": "Keep it small."}],
                }
            ],
        )
        formatted = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-decision",
                "format",
                decision_id,
                "--project-dir",
                project,
                "--provider",
                "codex",
                "--json",
            ]
        )
        self.assertEqual(formatted.returncode, 0, formatted.stderr)
        payload = json.loads(formatted.stdout)
        question = payload["params"]["questions"][0]
        self.assertEqual("Which scope?", question["question"])
        self.assertEqual("narrow", question["options"][0]["label"])

        invalid = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-decision",
                "answer",
                decision_id,
                "--project-dir",
                project,
                "--choice",
                "wide",
            ]
        )
        self.assertEqual(invalid.returncode, 1)

    def test_advisory_bridge_writes_inbox_without_ticket_state_mutation(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_ticket(ct2 / "backlog" / "001-vao-smoke-ticket.md", status="backlog")

        for idx in range(5):
            bridge = run_cmd(
                [
                    PYTHON,
                    REPO_ROOT / "bin" / "ct2-bridge",
                    "notify",
                    "--project-dir",
                    project,
                    "--source",
                    "slack",
                    "--to",
                    "ct2-helm",
                    "--ticket",
                    "001",
                    "--subject",
                    f"External signal {idx}",
                    "--body",
                    "A watcher noticed relevant activity.",
                    "--json",
                ]
            )
            self.assertEqual(bridge.returncode, 0, bridge.stderr)
            event = json.loads(bridge.stdout)
            self.assertEqual("advisory_notification", event["type"])
        self.assertTrue((ct2 / "backlog" / "001-vao-smoke-ticket.md").is_file())
        self.assertFalse((ct2 / "done" / "001-vao-smoke-ticket.md").exists())
        self.assertEqual(5, len(list((ct2 / "inbox" / "ct2-helm").glob("*.md"))))

        events = (ct2 / "telemetry" / "events.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(5, sum(1 for line in events if json.loads(line)["type"] == "advisory_notification"))

        rejected = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-bridge",
                "state-move",
                "--project-dir",
                project,
                "--ticket",
                "001",
                "--to-state",
                "done",
                "--json",
            ]
        )
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("advisory-only", rejected.stderr)
        self.assertTrue((ct2 / "backlog" / "001-vao-smoke-ticket.md").is_file())

    def test_hook_guards_block_ticket_state_writes_and_partner_sidecar_reads(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        (ct2 / ".meta").mkdir(parents=True, exist_ok=True)
        write_sidecar(ct2 / "reviews" / "001-cc-r0.md", reviewer="ct2-lens-cc")

        write_guard = REPO_ROOT / "claude-plugin" / "hooks" / "enforce-write-access.sh"
        read_guard = REPO_ROOT / "claude-plugin" / "hooks" / "enforce-review-independence.sh"
        denied = run_cmd(
            ["bash", write_guard],
            cwd=project,
            env={**os.environ, "CT2_ROLE": "lens-cx"},
        )
        self.assertEqual(denied.returncode, 0)

        bash_input = json.dumps(
            {
                "tool_name": "Bash",
                "cwd": str(project),
                "tool_input": {"command": "mv .ct2/backlog/001.md .ct2/done/001.md"},
            }
        )
        denied = subprocess.run(
            ["bash", str(write_guard)],
            cwd=str(project),
            input=bash_input,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
            env={**os.environ, "CT2_ROLE": "forge"},
        )
        self.assertEqual(2, denied.returncode)
        self.assertIn("protected path", denied.stderr)

        read_input = json.dumps(
            {
                "tool_name": "Read",
                "cwd": str(project),
                "tool_input": {"file_path": ".ct2/reviews/001-cc-r0.md"},
            }
        )
        before_own = subprocess.run(
            ["bash", str(read_guard)],
            cwd=str(project),
            input=read_input,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
            env={**os.environ, "CT2_ROLE": "lens-cx"},
        )
        self.assertEqual(2, before_own.returncode)
        self.assertIn("independence violation", before_own.stderr)

        write_sidecar(ct2 / "reviews" / "001-cx-r0.md", reviewer="ct2-lens-cx")
        after_own = subprocess.run(
            ["bash", str(read_guard)],
            cwd=str(project),
            input=read_input,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
            env={**os.environ, "CT2_ROLE": "lens-cx"},
        )
        self.assertEqual(0, after_own.returncode, after_own.stderr)

    def test_policy_compiler_emits_provider_hooks_and_shell_validators(self):
        project = self.make_project()
        compile_policy = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-policy-compile", "--json", project])
        self.assertEqual(compile_policy.returncode, 0, compile_policy.stderr)
        report = json.loads(compile_policy.stdout)
        self.assertGreaterEqual(report["validators"], 2)
        out_dir = project / ".ct2" / "runtime" / "provider-hooks"
        hooks = json.loads((out_dir / "claude-hooks.json").read_text(encoding="utf-8"))
        validators = json.loads((out_dir / "shell-validators.json").read_text(encoding="utf-8"))
        self.assertIn("PreToolUse", hooks["hooks"])
        self.assertEqual("defense-in-depth", validators["validators"][0]["authority"])
        self.assertIn("scripts remain authoritative", validators["script_authority"])

    def test_role_eval_runner_records_results_and_catches_regression(self):
        project = self.make_project()
        ok = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-role-eval", "--json", project])
        self.assertEqual(ok.returncode, 0, ok.stderr)
        report = json.loads(ok.stdout)
        self.assertTrue(report["complete"])
        self.assertEqual(5, report["case_count"])
        self.assertTrue((project / ".ct2" / "evals" / "results.jsonl").is_file())

        regressed = project / "regressed-forge.md"
        regressed.write_text("# Regressed forge role\n\nNo plan requirement here.\n", encoding="utf-8")
        failed = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-role-eval",
                "--json",
                "--role",
                "ct2-forge",
                "--target-override",
                f"ct2-forge={regressed}",
                project,
            ]
        )
        self.assertEqual(failed.returncode, 1)
        failed_report = json.loads(failed.stdout)
        self.assertFalse(failed_report["complete"])
        self.assertIn("ct2-forge-plan-evidence-codex", failed_report["failed"])

    def test_strategy_spec_documents_exist_for_all_spec_prs(self):
        expected = {
            "runtime-capabilities.md": "Capability Registry",
            "balanced-scorecard.md": "Trust",
            "role-contracts.md": "role contract",
            "plan-evidence.md": "plan-first",
            "role-evals.md": "regression",
            "decision-bridge.md": "provider-neutral",
            "evidence-graph.md": "evidence id",
            "external-channels.md": "advisory",
            "runtime-mirror.md": "runtime twin",
        }
        for filename, needle in expected.items():
            path = REPO_ROOT / "spec" / filename
            self.assertTrue(path.is_file(), filename)
            self.assertIn(needle, path.read_text(encoding="utf-8"))

    def test_forge_role_docs_require_plan_evidence_before_source_edits(self):
        for rel in (
            "codex-plugin/skills/ct2-forge/SKILL.md",
            "claude-plugin/skills/ct2-forge/SKILL.md",
        ):
            text = (REPO_ROOT / rel).read_text(encoding="utf-8")
            self.assertIn(".ct2/plans", text, rel)
            self.assertIn("plan-exempt", text, rel)
            self.assertIn("before", text.lower(), rel)

    def test_plan_audit_verifies_five_plan_first_tickets(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        for idx in range(1, 6):
            ticket_id = f"{idx:03d}"
            write_ticket(ct2 / "in-review" / f"{ticket_id}-plan-ticket.md", ticket_id=ticket_id, status="in-review")
            (ct2 / "plans" / f"{ticket_id}-r0.md").write_text(
                f"# Plan {ticket_id}\n\n- AC mapping exists.\n- Verification command recorded.\n",
                encoding="utf-8",
            )

        ok = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-plan-audit", "--json", project])
        self.assertEqual(ok.returncode, 0, ok.stderr)
        report = json.loads(ok.stdout)
        self.assertTrue(report["complete"])
        self.assertEqual(5, report["tickets_checked"])

        (ct2 / "plans" / "005-r0.md").unlink()
        missing = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-plan-audit", "--json", project])
        self.assertEqual(missing.returncode, 1)
        self.assertFalse(json.loads(missing.stdout)["complete"])

    def test_review_protocol_and_lens_roles_make_missing_plan_evidence_blocking(self):
        review_protocol = (REPO_ROOT / "spec" / "review-protocol.md").read_text(encoding="utf-8").lower()
        self.assertIn("plan evidence", review_protocol)
        self.assertIn("blocking", review_protocol)
        self.assertIn("plan-exempt", review_protocol)
        for rel in ("config/ct2-lens-cc-role.md", "config/ct2-lens-cx-role.md"):
            text = (REPO_ROOT / rel).read_text(encoding="utf-8").lower()
            self.assertIn("plan evidence", text, rel)
            self.assertIn("blocking", text, rel)
            self.assertIn("plan-exempt", text, rel)

    def test_vao_pilot_generates_full_phase_evidence_report(self):
        project = self.make_project()
        report_path = project / "pilot.md"
        pilot = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "ct2-vao-pilot",
                "--project-dir",
                project,
                "--report-file",
                report_path,
                "--json",
            ]
        )
        self.assertEqual(pilot.returncode, 0, pilot.stderr)
        report = json.loads(pilot.stdout)
        self.assertTrue(report["complete"])
        self.assertTrue(all(report["phase_status"].values()))
        self.assertEqual(20, report["metrics"]["done_tickets"])
        self.assertEqual(5, report["metrics"]["cost_events"])
        self.assertEqual(25, report["metrics"]["plan_tickets_checked"])
        self.assertEqual(5, report["metrics"]["role_eval_cases"])
        self.assertEqual(5, report["metrics"]["advisory_notifications"])
        self.assertTrue(report["metrics"]["ticket_state_unchanged"])
        self.assertTrue(report_path.is_file())

    def test_vao_pilot_defaults_to_isolated_scratch_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            pilot = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-vao-pilot", "--json"], cwd=cwd)
            self.assertEqual(pilot.returncode, 0, pilot.stderr)
            report = json.loads(pilot.stdout)
            self.assertTrue(report["complete"])
            self.assertNotEqual(str(cwd.resolve()), report["project_dir"])
            self.assertFalse((cwd / ".ct2" / "done" / "900-vao-pilot.md").exists())

    def test_vao_pilot_refuses_existing_project_collisions_without_opt_in(self):
        project = self.make_project()
        collision = project / ".ct2" / "done" / "900-vao-pilot.md"
        collision.write_text("real ticket\n", encoding="utf-8")
        pilot = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-vao-pilot", "--project-dir", project, "--json"])
        self.assertEqual(pilot.returncode, 2)
        self.assertIn("refusing", pilot.stderr.lower())
        self.assertEqual("real ticket\n", collision.read_text(encoding="utf-8"))

    def test_self_verification_criteria_include_documentation_metrics(self):
        path = REPO_ROOT / "docs" / "ct2-vao-self-verification-criteria-2026-05-11.md"
        text = path.read_text(encoding="utf-8")
        for needle in (
            "Artifact coverage",
            "Test coverage",
            "Spec coverage",
            "User/operator documentation coverage",
            "Documentation coverage score",
            "measurement_started",
            "ct2-verified-autonomy-os-full-phase-audit-2026-05-11.md",
            "ct2-vao-full-implementation-self-review-criteria-2026-05-11.md",
            "ct2-vao-pilot",
        ):
            self.assertIn(needle, text)

        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        for command in (
            "ct2-runtime-doctor",
            "ct2-baseline",
            "ct2-role-run",
            "ct2-cost",
            "ct2-evidence",
            "ct2-decision",
            "ct2-policy-compile",
            "ct2-bridge",
            "ct2-plan-audit",
            "ct2-role-eval",
            "ct2-vao-pilot",
            "ct2-vao-self-verify",
        ):
            self.assertIn(command, readme)
            self.assertIn(command, text)

        audit = (REPO_ROOT / "docs" / "ct2-vao-completion-audit-2026-05-11.md").read_text(encoding="utf-8")
        self.assertIn("Documentation Quality Gate", audit)
        self.assertIn("Self-verification standard", audit)
        report = (REPO_ROOT / "docs" / "ct2-vao-self-verification-report-2026-05-11.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Status: complete", report)
        self.assertIn("Artifact coverage", report)

        full_phase_audit = (
            REPO_ROOT / "docs" / "ct2-verified-autonomy-os-full-phase-audit-2026-05-11.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Overall status: complete", full_phase_audit)
        self.assertIn("local pilot evidence", full_phase_audit)

        phase_report = (REPO_ROOT / "docs" / "ct2-vao-phase-completion-report-2026-05-11.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Overall complete: `true`", phase_report)
        self.assertIn("Ticket state unchanged by bridge: `true`", phase_report)

        strict_criteria = (
            REPO_ROOT / "docs" / "ct2-vao-full-implementation-self-review-criteria-2026-05-11.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Evidence Strength", strict_criteria)
        self.assertIn("Hard Fail Conditions", strict_criteria)
        self.assertIn("A | Executed command output", strict_criteria)

    def test_readme_validation_delegates_to_self_verifier_without_pycache_drift(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("ct2-vao-self-verify --run-checks", readme)
        self.assertIn("PYTHONDONTWRITEBYTECODE=1", readme)
        self.assertNotIn("python3 -m py_compile", readme)

    def test_vao_self_verify_reports_all_static_gates_complete(self):
        verify = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-vao-self-verify", "--json", "--repo", REPO_ROOT])
        self.assertEqual(verify.returncode, 0, verify.stderr)
        report = json.loads(verify.stdout)
        self.assertTrue(report["complete"])
        self.assertEqual(0, report["unknown_count"])
        self.assertEqual(
            {
                "Artifact coverage",
                "Test coverage",
                "Spec coverage",
                "User/operator documentation coverage",
                "Safety invariant coverage",
                "Measurement honesty",
            },
            {gate["name"] for gate in report["gates"]},
        )
        documentation_items = {
            item["name"]
            for gate in report["gates"]
            if gate["name"] == "User/operator documentation coverage"
            for item in gate["items"]
        }
        self.assertIn("README validation command mirrors self-verifier", documentation_items)
        safety_items = {
            item["name"]
            for gate in report["gates"]
            if gate["name"] == "Safety invariant coverage"
            for item in gate["items"]
        }
        self.assertIn("negative verifier evidence fixture exists", safety_items)
        for gate in report["gates"]:
            self.assertEqual(1.0, gate["score"], gate["name"])

    def test_vao_self_verify_discovers_known_script_surfaces(self):
        verifier = load_script_module("ct2_vao_self_verify_test", "bin/ct2-vao-self-verify")

        python_files = set(verifier.python_check_files(REPO_ROOT))
        bash_files = set(verifier.bash_check_files(REPO_ROOT))

        for relpath in (
            "bin/ct2-vao-self-verify",
            "bin/_ct2_vao.py",
            "bin/_ct2_validate_review_sidecar.py",
        ):
            self.assertIn(relpath, python_files)

        for relpath in (
            "install.sh",
            "bin/ct2-init",
            "bin/ct2-seal",
            "claude-plugin/hooks/enforce-write-access.sh",
        ):
            self.assertIn(relpath, bash_files)

        self.assertNotIn("README.md", python_files)
        self.assertNotIn("README.md", bash_files)

    def test_vao_self_verify_discovery_uses_strict_shebangs_and_py_suffixes(self):
        verifier = load_script_module("ct2_vao_self_verify_fixture", "bin/ct2-vao-self-verify")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        (project / "bin").mkdir()
        (project / "claude-plugin" / "hooks").mkdir(parents=True)

        (project / "bin" / "helper.py").write_text("print('ok')\n", encoding="utf-8")
        (project / "bin" / "cli").write_text("#!/usr/bin/env python3\nprint('ok')\n", encoding="utf-8")
        (project / "bin" / "comment").write_text("# This script mentions python3\n", encoding="utf-8")
        (project / "bin" / "leading-blank").write_text("\n#!/usr/bin/env python3\n", encoding="utf-8")
        (project / "bin" / "shell").write_text("#!/usr/bin/env bash\nset -euo pipefail\n", encoding="utf-8")
        (project / "install.sh").write_text("#!/usr/bin/env bash\nset -euo pipefail\n", encoding="utf-8")
        (project / "claude-plugin" / "hooks" / "hook.sh").write_text("echo hook\n", encoding="utf-8")

        self.assertEqual(["bin/cli", "bin/helper.py"], verifier.python_check_files(project))
        self.assertEqual(
            ["bin/shell", "claude-plugin/hooks/hook.sh", "install.sh"],
            verifier.bash_check_files(project),
        )


if __name__ == "__main__":
    unittest.main()
