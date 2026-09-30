"""Target CIP configuration (docs/spec/04_candidate_selection.md §1)."""

import re

import pandas as pd

CONFIG_COLUMNS = ["pattern", "kind", "cip_group", "label"]
GROUP_ORDER = ("ds", "analytics", "stats", "mgmt_sci", "econ")
MUST_EXIST = ("30.7102", "30.7103", "30.7104", "45.0603", "27.0601")
PATTERNS = {"prefix": re.compile(r"^\d{2}\.\d{2}$"), "exact": re.compile(r"^\d{2}\.\d{4}$")}


class TargetCipError(ValueError):
    """Target CIP configuration is inconsistent with CIP 2020."""


def load_target_config(path):
    config = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(config.columns) != CONFIG_COLUMNS:
        raise TargetCipError(f"target config columns must be {CONFIG_COLUMNS}, got {list(config.columns)}")
    return config


def expand_targets(config, cip2020, must_exist=None):
    must_exist = MUST_EXIST if must_exist is None else must_exist
    valid6 = sorted(cip2020.loc[cip2020["level"].astype(int) == 6, "cip_code"])
    problems, rows = [], []
    for r in config.itertuples(index=False):
        where = f"{r.pattern},{r.kind},{r.cip_group}"
        if r.cip_group not in GROUP_ORDER:
            problems.append(f"{where}: cip_group must be one of {list(GROUP_ORDER)}")
        if r.kind not in PATTERNS:
            problems.append(f"{where}: kind must be prefix or exact")
            continue
        if not PATTERNS[r.kind].match(r.pattern):
            problems.append(f"{where}: pattern {r.pattern!r} is not a valid {r.kind} pattern")
            continue
        if r.kind == "prefix":
            codes = [c for c in valid6 if c.startswith(r.pattern)]
            if not codes:
                problems.append(f"{where}: prefix {r.pattern} matches no valid CIP 2020 6-digit code")
        else:
            codes = [r.pattern] if r.pattern in valid6 else []
            if not codes:
                problems.append(f"{where}: {r.pattern} is not a valid CIP 2020 6-digit code")
        rows += [(c, r.cip_group, r.label) for c in codes]

    out = pd.DataFrame(rows, columns=["cip_code", "cip_group", "label"])
    groups = out.groupby("cip_code")["cip_group"].nunique()
    for code in sorted(groups[groups > 1].index):
        problems.append(f"{code} is assigned to several groups: {sorted(set(out.loc[out.cip_code == code, 'cip_group']))}")
    out = out.drop_duplicates("cip_code", keep="first")
    missing = [c for c in must_exist if c not in set(out["cip_code"])]
    if missing:
        problems.append(f"required codes missing from the expanded targets: {missing}")
    if problems:
        raise TargetCipError("target CIP problems:\n- " + "\n- ".join(problems))
    return out.sort_values("cip_code").reset_index(drop=True)
