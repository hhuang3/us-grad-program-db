"""robots.txt checks and crawl permission (06 §4)."""

import os
import time
from urllib.robotparser import RobotFileParser

import httpx
import pandas as pd

from gradprog.util.download import CONTACT_ENV, TIMEOUT_SECONDS, DownloadError, user_agent, utc_now

AGENT_TOKEN = "gradprog-refdata"
MAX_REDIRECTS = 5


def robots_verdicts(status_code, text, urls):
    """Return (robots_status, {url: 'yes'|'no'}) for one robots.txt response (06 §4.1)."""
    if status_code is not None and 200 <= status_code < 300:
        rp = RobotFileParser()
        rp.parse(text.splitlines())
        return "fetched", {u: "yes" if rp.can_fetch(AGENT_TOKEN, u) else "no" for u in urls}
    if status_code in (404, 410):
        return "not_found", {u: "yes" for u in urls}
    return "error", {u: "no" for u in urls}


def crawl_allowed_for(pages, domains):
    """Per-page crawl permission (06 §4.3) as a 'true'/'false' Series aligned with pages."""
    tos = dict(zip(domains["domain"], domains["tos_status"]))
    values = ["true" if r == "yes" and tos.get(d) == "no_restriction" else "false"
              for r, d in zip(pages["robots_allowed"], pages["domain"])]
    return pd.Series(values, index=pages.index, dtype=object)


def summarize(verdicts):
    values = set(verdicts)
    if not values:
        return "no_pages"
    if values == {"yes"}:
        return "yes"
    if values == {"no"}:
        return "no"
    return "partial"


def check_robots(registry, contact_email=None, client=None, min_interval=3.0, clock=None, sleep=None,
                 now=None):
    email = contact_email or os.environ.get(CONTACT_ENV, "").strip()
    if not email:
        raise DownloadError(f"set {CONTACT_ENV} to a contact email before checking robots.txt")
    client = client or httpx.Client(follow_redirects=True, max_redirects=MAX_REDIRECTS, timeout=TIMEOUT_SECONDS)
    clock = clock or time.monotonic
    sleep = sleep or time.sleep
    now = now or utc_now
    headers = {"User-Agent": user_agent(email)}

    pages, domains = registry.pages, registry.domains
    last = None
    active = pages["url_status"] != "retired"   # 06 §4.1: retired pages are not judged
    for i, row in domains.iterrows():
        on_domain = pages["domain"] == row["domain"]
        if on_domain.any() and not (on_domain & active).any():
            continue
        if last is not None and clock() - last < min_interval:
            sleep(min_interval - (clock() - last))
        try:
            resp = client.get(row["robots_url"], headers=headers, follow_redirects=True)
            code, text = resp.status_code, resp.text
            if resp.history and resp.url.host != row["domain"]:
                print(f"{row['domain']}: robots.txt redirected to {resp.url}")
        except httpx.HTTPError as e:
            print(f"{row['domain']}: robots.txt request failed: {e}")
            code, text = None, ""
        last = clock()
        mask = on_domain & active
        status, verdicts = robots_verdicts(code, text, list(pages.loc[mask, "url"]))
        pages.loc[mask, "robots_allowed"] = [verdicts[u] for u in pages.loc[mask, "url"]]
        domains.loc[i, "robots_checked_at"] = now()
        domains.loc[i, "robots_status"] = status
        domains.loc[i, "robots_allows_registered_paths"] = summarize(verdicts.values())
    pages["crawl_allowed"] = list(crawl_allowed_for(pages, domains))
    return registry
