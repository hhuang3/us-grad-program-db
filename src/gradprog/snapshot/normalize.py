"""Text normalization of HTML, MHTML and PDF snapshots (07 §6)."""

import email
import io
import re
import unicodedata
from collections import Counter
from email import policy
from pathlib import Path

import soupsieve
import yaml
from bs4 import BeautifulSoup, Comment, Declaration, Doctype, NavigableString, ProcessingInstruction, Tag

from gradprog.registry.urls import UrlError, normalize_url

# Bump whenever output can change (code, rules file, dependency behaviour) and add the new rules-file hash.
NORMALIZER_VERSION = 2
RULES_SHA256 = {1: "e526cbb980de8a67f4aa890aff8b10f11e1b8078d6a41303a04631db042e763a",
                2: "c371b1902d4a34bd9aefd30990c5229eee6120fc72866db2aaa5356bcf15f4b6"}
RULES_FILE = Path(__file__).resolve().parents[3] / "config" / "normalize_rules.yaml"

REMOVE_TAGS = ["script", "style", "noscript", "template", "svg", "iframe", "header", "nav", "footer", "form"]
REMOVE_ROLES = {"banner", "navigation", "contentinfo", "search"}
COOKIE = re.compile(r"cookie|consent|gdpr", re.IGNORECASE)
BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "caption", "dd", "details", "dialog", "div", "dl", "dt",
    "fieldset", "figcaption", "figure", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "li", "main", "ol", "p", "pre",
    "section", "summary", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul", "body", "html",
}
RULE_KINDS = ("remove_selector", "remove_line_regex")
META_CHARSET = re.compile(rb"""<meta[^>]+charset\s*=\s*["']?([A-Za-z0-9_\-:.]+)""", re.IGNORECASE)
SPACES = re.compile(r"\s+")
NOT_TEXT = (Comment, Doctype, Declaration, ProcessingInstruction)
_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"
# 07 §6.5: lines that look like data (dates, money, scores, admission keywords)
DATA_LIKE = re.compile(
    rf"\b{_MONTH} \d{{1,2}}, \d{{4}}\b|\b\d{{1,2}}/\d{{1,2}}/\d{{4}}\b|\b\d{{4}}-\d{{2}}-\d{{2}}\b|\$\s?\d"
    r"|\bscores?\b|\bdeadlines?\b|\bapply by\b|\btuition\b|\bfees?\b|\btoefl\b|\bielts\b|\bduolingo\b|\bgre\b"
    r"|\bgmat\b", re.IGNORECASE)


def load_rules(path=RULES_FILE):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("normalize rules must be a mapping of domain -> list of rules")
    for domain, rules in data.items():
        if not isinstance(rules, list):
            raise ValueError(f"{domain}: rules must be a list")
        for rule in rules:
            if not isinstance(rule, dict) or len(rule) != 1 or next(iter(rule)) not in RULE_KINDS:
                raise ValueError(f"{domain}: each rule needs exactly one of {RULE_KINDS}, got {rule!r}")
            kind, value = next(iter(rule.items()))
            try:
                if kind == "remove_selector":
                    soupsieve.compile(value)
                else:
                    re.compile(value)
            except Exception as e:
                raise ValueError(f"{domain}: invalid {kind} {value!r}: {e}") from e
    return data


def _message(raw):
    return email.message_from_bytes(raw, policy=policy.default)


def mhtml_location(raw):
    msg = _message(raw)
    loc = msg.get("Snapshot-Content-Location")
    if loc:
        return str(loc).strip()
    for part in msg.walk():
        if part.get_content_type() == "text/html" and part.get("Content-Location"):
            return str(part.get("Content-Location")).strip()
    return None


def _mhtml_html(raw):
    msg = _message(raw)
    target = msg.get("Snapshot-Content-Location")
    htmls = [p for p in msg.walk() if p.get_content_type() == "text/html"]
    if not htmls:
        raise ValueError("MHTML file has no text/html part")
    main = next((p for p in htmls if target and str(p.get("Content-Location", "")).strip() == str(target).strip()),
                htmls[0])
    return main.get_payload(decode=True) or b"", main.get_content_charset()


def _decode(raw, charset):
    for cs in (charset, *(m.decode("ascii", "ignore") for m in META_CHARSET.findall(raw[:4096])[:1])):
        if cs:
            try:
                return raw.decode(cs, errors="replace")
            except LookupError:
                continue
    return raw.decode("utf-8", errors="replace")


def _is_cookie(tag):
    ident = " ".join([tag.get("id") or "", " ".join(tag.get("class") or [])])
    return bool(ident.strip()) and bool(COOKIE.search(ident))


def strip_structure(root, domain, rules):
    """07 §6.2 step 3: remove comments, structural elements, navigation roles, cookie notices, domain selectors."""
    for c in root.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for tag in root.find_all(REMOVE_TAGS):
        tag.decompose()
    for tag in root.find_all(lambda t: isinstance(t, Tag) and (
            (t.get("role") or "").strip().lower() in REMOVE_ROLES or _is_cookie(t))):
        if not tag.decomposed:
            tag.decompose()
    for rule in rules.get(domain, []) if domain else []:
        if "remove_selector" in rule:
            for tag in root.select(rule["remove_selector"]):
                if not tag.decomposed:
                    tag.decompose()


def _cell_text(cell):
    return SPACES.sub(" ", cell.get_text(" ")).strip()


def _emit(node, out):
    if isinstance(node, NavigableString):
        if not isinstance(node, NOT_TEXT):   # v2: a stray <!DOCTYPE html> is not text
            out.append(str(node))
        return
    if not isinstance(node, Tag):
        return
    name = node.name
    if name == "br":
        out.append("\n")
        return
    if name == "tr":
        cells = [_cell_text(c) for c in node.find_all(["td", "th"], recursive=False)]
        while cells and not cells[-1]:   # v2: drop trailing empty cells; all-empty rows vanish
            cells.pop()
        if cells:
            out.append("\n" + " | ".join(cells) + "\n")
        return
    block = name in BLOCK_TAGS
    if block:
        out.append("\n")
    for child in node.children:
        _emit(child, out)
    if block:
        out.append("\n")


def _lines(text):
    lines = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = SPACES.sub(" ", line.replace(" ", " ")).strip()
        if line:
            lines.append(unicodedata.normalize("NFC", line))
    return lines


def _finish(text, domain, rules):
    lines = _lines(text)
    for rule in rules.get(domain, []) if domain else []:
        if "remove_line_regex" in rule:
            rx = re.compile(rule["remove_line_regex"])
            lines = [line for line in lines if not rx.search(line)]
    return "\n".join(lines) + "\n" if lines else ""


def _html_text(text, domain, rules):
    soup = BeautifulSoup(text, "lxml")
    root = soup.body or soup
    strip_structure(root, domain, rules)
    out = []
    _emit(root, out)
    return "".join(out)


def _pdf_text(raw):
    import pdfplumber

    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        return "\n\n".join(page.extract_text() or "" for page in pdf.pages)


def normalize(raw, content_type, domain=None, rules=None, charset=None):
    rules = {} if rules is None else rules
    if content_type == "pdf":
        return _finish(_pdf_text(raw), domain, rules)
    if content_type == "mhtml":
        raw, charset = _mhtml_html(raw)
    elif content_type != "html":
        raise ValueError(f"unsupported content type {content_type!r}")
    return _finish(_html_text(_decode(raw, charset), domain, rules), domain, rules)


def rule_losses(raw, content_type, domain, rules, charset=None):
    """07 §6.5: data-like lines that the domain rules removed (generic-only text minus full text)."""
    if not domain or not rules.get(domain):
        return []
    base = Counter(normalize(raw, content_type, domain, {}, charset).splitlines())
    full = Counter(normalize(raw, content_type, domain, rules, charset).splitlines())
    return [line for line, n in (base - full).items() for _ in range(n) if DATA_LIKE.search(line)]


def location_matches(location, allowed_urls):
    """True when an MHTML location normalizes to one of the allowed (normalized) URLs."""
    try:
        return normalize_url(location) in allowed_urls
    except UrlError:
        return False
