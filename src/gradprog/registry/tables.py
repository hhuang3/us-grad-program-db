"""Registry tables: init, load/save, add-page, derive (06 §3, §4.2, §6)."""

import re
from datetime import date
from pathlib import Path

import pandas as pd

from gradprog.registry.urls import domain_of, normalize_url

COLUMNS = {
    "programs": ["program_id", "unitid", "cip_code", "cip_group", "institution_name", "program_name", "degree_type",
                 "department", "delivery_mode", "status", "exclusion_reason", "selection_note", "batch", "fetch_method", "added_at"],
    "pages": ["page_id", "url", "domain", "page_type", "owner_level", "url_status", "content_format",
              "robots_allowed", "crawl_allowed", "added_at"],
    "program_pages": ["program_id", "page_id", "scope_note"],
    "domains": ["domain", "robots_url", "robots_checked_at", "robots_status", "robots_allows_registered_paths",
                "tos_url", "tos_status", "tos_note"],
}
TABLES = list(COLUMNS)

DEGREE_TYPES = ("ms", "ma", "mps", "meng", "msc", "other")
DELIVERY_MODES = ("on_campus", "hybrid", "online", "unknown")
STATUSES = ("selected", "excluded", "backlog")
EXCLUSION_REASONS = ("mba", "online_only", "certificate", "out_of_scope", "duplicate", "not_found", "not_admitting",
                     "other")
BATCHES = ("pilot", "main")
FETCH_METHODS = ("auto", "manual")
PAGE_TYPES = ("program_home", "admissions", "deadlines", "requirements", "tuition", "funding", "faq",
              "grad_school_intl", "isso_stem_list", "other")
OWNER_LEVELS = ("program", "department", "graduate_school", "university")
URL_STATUSES = ("proposed", "confirmed")
CONTENT_FORMATS = ("html", "pdf")
ROBOTS_ALLOWED = ("yes", "no", "not_checked")
CRAWL_ALLOWED = ("true", "false")
ROBOTS_STATUSES = ("fetched", "not_found", "error")
ROBOTS_SUMMARIES = ("yes", "no", "partial", "no_pages")
TOS_STATUSES = ("no_restriction", "prohibits_automated_access", "unclear", "not_checked")

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PAGE_ID = re.compile(r"^pg-(\d{4,})$")


class RegistryError(ValueError):
    """Registry operation violates a documented rule."""


class Registry:
    def __init__(self, programs, pages, program_pages, domains):
        self.programs = programs
        self.pages = pages
        self.program_pages = program_pages
        self.domains = domains

    def table(self, name):
        return getattr(self, name)


def is_date(value):
    if not DATE.match(value or ""):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _path(registry_dir, name):
    return Path(registry_dir) / f"{name}.csv"


def init_registry(registry_dir):
    existing = [n for n in TABLES if _path(registry_dir, n).exists()]
    if existing:
        raise RegistryError(f"registry tables already exist, refusing to overwrite: {existing}")
    Path(registry_dir).mkdir(parents=True, exist_ok=True)
    for name in TABLES:
        _path(registry_dir, name).write_text(",".join(COLUMNS[name]) + "\n", encoding="utf-8")


def load_registry(registry_dir):
    frames = {}
    for name in TABLES:
        path = _path(registry_dir, name)
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        if list(df.columns) != COLUMNS[name]:
            raise RegistryError(f"{path.name}: columns must be {COLUMNS[name]}, got {list(df.columns)}")
        frames[name] = df
    return Registry(**frames)


def save_registry(registry, registry_dir):
    Path(registry_dir).mkdir(parents=True, exist_ok=True)
    for name in TABLES:
        registry.table(name)[COLUMNS[name]].to_csv(
            _path(registry_dir, name), index=False, lineterminator="\n", encoding="utf-8")


def _append(df, row):
    return pd.concat([df, pd.DataFrame([row], columns=df.columns)], ignore_index=True)


def new_domain_row(domain):
    return {"domain": domain, "robots_url": f"https://{domain}/robots.txt", "robots_checked_at": "",
            "robots_status": "", "robots_allows_registered_paths": "", "tos_url": "",
            "tos_status": "not_checked", "tos_note": ""}


def _ensure_domains(registry, domains):
    known = set(registry.domains["domain"])
    for d in domains:
        if d not in known:
            registry.domains = _append(registry.domains, new_domain_row(d))
            known.add(d)


def next_page_id(pages):
    nums = [int(m.group(1)) for m in map(PAGE_ID.match, pages["page_id"]) if m]
    return f"pg-{(max(nums) + 1 if nums else 1):04d}"


def add_page(registry, url, page_type, owner_level, content_format, program_ids, added_at,
             url_status="proposed"):
    checks = [("page_type", page_type, PAGE_TYPES), ("owner_level", owner_level, OWNER_LEVELS),
              ("content_format", content_format, CONTENT_FORMATS), ("url_status", url_status, URL_STATUSES)]
    for name, value, allowed in checks:
        if value not in allowed:
            raise RegistryError(f"{name}={value!r} must be one of {list(allowed)}")
    if not is_date(added_at):
        raise RegistryError(f"added_at must be YYYY-MM-DD, got {added_at!r}")
    if not program_ids:
        raise RegistryError("a page must be linked to at least one program")
    unknown = [p for p in program_ids if p not in set(registry.programs["program_id"])]
    if unknown:
        raise RegistryError(f"unknown program_id(s): {unknown}")
    norm = normalize_url(url)
    dup = registry.pages[registry.pages["url"] == norm]
    if len(dup):
        raise RegistryError(f"URL {norm} is already registered as {dup['page_id'].iloc[0]}")

    from gradprog.registry.robots import crawl_allowed_for

    page_id = next_page_id(registry.pages)
    domain = domain_of(norm)
    _ensure_domains(registry, [domain])
    registry.pages = _append(registry.pages, {
        "page_id": page_id, "url": norm, "domain": domain, "page_type": page_type, "owner_level": owner_level,
        "url_status": url_status, "content_format": content_format, "robots_allowed": "not_checked",
        "crawl_allowed": "false", "added_at": added_at,
    })
    registry.pages["crawl_allowed"] = list(crawl_allowed_for(registry.pages, registry.domains))
    linked = set(map(tuple, registry.program_pages[["program_id", "page_id"]].values.tolist()))
    for pid in dict.fromkeys(program_ids):
        if (pid, page_id) not in linked:
            registry.program_pages = _append(registry.program_pages,
                                             {"program_id": pid, "page_id": page_id, "scope_note": ""})
    return page_id


def derive(registry):
    from gradprog.registry.robots import crawl_allowed_for

    registry.pages["domain"] = [domain_of(u) for u in registry.pages["url"]]
    _ensure_domains(registry, list(dict.fromkeys(registry.pages["domain"])))
    registry.pages["crawl_allowed"] = list(crawl_allowed_for(registry.pages, registry.domains))
    return registry
