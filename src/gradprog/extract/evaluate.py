"""Score the current observations against the gold set (09 §1, §5). Only `run_evaluation` touches files; no LLM."""

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import yaml

GROUPS = {"Noah": "independent", "Noah+Claude": "assisted"}
LABELS = {"independent": "独立标注", "assisted": "Claude 协助"}
STATUS_RANK = ["found", "referenced_elsewhere", "mentioned_without_value", "not_mentioned", "extraction_failed",
               "page_unavailable"]
CONTAMINATED = "cross_program_contamination"
ACADEMIC_YEAR = re.compile(r"^((?:19|20)\d{2})\s*[-–—/]\s*(\d{2,4})$")
NUMERIC = {"toefl_min_legacy", "toefl_min_new_scale", "ielts_min_overall", "tuition_amount_usd", "length_months_min",
           "length_months_max", "credits_required", "app_fee_usd"}
COUNTS = ("extracted_values", "correct_values", "gold_values", "missed_values", "no_value_total", "no_value_correct",
          "false_positives", "term_total", "term_correct")


def normalize_value(field, value):
    if field in NUMERIC:
        return float(value)
    text = str(value).strip()
    if field == "tuition_year":
        m = ACADEMIC_YEAR.match(text)
        if m:
            return f"{m.group(1)}-{m.group(1)[:2]}{m.group(2)[-2:]}"
    return text.lower()


def _observed_key(row):
    if row["field"] != "deadline":
        return normalize_value(row["field"], row["value"])
    return row["value"].get("deadline_date") or "rolling", row["value"].get("deadline_type")


def _gold_key(row):
    if row["field"] != "deadline":
        return normalize_value(row["field"], row["value"])
    return row["value"] or "rolling", row["deadline_type"]


def _pages(gold_rows):
    return {s[s.index("-pg-") + 1:] for row in gold_rows for s in row["snapshot_ids"].split(";")}


def _excluded(row, rules):
    for rule in rules:
        for item in rule.get("observed", ()):
            if item["program_id"] == row["program_id"] and item["field"] == row["field"] \
                    and row["value_status"] == "found" and item["date"] == row["value"].get("deadline_date"):
                return True
    return False


def _status(rows):
    return min((r["value_status"] for r in rows), key=STATUS_RANK.index, default="not_mentioned")


def _bucket(confidence):
    if confidence is None or confidence == "":
        return "none"
    return "<0.7" if float(confidence) < 0.7 else "0.7-0.9" if float(confidence) < 0.9 else ">=0.9"


def _empty_group():
    return {"total": dict.fromkeys(COUNTS, 0), "by_field": defaultdict(lambda: dict.fromkeys(COUNTS, 0)),
            "by_program": defaultdict(lambda: dict.fromkeys(COUNTS, 0)),
            "review_recall": {f: {"total": 0, "in_review": 0, "with_signal": 0} for f in ("contradictory", "stale", "contamination")},
            "confidence": {b: {"right": 0, "wrong": 0} for b in ("<0.7", "0.7-0.9", ">=0.9", "none")}}


def _has_signal(flag, rows):
    if flag == "contradictory":
        return any(r["conflict_type"] for r in rows)
    if flag == "stale":
        return any(r["stale"] for r in rows)
    return any(CONTAMINATED in r["conflict_type"] for r in rows)


def _score_pair(answers, rows, add, recall, confidence, differences):
    """One program × field."""
    program, field = answers[0]["program_id"], answers[0]["field"]
    found = [r for r in rows if r["value_status"] == "found" and r["value"] is not None]
    if any(a["is_rolling"] == "true" for a in answers):
        found = [r for r in found if field != "deadline" or r["value"].get("deadline_date")]
    by_key = defaultdict(list)
    for row in found:
        by_key[_observed_key(row)].append(row)
    wanted = defaultdict(list)
    for answer in answers:
        if answer["value_status"] == "found":
            wanted[_gold_key(answer)].append(answer)

    add("extracted_values", len(by_key))
    add("gold_values", len(wanted))
    add("correct_values", len(set(by_key) & set(wanted)))
    add("missed_values", len(set(wanted) - set(by_key)))
    for key in set(wanted) - set(by_key):
        differences.append({"kind": "missed", "program_id": program, "field": field, "gold": str(key)})
    for key in set(by_key) - set(wanted):
        differences.append({"kind": "wrong_value", "program_id": program, "field": field, "observed": str(key),
                            "pages": sorted({r["page_id"] for r in by_key[key]})})
    for key in set(wanted) & set(by_key):
        add("term_total", 1)
        expected = {a["valid_for_term"] for a in wanted[key]}
        terms = {r["valid_for_term"] or "" for r in by_key[key]}
        if terms <= expected:
            add("term_correct", 1)
        else:
            differences.append({"kind": "wrong_term", "program_id": program, "field": field, "value": str(key),
                                "gold": sorted(expected), "observed": sorted(terms)})
    for row in found:
        side = "right" if _observed_key(row) in wanted else "wrong"
        confidence[_bucket(row.get("confidence"))][side] += 1
    if not wanted:
        add("no_value_total", 1)
        status = _status(rows)
        if status == answers[0]["value_status"]:
            add("no_value_correct", 1)
        else:
            differences.append({"kind": "wrong_status", "program_id": program, "field": field,
                                "gold": answers[0]["value_status"], "observed": status})
        if status == "found":
            add("false_positives", 1)
    for answer in answers:
        matched = by_key.get(_gold_key(answer), []) if answer["value_status"] == "found" else []
        for flag in filter(None, answer["flags"].split(";")):
            if flag in recall:
                recall[flag]["total"] += 1
                recall[flag]["in_review"] += any(r["review_reasons"] for r in matched)
                recall[flag]["with_signal"] += _has_signal(flag, matched)


def evaluate(gold_rows, view_rows, exclusions=(), include_flagged=False):
    """Counts per annotation group and the differences behind them. Values only, never evidence text."""
    excluded_rows = {r for rule in exclusions for r in rule.get("gold_rows", ())}
    pages = _pages(gold_rows)
    answers = defaultdict(list)
    all_answers = defaultdict(list)
    for row in gold_rows:
        all_answers[row["program_id"], row["field"]].append(row)
        if row["row_id"] not in excluded_rows:
            answers[row["program_id"], row["field"]].append(row)
    rows = defaultdict(list)
    for row in view_rows:
        if row["page_id"] not in pages or (row["program_id"], row["field"]) not in all_answers:
            continue
        if not include_flagged and CONTAMINATED in row["conflict_type"]:
            continue
        if not _excluded(row, exclusions):
            rows[row["program_id"], row["field"]].append(row)
    groups = {name: _empty_group() for name in LABELS}
    differences = []
    for key, mine in answers.items():
        group = groups[GROUPS[mine[0]["annotated_by"]]]

        def add(name, n, group=group, key=key):
            group["total"][name] += n
            group["by_program"][key[0]][name] += n
            group["by_field"][key[1]][name] += n

        _score_pair(mine, rows[key], add, group["review_recall"], group["confidence"], differences)
    for group in groups.values():
        group["by_field"] = dict(group["by_field"])
        group["by_program"] = dict(group["by_program"])
    return {"groups": groups, "differences": differences}


def changed_pages(gold_rows, view_rows, norm_sha):
    """Pages whose extracted snapshot has different text from the gold snapshot (09 §5). norm_sha: snapshot_id -> sha."""
    gold_snapshots = {s[s.index("-pg-") + 1:]: s for row in gold_rows for s in row["snapshot_ids"].split(";")}
    used = {r["page_id"]: r["snapshot_id"] for r in view_rows if r["page_id"] in gold_snapshots}
    return sorted(p for p, s in used.items() if norm_sha.get(s) != norm_sha.get(gold_snapshots[p]))


def _rate(top, bottom):
    return f"{top}/{bottom} ({top / bottom:.1%})" if bottom else "–"


def _metrics(c):
    return [_rate(c["correct_values"], c["extracted_values"]), _rate(c["missed_values"], c["gold_values"]),
            _rate(c["no_value_correct"], c["no_value_total"]), _rate(c["false_positives"], c["no_value_total"]),
            _rate(c["term_correct"], c["term_total"])]


def render_report(result):
    head = "| {} | 准确率 | 漏抽率 | 无值状态正确率 | 误报率 | 学期正确率 |\n|---|---|---|---|---|---|"
    out = []
    for name, label in LABELS.items():
        group = result["groups"][name]
        out += [f"## {label}", "", head.format("范围"), "| **合计** | " + " | ".join(_metrics(group["total"])) + " |"]
        out += [f"| {p} | " + " | ".join(_metrics(c)) + " |" for p, c in sorted(group["by_program"].items())]
        out += ["", head.format("字段")]
        out += [f"| {f} | " + " | ".join(_metrics(c)) + " |" for f, c in group["by_field"].items()]
        out += ["", "审核召回（进审核 / 有对应信号 / 总数）："]
        out += [f"- {f}: {r['in_review']} / {r['with_signal']} / {r['total']}" for f, r in group["review_recall"].items()]
        out += ["", "confidence（对 / 错）："]
        out += [f"- {b}: {c['right']} / {c['wrong']}" for b, c in group["confidence"].items()]
        out.append("")
    return "\n".join(out)


def run_evaluation(gold_path, view, index, label, stats_dir, details_dir,
                   exclusions_path=Path(__file__).resolve().parents[3] / "config" / "extraction" / "eval_exclusions.yaml"):
    """Write the counts (for git) and the value-level differences (local only), and return the report (09 §5)."""
    with open(gold_path, encoding="utf-8", newline="") as fh:
        gold_rows = list(csv.DictReader(fh))
    exclusions = yaml.safe_load(Path(exclusions_path).read_text(encoding="utf-8")) or []
    main = evaluate(gold_rows, view, exclusions)
    flagged = evaluate(gold_rows, view, exclusions, include_flagged=True)
    sha = dict(zip(index["snapshot_id"], index["norm_sha256"]))
    changed = changed_pages(gold_rows, view, sha)
    versions = sorted({(r["prompt_version"], r["extract_rules_version"]) for r in view})
    summary = {"label": label, "prompt_and_rules_versions": versions, "changed_pages": changed,
               "exclusions": [r["reason"] for r in exclusions], "groups": main["groups"],
               "groups_counting_contaminated_rows": {n: g["total"] for n, g in flagged["groups"].items()}}
    Path(stats_dir, f"eval_{label}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", "utf-8")
    columns = ["kind", "program_id", "field", "gold", "observed", "value", "pages"]
    with open(Path(details_dir, f"eval_{label}_differences.csv"), "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(main["differences"])
    lines = [render_report(main), f"正文与 gold 快照不同的页面：{', '.join(changed) or '无'}", "", "计入污染标记行时的合计："]
    lines += [f"- {LABELS[n]}: " + " | ".join(_metrics(g["total"])) for n, g in flagged["groups"].items()]
    return "\n".join(lines)
