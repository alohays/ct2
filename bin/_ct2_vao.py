#!/usr/bin/env python3
"""Shared helpers for CT2 Verified Autonomy OS commands."""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
import uuid
import fcntl
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATE_DIRS = ("draft", "backlog", "in-progress", "in-review", "rejected", "escalated", "done")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compact_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def new_id(prefix: str) -> str:
    return f"{prefix}-{compact_now()}-{uuid.uuid4().hex[:8]}"


def ensure_ct2(project_dir: Path) -> Path:
    ct2_dir = project_dir / ".ct2"
    if not ct2_dir.is_dir():
        raise SystemExit(f"ct2: .ct2/ not found in {project_dir}. Run ct2-init first.")
    for rel in (
        ".tmp",
        "runtime",
        "runtime/artifacts",
        "telemetry",
        "evidence",
        "evidence/commands",
        "evidence/artifacts",
        "evidence/screenshots",
        "evidence/verifiers",
        "evidence/hooks",
        "decisions/pending",
        "decisions/answered",
        "decisions/expired",
        "decisions/audit",
        "plans",
        "plans/canvas/open",
        "plans/canvas/answered",
        "plans/canvas/sealed",
        "plans/canvas/expired",
        "watchers",
        "postmortems",
        "evals",
        "evals/ct2-helm",
        "evals/ct2-forge",
        "evals/ct2-lens-cc",
        "evals/ct2-lens-cx",
    ):
        (ct2_dir / rel).mkdir(parents=True, exist_ok=True)
    return ct2_dir


def atomic_write_text(ct2_dir: Path, dest: Path, text: str, prefix: str = "ct2-write-") -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = ct2_dir / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=prefix, dir=str(tmp_dir))
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp_name, dest)


def atomic_write_json(ct2_dir: Path, dest: Path, data: dict[str, Any], prefix: str = "ct2-json-") -> None:
    atomic_write_text(ct2_dir, dest, json.dumps(data, indent=2, sort_keys=True) + "\n", prefix)


def append_jsonl(ct2_dir: Path, dest: Path, row: dict[str, Any]) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, sort_keys=True) + "\n"
    with dest.open("a+", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            if size:
                fh.seek(size - 1)
                if fh.read(1) != "\n":
                    fh.write("\n")
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"_invalid": line})
    return rows


FANOUT_NUMERIC_FIELDS = ("fanout_width", "agent_count", "wall_ms", "agent_ms_total")


def _is_fanout_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def read_fanout_records(ct2_dir: Path) -> list[dict[str, Any]]:
    """Load advisory fan-out records (spec/balanced-scorecard.md). Advisory only."""
    records: list[dict[str, Any]] = []
    fanout_dir = ct2_dir / "runtime" / "fanout"
    if not fanout_dir.is_dir():
        return records
    for path in sorted(fanout_dir.glob("fanout-*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        if "fanout_width" not in data and "agent_count" not in data:
            continue
        if any(field in data and not _is_fanout_number(data[field]) for field in FANOUT_NUMERIC_FIELDS):
            continue
        records.append(data)
    return records


def read_frontmatter(path: Path) -> dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    fm: dict[str, Any] = {}
    current_list: str | None = None
    for raw in match.group(1).splitlines():
        if current_list and re.match(r"^\s+-\s+", raw):
            fm.setdefault(current_list, []).append(re.sub(r"^\s+-\s+", "", raw).strip())
            continue
        kv = re.match(r"^(\w[\w-]*):\s*(.*)$", raw)
        if not kv:
            continue
        key, val = kv.group(1), kv.group(2).strip()
        val = re.sub(r"\s+#.*$", "", val).strip()
        if val == "":
            current_list = key
            fm[key] = []
        else:
            current_list = None
            fm[key] = val.strip('"')
    return fm


def ticket_id_from_name(path: Path) -> str:
    match = re.match(r"^(\d+)", path.stem)
    return match.group(1) if match else path.stem


def relative_to_project(project_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project_dir))
    except ValueError:
        return str(path)
