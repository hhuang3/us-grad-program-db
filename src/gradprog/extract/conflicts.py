"""Conflict detection and default suggestions (08 §8).

Works on observation rows (see observations.py): `field`, `value`, `value_status`, `valid_for_term`, `conflict_type`,
`excluded_by_scope_note`, `other_program_mentioned`, `group_key`, `page_id`, `owner_level`, `program_id`.
"""

from collections import defaultdict

LEVEL_RANK = {"program": 0, "department": 1, "graduate_school": 2, "university": 3}   # most specific first (§8.1)
MINIMUM_FIELDS = ("toefl_min_legacy", "toefl_min_new_scale", "ielts_min_overall")
NOT_COMPARED = ("toefl_scale_on_page", "tuition_basis", "tuition_year")   # read through tuition_amount_usd's group_key
SPECIFIC_LEVELS = ("program", "department")


def _no_basis(row):
    return row["field"] == "tuition_amount_usd" and row["group_key"].startswith("|")   # already in review (§8.3)


def _other_deadline(row):
    return row["field"] == "deadline" and row["value"].get("deadline_type") == "other"    # not the same kind of date (§8.2)


def _comparable(row):
    return (row["value_status"] == "found" and row["field"] not in NOT_COMPARED and row["value"] is not None
            and row["valid_for_term"] != "term_unknown" and not row["excluded_by_scope_note"] and not _no_basis(row)
            and not _other_deadline(row))


def _value(row):
    value = row["value"]
    if row["field"] == "deadline":
        return value.get("deadline_date") or ("rolling" if value.get("is_rolling") else None)
    return value.strip().lower() if isinstance(value, str) else float(value) if not isinstance(value, bool) else value


def _groups(rows):
    groups = defaultdict(list)
    for row in rows:
        if _comparable(row):
            groups[row["program_id"], row["field"], row["valid_for_term"], row["group_key"]].append(row)
    return groups


def in_page_conflicts(rows):
    """conflict types per row index for one call's rows; written on the observation (§8.3, §8.4 signals 1 and 2)."""
    out = {id(row): [] for row in rows}
    for group in _groups(rows).values():
        if len({_value(r) for r in group}) > 1:
            for row in group:
                out[id(row)].append("in_page_contradiction")
    for row in rows:
        if row["value_status"] in ("found", "referenced_elsewhere", "mentioned_without_value") and (
                row["other_program_mentioned"] or row["excluded_by_scope_note"]):
            out[id(row)].append("cross_program_contamination")
    return out


def _below_minimum(group):
    """(rows under the graduate school's minimum, the graduate school's rows) (§8.1)."""
    floors = [r for r in group if r["owner_level"] == "graduate_school"]
    if not floors or group[0]["field"] not in MINIMUM_FIELDS:
        return [], []
    floor = max(_value(r) for r in floors)
    below = [r for r in group if r["owner_level"] in SPECIFIC_LEVELS and _value(r) < floor]
    return below, floors if below else []


def cross_page_conflicts(rows):
    """{observation_id: [types]} over a program's current rows; only ever written to the derived view (§8)."""
    out = defaultdict(list)
    for group in _groups(rows).values():
        if len({r["page_id"] for r in group}) < 2 or len({_value(r) for r in group}) < 2:
            continue
        if group[0]["field"] == "deadline":
            by_page = defaultdict(set)
            for row in group:
                by_page[row["page_id"]].add(_value(row))
            if len({frozenset(v) for v in by_page.values()}) > 1:
                for row in group:
                    out[row["observation_id"]].append("deadline_mismatch")
            continue
        below, floors = _below_minimum(group)
        involved = {r["observation_id"] for r in [*below, *floors]}
        for row in group:
            out[row["observation_id"]].append(
                "below_graduate_school_minimum" if row["observation_id"] in involved else "level_mismatch")
    return dict(out)


def default_suggestion(group):
    """observation_id the reviewer is pointed to, or None (§8.1, §8.2, §8.4). The choice is never automatic."""
    clean = [r for r in group if not (r["other_program_mentioned"] or r["excluded_by_scope_note"])]
    if not clean:
        return None
    below, _ = _below_minimum(group)
    if below:
        return None
    best = min(LEVEL_RANK[r["owner_level"]] for r in clean)
    top = [r for r in clean if LEVEL_RANK[r["owner_level"]] == best]
    return top[0]["observation_id"] if len({_value(r) for r in top}) == 1 else None


def suggestions(rows):
    out = {}
    for group in _groups(rows).values():
        if len({_value(r) for r in group}) > 1:
            pick = default_suggestion(group)
            for row in group:
                out[row["observation_id"]] = pick
    return out
