"""Reasons an observation is listed first in the review queue (08 §10).

Row 7 waits for the fact layer. Row 6 (low confidence) is suspended until the gold set shows what confidence is worth.
"""

from collections import defaultdict


def _is_url(text):
    return text.startswith(("http://", "https://", "www."))


def coverage_gap(row, program_rows, program_urls):
    """Row 12: a reference no registered page answers.

    A URL is matched against the program's registered pages. Link text cannot be matched, so the field must then be
    `found` on another page of the program.
    """
    target = (row["reference_target"] or "").strip()
    if _is_url(target):
        return target.rstrip("/").removeprefix("https://").removeprefix("http://") not in program_urls
    return not any(r["field"] == row["field"] and r["value_status"] == "found" and r["page_id"] != row["page_id"]
                   for r in program_rows)


def only_stale_deadlines(program_rows):
    """Row 5: the program's dated deadlines have all passed, so the pages may not have been updated yet."""
    dated = [r for r in program_rows if r["field"] == "deadline" and r["value_status"] == "found"
             and (r["value"] or {}).get("deadline_date")]
    return bool(dated) and all(r["stale"] for r in dated)


def row_reasons(row):
    reasons = list(row["review_from_rules"])    # rows 1, 2, 3, 9, 10, 13, 14, 15: set where they were decided
    reasons.extend(f"conflict:{c}" for c in row["conflict_type"])              # row 4
    if row["snapshot_classification"] == "suspected_redesign":
        reasons.append("suspected_redesign")                                   # row 8
    if row["audience"] != "applicants":
        reasons.append("audience_doubtful")                                    # row 11
    return reasons


def review_reasons(rows, urls_by_program):
    """{observation_id: [reasons]} over the current rows."""
    by_program = defaultdict(list)
    for row in rows:
        by_program[row["program_id"]].append(row)
    out = {}
    for program, program_rows in by_program.items():
        stale_only = only_stale_deadlines(program_rows)
        for row in program_rows:
            reasons = row_reasons(row)
            if row["value_status"] == "referenced_elsewhere" and coverage_gap(
                    row, program_rows, urls_by_program.get(program, set())):
                reasons.append("coverage_gap")
            if stale_only and row["field"] == "deadline" and row["value_status"] == "found":
                reasons.append("only_stale_deadlines")
            out[row["observation_id"]] = sorted(set(reasons))
    return out
