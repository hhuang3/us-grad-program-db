"""docs/spec/08_extraction.md §6, §9: evidence checks and TOEFL scale."""

import pytest

from gradprog.extract.evidence import check_entry, date_in_evidence, number_in_evidence, toefl_scale

PAGE = """Applicants need a minimum TOEFL score of 100.
Deadline:   October 7,
2026 for fall. The fee is $1,250 per credit.
See the Graduate School requirements page."""


def e(**over):
    base = {"value_status": "found", "value": 100, "evidence_text": "minimum TOEFL score of 100", "confidence": 0.9,
            "reference_target": None}
    base.update(over)
    return base


def test_passes_when_evidence_is_verbatim_and_value_matches():
    assert check_entry("toefl_total", e(), PAGE) == []


def test_whitespace_is_normalized_on_both_sides():
    entry = {"value_status": "found", "deadline_month": 10, "deadline_day": 7, "deadline_year": 2026,
             "evidence_text": "Deadline: October 7, 2026", "confidence": 0.9, "is_rolling": False}
    assert check_entry("deadlines", entry, PAGE) == []


@pytest.mark.parametrize("evidence", ["minimum toefl score of 100", "minimum TOEFL score of 100!", "TOEFL 100"])
def test_case_and_punctuation_are_not_fuzzy(evidence):
    assert check_entry("toefl_total", e(evidence_text=evidence), PAGE) == ["evidence_not_verbatim"]


def test_evidence_over_200_characters_fails():
    long = "x" * 201
    assert check_entry("toefl_total", e(evidence_text=long), PAGE + long) == ["evidence_too_long"]


def test_evidence_of_exactly_200_characters_passes():
    text = "x" * 196 + " 100"
    assert check_entry("toefl_total", e(evidence_text=text), PAGE + text) == []


@pytest.mark.parametrize("status", ["found", "referenced_elsewhere", "mentioned_without_value"])
def test_every_status_needs_evidence(status):
    assert check_entry("toefl_total", e(value_status=status, evidence_text=None), PAGE) == ["evidence_missing"]


def test_value_must_appear_in_evidence():
    assert check_entry("toefl_total", e(value=90), PAGE) == ["value_not_in_evidence"]


@pytest.mark.parametrize("value,text,ok", [
    (100, "score of 100", True), (100, "score of 1000", False), (100, "score of 100.5", False),
    (90, "at least 90.", True), (1250, "$1,250 per credit", True), (1250.0, "$1,250.00", True),
    (5.0, "5.0 overall", True), (5.0, "a score of 5", True), (79, "279 total", False), (5, "5.0 overall", True),
    (90, "90.0 total", True),
])
def test_numbers_match_on_word_boundaries(value, text, ok):
    assert number_in_evidence(value, text) is ok


@pytest.mark.parametrize("m,d,y,text", [
    (10, 7, 2026, "October 7, 2026"), (10, 7, 2026, "Oct. 7, 2026"), (10, 7, 2026, "10/07/2026"),
    (10, 7, 2026, "2026-10-07"), (10, 7, 2026, "7 October 2026"), (10, 7, 2026, "October 7th, 2026"),
    (9, 15, None, "Sept 15"), (9, 15, None, "September 15th"), (9, 15, None, "Sep. 15"), (1, 2, None, "January 2"),
    (1, 2, None, "2 January"), (10, 7, None, "10/07"), (3, 1, None, "March 1st for"),
])
def test_date_wordings_match(m, d, y, text):
    assert date_in_evidence(m, d, y, text)


@pytest.mark.parametrize("m,d,y,text", [
    (10, 7, 2026, "October 17, 2026"), (10, 7, 2026, "October 7, 2025"), (10, 7, 2026, "October 7"),
    (1, 2, None, "January 20"), (1, 2, None, "June 2"), (3, 1, None, "1/3/2027"), (10, 7, 2026, "07/10/2026"),
])
def test_wrong_dates_do_not_match(m, d, y, text):
    assert not date_in_evidence(m, d, y, text)


def test_rolling_without_a_date_passes():
    entry = {"value_status": "found", "deadline_month": None, "deadline_day": None, "deadline_year": None,
             "is_rolling": True, "evidence_text": "minimum TOEFL", "confidence": 0.5}
    assert check_entry("deadlines", entry, PAGE) == []


@pytest.mark.parametrize("m,d,y,reason", [(2, 30, None, ["value_out_of_range"]), (2, 29, 2027, ["value_out_of_range"]),
                                            (13, 1, None, ["value_out_of_range"]), (2, 29, None, ["value_not_in_evidence"])])
def test_impossible_dates_fail_before_term_logic(m, d, y, reason):
    entry = {"value_status": "found", "deadline_month": m, "deadline_day": d, "deadline_year": y,
             "is_rolling": False, "evidence_text": "minimum TOEFL", "confidence": 0.5}
    assert check_entry("deadlines", entry, PAGE) == reason


def test_found_deadline_without_date_or_rolling_fails():
    entry = {"value_status": "found", "deadline_month": None, "deadline_day": None, "deadline_year": None,
             "is_rolling": False, "evidence_text": "minimum TOEFL", "confidence": 0.5}
    assert check_entry("deadlines", entry, PAGE) == ["value_missing"]


@pytest.mark.parametrize("key,value", [
    ("toefl_total", 121), ("toefl_total", 6.5), ("toefl_total", 90.5), ("ielts_min_overall", 9.5),
    ("ielts_min_overall", 6.3), ("length_months_min", 0), ("credits_required", 0), ("cip_code", "45.06"),
])
def test_values_out_of_range_fail(key, value):
    assert check_entry(key, e(value=value), PAGE) == ["value_out_of_range"]


def test_enum_values_are_not_compared_with_evidence():
    assert check_entry("gre_policy", e(value="optional"), PAGE) == []


@pytest.mark.parametrize("key,value", [("gre_policy", "maybe"), ("gmat_policy", "Required"), ("stem_claim_on_page", "x")])
def test_free_text_enums_are_checked_in_code(key, value):
    assert check_entry(key, e(value=value), PAGE) == ["value_out_of_range"]


def test_tuition_amount_must_appear():
    base = {"value_status": "found", "tuition_basis": "per_credit", "evidence_text": "The fee is $1,250 per credit",
            "confidence": 0.9, "tuition_year": None, "includes_fees": None}
    assert check_entry("tuition", {**base, "tuition_amount_usd": 1250}, PAGE) == []
    assert check_entry("tuition", {**base, "tuition_amount_usd": 1300}, PAGE) == ["value_not_in_evidence"]
    assert check_entry("tuition", {**base, "tuition_amount_usd": None}, PAGE) == ["value_missing"]


def test_cip_must_appear_in_evidence():
    page = "CIP code 45.0603 applies."
    assert check_entry("cip_code", e(value="45.0603", evidence_text="CIP code 45.0603"), page) == []
    assert check_entry("cip_code", e(value="45.0604", evidence_text="CIP code 45.0603"), page) == ["value_not_in_evidence"]


def test_no_value_statuses_skip_the_value_checks():
    entry = e(value=None, value_status="mentioned_without_value", evidence_text="minimum TOEFL score")
    assert check_entry("toefl_total", entry, PAGE) == []


def test_reference_needs_a_target():
    entry = e(value=None, value_status="referenced_elsewhere", evidence_text="See the Graduate School")
    assert check_entry("toefl_total", entry, PAGE) == ["reference_target_missing"]
    assert check_entry("toefl_total", {**entry, "reference_target": "requirements page"}, PAGE) == []


def test_confidence_outside_0_to_1_fails():
    assert check_entry("toefl_total", e(confidence=1.5), PAGE) == ["confidence_out_of_range"]


# TOEFL scale, 08 §9
@pytest.mark.parametrize("value,evidence,expected", [
    (100, "TOEFL 100", ("legacy", None)),
    (79, "79 overall", ("legacy", None)),
    (4.5, "TOEFL 4.5", ("new", None)),
    (5, "TOEFL 5", ("new", None)),
    (6.5, "TOEFL 6.5", (None, "unrecognized")),
    (0, "TOEFL 0", (None, "unrecognized")),
    (4.5, "4.5 on the new scale", ("new", None)),
    (90, "90 on the old scale", ("legacy", None)),
    (90, "90 iBT total", ("legacy", None)),
    (90, "90 on the new TOEFL", (None, "scale_mismatch")),
    (5.0, "5.0 (old scale)", (None, "scale_mismatch")),
])
def test_toefl_scale(value, evidence, expected):
    assert toefl_scale(value, evidence) == expected
