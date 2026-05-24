import json
import re
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


def parse_version(value):
    major, minor, patch = (int(part) for part in value.split("."))
    return major, minor, patch


def bumped_patch(value):
    major, minor, patch = parse_version(value)
    return f"{major}.{minor}.{patch + 1}"


def add_unreleased_bullet(repo, bullet="- Release test entry."):
    path = repo / "CHANGELOG.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace("### Changed\n\n", f"### Changed\n\n{bullet}\n", 1)
    path.write_text(text, encoding="utf-8")


def clear_unreleased_bullets(repo):
    path = repo / "CHANGELOG.md"
    text = path.read_text(encoding="utf-8")
    marker = "## [Unreleased]"
    start = text.index(marker) + len(marker)
    next_start = text.index("\n## [", start)
    empty = "\n\n### Added\n\n### Changed\n\n### Fixed\n\n### Deprecated\n\n### Removed\n\n### Security\n\n"
    path.write_text(text[:start] + empty + text[next_start:], encoding="utf-8")


def make_release_repo(test_case):
    tmp = tempfile.TemporaryDirectory()
    test_case.addCleanup(tmp.cleanup)
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

    test_case.assertEqual(run_cmd(["git", "init"], cwd=repo).returncode, 0)
    test_case.assertEqual(run_cmd(["git", "add", "."], cwd=repo).returncode, 0)
    test_case.assertEqual(
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
    return repo


class ReleaseWorkflowTest(unittest.TestCase):
    def test_version_file_and_plugin_manifests_match(self):
        version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(version, r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
        for rel in (
            "claude-plugin/.claude-plugin/plugin.json",
            "codex-plugin/.codex-plugin/plugin.json",
        ):
            with self.subTest(rel=rel):
                data = json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))
                self.assertEqual(version, data["version"])

    def test_ct2_status_version_output_is_project_independent(self):
        version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        protocol = ".".join(version.split(".")[:2])
        proc = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-status", "--version"], cwd=REPO_ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(f"ct2 {version}", proc.stdout)
        self.assertIn(f"plugin (claude): {version}", proc.stdout)
        self.assertIn(f"plugin (codex):  {version}", proc.stdout)
        self.assertIn(f"protocol:        {protocol}", proc.stdout)

    def test_changelog_bootstrap_sections_exist(self):
        text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## [Unreleased]", text)
        self.assertIn("## [0.2.0]", text)
        self.assertIn("## [0.1.0]", text)

    def test_prepare_patch_updates_derived_artifacts_and_creates_one_commit(self):
        repo = make_release_repo(self)
        add_unreleased_bullet(repo)

        version = (repo / "VERSION").read_text(encoding="utf-8").strip()
        next_version = bumped_patch(version)
        before = run_cmd(["git", "rev-list", "--count", "HEAD"], cwd=repo)
        self.assertEqual(before.stdout.strip(), "1")
        proc = run_cmd([PYTHON, repo / "bin" / "ct2-release", "prepare", "patch"], cwd=repo)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(next_version, (repo / "VERSION").read_text(encoding="utf-8").strip())
        for rel in (
            "claude-plugin/.claude-plugin/plugin.json",
            "codex-plugin/.codex-plugin/plugin.json",
        ):
            data = json.loads((repo / rel).read_text(encoding="utf-8"))
            self.assertEqual(next_version, data["version"])
        changelog = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## [{next_version}]", changelog)
        after = run_cmd(["git", "rev-list", "--count", "HEAD"], cwd=repo)
        self.assertEqual(after.stdout.strip(), "2")

    def test_prepare_rejects_invalid_semver(self):
        for value in ("1.2", "", "1.2.3-rc.1"):
            with self.subTest(value=value):
                repo = make_release_repo(self)
                (repo / "VERSION").write_text(value, encoding="utf-8")
                proc = run_cmd([PYTHON, repo / "bin" / "ct2-release", "prepare", "patch"], cwd=repo)
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn("invalid SemVer", proc.stderr)

    def test_prepare_fails_on_missing_unreleased_section_without_version_mutation(self):
        repo = make_release_repo(self)
        original = (repo / "VERSION").read_text(encoding="utf-8")
        changelog = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
        (repo / "CHANGELOG.md").write_text(changelog.replace("## [Unreleased]", "## [Next]", 1), encoding="utf-8")
        proc = run_cmd([PYTHON, repo / "bin" / "ct2-release", "prepare", "patch"], cwd=repo)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("missing an [Unreleased]", proc.stderr)
        self.assertEqual(original, (repo / "VERSION").read_text(encoding="utf-8"))

    def test_prepare_rejects_empty_unreleased_body(self):
        repo = make_release_repo(self)
        clear_unreleased_bullets(repo)
        original = (repo / "VERSION").read_text(encoding="utf-8")
        proc = run_cmd([PYTHON, repo / "bin" / "ct2-release", "prepare", "patch"], cwd=repo)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("[Unreleased] is empty", proc.stderr)
        self.assertEqual(original, (repo / "VERSION").read_text(encoding="utf-8"))

    def test_prepare_second_run_fails_instead_of_silent_noop(self):
        repo = make_release_repo(self)
        add_unreleased_bullet(repo)
        first = run_cmd([PYTHON, repo / "bin" / "ct2-release", "prepare", "patch"], cwd=repo)
        self.assertEqual(first.returncode, 0, first.stderr)
        second = run_cmd([PYTHON, repo / "bin" / "ct2-release", "prepare", "patch"], cwd=repo)
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("[Unreleased] is empty", second.stderr)

    def test_sync_no_op_when_aligned(self):
        repo = make_release_repo(self)
        paths = [
            repo / "install.sh",
            repo / "claude-plugin" / ".claude-plugin" / "plugin.json",
            repo / "codex-plugin" / ".codex-plugin" / "plugin.json",
        ]
        before = {path: path.stat().st_mtime_ns for path in paths}
        proc = run_cmd([PYTHON, repo / "bin" / "ct2-release", "sync"], cwd=repo)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        after = {path: path.stat().st_mtime_ns for path in paths}
        self.assertEqual(before, after)

    def test_install_sh_help_avoids_bare_empty_array_expansion(self):
        install = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn('${POSITIONAL[@]+"${POSITIONAL[@]}"}', install)
        self.assertIsNone(re.search(r'set -- "\\$\\{POSITIONAL\\[@\\]\\}"', install))

    def test_prepare_with_pre_existing_staged_changes_keeps_them_out_of_release_commit(self):
        repo = make_release_repo(self)
        add_unreleased_bullet(repo)
        unrelated = repo / "unrelated.txt"
        unrelated.write_text("keep me staged\n", encoding="utf-8")
        self.assertEqual(run_cmd(["git", "add", "unrelated.txt"], cwd=repo).returncode, 0)

        proc = run_cmd([PYTHON, repo / "bin" / "ct2-release", "prepare", "patch"], cwd=repo)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        committed = run_cmd(["git", "show", "--name-only", "--format=", "HEAD"], cwd=repo)
        self.assertNotIn("unrelated.txt", committed.stdout.splitlines())
        staged = run_cmd(["git", "diff", "--cached", "--name-only"], cwd=repo)
        self.assertIn("unrelated.txt", staged.stdout.splitlines())

    def test_release_workflow_and_installer_pin_are_documented(self):
        version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn('python3 bin/ct2-release prepare "$BUMP"', workflow)
        self.assertIn('git push origin "HEAD:${{ github.ref_name }}"', workflow)
        self.assertIn("git config user.name", workflow)
        self.assertIn("git ls-remote --exit-code --tags origin", workflow)
        self.assertIn("gh release create", workflow)
        self.assertIn('host="$(mktemp -d)"', workflow)
        self.assertIn('bash "$GITHUB_WORKSPACE/bin/ct2-init" "$host"', workflow)
        self.assertIn('"$GITHUB_WORKSPACE/bin/ct2-trace-lint" --strict "$host"', workflow)
        self.assertNotIn("bin/ct2-trace-lint --strict .", workflow)
        install = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("--version", install)
        self.assertIn(f"CT2_INSTALL_VERSION=\"{version}\"", install)


if __name__ == "__main__":
    unittest.main()
