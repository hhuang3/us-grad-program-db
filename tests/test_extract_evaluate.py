"""docs/spec/09_gold_set.md §1, §5: scoring extraction against the gold set."""

import pytest

from gradprog.extract.evaluate import changed_pages, evaluate, normalize_value, render_report


def gold(field="credits_required", value="36", status="found", term="", by="Noah", program="p1", row=1, **over):
    base = {"row_id": f"{program}:{field}:{row}", "program_id": program, "field": field, "value": value,
            "value_status": status, "valid_for_term": term, "deadline_type": "", "is_rolling": "", "flags": "",
            "annotated_by": by, "snapshot_ids": "snap-1-pg-0001;snap-2-pg-0002"}
    return {**base, **over}


def seen(field="credits_required", value=36, status="found", term="", program="p1", page="pg-0001", **over):
    base = {"program_id": program, "page_id": page, "field": field, "value": value, "value_status": status,
            "valid_for_term": term, "conflict_type": [], "review_reasons": [], "stale": False, "confidence": 0.95}
    return {**base, **over}


def date(day, kind="application"):
    return {"deadline_date": day, "deadline_type": kind, "is_rolling": False}


def gold_date(day, kind="application", term="Fall 2027", **over):
    return gold("deadline", day, term=term, deadline_type=kind, **over)


def total(result, group="independent"):
    return result["groups"][group]["total"]


@pytest.mark.parametrize("field,value,expected", [
    ("tuition_year", "2026/27", "2026-2027"), ("tuition_year", "2026–2027", "2026-2027"),
    ("tuition_year", "2026-27", "2026-2027"), ("tuition_amount_usd", "86716", 86716.0),
    ("toefl_min_new_scale", 5, 5.0), ("gre_policy", "Optional ", "optional"),
])
def test_values_are_compared_in_one_form(field, value, expected):
    assert normalize_value(field, value) == expected


def test_a_matching_value_counts_once_across_pages():
    t = total(evaluate([gold()], [seen(), seen(page="pg-0002")]))
    assert (t["extracted_values"], t["correct_values"], t["gold_values"], t["missed_values"]) == (1, 1, 1, 0)


def test_a_wrong_value_lowers_accuracy_and_counts_as_missed():
    t = total(evaluate([gold()], [seen(value=30)]))
    assert (t["extracted_values"], t["correct_values"], t["missed_values"]) == (1, 0, 1)


def test_extraction_failed_is_a_miss():
    t = total(evaluate([gold()], [seen(value=None, status="extraction_failed")]))
    assert (t["extracted_values"], t["missed_values"]) == (0, 1)


def test_no_value_status_takes_the_most_informative_page():
    rows = [seen(value=None, status="not_mentioned"), seen(value=None, status="referenced_elsewhere", page="pg-0002")]
    t = total(evaluate([gold(value="", status="referenced_elsewhere")], rows))
    assert (t["no_value_total"], t["no_value_correct"], t["false_positives"]) == (1, 1, 0)


def test_failure_ranks_below_not_mentioned():
    rows = [seen(value=None, status="extraction_failed"), seen(value=None, status="not_mentioned", page="pg-0002")]
    t = total(evaluate([gold(value="", status="not_mentioned")], rows))
    assert t["no_value_correct"] == 1


def test_found_against_a_no_value_answer_is_a_false_positive_and_a_wrong_value():
    t = total(evaluate([gold(value="", status="not_mentioned")], [seen()]))
    assert (t["false_positives"], t["no_value_correct"], t["extracted_values"], t["correct_values"]) == (1, 0, 1, 0)


def test_deadlines_match_on_date_and_type_only():
    rows = [seen("deadline", {**date("2027-01-02"), "round_name": "R1", "applicant_scope": "all"}, term="Fall 2027"),
            seen("deadline", date("2027-01-02", "deposit"), term="Fall 2027")]
    t = total(evaluate([gold_date("2027-01-02")], rows))
    assert (t["correct_values"], t["extracted_values"], t["missed_values"]) == (1, 2, 0)


def test_rolling_without_a_date_is_ignored_when_the_answer_says_rolling():
    rolling = seen("deadline", {"deadline_date": None, "deadline_type": "application", "is_rolling": True})
    rows = [rolling, seen("deadline", date("2027-01-02"), term="Fall 2027")]
    assert total(evaluate([gold_date("2027-01-02", is_rolling="true")], rows))["extracted_values"] == 1
    assert total(evaluate([gold_date("2027-01-02", is_rolling="false")], rows))["extracted_values"] == 2


def test_term_is_right_only_when_every_matching_row_agrees():
    rows = [seen("deadline", date("2027-01-02"), term="Fall 2027"),
            seen("deadline", date("2027-01-02"), term="Fall 2026", page="pg-0002")]
    t = total(evaluate([gold_date("2027-01-02")], rows))
    assert (t["term_total"], t["term_correct"]) == (1, 0)


def test_undated_field_with_a_term_where_the_answer_has_none_is_a_term_error():
    t = total(evaluate([gold()], [seen(term="Fall 2026")]))
    assert (t["term_total"], t["term_correct"]) == (1, 0)


def test_contaminated_rows_are_left_out_by_default_and_counted_on_request():
    row = seen(conflict_type=["cross_program_contamination"])
    assert total(evaluate([gold()], [row]))["missed_values"] == 1
    assert total(evaluate([gold()], [row], include_flagged=True))["missed_values"] == 0


def test_only_gold_pages_are_scored():
    t = total(evaluate([gold()], [seen(value=30, page="pg-0999")]))
    assert t["extracted_values"] == 0


def test_groups_stay_apart():
    result = evaluate([gold(), gold(by="Noah+Claude", program="p2", snapshot_ids="snap-1-pg-0001")],
                      [seen(), seen(program="p2", value=1)])
    assert total(result, "independent")["correct_values"] == 1
    assert total(result, "assisted")["correct_values"] == 0


def test_excluded_values_are_not_scored():
    rules = [{"reason": "page changed", "gold_rows": ["p1:deadline:1"],
              "observed": [{"program_id": "p1", "field": "deadline", "date": "2026-12-15"}]}]
    rows = [seen("deadline", date("2026-12-15"), term="Fall 2027")]
    t = total(evaluate([gold_date("2026-12-01")], rows, exclusions=rules))
    assert (t["gold_values"], t["extracted_values"], t["missed_values"]) == (0, 0, 0)


def test_review_recall_counts_gold_rows_and_needs_the_matching_signal():
    answers = [gold(value="90", row=1, flags="contradictory"), gold(value="95", row=2, flags="contradictory"),
               gold(value="80", row=3, flags="contradictory")]
    rows = [seen(value=90, conflict_type=["in_page_contradiction"], review_reasons=["conflict:in_page_contradiction"]),
            seen(value=95, review_reasons=["term_inferred"])]
    recall = evaluate(answers, rows)["groups"]["independent"]["review_recall"]["contradictory"]
    assert recall == {"total": 3, "in_review": 2, "with_signal": 1}


def test_review_recall_for_stale_uses_the_stale_mark():
    recall = evaluate([gold_date("2026-08-15", term="Fall 2026", flags="inferred_term;stale")],
                      [seen("deadline", date("2026-08-15"), term="Fall 2026", stale=True)])
    assert recall["groups"]["independent"]["review_recall"]["stale"] == {"total": 1, "in_review": 0, "with_signal": 1}


def test_confidence_buckets_record_right_and_wrong():
    rows = [seen(confidence=0.95), seen(value=30, confidence=0.5), seen(value=31, confidence=None)]
    buckets = evaluate([gold()], rows)["groups"]["independent"]["confidence"]
    assert buckets[">=0.9"] == {"right": 1, "wrong": 0}
    assert buckets["<0.7"] == {"right": 0, "wrong": 1}
    assert buckets["none"] == {"right": 0, "wrong": 1}


def test_differences_name_each_value_without_page_text():
    result = evaluate([gold()], [seen(value=30, evidence_text="secret page text")])
    kinds = {d["kind"] for d in result["differences"]}
    assert kinds == {"missed", "wrong_value"}
    assert "secret" not in str(result)


def test_report_shows_both_groups_and_the_small_sample_warning():
    text = render_report(evaluate([gold()], [seen()]))
    assert "独立标注" in text and "Claude 协助" in text


def test_changed_pages_compares_the_text_behind_both_snapshots():
    rows = [seen(snapshot_id="snap-9-pg-0001"), seen(page="pg-0002", snapshot_id="snap-8-pg-0002")]
    sha = {"snap-1-pg-0001": "a", "snap-9-pg-0001": "b", "snap-2-pg-0002": "c", "snap-8-pg-0002": "c"}
    assert changed_pages([gold()], rows, sha) == ["pg-0001"]


def test_run_evaluation_keeps_values_out_of_the_committed_file(tmp_path):
    import csv

    import pandas as pd

    from gradprog.extract.evaluate import run_evaluation

    answer = gold(value="36")
    path = tmp_path / "gold.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, answer)
        writer.writeheader()
        writer.writerow(answer)
    rules = tmp_path / "rules.yaml"
    rules.write_text("[]\n", encoding="utf-8")
    view = [seen(value=31, snapshot_id="snap-1-pg-0001", prompt_version=4, extract_rules_version=5)]
    index = pd.DataFrame({"snapshot_id": ["snap-1-pg-0001"], "norm_sha256": ["a"]})
    report = run_evaluation(path, view, index, "t", tmp_path, tmp_path, rules)
    assert "独立标注" in report
    assert "31" not in (tmp_path / "eval_t.json").read_text(encoding="utf-8")
    assert "31" in (tmp_path / "eval_t_differences.csv").read_text(encoding="utf-8")
