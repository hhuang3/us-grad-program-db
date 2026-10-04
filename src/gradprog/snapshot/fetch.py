"""Automatic snapshot runs (07 §5.1, §7, §8, §9)."""

import os
import time
from dataclasses import dataclass, field

import httpx

from gradprog.registry.robots import robots_verdicts
from gradprog.registry.url_check import is_different_page
from gradprog.registry.urls import UrlError, normalize_url
from gradprog.snapshot import report as run_report
from gradprog.snapshot.classify import load_thresholds
from gradprog.snapshot.ingest import failure, ingest, join_note
from gradprog.snapshot.links import discover_links, load_keywords
from gradprog.snapshot.normalize import load_rules
from gradprog.snapshot.store import ANOMALIES, CLASSES, SUCCESS, make_run_id
from gradprog.snapshot.targets import not_included, page_sets, programs_of
from gradprog.util.download import CONTACT_ENV, DownloadError, user_agent, utc_now

MAX_BYTES = 10 * 1024 * 1024
TIMEOUT_SECONDS = 30
MAX_REDIRECTS = 5
HTML_TYPES = ("text/html", "application/xhtml+xml")

ACTIONS = {
    ("unavailable", "gone"): "找新网址",
    ("unavailable", "redirected_other"): "确认最终页面；必要时找新网址",
    ("blocked", "robots"): "运行 registry check-robots，考虑改为人工取得",
    ("blocked", "http"): "考虑改为人工取得",
    ("fetch_error", "repeat"): "检查网址或网站状态",
    ("fetch_error", "first"): "下次运行再看",
    ("suspected_redesign", ""): "人工查看 diff，确认是否改版；必要时调整规范化规则",
}


@dataclass
class RunResult:
    run_id: str | None = None
    planned: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    counts: dict = field(default_factory=dict)
    anomalies: list = field(default_factory=list)
    link_candidates: list = field(default_factory=list)
    not_included: list = field(default_factory=list)
    manual_due: int = 0
    report_path: object = None


class _Polite:
    def __init__(self, client, headers, min_interval, clock, sleep):
        self.client, self.headers = client, headers
        self.min_interval, self.clock, self.sleep = min_interval, clock, sleep
        self.last = None

    def send(self, url):
        if self.last is not None and self.clock() - self.last < self.min_interval:
            self.sleep(self.min_interval - (self.clock() - self.last))
        try:
            request = self.client.build_request("GET", url, headers=self.headers)
            return self.client.send(request, stream=True, follow_redirects=True)
        finally:
            self.last = self.clock()


def _read_limited(resp, max_bytes):
    declared = resp.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > max_bytes:
        return None
    buf = bytearray()
    for chunk in resp.iter_bytes():
        buf += chunk
        if len(buf) > max_bytes:
            return None
    return bytes(buf)


def _content_kind(resp, body):
    ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    if ctype in HTML_TYPES:
        return "html"
    if ctype == "application/pdf" or body.startswith(b"%PDF-"):
        return "pdf"
    return None


def _same_page(url, final):
    try:
        return normalize_url(final) == url
    except UrlError:
        return False


def _fetch_one(polite, store, registry, page_id, url, run_id, now, max_bytes, rules, thresholds):
    base = {"page_id": page_id, "run_id": run_id, "method": "auto", "requested_url": url}
    try:
        resp = polite.send(url)
    except httpx.TimeoutException:
        return failure(store, **base, retrieved_at=now(), final_url="", http_status="", classification="fetch_error",
                       note="timeout")
    except httpx.HTTPError as e:
        return failure(store, **base, retrieved_at=now(), final_url="", http_status="", classification="fetch_error",
                       note=type(e).__name__)
    try:
        status, final, at = resp.status_code, str(resp.url), now()
        base.update(retrieved_at=at, final_url=final, http_status=status)
        if status in (401, 403):
            return failure(store, **base, classification="blocked", note=f"HTTP {status}")
        if status in (404, 410):
            return failure(store, **base, classification="unavailable", note=f"HTTP {status}")
        if not 200 <= status < 300:
            return failure(store, **base, classification="fetch_error", note=f"HTTP {status}")
        if not _same_page(url, final) and is_different_page(url, final):
            return failure(store, **base, classification="unavailable", note="redirected_other")
        try:
            body = _read_limited(resp, max_bytes)
        except httpx.HTTPError as e:
            return failure(store, **base, classification="fetch_error", note=type(e).__name__)
        if body is None:
            return failure(store, **base, classification="fetch_error", note=f"response exceeds {max_bytes} bytes")
        kind = _content_kind(resp, body)
        if kind is None:
            return failure(store, **base, classification="fetch_error",
                           note=f"unsupported content type {resp.headers.get('content-type', '')!r}")
        charset = resp.charset_encoding if kind == "html" else None
        note = join_note("" if _same_page(url, final) else "redirected", f"charset={charset}" if charset else "")
        return ingest(store, registry, **base, raw=body, content_type=kind, charset=charset, note=note,
                      rules=rules, thresholds=thresholds)
    finally:
        resp.close()


def _anomalies(rows, before, registry):
    out = []
    for r in rows:
        cls = r["classification"]
        if cls not in ANOMALIES:
            continue
        if cls == "unavailable":
            key = ("unavailable", "redirected_other" if "redirected_other" in r["note"] else "gone")
        elif cls == "blocked":
            key = ("blocked", "robots" if r["note"].startswith("robots") else "http")
        elif cls == "fetch_error":
            prior = before[before["page_id"] == r["page_id"]].sort_values(["retrieved_at", "snapshot_id"])
            repeat = len(prior) > 0 and prior.iloc[-1]["classification"] == "fetch_error"
            key = ("fetch_error", "repeat" if repeat else "first")
        else:
            key = ("suspected_redesign", "")
        out.append({"page_id": r["page_id"], "program_ids": ";".join(programs_of(registry, r["page_id"])),
                    "classification": cls, "reason": r["note"] or r["http_status"], "action": ACTIONS[key],
                    "needs_action": key != ("fetch_error", "first")})
    return out


def _links(rows, store, registry, keywords, rules):
    pages = registry.pages.drop_duplicates("page_id").set_index("page_id")
    found, seen = [], set()
    for r in rows:
        if r["classification"] not in SUCCESS or r["content_type"] != "html":
            continue
        if pages.loc[r["page_id"], "page_type"] != "program_home":
            continue
        raw = store.raw_path(r["page_id"], r["snapshot_id"], "html").read_bytes()
        for program in programs_of(registry, r["page_id"]):
            pp = registry.program_pages
            registered = set(pages.loc[[p for p in pp.loc[pp["program_id"] == program, "page_id"] if p in pages.index],
                                       "url"])
            for c in discover_links(raw, r["final_url"] or r["requested_url"], registered, keywords,
                                    domain=pages.loc[r["page_id"], "domain"], rules=rules):
                if (program, c["url"]) not in seen:
                    seen.add((program, c["url"]))
                    found.append({"program_id": program, "page_id": r["page_id"], **c})
    return found


def run_auto(registry, store, contact_email=None, client=None, clock=None, sleep=None, now=None,
             page_ids=None, dry_run=False, thresholds=None, rules=None, url_check=None,
             max_bytes=MAX_BYTES, keywords=None):
    email = contact_email or os.environ.get(CONTACT_ENV, "").strip()
    if not email:
        raise DownloadError(f"set {CONTACT_ENV} to a contact email before running snapshots")
    thresholds = thresholds or load_thresholds()
    rules = load_rules() if rules is None else rules
    keywords = keywords or load_keywords()

    auto, _ = page_sets(registry, url_check)
    if page_ids:
        bad = [p for p in page_ids if p not in auto]
        if bad:
            raise ValueError(f"page_id(s) not fetched automatically (07 §3): {bad}")
        auto = [p for p in auto if p in set(page_ids)]
    pages = registry.pages.drop_duplicates("page_id").set_index("page_id")
    robots_urls = dict(zip(registry.domains["domain"], registry.domains["robots_url"]))
    planned = [{"page_id": p, "url": pages.loc[p, "url"], "domain": pages.loc[p, "domain"],
                "robots_url": robots_urls.get(pages.loc[p, "domain"], f"https://{pages.loc[p, 'domain']}/robots.txt")}
               for p in auto]
    if dry_run:
        return RunResult(planned=planned)

    now = now or utc_now
    started = now()
    run_id = make_run_id(started, "auto")
    client = client or httpx.Client(timeout=TIMEOUT_SECONDS, max_redirects=MAX_REDIRECTS)
    polite = _Polite(client, {"User-Agent": user_agent(email)}, 3.0, clock or time.monotonic, sleep or time.sleep)
    before = store.read_index()

    robots = {}
    for domain, robots_url in sorted({(p["domain"], p["robots_url"]) for p in planned}):
        try:
            resp = polite.send(robots_url)
            try:
                code = resp.status_code
                text = resp.read().decode("utf-8", errors="replace") if 200 <= code < 300 else ""
            finally:
                resp.close()
        except httpx.HTTPError:
            code, text = None, ""
        robots[domain] = (code, text)

    rows = []
    for p in planned:
        code, text = robots[p["domain"]]
        status, verdict = robots_verdicts(code, text, [p["url"]])
        if verdict[p["url"]] != "yes":
            note = "robots.txt unavailable" if status == "error" else "robots.txt disallows"
            rows.append(failure(store, page_id=p["page_id"], run_id=run_id, method="auto", retrieved_at=now(),
                                requested_url=p["url"], final_url="", http_status="", classification="blocked",
                                note=note))
            continue
        rows.append(_fetch_one(polite, store, registry, p["page_id"], p["url"], run_id, now, max_bytes, rules,
                               thresholds))

    from gradprog.snapshot.manual import manual_due

    result = RunResult(run_id=run_id, planned=planned, rows=rows,
                       counts={c: sum(r["classification"] == c for r in rows) for c in CLASSES},
                       anomalies=_anomalies(rows, before, registry),
                       link_candidates=_links(rows, store, registry, keywords, rules),
                       not_included=not_included(registry, url_check),
                       manual_due=len(manual_due(registry, store, today=now()[:10], url_check=url_check)))
    finished = now()
    store.append_run({"run_id": run_id, "method": "auto", "started_at": started, "finished_at": finished,
                      **{c: result.counts[c] for c in CLASSES},
                      "anomaly_page_ids": ";".join(sorted({a["page_id"] for a in result.anomalies}))})
    result.report_path = run_report.write(store, result, registry)
    return result
