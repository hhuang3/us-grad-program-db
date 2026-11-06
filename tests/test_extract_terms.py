"""docs/spec/08_extraction.md §7: valid_for_term, term_basis, stale, including every §7.5 case."""

from datetime import date

import pytest

from gradprog.extract.terms import (
    TERM_UNKNOWN, deadline_term, next_occurrence, parse_term, term_of_date, tuition_term, undated_term,
)

OCT11 = date(2026, 10, 11)


@pytest.mark.parametrize("season,d,term", [
    ("Fall", date(2026, 8, 15), "Fall 2026"), ("Fall", date(2026, 10, 7), "Fall 2027"),
    ("Fall", date(2026, 9, 1), "Fall 2027"), ("Fall", date(2026, 8, 31), "Fall 2026"),
    ("Spring", date(2026, 11, 9), "Spring 2027"), ("Spring", date(2026, 2, 15), "Spring 2026"),
    ("Spring", date(2026, 3, 1), "Spring 2027"), ("Spring", date(2028, 2, 29), "Spring 2028"),
    ("Spring", date(2027, 9, 15), "Spring 2028"),
])
def test_season_windows(season, d, term):
    assert term_of_date(season, d) == term


def test_summer_has_no_window():
    with pytest.raises(ValueError):
        term_of_date("Summer", date(2026, 1, 1))


@pytest.mark.parametrize("written,parsed", [
    ("Fall 2027", ("season_year", "Fall", 2027)), ("Fall semester 2027", ("season_year", "Fall", 2027)),
    ("2027 fall entry", ("season_year", "Fall", 2027)), ("Autumn 2027", ("season_year", "Fall", 2027)),
    ("for the fall semester", ("season", "Fall", None)), ("spring", ("season", "Spring", None)),
    ("2026-27", ("academic_year", None, 2026)), ("AY 2026-2027", ("academic_year", None, 2026)),
    ("2026 applications", (None, None, None)), ("October 2026 Start", (None, None, None)), ("", (None, None, None)),
])
def test_parse_term(written, parsed):
    assert parse_term(written) == parsed


def test_next_occurrence_includes_the_day_itself():
    assert next_occurrence(10, 11, OCT11) == OCT11
    assert next_occurrence(10, 10, OCT11) == date(2027, 10, 10)
    assert next_occurrence(2, 29, OCT11) == date(2028, 2, 29)


# §7.5, in the table's order
def test_unt_pg0007_fall_semester_with_a_past_date():
    r = deadline_term("for the fall semester", 8, 15, 2026, "fall;spring;summer", date(2026, 10, 4))
    assert (r.valid_for_term, r.term_basis, r.stale) == ("Fall 2026", "inferred_from_date", True)
    assert r.review == ("term_inferred",)


def test_duke_pg0055_visa_dates_in_2025_are_not_fall_2027():
    r = deadline_term(None, 6, 1, 2025, "fall", OCT11)
    assert (r.valid_for_term, r.term_basis, r.stale) == ("Fall 2025", "inferred_from_date", True)


def test_ucla_fall_2027_is_stated():
    r = deadline_term("Fall 2027", 12, 1, 2026, "fall", OCT11)
    assert (r.valid_for_term, r.term_basis, r.stale, r.review) == ("Fall 2027", "stated", False, ())


def test_columbia_2026_applications_is_unknown():
    r = undated_term("GRE optional for the 2026 applications", "fall")
    assert (r.valid_for_term, r.term_basis, r.review) == (TERM_UNKNOWN, "unknown", ("term_unknown",))


def test_unt_pg0008_spring_2027_stays_spring():
    r = deadline_term("Spring 2027", 11, 9, 2026, "fall;spring;summer", date(2026, 10, 7))
    assert (r.valid_for_term, r.term_basis, r.review) == ("Spring 2027", "stated", ())


def test_uwmadison_pg0031_january_2_with_no_year():
    r = deadline_term("fall term", 1, 2, None, "fall", OCT11)
    assert (r.valid_for_term, r.term_basis, r.deadline_date, r.stale) == (
        "Fall 2027", "recurring_no_year", date(2027, 1, 2), False)
    assert r.review == ()


def test_uiuc_pg0039_spring_september_15():
    r = deadline_term("MS Spring Admission", 9, 15, None, "fall;spring", date(2026, 10, 4))
    assert (r.valid_for_term, r.term_basis, r.deadline_date) == ("Spring 2028", "recurring_no_year", date(2027, 9, 15))
    assert r.review == ()


def test_washu_october_2026_start_is_not_fall_2027():
    r = deadline_term("October 2026 Start", 8, 1, 2026, "fall", OCT11)
    assert r.valid_for_term == TERM_UNKNOWN


# new synthetic cases in §7.5
def test_stated_term_wins_over_a_date_outside_its_window_and_goes_to_review():
    r = deadline_term("Fall 2027", 12, 1, 2025, "fall", OCT11)
    assert (r.valid_for_term, r.term_basis, r.stale) == ("Fall 2027", "stated", True)
    assert r.deadline_date == date(2025, 12, 1)
    assert r.review == ("term_date_mismatch",)


def test_stated_term_with_a_date_without_year_stays_in_its_window():
    r = deadline_term("Fall 2027", 1, 2, None, "fall", date(2027, 2, 10))
    assert (r.valid_for_term, r.term_basis, r.deadline_date, r.stale) == (
        "Fall 2027", "stated", date(2027, 1, 2), True)
    assert r.review == ()


def test_stated_spring_term_without_year_on_the_date():
    r = deadline_term("Spring 2028", 9, 15, None, "fall;spring", OCT11)
    assert (r.deadline_date, r.stale) == (date(2027, 9, 15), False)


def test_summer_stated_date_without_year_goes_to_review():
    r = deadline_term("Summer 2027", 3, 1, None, "fall;spring;summer", OCT11)
    assert (r.valid_for_term, r.term_basis, r.deadline_date) == ("Summer 2027", "stated", date(2027, 3, 1))
    assert r.review == ("summer_date_unverified",)


def test_summer_stated_with_a_full_date_is_not_checked():
    r = deadline_term("Summer 2027", 3, 1, 2027, "fall;spring;summer", OCT11)
    assert (r.valid_for_term, r.term_basis, r.review) == ("Summer 2027", "stated", ())


def test_academic_year_on_a_full_dated_deadline_uses_the_fall_window():
    # BU pg-0026: "2026-2027" names the application cycle, so October 2026 is for Fall 2027
    r = deadline_term("2026-2027", 10, 15, 2026, "fall", OCT11)
    assert (r.valid_for_term, r.term_basis, r.review) == ("Fall 2027", "inferred_from_date", ("term_inferred",))
    assert deadline_term("2026-2027", 3, 15, 2027, "fall", OCT11).valid_for_term == "Fall 2027"


def test_academic_year_on_a_deadline_is_unknown_unless_fall_only():
    r = deadline_term("2026-27", 10, 15, 2026, "fall;spring", OCT11)
    assert (r.valid_for_term, r.review) == (TERM_UNKNOWN, ("term_unknown",))


@pytest.mark.parametrize("month,day", [(1, 2), (None, None)])
def test_academic_year_on_a_deadline_without_a_full_date_is_unknown(month, day):
    r = deadline_term("2026-27", month, day, None, "fall", OCT11)
    assert (r.valid_for_term, r.review) == (TERM_UNKNOWN, ("term_unknown",))


@pytest.mark.parametrize("written", ["2026-27", "AY 2026-2027"])
def test_academic_year_on_tuition_leaves_the_term_empty(written):
    r = tuition_term(written, "fall;spring")
    assert (r.valid_for_term, r.term_basis, r.review) == ("", "unknown", ())
    assert tuition_term(written, "fall") == r


def test_other_tuition_wordings_follow_the_undated_rules():
    assert tuition_term("Fall 2027", "fall").valid_for_term == "Fall 2027"
    assert tuition_term(None, "fall").valid_for_term == ""
    assert tuition_term("2026 applications", "fall").valid_for_term == TERM_UNKNOWN


def test_academic_year_on_another_undated_field_is_unknown():
    r = undated_term("2026-27", "fall")
    assert (r.valid_for_term, r.review) == (TERM_UNKNOWN, ("term_unknown",))


def test_no_term_written_never_borrows_the_page_term():
    # the function does not even take terms_mentioned: §7.4 relies on term_as_written alone
    r = deadline_term(None, 11, 1, 2026, "fall;spring", OCT11)
    assert (r.valid_for_term, r.review) == (TERM_UNKNOWN, ("term_unknown", "season_undetermined"))


# §7.2
def test_full_date_with_one_intake_is_inferred():
    r = deadline_term(None, 11, 9, 2026, "fall", OCT11)
    assert (r.valid_for_term, r.term_basis, r.review) == ("Fall 2027", "inferred_from_date", ("term_inferred",))


def test_only_intake_summer_is_not_inferred():
    assert deadline_term(None, 3, 1, 2027, "summer", OCT11).valid_for_term == TERM_UNKNOWN


def test_season_written_as_summer_without_year_is_unknown():
    r = deadline_term("summer session", 3, 1, 2027, "fall;spring;summer", OCT11)
    assert (r.valid_for_term, r.review) == (TERM_UNKNOWN, ("term_unknown", "season_undetermined"))


def test_no_year_and_several_intakes_goes_to_review():
    r = deadline_term(None, 1, 2, None, "fall;spring", OCT11)
    assert (r.valid_for_term, r.review) == (TERM_UNKNOWN, ("term_unknown", "season_undetermined"))
    assert r.deadline_date == date(2027, 1, 2)


def test_recurring_with_one_intake_is_not_reviewed():
    r = deadline_term(None, 1, 2, None, "fall", OCT11)
    assert (r.valid_for_term, r.term_basis, r.review) == ("Fall 2027", "recurring_no_year", ())


def test_date_on_the_retrieval_day_is_not_stale():
    assert deadline_term("Fall 2027", 10, 11, 2026, "fall", OCT11).stale is False
    assert deadline_term("Fall 2027", 10, 10, 2026, "fall", OCT11).stale is True


def test_rolling_with_no_date():
    r = deadline_term("Fall 2027", None, None, None, "fall", OCT11)
    assert (r.valid_for_term, r.term_basis, r.deadline_date, r.stale) == ("Fall 2027", "stated", None, False)
    assert deadline_term(None, None, None, None, "fall", OCT11).valid_for_term == TERM_UNKNOWN


def test_undated_field_without_a_term_stays_empty_and_unreviewed():
    r = undated_term(None, "fall;spring")
    assert (r.valid_for_term, r.term_basis, r.review) == ("", "unknown", ())


def test_undated_field_with_a_stated_term():
    assert undated_term("Fall 2027", "fall").valid_for_term == "Fall 2027"


def test_undated_field_with_a_season_and_no_date_is_unknown():
    r = undated_term("for the fall semester", "fall")
    assert (r.valid_for_term, r.review) == (TERM_UNKNOWN, ("term_unknown",))


def test_invalid_full_date_is_caught_earlier_not_here():
    with pytest.raises(ValueError):
        deadline_term("Fall 2027", 2, 30, 2027, "fall", OCT11)
