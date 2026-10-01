"""DHS STEM list parsing and STEM logic (docs/spec/03_stem_logic.md)."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from gradprog.ref.cip import UnknownCipError, normalize_cip6

SERIES_MAX_X = 130   # x0 < 130 -> series column (03 §3.2)
CODE_MAX_X = 205     # 130 <= x0 < 205 -> code column; x0 >= 205 -> title column
BASELINE_TOL = 2.0
CODE = re.compile(r"^\d{2}\.\d{4}$")
CODE_ANYWHERE = re.compile(r"(?<![\d.])\d{2}\.\d{4}(?!\d)")
SERIES = re.compile(r"^\d{2}$")
DATE = re.compile(r"^([A-Za-z]+) (\d{1,2}), (\d{4})$")

SCHOOL_DECLARED = frozenset({"school_stem_page", "program_page", "i20_statement"})
NOT_DECLARED = frozenset({"ipeds_inferred", "unknown"})


class StemParseError(ValueError):
    """The STEM list PDF does not match the documented structure."""


@dataclass
class StemParseResult:
    stem_list: pd.DataFrame
    core_series: pd.DataFrame
    last_updated: str
    dropped_group_headers: int
    title_mismatches: list = field(default_factory=list)


def extract_pdf_words(path):
    """Words per page as dicts with text, x0, x1, top, bottom (pdfplumber coordinates, pt)."""
    import pdfplumber

    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            pages.append([
                {k: w[k] for k in ("text", "x0", "x1", "top", "bottom")}
                for w in page.extract_words()
            ])
    return pages


def _squash(s):
    return re.sub(r"\s+", "", s).lower()


def _baselines(words):
    """Group words whose top differs by at most BASELINE_TOL from the first word of the group."""
    groups = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if groups and w["top"] - groups[-1][0]["top"] <= BASELINE_TOL:
            groups[-1].append(w)
        else:
            groups.append([w])
    return groups


def _join(words):
    return re.sub(r"\s+", " ", " ".join(w["text"] for w in sorted(words, key=lambda w: w["x0"]))).strip()


def _same_line(a, b):
    return abs(a["top"] - b["top"]) <= BASELINE_TOL


def _last_updated_dates(words, pno):
    """Dates following each 'Last' + 'Updated:' pair on the page."""
    dates = []
    for w in words:
        if w["text"].lower() != "last":
            continue
        line = sorted((u for u in words if _same_line(u, w) and u["x0"] > w["x0"]), key=lambda u: u["x0"])
        if not line or line[0]["text"].lower() != "updated:":
            continue
        text = " ".join(u["text"] for u in line[1:4])
        m = DATE.match(text)
        if not m:
            raise StemParseError(f"page {pno}: cannot read 'Last updated' date from {text!r}")
        try:
            dates.append(datetime.strptime(text, "%B %d, %Y").date().isoformat())
        except ValueError as e:
            raise StemParseError(f"page {pno}: invalid 'Last updated' date {text!r}") from e
    return dates


def _footer_top(words, below, pno):
    tops = [
        w["top"] for w in words
        if w["text"].lower() == "last" and w["top"] > below
        and any(u["text"].lower() == "updated:" and _same_line(u, w) and u["x0"] > w["x0"] for u in words)
    ]
    if not tops:
        raise StemParseError(f"page {pno}: footer 'Last updated' not found below the table header")
    return min(tops)


def parse_core_series_from_intro(text):
    flat = re.sub(r"\s+", " ", text)
    start = re.search(r"at the 2-digit CIP code level", flat, re.IGNORECASE)
    if not start:
        raise StemParseError("intro: sentence 'at the 2-digit CIP code level' not found")
    end = re.search(r"Any new additions", flat[start.end():], re.IGNORECASE)
    if not end:
        raise StemParseError("intro: sentence 'Any new additions' not found after the 2-digit sentence")
    series = set(re.findall(r"\((\d{2})\)", flat[start.end():start.end() + end.start()]))
    if not series:
        raise StemParseError("intro: no 2-digit series found between the anchor sentences")
    return series


def _parse_page(words, pno):
    """Return (rows, intro_words, dates) for one page. rows: dicts with code, series, title, top."""
    headers = [w for w in words if w["text"] == "Series"]
    if not headers:
        raise StemParseError(f"page {pno}: table header 'Series' not found")
    header_bottom = min(headers, key=lambda w: w["top"])["bottom"]
    footer_top = _footer_top(words, header_bottom, pno)

    table = [w for w in words if header_bottom < w["top"] < footer_top]
    outside = [w for w in words if not (header_bottom < w["top"] < footer_top)]
    stray = sorted({m.group(0) for w in outside for m in CODE_ANYWHERE.finditer(w["text"])})
    if stray:
        raise StemParseError(f"page {pno}: CIP-like code(s) outside the table region: {stray}")

    rows, fragments = [], []
    for line in _baselines(table):
        series_w = [w for w in line if w["x0"] < SERIES_MAX_X]
        code_w = [w for w in line if SERIES_MAX_X <= w["x0"] < CODE_MAX_X]
        title_w = [w for w in line if w["x0"] >= CODE_MAX_X]
        top = line[0]["top"]
        in_title = sorted({m.group(0) for w in title_w for m in CODE_ANYWHERE.finditer(w["text"])})
        if in_title:
            raise StemParseError(f"page {pno}: CIP-like code(s) in the title column at y={top}: {in_title}")
        if code_w:
            code = "".join(w["text"] for w in sorted(code_w, key=lambda w: w["x0"])).replace(" ", "")
            if not CODE.match(code):
                raise StemParseError(f"page {pno}: unexpected text in code column at y={top}: {code!r}")
            if len(series_w) != 1 or not SERIES.match(series_w[0]["text"]):
                raise StemParseError(f"page {pno}: code {code} without a single 2-digit series value")
            if series_w[0]["text"] != code[:2]:
                raise StemParseError(f"page {pno}: series {series_w[0]['text']} does not match code {code}")
            rows.append({"code": code, "series": code[:2], "top": top,
                         "parts": [(top, _join(title_w))] if title_w else []})
        elif series_w:
            raise StemParseError(f"page {pno}: text in series column without a code at y={top}: {_join(series_w)!r}")
        elif title_w:
            fragments.append((top, _join(title_w)))

    if not rows:
        raise StemParseError(f"page {pno}: no data rows found")
    for top, text in fragments:
        dists = sorted((abs(r["top"] - top), i) for i, r in enumerate(rows))
        if len(dists) > 1 and dists[0][0] == dists[1][0]:
            raise StemParseError(f"page {pno}: title fragment {text!r} at y={top} is equidistant from two rows")
        rows[dists[0][1]]["parts"].append((top, text))
    for r in rows:
        r["title"] = re.sub(r"\s+", " ", " ".join(t for _, t in sorted(r["parts"]))).strip()

    intro = [w for w in words if w["top"] < header_bottom]
    return rows, intro, _last_updated_dates(words, pno)


def parse_stem_words(pages, cip2020):
    levels = cip2020["level"].astype(int)
    six = set(cip2020.loc[levels == 6, "cip_code"])
    four = set(cip2020.loc[levels == 4, "cip_code"])
    two = set(cip2020.loc[levels == 2, "cip_code"])
    official = dict(zip(cip2020["cip_code"], cip2020["title"]))

    stem_rows, core_rows, dates = [], [], []
    dropped = 0
    intro_text = ""
    for pno, words in enumerate(pages, start=1):
        rows, intro, page_dates = _parse_page(words, pno)
        dates += page_dates
        if pno == 1:
            intro_text = " ".join(w["text"] for w in sorted(intro, key=lambda w: (round(w["top"]), w["x0"])))
        for r in rows:
            code = r["code"]
            if code in six:
                stem_rows.append({"cip_code": code, "title": r["title"], "series": r["series"], "page": pno})
            elif code.endswith(".0000") and code[:2] in two:
                core_rows.append({"series": code[:2], "title": r["title"], "page": pno})
            elif code.endswith("00") and code[:5] in four:
                dropped += 1
            else:
                raise StemParseError(f"page {pno}: code {code} is not in CIP 2020 (6-digit, series or group)")

    stem_list = pd.DataFrame(stem_rows, columns=["cip_code", "title", "series", "page"])
    core = pd.DataFrame(core_rows, columns=["series", "title", "page"])
    dup = sorted(stem_list.loc[stem_list["cip_code"].duplicated(), "cip_code"])
    if dup:
        raise StemParseError(f"duplicate 6-digit codes: {dup}")
    if core["series"].duplicated().any():
        raise StemParseError(f"duplicate series headers: {sorted(core.loc[core['series'].duplicated(), 'series'])}")
    if not dates:
        raise StemParseError("no 'Last updated' date found")
    if len(set(dates)) != 1:
        raise StemParseError(f"inconsistent 'Last updated' dates: {sorted(set(dates))}")
    intro_series = parse_core_series_from_intro(intro_text)
    if intro_series != set(core["series"]):
        raise StemParseError(
            f"core series in intro {sorted(intro_series)} != series header rows {sorted(core['series'])}"
        )
    mismatches = [
        c for c, t in zip(stem_list["cip_code"], stem_list["title"]) if _squash(official[c]) != _squash(t)
    ]
    return StemParseResult(stem_list, core, dates[0], dropped, mismatches)


# --- STEM logic (03 §4–5) -----------------------------------------------------

class StemReference:
    def __init__(self, stem_list, core_series, cip2020):
        self.six_digit = frozenset(stem_list["cip_code"])
        self.core_series = frozenset(core_series["series"])
        self.valid_six = frozenset(cip2020.loc[cip2020["level"].astype(int) == 6, "cip_code"])

    @classmethod
    def load(cls, ref_dir):
        ref_dir = Path(ref_dir)

        def read(name):
            return pd.read_csv(ref_dir / name, dtype=str, keep_default_na=False)

        return cls(read("stem_list.csv"), read("stem_core_series.csv"), read("cip2020.csv"))


def _checked(cip, ref):
    code = normalize_cip6(cip)
    if code not in ref.valid_six:
        raise UnknownCipError(f"{code} is not a valid CIP 2020 6-digit code")
    return code


def cip_on_stem_list_exact(cip, ref):
    return _checked(cip, ref) in ref.six_digit


def cip_on_stem_list(cip, ref):
    code = _checked(cip, ref)
    return code in ref.six_digit or code[:2] in ref.core_series


def expansion_only_codes(ref):
    return sorted(c for c in ref.valid_six if cip_on_stem_list(c, ref) and not cip_on_stem_list_exact(c, ref))


def derive_stem_status(cip_code, cip_source, ref):
    if cip_source not in SCHOOL_DECLARED | NOT_DECLARED:
        raise ValueError(f"unknown cip_source {cip_source!r}")
    empty = cip_code is None or (isinstance(cip_code, str) and not cip_code.strip())
    if empty:
        if cip_source == "unknown":
            return "unknown"
        raise ValueError(f"cip_source {cip_source!r} given without a CIP code")
    on_list = cip_on_stem_list(cip_code, ref)
    if cip_source in SCHOOL_DECLARED:
        return "confirmed_by_school" if on_list else "not_on_list"
    return "cip_on_list_unconfirmed" if on_list else "cip_not_on_list_unconfirmed"
