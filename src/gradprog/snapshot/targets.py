"""Which pages are fetched automatically and which are captured by hand (07 §3)."""

from gradprog.registry.validate import _Crawl


def _selected_links(registry):
    sel = registry.programs[registry.programs["status"] == "selected"][["program_id", "fetch_method"]]
    return registry.program_pages.merge(sel, on="program_id")


def page_sets(registry, url_check=None):
    """(auto page_ids, manual page_ids), both sorted and disjoint."""
    links = _selected_links(registry)
    crawl = _Crawl(registry, url_check)
    pages = registry.pages.drop_duplicates("page_id").set_index("page_id")
    linked = [p for p in sorted(set(links["page_id"]))
              if p in pages.index and pages.loc[p, "url_status"] != "retired"]   # 07 §3: retired pages are skipped
    auto = [p for p in linked if crawl.ok(p, pages.loc[p])]
    manual_linked = set(links.loc[links["fetch_method"] == "manual", "page_id"])
    manual = [p for p in linked if p in manual_linked and p not in auto]
    return auto, manual


def not_included(registry, url_check=None):
    """Pages of selected programs that are neither fetched nor captured by hand (07 §3), with the reason."""
    auto, manual = page_sets(registry, url_check)
    links = _selected_links(registry)
    crawl = _Crawl(registry, url_check)
    pages = registry.pages.drop_duplicates("page_id").set_index("page_id")
    out = []
    for p in sorted(set(links["page_id"]) - set(auto) - set(manual)):
        if p in pages.index and pages.loc[p, "url_status"] != "retired":
            progs = sorted(set(links.loc[links["page_id"] == p, "program_id"]))
            out.append({"page_id": p, "program_ids": ";".join(progs), "reason": crawl.reason(p, pages.loc[p])})
    return out


def programs_of(registry, page_id):
    links = _selected_links(registry)
    return sorted(set(links.loc[links["page_id"] == page_id, "program_id"]))
