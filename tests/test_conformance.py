import json
import importlib.machinery
import importlib.util
import posixpath
import re
import subprocess
import sys
import tempfile
import unicodedata
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


MANIFEST_FORMAT = "ct2-workflow-run/v1"
SUBAGENT_KINDS = ("worker", "verifier")
# Anchor identities fixed by spec/reconciler.md (Terms): cc is Claude,
# cx is Codex. Violation code 4 binds the keys to these vendors.
ANCHOR_VENDORS = {"cc": "claude", "cx": "codex"}
# Sibling-output containment threshold (spec/conformance.md, code 2):
# outputs at or above this normalized length use substring containment;
# shorter non-empty outputs (a terse verdict such as "reject") are flagged
# when they appear in the prompt as a standalone word-boundary token
# sequence. Empty outputs never flag: nothing leaked.
SIBLING_OUTPUT_MIN_CHARS = 20
# Sanctioned .ct2/ surfaces, explicitly exempt from code 7: evidence/ and
# inbox/ are the re-entry contract's return channels; runtime/ is
# advisory; logs/ and telemetry/ are observability; worktrees/ is the
# Phase-1.5 isolated write target named by re-entry rule 2. Every other
# .ct2/ child is protected — the model is default-protected, so an
# unenumerated child (config/, .protocol-version, .migrations/, anything
# future) fails closed rather than open.
EXEMPT_CT2_SEGMENTS = frozenset({
    "evidence",
    "inbox",
    "runtime",
    "logs",
    "telemetry",
    "worktrees",
})


def _normalize_ws(value):
    """Normalization behind violation code 2 (spec/conformance.md).

    Unicode format code points (category Cf: ZWSP, ZWJ, BOM, ...) are
    stripped before whitespace is collapsed, so an invisible separator
    inserted into a leaked sibling output cannot break the token apart
    while a downstream model reads straight through it.
    """
    if not isinstance(value, str):
        return ""
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Cf")
    return " ".join(value.split())


def _sibling_output_leaked(output, prompt):
    """Containment check behind violation code 2 (spec/conformance.md).

    Both arguments are whitespace-normalized. An output of at least
    SIBLING_OUTPUT_MIN_CHARS characters uses plain substring containment;
    a shorter non-empty output (a terse verdict such as "reject") is
    flagged when it appears in the prompt bounded by string edges or
    non-word characters (lookaround boundaries, not bare \\b anchors —
    a \\b around an output that starts or ends with punctuation such as
    "reject!" or "[reject]" would silently fail to anchor), so a leaked
    punctuation-wrapped verdict cannot slip under the substring floor
    while a fragment inside a longer word ("pass" in "passport") does
    not fire. Empty outputs never flag: nothing leaked.
    """
    if not output:
        return False
    if len(output) >= SIBLING_OUTPUT_MIN_CHARS:
        return output in prompt
    pattern = r"(?<!\w)" + re.escape(output) + r"(?!\w)"
    return re.search(pattern, prompt) is not None


def _normalized_path_segments(path):
    """Shared write-path normalization for codes 3 and 7.

    One normal form feeds both codes so no path can fall between them:
    outer whitespace stripped, backslash separators normalized to
    slashes, posixpath.normpath applied, segments casefolded.
    """
    return [
        segment.casefold()
        for segment in posixpath.normpath(
            path.strip().replace("\\", "/")
        ).split("/")
        if segment and segment != "."
    ]


def _is_active_role_write(path):
    """Code 3: the write's final normalized component is the marker."""
    segments = _normalized_path_segments(path)
    return bool(segments) and segments[-1] == "ct2-active-role"


def _is_protected_ct2_write(path):
    """True when a write path lands on an authoritative `.ct2/` surface.

    Implements violation code 7 of spec/conformance.md ("Workflow-Run
    Manifest"). The model is default-protected: any `.ct2/` child not in
    EXEMPT_CT2_SEGMENTS is protected, so an unenumerated child (config/,
    .protocol-version, .migrations/, anything future) fails closed
    rather than open. Matching is on normalized path segments:
    posixpath.normpath resolves a leading `./`, `..` hops, duplicate
    slashes, and a trailing slash, and every `.ct2` segment is checked so
    absolute paths containing `/.ct2/` are covered. Backslash separators
    are normalized to slashes first, and segment comparisons are
    casefolded — case-insensitive filesystems (the macOS default) resolve
    `.CT2/Done/` onto the protected directories, so case variants must
    not validate clean. Fails closed on ambiguity: a write naming `.ct2`
    itself, with no resolvable child directory, is protected. A path
    whose final component is the `ct2-active-role` marker (casefolded)
    is excluded — that write reports as code 3
    (`subagent-wrote-active-role`), so one write maps to one code. Both
    codes consume the same _normalized_path_segments form, so a
    whitespace-padded or case-variant marker write cannot fall between
    them.
    """
    segments = _normalized_path_segments(path)
    if not segments or segments[-1] == "ct2-active-role":
        return False
    for index, segment in enumerate(segments):
        if segment != ".ct2":
            continue
        if index + 1 >= len(segments):
            return True
        if segments[index + 1] not in EXEMPT_CT2_SEGMENTS:
            return True
    return False


def _manifest_is_malformed(manifest):
    """Schema check behind the `malformed-manifest` violation code.

    Covers the top-level and subagent shapes; quorum shapes are checked in
    _validate_quorum, which reports the same code.
    """
    if not isinstance(manifest, dict):
        return True
    if manifest.get("manifest") != MANIFEST_FORMAT:
        return True
    subagents = manifest.get("subagents")
    if not isinstance(subagents, list):
        return True
    for record in subagents:
        if not isinstance(record, dict):
            return True
        for field in ("id", "kind", "prompt"):
            value = record.get(field)
            if not isinstance(value, str) or not value:
                return True
        if record["kind"] not in SUBAGENT_KINDS:
            return True
        writes = record.get("writes", [])
        if not isinstance(writes, list):
            return True
        if any(not isinstance(path, str) for path in writes):
            return True
    return False


def validate_workflow_run_manifest(manifest):
    """Reference validator for `ct2-workflow-run/v1` records.

    Implements the violation codes specified in spec/conformance.md
    ("Workflow-Run Manifest"). Returns a list of stable violation codes;
    an empty list means the record conforms. Fails closed: a malformed
    record is reported as `malformed-manifest` and the remaining checks
    still run on whatever can be read.
    """
    violations = []
    if _manifest_is_malformed(manifest):
        violations.append("malformed-manifest")
    if not isinstance(manifest, dict):
        return violations
    ticket = manifest.get("ticket")
    if not isinstance(ticket, str) or not ticket.strip():
        violations.append("missing-ticket")
    subagents = manifest.get("subagents")
    if not isinstance(subagents, list):
        subagents = []
    subagents = [record for record in subagents if isinstance(record, dict)]
    # Reviewer-class rule (spec code 2): every record whose kind is not
    # exactly "worker" is held to the sibling-output check, so a reviewer
    # relabeled "skeptic", "judge", or any future label cannot evade it.
    reviewers = [agent for agent in subagents if agent.get("kind") != "worker"]
    for agent in reviewers:
        prompt = _normalize_ws(agent.get("prompt"))
        leaked = False
        for sibling in reviewers:
            if sibling is agent:
                continue
            output = _normalize_ws(sibling.get("output"))
            if _sibling_output_leaked(output, prompt):
                leaked = True
                break
        if leaked:
            violations.append("sibling-output-in-verifier-prompt")
            break
    for agent in subagents:
        writes = agent.get("writes", [])
        if not isinstance(writes, list):
            writes = []
        wrote_role = any(
            isinstance(path, str) and _is_active_role_write(path)
            for path in writes
        )
        if wrote_role:
            violations.append("subagent-wrote-active-role")
            break
    for agent in subagents:
        writes = agent.get("writes", [])
        if not isinstance(writes, list):
            writes = []
        wrote_protected = any(
            isinstance(path, str) and _is_protected_ct2_write(path)
            for path in writes
        )
        if wrote_protected:
            violations.append("subagent-wrote-protected-path")
            break
    violations.extend(_validate_quorum(manifest.get("quorum")))
    deduped = []
    for code in violations:
        if code not in deduped:
            deduped.append(code)
    return deduped


def _validate_quorum(quorum):
    """Vendor-symmetry checks for the optional `quorum` declaration.

    Implements violation codes 4-5 of spec/conformance.md ("Workflow-Run
    Manifest"), plus the quorum-shape half of code 6 (`malformed-manifest`).
    Absence of a quorum means the protocol default — the cross-vendor cc
    AND cx anchors — which always conforms. Malformed records fail closed:
    they contribute neither key nor vendor toward the floor, and a record
    that is not the specified shape (an object with a non-empty string
    `key` and a non-empty string `vendor`) is reported, never silently
    skipped.
    """
    if quorum is None:
        return []
    if not isinstance(quorum, dict):
        return ["malformed-manifest", "quorum-single-vendor-satisfiable"]
    violations = []
    malformed = False
    binding = quorum.get("binding")
    if not isinstance(binding, list):
        malformed = True
        binding = []
    advisory = quorum.get("advisory", [])
    if not isinstance(advisory, list):
        malformed = True
        advisory = []
    for record in advisory:
        if not isinstance(record, dict):
            malformed = True
            continue
        key = record.get("key")
        if not isinstance(key, str) or not key:
            malformed = True
        vendor = record.get("vendor")
        if not isinstance(vendor, str) or not vendor.strip():
            malformed = True
    keys = set()
    vendors = set()
    anchor_vendors = {key: set() for key in ANCHOR_VENDORS}
    for record in binding:
        if not isinstance(record, dict):
            malformed = True
            continue
        key = record.get("key")
        if isinstance(key, str) and key:
            keys.add(key)
        else:
            # A hostile non-string key (a list or object) must not reach
            # the anchor membership test below — hashing it would raise —
            # and a missing or empty key is not the specified shape.
            malformed = True
            key = None
        vendor = record.get("vendor")
        vendor = vendor.strip() if isinstance(vendor, str) else ""
        if vendor:
            vendors.add(vendor)
        else:
            malformed = True
        if key in anchor_vendors:
            anchor_vendors[key].add(vendor)
    if malformed:
        violations.append("malformed-manifest")
    anchors_bound = all(
        anchor_vendors[key] == {required}
        for key, required in ANCHOR_VENDORS.items()
    )
    if not {"cc", "cx"} <= keys or len(vendors) < 2 or not anchors_bound:
        violations.append("quorum-single-vendor-satisfiable")
    rejection_rule = quorum.get("rejection_rule", "any-binding-rejects")
    if rejection_rule != "any-binding-rejects" or "threshold" in quorum:
        violations.append("quorum-overrides-cross-vendor-rejection")
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
            "subagent-wrote-protected-path",
            "malformed-manifest",
        ):
            with self.subTest(code=code):
                self.assertIn(code, spec)

    def test_conforming_manifest_passes(self):
        # The conforming fixture deliberately places WORKER output inside
        # both verifier prompts: a verifier may see the work product, only
        # a sibling reviewer's output is forbidden. Assert that precondition
        # first so this stays a regression guard against an over-broad
        # sibling-output check.
        manifest = self.load_fixture("workflow-run-conforming.json")
        worker = next(
            agent for agent in manifest["subagents"] if agent["kind"] == "worker"
        )
        verifiers = [
            agent for agent in manifest["subagents"] if agent["kind"] == "verifier"
        ]
        self.assertGreaterEqual(len(verifiers), 2)
        for verifier in verifiers:
            self.assertIn(worker["output"], verifier["prompt"])
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

    def test_relabeled_reviewer_cannot_evade_sibling_output_check(self):
        # A reviewer declared with kind "skeptic" is reviewer-class for the
        # sibling-output check; the undeclared label also fails the schema.
        manifest = self.load_fixture("workflow-run-skeptic-evasion.json")
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["malformed-manifest", "sibling-output-in-verifier-prompt"],
        )

    def test_unknown_kind_without_leak_fails_schema_only(self):
        manifest = self.load_fixture("workflow-run-conforming.json")
        manifest["subagents"][2]["kind"] = "judge"
        self.assertEqual(
            validate_workflow_run_manifest(manifest), ["malformed-manifest"]
        )

    def test_terse_sibling_output_in_instruction_template_is_flagged(self):
        # Fail closed (spec code 2): a sibling output of bare "approve" is
        # below the substring floor but appears as a standalone token in
        # the verifier's instruction template, so it fires. The check is
        # deliberately conservative — a coincidental standalone occurrence
        # like this one is flagged; conforming producers keep bare verdict
        # tokens out of verifier instruction text.
        manifest = self.load_fixture("workflow-run-conforming.json")
        manifest["subagents"][1]["output"] = "approve"
        manifest["subagents"][2]["prompt"] = (
            "Reply with the single word approve if nothing blocks: "
            "diff --git a/src/parser.py b/src/parser.py"
        )
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["sibling-output-in-verifier-prompt"],
        )

    def test_leaked_terse_verdict_tokens_are_flagged(self):
        # A parent orchestrator leaking a sibling's one-word verdict into
        # a verifier prompt is exactly the evasion the word-boundary rule
        # closes (spec code 2).
        for token in ("approve", "approved", "reject", "rejected"):
            with self.subTest(token=token):
                manifest = self.load_fixture("workflow-run-conforming.json")
                manifest["subagents"][1]["output"] = token
                manifest["subagents"][2]["prompt"] = (
                    f"The sibling verdict was {token}. Now review: "
                    "diff --git a/src/parser.py b/src/parser.py"
                )
                self.assertEqual(
                    validate_workflow_run_manifest(manifest),
                    ["sibling-output-in-verifier-prompt"],
                )

    def test_terse_output_inside_longer_word_is_not_flagged(self):
        # Word-boundary negative: "pass" occurring only inside "passport"
        # is not a standalone token sequence, so nothing fires.
        manifest = self.load_fixture("workflow-run-conforming.json")
        manifest["subagents"][1]["output"] = "pass"
        manifest["subagents"][2]["prompt"] = (
            "Check the passport validation: "
            "diff --git a/src/parser.py b/src/parser.py"
        )
        self.assertEqual(validate_workflow_run_manifest(manifest), [])

    def test_empty_sibling_output_is_not_flagged(self):
        # An empty or whitespace-only output leaks nothing (spec code 2).
        manifest = self.load_fixture("workflow-run-conforming.json")
        manifest["subagents"][1]["output"] = "   "
        self.assertEqual(validate_workflow_run_manifest(manifest), [])

    def test_wrong_manifest_identifier_fails(self):
        manifest = self.load_fixture("workflow-run-malformed.json")
        self.assertEqual(
            validate_workflow_run_manifest(manifest), ["malformed-manifest"]
        )

    def test_missing_subagents_key_fails(self):
        manifest = self.load_fixture("workflow-run-conforming.json")
        del manifest["subagents"]
        self.assertEqual(
            validate_workflow_run_manifest(manifest), ["malformed-manifest"]
        )

    def test_subagent_record_missing_prompt_fails(self):
        manifest = self.load_fixture("workflow-run-conforming.json")
        del manifest["subagents"][1]["prompt"]
        self.assertEqual(
            validate_workflow_run_manifest(manifest), ["malformed-manifest"]
        )

    def test_non_string_writes_entry_fails_without_crashing(self):
        manifest = self.load_fixture("workflow-run-conforming.json")
        manifest["subagents"][0]["writes"] = ["src/parser.py", 42]
        self.assertEqual(
            validate_workflow_run_manifest(manifest), ["malformed-manifest"]
        )

    def test_subagent_active_role_write_fails(self):
        manifest = self.load_fixture("workflow-run-role-write.json")
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["subagent-wrote-active-role"],
        )

    def test_subagent_protected_path_write_fails(self):
        # A subagent writing a ticket directly into done/ bypasses the
        # reconciler; the manifest must fail closed (spec code 7).
        manifest = self.load_fixture("workflow-run-protected-write.json")
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["subagent-wrote-protected-path"],
        )

    def test_protected_ct2_surface_writes_fail(self):
        # Every ticket state directory, the review sidecars, and the .meta
        # markers are authoritative surfaces (spec code 7).
        for path in (
            ".ct2/draft/001-wip.md",
            ".ct2/backlog/001-queued.md",
            ".ct2/in-progress/001-claimed.md",
            ".ct2/in-review/001-pending.md",
            ".ct2/rejected/001-rework.md",
            ".ct2/escalated/001-stuck.md",
            ".ct2/reviews/001-cx-r1.md",
            ".ct2/.meta/anything",
        ):
            with self.subTest(path=path):
                manifest = self.load_fixture("workflow-run-conforming.json")
                manifest["subagents"][0]["writes"] = ["src/parser.py", path]
                self.assertEqual(
                    validate_workflow_run_manifest(manifest),
                    ["subagent-wrote-protected-path"],
                )

    def test_protected_path_matching_normalizes_segments(self):
        # A leading ./, an absolute prefix, a .. hop, and a trailing slash
        # all resolve before matching; a bare .ct2 write fails closed.
        for path in (
            "./.ct2/done/001-bypass.md",
            "/home/runner/project/.ct2/done/001-bypass.md",
            ".ct2/done/",
            ".ct2/evidence/../done/001-bypass.md",
            ".ct2",
        ):
            with self.subTest(path=path):
                manifest = self.load_fixture("workflow-run-conforming.json")
                manifest["subagents"][0]["writes"] = [path]
                self.assertEqual(
                    validate_workflow_run_manifest(manifest),
                    ["subagent-wrote-protected-path"],
                )

    def test_case_variant_protected_paths_fail(self):
        # Case-insensitive filesystems (the macOS default) resolve case
        # variants onto the protected directories; segment comparisons
        # are casefolded so a relabeled case cannot validate clean
        # (lens-cx round-2 finding).
        for path in (
            ".CT2/done/001-bypass.md",
            ".ct2/Done/001-bypass.md",
            ".Ct2/reviews/001-cx-r1.md",
            ".ct2/IN-REVIEW/001-pending.md",
            ".ct2/.META/anything",
        ):
            with self.subTest(path=path):
                manifest = self.load_fixture("workflow-run-conforming.json")
                manifest["subagents"][0]["writes"] = [path]
                self.assertEqual(
                    validate_workflow_run_manifest(manifest),
                    ["subagent-wrote-protected-path"],
                )

    def test_backslash_separator_protected_paths_fail(self):
        # Alternate separator forms are normalized before matching, not
        # passed through (lens-cx round-2 finding).
        for path in (".ct2\\done\\001-bypass.md", "\\.ct2\\reviews\\001.md"):
            with self.subTest(path=path):
                manifest = self.load_fixture("workflow-run-conforming.json")
                manifest["subagents"][0]["writes"] = [path]
                self.assertEqual(
                    validate_workflow_run_manifest(manifest),
                    ["subagent-wrote-protected-path"],
                )

    def test_case_variant_active_role_write_reports_code_3(self):
        # The active-role marker match is casefolded consistently with
        # code 7, so the case-variant marker write still maps to code 3.
        manifest = self.load_fixture("workflow-run-conforming.json")
        manifest["subagents"][0]["writes"] = [".ct2/.meta/CT2-ACTIVE-ROLE"]
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["subagent-wrote-active-role"],
        )

    def test_whitespace_padded_active_role_write_reports_code_3(self):
        # Codes 3 and 7 consume one shared normal form, so a
        # whitespace-padded marker write cannot fall between them: it
        # classifies as the trimmed canonical marker, code 3 (lens-cx
        # round-3 finding).
        for path in (
            ".ct2/.meta/ct2-active-role ",
            ".ct2/.meta/ct2-active-role\n",
            ".ct2/.meta/ct2-active-role\t",
            " .ct2/.meta/ct2-active-role",
        ):
            with self.subTest(path=repr(path)):
                manifest = self.load_fixture("workflow-run-conforming.json")
                manifest["subagents"][0]["writes"] = [path]
                self.assertEqual(
                    validate_workflow_run_manifest(manifest),
                    ["subagent-wrote-active-role"],
                )

    def test_meta_write_with_internal_whitespace_reports_code_7(self):
        # Internal whitespace stays significant: not the marker, but
        # still under protected .ct2/.meta/ — code 7, never clean.
        manifest = self.load_fixture("workflow-run-conforming.json")
        manifest["subagents"][0]["writes"] = [".ct2/.meta/ct2-active-role x"]
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["subagent-wrote-protected-path"],
        )

    def test_case_variant_exempt_channel_writes_pass(self):
        # Exemptions casefold symmetrically with protections: a case
        # variant of a sanctioned channel is still that channel.
        manifest = self.load_fixture("workflow-run-conforming.json")
        manifest["subagents"][0]["writes"] = [
            ".ct2/Evidence/claims.jsonl",
            ".CT2/inbox/helm/msg.md",
        ]
        self.assertEqual(validate_workflow_run_manifest(manifest), [])

    def test_punctuation_wrapped_terse_verdict_leak_is_flagged(self):
        # \b around an escaped output that starts or ends with punctuation
        # fails to anchor; lookaround boundaries do not (lens-cx round-2
        # finding). Each output is copied verbatim into a sibling
        # verifier's prompt and must fire spec code 2.
        for output in (
            "reject.",
            "reject!",
            '"reject"',
            "[reject]",
            "(reject)",
            "**reject**",
        ):
            with self.subTest(output=output):
                manifest = self.load_fixture("workflow-run-conforming.json")
                manifest["subagents"][1]["output"] = output
                manifest["subagents"][2]["prompt"] = (
                    "Review the diff. Context note: " + output
                )
                self.assertEqual(
                    validate_workflow_run_manifest(manifest),
                    ["sibling-output-in-verifier-prompt"],
                )

    def test_zero_width_separator_in_leak_is_still_flagged(self):
        # Unicode format code points (Cf: ZWSP, ZWJ) are invisible to the
        # downstream model but break naive substring containment, so a
        # single one inserted into the leaked copy would defeat spec
        # code 2 while keeping the manifest faithful to the real prompt.
        # Normalization strips them; both the substring path (long
        # output) and the lookaround path (terse verdict) must still
        # fire (ultracode review finding).
        long_output = "verdict: approve. Findings: none blocking."
        for zero_width in ("\u200b", "\u200d"):
            for output in ("reject", long_output):
                with self.subTest(
                    zero_width=f"U+{ord(zero_width):04X}", output=output
                ):
                    manifest = self.load_fixture("workflow-run-conforming.json")
                    manifest["subagents"][1]["output"] = output
                    middle = len(output) // 2
                    leaked = output[:middle] + zero_width + output[middle:]
                    manifest["subagents"][2]["prompt"] = (
                        "Review the diff. Context note: " + leaked
                    )
                    self.assertEqual(
                        validate_workflow_run_manifest(manifest),
                        ["sibling-output-in-verifier-prompt"],
                    )

    def test_sanctioned_return_channel_writes_pass(self):
        # evidence/ and inbox/ are the re-entry contract's sanctioned
        # return channels; runtime/, logs/, and telemetry/ are advisory
        # and observability surfaces (spec code 7 exemptions).
        manifest = self.load_fixture("workflow-run-conforming.json")
        manifest["subagents"][0]["writes"] = [
            "src/parser.py",
            ".ct2/evidence/claims.jsonl",
            ".ct2/inbox/helm/msg.md",
            ".ct2/runtime/fanout/record.json",
            ".ct2/logs/ct2-forge.log",
            ".ct2/telemetry/events.jsonl",
        ]
        self.assertEqual(validate_workflow_run_manifest(manifest), [])

    def test_unenumerated_ct2_children_fail_closed(self):
        # Default-protected (spec code 7): a .ct2/ child outside the
        # exempt list is authoritative — config/ parameterizes the
        # reconciler's verdict table (max_review_rounds) and skeptic
        # promotion, .protocol-version gates the state-mutating helpers —
        # so an unenumerated child reports, never validates clean
        # (ultracode review finding).
        for path in (
            ".ct2/config/harness.yaml",
            ".ct2/.protocol-version",
            ".ct2/.migrations/0001-layout.sh",
            ".ct2/decisions/pending/d1.md",
            ".ct2/plans/plan.md",
        ):
            with self.subTest(path=path):
                manifest = self.load_fixture("workflow-run-conforming.json")
                manifest["subagents"][0]["writes"] = ["src/parser.py", path]
                self.assertEqual(
                    validate_workflow_run_manifest(manifest),
                    ["subagent-wrote-protected-path"],
                )

    def test_worktree_writes_pass(self):
        # .ct2/worktrees/ is the Phase-1.5 isolated write target named by
        # re-entry rule 2 — exactly where workflow edits are supposed to
        # land, so it is exempt from code 7.
        manifest = self.load_fixture("workflow-run-conforming.json")
        manifest["subagents"][0]["writes"] = [
            ".ct2/worktrees/001-fanout/src/parser.py",
        ]
        self.assertEqual(validate_workflow_run_manifest(manifest), [])

    def test_cross_vendor_quorum_with_advisory_skeptic_passes(self):
        # Anchors cc (claude) AND cx (codex) binding, plus a same-vendor
        # skeptic kept advisory: the conforming quorum shape.
        manifest = self.load_fixture("workflow-run-quorum-conforming.json")
        self.assertEqual(validate_workflow_run_manifest(manifest), [])

    def test_single_vendor_satisfiable_quorum_fails(self):
        # cx demoted to advisory; a claude judge-panel forms the binding
        # set. Satisfiable by one vendor => Claude-primary drift.
        manifest = self.load_fixture("workflow-run-quorum-single-vendor.json")
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["quorum-single-vendor-satisfiable"],
        )

    def test_same_vendor_majority_override_fails(self):
        # Both anchors present, but vote/threshold semantics would let a
        # same-vendor majority outvote a single cross-vendor rejection.
        manifest = self.load_fixture("workflow-run-quorum-majority-override.json")
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["quorum-overrides-cross-vendor-rejection"],
        )

    def test_quorum_missing_anchor_fails_despite_two_vendors(self):
        # Two distinct vendors are not enough: both anchor keys (cc, cx)
        # must be in the binding set. A codex skeptic cannot substitute
        # for the cx anchor.
        manifest = self.load_fixture("workflow-run-quorum-conforming.json")
        manifest["quorum"]["binding"] = [
            {"key": "cc", "vendor": "claude"},
            {"key": "sk1", "vendor": "codex"},
        ]
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["quorum-single-vendor-satisfiable"],
        )

    def test_quorum_unknown_vendor_fails_closed(self):
        # A reviewer whose vendor cannot be determined never counts toward
        # cross-vendor coverage, and an empty vendor is not the specified
        # record shape (spec code 6), so the record is also malformed.
        manifest = self.load_fixture("workflow-run-quorum-conforming.json")
        manifest["quorum"]["binding"] = [
            {"key": "cc", "vendor": "claude"},
            {"key": "cx", "vendor": ""},
        ]
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["malformed-manifest", "quorum-single-vendor-satisfiable"],
        )

    def test_quorum_swapped_anchor_vendors_fail(self):
        # Anchor keys are bound to fixed vendors (spec/reconciler.md, Terms):
        # cc is claude and cx is codex. Swapping them spans two vendors but
        # breaks the anchor identities.
        manifest = self.load_fixture("workflow-run-quorum-swapped-anchors.json")
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["quorum-single-vendor-satisfiable"],
        )

    def test_quorum_same_vendor_anchor_fails_despite_extra_vendor(self):
        # cx declaring claude is single-vendor drift even when a codex
        # skeptic makes the binding set span two vendors.
        manifest = self.load_fixture("workflow-run-quorum-conforming.json")
        manifest["quorum"]["binding"] = [
            {"key": "cc", "vendor": "claude"},
            {"key": "cx", "vendor": "claude"},
            {"key": "sk1", "vendor": "codex"},
        ]
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["quorum-single-vendor-satisfiable"],
        )

    def test_quorum_non_dict_binding_records_fail_closed(self):
        # A non-object binding record is malformed and contributes neither
        # key nor vendor, so the floor violation fires as well.
        manifest = self.load_fixture("workflow-run-quorum-conforming.json")
        manifest["quorum"]["binding"] = ["cc", "cx"]
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["malformed-manifest", "quorum-single-vendor-satisfiable"],
        )

    def test_non_dict_quorum_fails_closed(self):
        # A quorum that is not an object at all is malformed and cannot
        # demonstrate the cross-vendor floor (spec code 6).
        for quorum in ("any-two", ["cc", "cx"]):
            with self.subTest(quorum=quorum):
                manifest = self.load_fixture(
                    "workflow-run-quorum-conforming.json"
                )
                manifest["quorum"] = quorum
                self.assertEqual(
                    validate_workflow_run_manifest(manifest),
                    ["malformed-manifest", "quorum-single-vendor-satisfiable"],
                )

    def test_quorum_non_list_binding_fails_closed(self):
        # A non-array binding declaration contributes no anchors, so the
        # floor violation fires alongside the shape report (spec code 6).
        manifest = self.load_fixture("workflow-run-quorum-conforming.json")
        manifest["quorum"]["binding"] = "cc,cx"
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["malformed-manifest", "quorum-single-vendor-satisfiable"],
        )

    def test_quorum_off_shape_advisory_fails_closed(self):
        # A non-array advisory declaration, or an advisory record that is
        # not the specified shape, is malformed (spec code 6); the intact
        # binding set keeps the floor satisfied, isolating the report.
        for advisory in ("none", ["sk1"], [{"foo": 1}]):
            with self.subTest(advisory=advisory):
                manifest = self.load_fixture(
                    "workflow-run-quorum-conforming.json"
                )
                manifest["quorum"]["advisory"] = advisory
                self.assertEqual(
                    validate_workflow_run_manifest(manifest),
                    ["malformed-manifest"],
                )

    def test_quorum_dict_records_off_shape_fail_closed(self):
        # A record that is an object but lacks a non-empty string key or
        # a non-empty string vendor is not the specified shape (spec
        # code 6) and must be reported, never silently skipped. The
        # intact anchors keep the floor satisfied, isolating the report.
        anchors = [
            {"key": "cc", "vendor": "claude"},
            {"key": "cx", "vendor": "codex"},
        ]
        for label, extra_record in (
            ("missing vendor", {"key": "sk1"}),
            ("non-string key", {"key": 42, "vendor": "codex"}),
            ("empty key", {"key": "", "vendor": "codex"}),
        ):
            with self.subTest(label=label):
                manifest = self.load_fixture(
                    "workflow-run-quorum-conforming.json"
                )
                manifest["quorum"]["binding"] = anchors + [extra_record]
                self.assertEqual(
                    validate_workflow_run_manifest(manifest),
                    ["malformed-manifest"],
                )

    def test_hostile_quorum_binding_key_fails_closed_without_crashing(self):
        # A binding key declared as a JSON array or object must not crash
        # the anchor membership test (hashing an unhashable key raises
        # TypeError); the record is off-shape, so it reports malformed and
        # contributes nothing toward the floor (ultracode review finding).
        for hostile_key in (["cc"], {"x": 1}):
            with self.subTest(key=hostile_key):
                manifest = self.load_fixture(
                    "workflow-run-quorum-conforming.json"
                )
                manifest["quorum"]["binding"] = [
                    {"key": hostile_key, "vendor": "claude"},
                    {"key": "cx", "vendor": "codex"},
                ]
                self.assertEqual(
                    validate_workflow_run_manifest(manifest),
                    ["malformed-manifest", "quorum-single-vendor-satisfiable"],
                )

    def test_hostile_quorum_key_does_not_discard_other_violations(self):
        # _validate_quorum runs last; a crash there would throw away every
        # violation already collected. A manifest that both writes done/
        # and carries a list-typed key must report all three codes.
        manifest = self.load_fixture("workflow-run-quorum-conforming.json")
        manifest["subagents"][0]["writes"] = [".ct2/done/001-bypass.md"]
        manifest["quorum"]["binding"] = [
            {"key": ["cc"], "vendor": "claude"},
            {"key": "cx", "vendor": "codex"},
        ]
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            [
                "subagent-wrote-protected-path",
                "malformed-manifest",
                "quorum-single-vendor-satisfiable",
            ],
        )

    def test_quorum_threshold_alone_fails(self):
        # Threshold semantics is the override mechanism even when the
        # rejection rule is left conforming (spec code 5): a threshold is
        # exactly what would let a same-vendor majority outvote a single
        # cross-vendor rejection.
        manifest = self.load_fixture("workflow-run-quorum-conforming.json")
        manifest["quorum"]["threshold"] = 2
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["quorum-overrides-cross-vendor-rejection"],
        )

    def test_quorum_rejection_rule_alone_fails(self):
        # A vote-style rejection rule fails on its own, without any
        # declared threshold (spec code 5).
        manifest = self.load_fixture("workflow-run-quorum-conforming.json")
        manifest["quorum"]["rejection_rule"] = "binding-majority"
        self.assertNotIn("threshold", manifest["quorum"])
        self.assertEqual(
            validate_workflow_run_manifest(manifest),
            ["quorum-overrides-cross-vendor-rejection"],
        )


class ClaudePrimaryDriftTest(unittest.TestCase):
    """Drift guard for spec/conformance.md "Vendor Symmetry" rule 3.

    lens-cx is first-class at parity with lens-cc. Each check asserts
    against real repo files so that removing or degrading a Codex-side
    surface without an equivalent Claude-side change fails conformance.
    """

    def test_adapter_lens_variants_are_identical_across_runtimes(self):
        per_runtime = {}
        for runtime in ("claude", "codex"):
            adapter_dir = REPO_ROOT / "adapters" / runtime
            per_runtime[runtime] = {
                path.name for path in adapter_dir.glob("lens-*.md")
            }
        self.assertEqual(per_runtime["claude"], per_runtime["codex"])
        self.assertLessEqual({"lens-cc.md", "lens-cx.md"}, per_runtime["claude"])

    def test_plugin_skills_retain_their_lens_role(self):
        for rel in (
            "claude-plugin/skills/ct2-lens-cc/SKILL.md",
            "codex-plugin/skills/ct2-lens-cx/SKILL.md",
        ):
            with self.subTest(rel=rel):
                path = REPO_ROOT / rel
                self.assertTrue(path.is_file(), f"missing lens skill: {rel}")
                self.assertTrue(path.read_text(encoding="utf-8").strip())

    def test_config_retains_both_lens_role_docs(self):
        for rel in ("config/ct2-lens-cc-role.md", "config/ct2-lens-cx-role.md"):
            with self.subTest(rel=rel):
                path = REPO_ROOT / rel
                self.assertTrue(path.is_file(), f"missing role config: {rel}")
                self.assertTrue(path.read_text(encoding="utf-8").strip())

    def test_runtime_doctor_probes_both_vendors(self):
        doctor = (REPO_ROOT / "bin" / "ct2-runtime-doctor").read_text(encoding="utf-8")
        for marker in ("codex", "claude", "lens-cx", "lens-cc"):
            with self.subTest(marker=marker):
                self.assertIn(marker, doctor)

    def test_vendor_symmetry_is_specified(self):
        spec = (REPO_ROOT / "spec" / "conformance.md").read_text(encoding="utf-8")
        self.assertIn("## Vendor Symmetry", spec)
        for needle in (
            "quorum-single-vendor-satisfiable",
            "quorum-overrides-cross-vendor-rejection",
            "either reviewer rejects means rejected",
            "delete every Codex reference",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, spec)

    def test_codex_references_are_load_bearing_in_core_specs(self):
        # The one-line litmus (spec/conformance.md, Vendor Symmetry):
        # deleting every Codex reference must break the protocol. These
        # core specs must therefore keep naming lens-cx.
        for rel in (
            "spec/PROTOCOL.md",
            "spec/reconciler.md",
            "spec/conformance.md",
        ):
            with self.subTest(rel=rel):
                text = (REPO_ROOT / rel).read_text(encoding="utf-8")
                self.assertIn("lens-cx", text)


if __name__ == "__main__":
    unittest.main()
