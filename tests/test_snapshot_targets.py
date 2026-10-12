"""docs/spec/07_snapshots.md §3: per-page fetch method."""

import pandas as pd

from gradprog.snapshot.targets import page_sets


def uc(*pairs):
    return pd.DataFrame([{"page_id": p, "url": "", "result": "error", "http_status": c, "final_url": "",
                          "checked_at": "2026-10-03T00:00:00Z"} for p, c in pairs])


def test_auto_and_manual_sets(registry):
    # fixture: pg-0001/pg-0002 crawlable; pg-0003 tos unclear; pg-0004 robots no; pg-0005 not checked.
    p = registry.programs
    p.loc[p.program_id == "alpha-ms-businessanalytics", "fetch_method"] = "manual"
    auto, manual = page_sets(registry)
    assert auto == ["pg-0001", "pg-0002"]                 # pg-0002 is shared with the manual program: still auto
    assert manual == ["pg-0003", "pg-0004"]               # non-crawlable pages of the manual program
    # pg-0005 belongs to an auto program but is not crawlable: neither list (reported elsewhere)


def test_site_blocked_page_is_not_auto(registry):
    p = registry.programs
    p.loc[p.program_id == "alpha-ms-datascience", "fetch_method"] = "manual"
    auto, manual = page_sets(registry, url_check=uc(("pg-0001", "403")))
    assert "pg-0001" not in auto and "pg-0001" in manual


def test_only_selected_programs(registry):
    registry.programs["status"] = "backlog"
    registry.programs["fetch_method"] = ""
    assert page_sets(registry) == ([], [])


def test_sets_are_disjoint_and_sorted(registry):
    auto, manual = page_sets(registry)
    assert not set(auto) & set(manual)
    assert auto == sorted(auto) and manual == sorted(manual)


def test_retired_pages_are_neither_fetched_nor_listed(registry):
    from gradprog.snapshot.targets import not_included

    p = registry.programs
    p.loc[p.program_id == "alpha-ms-businessanalytics", "fetch_method"] = "manual"
    registry.pages.loc[registry.pages.page_id.isin(["pg-0002", "pg-0004", "pg-0005"]), "url_status"] = "retired"
    auto, manual = page_sets(registry)
    assert auto == ["pg-0001"] and manual == ["pg-0003"]
    assert not_included(registry) == []
