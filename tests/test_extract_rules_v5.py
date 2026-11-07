"""docs/spec/08_extraction.md §2.1, §3.3a, §6, §7.1, §8.2: rules added on 2026-11-08."""

from gradprog.extract.conflicts import cross_page_conflicts, in_page_conflicts
from gradprog.extract.fields import COMMON, GROUPS
from gradprog.extract.observations import build_rows
from gradprog.util import awake

CALL = {"page_id": "pg-0001", "program_id": "alpha-ms-datascience", "snapshot_id": "snap-1", "owner_level": "program",
        "final_url": "https://a.edu", "retrieved_at": "2026-10-11T00:00:00Z", "classification": "unchanged",
        "intake_terms": "fall", "page_type": "program_home"}
META = {"call_id": "call-1", "model_name": "m", "prompt_version": 1, "schema_version": 1,
        "extracted_at": "2026-11-06T00:00:00Z"}
PAGE = """The MS degree requires 32-36 hours (8 or 9 courses) beyond the prerequisites.
The degree requires 30 credits.
We do not charge an application fee.
Fee waived for alumni of the program.
GRE – Optional Beginning Fall 2025
Applicants may choose to submit GRE scores.
The GMAT is optional for Fall 2026.
Fall 2027 applications close December 1, 2026."""


def entry(group, evidence, **over):
    base = dict.fromkeys({**COMMON, **GROUPS[group]})
    base.update(value_status="found", evidence_text=evidence, confidence=0.9, excluded_by_scope_note=False, notes="")
    base.update(over)
    return base


def rows_of(**groups):
    output = {"terms_mentioned": [], "audience": "applicants", **{k: [] for k in GROUPS}, **groups}
    return build_rows(CALL, output, PAGE, META)


def field(rows, name):
    return [r for r in rows if r["field"] == name]


RANGE = "The MS degree requires 32-36 hours (8 or 9 courses) beyond the prerequisites."


def test_credit_range_given_as_two_entries_becomes_its_lower_bound():
    rows = field(rows_of(credits_required=[entry("credits_required", RANGE, value=32),
                                           entry("credits_required", RANGE, value=36)]), "credits_required")
    assert [r["value"] for r in rows] == [32]
    assert rows[0]["conflict_type"] == [] and rows[0]["review_from_rules"] == []
    assert rows[0]["extras"]["notes"] == "32-36 hours"


def test_credit_range_given_as_its_upper_bound_still_records_the_lower():
    rows = field(rows_of(credits_required=[entry("credits_required", RANGE, value=36)]), "credits_required")
    assert [r["value"] for r in rows] == [32]


def test_a_single_credit_count_is_left_alone():
    rows = field(rows_of(credits_required=[entry("credits_required", "The degree requires 30 credits.", value=30)]),
                 "credits_required")
    assert [r["value"] for r in rows] == [30] and "notes" not in rows[0]["extras"]


def test_zero_fee_needs_evidence_that_says_no_fee_is_charged():
    rows = field(rows_of(app_fee_usd=[entry("app_fee_usd", "We do not charge an application fee.", value=0)]), "app_fee_usd")
    assert rows[0]["value_status"] == "found" and rows[0]["value"] == 0


def test_zero_fee_with_only_a_conditional_waiver_is_rejected():
    rows = field(rows_of(app_fee_usd=[entry("app_fee_usd", "Fee waived for alumni of the program.", value=0)]), "app_fee_usd")
    assert rows[0]["value_status"] == "extraction_failed"
    assert rows[0]["review_from_rules"] == ["evidence_failed:value_not_in_evidence"]


def test_a_start_term_goes_to_effective_from_even_when_the_wording_is_outside_the_evidence():
    rows = rows_of(gre_policy=[entry("gre_policy", "Applicants may choose to submit GRE scores.", value="optional",
                                     term_as_written="Fall 2025")])
    row = field(rows, "gre_policy")[0]
    assert row["valid_for_term"] == "" and row["term_basis"] == "unknown" and row["review_from_rules"] == []
    assert row["extras"]["effective_from"] == "Fall 2025"


def test_a_plain_term_stays_valid_for_term():
    rows = rows_of(gmat_policy=[entry("gmat_policy", "The GMAT is optional for Fall 2026.", value="optional",
                                      term_as_written="Fall 2026")])
    row = field(rows, "gmat_policy")[0]
    assert row["valid_for_term"] == "Fall 2026" and "effective_from" not in row["extras"]


def test_a_term_with_no_year_is_not_a_start_term():
    rows = rows_of(gre_policy=[entry("gre_policy", "Applicants may choose to submit GRE scores.", value="optional",
                                     term_as_written="beginning fall")])
    row = field(rows, "gre_policy")[0]
    assert row["valid_for_term"] == "term_unknown" and "effective_from" not in row["extras"]


def test_deadlines_never_get_effective_from():
    rows = rows_of(deadlines=[entry("deadlines", "Fall 2027 applications close December 1, 2026.", deadline_month=12,
                                    deadline_day=1, deadline_year=2026, term_as_written="Fall 2027")])
    assert "effective_from" not in field(rows, "deadline")[0]["extras"]


def _deadline(date, kind, page):
    return {"field": "deadline", "value": {"deadline_date": date, "deadline_type": kind, "is_rolling": False},
            "value_status": "found", "valid_for_term": "Fall 2027", "group_key": f"{kind}|all|", "page_id": page,
            "owner_level": "program", "program_id": "p", "observation_id": f"{date}-{page}",
            "excluded_by_scope_note": False, "other_program_mentioned": None}


def test_other_type_deadlines_are_not_compared_on_one_page():
    rows = [_deadline("2027-06-01", "other", "pg-1"), _deadline("2027-08-01", "other", "pg-1")]
    assert all(v == [] for v in in_page_conflicts(rows).values())


def test_other_type_deadlines_are_not_compared_across_pages():
    assert cross_page_conflicts([_deadline("2027-06-01", "other", "pg-1"), _deadline("2027-08-01", "other", "pg-2")]) == {}


def test_application_deadlines_are_still_compared():
    rows = [_deadline("2027-06-01", "application", "pg-1"), _deadline("2027-08-01", "application", "pg-1")]
    assert all(v == ["in_page_contradiction"] for v in in_page_conflicts(rows).values())


def test_keep_awake_watches_this_process(monkeypatch):
    calls = []

    class Fake:
        def terminate(self):
            calls.append("stop")

    monkeypatch.setattr(awake.shutil, "which", lambda name: "/usr/bin/caffeinate")
    monkeypatch.setattr(awake.subprocess, "Popen", lambda cmd, **kw: calls.append(cmd) or Fake())
    monkeypatch.setattr(awake.os, "getpid", lambda: 42)
    with awake.keep_awake():
        assert calls == [["/usr/bin/caffeinate", "-i", "-w", "42"]]
    assert calls[-1] == "stop"


def test_keep_awake_warns_and_goes_on_without_caffeinate(monkeypatch, capsys):
    monkeypatch.setattr(awake.shutil, "which", lambda name: None)
    with awake.keep_awake():
        pass
    assert "caffeinate" in capsys.readouterr().err


def test_keep_awake_warns_and_goes_on_when_caffeinate_fails_to_start(monkeypatch, capsys):
    def fail(cmd, **kw):
        raise OSError("no")

    monkeypatch.setattr(awake.shutil, "which", lambda name: "/usr/bin/caffeinate")
    monkeypatch.setattr(awake.subprocess, "Popen", fail)
    with awake.keep_awake():
        pass
    assert "caffeinate" in capsys.readouterr().err
