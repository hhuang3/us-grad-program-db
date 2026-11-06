"""docs/spec/08_extraction.md §2, §4, §4.1, §8, §9, §11: selection, rows, storage and runs with a fake LLM."""

import json
from datetime import date

import pytest

from gradprog.extract.fields import COMMON, GROUPS, NUMBER_KEYS, OWN_ARRAY_KEYS, SIMPLE_KEYS, build_schema, schema_errors
from gradprog.extract.llm import LLMCallFailed, LLMResult, LLMSetupError, cost_usd
from gradprog.extract.observations import build_rows
from gradprog.extract.pipeline import (
    estimate_usd, key_expiry_warning, make_plan, rebuild_view, render_summary, replay, run_extract, summarize,
)
from gradprog.extract.prompt import load_settings
from gradprog.extract.store import ExtractionStore
from gradprog.snapshot.store import INDEX_COLUMNS, SnapshotStore

PAGE = """Fall 2027 applications close December 1, 2026.
Spring: January 2 for international applicants.
Applicants must have a minimum TOEFL of 90.
English scores must be submitted.
See the Graduate School requirements page for English rules.
Tuition is $1,250 per credit for 2026-27. CIP code 30.7001.
For MBA students the GRE is required."""
CALL = {"page_id": "pg-0001", "program_id": "alpha-ms-datascience", "snapshot_id": "snap-1", "owner_level": "program",
        "final_url": "https://a.edu", "retrieved_at": "2026-10-11T00:00:00Z", "classification": "unchanged",
        "intake_terms": "fall", "page_type": "program_home"}
META = {"call_id": "call-1", "model_name": "m", "prompt_version": 1, "schema_version": 1,
        "extracted_at": "2026-11-06T00:00:00Z"}


def entry(group, evidence="", **over):
    base = dict.fromkeys({**COMMON, **GROUPS[group]})
    base.update(value_status="found", evidence_text=evidence, confidence=0.9, excluded_by_scope_note=False)
    base.update(over)
    return base


def output(**over):
    base = {"terms_mentioned": [], "audience": "applicants", **{k: [] for k in GROUPS}}
    base.update(over)
    return base


def rows_of(**over):
    return build_rows(CALL, output(**over), PAGE, META)


def by_field(rows, field):
    return [r for r in rows if r["field"] == field]


# §4.1: empty arrays and the two no-value statuses
def test_empty_arrays_become_not_mentioned_rows_for_every_field():
    rows = rows_of()
    assert {r["value_status"] for r in rows} == {"not_mentioned"}
    assert len(rows) == 16


def test_mentioned_without_a_value_is_not_written_as_not_mentioned():
    e = entry("toefl_total", "English scores must be submitted", value_status="mentioned_without_value")
    rows = rows_of(toefl_total=[e])
    assert [r["value_status"] for r in by_field(rows, "toefl_min_legacy")] == ["mentioned_without_value"]
    assert by_field(rows, "toefl_min_legacy")[0]["value"] is None
    assert by_field(rows, "toefl_min_legacy")[0]["evidence_text"] == "English scores must be submitted"


def test_referenced_elsewhere_keeps_its_target():
    e = entry("toefl_total", "See the Graduate School requirements page", value_status="referenced_elsewhere",
              reference_target="Graduate School requirements page")
    row = by_field(rows_of(toefl_total=[e]), "toefl_min_new_scale")[0]
    assert (row["value_status"], row["reference_target"]) == ("referenced_elsewhere", "Graduate School requirements page")


# §6: failed checks
def test_failed_evidence_voids_the_entry_and_records_the_reason():
    e = entry("gre_policy", "made up text", value="required")
    row = by_field(rows_of(gre_policy=[e]), "gre_policy")[0]
    assert (row["value_status"], row["value"], row["evidence_text"]) == ("extraction_failed", None, None)
    assert row["review_from_rules"] == ["evidence_failed:evidence_not_verbatim"]


# §9
def test_toefl_goes_to_the_field_of_its_scale():
    rows = rows_of(toefl_total=[entry("toefl_total", "a minimum TOEFL of 90", value=90)])
    assert by_field(rows, "toefl_min_legacy")[0]["value"] == 90
    assert by_field(rows, "toefl_min_new_scale")[0]["value_status"] == "not_mentioned"
    assert by_field(rows, "toefl_scale_on_page")[0]["value"] == "legacy"


def test_both_scales_write_both_fields():
    page = "79 (old scale) or 4.5 (new scale)"
    out = output(toefl_total=[entry("toefl_total", "79 (old scale)", value=79), entry("toefl_total", "4.5 (new scale)", value=4.5)])
    rows = build_rows(CALL, out, page, META)
    assert by_field(rows, "toefl_min_legacy")[0]["value"] == 79
    assert by_field(rows, "toefl_min_new_scale")[0]["value"] == 4.5
    assert by_field(rows, "toefl_scale_on_page")[0]["value"] == "both"


def test_written_scale_contradicting_the_number_is_a_contradiction():
    page = "90 on the new TOEFL"
    rows = build_rows(CALL, output(toefl_total=[entry("toefl_total", page, value=90)]), page, META)
    assert by_field(rows, "toefl_min_legacy")[0]["conflict_type"] == ["in_page_contradiction"]


def test_unrecognizable_toefl_fails():
    page = "TOEFL score of 0"
    rows = build_rows(CALL, output(toefl_total=[entry("toefl_total", page, value=0)]), page, META)
    assert "toefl_scale_unrecognized" in by_field(rows, "toefl_min_legacy")[0]["review_from_rules"]


def test_conditional_range_is_kept_aside_and_not_the_minimum():
    e = entry("toefl_total", "a minimum TOEFL of 90", value=90, conditional_admission_range="70-89")
    row = by_field(rows_of(toefl_total=[e]), "toefl_min_legacy")[0]
    assert (row["value"], row["extras"]) == (90, {"conditional_admission_range": "70-89"})


# §4.1, §7
def test_deadline_date_is_completed_by_code():
    e = entry("deadlines", "January 2 for international", deadline_month=1, deadline_day=2,
              applicant_scope="international", term_as_written="fall")
    row = by_field(rows_of(deadlines=[e]), "deadline")[0]
    assert row["value"]["deadline_date"] == "2027-01-02"
    assert (row["valid_for_term"], row["term_basis"]) == ("Fall 2027", "recurring_no_year")
    assert row["group_key"] == "application|international|"


def test_deadline_defaults_follow_the_gold_set_rules():
    e = entry("deadlines", "close December 1, 2026", deadline_month=12, deadline_day=1, deadline_year=2026,
              term_as_written="Fall 2027")
    value = by_field(rows_of(deadlines=[e]), "deadline")[0]["value"]
    assert (value["applicant_scope"], value["is_rolling"], value["round_name"]) == ("all", False, "")


def test_undated_field_without_term_stays_empty():
    e = entry("gre_policy", "the GRE is required", value="required")
    row = by_field(rows_of(gre_policy=[e]), "gre_policy")[0]
    assert (row["valid_for_term"], row["review_from_rules"]) == ("", [])


# §4.1: tuition group
def test_tuition_group_splits_into_three_linked_rows():
    e = entry("tuition", "Tuition is $1,250 per credit for 2026-27", tuition_basis="per_credit", tuition_amount_usd=1250,
              tuition_year="2026-27", includes_fees=False)
    rows = rows_of(tuition=[e])
    group = {r["group_id"] for f in ("tuition_basis", "tuition_amount_usd", "tuition_year") for r in by_field(rows, f)}
    assert len(group) == 1 and "" not in group
    assert by_field(rows, "tuition_amount_usd")[0]["value"] == 1250
    assert by_field(rows, "tuition_amount_usd")[0]["extras"] == {"includes_fees": False}


# §3.1: an amount with no stated basis
def test_tuition_amount_without_a_basis_is_kept_and_reviewed():
    e = entry("tuition", "Tuition is $1,250 per credit for 2026-27", tuition_basis=None, tuition_amount_usd=1250,
              tuition_year=None, includes_fees=False)
    rows = rows_of(tuition=[e])
    amount = by_field(rows, "tuition_amount_usd")[0]
    assert (amount["value_status"], amount["value"]) == ("found", 1250)
    assert amount["review_from_rules"] == ["tuition_basis_missing"]
    basis = by_field(rows, "tuition_basis")[0]
    assert (basis["value_status"], basis["value"], basis["review_from_rules"]) == ("not_mentioned", None, [])
    assert basis["group_id"] == amount["group_id"]


# §7.1: an academic year on tuition goes to tuition_year
def test_academic_year_on_tuition_fills_the_year_and_leaves_the_term_empty():
    e = entry("tuition", "Tuition is $1,250 per credit for 2026-27", tuition_basis="per_credit", tuition_amount_usd=1250,
              tuition_year=None, includes_fees=False, term_as_written="2026-27")
    rows = rows_of(tuition=[e])
    year = by_field(rows, "tuition_year")[0]
    assert (year["value_status"], year["value"]) == ("found", "2026-27")
    for field in ("tuition_basis", "tuition_amount_usd", "tuition_year"):
        row = by_field(rows, field)[0]
        assert (row["valid_for_term"], row["review_from_rules"]) == ("", [])


def test_a_written_tuition_year_is_not_replaced():
    e = entry("tuition", "Tuition is $1,250 per credit for 2026-27", tuition_basis="per_credit", tuition_amount_usd=1250,
              tuition_year="AY26", includes_fees=False, term_as_written="2026-27")
    assert by_field(rows_of(tuition=[e]), "tuition_year")[0]["value"] == "AY26"


# §3.2, §8.4
def test_cip_source_is_derived(stem_ref):
    e = entry("cip_code", "CIP code 30.7001", value="30.7001", cip_context="program_intro")
    row = by_field(build_rows(CALL, output(cip_code=[e]), PAGE, META, stem_ref), "cip_code")[0]
    assert row["derived"]["cip_source"] == "program_page"
    assert "stem_status" in row["derived"]


def test_contamination_signals_land_on_the_row():
    e = entry("gre_policy", "For MBA students the GRE is required", value="required", other_program_mentioned="MBA")
    assert by_field(rows_of(gre_policy=[e]), "gre_policy")[0]["conflict_type"] == ["cross_program_contamination"]


def test_two_toefl_values_on_one_page_conflict():
    page = "TOEFL 90 and TOEFL 95"
    out = output(toefl_total=[entry("toefl_total", "TOEFL 90", value=90), entry("toefl_total", "TOEFL 95", value=95)])
    rows = by_field(build_rows(CALL, out, page, META), "toefl_min_legacy")
    assert [r["conflict_type"] for r in rows] == [["in_page_contradiction"]] * 2


# storage, selection and runs
class FakeLLM:
    """Plays back queued results; raises queued LLMCallFailed. Never touches the network."""

    def __init__(self, *results):
        self.results, self.calls = list(results), []

    def extract(self, system, user, schema, settings):
        self.calls.append(user)
        result = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        if isinstance(result, Exception):
            raise result
        return result


def _wire_value(value, prop):
    if value is not None:
        return value
    return "none" if "enum" in prop else {"string": "", "number": 0, "integer": 0, "boolean": False}[prop["type"]]


def wire(out):
    """An output as the API returns it: three arrays and empty forms instead of None (08 §4.1)."""
    schema = build_schema()["properties"]
    done = {"terms_mentioned": out["terms_mentioned"], "audience": out["audience"], "fields": []}
    for key in OWN_ARRAY_KEYS:
        props = schema[key]["items"]["properties"]
        done[key] = [{k: _wire_value(v, props[k]) for k, v in e.items()} for e in out[key]]
    props = schema["fields"]["items"]["properties"]
    for key in SIMPLE_KEYS:
        for e in out[key]:
            item = {k: _wire_value(None, p) for k, p in props.items() if k != "field"}
            item.update({k: _wire_value(e[k], props[k]) for k in e if k in props})
            item["number_value" if key in NUMBER_KEYS else "text_value"] = _wire_value(
                e["value"], props["number_value" if key in NUMBER_KEYS else "text_value"])
            done["fields"].append({"field": key, **item})
    return done


def ok(out=None, stop="end_turn"):
    return LLMResult(json.dumps(wire(out or output())), stop, "claude-haiku-5-5", "req_1", {"input": 1000, "output": 100})


@pytest.fixture
def env(tmp_path, registry):
    snaps = SnapshotStore(tmp_path / "snapshots")
    store = ExtractionStore(tmp_path / "extraction", tmp_path / "stats")
    return registry, snaps, store, load_settings()


def add_snapshot(snaps, page="pg-0001", ts="2026-10-11T00:00:00Z", cls="unchanged", sha="aaa", text=PAGE):
    sid = f"snap-{ts}-{page}".replace(":", "").replace("-", "")[:30] + page
    row = dict.fromkeys(INDEX_COLUMNS, "")
    row.update(snapshot_id=sid, page_id=page, run_id="r", method="auto", retrieved_at=ts, requested_url="u",
               final_url="https://a.edu", http_status="200", content_type="html", raw_sha256="r", raw_bytes="1",
               normalizer_version="2", norm_sha256=sha, norm_chars=str(len(text)), classification=cls)
    snaps.append_index(row)
    if cls in ("first_capture", "unchanged", "changed", "suspected_redesign"):
        path = snaps.norm_path(page, sid, 2)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return sid


def actions(env, pages=("pg-0001",), **kw):
    registry, snaps, store, settings = env
    return [c.action for c in make_plan(registry, snaps, store, settings, set(pages), **kw)]


def go(env, llm, pages=("pg-0001",), **kw):
    registry, snaps, store, settings = env
    return run_extract(registry, snaps, store, llm, settings, set(pages), **kw)


def test_plan_covers_selected_confirmed_pages_per_program(env):
    registry, snaps, store, settings = env
    plan = make_plan(registry, snaps, store, settings)
    pairs = {(c.page_id, c.program_id) for c in plan}
    assert ("pg-0002", "alpha-ms-datascience") in pairs and ("pg-0002", "alpha-ms-businessanalytics") in pairs
    assert not any(c.page_id == "pg-0004" for c in plan)                     # proposed page
    assert {c.action for c in plan} == {"no_snapshot"}


def test_shared_page_gets_one_call_per_program_with_its_own_scope_note(env):
    registry, snaps, store, settings = env
    add_snapshot(snaps, "pg-0002")
    llm = FakeLLM(ok())
    go(env, llm, ("pg-0002",))
    assert len(llm.calls) == 2
    assert any("use only the business school sections" in u for u in llm.calls)
    assert any("Scope note for this program and page: (none)" in u for u in llm.calls)


def test_first_extraction_uses_the_latest_success_whatever_its_class(env):
    _, snaps, _, _ = env
    add_snapshot(snaps, ts="2026-10-04T00:00:00Z", cls="first_capture", sha="old")
    sid = add_snapshot(snaps, ts="2026-10-11T00:00:00Z", cls="unchanged", sha="new")
    registry, _, store, settings = env
    assert make_plan(registry, snaps, store, settings, {"pg-0001"})[0].snapshot_id == sid


def test_unchanged_text_is_not_extracted_again(env):
    _, snaps, _, _ = env
    add_snapshot(snaps)
    go(env, FakeLLM(ok()))
    assert actions(env) == ["skip"]


def test_changed_text_is_extracted_again(env):
    _, snaps, _, _ = env
    add_snapshot(snaps)
    go(env, FakeLLM(ok()))
    add_snapshot(snaps, ts="2026-10-18T00:00:00Z", cls="changed", sha="bbb")
    assert actions(env) == ["call"]


def test_new_snapshot_with_the_same_text_is_not_extracted_again(env):
    _, snaps, _, _ = env
    add_snapshot(snaps)
    go(env, FakeLLM(ok()))
    add_snapshot(snaps, ts="2026-10-18T00:00:00Z", cls="unchanged")
    assert actions(env) == ["skip"]


def test_a_new_model_extracts_again(env):
    registry, snaps, store, settings = env
    add_snapshot(snaps)
    go(env, FakeLLM(ok()))
    other = {**settings, "model": "claude-sonnet-5-5"}
    assert make_plan(registry, snaps, store, other, {"pg-0001"})[0].action == "call"


def test_failed_fetch_writes_page_unavailable_once_and_keeps_earlier_rows(env):
    registry, snaps, store, settings = env
    add_snapshot(snaps)
    llm = FakeLLM(ok())
    go(env, llm)
    add_snapshot(snaps, ts="2026-10-18T00:00:00Z", cls="unavailable", sha="")
    assert actions(env) == ["unavailable"]
    result = go(env, llm)
    assert result["counts"]["unavailable"] == 1 and len(llm.calls) == 1
    assert actions(env) == ["skip"]
    statuses = {r["value_status"] for r in store.read_observations()}
    assert {"page_unavailable", "not_mentioned"} <= statuses


@pytest.mark.parametrize("failure", [LLMCallFailed("rate_limit"), ok(stop="refusal"), ok(stop="max_tokens")])
def test_failed_call_writes_failed_rows_and_is_retried_next_run(env, failure):
    registry, snaps, store, settings = env
    add_snapshot(snaps)
    go(env, FakeLLM(failure))
    assert {r["value_status"] for r in store.read_observations()} == {"extraction_failed"}
    assert actions(env) == ["call"]


def test_two_failures_in_a_row_go_to_review_and_stop_retrying(env):
    registry, snaps, store, settings = env
    add_snapshot(snaps)
    llm = FakeLLM(LLMCallFailed("boom"))
    go(env, llm)
    go(env, llm)
    assert len(llm.calls) == 2 and actions(env) == ["needs_review"]
    third = go(env, llm)
    assert len(llm.calls) == 2 and third["counts"]["needs_review"] == 1
    last = [r for r in store.read_observations() if r["call_id"] == store.read_records()[-1]["call_id"]]
    assert all("repeated_call_failure" in r["review_from_rules"] for r in last)


def test_explicit_retry_overrides_the_hold(env):
    _, snaps, _, _ = env
    add_snapshot(snaps)
    llm = FakeLLM(LLMCallFailed("boom"))
    go(env, llm)
    go(env, llm)
    assert actions(env, retry_failed=True) == ["call"]


def test_success_after_one_failure_clears_the_count(env):
    _, snaps, _, _ = env
    add_snapshot(snaps)
    go(env, FakeLLM(LLMCallFailed("boom")))
    go(env, FakeLLM(ok()))
    add_snapshot(snaps, ts="2026-10-18T00:00:00Z", cls="changed", sha="bbb")
    go(env, FakeLLM(LLMCallFailed("boom")))
    assert actions(env) == ["call"]


def test_new_text_restarts_the_failure_count(env):
    _, snaps, _, _ = env
    add_snapshot(snaps)
    llm = FakeLLM(LLMCallFailed("boom"))
    go(env, llm)
    go(env, llm)
    add_snapshot(snaps, ts="2026-10-18T00:00:00Z", cls="changed", sha="bbb")
    assert actions(env) == ["call"]


def test_wire_helper_produces_valid_output():
    full = output(toefl_total=[entry("toefl_total", "x", value=90)], tuition=[entry("tuition", "x", tuition_amount_usd=9)])
    assert schema_errors(wire(full), build_schema()) == []


@pytest.mark.parametrize("text", ["not json", json.dumps({"terms_mentioned": []})])
def test_off_schema_output_counts_as_an_extraction_and_is_not_retried(env, text):
    _, snaps, store, _ = env
    add_snapshot(snaps)
    go(env, FakeLLM(LLMResult(text, "end_turn", "claude-haiku-5-5", "r", {"input": 10, "output": 5})))
    assert store.read_records()[0]["status"] == "invalid_output"
    assert {r["value_status"] for r in store.read_observations()} == {"extraction_failed"}
    assert actions(env) == ["skip"]


def test_budget_stops_further_calls(env):
    registry, snaps, store, settings = env
    add_snapshot(snaps, "pg-0001")
    add_snapshot(snaps, "pg-0002")
    expensive = LLMResult(json.dumps(wire(output())), "end_turn", "m", "r", {"input": 100_000_000})
    llm = FakeLLM(expensive)
    result = run_extract(registry, snaps, store, llm, settings, {"pg-0001", "pg-0002"}, max_usd=1.0)
    assert len(llm.calls) == 1 and result["counts"]["stopped_by_budget"] == 2


def test_cap_cannot_be_raised_above_the_config(env):
    registry, snaps, store, settings = env
    assert run_extract(registry, snaps, store, FakeLLM(ok()), settings, {"pg-0001"}, max_usd=99)["cap_usd"] == 5.0


def test_limit_caps_the_calls(env):
    registry, snaps, store, settings = env
    add_snapshot(snaps, "pg-0002")
    llm = FakeLLM(ok())
    go(env, llm, ("pg-0002",), limit=1)
    assert len(llm.calls) == 1


def test_records_are_complete_and_runs_csv_has_no_page_text(env):
    registry, snaps, store, settings = env
    add_snapshot(snaps)
    go(env, FakeLLM(ok(output(toefl_total=[entry("toefl_total", "a minimum TOEFL of 90", value=90)], terms_mentioned=["Fall 2027"]))))
    record = store.read_records()[0]
    assert record["terms_mentioned"] == ["Fall 2027"] and record["usd"] > 0 and record["request_id"] == "req_1"
    payload = store.read_call(record["call_id"])
    assert json.loads(payload["output_text"])["terms_mentioned"] == ["Fall 2027"]
    runs = store.runs_path.read_text(encoding="utf-8")
    assert "TOEFL" not in runs and "Fall 2027" not in runs
    obs = store.read_observations()[0]
    for key in ("snapshot_id", "evidence_url", "retrieved_at", "program_id", "model_name", "prompt_version",
                "schema_version", "extract_rules_version", "extracted_at"):
        assert obs[key] not in (None, "")


def test_stored_outputs_are_never_overwritten(env):
    _, _, store, _ = env
    store.write_call("c", {"a": 1})
    with pytest.raises(FileExistsError):
        store.write_call("c", {"a": 2})


def test_view_adds_cross_page_conflicts_without_touching_observations(env):
    registry, snaps, store, settings = env
    add_snapshot(snaps, "pg-0001", text="minimum TOEFL of 100")
    add_snapshot(snaps, "pg-0002", text="minimum TOEFL of 90")
    a = ok(output(toefl_total=[entry("toefl_total", "minimum TOEFL of 100", value=100)]))
    b = ok(output(toefl_total=[entry("toefl_total", "minimum TOEFL of 90", value=90)]))
    run_extract(registry, snaps, store, FakeLLM(a, b, b), settings, {"pg-0001", "pg-0002"})
    lines = store.view_path.read_text(encoding="utf-8")
    assert "level_mismatch" in lines
    assert all(r["conflict_type"] == [] for r in store.read_observations())


def test_replay_needs_no_llm_and_nothing_is_added_twice(env, monkeypatch):
    import gradprog.extract.observations as observations
    import gradprog.extract.pipeline as pipeline
    registry, snaps, store, settings = env
    add_snapshot(snaps)
    go(env, FakeLLM(ok()))
    before = len(store.read_observations())
    assert replay(registry, snaps, store, settings) == 0
    assert len(store.read_observations()) == before
    newer = pipeline.EXTRACT_RULES_VERSION + 1
    monkeypatch.setattr(pipeline, "EXTRACT_RULES_VERSION", newer)
    monkeypatch.setattr(observations, "EXTRACT_RULES_VERSION", newer)
    assert replay(registry, snaps, store, settings) == 1
    assert len(store.read_observations()) == 2 * before
    assert replay(registry, snaps, store, settings) == 0


def test_view_uses_only_the_newest_rules_version(env, monkeypatch):
    import gradprog.extract.observations as observations
    import gradprog.extract.pipeline as pipeline
    registry, snaps, store, settings = env
    add_snapshot(snaps)
    go(env, FakeLLM(ok()))
    n = len(store.read_observations())
    newer = pipeline.EXTRACT_RULES_VERSION + 1
    monkeypatch.setattr(pipeline, "EXTRACT_RULES_VERSION", newer)
    monkeypatch.setattr(observations, "EXTRACT_RULES_VERSION", newer)
    replay(registry, snaps, store, settings)
    assert pipeline.current_rows(store.read_records(), store.read_observations())[0]["extract_rules_version"] == newer
    assert len(pipeline.current_rows(store.read_records(), store.read_observations())) == n


def test_summary_holds_counts_only(env):
    registry, snaps, store, settings = env
    add_snapshot(snaps)
    go(env, FakeLLM(ok(output(toefl_total=[entry("toefl_total", "a minimum TOEFL of 90", value=90)]))))
    text = str(summarize(rebuild_view(registry, store, settings)))
    assert "minimum TOEFL" not in text and "'found'" in text


def test_cost_and_estimate(env):
    registry, snaps, store, settings = env
    prices = settings["prices"]["claude-haiku-5-5"]
    assert cost_usd({"input": 1_000_000, "output": 1_000_000, "cache_read": 1_000_000, "cache_write": 1_000_000}, prices) == pytest.approx(0.735)
    add_snapshot(snaps)
    plan = make_plan(registry, snaps, store, settings, {"pg-0001"})
    assert 0 < estimate_usd(plan, settings) < 0.05


@pytest.mark.parametrize("today,expected", [
    (date(2026, 11, 21), None), (date(2026, 11, 22), "14 days left"), (date(2026, 12, 6), "0 days left"),
    (date(2026, 12, 7), "expired on 2026-12-06"),
])
def test_key_expiry_warning(today, expected):
    warning = key_expiry_warning(load_settings(), today)
    assert warning is None if expected is None else expected in warning


def test_cli_plan_makes_no_calls_and_run_needs_the_key(tmp_path, monkeypatch, capsys, registry_dir):
    import gradprog.cli as cli
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(cli, "REGISTRY", registry_dir)
    monkeypatch.setattr(cli, "SNAPSHOTS", tmp_path / "snapshots")
    monkeypatch.setattr(cli, "EXTRACTION", tmp_path / "extraction")
    monkeypatch.setattr(cli, "EXTRACTION_STATS", tmp_path / "stats")
    assert cli.main(["extract", "plan"]) == 0
    out = capsys.readouterr().out
    assert "no_snapshot" in out and "claude-haiku-5-5" in out and "of $5.00" in out
    assert cli.main(["extract", "run"]) == 1
    assert "ANTHROPIC_API_KEY is not set" in capsys.readouterr().err
    assert not (tmp_path / "extraction").exists()


def test_setup_error_stops_the_run_and_blames_no_page(env):
    registry, snaps, store, settings = env
    add_snapshot(snaps)
    with pytest.raises(LLMSetupError):
        go(env, FakeLLM(LLMSetupError("rejected")))
    assert store.read_records() == [] and store.read_observations() == []
    assert actions(env) == ["call"]
    assert len(store.runs_path.read_text(encoding="utf-8").splitlines()) == 2


def test_summary_lists_statuses_by_page_without_values(env):
    registry, snaps, store, settings = env
    add_snapshot(snaps)
    good = entry("toefl_total", "a minimum TOEFL of 90", value=90)
    bad = entry("gre_policy", "made up text", value="required")
    go(env, FakeLLM(ok(output(toefl_total=[good], gre_policy=[bad]))))
    text = render_summary(rebuild_view(registry, store, settings))
    assert "pg-0001 alpha-ms-datascience" in text
    assert "toefl_min_legacy: found 1" in text and "gre_policy: extraction_failed 1" in text
    assert "evidence failures: 1 {'evidence_not_verbatim': 1}" in text
    assert "made up" not in text and "minimum TOEFL" not in text and "90" not in text.replace("0.90", "")
