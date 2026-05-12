import re
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


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


class RepositoryHygieneTest(unittest.TestCase):
    def test_tracked_gitignore_does_not_hide_ct2_runtime_state(self):
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

        for line in gitignore.splitlines():
            stripped = line.split("#", 1)[0].strip()
            self.assertFalse(
                re.fullmatch(r"(/?\*\*/)?/?\.ct2(/.*)?", stripped),
                f"`.ct2` family pattern leaked back into .gitignore: {stripped!r}",
            )

    def test_ct2_init_excludes_runtime_state_via_git_info_exclude(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)

        init_git = run_cmd(["git", "init"], cwd=project)
        self.assertEqual(init_git.returncode, 0, init_git.stderr)

        # Run from REPO_ROOT so ct2-init reads repository templates while initializing the scratch target.
        init_ct2 = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project], cwd=REPO_ROOT)
        self.assertEqual(init_ct2.returncode, 0, init_ct2.stderr)
        repair_ct2 = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", "--repair", project], cwd=REPO_ROOT)
        self.assertEqual(repair_ct2.returncode, 0, repair_ct2.stderr)

        exclude = (project / ".git" / "info" / "exclude").read_text(encoding="utf-8").splitlines()
        self.assertEqual(1, [line.strip() for line in exclude].count(".ct2/"))
        self.assertFalse((project / ".gitignore").exists())

    def test_ct2_init_excludes_runtime_state_in_linked_worktree_common_dir(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name) / "repo"
        worktree = Path(tmp.name) / "worktree"
        project.mkdir()

        self.assertEqual(run_cmd(["git", "init"], cwd=project).returncode, 0)
        self.assertEqual(
            run_cmd(
                ["git", "-c", "user.name=CT2 Test", "-c", "user.email=ct2@example.invalid", "commit", "--allow-empty", "-m", "init"],
                cwd=project,
            ).returncode,
            0,
        )
        add_worktree = run_cmd(["git", "worktree", "add", "-b", "feat/test", worktree], cwd=project)
        self.assertEqual(add_worktree.returncode, 0, add_worktree.stderr)

        # Run from REPO_ROOT so ct2-init reads repository templates while initializing the scratch target.
        init_ct2 = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", worktree], cwd=REPO_ROOT)
        self.assertEqual(init_ct2.returncode, 0, init_ct2.stderr)

        common = run_cmd(["git", "rev-parse", "--git-common-dir"], cwd=worktree)
        self.assertEqual(common.returncode, 0, common.stderr)
        common_dir = Path(common.stdout.strip())
        if not common_dir.is_absolute():
            common_dir = worktree / common_dir
        exclude = (common_dir / "info" / "exclude").read_text(encoding="utf-8").splitlines()
        self.assertIn(".ct2/", [line.strip() for line in exclude])

    def test_ct2_init_warns_without_git_and_does_not_create_gitignore(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)

        # Run from REPO_ROOT so ct2-init reads repository templates while initializing the scratch target.
        init_ct2 = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project], cwd=REPO_ROOT)
        self.assertEqual(init_ct2.returncode, 0, init_ct2.stderr)
        self.assertIn("not a git repository", init_ct2.stderr)
        self.assertFalse((project / ".gitignore").exists())


if __name__ == "__main__":
    unittest.main()
