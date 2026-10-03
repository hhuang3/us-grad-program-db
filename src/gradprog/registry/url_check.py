"""check-urls: status codes and redirects for proposed pages (06 §4.4).

Only status codes and final URLs are recorded; response bodies are never read.
"""

import os
import time
from pathlib import Path

import httpx
import pandas as pd

from gradprog.registry.robots import MAX_REDIRECTS, robots_verdicts
from gradprog.registry.urls import UrlError, normalize_url
from gradprog.util.download import CONTACT_ENV, TIMEOUT_SECONDS, DownloadError, user_agent, utc_now

COLUMNS = ["page_id", "url", "result", "http_status", "final_url", "checked_at"]


class _Polite:
    """Single-threaded request spacing shared by robots.txt and page requests."""

    def __init__(self, client, headers, min_interval, clock, sleep):
        self.client, self.headers = client, headers
        self.min_interval, self.clock, self.sleep = min_interval, clock, sleep
        self.last = None

    def get(self, url, read_body=False):
        if self.last is not None and self.clock() - self.last < self.min_interval:
            self.sleep(self.min_interval - (self.clock() - self.last))
        try:
            request = self.client.build_request("GET", url, headers=self.headers)
            resp = self.client.send(request, stream=True, follow_redirects=True)
            try:
                if read_body:  # only robots.txt; project pages are never read
                    resp.read()
            finally:
                resp.close()
            return resp
        finally:
            self.last = self.clock()


def _classify(url, resp):
    final = str(resp.url)
    moved = final if final != url else ""
    code = resp.status_code
    if code in (404, 410):
        return "broken", str(code), moved
    if not 200 <= code < 300:
        return "error", str(code), moved
    try:
        same = normalize_url(final) == url
    except UrlError:
        same = False
    return ("ok" if same else "redirected"), str(code), moved


def check_urls(registry, contact_email=None, client=None, min_interval=3.0, clock=None, sleep=None, now=None,
               page_ids=None):
    pages = registry.pages[registry.pages["url_status"] == "proposed"].sort_values("page_id")
    if page_ids is not None:
        known, proposed = set(registry.pages["page_id"]), set(pages["page_id"])
        bad = [p for p in page_ids if p not in proposed]
        if bad:
            raise ValueError(f"page_id(s) not found or not proposed: {bad} "
                             f"(unknown: {[p for p in bad if p not in known]})")
        pages = pages[pages["page_id"].isin(page_ids)]
    email = contact_email or os.environ.get(CONTACT_ENV, "").strip()
    if not email:
        raise DownloadError(f"set {CONTACT_ENV} to a contact email before checking URLs")
    client = client or httpx.Client(timeout=TIMEOUT_SECONDS, max_redirects=MAX_REDIRECTS)
    polite = _Polite(client, {"User-Agent": user_agent(email)}, min_interval, clock or time.monotonic,
                     sleep or time.sleep)
    now = now or utc_now

    robots_urls = dict(zip(registry.domains["domain"], registry.domains["robots_url"]))
    allowed, unavailable = {}, set()
    for domain, group in pages.groupby("domain", sort=True):
        robots_url = robots_urls.get(domain, f"https://{domain}/robots.txt")
        try:
            resp = polite.get(robots_url, read_body=True)
            code = resp.status_code
            text = resp.text if 200 <= code < 300 else ""
        except httpx.HTTPError:
            code, text = None, ""
        status, verdicts = robots_verdicts(code, text, list(group["url"]))
        allowed.update(verdicts)
        if status == "error":
            unavailable.add(domain)

    rows = []
    for r in pages.itertuples(index=False):
        if allowed.get(r.url) != "yes":
            result = "robots_unavailable" if r.domain in unavailable else "robots_disallowed"
            rows.append([r.page_id, r.url, result, "", "", now()])
            continue
        try:
            result, status, final = _classify(r.url, polite.get(r.url))
        except httpx.HTTPError as e:
            result, status, final = "error", "", ""
            print(f"{r.page_id}: {type(e).__name__}: {e}")
        rows.append([r.page_id, r.url, result, status, final, now()])
    return pd.DataFrame(rows, columns=COLUMNS)


def write_url_check(result, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    result[COLUMNS].to_csv(path, index=False, lineterminator="\n", encoding="utf-8")


def merge_url_check(path, partial):
    """Replace the rows of the checked pages in an existing url_check.csv; keep the others."""
    path = Path(path)
    if path.exists():
        old = pd.read_csv(path, dtype=str, keep_default_na=False)
        old = old[~old["page_id"].isin(set(partial["page_id"]))]
        merged = pd.concat([old, partial[COLUMNS]], ignore_index=True)
    else:
        merged = partial[COLUMNS].copy()
    return merged.sort_values("page_id").reset_index(drop=True)
