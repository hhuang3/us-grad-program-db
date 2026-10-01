"""Checks on the committed real reference tables (data/ref, data/manifest).

These run against real derived data, not fixtures. They are red until 1d generates the tables.
Expected values live in config/expected_counts.yaml; a mismatch there most likely means the
official data changed and needs human confirmation, not that the test should be edited.
docs/spec/01 §6.2 (lineage), 03 §3.3/§3.4/§4.3 (STEM list), 04 §1.3 (targets).
"""

import re

import pytest

from gradprog.ref.stem import StemReference, cip_on_stem_list, expansion_only_codes
from gradprog.ref.targets import expand_targets, load_target_config
from gradprog.util.manifest import check_lineage
from helpers import REPO, assert_expected, load_expected, read_str_csv

REF = REPO / "data" / "ref"
MANIFEST = REPO / "data" / "manifest" / "manifest.csv"
DERIVED = REPO / "data" / "manifest" / "derived.csv"

TABLES = [
    "cip2020.csv", "stem_list.csv", "stem_core_series.csv", "ipeds_masters_target_cip.csv",
    "scorecard_fos_masters_target.csv", "candidates.csv", "candidates_by_institution.csv",
]


def test_all_reference_tables_exist():
    missing = [t for t in TABLES if not (REF / t).is_file()]
    assert missing == []


def test_every_reference_table_traces_to_manifest():
    assert check_lineage(REF, MANIFEST, DERIVED) == []


def test_expected_counts_file_names_stem_version():
    expected = load_expected()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", expected["stem_list"]["version_date"])


@pytest.fixture(scope="module")
def real_ref():
    return StemReference.load(REF)


@pytest.fixture(scope="module")
def real_cip():
    return read_str_csv(REF / "cip2020.csv")


def test_series_expansion_sentinel(real_ref):
    # 03 §4.3: if this fails, the STEM list or CIP changed. Stop and discuss before editing anything.
    assert_expected("stem_list.expansion_only_codes", expansion_only_codes(real_ref))


def test_real_stem_list_counts():
    stem = read_str_csv(REF / "stem_list.csv")
    core = read_str_csv(REF / "stem_core_series.csv")
    assert stem["cip_code"].is_unique
    assert_expected("stem_list.six_digit_codes", len(stem))
    assert_expected("stem_list.core_series_headers", len(core))
    assert_expected("stem_list.core_series", sorted(core["series"]))


def test_real_stem_list_title_mismatches(real_cip):
    stem = read_str_csv(REF / "stem_list.csv")
    squash = lambda s: re.sub(r"\s+", "", s).lower()  # noqa: E731
    official = {c: squash(t) for c, t in zip(real_cip["cip_code"], real_cip["title"])}
    mismatched = sorted(c for c, t in zip(stem["cip_code"], stem["title"]) if official.get(c) != squash(t))
    assert_expected("stem_list.title_mismatches", len(mismatched))


def test_real_cip2020_counts(real_cip):
    levels = real_cip["level"].astype(int).value_counts().to_dict()
    assert_expected("cip2020.valid_six_digit", levels.get(6, 0))
    assert_expected("cip2020.valid_four_digit", levels.get(4, 0))
    assert_expected("cip2020.valid_two_digit", levels.get(2, 0))


def test_real_targets(real_ref, real_cip):
    targets = expand_targets(load_target_config(REPO / "config" / "target_cip.csv"), real_cip)
    assert_expected("targets.total", len(targets))
    off = sorted(c for c in targets["cip_code"] if not cip_on_stem_list(c, real_ref))
    assert_expected("targets.not_on_stem_list", off)


def test_stem_list_built_from_expected_pdf():
    # The derived STEM tables must come from the manifest row of the expected PDF URL.
    from gradprog.util.manifest import read_manifest

    expected_url = load_expected()["stem_list"]["source_url"]
    manifest = read_manifest(MANIFEST)
    stem_rows = manifest[(manifest["source"] == "dhs_stem") & (manifest["url"] == expected_url)]
    assert len(stem_rows) >= 1, f"no dhs_stem manifest row for {expected_url}"
    derived = read_str_csv(DERIVED)
    latest = derived[derived["table"] == "stem_list.csv"].iloc[-1]
    assert set(stem_rows["sha256"]) & set(latest["input_sha256"].split(";")), (
        "stem_list.csv was not built from the PDF named in config/expected_counts.yaml"
    )
