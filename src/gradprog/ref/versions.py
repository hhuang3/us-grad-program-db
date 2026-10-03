"""Derive the data version of committed reference tables (docs/spec/01_reference_data.md §8)."""

import re
from datetime import date

import pandas as pd

DATA_YEAR = re.compile(r"^(\d{4})-(\d{2})$")
RELEASE_IN_NAME = re.compile(r"_(\d{2})(\d{2})(\d{4})\.zip$")
SCORECARD_TABLE = "scorecard_fos_masters_target.csv"


class VersionError(ValueError):
    """The data version cannot be derived unambiguously."""


def ipeds_version(data_year):
    m = DATA_YEAR.match(data_year or "")
    if not m:
        raise VersionError(f"IPEDS data_year must look like 'YYYY-YY', got {data_year!r}")
    start = int(m.group(1))
    if int(m.group(2)) != (start + 1) % 100:
        raise VersionError(f"IPEDS data_year {data_year!r} does not span consecutive years")
    return f"C{start + 1}"


def scorecard_release(manifest_path, derived_path):
    derived = pd.read_csv(derived_path, dtype=str, keep_default_na=False)
    rows = derived[derived["table"] == SCORECARD_TABLE]
    if rows.empty:
        raise VersionError(f"no derived.csv row for {SCORECARD_TABLE}")
    inputs = set(rows.iloc[-1]["input_sha256"].split(";"))
    manifest = pd.read_csv(manifest_path, dtype=str, keep_default_na=False)
    urls = sorted({u for s, u in zip(manifest["sha256"], manifest["url"]) if s in inputs and u.endswith(".zip")})
    if len(urls) != 1:
        raise VersionError(f"expected exactly one Scorecard .zip input for {SCORECARD_TABLE}, found {urls}")
    m = RELEASE_IN_NAME.search(urls[0])
    if not m:
        raise VersionError(f"cannot read a release date '_MMDDYYYY.zip' from {urls[0]}")
    try:
        return date(int(m.group(3)), int(m.group(1)), int(m.group(2))).isoformat()
    except ValueError as e:
        raise VersionError(f"invalid release date in {urls[0]}") from e
