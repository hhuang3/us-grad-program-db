"""valid_for_term, term_basis and stale (08 §7). Pure functions: no LLM, no files."""

import calendar
import re
from dataclasses import dataclass
from datetime import date

TERM_UNKNOWN = "term_unknown"
SEASONS = {"fall": "Fall", "autumn": "Fall", "spring": "Spring", "summer": "Summer"}
_SEASON = r"(fall|autumn|spring|summer)"
SEASON_YEAR = re.compile(rf"\b{_SEASON}\b(?:\s+\w+){{0,2}}?\s+((?:19|20)\d{{2}})\b", re.IGNORECASE)
YEAR_SEASON = re.compile(rf"\b((?:19|20)\d{{2}})\s+{_SEASON}\b", re.IGNORECASE)
SEASON_ONLY = re.compile(rf"\b{_SEASON}\b", re.IGNORECASE)
ACADEMIC_YEAR = re.compile(r"\b((?:19|20)\d{2})\s*[-–/]\s*(?:(?:19|20)?\d{2})\b")


@dataclass(frozen=True)
class TermResult:
    valid_for_term: str   # "Fall 2027", TERM_UNKNOWN, or "" (undated field with no term written)
    term_basis: str       # stated / inferred_from_date / recurring_no_year / unknown
    deadline_date: date | None = None
    stale: bool = False
    review: tuple = ()    # review reasons from 08 §10 rows 1, 2, 9, 14


def parse_term(written):
    """(kind, season, year) from a term wording: kind is season_year, season, academic_year or None (08 §7.1)."""
    text = (written or "").strip()
    if ACADEMIC_YEAR.search(text):
        return "academic_year", None, int(ACADEMIC_YEAR.search(text).group(1))
    m = SEASON_YEAR.search(text)
    if m:
        return "season_year", SEASONS[m.group(1).lower()], int(m.group(2))
    m = YEAR_SEASON.search(text)
    if m:
        return "season_year", SEASONS[m.group(2).lower()], int(m.group(1))
    m = SEASON_ONLY.search(text)
    if m:
        return "season", SEASONS[m.group(1).lower()], None
    return None, None, None


def term_of_date(season, d):
    """The term whose window holds d (08 §7.2). Fall Y: Sep 1 (Y-1)–Aug 31 Y. Spring Y: Mar 1 (Y-1)–end Feb Y."""
    if season == "Fall":
        return f"Fall {d.year + 1 if d.month >= 9 else d.year}"
    if season == "Spring":
        return f"Spring {d.year + 1 if d.month >= 3 else d.year}"
    raise ValueError(f"no window for {season}")


def date_in_term(season, year, month, day):
    """The month and day inside the window of `season year`, which has no year on the page (08 §7.1)."""
    first_month = {"Fall": 9, "Spring": 3}[season]
    return _safe_date(year - 1 if month >= first_month else year, month, day)


def next_occurrence(month, day, on_or_after):
    """The month and day on or after a date (08 §7.2). February 29 waits for the next leap year."""
    year = on_or_after.year
    while True:
        d = _safe_date(year, month, day)
        if d is not None and d >= on_or_after:
            return d
        year += 1
        if year > on_or_after.year + 8:
            raise ValueError(f"no date for month {month} day {day}")


def _safe_date(year, month, day):
    if day > calendar.monthrange(year, month)[1]:
        return None
    return date(year, month, day)


def only_season(intake_terms):
    """The program's single intake season, or None (08 §7.2)."""
    values = [v for v in (intake_terms or "").split(";") if v]
    return SEASONS[values[0]] if len(values) == 1 else None


def undated_term(term_as_written, intake_terms):
    """A field with no date: tuition, scores, length and so on (08 §7.1, §7.2)."""
    if not (term_as_written or "").strip():
        return TermResult("", "unknown")
    kind, season, year = parse_term(term_as_written)
    if kind == "season_year":
        return TermResult(f"{season} {year}", "stated")
    return TermResult(TERM_UNKNOWN, "unknown", review=("term_unknown",))


def academic_year_as_written(term_as_written):
    """The academic year in a term wording, or None."""
    m = ACADEMIC_YEAR.search(term_as_written or "")
    return m.group(0) if m else None


def tuition_term(term_as_written, intake_terms):
    """An academic year on tuition belongs in tuition_year and names no term (08 §7.1)."""
    if academic_year_as_written(term_as_written):
        return TermResult("", "unknown")
    return undated_term(term_as_written, intake_terms)


def deadline_term(term_as_written, month, day, year, intake_terms, retrieved_on):
    """A deadline entry: the date parts come from the page, the year may be None (08 §7.1–§7.3)."""
    written = (term_as_written or "").strip()
    kind, season, stated_year = parse_term(written)
    if month is None or day is None:                  # rolling, no date
        return _without_date(kind, season, stated_year)
    if year is not None:
        return _with_full_date(kind, season, stated_year, written, date(year, month, day), intake_terms, retrieved_on)
    return _without_year(kind, season, stated_year, written, month, day, intake_terms, retrieved_on)


def _without_date(kind, season, stated_year):
    if kind == "season_year":
        return TermResult(f"{season} {stated_year}", "stated")
    return TermResult(TERM_UNKNOWN, "unknown", review=("term_unknown",))


def _with_full_date(kind, season, stated_year, written, d, intake_terms, retrieved_on):
    stale = d < retrieved_on
    if kind == "season_year":
        term = f"{season} {stated_year}"
        mismatch = season != "Summer" and term_of_date(season, d) != term
        return TermResult(term, "stated", d, stale, ("term_date_mismatch",) if mismatch else ())
    if kind == "academic_year":
        if only_season(intake_terms) == "Fall":       # the wording names the cycle, so the date decides (08 §7.1)
            return TermResult(term_of_date("Fall", d), "inferred_from_date", d, stale, ("term_inferred",))
        return TermResult(TERM_UNKNOWN, "unknown", d, stale, ("term_unknown",))
    if written and kind is None:                      # "2026 applications", "October 2026 Start"
        return TermResult(TERM_UNKNOWN, "unknown", d, stale, ("term_unknown",))
    use = season or only_season(intake_terms)
    if use is None:
        return TermResult(TERM_UNKNOWN, "unknown", d, stale, ("term_unknown", "season_undetermined"))
    if use == "Summer":
        return TermResult(TERM_UNKNOWN, "unknown", d, stale, ("term_unknown", "season_undetermined"))
    return TermResult(term_of_date(use, d), "inferred_from_date", d, stale, ("term_inferred",))


def _without_year(kind, season, stated_year, written, month, day, intake_terms, retrieved_on):
    if kind == "season_year":
        if season == "Summer":
            d = next_occurrence(month, day, retrieved_on)
            return TermResult(f"Summer {stated_year}", "stated", d, d < retrieved_on, ("summer_date_unverified",))
        d = date_in_term(season, stated_year, month, day)
        if d is None:                                 # February 29 in a year without one
            return TermResult(f"{season} {stated_year}", "stated", None, False, ("term_date_mismatch",))
        return TermResult(f"{season} {stated_year}", "stated", d, d < retrieved_on)
    d = next_occurrence(month, day, retrieved_on)
    if kind == "academic_year" or (written and kind is None):
        return TermResult(TERM_UNKNOWN, "unknown", d, False, ("term_unknown",))
    use = season or only_season(intake_terms)
    if use is None or use == "Summer":
        return TermResult(TERM_UNKNOWN, "unknown", d, False, ("term_unknown", "season_undetermined"))
    return TermResult(term_of_date(use, d), "recurring_no_year", d, False)
