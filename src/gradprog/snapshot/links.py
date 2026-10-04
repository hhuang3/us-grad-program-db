"""Link discovery on program home pages (07 §8)."""

from pathlib import Path
from urllib.parse import urljoin, urlsplit

import yaml
from bs4 import BeautifulSoup

from gradprog.registry.urls import UrlError, normalize_url
from gradprog.snapshot.normalize import strip_structure

KEYWORDS_FILE = Path(__file__).resolve().parents[3] / "config" / "link_keywords.yaml"


def registrable_domain(host):
    host = (host or "").lower().rstrip(".")
    if host.endswith(".edu"):
        return ".".join(host.split(".")[-2:])
    return host


def load_keywords(path=KEYWORDS_FILE):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    words = data.get("keywords")
    if not isinstance(words, list) or not all(isinstance(w, str) and w for w in words):
        raise ValueError("link_keywords.yaml must define a non-empty list 'keywords'")
    return [w.lower() for w in words]


def discover_links(raw_html, base_url, registered_urls, keywords, domain=None, rules=None):
    soup = BeautifulSoup(raw_html, "lxml")
    strip_structure(soup.body or soup, domain, rules or {})   # 07 §8: only links in the content area
    home = registrable_domain(urlsplit(base_url).hostname)
    registered = set()
    for u in registered_urls:
        try:
            registered.add(normalize_url(u))
        except UrlError:
            pass
    found, seen = [], set()
    for a in soup.find_all("a", href=True):
        try:
            url = normalize_url(urljoin(base_url, a["href"].strip()))
        except (UrlError, ValueError):
            continue
        parts = urlsplit(url)
        if "@" in parts.path:   # e-mail address written as a relative link
            continue
        if registrable_domain(parts.hostname) != home or url in registered or url in seen:
            continue
        text = " ".join(a.get_text(" ").split())
        hay = (text + " " + parts.path).lower()
        if any(k in hay for k in keywords):
            seen.add(url)
            found.append({"text": text, "url": url})
    return found
