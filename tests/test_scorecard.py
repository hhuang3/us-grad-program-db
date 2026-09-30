"""docs/spec/01_reference_data.md §5 (missing-value handling) and 04_candidate_selection.md §6."""

import math

import pandas as pd
import pytest

from gradprog.ref.scorecard import ScorecardValueError, build_scorecard_fos_target, parse_metric
from helpers import read_str_csv

METRICS = [
    "ipedscount1", "ipedscount2", "earn_mdn_1yr", "earn_mdn_4yr", "earn_mdn_5yr",
    "earn_count_wne_1yr", "debt_all_stgp_eval_mdn",
]


# --- parse_metric -------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, value, status",
    [
        ("95000", 95000.0, "reported"),
        ("88000.5", 88000.5, "reported"),
        ("0", 0.0, "reported"),
        ("PS", None, "privacy_suppressed"),
        ("NA", None, "not_available"),
    ],
)
def test_parse_metric(raw, value, status):
    assert parse_metric(raw) == (value, status)


@pytest.mark.parametrize("raw", ["", " ", "PrivacySuppressed", "NULL", "n/a", "ps", "1,000", "12a", None])
def test_parse_metric_rejects_undocumented_values(raw):
    with pytest.raises(ScorecardValueError):
        parse_metric(raw)


# --- derived table ------------------------------------------------------------

@pytest.fixture
def fos(fixtures, targets, cip2020):
    raw = read_str_csv(fixtures / "scorecard_fos_sample.csv")
    return build_scorecard_fos_target(raw, targets, cip2020)


def test_columns(fos):
    expected = ["unitid", "opeid6", "instnm", "control", "cip4", "cipdesc", "credlev", "creddesc",
                "cip4_broader_than_target"]
    for m in METRICS:
        expected += [m, f"{m}_status"]
    assert list(fos.columns) == expected


def test_only_masters_and_target_parents(fos):
    assert set(fos["credlev"]) == {"5"}
    assert list(zip(fos["unitid"], fos["cip4"])) == [
        ("100001", "30.70"), ("100002", "30.71"), ("100003", "45.06"),
        ("100005", "27.06"), ("100006", "52.13"),
    ]


def test_opeid6_leading_zeros_kept(fos):
    assert fos["opeid6"].iloc[0] == "000001"


def test_missing_codes_become_null_with_status(fos):
    r = fos.set_index("unitid").loc["100001"]
    assert pd.isna(r["earn_mdn_1yr"]) and r["earn_mdn_1yr_status"] == "not_available"
    assert r["earn_mdn_4yr"] == 95000 and r["earn_mdn_4yr_status"] == "reported"
    assert pd.isna(r["debt_all_stgp_eval_mdn"]) and r["debt_all_stgp_eval_mdn_status"] == "privacy_suppressed"
    r2 = fos.set_index("unitid").loc["100002"]
    assert pd.isna(r2["ipedscount1"]) and r2["ipedscount1_status"] == "not_available"
    assert math.isclose(r2["earn_mdn_4yr"], 88000.5)


def test_status_values_are_documented(fos):
    for m in METRICS:
        assert set(fos[f"{m}_status"]) <= {"reported", "privacy_suppressed", "not_available"}
        reported = fos[f"{m}_status"] == "reported"
        assert fos.loc[reported, m].notna().all()
        assert fos.loc[~reported, m].isna().all()


def test_broader_than_target_flag(fos):
    flags = dict(zip(fos["cip4"], fos["cip4_broader_than_target"].map(bool)))
    assert flags == {"30.70": False, "30.71": False, "45.06": True, "27.06": False, "52.13": False}


def test_undocumented_value_in_target_row_raises(fixtures, targets, cip2020):
    raw = read_str_csv(fixtures / "scorecard_fos_sample.csv")
    raw.loc[0, "EARN_MDN_5YR"] = "PrivacySuppressed"
    with pytest.raises(ScorecardValueError):
        build_scorecard_fos_target(raw, targets, cip2020)


def test_malformed_cipcode_raises(fixtures, targets, cip2020):
    from gradprog.ref.cip import CipFormatError

    raw = read_str_csv(fixtures / "scorecard_fos_sample.csv")
    raw.loc[0, "CIPCODE"] = "370"
    with pytest.raises(CipFormatError):
        build_scorecard_fos_target(raw, targets, cip2020)
