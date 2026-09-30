"""CIP code normalization and CIP 2020 parsing (docs/spec/03_stem_logic.md §1, 01 §2)."""

import re

import pandas as pd

CIP6_A = re.compile(r"^\d{2}\.\d{4}$")
CIP6_B = re.compile(r"^\d\.\d{4}$")
CIP6_C = re.compile(r"^\d{6}$")
CIP4_A = re.compile(r"^\d{2}\.\d{2}$")
CIP4_B = re.compile(r"^\d{4}$")
EXCEL_WRAPPED = re.compile(r'^="(.*)"$', re.DOTALL)
# str.strip() covers  , tabs and newlines; ASCII-only digits are enforced by the patterns.

VALID_ACTIONS = {"No substantive changes", "New", "Moved to"}
INVALID_ACTIONS = {"Moved from", "Deleted"}
REF_COLUMNS = ["cip_code", "level", "title", "definition", "action"]


class CipFormatError(ValueError):
    """Input cannot be normalized to a standard CIP format."""


class UnknownCipError(ValueError):
    """Well-formed CIP code that is not a valid CIP 2020 code."""


def _clean(value):
    s = value.strip()
    m = EXCEL_WRAPPED.match(s)
    if m:
        s = m.group(1).strip()
    return s


def normalize_cip6(value):
    if isinstance(value, bool) or not isinstance(value, (str, float)):
        raise TypeError(f"CIP code must be str or float, got {type(value).__name__}: {value!r}")
    s = _clean(repr(value) if isinstance(value, float) else value)
    if CIP6_A.fullmatch(s) and s.isascii():
        return s
    if CIP6_B.fullmatch(s) and s.isascii():
        return "0" + s
    if CIP6_C.fullmatch(s) and s.isascii():
        return f"{s[:2]}.{s[2:]}"
    raise CipFormatError(f"cannot normalize {value!r} to a 6-digit CIP code 'NN.NNNN'")


def normalize_cip4(value):
    if not isinstance(value, str):
        raise TypeError(f"4-digit CIP code must be str, got {type(value).__name__}: {value!r}")
    s = _clean(value)
    if CIP4_A.fullmatch(s) and s.isascii():
        return s
    if CIP4_B.fullmatch(s) and s.isascii():
        return f"{s[:2]}.{s[2:]}"
    raise CipFormatError(f"cannot normalize {value!r} to a 4-digit CIP code 'NN.NN'")


def _level(code):
    for level, pattern in ((2, r"^\d{2}$"), (4, r"^\d{2}\.\d{2}$"), (6, r"^\d{2}\.\d{4}$")):
        if re.fullmatch(pattern, code):
            return level
    raise CipFormatError(f"unexpected CIPCode {code!r} in CIP 2020 file")


def parse_cip2020_csv(path):
    raw = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    unknown = sorted(set(raw["Action"]) - VALID_ACTIONS - INVALID_ACTIONS)
    if unknown:
        raise ValueError(f"unknown CIP 2020 Action value(s): {unknown}")
    kept = raw[raw["Action"].isin(VALID_ACTIONS)]
    codes = kept["CIPCode"].map(_clean)
    out = pd.DataFrame({
        "cip_code": codes,
        "level": codes.map(_level),
        "title": kept["CIPTitle"].str.strip(),
        "definition": kept["CIPDefinition"].str.strip(),
        "action": kept["Action"],
    })[REF_COLUMNS].reset_index(drop=True)
    if not out["cip_code"].is_unique:
        dups = sorted(out.loc[out["cip_code"].duplicated(), "cip_code"])
        raise ValueError(f"duplicate valid CIP 2020 codes: {dups}")
    return out


def valid_six_digit(cip2020):
    return set(cip2020.loc[cip2020["level"].astype(int) == 6, "cip_code"])


def is_valid_cip2020(code6, cip2020):
    return code6 in valid_six_digit(cip2020)
