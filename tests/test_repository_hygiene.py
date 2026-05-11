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
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

        self.assertNotIn(".ct2/", [line.strip() for line in gitignore])

    def test_ct2_init_excludes_runtime_state_via_git_info_exclude(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)

        init_git = run_cmd(["git", "init"], cwd=project)
        self.assertEqual(init_git.returncode, 0, init_git.stderr)

        init_ct2 = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project], cwd=REPO_ROOT)
        self.assertEqual(init_ct2.returncode, 0, init_ct2.stderr)

        exclude = (project / ".git" / "info" / "exclude").read_text(encoding="utf-8").splitlines()
        self.assertIn(".ct2/", [line.strip() for line in exclude])
        self.assertFalse((project / ".gitignore").exists())


if __name__ == "__main__":
    unittest.main()
