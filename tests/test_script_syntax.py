import json
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class ScriptSyntaxTest(unittest.TestCase):
    def test_bash_shebang_scripts_parse(self):
        candidates = [REPO_ROOT / "install.sh"]
        candidates.extend((REPO_ROOT / "bin").iterdir())
        candidates.extend((REPO_ROOT / "claude-plugin" / "hooks").glob("*.sh"))
        for path in sorted(p for p in candidates if p.is_file()):
            first = path.read_text(encoding="utf-8", errors="ignore").splitlines()[:1]
            if path.suffix == ".sh" or (first and "bash" in first[0]):
                with self.subTest(path=path.relative_to(REPO_ROOT)):
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

    def test_python_shebang_scripts_compile_without_pycache(self):
        for path in sorted((REPO_ROOT / "bin").iterdir()):
            if not path.is_file():
                continue
            first = path.read_text(encoding="utf-8", errors="ignore").splitlines()[:1]
            if first and "python" in first[0]:
                with self.subTest(path=path.relative_to(REPO_ROOT)):
                    compile(path.read_text(encoding="utf-8"), str(path), "exec")

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
