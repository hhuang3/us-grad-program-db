"""docs/spec/06_source_registry.md §5: registry validation."""

import copy
import os
import shutil
import subprocess

import pandas as pd
import pytest

from gradprog.registry.tables import load_registry
from gradprog.registry.validate import load_head_tables, validate
from helpers import REGISTRY_FIXTURES, REGISTRY_TABLES


def run(registry, candidates, **kw):
    return validate(registry, candidates, **kw)


def set_cell(df, key_col, key, col, value):
    df.loc[df[key_col] == key, col] = value


def assert_error(result, *needles):
    hits = [e for e in result.errors if all(n in e for n in needles)]
    assert hits, f"no error containing {needles}; errors were: {result.errors}"


# --- the hand-made fixture is valid --------------------------------------------

def test_fixture_has_no_errors(registry, registry_candidates):
    r = run(registry, registry_candidates)
    assert r.errors == []


def test_fixture_warns_about_proposed_page(registry, registry_candidates):
    r = run(registry, registry_candidates)
    assert any("alpha-ms-businessanalytics" in w and "pg-0004" in w for w in r.warnings)


# --- structure: columns, keys, foreign keys (§5.1) -----------------------------

def test_wrong_column_order(registry, registry_candidates):
    cols = list(registry.domains.columns)
    registry.domains = registry.domains[[cols[1], cols[0], *cols[2:]]]
    assert_error(run(registry, registry_candidates), "domains")


@pytest.mark.parametrize(
    "table, key_col, key",
    [("programs", "program_id", "alpha-ms-datascience"), ("pages", "page_id", "pg-0001"),
     ("domains", "domain", "grad.alpha.edu")],
)
def test_duplicate_primary_key(registry, registry_candidates, table, key_col, key):
    df = getattr(registry, table)
    setattr(registry, table, pd.concat([df, df[df[key_col] == key]], ignore_index=True))
    assert_error(run(registry, registry_candidates), key)


def test_duplicate_url(registry, registry_candidates):
    set_cell(registry.pages, "page_id", "pg-0005", "url", "https://grad.alpha.edu/admissions/international")
    assert_error(run(registry, registry_candidates), "https://grad.alpha.edu/admissions/international")


def test_duplicate_program_page_link(registry, registry_candidates):
    pp = registry.program_pages
    registry.program_pages = pd.concat([pp, pp.iloc[[0]]], ignore_index=True)
    assert_error(run(registry, registry_candidates), "alpha-ms-datascience", "pg-0001")


def test_duplicate_link_ignores_scope_note(registry, registry_candidates):
    pp = registry.program_pages
    dup = pp.iloc[[0]].copy()
    dup["scope_note"] = "different note"
    registry.program_pages = pd.concat([pp, dup], ignore_index=True)
    assert_error(run(registry, registry_candidates), "alpha-ms-datascience", "pg-0001")


def test_scope_note_must_be_single_line(registry, registry_candidates):
    registry.program_pages.loc[0, "scope_note"] = "line one\nline two"
    assert_error(run(registry, registry_candidates), "scope_note", "pg-0001")


def test_unitid_cip_not_in_candidates(registry, registry_candidates):
    set_cell(registry.programs, "program_id", "gamma-ms-statistics", "cip_code", "27.0599")
    assert_error(run(registry, registry_candidates), "gamma-ms-statistics")


@pytest.mark.parametrize("col, value", [("cip_group", "ds"), ("institution_name", "Gamma Inst.")])
def test_program_must_match_candidate_row(registry, registry_candidates, col, value):
    set_cell(registry.programs, "program_id", "gamma-ms-statistics", col, value)
    assert_error(run(registry, registry_candidates), "gamma-ms-statistics", col)


def test_page_domain_must_exist(registry, registry_candidates):
    registry.domains = registry.domains[registry.domains["domain"] != "business.alpha.edu"]
    assert_error(run(registry, registry_candidates), "business.alpha.edu")


@pytest.mark.parametrize("col, value", [("program_id", "nobody-ms-x"), ("page_id", "pg-0999")])
def test_program_pages_both_ends_exist(registry, registry_candidates, col, value):
    registry.program_pages.loc[0, col] = value
    assert_error(run(registry, registry_candidates), value)


# --- enums, dates, status combinations ----------------------------------------

@pytest.mark.parametrize(
    "table, key_col, key, col, value",
    [
        ("programs", "program_id", "gamma-ms-statistics", "delivery_mode", "remote"),
        ("programs", "program_id", "gamma-ms-statistics", "status", "maybe"),
        ("programs", "program_id", "gamma-ms-statistics", "degree_type", "phd"),
        ("programs", "program_id", "gamma-ms-statistics", "batch", "pilot2"),
        ("programs", "program_id", "gamma-ms-statistics", "added_at", "2026/10/01"),
        ("pages", "page_id", "pg-0001", "page_type", "homepage"),
        ("pages", "page_id", "pg-0001", "owner_level", "school"),
        ("pages", "page_id", "pg-0001", "url_status", "ok"),
        ("pages", "page_id", "pg-0001", "content_format", "docx"),
        ("pages", "page_id", "pg-0001", "robots_allowed", "partial"),
        ("pages", "page_id", "pg-0001", "crawl_allowed", "yes"),
        ("pages", "page_id", "pg-0001", "added_at", "yesterday"),
        ("domains", "domain", "grad.alpha.edu", "robots_status", "ok"),
        ("domains", "domain", "grad.alpha.edu", "robots_allows_registered_paths", "some"),
        ("domains", "domain", "grad.alpha.edu", "tos_status", "fine"),
        ("domains", "domain", "grad.alpha.edu", "robots_checked_at", "2026-10-01 12:00"),
    ],
)
def test_invalid_values(registry, registry_candidates, table, key_col, key, col, value):
    set_cell(getattr(registry, table), key_col, key, col, value)
    assert_error(run(registry, registry_candidates), key, col)


def test_no_pages_summary_is_valid(registry, registry_candidates):
    set_cell(registry.domains, "domain", "grad.alpha.edu", "robots_allows_registered_paths", "no_pages")
    assert run(registry, registry_candidates).errors == []


def test_unchecked_domain_columns_may_be_empty(registry, registry_candidates):
    for col in ["robots_checked_at", "robots_status", "robots_allows_registered_paths"]:
        set_cell(registry.domains, "domain", "grad.alpha.edu", col, "")
    assert run(registry, registry_candidates).errors == []


@pytest.mark.parametrize(
    "program_id, col, value",
    [
        ("delta-other-mbaanalytics", "exclusion_reason", ""),          # excluded needs a reason
        ("alpha-ms-datascience", "exclusion_reason", "mba"),           # selected must not have a reason
        ("gamma-ms-statistics", "exclusion_reason", "duplicate"),      # backlog must not have a reason
        ("delta-other-mbaanalytics", "exclusion_reason", "too_expensive"),
        ("alpha-ms-datascience", "selection_note", ""),                # selected needs a note
        ("delta-other-mbaanalytics", "selection_note", ""),            # excluded needs a note
    ],
)
def test_status_combinations(registry, registry_candidates, program_id, col, value):
    set_cell(registry.programs, "program_id", program_id, col, value)
    assert_error(run(registry, registry_candidates), program_id)


def test_not_admitting_is_a_valid_exclusion_reason(registry, registry_candidates):
    set_cell(registry.programs, "program_id", "delta-other-mbaanalytics", "exclusion_reason", "not_admitting")
    assert run(registry, registry_candidates).errors == []


def test_backlog_without_note_is_fine(registry, registry_candidates):
    assert registry.programs.set_index("program_id").loc["gamma-ms-statistics", "selection_note"] == ""
    assert run(registry, registry_candidates).errors == []


# --- program_id format and placeholder rows (§2.1, §3.1) ----------------------

@pytest.mark.parametrize("bad", ["Alpha-MS-DataScience", "alpha-ms", "alpha_ms_ds", "alpha-ma-datascience", "alpha--ms-ds"])
def test_program_id_format(registry, registry_candidates, bad):
    set_cell(registry.programs, "program_id", "alpha-ms-datascience", "program_id", bad)
    registry.program_pages.loc[registry.program_pages["program_id"] == "alpha-ms-datascience", "program_id"] = bad
    assert_error(run(registry, registry_candidates), bad)


def test_placeholder_id_must_use_none_segment(registry, registry_candidates):
    set_cell(registry.programs, "program_id", "epsilon-none-307099", "program_id", "epsilon-ms-307099")
    assert_error(run(registry, registry_candidates), "epsilon-ms-307099")


@pytest.mark.parametrize("col", ["program_name", "degree_type"])
def test_non_placeholder_rows_need_name_and_degree(registry, registry_candidates, col):
    set_cell(registry.programs, "program_id", "delta-other-mbaanalytics", col, "")
    assert_error(run(registry, registry_candidates), "delta-other-mbaanalytics")


# --- URLs and derived columns -------------------------------------------------

@pytest.mark.parametrize(
    "url",
    ["http://datascience.alpha.edu/ms", "https://datascience.alpha.edu/ms#top",
     "https://DataScience.alpha.edu/ms", "https://datascience.alpha.edu/ms?utm_source=x"],
)
def test_url_must_be_https_and_normalized(registry, registry_candidates, url):
    set_cell(registry.pages, "page_id", "pg-0001", "url", url)
    assert_error(run(registry, registry_candidates), "pg-0001")


def test_domain_must_match_url(registry, registry_candidates):
    set_cell(registry.pages, "page_id", "pg-0001", "domain", "grad.alpha.edu")
    assert_error(run(registry, registry_candidates), "pg-0001", "domain")


@pytest.mark.parametrize("bad", ["page-1", "pg-1", "pg-00a1", "PG-0001"])
def test_page_id_format(registry, registry_candidates, bad):
    set_cell(registry.pages, "page_id", "pg-0001", "page_id", bad)
    registry.program_pages.loc[registry.program_pages["page_id"] == "pg-0001", "page_id"] = bad
    assert_error(run(registry, registry_candidates), bad)


def test_stale_crawl_allowed(registry, registry_candidates):
    set_cell(registry.domains, "domain", "business.alpha.edu", "tos_status", "no_restriction")
    r = run(registry, registry_candidates)
    assert_error(r, "pg-0003", "crawl_allowed")
    assert any("derive" in e for e in r.errors)


# --- selected programs (§5.2) -------------------------------------------------

def test_selected_online_is_error(registry, registry_candidates):
    set_cell(registry.programs, "program_id", "alpha-ms-datascience", "delivery_mode", "online")
    assert_error(run(registry, registry_candidates), "alpha-ms-datascience", "online")


def test_selected_unknown_delivery_warns_by_default_errors_when_ready(registry, registry_candidates):
    set_cell(registry.programs, "program_id", "alpha-ms-datascience", "delivery_mode", "unknown")
    r = run(registry, registry_candidates)
    assert not any("alpha-ms-datascience" in e for e in r.errors)
    assert any("alpha-ms-datascience" in w and "unknown" in w for w in r.warnings)
    assert_error(run(registry, registry_candidates, ready=True, batch="pilot"), "alpha-ms-datascience", "unknown")


@pytest.mark.parametrize(
    "name",
    ["Analytics MBA", "STEM mba in Business Analytics", "M.B.A. in Analytics", "M.B.A Analytics",
     "Master of Business Administration (Analytics)"],
)
def test_mba_is_a_warning(registry, registry_candidates, name):
    set_cell(registry.programs, "program_id", "alpha-ms-businessanalytics", "program_name", name)
    r = run(registry, registry_candidates)
    assert not any("alpha-ms-businessanalytics" in e for e in r.errors)
    assert any("alpha-ms-businessanalytics" in w and "MBA" in w for w in r.warnings)


@pytest.mark.parametrize("name", ["MS in Ambassador Analytics", "Master of Business Analytics", "MSBA"])
def test_mba_check_avoids_false_positives(registry, registry_candidates, name):
    set_cell(registry.programs, "program_id", "alpha-ms-businessanalytics", "program_name", name)
    r = run(registry, registry_candidates)
    assert not any("MBA" in w and "alpha-ms-businessanalytics" in w for w in r.warnings)


def test_selected_needs_program_home(registry, registry_candidates):
    registry.program_pages = registry.program_pages[
        ~((registry.program_pages["program_id"] == "alpha-ms-datascience")
          & (registry.program_pages["page_id"] == "pg-0001"))]
    assert_error(run(registry, registry_candidates), "alpha-ms-datascience", "program_home")


def test_selected_needs_admissions_or_requirements(registry, registry_candidates):
    registry.program_pages = registry.program_pages[
        ~((registry.program_pages["program_id"] == "alpha-ms-datascience")
          & (registry.program_pages["page_id"] == "pg-0002"))]
    assert_error(run(registry, registry_candidates), "alpha-ms-datascience", "admissions")


def test_requirements_page_satisfies_rule(registry, registry_candidates):
    # alpha-ms-businessanalytics has a requirements page (pg-0004) as well as the shared admissions page
    registry.program_pages = registry.program_pages[
        ~((registry.program_pages["program_id"] == "alpha-ms-businessanalytics")
          & (registry.program_pages["page_id"] == "pg-0002"))]
    assert run(registry, registry_candidates).errors == []


def test_excluded_and_backlog_need_no_pages(registry, registry_candidates):
    r = run(registry, registry_candidates)
    assert not any(p in e for e in r.errors for p in ["delta-other-mbaanalytics", "epsilon-none-307099",
                                                      "gamma-ms-statistics"])


# --- --ready --batch pilot (§5.2) ---------------------------------------------

def test_ready_pilot_errors(registry, registry_candidates):
    r = run(registry, registry_candidates, ready=True, batch="pilot")
    assert_error(r, "alpha-ms-businessanalytics", "pg-0004")          # proposed page
    assert_error(r, "alpha-ms-businessanalytics", "pg-0003", "program_home")  # program_home not crawlable
    assert not any("alpha-ms-datascience" in e for e in r.errors)


def test_ready_pilot_reports_blocked_pages_with_reasons(registry, registry_candidates):
    r = run(registry, registry_candidates, ready=True, batch="pilot")
    blocked = {(b["page_id"], b["domain"], b["reason"]) for b in r.report["ready_crawl_blocked"]}
    assert blocked == {
        ("pg-0003", "business.alpha.edu", "tos"),
        ("pg-0004", "business.alpha.edu", "robots"),
        ("pg-0005", "grad.alpha.edu", "not_checked"),
    }


def test_ready_only_checks_requested_batch(registry, registry_candidates):
    r = run(registry, registry_candidates, ready=True, batch="main")
    assert r.errors == []


# --- reports (§5.3) -----------------------------------------------------------

def test_quota_report(registry, registry_candidates):
    q = run(registry, registry_candidates).report["quota"]
    assert q["ds"] == {"target": 25, "selected": 1, "pilot": 1, "main": 0}
    assert q["analytics"]["selected"] == 1
    assert q["stats"]["selected"] == 0 and q["mgmt_sci"]["target"] == 20 and q["econ"]["target"] == 10


def test_status_and_reason_counts(registry, registry_candidates):
    rep = run(registry, registry_candidates).report
    assert rep["status_counts"]["ds"] == {"selected": 1, "excluded": 1, "backlog": 0}
    assert rep["status_counts"]["stats"] == {"selected": 0, "excluded": 0, "backlog": 1}
    assert rep["exclusion_reasons"] == {"mba": 1, "not_found": 1}


def test_crawl_and_sharing_report(registry, registry_candidates):
    rep = run(registry, registry_candidates).report
    assert {(b["page_id"], b["reason"]) for b in rep["crawl_blocked_pages"]} == {
        ("pg-0003", "tos"), ("pg-0004", "robots"), ("pg-0005", "not_checked")}
    assert rep["tos_not_ok_domains"] == ["business.alpha.edu"]
    assert rep["shared_pages"] == 1
    assert rep["graduate_school_pages"] == 2


# --- no deletion vs. git HEAD (§5.1) ------------------------------------------

def test_first_commit_previous_none_passes(registry, registry_candidates):
    assert run(registry, registry_candidates, previous=None).errors == []


def test_first_commit_previous_tables_missing_passes(registry, registry_candidates):
    previous = {name: None for name in ["programs", "pages", "program_pages", "domains"]}
    assert run(registry, registry_candidates, previous=previous).errors == []


def previous_from(registry):
    return {"programs": registry.programs.copy(), "pages": registry.pages.copy(),
            "program_pages": registry.program_pages.copy(), "domains": registry.domains.copy()}


def test_unchanged_previous_passes(registry, registry_candidates):
    assert run(registry, registry_candidates, previous=previous_from(registry)).errors == []


@pytest.mark.parametrize(
    "table, key_col, key",
    [("programs", "program_id", "gamma-ms-statistics"), ("domains", "domain", "grad.alpha.edu"),
     ("pages", "page_id", "pg-0005")],
)
def test_deleted_rows_are_errors(registry, registry_candidates, table, key_col, key):
    previous = previous_from(registry)
    df = getattr(registry, table)
    setattr(registry, table, df[df[key_col] != key])
    if table == "pages":
        registry.program_pages = registry.program_pages[registry.program_pages["page_id"] != key]
    assert_error(run(registry, registry_candidates, previous=previous), key)


def test_changed_page_added_at_is_error(registry, registry_candidates):
    previous = previous_from(registry)
    set_cell(registry.pages, "page_id", "pg-0001", "added_at", "2026-10-05")
    assert_error(run(registry, registry_candidates, previous=previous), "pg-0001", "added_at")


def test_url_change_keeps_page_id_and_is_allowed(registry, registry_candidates):
    previous = previous_from(registry)
    set_cell(registry.pages, "page_id", "pg-0001", "url", "https://datascience.alpha.edu/ms/")
    assert run(registry, registry_candidates, previous=previous).errors == []


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
                        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})


def test_load_head_tables_first_commit(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "README.md").write_text("x\n")
    git(repo, "add", "README.md")
    git(repo, "commit", "-q", "-m", "init")
    reg = repo / "data" / "registry"
    shutil.copytree(REGISTRY_FIXTURES, reg)      # present on disk but not committed
    tables = load_head_tables(repo)
    assert tables == {"programs": None, "pages": None, "program_pages": None, "domains": None}


def test_load_head_tables_after_commit(tmp_path):
    repo = tmp_path / "repo"
    reg = repo / "data" / "registry"
    reg.mkdir(parents=True)
    for name in REGISTRY_TABLES:
        shutil.copy(REGISTRY_FIXTURES / name, reg / name)
    git(repo, "init", "-q")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "registry")
    (reg / "programs.csv").write_text("changed on disk\n")
    tables = load_head_tables(repo)
    assert list(tables["programs"]["program_id"])[:1] == ["alpha-ms-datascience"]   # HEAD content, not disk
    assert tables["programs"]["exclusion_reason"].iloc[0] == ""


def test_load_head_tables_outside_git(tmp_path):
    assert load_head_tables(tmp_path) is None


def test_validate_does_not_modify_tables(registry, registry_candidates):
    before = copy.deepcopy([registry.programs, registry.pages, registry.program_pages, registry.domains])
    run(registry, registry_candidates, ready=True, batch="pilot")
    after = [registry.programs, registry.pages, registry.program_pages, registry.domains]
    for a, b in zip(before, after):
        assert a.equals(b)
