#!/usr/bin/env python3
"""CT2 protocol compatibility checks."""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from _ct2_version import read_version, repo_root_from_file


PROTOCOL_FILE = ".protocol-version"


@dataclass(frozen=True)
class ProtocolStatus:
    project_protocol: str
    current_protocol: str
    compatible: bool
    action: str
    message: str
    marker_missing: bool = False


def parse_protocol(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)", value.strip())
    if not match:
        raise ValueError(f"invalid protocol version: {value!r}")
    return int(match.group(1)), int(match.group(2))


def current_protocol(repo: Path | None = None) -> str:
    override = os.environ.get("CT2_PROTOCOL_CURRENT")
    if override:
        parse_protocol(override)
        return override
    root = repo or repo_root_from_file(__file__)
    return read_version(root).protocol


def read_project_protocol(ct2_dir: Path) -> tuple[str, bool]:
    path = ct2_dir / PROTOCOL_FILE
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.1", True
    except UnicodeError as exc:
        raise RuntimeError(f"{path} cannot be read as UTF-8; rewrite or remove the file and re-run ct2-protocol assert") from exc
    try:
        parse_protocol(value)
    except ValueError as exc:
        raise RuntimeError(
            f"{path} contains an invalid protocol version ({value!r}); "
            "rewrite or remove the file and re-run ct2-protocol assert"
        ) from exc
    return value, False


def migration_hops(project_protocol: str, current: str) -> list[tuple[str, str]]:
    start = parse_protocol(project_protocol)
    target = parse_protocol(current)
    if start >= target:
        return []
    hops: list[tuple[str, str]] = []
    major, minor = start
    while (major, minor) < target:
        if major < target[0]:
            next_version = (major + 1, 0)
        else:
            next_version = (major, minor + 1)
        hops.append((f"{major}.{minor}", f"{next_version[0]}.{next_version[1]}"))
        major, minor = next_version
    return hops


def migration_command(project_protocol: str, current: str) -> str:
    hops = migration_hops(project_protocol, current)
    if not hops:
        return f"ct2-migrate-{project_protocol}-{current}"
    return " && ".join(f"ct2-migrate-{source}-{target}" for source, target in hops)


def status(project_dir: Path, repo: Path | None = None) -> ProtocolStatus:
    ct2_dir = project_dir / ".ct2"
    if not ct2_dir.is_dir():
        raise RuntimeError(f".ct2/ not found in {project_dir}. Run ct2-init first.")
    current = current_protocol(repo)
    project, missing = read_project_protocol(ct2_dir)
    project_tuple = parse_protocol(project)
    current_tuple = parse_protocol(current)
    if project_tuple == current_tuple:
        return ProtocolStatus(project, current, True, "proceed", "protocol compatible", missing)
    if project_tuple < current_tuple:
        cmd = migration_command(project, current)
        return ProtocolStatus(
            project,
            current,
            False,
            "migrate",
            f".ct2/ protocol {project} detected, CT2 expects {current}; run {cmd}",
            missing,
        )
    return ProtocolStatus(
        project,
        current,
        False,
        "upgrade-install",
        f".ct2/ protocol {project} is newer than this CT2 install ({current}); upgrade CT2 first",
        missing,
    )


def assert_compatible(project_dir: Path, repo: Path | None = None) -> None:
    result = status(project_dir, repo)
    if not result.compatible:
        raise RuntimeError(result.message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check CT2 protocol compatibility")
    parser.add_argument("command", choices=("status", "assert"))
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--repo", default=repo_root_from_file(__file__), type=Path)
    args = parser.parse_args()
    project_dir = Path(args.project_dir).resolve()
    try:
        result = status(project_dir, args.repo.resolve())
    except Exception as exc:
        print(f"ct2-protocol: error: {exc}", file=sys.stderr)
        return 1
    if args.command == "status":
        print(f"project: {result.project_protocol}")
        print(f"current: {result.current_protocol}")
        print(f"status: {'compatible' if result.compatible else result.action}")
        print(f"message: {result.message}")
        return 0 if result.compatible else 2
    if not result.compatible:
        print(f"ct2-protocol: {result.message}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
