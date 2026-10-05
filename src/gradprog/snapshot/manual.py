"""Manual captures: due list and registration (07 §5.2)."""

import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd

from gradprog.registry.urls import UrlError, normalize_url
from gradprog.snapshot.classify import load_thresholds
from gradprog.snapshot.ingest import ingest, join_note
from gradprog.snapshot.links import registrable_domain
from gradprog.snapshot.normalize import load_rules, mhtml_location
from gradprog.snapshot.store import CLASSES, SUCCESS, SnapshotError, make_run_id
from gradprog.snapshot.targets import page_sets, programs_of
from gradprog.util.download import utc_now
from gradprog.util.manifest import ManifestError, validate_timestamp

DUE_DAYS = 14
DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DUE_COLUMNS = ["program_id", "page_id", "page_type", "url", "last_retrieved"]


def manual_due(registry, store, today, url_check=None):
    _, manual = page_sets(registry, url_check)
    ix = store.read_index()
    ok = ix[ix["classification"].isin(SUCCESS)]
    pages = registry.pages.drop_duplicates("page_id").set_index("page_id")
    today_d = date.fromisoformat(today)
    rows = []
    for p in manual:
        done = ok.loc[ok["page_id"] == p, "retrieved_at"]
        last = max(done) if len(done) else ""
        if last and (today_d - date.fromisoformat(last[:10])).days < DUE_DAYS:
            continue
        rows.append([";".join(programs_of(registry, p)), p, pages.loc[p, "page_type"], pages.loc[p, "url"],
                     last[:10]])
    due = pd.DataFrame(rows, columns=DUE_COLUMNS)
    return due.sort_values(["program_id", "page_id"]).reset_index(drop=True)


def render_manual_due(due):
    out = ["# 人工取得待办", "", f"距上次成功取得 ≥ {DUE_DAYS} 天或从未取得的页面。保存为 .mhtml（页面本身是 PDF 时保存 .pdf）。", ""]
    for program, g in due.groupby("program_id", sort=True):
        out += [f"## {program}", "", "| page_id | page_type | URL | 上次取得 |", "|---|---|---|---|"]
        out += [f"| {r.page_id} | {r.page_type} | [{r.url}]({r.url}) | {r.last_retrieved or '从未'} |"
                for r in g.itertuples(index=False)]
        out.append("")
    out.append(f"合计待办：{len(due)} 个页面")
    return "\n".join(out) + "\n"


def _retrieved_at(value, file):
    if value is None:
        ts = datetime.fromtimestamp(Path(file).stat().st_mtime, tz=timezone.utc)
        return ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "retrieved_at_from_mtime"
    if DATE_ONLY.match(value):
        return f"{value}T00:00:00Z", "time_unknown"
    try:
        return validate_timestamp(value), ""
    except ManifestError as e:
        raise SnapshotError(str(e)) from e


def _known_redirect(url, target):
    """07 §5.2 --known-redirect: an https URL on the same registrable domain as the registered URL."""
    try:
        target = normalize_url(target)
    except UrlError as e:
        raise SnapshotError(f"--known-redirect {target!r} is not a valid https URL") from e
    if registrable_domain(urlsplit(target).hostname) != registrable_domain(urlsplit(url).hostname):
        raise SnapshotError(f"--known-redirect {target} is not on the same site as {url}")
    return target


def _allowed_urls(registry, store, page_id, known_redirect=None):
    url = registry.pages.loc[registry.pages["page_id"] == page_id, "url"].iloc[0]
    allowed = {url}
    if known_redirect:
        allowed.add(_known_redirect(url, known_redirect))
    ix = store.read_index()
    for final in ix.loc[ix["page_id"] == page_id, "final_url"]:
        try:
            allowed.add(normalize_url(final))
        except UrlError:
            pass
    return url, allowed


def _read_file(file):
    file = Path(file).expanduser()
    if not file.is_file():
        raise SnapshotError(f"{file} does not exist")
    ext = file.suffix.lower()
    raw = file.read_bytes()
    if ext == ".pdf":
        if not raw.startswith(b"%PDF-"):
            raise SnapshotError(f"{file.name} is not a PDF file")
        return raw, "pdf", None
    if ext == ".mhtml":
        return raw, "mhtml", mhtml_location(raw)
    raise SnapshotError(f"{file.name}: only .mhtml and .pdf files can be registered")


def _register(registry, store, page_id, file, retrieved_at, run_id, thresholds, rules, url_check,
              known_redirect=None):
    _, manual = page_sets(registry, url_check)
    if page_id not in manual:
        raise SnapshotError(f"{page_id} is not a manually captured page (07 §3)")
    raw, kind, location = _read_file(file)
    url, allowed = _allowed_urls(registry, store, page_id, known_redirect)
    final = url
    if kind == "mhtml":
        if not location:
            raise SnapshotError(f"{Path(file).name}: no Snapshot-Content-Location or Content-Location in the file")
        try:
            loc = normalize_url(location)
        except UrlError as e:
            raise SnapshotError(f"{Path(file).name}: saved page address {location!r} is not a valid https URL") from e
        if loc not in allowed:
            raise SnapshotError(f"{Path(file).name}: saved page address {location} does not match {page_id} ({url})")
        final = loc
    at, note = _retrieved_at(retrieved_at, file)
    note = join_note(note, "" if final == url else "redirected")
    return ingest(store, registry, page_id=page_id, run_id=run_id, method="manual", retrieved_at=at,
                  requested_url=url, final_url=final, http_status="", raw=raw, content_type=kind, note=note,
                  rules=rules, thresholds=thresholds)


def _record_run(store, run_id, started, finished, rows):
    counts = {c: sum(r["classification"] == c for r in rows) for c in CLASSES}
    anomalies = sorted({r["page_id"] for r in rows if r["classification"] not in SUCCESS
                        or r["classification"] == "suspected_redesign"})
    store.append_run({"run_id": run_id, "method": "manual", "started_at": started, "finished_at": finished,
                      **counts, "anomaly_page_ids": ";".join(anomalies)})


def register_manual(registry, store, page_id, file, retrieved_at=None, now=None, thresholds=None, rules=None,
                    url_check=None, known_redirect=None):
    now = now or utc_now
    thresholds = thresholds or load_thresholds()
    rules = load_rules() if rules is None else rules
    started = now()
    run_id = make_run_id(started, "manual")
    row = _register(registry, store, page_id, file, retrieved_at, run_id, thresholds, rules, url_check,
                    known_redirect)
    _record_run(store, run_id, started, now(), [row])
    return row


def register_from_dir(registry, store, directory, retrieved_at=None, now=None, thresholds=None, rules=None,
                      url_check=None):
    now = now or utc_now
    thresholds = thresholds or load_thresholds()
    rules = load_rules() if rules is None else rules
    auto, manual = page_sets(registry, url_check)
    pages = registry.pages.drop_duplicates("page_id")
    by_url = dict(zip(pages["url"], pages["page_id"]))
    ix = store.read_index()
    for p, final in zip(ix["page_id"], ix["final_url"]):
        try:
            by_url.setdefault(normalize_url(final), p)
        except UrlError:
            pass
    started = now()
    run_id = make_run_id(started, "manual")
    registered, unmatched = [], []
    for f in sorted(Path(directory).expanduser().iterdir()):
        ext = f.suffix.lower()
        if ext == ".pdf":
            unmatched.append({"file": f.name, "reason": "PDF has no address; register it with --page --file"})
            continue
        if ext != ".mhtml":
            continue
        location = mhtml_location(f.read_bytes())
        try:
            page_id = by_url.get(normalize_url(location)) if location else None
        except UrlError:
            page_id = None
        if page_id is None:
            unmatched.append({"file": f.name, "reason": f"no registered page for {location!r}"})
        elif page_id not in manual:
            unmatched.append({"file": f.name, "reason": f"{page_id} is not a manually captured page"})
        else:
            try:
                registered.append(_register(registry, store, page_id, f, retrieved_at, run_id, thresholds, rules,
                                            url_check))
            except SnapshotError as e:
                unmatched.append({"file": f.name, "reason": str(e)})
    if registered:
        _record_run(store, run_id, started, now(), registered)
    return registered, unmatched


__all__ = ["manual_due", "render_manual_due", "register_manual", "register_from_dir", "join_note"]
