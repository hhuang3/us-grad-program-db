"""Find the page a "see another page" reference points to (10 §3.1). Reads the stored raw snapshot; no page text out."""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from gradprog.snapshot.normalize import _decode, _mhtml_html

SPACES = re.compile(r"\s+")


def _norm(text):
    return SPACES.sub(" ", text or "").strip().lower().replace("’", "'")


def anchors(raw, content_type, base_url):
    """[(link text, absolute URL)] of a stored snapshot."""
    if content_type == "mhtml":
        body, charset = _mhtml_html(raw)
    else:
        body, charset = raw, None
    soup = BeautifulSoup(_decode(body, charset), "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        out.append((" ".join(a.get_text(" ").split()), urljoin(base_url, href)))
    return out


def resolve(target, links):
    """The URL the reference names, or None when it is not a unique link on the page."""
    target = (target or "").strip()
    if target.startswith(("http://", "https://")):
        return target
    wanted = _norm(target)
    if not wanted:
        return None
    exact = {url for text, url in links if _norm(text) == wanted}
    if len(exact) == 1:
        return exact.pop()
    if exact:
        return None
    partial = {url for text, url in links if len(_norm(text)) >= 4 and (_norm(text) in wanted or wanted in _norm(text))}
    return partial.pop() if len(partial) == 1 else None
