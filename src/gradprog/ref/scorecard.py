"""College Scorecard Field of Study filtering (docs/spec/01_reference_data.md §5, 04 §6)."""

import re

import pandas as pd

from gradprog.ref.cip import normalize_cip4

MASTERS_CREDLEV = "5"
ID_COLUMNS = ["UNITID", "OPEID6", "INSTNM", "CONTROL"]
DESC_COLUMNS = ["CIPDESC", "CREDLEV", "CREDDESC"]
METRICS = [
    "IPEDSCOUNT1", "IPEDSCOUNT2", "EARN_MDN_1YR", "EARN_MDN_4YR", "EARN_MDN_5YR",
    "EARN_COUNT_WNE_1YR", "DEBT_ALL_STGP_EVAL_MDN",
]
NO_UNITID = "NA"  # rows without an IPEDS UNITID are excluded (01 §5)
MISSING = {"PS": "privacy_suppressed", "NA": "not_available"}
NUMBER = re.compile(r"^-?\d+(\.\d+)?$")


class ScorecardValueError(ValueError):
    """A Scorecard metric value is neither numeric nor a documented missing code."""


def parse_metric(raw):
    if not isinstance(raw, str):
        raise ScorecardValueError(f"metric value must be a string, got {raw!r}")
    if raw in MISSING:
        return None, MISSING[raw]
    if NUMBER.match(raw):
        return float(raw), "reported"
    raise ScorecardValueError(f"undocumented Scorecard value {raw!r} (expected a number, 'PS' or 'NA')")


def build_scorecard_fos_target(raw, targets, cip2020):
    unitid = raw["UNITID"].str.strip()
    bad = sorted(set(unitid[~unitid.str.fullmatch(r"\d+") & (unitid != NO_UNITID)]))
    if bad:
        raise ScorecardValueError(f"UNITID must be an integer or {NO_UNITID!r}, got {bad[:5]}")
    raw = raw[unitid != NO_UNITID]
    cip4 = raw["CIPCODE"].map(normalize_cip4)
    parents = sorted({c[:5] for c in targets["cip_code"]})
    keep = raw[(raw["CREDLEV"].str.strip() == MASTERS_CREDLEV) & cip4.isin(parents)].copy()
    keep["cip4"] = cip4[keep.index]

    valid6 = cip2020.loc[cip2020["level"].astype(int) == 6, "cip_code"]
    target_codes = set(targets["cip_code"])
    broader = {p: any(c.startswith(p) and c not in target_codes for c in valid6) for p in parents}

    out = pd.DataFrame({c.lower(): keep[c].str.strip() for c in ID_COLUMNS})
    out["cip4"] = keep["cip4"]
    for c in DESC_COLUMNS:
        out[c.lower()] = keep[c].str.strip()
    out["cip4_broader_than_target"] = keep["cip4"].map(broader).astype(bool)
    for m in METRICS:
        parsed = keep[m].map(parse_metric)
        out[m.lower()] = pd.array([v for v, _ in parsed], dtype="Float64")
        out[f"{m.lower()}_status"] = [s for _, s in parsed]
    out = out.assign(_u=out["unitid"].astype(int)).sort_values(["_u", "cip4"]).drop(columns="_u")
    return out.reset_index(drop=True)
