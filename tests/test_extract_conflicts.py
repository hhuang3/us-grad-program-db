"""docs/spec/08_extraction.md §3, §8, §10: conflicts, derived values, review reasons."""

import pytest

from gradprog.extract.conflicts import cross_page_conflicts, in_page_conflicts, suggestions
from gradprog.extract.derive import cip_source, stem_status, tuition_total
from gradprog.extract.review import coverage_gap, only_stale_deadlines, review_reasons

_n = [0]


def row(field="toefl_min_legacy", value=100, page="pg-1", level="program", term="", **over):
    _n[0] += 1
    base = {"observation_id": f"obs-{_n[0]}", "program_id": "p", "page_id": page, "owner_level": level, "field": field,
            "value": value, "value_status": "found", "valid_for_term": term, "group_key": "", "conflict_type": [],
            "excluded_by_scope_note": False, "other_program_mentioned": None, "reference_target": None,
            "review_from_rules": [], "confidence": 0.9, "snapshot_classification": "unchanged",
            "audience": "applicants", "stale": False}
    base.update(over)
    return base


def deadline(date, page="pg-1", level="program", term="Fall 2027", key="application|all|Round 1", **over):
    return row("deadline", {"deadline_date": date, "is_rolling": False}, page, level, term, group_key=key, **over)


def types(rows):
    found = in_page_conflicts(rows)
    return [found[id(r)] for r in rows]


# §8.3
def test_two_values_on_one_page_conflict():
    assert types([row(value=90), row(value=95)]) == [["in_page_contradiction"]] * 2


def test_same_value_twice_is_no_conflict():
    assert types([row(value=90), row(value=90.0)]) == [[], []]


def test_different_terms_are_no_conflict():
    assert types([row(value=90, term="Fall 2026"), row(value=95, term="Fall 2027")]) == [[], []]


def test_empty_term_compares_only_with_empty_term():
    assert types([row(value=90, term=""), row(value=95, term="Fall 2027")]) == [[], []]


def test_term_unknown_is_not_compared():
    assert types([row(value=90, term="term_unknown"), row(value=95, term="term_unknown")]) == [[], []]


def test_non_found_rows_are_not_compared():
    assert types([row(value=None, value_status="not_mentioned"), row(value=95)]) == [[], []]


def test_deadlines_in_different_groups_coexist():
    a = deadline("2026-12-01", key="application|all|Round 1")
    b = deadline("2027-02-01", key="application|all|Round 2")
    c = deadline("2027-03-01", key="deposit|all|Round 1")
    assert types([a, b, c]) == [[], [], []]


def test_same_deadline_group_on_one_page_is_in_page_contradiction():
    assert types([deadline("2026-12-01"), deadline("2026-12-15")]) == [["in_page_contradiction"]] * 2


def test_tuition_compares_within_its_basis_and_year():
    a = row("tuition_amount_usd", 1000, group_key="per_credit|2026-27")
    b = row("tuition_amount_usd", 30000, group_key="per_year|2026-27")
    assert types([a, b]) == [[], []]
    assert types([a, row("tuition_amount_usd", 1100, group_key="per_credit|2026-27")])[0] == ["in_page_contradiction"]


# §8.4
def test_other_program_name_marks_contamination():
    assert types([row(other_program_mentioned="MBA")]) == [["cross_program_contamination"]]


def test_scope_note_exclusion_marks_contamination_and_skips_comparison():
    rows = [row(value=90, excluded_by_scope_note=True), row(value=95)]
    assert types(rows) == [["cross_program_contamination"], []]


def test_cross_page_difference_alone_is_not_contamination():
    rows = [row(value=90, page="pg-1"), row(value=95, page="pg-2")]
    assert all("cross_program_contamination" not in v for v in cross_page_conflicts(rows).values())


# §8.1
def test_levels_differ_is_level_mismatch_and_suggests_the_specific_page():
    a, b = row(value=100, level="program"), row(value=90, page="pg-2", level="graduate_school")
    assert cross_page_conflicts([a, b]) == {a["observation_id"]: ["level_mismatch"], b["observation_id"]: ["level_mismatch"]}
    assert suggestions([a, b])[a["observation_id"]] == a["observation_id"]


def test_same_level_difference_has_no_suggestion():
    a, b = row(value=100), row(value=90, page="pg-2")
    assert cross_page_conflicts([a, b])[a["observation_id"]] == ["level_mismatch"]
    assert suggestions([a, b])[a["observation_id"]] is None


def test_below_graduate_school_minimum_replaces_level_mismatch_and_has_no_suggestion():
    a, b = row(value=79, level="program"), row(value=80, page="pg-2", level="graduate_school")
    out = cross_page_conflicts([a, b])
    assert out[a["observation_id"]] == ["below_graduate_school_minimum"]
    assert out[b["observation_id"]] == ["below_graduate_school_minimum"]
    assert suggestions([a, b])[a["observation_id"]] is None


def test_enums_are_not_compared_against_a_minimum():
    a = row("gre_policy", "optional", level="program")
    b = row("gre_policy", "required", page="pg-2", level="graduate_school")
    assert cross_page_conflicts([a, b])[a["observation_id"]] == ["level_mismatch"]


def test_ielts_uses_the_minimum_rule():
    a = row("ielts_min_overall", 6.0, level="department")
    b = row("ielts_min_overall", 6.5, page="pg-2", level="graduate_school")
    assert cross_page_conflicts([a, b])[a["observation_id"]] == ["below_graduate_school_minimum"]


def test_contaminated_page_is_not_suggested():
    a = row(value=100, other_program_mentioned="MBA")
    b = row(value=90, page="pg-2", level="graduate_school")
    assert suggestions([a, b])[a["observation_id"]] == b["observation_id"]


def test_all_pages_contaminated_gives_no_suggestion():
    a = row(value=100, other_program_mentioned="MBA")
    b = row(value=90, page="pg-2", level="graduate_school", other_program_mentioned="MiM")
    assert suggestions([a, b])[a["observation_id"]] is None


def test_programs_are_not_compared_with_each_other():
    assert cross_page_conflicts([row(value=100), row(value=90, page="pg-2", program_id="q")]) == {}


# §8.2
def test_same_group_on_two_pages_is_deadline_mismatch():
    a, b = deadline("2026-12-01"), deadline("2026-12-15", page="pg-2")
    assert cross_page_conflicts([a, b])[a["observation_id"]] == ["deadline_mismatch"]


def test_page_with_rows_in_other_group_is_no_mismatch():
    a, b = deadline("2026-12-01"), deadline("2027-01-15", page="pg-2", key="application|all|Priority")
    assert cross_page_conflicts([a, b]) == {}


# §3.1, §3.2
@pytest.mark.parametrize("args,kw,expected", [
    (("per_credit", 1000), {"credits": 30}, (30000, "per_credit x 30 credits")),
    (("per_credit", 1000), {}, (None, "")),
    (("per_term", 20000), {}, (None, "")),
    (("per_term", 20000), {"terms": 3}, (60000, "per_term x 3 terms")),
    (("per_year", 40000), {"years": 2}, (80000, "per_year x 2 years")),
    (("program_total", 70000), {}, (70000, "program_total")),
    (("program_total", None), {}, (None, "")),
])
def test_tuition_total(args, kw, expected):
    assert tuition_total(*args, **kw) == expected


@pytest.mark.parametrize("context,page_type,source", [
    ("stem_list", "faq", "school_stem_page"), ("other", "isso_stem_list", "school_stem_page"),
    ("i20_statement", "faq", "i20_statement"), ("program_intro", "program_home", "program_page"),
    ("other", "faq", "program_page"), (None, "faq", "program_page"),
])
def test_cip_source(context, page_type, source):
    assert cip_source(context, page_type) == source


def test_jhu_economics_cip_from_the_program_page_is_confirmed_by_school(stem_ref):
    assert stem_status("45.0603", cip_source("program_intro", "program_home"), stem_ref) == "confirmed_by_school"


# §10
def reasons(*rows, threshold=0.7, urls=None):
    return review_reasons(list(rows), threshold, urls or {})


def test_clean_row_has_no_reasons():
    r = row()
    assert reasons(r) == {r["observation_id"]: []}


def test_reasons_from_earlier_rules_and_conflicts_are_kept():
    r = row(review_from_rules=["term_date_mismatch"], conflict_type=["level_mismatch"])
    assert reasons(r)[r["observation_id"]] == ["conflict:level_mismatch", "term_date_mismatch"]


def test_low_confidence_uses_the_threshold():
    a, b = row(confidence=0.69), row(confidence=0.7, field="gre_policy", value="optional")
    out = reasons(a, b)
    assert out[a["observation_id"]] == ["low_confidence"] and out[b["observation_id"]] == []


def test_suspected_redesign_and_doubtful_audience():
    r = row(snapshot_classification="suspected_redesign", audience="current_students")
    assert reasons(r)[r["observation_id"]] == ["audience_doubtful", "suspected_redesign"]


def test_only_stale_deadlines():
    a, b = deadline("2025-12-01", stale=True), deadline("2025-12-02", stale=True, key="k")
    assert only_stale_deadlines([a, b])
    assert "only_stale_deadlines" in reasons(a, b)[a["observation_id"]]
    assert not only_stale_deadlines([a, deadline("2027-01-01", key="j")])


def test_undated_rolling_alone_is_not_only_stale():
    assert not only_stale_deadlines([row("deadline", {"deadline_date": None, "is_rolling": True})])


def ref(target):
    return row(value=None, value_status="referenced_elsewhere", reference_target=target)


def test_reference_to_a_registered_url_is_covered():
    assert not coverage_gap(ref("https://a.edu/req/"), [], {"a.edu/req"})


def test_reference_to_an_unregistered_url_is_a_gap():
    assert coverage_gap(ref("https://a.edu/other"), [], {"a.edu/req"})


def test_link_text_needs_a_value_on_another_page():
    r = ref("Graduate School requirements")
    assert coverage_gap(r, [r], set())
    assert not coverage_gap(r, [r, row(page="pg-2")], set())


def test_gap_reaches_the_review_reasons():
    r = ref("Graduate School requirements")
    assert reasons(r)[r["observation_id"]] == ["coverage_gap"]
