#!/usr/bin/env python3
"""Shared adapter dispatcher for CT2 lens roles."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_agent(role: str) -> str:
    return "claude" if role == "lens-cc" else "codex"


def command_for(agent: str, adapter_text: str) -> tuple[list[str], str | None]:
    if agent == "claude":
        cmd = os.environ.get("CT2_CLAUDE_CMD", "claude")
        return [cmd, "-p", adapter_text], None
    if agent == "codex":
        cmd = os.environ.get("CT2_CODEX_CMD", "codex")
        return [cmd, "exec", "--sandbox", "workspace-write", "-"], adapter_text
    raise SystemExit(f"ct2-lens: unsupported agent '{agent}'")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dispatch CT2 lens role through an adapter")
    parser.add_argument("role", choices=("lens-cc", "lens-cx"))
    parser.add_argument("project_dir", nargs="?", default=".")
    parser.add_argument("--agent")
    parser.add_argument("--adapter")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--print-objective", action="store_true")
    args, rest = parser.parse_known_args(argv)
    if rest:
        if len(rest) == 1 and args.project_dir == ".":
            args.project_dir = rest[0]
        else:
            parser.error(f"unrecognized arguments: {' '.join(rest)}")

    project_dir = Path(args.project_dir).resolve()
    if not (project_dir / ".ct2").is_dir():
        print(f"ct2-lens: .ct2/ not found in {project_dir}", file=sys.stderr)
        return 1

    agent = args.agent or default_agent(args.role)
    adapter = Path(args.adapter) if args.adapter else repo_root() / "adapters" / agent / f"{args.role}.md"
    if not adapter.is_file():
        print(f"ct2-lens: adapter not found: {adapter}", file=sys.stderr)
        return 1
    adapter_text = adapter.read_text(encoding="utf-8")

    if args.print_objective:
        print(adapter_text)
        return 0

    command, stdin_text = command_for(agent, adapter_text)
    if args.dry_run or os.environ.get("CT2_LENS_DRY_RUN") == "1":
        print(
            json.dumps(
                {
                    "agent": agent,
                    "role": args.role,
                    "adapter": str(adapter),
                    "project_dir": str(project_dir),
                    "command": command,
                    "stdin": stdin_text is not None,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if shutil.which(command[0]) is None and "/" not in command[0]:
        print(f"ct2-lens: command not found: {command[0]}", file=sys.stderr)
        return 1
    proc = subprocess.run(command, cwd=str(project_dir), input=stdin_text, text=True, check=False)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
