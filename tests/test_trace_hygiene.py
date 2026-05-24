import json
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


def write_ticket(
    path,
    title="Parse nested config",
    branch="null",
    requirements="- [x] Parse nested config safely.",
    context="This change keeps generated host repository artifacts clean.",
    acceptance="- [x] Branch names omit CT2 ticket IDs.\n- [x] PR body hides CT2 mapping metadata.",
):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
id: "001"
title: "{title}"
status: in-progress
priority: medium
created: 2026-05-24T00:00:00Z
updated: 2026-05-24T00:00:00Z
sealed: 2026-05-24T00:00:00Z
branch: {branch}
pr: null
review-round: 0
duration-bounce-count: 0
total-attempts: 0
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
{requirements}

## Constraints
- Use stdlib-only tests.

## Context
{context}

## Acceptance Criteria
{acceptance}
""",
        encoding="utf-8",
    )


class TraceHygieneTest(unittest.TestCase):
    def make_git_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        self.assertEqual(run_cmd(["git", "init"], cwd=project).returncode, 0)
        self.assertEqual(run_cmd(["git", "config", "user.name", "CT2 Test"], cwd=project).returncode, 0)
        self.assertEqual(run_cmd(["git", "config", "user.email", "ct2@example.invalid"], cwd=project).returncode, 0)
        (project / "README.md").write_text("# Host\n", encoding="utf-8")
        self.assertEqual(run_cmd(["git", "add", "README.md"], cwd=project).returncode, 0)
        self.assertEqual(run_cmd(["git", "commit", "-m", "init"], cwd=project).returncode, 0)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project])
        self.assertEqual(init.returncode, 0, init.stderr)
        return project

    def strip_trace_hygiene(self, project):
        cfg = project / ".ct2" / "config" / "harness.yaml"
        text = cfg.read_text(encoding="utf-8")
        cfg.write_text(text.split("# Host-repo cleanliness defaults", 1)[0].rstrip() + "\n", encoding="utf-8")

    def test_default_config_and_template_are_clean(self):
        config = (REPO_ROOT / "config" / "harness.yaml").read_text(encoding="utf-8")
        template = (REPO_ROOT / "templates" / "ticket.md").read_text(encoding="utf-8")
        git_submit = (REPO_ROOT / "bin" / "ct2-git-submit").read_text(encoding="utf-8")

        self.assertIn("trace_hygiene:", config)
        self.assertIn("preset: clean", config)
        self.assertIn("branch: null", template)
        self.assertNotIn("Opened by ct2-forge via ct2-git-submit.", git_submit)
        self.assertNotIn("Ticket: `.ct2/in-review/", git_submit)

    def test_clean_pr_body_hides_ct2_strings(self):
        project = self.make_git_project()
        ticket = project / ".ct2" / "in-progress" / "001-parse-nested-config.md"
        write_ticket(
            ticket,
            requirements=(
                "- [x] 🤖 Automated by ct2-forge in .ct2/in-progress/001-parse-nested-config.md\n"
                "- [x] Keep the visible behavior"
            ),
            context=(
                "This change keeps generated host repository artifacts clean.\n"
                "<!-- hidden\ncomment mentioning ct2-lens-cc and .ct2/reviews/001-cx-r0.md\n-->\n"
                "Visible summary stays."
            ),
        )

        body = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "_ct2_trace_hygiene.py",
                "pr-body",
                "--ticket",
                ticket,
                "--ct2-dir",
                project / ".ct2",
                "--ticket-file",
                ticket.name,
            ]
        )

        self.assertEqual(body.returncode, 0, body.stderr)
        self.assertNotIn("ct2-forge", body.stdout)
        self.assertNotIn("ct2-lens-cc", body.stdout)
        self.assertNotIn("🤖", body.stdout)
        self.assertNotIn("Ticket: `.ct2", body.stdout)
        self.assertNotIn(".ct2/", body.stdout)
        self.assertNotIn(".ct2/in-review", body.stdout)
        self.assertNotIn("hidden", body.stdout)
        self.assertNotIn("comment mentioning", body.stdout)
        self.assertIn("Visible summary stays.", body.stdout)
        self.assertIn("<!-- ct2-ticket: 001 / pr-managed -->", body.stdout)
        self.assertIn("## What changed", body.stdout)
        self.assertIn("## Acceptance criteria", body.stdout)

    def test_pr_body_links_mirrored_github_issue(self):
        project = self.make_git_project()
        ticket = project / ".ct2" / "in-progress" / "001-parse-nested-config.md"
        write_ticket(ticket)
        ticket.write_text(
            ticket.read_text(encoding="utf-8").replace("pr: null\n", "pr: null\nissue: 142\n"),
            encoding="utf-8",
        )

        body = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "_ct2_trace_hygiene.py",
                "pr-body",
                "--ticket",
                ticket,
                "--ct2-dir",
                project / ".ct2",
                "--ticket-file",
                ticket.name,
            ]
        )

        self.assertEqual(body.returncode, 0, body.stderr)
        self.assertTrue(body.stdout.startswith("Closes #142\n\n"), body.stdout)

    def test_pr_closes_issue_false_omits_closes_line(self):
        project = self.make_git_project()
        cfg = project / ".ct2" / "config" / "harness.yaml"
        cfg.write_text(cfg.read_text(encoding="utf-8").replace("pr_closes_issue: true", "pr_closes_issue: false"), encoding="utf-8")
        ticket = project / ".ct2" / "in-progress" / "001-parse-nested-config.md"
        write_ticket(ticket)
        ticket.write_text(
            ticket.read_text(encoding="utf-8").replace("pr: null\n", "pr: null\nissue: 142\n"),
            encoding="utf-8",
        )

        body = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "_ct2_trace_hygiene.py",
                "pr-body",
                "--ticket",
                ticket,
                "--ct2-dir",
                project / ".ct2",
                "--ticket-file",
                ticket.name,
            ]
        )

        self.assertEqual(body.returncode, 0, body.stderr)
        self.assertNotIn("Closes #142", body.stdout)

    def test_closes_line_removed_when_issue_unset(self):
        project = self.make_git_project()
        ticket = project / ".ct2" / "in-progress" / "001-parse-nested-config.md"
        write_ticket(ticket)

        body = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "_ct2_trace_hygiene.py",
                "pr-body",
                "--ticket",
                ticket,
                "--ct2-dir",
                project / ".ct2",
                "--ticket-file",
                ticket.name,
            ]
        )

        self.assertEqual(body.returncode, 0, body.stderr)
        self.assertNotIn("Closes #", body.stdout)

    def test_pr_body_ticket_link_none_omits_hidden_mapping(self):
        project = self.make_git_project()
        cfg = project / ".ct2" / "config" / "harness.yaml"
        cfg.write_text(
            cfg.read_text(encoding="utf-8").replace(
                "pr_body_ticket_link: hidden-html",
                "pr_body_ticket_link: none",
            ),
            encoding="utf-8",
        )
        ticket = project / ".ct2" / "in-progress" / "001-parse-nested-config.md"
        write_ticket(ticket)

        body = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "_ct2_trace_hygiene.py",
                "pr-body",
                "--ticket",
                ticket,
                "--ct2-dir",
                project / ".ct2",
                "--ticket-file",
                ticket.name,
            ]
        )

        self.assertEqual(body.returncode, 0, body.stderr)
        self.assertNotIn("ct2-ticket:", body.stdout)

    def test_missing_trace_config_uses_legacy_pr_body(self):
        project = self.make_git_project()
        self.strip_trace_hygiene(project)
        ticket = project / ".ct2" / "in-progress" / "001-parse-nested-config.md"
        write_ticket(ticket)

        body = run_cmd(
            [
                PYTHON,
                REPO_ROOT / "bin" / "_ct2_trace_hygiene.py",
                "pr-body",
                "--ticket",
                ticket,
                "--ct2-dir",
                project / ".ct2",
                "--ticket-file",
                ticket.name,
            ]
        )

        self.assertEqual(body.returncode, 0, body.stderr)
        self.assertIn("Ticket: `.ct2/in-review/001-parse-nested-config.md`", body.stdout)
        self.assertIn("Opened by ct2-forge via ct2-git-submit.", body.stdout)

    def test_git_start_derives_clean_branch_and_records_it(self):
        project = self.make_git_project()
        ticket = project / ".ct2" / "in-progress" / "001-parse-nested-config.md"
        write_ticket(ticket)

        start = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-git-start", "001"], cwd=project)

        self.assertEqual(start.returncode, 0, start.stderr)
        self.assertIn("feat/parse-nested-config", start.stdout)
        branch = run_cmd(["git", "branch", "--show-current"], cwd=project)
        self.assertEqual("feat/parse-nested-config", branch.stdout.strip())
        self.assertIn("branch: feat/parse-nested-config", ticket.read_text(encoding="utf-8"))

    def test_git_start_legacy_without_trace_block_keeps_ticket_stem(self):
        project = self.make_git_project()
        self.strip_trace_hygiene(project)
        ticket = project / ".ct2" / "in-progress" / "001-parse-nested-config.md"
        write_ticket(ticket)

        start = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-git-start", "001"], cwd=project)

        self.assertEqual(start.returncode, 0, start.stderr)
        self.assertIn("feat/001-parse-nested-config", start.stdout)
        branch = run_cmd(["git", "branch", "--show-current"], cwd=project)
        self.assertEqual("feat/001-parse-nested-config", branch.stdout.strip())

    def test_git_start_appends_collision_suffix_for_clean_branch(self):
        project = self.make_git_project()
        self.assertEqual(run_cmd(["git", "branch", "feat/parse-nested-config"], cwd=project).returncode, 0)
        ticket = project / ".ct2" / "in-progress" / "001-parse-nested-config.md"
        write_ticket(ticket)

        start = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-git-start", "001"], cwd=project)

        self.assertEqual(start.returncode, 0, start.stderr)
        self.assertIn("feat/parse-nested-config-2", start.stdout)
        self.assertNotRegex(start.stdout, r"feat/001-")

    def test_git_start_truncates_long_clean_branch_slug(self):
        project = self.make_git_project()
        long_title = "feat: " + "very long branch segment " * 12
        ticket = project / ".ct2" / "in-progress" / "001-parse-nested-config.md"
        write_ticket(ticket, title=long_title)

        start = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-git-start", "001"], cwd=project)

        self.assertEqual(start.returncode, 0, start.stderr)
        branch = run_cmd(["git", "branch", "--show-current"], cwd=project).stdout.strip()
        self.assertLessEqual(len(branch.split("/", 1)[1]), 60)

    def test_git_submit_treats_branch_null_as_unset(self):
        project = self.make_git_project()
        ticket = project / ".ct2" / "in-progress" / "001-parse-nested-config.md"
        write_ticket(ticket, branch="null")

        submit = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-git-submit", "001"], cwd=project)

        self.assertEqual(submit.returncode, 0)
        self.assertIn("expected branch feat/parse-nested-config", submit.stderr)
        self.assertNotIn("expected branch null", submit.stderr)

    def test_git_helpers_do_not_use_non_atomic_ticket_overwrite_or_repeated_ls_remote(self):
        start = (REPO_ROOT / "bin" / "ct2-git-start").read_text(encoding="utf-8")
        submit = (REPO_ROOT / "bin" / "ct2-git-submit").read_text(encoding="utf-8")
        self.assertNotIn("git ls-remote --exit-code --heads origin", start)
        self.assertNotIn("open(path, 'w').write", start)
        self.assertNotIn("open(path, 'w').write", submit)
        self.assertIn("os.replace(tmp, path)", start)
        self.assertIn("os.replace(tmp, path)", submit)

    def test_trace_hygiene_config_json_reports_clean_preset(self):
        project = self.make_git_project()
        proc = run_cmd(
            [PYTHON, REPO_ROOT / "bin" / "_ct2_trace_hygiene.py", "config", "--ct2-dir", project / ".ct2"]
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        config = json.loads(proc.stdout)
        self.assertEqual("clean", config["preset"])
        self.assertEqual("title-slug", config["branch_naming"])

    def test_protocol_surface_parent_default_matches_clean_template(self):
        surface = (REPO_ROOT / "spec" / "protocol-surface.yaml").read_text(encoding="utf-8")
        self.assertIn("id: config.harness.trace_hygiene", surface)
        self.assertIn("default: {preset: clean}", surface)

    def test_trace_hygiene_migrate_switches_presets(self):
        project = self.make_git_project()
        self.strip_trace_hygiene(project)

        clean = run_cmd(
            [PYTHON, REPO_ROOT / "bin" / "ct2-trace-hygiene-migrate", "--json", "--preset", "clean", project]
        )
        self.assertEqual(clean.returncode, 0, clean.stderr)
        cfg = json.loads(
            run_cmd(
                [PYTHON, REPO_ROOT / "bin" / "_ct2_trace_hygiene.py", "config", "--ct2-dir", project / ".ct2"]
            ).stdout
        )
        self.assertEqual("clean", cfg["preset"])

        legacy = run_cmd(
            [PYTHON, REPO_ROOT / "bin" / "ct2-trace-hygiene-migrate", "--json", "--preset", "legacy-branded", project]
        )
        self.assertEqual(legacy.returncode, 0, legacy.stderr)
        cfg = json.loads(
            run_cmd(
                [PYTHON, REPO_ROOT / "bin" / "_ct2_trace_hygiene.py", "config", "--ct2-dir", project / ".ct2"]
            ).stdout
        )
        self.assertEqual("legacy-branded", cfg["preset"])


if __name__ == "__main__":
    unittest.main()
