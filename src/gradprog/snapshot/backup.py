"""Incremental backup of data/snapshots (07 §10.2)."""

import shutil
from pathlib import Path

APPEND_ONLY = {"index.csv", "runs.csv"}
REGENERABLE_DIRS = {"reports", "logs"}
REGENERABLE_FILES = {"manual_due.md"}


class BackupError(RuntimeError):
    """The destination holds a file that must not be overwritten."""


def _kind(rel):
    if rel.as_posix() in APPEND_ONLY:
        return "append"
    if rel.as_posix() in REGENERABLE_FILES or rel.parts[0] in REGENERABLE_DIRS:
        return "regenerable"
    return "immutable"


def backup(src, dest):
    if not dest:
        raise BackupError("a backup destination (--dest) is required")
    src, dest = Path(src), Path(dest)
    counts = {"copied": 0, "skipped": 0, "overwritten": 0}
    plan = []
    for f in sorted(p for p in src.rglob("*") if p.is_file()):
        rel = f.relative_to(src)
        target = dest / rel
        if not target.exists():
            plan.append(("copy", f, target))
            continue
        a, b = f.read_bytes(), target.read_bytes()
        if a == b:
            counts["skipped"] += 1
            continue
        kind = _kind(rel)
        if kind == "append" and a.startswith(b):
            plan.append(("overwrite", f, target))
        elif kind == "regenerable":
            plan.append(("overwrite", f, target))
        else:
            raise BackupError(f"{rel} differs at the destination and must not be overwritten")
    for action, f, target in plan:       # nothing is written unless every file passed the checks
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
        counts["copied" if action == "copy" else "overwritten"] += 1
    return counts
