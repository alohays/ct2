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
FIXTURES = REPO_ROOT / "tests" / "fixtures"


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


def validate_workflow_run_manifest(manifest):
    """Reference validator for `ct2-workflow-run/v1` records.

    Implements the violation codes specified in spec/conformance.md
    ("Workflow-Run Manifest"). Returns a list of stable violation codes;
    an empty list means the record conforms.
    """
    violations = []
    ticket = manifest.get("ticket")
    if not isinstance(ticket, str) or not ticket.strip():
        violations.append("missing-ticket")
    subagents = manifest.get("subagents") or []
    verifiers = [agent for agent in subagents if agent.get("kind") == "verifier"]
    for agent in verifiers:
        prompt = agent.get("prompt", "")
        leaked = any(
            sibling.get("output", "") and sibling.get("output", "") in prompt
            for sibling in verifiers
            if sibling is not agent
        )
        if leaked:
            violations.append("sibling-output-in-verifier-prompt")
            break
    for agent in subagents:
        wrote_role = any(
            path.rstrip("/").split("/")[-1] == "ct2-active-role"
            for path in agent.get("writes", [])
        )
        if wrote_role:
            violations.append("subagent-wrote-active-role")
            break
    return violations


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
            "spec/protocol-surface.md",
            "spec/versioning.md",
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

    def _load_verify_module(self):
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
        return module

    def _write_role_doc(self, body: str) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = Path(tmp.name)
        role_doc = repo / "claude-plugin" / "skills" / "ct2-helm" / "SKILL.md"
        role_doc.parent.mkdir(parents=True)
        role_doc.write_text(body, encoding="utf-8")
        return repo

    def test_manual_done_bypass_checker_rejects_role_doc_override(self):
        module = self._load_verify_module()
        repo = self._write_role_doc(
            "- **Close the ticket**: Move to `done/` with a manual override note.\n"
        )
        ok, evidence = module.role_docs_no_done_bypass(repo)
        self.assertFalse(ok)
        self.assertIn("ct2-helm/SKILL.md:1", evidence)

    def test_manual_done_bypass_checker_rejects_reconciler_unavailable_variant(self):
        # Mere mention of "reconciler" must not whitelist a bypass instruction.
        module = self._load_verify_module()
        repo = self._write_role_doc(
            "- If the reconciler is unavailable, move the ticket to `done/` manually.\n"
        )
        ok, evidence = module.role_docs_no_done_bypass(repo)
        self.assertFalse(ok, evidence)
        self.assertIn("ct2-helm/SKILL.md:1", evidence)

    def test_manual_done_bypass_checker_rejects_do_not_wait_variant(self):
        # "Do not" prefixing an unrelated verb must not whitelist a same-line bypass.
        module = self._load_verify_module()
        repo = self._write_role_doc(
            "- Do not wait for review; move the ticket to `done/` manually.\n"
        )
        ok, evidence = module.role_docs_no_done_bypass(repo)
        self.assertFalse(ok, evidence)
        self.assertIn("ct2-helm/SKILL.md:1", evidence)

    def test_manual_done_bypass_checker_rejects_ct2_done_path_variant(self):
        # The actual state path `.ct2/done/` must be detected, not only the
        # short `done/` form.
        module = self._load_verify_module()
        repo = self._write_role_doc(
            "- Move the ticket to `.ct2/done/` after user confirmation.\n"
        )
        ok, evidence = module.role_docs_no_done_bypass(repo)
        self.assertFalse(ok, evidence)
        self.assertIn("ct2-helm/SKILL.md:1", evidence)

    def test_manual_done_bypass_checker_allows_explicit_prohibitions(self):
        module = self._load_verify_module()
        # Each of these must be allowed: explicit inline prohibition,
        # reservation prose, reconciler-as-subject prose, and lines inside a
        # prohibition section.
        body = (
            "## Allowed Writes\n"
            "- After dual approval the reconciler moves the ticket to `done/`.\n"
            "- Do not move tickets to `.ct2/done/`; only the reconciler can do that.\n"
            "- `done/` is reserved for ct2-reconcile after both lens approvals.\n"
            "\n"
            "## Forbidden Operations\n"
            "- Place tickets into `done/` (the reconciler handles this).\n"
            "\n"
            '<constraints id="prohibitions">\n'
            "- Place tickets into `done/` (reconciler handles this)\n"
            "</constraints>\n"
        )
        repo = self._write_role_doc(body)
        ok, evidence = module.role_docs_no_done_bypass(repo)
        self.assertTrue(ok, evidence)


class WorkflowRunManifestTest(unittest.TestCase):
    def load_fixture(self, name):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def test_manifest_format_is_specified(self):
        spec = (REPO_ROOT / "spec" / "conformance.md").read_text(encoding="utf-8")
        self.assertIn("ct2-workflow-run/v1", spec)
        for code in (
            "missing-ticket",
            "sibling-output-in-verifier-prompt",
            "subagent-wrote-active-role",
        ):
            with self.subTest(code=code):
                self.assertIn(code, spec)

    def test_conforming_manifest_passes(self):
        # The conforming fixture deliberately places WORKER output inside
        # both verifier prompts: a verifier may see the work product, only
        # a sibling reviewer's output is forbidden.
        manifest = self.load_fixture("workflow-run-conforming.json")
        self.assertEqual(validate_workflow_run_manifest(manifest), [])

    def test_missing_ticket_id_fails(self):
        manifest = self.load_fixture("workflow-run-missing-ticket.json")
        self.assertEqual(validate_workflow_run_manifest(manifest), ["missing-ticket"])

    def test_absent_ticket_key_fails(self):
        manifest = self.load_fixture("workflow-run-conforming.json")
        del manifest["ticket"]
        self.assertEqual(validate_workflow_run_manifest(manifest), ["missing-ticket"])

    def test_sibling_reviewer_output_in_verifier_prompt_fails(self):
        manifest = self.load_fixture("workflow-run-sibling-output.json")
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["sibling-output-in-verifier-prompt"],
        )

    def test_subagent_active_role_write_fails(self):
        manifest = self.load_fixture("workflow-run-role-write.json")
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["subagent-wrote-active-role"],
        )


if __name__ == "__main__":
    unittest.main()
