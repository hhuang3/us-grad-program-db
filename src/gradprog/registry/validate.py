"""Registry validation (06 §5)."""

import io
import re
import subprocess
from collections import Counter
from dataclasses import dataclass, field

import pandas as pd

from gradprog.ref.targets import GROUP_ORDER
from gradprog.registry import tables as t
from gradprog.registry.robots import crawl_allowed_for
from gradprog.registry.urls import UrlError, domain_of, normalize_url
from gradprog.util.manifest import UTC_TIMESTAMP

QUOTAS = {"ds": 25, "analytics": 25, "stats": 20, "mgmt_sci": 20, "econ": 10}
PROGRAM_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+){2,}$")
MBA = re.compile(r"\bMBA\b|\bM\.B\.A\b\.?|master of business administration", re.IGNORECASE)
PLACEHOLDER_SEGMENT = "none"

ENUMS = {
    "programs": {"delivery_mode": t.DELIVERY_MODES, "status": t.STATUSES, "batch": t.BATCHES},
    "pages": {"page_type": t.PAGE_TYPES, "owner_level": t.OWNER_LEVELS, "url_status": t.URL_STATUSES,
              "content_format": t.CONTENT_FORMATS, "robots_allowed": t.ROBOTS_ALLOWED,
              "crawl_allowed": t.CRAWL_ALLOWED},
    "domains": {"tos_status": t.TOS_STATUSES},
}
# Enumerations where an empty value is allowed (checked elsewhere or "not yet checked").
OPTIONAL_ENUMS = {
    "programs": {"degree_type": t.DEGREE_TYPES, "exclusion_reason": t.EXCLUSION_REASONS},
    "domains": {"robots_status": t.ROBOTS_STATUSES, "robots_allows_registered_paths": t.ROBOTS_SUMMARIES},
}
KEYS = {"programs": "program_id", "pages": "page_id", "domains": "domain"}


@dataclass
class ValidationResult:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    report: dict = field(default_factory=dict)


def load_head_tables(repo_root, registry_rel="data/registry"):
    """Registry tables as committed in git HEAD; a table missing from HEAD maps to None.

    Returns None when repo_root is not inside a git work tree (or git is unavailable).
    """
    try:
        inside = subprocess.run(["git", "-C", str(repo_root), "rev-parse", "--is-inside-work-tree"],
                                capture_output=True, text=True)
    except FileNotFoundError:
        return None
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return None
    out = {}
    for name in t.TABLES:
        shown = subprocess.run(["git", "-C", str(repo_root), "show", f"HEAD:./{registry_rel}/{name}.csv"],
                               capture_output=True)
        out[name] = (pd.read_csv(io.BytesIO(shown.stdout), dtype=str, keep_default_na=False)
                     if shown.returncode == 0 else None)
    return out


def _crawl_reason(robots_allowed, tos_status):
    if robots_allowed == "not_checked":
        return "not_checked"
    if robots_allowed == "no":
        return "robots"
    if tos_status != "no_restriction":
        return "tos"
    return "stale"


def _check_columns(registry, errors):
    for name in t.TABLES:
        cols = list(registry.table(name).columns)
        if cols != t.COLUMNS[name]:
            errors.append(f"{name}.csv: columns must be {t.COLUMNS[name]}, got {cols}")


def _check_keys(registry, errors):
    for name, key in KEYS.items():
        df = registry.table(name)
        for k in sorted(set(df.loc[df[key].duplicated(), key])):
            errors.append(f"{name}: duplicate {key} {k}")
    pages = registry.pages
    for u in sorted(set(pages.loc[pages["url"].duplicated(), "url"])):
        errors.append(f"pages: duplicate url {u}")
    pp = registry.program_pages
    for pid, page in pp[pp.duplicated()].drop_duplicates().itertuples(index=False):
        errors.append(f"program_pages: duplicate link {pid} -> {page}")


def _check_values(registry, errors):
    for name in ("programs", "pages", "domains"):
        df, key = registry.table(name), KEYS[name]
        for col, allowed in ENUMS.get(name, {}).items():
            for k, v in zip(df[key], df[col]):
                if v not in allowed:
                    errors.append(f"{name}: {k}: {col}={v!r} not in {list(allowed)}")
        for col, allowed in OPTIONAL_ENUMS.get(name, {}).items():
            for k, v in zip(df[key], df[col]):
                if v and v not in allowed:
                    errors.append(f"{name}: {k}: {col}={v!r} not in {list(allowed)}")
    for name in ("programs", "pages"):
        df, key = registry.table(name), KEYS[name]
        for k, v in zip(df[key], df["added_at"]):
            if not t.is_date(v):
                errors.append(f"{name}: {k}: added_at={v!r} is not a valid YYYY-MM-DD date")
    d = registry.domains
    for k, v in zip(d["domain"], d["robots_checked_at"]):
        if v and not UTC_TIMESTAMP.match(v):
            errors.append(f"domains: {k}: robots_checked_at={v!r} is not UTC YYYY-MM-DDTHH:MM:SSZ")


def _check_programs(registry, candidates, errors):
    cand = candidates.set_index(["unitid", "cip_code"])
    for r in registry.programs.itertuples(index=False):
        pid = r.program_id
        key = (r.unitid, r.cip_code)
        if key not in cand.index:
            errors.append(f"programs: {pid}: (unitid, cip_code)={key} is not a row of candidates.csv")
        else:
            row = cand.loc[key]
            for col in ("cip_group", "institution_name"):
                if getattr(r, col) != row[col]:
                    errors.append(f"programs: {pid}: {col}={getattr(r, col)!r} differs from candidates.csv "
                                  f"({row[col]!r})")
        if r.status == "excluded":
            if not r.exclusion_reason:
                errors.append(f"programs: {pid}: excluded rows need an exclusion_reason")
        elif r.exclusion_reason:
            errors.append(f"programs: {pid}: exclusion_reason must be empty when status={r.status}")
        if r.status in ("selected", "excluded") and not r.selection_note.strip():
            errors.append(f"programs: {pid}: selection_note is required when status={r.status}")

        placeholder = r.status == "excluded" and r.exclusion_reason == "not_found"
        if not PROGRAM_ID.match(pid):
            errors.append(f"programs: {pid}: program_id must match {PROGRAM_ID.pattern}")
            continue
        segment = pid.split("-")[1]
        if placeholder:
            if segment != PLACEHOLDER_SEGMENT:
                errors.append(f"programs: {pid}: not_found placeholder ids use '{PLACEHOLDER_SEGMENT}' "
                              "as the second segment")
        else:
            if not r.program_name.strip() or not r.degree_type:
                errors.append(f"programs: {pid}: program_name and degree_type are required")
            elif segment != r.degree_type:
                errors.append(f"programs: {pid}: second segment '{segment}' must equal degree_type "
                              f"'{r.degree_type}'")


def _check_pages(registry, errors):
    domains = set(registry.domains["domain"])
    for r in registry.pages.itertuples(index=False):
        if not t.PAGE_ID.match(r.page_id):
            errors.append(f"pages: {r.page_id}: page_id must look like pg-0001")
        try:
            norm = normalize_url(r.url)
        except UrlError as e:
            errors.append(f"pages: {r.page_id}: {e}")
            continue
        if norm != r.url:
            errors.append(f"pages: {r.page_id}: url is not normalized (expected {norm})")
        if domain_of(norm) != r.domain:
            errors.append(f"pages: {r.page_id}: domain={r.domain!r} does not match url ({domain_of(norm)})")
        if r.domain not in domains:
            errors.append(f"pages: {r.page_id}: domain {r.domain} is not in domains.csv")
    expected = crawl_allowed_for(registry.pages, registry.domains)
    for pid, have, want in zip(registry.pages["page_id"], registry.pages["crawl_allowed"], expected):
        if have in t.CRAWL_ALLOWED and have != want:
            errors.append(f"pages: {pid}: crawl_allowed={have} is stale (expected {want}); "
                          "run `gradprog registry derive`")
    programs, pages = set(registry.programs["program_id"]), set(registry.pages["page_id"])
    for pid, page in registry.program_pages.itertuples(index=False):
        if pid not in programs:
            errors.append(f"program_pages: program_id {pid} is not in programs.csv")
        if page not in pages:
            errors.append(f"program_pages: page_id {page} is not in pages.csv")


def _check_previous(registry, previous, errors):
    for name, key in KEYS.items():
        before = previous.get(name)
        if before is None:
            continue
        gone = sorted(set(before[key]) - set(registry.table(name)[key]))
        for k in gone:
            errors.append(f"{name}: {key} {k} exists in git HEAD but was deleted (rows are never deleted)")
    before = previous.get("pages")
    if before is not None:
        now = dict(zip(registry.pages["page_id"], registry.pages["added_at"]))
        for pid, added in zip(before["page_id"], before["added_at"]):
            if pid in now and now[pid] != added:
                errors.append(f"pages: {pid}: added_at changed from {added} to {now[pid]}")


def _check_selected(registry, ready, batch, errors, warnings, blocked):
    # Duplicate page_ids are reported by _check_keys; look up the first occurrence here.
    pages = registry.pages.drop_duplicates("page_id").set_index("page_id")
    tos = dict(zip(registry.domains["domain"], registry.domains["tos_status"]))
    links = registry.program_pages.groupby("program_id")["page_id"].apply(list).to_dict()
    for r in registry.programs[registry.programs["status"] == "selected"].itertuples(index=False):
        pid = r.program_id
        strict = ready and r.batch == batch
        if r.delivery_mode == "online":
            errors.append(f"programs: {pid}: selected program is online-only (delivery_mode=online)")
        elif r.delivery_mode == "unknown":
            (errors if strict else warnings).append(f"programs: {pid}: delivery_mode is unknown; confirm it")
        if MBA.search(f"{r.program_name} {r.degree_type}"):
            warnings.append(f"programs: {pid}: program_name looks like an MBA ({r.program_name!r}); confirm it")
        linked = [p for p in links.get(pid, []) if p in pages.index]
        types = {pages.loc[p, "page_type"] for p in linked}
        if "program_home" not in types:
            errors.append(f"programs: {pid}: selected program needs a program_home page")
        if not types & {"admissions", "requirements"}:
            errors.append(f"programs: {pid}: selected program needs an admissions or requirements page")
        for p in linked:
            page = pages.loc[p]
            if page["url_status"] != "confirmed":
                (errors if strict else warnings).append(f"programs: {pid}: page {p} is still {page['url_status']}")
            if strict and page["crawl_allowed"] != "true":
                reason = _crawl_reason(page["robots_allowed"], tos.get(page["domain"]))
                blocked[p] = {"page_id": p, "domain": page["domain"], "reason": reason}
                if page["page_type"] == "program_home":
                    errors.append(f"programs: {pid}: program_home page {p} is not crawl_allowed ({reason})")


def _report(registry):
    progs = registry.programs
    sel = progs[progs["status"] == "selected"]
    quota = {g: {"target": QUOTAS[g], "selected": int((sel["cip_group"] == g).sum()),
                 "pilot": int(((sel["cip_group"] == g) & (sel["batch"] == "pilot")).sum()),
                 "main": int(((sel["cip_group"] == g) & (sel["batch"] == "main")).sum())} for g in GROUP_ORDER}
    status_counts = {g: {s: int(((progs["cip_group"] == g) & (progs["status"] == s)).sum()) for s in t.STATUSES}
                     for g in GROUP_ORDER}
    reasons = dict(Counter(progs.loc[progs["status"] == "excluded", "exclusion_reason"]))
    tos = dict(zip(registry.domains["domain"], registry.domains["tos_status"]))
    pages = registry.pages
    blocked = [{"page_id": p, "domain": d, "reason": _crawl_reason(r, tos.get(d))}
               for p, d, r, c in zip(pages["page_id"], pages["domain"], pages["robots_allowed"],
                                     pages["crawl_allowed"]) if c != "true"]
    link_counts = registry.program_pages.groupby("page_id")["program_id"].nunique()
    return {
        "quota": quota,
        "status_counts": status_counts,
        "exclusion_reasons": reasons,
        "crawl_blocked_pages": blocked,
        "tos_not_ok_domains": sorted(d for d, s in tos.items() if s != "no_restriction"),
        "shared_pages": int((link_counts > 1).sum()),
        "graduate_school_pages": int((pages["owner_level"] == "graduate_school").sum()),
    }


def validate(registry, candidates, previous=None, ready=False, batch=None):
    result = ValidationResult()
    _check_columns(registry, result.errors)
    if result.errors:
        return result
    _check_keys(registry, result.errors)
    _check_values(registry, result.errors)
    _check_programs(registry, candidates, result.errors)
    _check_pages(registry, result.errors)
    if previous:
        _check_previous(registry, previous, result.errors)
    blocked = {}
    _check_selected(registry, ready, batch, result.errors, result.warnings, blocked)
    result.report = _report(registry)
    if ready:
        result.report["ready_crawl_blocked"] = list(blocked.values())
    return result
