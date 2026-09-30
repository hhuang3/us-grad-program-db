"""IPEDS Completions filtering and candidate list (docs/spec/04_candidate_selection.md §3–4)."""

import pandas as pd

from gradprog.ref.cip import normalize_cip6
from gradprog.ref.stem import cip_on_stem_list
from gradprog.ref.targets import GROUP_ORDER

MASTERS_AWLEVEL = "7"
# 50 states + DC (04 §4.1); territories and freely associated states are excluded from candidates.
ALLOWED_STATES = frozenset(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY "
    "NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split()
)
IPEDS_COLUMNS = [
    "unitid", "state", "cip_code", "cip_group", "completions_masters",
    "completions_masters_second_major", "completions_masters_nonresident", "imputation_flag", "data_year",
]
CANDIDATE_COLUMNS = [
    "cip_group", "rank_in_group", "unitid", "institution_name", "state", "cip_code", "cip_title",
    "on_stem_list", "completions_masters", "completions_masters_second_major",
    "completions_masters_nonresident", "institution_target_cip_count", "data_year",
]


class IpedsError(ValueError):
    """IPEDS input violates a documented rule."""


def select_revised_member(names):
    revised = [n for n in names if n.lower().endswith("_rv.csv")]
    if len(revised) != 1:
        raise IpedsError(f"expected exactly one final/revised '_rv.csv' member, found {revised} in {names}")
    return revised[0]


def read_ipeds_csv(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig", low_memory=False)


def _to_int(series, name):
    s = series.str.strip()
    bad = sorted(set(s[~s.str.fullmatch(r"\d+")]))
    if bad:
        raise IpedsError(f"{name} must be non-negative integers, got {bad[:5]}")
    return s.astype(int)


def _hd_lookup(hd, unitids):
    hd = hd.assign(UNITID=hd["UNITID"].str.strip()).set_index("UNITID")
    missing = sorted(set(unitids) - set(hd.index), key=int)
    if missing:
        raise IpedsError(f"UNITID(s) not found in IPEDS HD: {missing}")
    return hd


def _sort_unitid(df, *more):
    return df.assign(_u=df["unitid"].astype(int)).sort_values(["_u", *more]).drop(columns="_u")


def build_ipeds_masters_target(completions, hd, targets, data_year):
    c = completions[completions["CIPCODE"].str.strip() != "99"].copy()
    c["cip_code"] = c["CIPCODE"].map(normalize_cip6)
    c["UNITID"] = c["UNITID"].str.strip()
    c = c[(c["AWLEVEL"].str.strip() == MASTERS_AWLEVEL) & c["cip_code"].isin(set(targets["cip_code"]))]
    c["MAJORNUM"] = c["MAJORNUM"].str.strip()
    bad = sorted(set(c["MAJORNUM"]) - {"1", "2"})
    if bad:
        raise IpedsError(f"MAJORNUM must be 1 or 2, got {bad}")
    dup = c[c.duplicated(["UNITID", "cip_code", "MAJORNUM"], keep=False)]
    if len(dup):
        raise IpedsError(f"duplicate (UNITID, CIPCODE, MAJORNUM) rows: {dup[['UNITID', 'cip_code', 'MAJORNUM']].values.tolist()[:5]}")
    c["CTOTALT"] = _to_int(c["CTOTALT"], "CTOTALT")
    c["CNRALT"] = _to_int(c["CNRALT"], "CNRALT")

    first = c[c["MAJORNUM"] == "1"]
    second = c[c["MAJORNUM"] == "2"][["UNITID", "cip_code", "CTOTALT"]].rename(columns={"CTOTALT": "second"})
    t = first.merge(second, on=["UNITID", "cip_code"], how="left")
    t["second"] = t["second"].fillna(0).astype(int)
    t = t[t["CTOTALT"] > 0]

    hd_idx = _hd_lookup(hd, t["UNITID"])
    groups = dict(zip(targets["cip_code"], targets["cip_group"]))
    out = pd.DataFrame({
        "unitid": t["UNITID"],
        "state": t["UNITID"].map(hd_idx["STABBR"].str.strip()),
        "cip_code": t["cip_code"],
        "cip_group": t["cip_code"].map(groups),
        "completions_masters": t["CTOTALT"],
        "completions_masters_second_major": t["second"],
        "completions_masters_nonresident": t["CNRALT"],
        "imputation_flag": t["XCTOTALT"].str.strip(),
        "data_year": data_year,
    })
    return _sort_unitid(out, "cip_code")[IPEDS_COLUMNS].reset_index(drop=True)


def build_candidates(ipeds_table, hd, cip2020, stem_ref):
    t = ipeds_table[ipeds_table["state"].isin(ALLOWED_STATES)].copy()
    hd_idx = _hd_lookup(hd, t["unitid"])
    titles = dict(zip(cip2020["cip_code"], cip2020["title"]))
    t["institution_name"] = t["unitid"].map(hd_idx["INSTNM"].str.strip())
    t["cip_title"] = t["cip_code"].map(titles)
    t["on_stem_list"] = t["cip_code"].map(lambda c: cip_on_stem_list(c, stem_ref)).astype(bool)
    t["institution_target_cip_count"] = t.groupby("unitid")["cip_code"].transform("count")
    t["_g"] = t["cip_group"].map({g: i for i, g in enumerate(GROUP_ORDER)})
    t["_u"] = t["unitid"].astype(int)
    t = t.sort_values(["_g", "completions_masters", "_u", "cip_code"], ascending=[True, False, True, True])
    t["rank_in_group"] = t.groupby("cip_group").cumcount() + 1
    return t[CANDIDATE_COLUMNS].reset_index(drop=True)


def build_candidates_by_institution(candidates):
    c = candidates
    base = c.groupby("unitid").agg(
        institution_name=("institution_name", "first"),
        state=("state", "first"),
        institution_target_cip_count=("cip_code", "count"),
        cip_codes=("cip_code", lambda s: ";".join(sorted(s))),
    )
    per_group = c.pivot_table(index="unitid", columns="cip_group", values="completions_masters",
                              aggfunc="sum", fill_value=0)
    for g in GROUP_ORDER:
        col = per_group[g] if g in per_group.columns else pd.Series(0, index=base.index)
        base[f"completions_{g}"] = col.reindex(base.index, fill_value=0).astype(int)
    return _sort_unitid(base.reset_index()).reset_index(drop=True)
