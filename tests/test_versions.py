"""docs/spec/01_reference_data.md §8: deriving the current data version from committed files."""

import pytest

from gradprog.ref.versions import VersionError, ipeds_version, scorecard_release
from gradprog.util.manifest import append_manifest, record_derived, sha256_file

ZIP_URL = "https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Field-of-Study_06102026.zip"


@pytest.mark.parametrize("data_year, expected", [("2023-24", "C2024"), ("2024-25", "C2025"), ("1999-00", "C2000")])
def test_ipeds_version(data_year, expected):
    assert ipeds_version(data_year) == expected


@pytest.mark.parametrize("bad", ["2023-25", "2023", "23-24", "2023/24", "", "2023-2024"])
def test_ipeds_version_rejects(bad):
    with pytest.raises(VersionError):
        ipeds_version(bad)


def setup_lineage(tmp_path, urls):
    manifest, derived = tmp_path / "manifest.csv", tmp_path / "derived.csv"
    shas = []
    for i, url in enumerate(urls):
        raw = tmp_path / f"raw{i}"
        raw.write_bytes(f"raw {i}".encode())
        sha = sha256_file(raw)
        shas.append(sha)
        append_manifest(manifest, {"source": "scorecard_fos" if "scorecard" in url else "cip2020", "url": url,
                                   "method": "http", "retrieved_at": f"2026-09-30T14:10:0{i}Z", "sha256": sha,
                                   "bytes": 5, "notes": ""})
    table = tmp_path / "scorecard_fos_masters_target.csv"
    table.write_text("unitid\n1\n", encoding="utf-8")
    record_derived(derived, table, shas, "2026-09-30T14:18:30Z")
    return manifest, derived


def test_scorecard_release_from_lineage(tmp_path):
    manifest, derived = setup_lineage(tmp_path, [ZIP_URL, "https://nces.ed.gov/ipeds/cipcode/Files/CIPCode2020.csv"])
    assert scorecard_release(manifest, derived) == "2026-06-10"


def test_scorecard_release_needs_exactly_one_zip(tmp_path):
    other = ZIP_URL.replace("06102026", "06102027")
    manifest, derived = setup_lineage(tmp_path, [ZIP_URL, other])
    with pytest.raises(VersionError):
        scorecard_release(manifest, derived)


@pytest.mark.parametrize("url", [
    "https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Field-of-Study.zip",
    "https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Field-of-Study_13402026.zip",
])
def test_scorecard_release_bad_file_name(tmp_path, url):
    manifest, derived = setup_lineage(tmp_path, [url])
    with pytest.raises(VersionError):
        scorecard_release(manifest, derived)


def test_scorecard_release_without_table_row(tmp_path):
    manifest, derived = setup_lineage(tmp_path, [ZIP_URL])
    derived.write_text("table,sha256,rows,input_sha256,generated_at\n", encoding="utf-8")
    with pytest.raises(VersionError):
        scorecard_release(manifest, derived)
