import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def rel(path: Path, repo: Path) -> str:
    return path.relative_to(repo).as_posix()


def shebang_line(path: Path) -> str:
    head = path.read_text(encoding="utf-8", errors="ignore")[:200]
    if not head.startswith("#!"):
        return ""
    return head.split("\n", 1)[0]


def python_check_files(repo: Path) -> list[Path]:
    files = []
    for path in sorted((repo / "bin").iterdir()):
        if not path.is_file():
            continue
        if path.suffix == ".py" or "python" in shebang_line(path):
            files.append(path)
    return files


def bash_check_files(repo: Path) -> list[Path]:
    candidates = [repo / "install.sh"]
    candidates.extend((repo / "bin").iterdir())
    candidates.extend((repo / "claude-plugin" / "hooks").glob("*.sh"))

    files = []
    for path in sorted(candidates):
        if not path.is_file():
            continue
        if path.suffix == ".sh" or "bash" in shebang_line(path):
            files.append(path)
    return files


class ScriptSyntaxTest(unittest.TestCase):
    def test_bash_entrypoints_parse(self):
        for path in bash_check_files(REPO_ROOT):
            with self.subTest(path=rel(path, REPO_ROOT)):
                proc = subprocess.run(
                    ["bash", "-n", str(path)],
                    cwd=str(REPO_ROOT),
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=30,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_python_helpers_compile_without_pycache(self):
        for path in python_check_files(REPO_ROOT):
            with self.subTest(path=rel(path, REPO_ROOT)):
                compile(path.read_text(encoding="utf-8"), str(path), "exec")

    def test_script_discovery_uses_strict_shebangs_and_py_suffixes(self):
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

        self.assertEqual(
            ["bin/cli", "bin/helper.py"],
            [rel(path, project) for path in python_check_files(project)],
        )
        self.assertEqual(
            ["bin/shell", "claude-plugin/hooks/hook.sh", "install.sh"],
            [rel(path, project) for path in bash_check_files(project)],
        )

    def test_json_metadata_parses(self):
        for path in (
            REPO_ROOT / "claude-plugin" / "hooks" / "hooks.json",
            REPO_ROOT / "codex-plugin" / ".codex-plugin" / "plugin.json",
            REPO_ROOT / "claude-plugin" / ".claude-plugin" / "plugin.json",
            REPO_ROOT / ".agents" / "plugins" / "marketplace.json",
        ):
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                with path.open(encoding="utf-8") as fh:
                    json.load(fh)


if __name__ == "__main__":
    unittest.main()
