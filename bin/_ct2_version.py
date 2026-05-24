#!/usr/bin/env python3
"""Shared CT2 version helpers."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "SemVer":
        match = SEMVER_RE.fullmatch(value.strip())
        if not match:
            raise ValueError(f"invalid SemVer: {value!r}")
        return cls(*(int(part) for part in match.groups()))

    def bump(self, level: str) -> "SemVer":
        if level == "major":
            return SemVer(self.major + 1, 0, 0)
        if level == "minor":
            return SemVer(self.major, self.minor + 1, 0)
        if level == "patch":
            return SemVer(self.major, self.minor, self.patch + 1)
        raise ValueError(f"unknown bump level: {level}")

    @property
    def protocol(self) -> str:
        return f"{self.major}.{self.minor}"

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def repo_root_from_file(file_path: str | Path) -> Path:
    path = Path(file_path).resolve()
    for candidate in (path.parent, *path.parents):
        if (candidate / "VERSION").is_file() and (candidate / "bin").is_dir():
            return candidate
    return path.parent


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def read_version(repo: Path) -> SemVer:
    return SemVer.parse((repo / "VERSION").read_text(encoding="utf-8").strip())


def plugin_manifest_paths(repo: Path) -> tuple[Path, Path]:
    return (
        repo / "claude-plugin" / ".claude-plugin" / "plugin.json",
        repo / "codex-plugin" / ".codex-plugin" / "plugin.json",
    )


def read_plugin_version(path: Path) -> str:
    return str(json.loads(path.read_text(encoding="utf-8")).get("version", ""))


def sync_plugin_manifest(path: Path, version: SemVer) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    old = data.get("version")
    data["version"] = str(version)
    if data.get("version") == old:
        return False
    atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=True) + "\n")
    return True


def sync_install_hint(repo: Path, version: SemVer) -> bool:
    path = repo / "install.sh"
    text = path.read_text(encoding="utf-8")
    pattern = r'^(CT2_INSTALL_VERSION=")[^"]+(")$'
    if re.search(pattern, text, flags=re.MULTILINE):
        updated = re.sub(
            pattern,
            rf"\g<1>{version}\2",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        updated = text.replace(
            'CT2_HOME="${HOME}/.ct2"\n',
            f'CT2_HOME="${{HOME}}/.ct2"\nCT2_INSTALL_VERSION="{version}"\n',
            1,
        )
    if updated == text:
        return False
    atomic_write_text(path, updated)
    return True


def sync_derived_artifacts(repo: Path) -> list[Path]:
    version = read_version(repo)
    changed: list[Path] = []
    for path in plugin_manifest_paths(repo):
        if sync_plugin_manifest(path, version):
            changed.append(path)
    if sync_install_hint(repo, version):
        changed.append(repo / "install.sh")
    return changed


def git_short_sha(repo: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10,
        )
    except Exception:
        return "unknown"
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else "unknown"
