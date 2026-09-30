"""docs/spec/01_reference_data.md §3–4 and 04_candidate_selection.md §3–4."""

import pandas as pd
import pytest

from gradprog.ref.cip import CipFormatError
from gradprog.ref.ipeds import (
    IpedsError,
    build_candidates,
    build_candidates_by_institution,
    build_ipeds_masters_target,
    read_ipeds_csv,
    select_revised_member,
)
from helpers import read_str_csv

DATA_YEAR = "2023-24"


@pytest.fixture
def completions(fixtures):
    return read_str_csv(fixtures / "ipeds_c_a_sample.csv")


@pytest.fixture
def hd(fixtures):
    return read_str_csv(fixtures / "ipeds_hd_sample.csv")


@pytest.fixture
def ipeds_table(completions, hd, targets):
    return build_ipeds_masters_target(completions, hd, targets, DATA_YEAR)


@pytest.fixture
def candidates(ipeds_table, hd, cip2020, stem_ref):
    return build_candidates(ipeds_table, hd, cip2020, stem_ref)


def keyed(df):
    return {(r.unitid, r.cip_code): r for r in df.itertuples(index=False)}


# --- zip member selection & reading (01 §3) -----------------------------------

@pytest.mark.parametrize(
    "names, expected",
    [
        (["c2024_a.csv", "c2024_a_rv.csv"], "c2024_a_rv.csv"),
        (["c2023_a.csv", "c2023_a_RV.csv"], "c2023_a_RV.csv"),
    ],
)
def test_select_revised_member_case_insensitive(names, expected):
    assert select_revised_member(names) == expected


@pytest.mark.parametrize("names", [["c2025_a.csv"], ["c2024_a_rv.csv", "c2024_a_RV.csv"], []])
def test_select_revised_member_never_falls_back(names):
    with pytest.raises(IpedsError):
        select_revised_member(names)


def test_read_ipeds_csv_strips_bom_and_keeps_strings(fixtures):
    df = read_ipeds_csv(fixtures / "ipeds_c_a_bom_sample.csv")
    assert df.columns[0] == "UNITID"
    assert df["CIPCODE"].iloc[0] == "30.7001"
    assert all(str(t) in ("object", "str", "string") for t in df.dtypes)


# --- reference table (04 §3) --------------------------------------------------

def test_ipeds_table_columns(ipeds_table):
    assert list(ipeds_table.columns) == [
        "unitid", "state", "cip_code", "cip_group", "completions_masters",
        "completions_masters_second_major", "completions_masters_nonresident",
        "imputation_flag", "data_year",
    ]


def test_ipeds_table_rows(ipeds_table):
    assert list(zip(ipeds_table["unitid"], ipeds_table["cip_code"])) == [
        ("100001", "30.7001"), ("100001", "30.7102"),
        ("100002", "27.0501"), ("100002", "30.7001"),
        ("100003", "52.1301"),
        ("100004", "30.7099"),
        ("100005", "27.0601"),
        ("100006", "30.7001"), ("100006", "30.7101"),
    ]


def test_only_masters_and_targets_kept(ipeds_table):
    rows = keyed(ipeds_table)
    assert ("100002", "11.0701") not in rows          # not a target CIP
    assert rows[("100001", "30.7001")].completions_masters == 50  # bachelor's row (AWLEVEL 5) ignored
    assert "99" not in set(ipeds_table["cip_code"])   # institution total row dropped


def test_zero_and_second_major_only_rows_dropped(ipeds_table):
    rows = keyed(ipeds_table)
    assert ("100004", "45.0603") not in rows   # CTOTALT == 0
    assert ("100005", "52.1302") not in rows   # only a second-major row


def test_major_columns(ipeds_table):
    r = keyed(ipeds_table)[("100001", "30.7001")]
    assert r.completions_masters == 50
    assert r.completions_masters_second_major == 3
    assert r.completions_masters_nonresident == 30
    assert keyed(ipeds_table)[("100001", "30.7102")].completions_masters_second_major == 0


def test_imputation_flag_and_data_year(ipeds_table):
    rows = keyed(ipeds_table)
    assert rows[("100005", "27.0601")].imputation_flag == "P"
    assert rows[("100001", "30.7001")].imputation_flag == "R"
    assert set(ipeds_table["data_year"]) == {DATA_YEAR}


def test_reference_table_keeps_territories(ipeds_table):
    assert keyed(ipeds_table)[("100003", "52.1301")].state == "PR"


def test_duplicate_unitid_cip_major_raises(completions, hd, targets):
    dup = completions.iloc[[0]]
    with pytest.raises(IpedsError):
        build_ipeds_masters_target(pd.concat([completions, dup]), hd, targets, DATA_YEAR)


def test_invalid_majornum_raises(completions, hd, targets):
    bad = completions.copy()
    bad.loc[0, "MAJORNUM"] = "3"
    with pytest.raises(IpedsError):
        build_ipeds_masters_target(bad, hd, targets, DATA_YEAR)


def test_malformed_cipcode_raises(completions, hd, targets):
    bad = completions.copy()
    bad.loc[0, "CIPCODE"] = "30.70"
    with pytest.raises(CipFormatError):
        build_ipeds_masters_target(bad, hd, targets, DATA_YEAR)


def test_unitid_missing_from_hd_raises(completions, hd, targets):
    with pytest.raises(IpedsError, match="100006"):
        build_ipeds_masters_target(completions, hd[hd["UNITID"] != "100006"], targets, DATA_YEAR)


# --- candidates.csv (04 §4) ---------------------------------------------------

CANDIDATE_COLUMNS = [
    "cip_group", "rank_in_group", "unitid", "institution_name", "state", "cip_code", "cip_title",
    "on_stem_list", "completions_masters", "completions_masters_second_major",
    "completions_masters_nonresident", "institution_target_cip_count", "data_year",
]


def test_candidates_columns(candidates):
    assert list(candidates.columns) == CANDIDATE_COLUMNS


def test_candidates_exclude_non_states(candidates):
    assert "PR" not in set(candidates["state"])
    assert "100003" not in set(candidates["unitid"])


def test_candidates_order_and_rank_within_group(candidates):
    got = list(zip(candidates["cip_group"], candidates["rank_in_group"].astype(int),
                   candidates["unitid"], candidates["cip_code"]))
    assert got == [
        ("ds", 1, "100002", "30.7001"),
        ("ds", 2, "100001", "30.7001"),   # tie at 50 broken by unitid
        ("ds", 3, "100006", "30.7001"),
        ("ds", 4, "100004", "30.7099"),
        ("analytics", 1, "100006", "30.7101"),
        ("analytics", 2, "100001", "30.7102"),
        ("stats", 1, "100005", "27.0601"),
        ("stats", 2, "100002", "27.0501"),
    ]


def test_candidates_lookups(candidates):
    rows = keyed(candidates)
    r = rows[("100002", "30.7001")]
    assert r.institution_name == "Beta State University"
    assert r.state == "CA"
    assert r.cip_title == "Data Science, General."
    assert r.data_year == DATA_YEAR


def test_candidates_on_stem_list(candidates):
    rows = keyed(candidates)
    assert bool(rows[("100004", "30.7099")].on_stem_list) is False
    assert bool(rows[("100001", "30.7001")].on_stem_list) is True
    assert bool(rows[("100005", "27.0601")].on_stem_list) is True  # via series 27 expansion


def test_candidates_institution_target_cip_count(candidates):
    counts = dict(zip(candidates["unitid"], candidates["institution_target_cip_count"].astype(int)))
    assert counts == {"100001": 2, "100002": 2, "100004": 1, "100005": 1, "100006": 2}


def test_nonresident_does_not_affect_order(ipeds_table, hd, cip2020, stem_ref):
    changed = ipeds_table.copy()
    changed["completions_masters_nonresident"] = 0
    a = build_candidates(ipeds_table, hd, cip2020, stem_ref)
    b = build_candidates(changed, hd, cip2020, stem_ref)
    assert list(zip(a["unitid"], a["cip_code"])) == list(zip(b["unitid"], b["cip_code"]))


# --- candidates_by_institution.csv (04 §4.4) ----------------------------------

def test_by_institution(candidates):
    by = build_candidates_by_institution(candidates)
    assert list(by.columns) == [
        "unitid", "institution_name", "state", "institution_target_cip_count", "cip_codes",
        "completions_ds", "completions_analytics", "completions_stats", "completions_mgmt_sci",
        "completions_econ",
    ]
    assert list(by["unitid"]) == ["100001", "100002", "100004", "100005", "100006"]
    r = {row.unitid: row for row in by.itertuples(index=False)}
    assert r["100001"].cip_codes == "30.7001;30.7102"
    assert (r["100001"].completions_ds, r["100001"].completions_analytics) == (50, 20)
    assert (r["100002"].completions_ds, r["100002"].completions_stats) == (80, 10)
    assert r["100005"].completions_mgmt_sci == 0
    assert r["100006"].institution_target_cip_count == 2
