#!/usr/bin/env python3
"""Common helpers for CT2 protocol migrations."""

from __future__ import annotations

import os
import re
import shutil
import tarfile
import tempfile
import uuid
from pathlib import Path

from _ct2_protocol import parse_protocol, read_project_protocol
from _ct2_sealed_baseline import sealed_snapshot_name, write_snapshot
from _ct2_vao import atomic_write_text, compact_now, now
from _ct2_version import repo_root_from_file


TICKET_STATES = ("draft", "backlog", "in-progress", "in-review", "rejected", "escalated", "done")
SEALED_BASELINE_STATES = ("backlog", "in-progress", "in-review", "rejected", "escalated", "done")


def ensure_project(project_dir: Path) -> Path:
    ct2_dir = project_dir / ".ct2"
    if not ct2_dir.is_dir():
        raise RuntimeError(f".ct2/ not found in {project_dir}")
    (ct2_dir / ".tmp").mkdir(parents=True, exist_ok=True)
    (ct2_dir / ".migrations").mkdir(parents=True, exist_ok=True)
    return ct2_dir


def migration_stem(from_version: str, to_version: str) -> str:
    return f"{compact_now()}-{from_version}-to-{to_version}"


def backup(ct2_dir: Path, from_version: str, to_version: str, stem: str) -> Path:
    dest = ct2_dir / ".migrations" / f"{stem}.tar.gz"
    tmp_dir = ct2_dir / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="migration-backup-", suffix=".tar.gz", dir=str(tmp_dir))
    os.close(fd)
    try:
        with tarfile.open(tmp_name, "w:gz") as archive:
            for path in sorted(ct2_dir.rglob("*")):
                rel = path.relative_to(ct2_dir)
                if rel.parts and rel.parts[0] in {".tmp", ".migrations"}:
                    continue
                archive.add(path, arcname=Path(".ct2") / rel)
        os.replace(tmp_name, dest)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return dest


def stamp(ct2_dir: Path, version: str) -> None:
    atomic_write_text(ct2_dir, ct2_dir / ".protocol-version", version + "\n", "protocol-version-")


def set_field_if_missing(text: str, key: str, value: str, after_key: str = "review-round") -> str:
    if re.search(rf"^{re.escape(key)}:", text, re.MULTILINE):
        return text
    pattern = rf"^({re.escape(after_key)}:.*\r?\n)"
    if re.search(pattern, text, re.MULTILINE):
        return re.sub(pattern, rf"\g<1>{key}: {value}\n", text, count=1, flags=re.MULTILINE)
    delimiter = re.search(r"^(---\r?\n)", text, re.MULTILINE)
    if delimiter:
        return text[: delimiter.end()] + f"{key}: {value}\n" + text[delimiter.end() :]
    raise ValueError(
        f"ticket missing both {after_key!r} anchor and opening '---' delimiter; "
        f"cannot inject {key!r}"
    )


def backfill_sealed_baselines(ct2_dir: Path) -> list[str]:
    changed: list[str] = []
    reviews_dir = ct2_dir / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = ct2_dir / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    for state in SEALED_BASELINE_STATES:
        for ticket in sorted((ct2_dir / state).glob("*.md")):
            snapshot = reviews_dir / sealed_snapshot_name(ticket)
            if snapshot.exists():
                continue
            tmp = tmp_dir / f"migration-sealed-{ticket.stem}-{uuid.uuid4().hex[:8]}.md"
            write_snapshot(ticket, tmp)
            try:
                os.link(tmp, snapshot)
            except FileExistsError:
                pass
            except OSError:
                shutil.copy2(tmp, snapshot)
            finally:
                try:
                    tmp.unlink()
                except OSError:
                    pass
            if snapshot.exists():
                changed.append(str(snapshot.relative_to(ct2_dir.parent)))
    return changed


def migrate_0_1_to_0_2(ct2_dir: Path) -> list[str]:
    changed: list[str] = []
    for state in TICKET_STATES:
        for ticket in sorted((ct2_dir / state).glob("*.md")):
            text = ticket.read_text(encoding="utf-8")
            updated = set_field_if_missing(text, "duration-bounce-count", "0")
            updated = set_field_if_missing(updated, "total-attempts", "0", after_key="duration-bounce-count")
            if updated != text:
                atomic_write_text(ct2_dir, ticket, updated, "migrate-ticket-")
                changed.append(str(ticket.relative_to(ct2_dir.parent)))
    changed.extend(backfill_sealed_baselines(ct2_dir))
    return changed


def migrate_0_3_to_0_4(ct2_dir: Path) -> list[str]:
    """Provision the 0.4 ledger surface: the lessons and goals directories
    (loop-design Direction C/D) and the advisory planning-lints config.

    Purely additive and idempotent — it creates only what a fresh 0.4
    ``ct2-init`` would create and never rewrites existing project state, so an
    already-customized ``planning-lints.json`` is preserved untouched.
    """
    changed: list[str] = []
    for name in ("lessons", "goals"):
        target = ct2_dir / name
        if target.exists() and not target.is_dir():
            raise RuntimeError(
                f"{target} exists but is not a directory; move or remove it before "
                "migrating (existing project data is left untouched)."
            )
        if not target.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            changed.append(str(target.relative_to(ct2_dir.parent)))
    lints_dst = ct2_dir / "config" / "planning-lints.json"
    if not lints_dst.exists():
        lints_src = repo_root_from_file(__file__) / "config" / "planning-lints.json"
        if lints_src.is_file():
            lints_dst.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(
                ct2_dir,
                lints_dst,
                lints_src.read_text(encoding="utf-8"),
                "planning-lints-",
            )
            changed.append(str(lints_dst.relative_to(ct2_dir.parent)))
    return changed


def migrate_noop(ct2_dir: Path) -> list[str]:
    return []


def run_migration(project_dir: Path, from_version: str, to_version: str, dry_run: bool = False) -> dict[str, object]:
    parse_protocol(from_version)
    parse_protocol(to_version)
    ct2_dir = ensure_project(project_dir)
    observed, missing = read_project_protocol(ct2_dir)
    if parse_protocol(observed) >= parse_protocol(to_version):
        return {"state": "already-current", "observed": observed, "changed": []}
    if observed != from_version:
        raise RuntimeError(f"expected protocol {from_version}, found {observed}")
    if dry_run:
        return {"state": "dry-run", "observed": observed, "target": to_version, "changed": []}
    stem = migration_stem(from_version, to_version)
    backup_path = backup(ct2_dir, from_version, to_version, stem)
    if from_version == "0.1" and to_version == "0.2":
        changed = migrate_0_1_to_0_2(ct2_dir)
    elif from_version == "0.3" and to_version == "0.4":
        changed = migrate_0_3_to_0_4(ct2_dir)
    else:
        changed = migrate_noop(ct2_dir)
    log = ct2_dir / ".migrations" / f"{stem}.log"
    lines = [
        f"timestamp: {now()}",
        f"from: {from_version}",
        f"to: {to_version}",
        f"backup: {backup_path.relative_to(ct2_dir.parent)}",
        f"changed: {len(changed)}",
    ]
    atomic_write_text(ct2_dir, log, "\n".join(lines) + "\n", "migration-log-")
    stamp(ct2_dir, to_version)
    return {"state": "migrated", "observed": observed, "target": to_version, "backup": str(backup_path), "changed": changed}
