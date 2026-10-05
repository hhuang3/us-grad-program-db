"""Snapshot storage layout, index.csv and runs.csv (07 §4)."""

import csv
from pathlib import Path

import pandas as pd

from gradprog.util.manifest import validate_timestamp

CLASSES = ["first_capture", "unchanged", "changed", "suspected_redesign", "unavailable", "blocked", "fetch_error"]
SUCCESS = ("first_capture", "unchanged", "changed", "suspected_redesign")
ANOMALIES = ("suspected_redesign", "unavailable", "blocked", "fetch_error")
METHODS = ("auto", "manual")
RUN_METHODS = ("auto", "manual", "renormalize")
CONTENT_TYPES = ("html", "pdf", "mhtml")
INDEX_COLUMNS = [
    "snapshot_id", "page_id", "run_id", "method", "retrieved_at", "requested_url", "final_url", "http_status",
    "content_type", "raw_sha256", "raw_bytes", "normalizer_version", "norm_sha256", "norm_chars",
    "classification", "prev_snapshot_id", "added_lines", "removed_lines", "note",
]
RUNS_COLUMNS = ["run_id", "method", "started_at", "finished_at", *CLASSES, "anomaly_page_ids"]


class SnapshotError(ValueError):
    """A snapshot operation violates a documented rule."""


def _compact(ts):
    validate_timestamp(ts)
    return ts.replace("-", "").replace(":", "")


def make_snapshot_id(retrieved_at, page_id):
    return f"snap-{_compact(retrieved_at)}-{page_id}"


def make_run_id(started_at, method):
    if method not in RUN_METHODS:
        raise ValueError(f"run method must be one of {RUN_METHODS}, got {method!r}")
    return f"run-{_compact(started_at)}-{method}"


def _read(path, columns):
    if not path.exists():
        return pd.DataFrame(columns=columns, dtype=str)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _check_header(path, columns):
    if path.exists():
        with open(path, encoding="utf-8", newline="") as f:
            header = next(csv.reader(f), [])
        if header != columns:
            raise SnapshotError(f"{path.name}: unexpected header {header}; expected {columns}")


def _append(path, columns, row):
    if set(row) != set(columns):
        raise SnapshotError(f"{path.name}: row keys must be {columns}, got {sorted(row)}")
    _check_header(path, columns)
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:   # append only: existing lines are never rewritten
        w = csv.writer(f, lineterminator="\n")
        if new:
            w.writerow(columns)
        w.writerow(["" if row[c] is None else str(row[c]) for c in columns])


class SnapshotStore:
    def __init__(self, root):
        self.root = Path(root)
        self.index_path = self.root / "index.csv"
        self.runs_path = self.root / "runs.csv"

    def raw_path(self, page_id, snapshot_id, ext):
        return self.root / "raw" / page_id / f"{snapshot_id}.{ext}"

    def norm_path(self, page_id, snapshot_id, version):
        return self.root / "normalized" / page_id / f"{snapshot_id}.v{int(version)}.txt"

    def diff_path(self, page_id, snapshot_id, version):
        return self.root / "diffs" / page_id / f"{snapshot_id}.v{int(version)}.diff"

    def report_path(self, run_id):
        return self.root / "reports" / f"run-{run_id.removeprefix('run-')}.md"

    def read_index(self):
        return _read(self.index_path, INDEX_COLUMNS)

    def append_index(self, row):
        r = {k: ("" if v is None else str(v)) for k, v in row.items()}
        _check_header(self.index_path, INDEX_COLUMNS)
        if set(r) == set(INDEX_COLUMNS):
            if r["classification"] not in CLASSES:
                raise SnapshotError(f"invalid classification {r['classification']!r}")
            if r["method"] not in METHODS:
                raise SnapshotError(f"invalid method {r['method']!r}")
            if r["content_type"] and r["content_type"] not in CONTENT_TYPES:
                raise SnapshotError(f"invalid content_type {r['content_type']!r}")
            if "\n" in r["note"] or "\r" in r["note"]:
                raise SnapshotError("note must be a single line")
            ix = self.read_index()
            dup = ix[(ix["snapshot_id"] == r["snapshot_id"]) & (ix["normalizer_version"] == r["normalizer_version"])]
            if len(dup):
                raise SnapshotError(f"duplicate index key ({r['snapshot_id']}, v{r['normalizer_version']})")
        _append(self.index_path, INDEX_COLUMNS, r)

    def read_runs(self):
        return _read(self.runs_path, RUNS_COLUMNS)

    def append_run(self, row):
        _append(self.runs_path, RUNS_COLUMNS, row)
