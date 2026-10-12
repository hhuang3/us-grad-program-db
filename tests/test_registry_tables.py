"""docs/spec/06_source_registry.md §3 (tables), §4.2 (derive), §6 (init, add-page)."""

import pytest

from gradprog.registry.tables import (
    RegistryError,
    add_page,
    derive,
    init_registry,
    load_registry,
    save_registry,
)
from helpers import REGISTRY_FIXTURES, REGISTRY_TABLES

HEADERS = {
    "programs.csv": "program_id,unitid,cip_code,cip_group,institution_name,program_name,degree_type,department,"
                    "delivery_mode,status,exclusion_reason,selection_note,batch,fetch_method,added_at",
    "pages.csv": "page_id,url,domain,page_type,owner_level,url_status,content_format,robots_allowed,crawl_allowed,"
                 "added_at",
    "program_pages.csv": "program_id,page_id,scope_note",
    "domains.csv": "domain,robots_url,robots_checked_at,robots_status,robots_allows_registered_paths,tos_url,"
                   "tos_status,tos_note",
}


# --- init ---------------------------------------------------------------------

def test_init_creates_header_only_tables(tmp_path):
    d = tmp_path / "registry"
    init_registry(d)
    for name, header in HEADERS.items():
        assert (d / name).read_text(encoding="utf-8") == header + "\n"


def test_init_refuses_to_overwrite(tmp_path):
    d = tmp_path / "registry"
    init_registry(d)
    (d / "programs.csv").write_text(HEADERS["programs.csv"] + "\nkeep-me\n", encoding="utf-8")
    with pytest.raises(RegistryError):
        init_registry(d)
    assert "keep-me" in (d / "programs.csv").read_text(encoding="utf-8")


# --- load / save --------------------------------------------------------------

def test_load_reads_everything_as_strings(registry):
    assert registry.programs["unitid"].iloc[0] == "200001"
    assert registry.programs["exclusion_reason"].iloc[0] == ""   # empty stays "", not NaN
    assert registry.pages["crawl_allowed"].iloc[0] == "true"


def test_save_round_trip_is_byte_identical(registry, tmp_path):
    out = tmp_path / "out"
    save_registry(registry, out)
    for name in REGISTRY_TABLES:
        assert (out / name).read_bytes() == (REGISTRY_FIXTURES / name).read_bytes(), name


def test_scope_note_round_trips(registry):
    pp = registry.program_pages
    note = pp.loc[(pp["program_id"] == "alpha-ms-businessanalytics") & (pp["page_id"] == "pg-0002"), "scope_note"]
    assert note.iloc[0] == "Shared graduate school page; use only the business school sections"


def test_load_rejects_wrong_columns(registry_dir):
    p = registry_dir / "domains.csv"
    p.write_text(p.read_text(encoding="utf-8").replace("tos_note", "notes"), encoding="utf-8")
    with pytest.raises(RegistryError, match="domains.csv"):
        load_registry(registry_dir)


# --- add-page -----------------------------------------------------------------

def test_add_page_allocates_next_id_and_links(registry):
    pid = add_page(registry, "https://DataScience.alpha.edu/ms/faq#top", "faq", "program", "html",
                   ["alpha-ms-datascience"], "2026-10-03")
    assert pid == "pg-0006"
    row = registry.pages.set_index("page_id").loc[pid]
    assert row["url"] == "https://datascience.alpha.edu/ms/faq"
    assert row["domain"] == "datascience.alpha.edu"
    assert (row["url_status"], row["robots_allowed"], row["crawl_allowed"]) == ("proposed", "not_checked", "false")
    assert row["added_at"] == "2026-10-03"
    links = set(map(tuple, registry.program_pages.values.tolist()))
    assert ("alpha-ms-datascience", pid, "") in links   # new links have an empty scope_note


def test_add_page_adds_new_domain_row(registry):
    add_page(registry, "https://isso.alpha.edu/stem-programs", "isso_stem_list", "university", "html",
             ["alpha-ms-datascience", "alpha-ms-businessanalytics"], "2026-10-03")
    d = registry.domains.set_index("domain").loc["isso.alpha.edu"]
    assert d["robots_url"] == "https://isso.alpha.edu/robots.txt"
    assert d["tos_status"] == "not_checked"
    assert d["robots_status"] == "" and d["robots_checked_at"] == ""


def test_add_page_rejects_duplicate_url_after_normalization(registry):
    with pytest.raises(RegistryError, match="pg-0001"):
        add_page(registry, "https://datascience.alpha.edu/ms?utm_source=newsletter", "program_home", "program",
                 "html", ["alpha-ms-datascience"], "2026-10-03")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"url": "http://datascience.alpha.edu/x"},
        {"page_type": "homepage"},
        {"owner_level": "school"},
        {"content_format": "docx"},
        {"program_ids": ["no-such-program"]},
        {"program_ids": []},
        {"added_at": "2026/10/03"},
        {"url_status": "maybe"},
        {"url_status": "retired"},          # pages are retired by hand, never registered retired
    ],
)
def test_add_page_rejects_invalid_input(registry, kwargs):
    args = {"url": "https://datascience.alpha.edu/new", "page_type": "faq", "owner_level": "program",
            "content_format": "html", "program_ids": ["alpha-ms-datascience"], "added_at": "2026-10-03"}
    args.update(kwargs)
    before = len(registry.pages)
    with pytest.raises((RegistryError, ValueError)):
        add_page(registry, **args)
    assert len(registry.pages) == before


def test_add_page_numbering_survives_gaps(registry):
    registry.pages.loc[registry.pages["page_id"] == "pg-0005", "page_id"] = "pg-0042"
    registry.program_pages.loc[registry.program_pages["page_id"] == "pg-0005", "page_id"] = "pg-0042"
    pid = add_page(registry, "https://datascience.alpha.edu/new", "faq", "program", "html",
                   ["alpha-ms-datascience"], "2026-10-03")
    assert pid == "pg-0043"


# --- derive (§4.2) ------------------------------------------------------------

def test_derive_recomputes_crawl_allowed_after_tos_change(registry):
    registry.domains.loc[registry.domains["domain"] == "business.alpha.edu", "tos_status"] = "no_restriction"
    derive(registry)
    crawl = dict(zip(registry.pages["page_id"], registry.pages["crawl_allowed"]))
    assert crawl["pg-0003"] == "true"     # robots yes + tos now ok
    assert crawl["pg-0004"] == "false"    # robots no


def test_derive_fills_domain_and_missing_domain_rows(registry):
    registry.pages.loc[registry.pages["page_id"] == "pg-0005", "url"] = "https://apply.alpha.edu/tuition.pdf"
    derive(registry)
    row = registry.pages.set_index("page_id").loc["pg-0005"]
    assert row["domain"] == "apply.alpha.edu"
    assert "apply.alpha.edu" in set(registry.domains["domain"])


def test_derive_does_not_touch_robots_allowed(registry):
    before = list(registry.pages["robots_allowed"])
    derive(registry)
    assert list(registry.pages["robots_allowed"]) == before
