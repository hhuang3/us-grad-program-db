"""Raw-file manifest and derived-table lineage (docs/spec/01_reference_data.md §6)."""

import csv
import hashlib
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import pandas as pd

MANIFEST_COLUMNS = ["source", "url", "method", "retrieved_at", "sha256", "bytes", "notes"]
DERIVED_COLUMNS = ["table", "sha256", "rows", "input_sha256", "generated_at"]
SOURCES = {"dhs_stem", "federal_register", "cip2020", "ipeds_completions", "ipeds_hd", "scorecard_fos"}
METHODS = {"http", "manual"}

UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ManifestError(ValueError):
    """A manifest row violates the manifest rules."""


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_timestamp(value):
    """Return value if it is a real UTC ISO 8601 timestamp of the form YYYY-MM-DDTHH:MM:SSZ."""
    if not isinstance(value, str) or not UTC_TIMESTAMP.match(value):
        raise ManifestError(f"retrieved_at must be UTC 'YYYY-MM-DDTHH:MM:SSZ', got {value!r}")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as e:
        raise ManifestError(f"retrieved_at is not a real time: {value!r}") from e
    return value


def raw_path_for(raw_root, source, url, retrieved_at):
    validate_timestamp(retrieved_at)
    name = PurePosixPath(urlparse(url).path).name
    if not name:
        raise ManifestError(f"URL has no file name: {url!r}")
    return Path(raw_root) / source / retrieved_at[:10] / name


def read_manifest(manifest_path):
    path = Path(manifest_path)
    if not path.exists():
        return pd.DataFrame(columns=MANIFEST_COLUMNS, dtype=str)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _validate_row(row):
    if set(row) != set(MANIFEST_COLUMNS):
        raise ManifestError(f"manifest row must have exactly {MANIFEST_COLUMNS}, got {sorted(row)}")
    if row["source"] not in SOURCES:
        raise ManifestError(f"unknown source {row['source']!r}")
    if not isinstance(row["url"], str) or not row["url"].startswith(("http://", "https://")):
        raise ManifestError(f"url must be an http(s) URL, got {row['url']!r}")
    if row["method"] not in METHODS:
        raise ManifestError(f"method must be one of {sorted(METHODS)}, got {row['method']!r}")
    validate_timestamp(row["retrieved_at"])
    if not isinstance(row["sha256"], str) or not SHA256.match(row["sha256"]):
        raise ManifestError(f"sha256 must be 64 lowercase hex chars, got {row['sha256']!r}")
    size = row["bytes"]
    if isinstance(size, bool) or not (isinstance(size, int) or (isinstance(size, str) and size.isdigit())):
        raise ManifestError(f"bytes must be a non-negative integer, got {size!r}")
    if int(size) < 0:
        raise ManifestError(f"bytes must be a non-negative integer, got {size!r}")
    notes = row["notes"] if isinstance(row["notes"], str) else ""
    if row["method"] == "manual" and not notes.strip():
        raise ManifestError("manual rows must explain why in notes")


def append_manifest(manifest_path, row):
    _validate_row(row)
    path = Path(manifest_path)
    existing = read_manifest(path)
    dup = existing[
        (existing["source"] == row["source"])
        & (existing["retrieved_at"] == row["retrieved_at"])
        & (existing["url"] == row["url"])
    ]
    if len(dup):
        raise ManifestError(f"duplicate manifest row for {row['source']} {row['url']} at {row['retrieved_at']}")
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if new:
            w.writerow(MANIFEST_COLUMNS)
        w.writerow([str(row[c]) for c in MANIFEST_COLUMNS])


def _count_rows(table_path):
    with open(table_path, encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def record_derived(derived_path, table_path, input_sha256s, generated_at):
    validate_timestamp(generated_at)
    for s in input_sha256s:
        if not SHA256.match(s):
            raise ManifestError(f"input sha256 must be 64 lowercase hex chars, got {s!r}")
    path = Path(derived_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if new:
            w.writerow(DERIVED_COLUMNS)
        w.writerow([
            Path(table_path).name,
            sha256_file(table_path),
            _count_rows(table_path),
            ";".join(sorted(set(input_sha256s))),
            generated_at,
        ])


def check_lineage(ref_dir, manifest_path, derived_path):
    """Return a list of problems; empty means every table in ref_dir traces to the manifest."""
    problems = []
    known = set(read_manifest(manifest_path)["sha256"])
    derived_file = Path(derived_path)
    if derived_file.exists():
        derived = pd.read_csv(derived_file, dtype=str, keep_default_na=False)
        latest = derived.groupby("table").tail(1).set_index("table")
    else:
        latest = pd.DataFrame(columns=DERIVED_COLUMNS[1:], dtype=str)
    for table in sorted(Path(ref_dir).glob("*.csv")):
        name = table.name
        if name not in latest.index:
            problems.append(f"{name}: no row in derived.csv")
            continue
        rec = latest.loc[name]
        actual = sha256_file(table)
        if rec["sha256"] != actual:
            problems.append(f"{name}: sha256 mismatch (derived.csv {rec['sha256']}, file {actual})")
        if str(_count_rows(table)) != rec["rows"]:
            problems.append(f"{name}: row count mismatch (derived.csv {rec['rows']}, file {_count_rows(table)})")
        inputs = [s for s in rec["input_sha256"].split(";") if s]
        if not inputs:
            problems.append(f"{name}: no input_sha256")
        for s in inputs:
            if s not in known:
                problems.append(f"{name}: input {s} not in manifest.csv")
    return problems
