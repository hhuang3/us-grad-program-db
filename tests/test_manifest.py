"""docs/spec/01_reference_data.md §6: raw-file manifest and derived-table lineage."""

import hashlib
from pathlib import Path

import pytest

from gradprog.util.manifest import (
    ManifestError,
    append_manifest,
    check_lineage,
    raw_path_for,
    read_manifest,
    record_derived,
    sha256_file,
)

MANIFEST_COLUMNS = ["source", "url", "method", "retrieved_at", "sha256", "bytes", "notes"]
STEM_URL = "https://www.ice.gov/doclib/sevis/pdf/stemList2024.pdf"


def row(**overrides):
    base = {
        "source": "dhs_stem",
        "url": STEM_URL,
        "method": "manual",
        "retrieved_at": "2026-10-01T15:04:00Z",
        "sha256": "a" * 64,
        "bytes": 428790,
        "notes": "automated request returned HTTP 403",
    }
    base.update(overrides)
    return base


def test_sha256_file(tmp_path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"abc")
    assert sha256_file(p) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_raw_path_for_uses_utc_date_and_last_url_segment():
    got = raw_path_for(Path("data/raw"), "dhs_stem", STEM_URL, "2026-10-01T15:04:00Z")
    assert got == Path("data/raw/dhs_stem/2026-10-01/stemList2024.pdf")
    got = raw_path_for(
        Path("data/raw"), "ipeds_completions",
        "https://nces.ed.gov/ipeds/complete-data-files/C2024_A.zip", "2026-10-02T00:00:01Z",
    )
    assert got == Path("data/raw/ipeds_completions/2026-10-02/C2024_A.zip")


def test_append_and_read_manifest(tmp_path):
    path = tmp_path / "manifest.csv"
    append_manifest(path, row())
    append_manifest(path, row(retrieved_at="2026-10-02T09:00:00Z", method="http", notes=""))
    text = path.read_text(encoding="utf-8")
    assert text.splitlines()[0] == ",".join(MANIFEST_COLUMNS)
    assert not text.startswith("﻿") and "\r\n" not in text
    df = read_manifest(path)
    assert list(df.columns) == MANIFEST_COLUMNS
    assert len(df) == 2
    assert list(df["method"]) == ["manual", "http"]


@pytest.mark.parametrize(
    "bad",
    [
        {"source": "scorecard_api"},
        {"method": "browser"},
        {"retrieved_at": "2026-10-01 15:04:00"},
        {"retrieved_at": "2026-10-01T15:04:00+00:00"},
        {"retrieved_at": "2026-10-01"},
        {"sha256": "A" * 64},
        {"sha256": "a" * 63},
        {"bytes": -1},
        {"bytes": "12kb"},
        {"url": ""},
    ],
)
def test_append_manifest_validates(tmp_path, bad):
    with pytest.raises(ManifestError):
        append_manifest(tmp_path / "manifest.csv", row(**bad))
    assert not (tmp_path / "manifest.csv").exists() or len(read_manifest(tmp_path / "manifest.csv")) == 0


def test_manual_row_requires_notes(tmp_path):
    with pytest.raises(ManifestError):
        append_manifest(tmp_path / "manifest.csv", row(notes=""))


def test_duplicate_source_time_url_rejected_but_same_sha_allowed(tmp_path):
    path = tmp_path / "manifest.csv"
    append_manifest(path, row())
    append_manifest(path, row(retrieved_at="2026-10-05T00:00:00Z"))  # same sha, new time: fine
    with pytest.raises(ManifestError):
        append_manifest(path, row())


# --- lineage ------------------------------------------------------------------

@pytest.fixture
def lineage(tmp_path):
    ref = tmp_path / "ref"
    ref.mkdir()
    raw_a = tmp_path / "a.pdf"
    raw_a.write_bytes(b"%PDF-1.6 raw a")
    raw_b = tmp_path / "b.csv"
    raw_b.write_bytes(b"raw b")
    manifest = tmp_path / "manifest.csv"
    for i, p in enumerate([raw_a, raw_b]):
        append_manifest(manifest, row(
            source="dhs_stem" if i == 0 else "cip2020",
            url=f"https://example.gov/{p.name}",
            method="http", notes="",
            sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            bytes=p.stat().st_size,
        ))
    table = ref / "stem_list.csv"
    table.write_text("cip_code,title\n30.7001,Data Science.\n27.0501,Statistics.\n", encoding="utf-8")
    derived = tmp_path / "derived.csv"
    record_derived(derived, table, [sha256_file(raw_b), sha256_file(raw_a)], "2026-10-03T00:00:00Z")
    return ref, manifest, derived, table, raw_a, raw_b


def test_record_derived_row(lineage):
    ref, manifest, derived, table, raw_a, raw_b = lineage
    lines = derived.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "table,sha256,rows,input_sha256,generated_at"
    table_name, sha, rows, inputs, generated = lines[1].split(",")
    assert table_name == "stem_list.csv"
    assert sha == sha256_file(table)
    assert rows == "2"
    assert inputs == ";".join(sorted([sha256_file(raw_a), sha256_file(raw_b)]))
    assert generated == "2026-10-03T00:00:00Z"


def test_lineage_ok(lineage):
    ref, manifest, derived, *_ = lineage
    assert check_lineage(ref, manifest, derived) == []


def test_lineage_detects_modified_table(lineage):
    ref, manifest, derived, table, *_ = lineage
    table.write_text("cip_code,title\n30.7001,Changed.\n", encoding="utf-8")
    problems = check_lineage(ref, manifest, derived)
    assert any("stem_list.csv" in p and "sha256" in p for p in problems)


def test_lineage_detects_table_without_derived_row(lineage):
    ref, manifest, derived, *_ = lineage
    (ref / "orphan.csv").write_text("a\n1\n", encoding="utf-8")
    assert any("orphan.csv" in p for p in check_lineage(ref, manifest, derived))


def test_lineage_detects_input_not_in_manifest(lineage, tmp_path):
    ref, manifest, derived, table, *_ = lineage
    record_derived(derived, table, ["f" * 64], "2026-10-04T00:00:00Z")
    assert any("f" * 64 in p for p in check_lineage(ref, manifest, derived))


def test_lineage_uses_latest_row_per_table(lineage):
    ref, manifest, derived, table, raw_a, raw_b = lineage
    table.write_text("cip_code,title\n30.7001,Data Science.\n", encoding="utf-8")
    record_derived(derived, table, [sha256_file(raw_a)], "2026-10-04T00:00:00Z")
    assert check_lineage(ref, manifest, derived) == []
