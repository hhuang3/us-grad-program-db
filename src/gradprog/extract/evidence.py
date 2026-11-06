"""Evidence and value checks (08 §6) and TOEFL scale detection (08 §9)."""

import calendar
import re

from gradprog.extract.fields import POLICIES, STEM_CLAIMS

EVIDENCE_MAX = 200
SPACES = re.compile(r"\s+")
SAME_CHARS = str.maketrans({"\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'",
                            **dict.fromkeys("\u2010\u2011\u2012\u2013\u2014\u2015\u2212", "-")})
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
MONTH_ALIASES = {9: ("Sept",)}
NEW_SCALE = re.compile(r"\bnew (?:toefl|scale)\b|\bband\b", re.IGNORECASE)
OLD_SCALE = re.compile(r"\bold scale\b|\blegacy\b|\bibt total\b", re.IGNORECASE)


def squeeze(text):
    return SPACES.sub(" ", text or "").strip()


def comparable(text):
    """The form evidence and page text are compared in (08 §6 item 1)."""
    return squeeze(text).translate(SAME_CHARS)


def is_half_step(value, low, high):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and low <= value <= high \
        and float(value * 2).is_integer()


def _number_forms(value):
    forms = {str(value)}
    if isinstance(value, float) and value.is_integer():
        forms.add(str(int(value)))
    number = float(value)
    forms.add(f"{number:,.2f}")
    if number.is_integer():
        forms.add(f"{int(number):,}")
    return forms


def number_in_evidence(value, evidence):
    """Whole-number match, ignoring thousands separators in the evidence (08 §6 item 3)."""
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", evidence)
    for form in _number_forms(value):
        if re.search(rf"(?<![\d.]){re.escape(form.replace(',', ''))}(?:\.0+)?(?!\d)(?!\.\d)", text):
            return True
    return False


def _names(month):
    full = MONTHS[month - 1]
    return (full, full[:3], *MONTH_ALIASES.get(month, ()))


def date_in_evidence(month, day, year, evidence):
    """The date's common wordings, with or without a year (08 §6 item 3)."""
    names = "|".join(_names(month))
    worded_day = rf"0?{day}(?:st|nd|rd|th)?(?!\d)"
    year_opt = rf"(?:,?\s*{year}\b)" if year else ""
    y = str(year) if year else None
    patterns = [
        rf"\b(?:{names})\b\.?\s+{worded_day}{year_opt}",
        rf"(?<!\d){worded_day}\s+(?:of\s+)?(?:{names})\b\.?{year_opt}",
    ]
    if y:
        patterns.append(rf"(?<!\d)0?{month}/0?{day}/{y}(?!\d)")
        patterns.append(rf"(?<!\d){y}-{month:02d}-{day:02d}(?!\d)")
    else:
        patterns.append(rf"(?<![\d/])0?{month}/0?{day}(?![\d/])")
    return any(re.search(p, evidence, re.IGNORECASE) for p in patterns)


def toefl_scale(value, evidence):
    """(scale, problem): 'legacy', 'new' or None, per 08 §9. problem is 'unrecognized' or 'scale_mismatch'."""
    fits_new = is_half_step(value, 1.0, 6.0)
    fits_old = isinstance(value, (int, float)) and not isinstance(value, bool) and float(value).is_integer() \
        and 7 <= value <= 120
    says_new, says_old = bool(NEW_SCALE.search(evidence)), bool(OLD_SCALE.search(evidence))
    if says_new and says_old:      # one passage names both scales: the value alone decides, and fails if it cannot
        return ("new", None) if fits_new else ("legacy", None) if fits_old else (None, "unrecognized")
    if says_new:
        return ("new", None) if fits_new else (None, "scale_mismatch")
    if says_old:
        return ("legacy", None) if fits_old else (None, "scale_mismatch")
    return ("new", None) if fits_new else ("legacy", None) if fits_old else (None, "unrecognized")


# per-field value checks: 08 §6 item 4 with 02's types and ranges
def _whole(low, high):
    return lambda v: isinstance(v, int) and not isinstance(v, bool) and low <= v <= high


def _positive(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0


def _valid_cip(v):
    return isinstance(v, str) and re.fullmatch(r"\d{2}\.\d{4}", v.strip()) is not None


RANGES = {
    "toefl_total": lambda v: is_half_step(v, 1.0, 6.0) or _whole(0, 120)(v) or (isinstance(v, float) and v.is_integer()
                                                                                 and 0 <= v <= 120),
    "ielts_min_overall": lambda v: is_half_step(v, 0, 9),
    "length_months_min": _whole(1, 120),
    "length_months_max": _whole(1, 120),
    "credits_required": _whole(1, 300),
    "app_fee_usd": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0,
    "cip_code": _valid_cip,
}
ENUMS = {"gre_policy": POLICIES, "gmat_policy": POLICIES, "stem_claim_on_page": STEM_CLAIMS}   # free text in the schema
NUMERIC_VALUE = ("toefl_total", "ielts_min_overall", "credits_required", "app_fee_usd")


def check_entry(key, entry, page_text):
    """Reasons this entry fails 08 §6, in the spec's order; empty when it passes."""
    status = entry["value_status"]
    evidence = entry.get("evidence_text") or ""
    if not evidence.strip():
        return ["evidence_missing"]
    if comparable(evidence) not in comparable(page_text):
        return ["evidence_not_verbatim"]
    if len(evidence) > EVIDENCE_MAX:
        return ["evidence_too_long"]
    confidence = entry.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        return ["confidence_out_of_range"]
    if status == "referenced_elsewhere" and not (entry.get("reference_target") or "").strip():
        return ["reference_target_missing"]
    if status != "found":
        return []
    return _check_found(key, entry, evidence)


def _check_found(key, entry, evidence):
    if key == "deadlines":
        return _check_deadline(entry, evidence)
    if key == "tuition":
        return _check_tuition(entry, evidence)
    value = entry["value"]
    if value is None:
        return ["value_missing"]
    if (key in RANGES and not RANGES[key](value)) or (key in ENUMS and value not in ENUMS[key]):
        return ["value_out_of_range"]
    if key in NUMERIC_VALUE and not number_in_evidence(value, evidence):
        return ["value_not_in_evidence"]
    if key == "cip_code" and value.strip() not in evidence:
        return ["value_not_in_evidence"]
    return []                 # length is written in many ways ("1 year"), enums are not compared (08 §6 item 3)


def _check_deadline(entry, evidence):
    month, day, year = entry["deadline_month"], entry["deadline_day"], entry["deadline_year"]
    if month is None and day is None and year is None:
        return [] if entry.get("is_rolling") else ["value_missing"]
    if month is None or day is None or not 1 <= month <= 12 or not 1 <= day <= 31:
        return ["value_out_of_range"]
    if year is not None and not 2000 <= year <= 2100:
        return ["value_out_of_range"]
    if day > calendar.monthrange(year or 2000, month)[1]:   # 2000 is a leap year: February 29 without a year passes
        return ["value_out_of_range"]
    if not date_in_evidence(month, day, year, evidence):
        return ["value_not_in_evidence"]
    return []


def _check_tuition(entry, evidence):
    amount = entry["tuition_amount_usd"]
    if amount is None:                 # a missing basis keeps the amount and goes to review (08 §3.1)
        return ["value_missing"]
    if not _positive(amount):
        return ["value_out_of_range"]
    if not number_in_evidence(amount, evidence):
        return ["value_not_in_evidence"]
    return []
