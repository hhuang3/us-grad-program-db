"""The advisor export's tables (10 §2–§7). Pure functions: no files, no LLM, no page text."""

import json
import re
from collections import defaultdict
from dataclasses import dataclass

from gradprog.extract.evaluate import normalize_value
from gradprog.registry.names import degree_name
from gradprog.registry.tables import display_group

LEVEL_RANK = {"program": 0, "department": 1, "graduate_school": 2, "university": 3}
STATUS_RANK = ["found", "referenced_elsewhere", "mentioned_without_value", "not_mentioned", "extraction_failed",
               "page_unavailable"]
CONTAMINATED = "cross_program_contamination"
POLICY = {"required": "必需", "optional": "可选", "not_required": "不要求", "not_accepted": "不接受",
          "conditional_waiver": "可申请豁免"}
BASIS = {"per_credit": "学分", "per_term": "学期", "per_year": "年", "program_total": "项目总额"}
DEADLINE_TYPE = {"application": "申请截止", "deposit": "押金", "decision_release": "录取结果",
                 "international_docs": "签证材料", "other": "其他"}
SCOPE = {"all": "全部", "international": "国际学生", "domestic": "美国本土", "funding_consideration": "奖助评选"}
SEASON = {"fall": "秋季", "spring": "春季", "summer": "夏季"}
AREA = {"ds": "数据科学", "analytics": "商业分析", "stats": "统计", "econ": "经济", "mgmt_sci": "管理科学",
        "cs": "计算机科学", "ece": "电子与计算机工程", "fin_eng": "金融工程", "ieor": "工业工程与运筹",
        "info_sys": "信息系统", "biostat": "生物统计"}
SEASON_ORDER = {"Spring": 0, "Summer": 1, "Fall": 2}
NO_VALUE = {"referenced_elsewhere": "见其他页面", "mentioned_without_value": "提到但未给值", "not_mentioned": "页面未写明",
            "extraction_failed": "待核实（抽取失败）", "page_unavailable": "待核实（页面无法访问）"}
REASONS = {
    "term_unknown": "无法确定适用学期", "term_inferred": "学期由日期推算", "season_undetermined": "无法确定是哪一季",
    "term_date_mismatch": "写明的学期与日期不一致", "summer_date_unverified": "夏季日期没写年份",
    "toefl_scale_unrecognized": "无法判断托福分制", "conflict:in_page_contradiction": "同一页面的数值互相矛盾",
    "conflict:level_mismatch": "不同层级页面的数值不同", "conflict:below_graduate_school_minimum": "低于研究生院的最低要求",
    "conflict:deadline_mismatch": "不同页面的截止日期不同", "conflict:cross_program_contamination": "可能属于其他项目",
    "only_stale_deadlines": "项目只有已过期的截止日期", "suspected_redesign": "页面疑似改版",
    "audience_doubtful": "页面可能不是写给申请者的", "coverage_gap": "指向的页面尚未收录",
    "repeated_call_failure": "多次抽取失败", "tuition_basis_missing": "学费没写口径",
    "term_outside_intake": "该学期不在项目入学季内", "multiple_values": "页面上有多个不同的值",
    "gold_mismatch": "抽取结果与人工标注不一致",
}
PROGRAM_COLUMNS = ["方向", "学校简称", "学校", "项目", "学位", "STEM", "时长", "托福（旧制）", "托福（新制）", "雅思", "GRE", "GMAT", "申请费",
                   "学费", "学费估算总额", "入学季", "官网链接", "最后检查日期", "待核实说明"]
DEADLINE_COLUMNS = ["学校简称", "学校", "项目", "学期", "轮次", "类型", "适用对象", "日期", "状态", "待核实说明", "来源链接"]
CHANGE_COLUMNS = ["日期", "学校简称", "学校", "项目", "变化", "页面链接"]
REVIEW, STALE = "review", "stale"


@dataclass
class Cell:
    text: str
    link: str = ""
    mark: str = ""          # "", REVIEW or STALE


def school(program):
    """The short name (06 §3.1), with the Chinese name when the registry has one; the full name as a fallback."""
    short, zh = program.get("institution_short", ""), program.get("institution_name_zh", "")
    if not short:
        return program["institution_name"]
    return f"{short} / {zh}" if zh else short


def school_key(program):
    return (program.get("institution_short") or program["institution_name"]).lower()


def degree(program):
    return degree_name(program) or "其他"


def term_key(term):
    """Spring, Summer, Fall of a year in order; unknown terms last."""
    parts = (term or "").split(" ")
    if len(parts) == 2 and parts[1].isdigit() and parts[0] in SEASON_ORDER:
        return (0, int(parts[1]), SEASON_ORDER[parts[0]])
    return (1, 0, 0)


def no_check(*args):
    return False


def no_link(row):
    return None


def reason_text(reason):
    if reason.startswith("evidence_failed:"):
        return "抽取结果未通过原文核对"
    return REASONS.get(reason, reason)


def parse_view_row(row):
    """A row of derived/current.csv with its JSON columns decoded."""
    out = dict(row)
    for key in ("conflict_type", "review_reasons", "extras", "derived"):
        out[key] = json.loads(row[key]) if row.get(key) else ([] if key in ("conflict_type", "review_reasons") else {})
    if row["field"] == "deadline" and row["value"]:
        out["value"] = json.loads(row["value"])
    out["stale"] = row["stale"] == "True"
    return out


def seasons(intake_terms):
    return {s.strip() for s in (intake_terms or "").split(";") if s.strip()}


def adjusted_reasons(row, intake_terms):
    """08 §10 reasons with the export's two changes (10 §5)."""
    reasons = [r for r in row["review_reasons"] if not (r == "term_inferred" and seasons(intake_terms) == {"fall"})]
    term = row.get("valid_for_term") or ""
    season = term.split(" ")[0].lower() if term and term != "term_unknown" else ""
    if row["field"] == "deadline" and season and seasons(intake_terms) and season not in seasons(intake_terms):
        reasons.append("term_outside_intake")
    return reasons


def _level(row):
    return LEVEL_RANK.get(row["owner_level"], len(LEVEL_RANK))


def choose(rows):
    """(status, chosen rows) for one program × field (10 §3.2)."""
    found = [r for r in rows if r["value_status"] == "found" and CONTAMINATED not in r["conflict_type"]]
    if not found:
        statuses = [r["value_status"] for r in rows] or ["not_mentioned"]
        status = min(statuses, key=STATUS_RANK.index)
        return status, [r for r in rows if r["value_status"] == status]
    ids = {r["observation_id"] for r in found}
    suggested = {r["suggested_observation_id"] for r in found if r.get("suggested_observation_id") in ids}
    if suggested:
        return "found", [r for r in found if r["observation_id"] in suggested]
    best = min(_level(r) for r in found)
    return "found", [r for r in found if _level(r) == best]


def _number(value):
    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:g}"


def _score(value, field):
    return f"{float(value):.1f}" if field in ("toefl_min_new_scale", "ielts_min_overall") else _number(value)


def _money(value):
    number = float(value)
    return f"${number:,.0f}" if number.is_integer() else f"${number:,.2f}"


class ProgramRow:
    def __init__(self, program, gold_check=no_check, link_of=no_link):
        self.program, self.intake_terms = program, program["intake_terms"]
        self.gold_check, self.link_of = gold_check, link_of
        self.notes = []

    def cell(self, label, rows, render, multi_check=True, sep=" / ", field=None):
        status, chosen = choose(rows)
        link = chosen[0]["evidence_url"] if chosen else ""
        reasons = []
        for row in chosen:
            reasons.extend(adjusted_reasons(row, self.intake_terms))
        if field and self.gold_check(self.program["program_id"], field, status, chosen):
            reasons.append("gold_mismatch")
        if status != "found":
            text = NO_VALUE[status]
            if status == "referenced_elsewhere":
                if chosen[0].get("reference_target"):
                    text = f"见其他页面：{chosen[0]['reference_target']}"
                link = self.link_of(chosen[0]) or link
            if status in ("extraction_failed", "page_unavailable"):
                return self._mark(label, Cell(text, link), reasons, already_marked=True)
            return self._mark(label, Cell(text, link if status == "referenced_elsewhere" else ""), reasons)
        texts = list(dict.fromkeys(render(r) for r in chosen))
        if multi_check and len(texts) > 1:
            reasons.append("multiple_values")
        return self._mark(label, Cell(sep.join(texts), link), reasons)

    def _mark(self, label, cell, reasons, already_marked=False):
        reasons = list(dict.fromkeys(reasons))
        if reasons or already_marked:
            if not cell.text.startswith("待核实"):
                cell.text += "（待核实）"
            cell.mark = REVIEW
            if reasons:
                self.notes.append(f"{label}：" + "、".join(dict.fromkeys(reason_text(r) for r in reasons)))
            else:
                self.notes.append(f"{label}：{cell.text}")
        return cell


def _tuition_text(amount, basis, year):
    text = _money(amount["value"])
    if basis:
        text += f" / {BASIS.get(basis['value'], basis['value'])}"
    if year:
        text += f"（{normalize_value('tuition_year', year['value'])}）"
    if amount["extras"].get("includes_fees"):
        text += "，含杂费"
    return text


def program_row(program, rows, home_url, last_checked, gold_check=no_check, link_of=no_link):
    """One row of the program table (10 §3)."""
    by_field = defaultdict(list)
    for row in rows:
        by_field[row["field"]].append(row)
    out = ProgramRow(program, gold_check, link_of)

    def cell(label, field, render):
        return out.cell(label, by_field[field], render, field=field)

    stem = cell("STEM", "stem_claim_on_page",
                lambda r: {"yes": "是（页面声称）", "no": "否（页面写明）"}.get(r["value"], r["value"]))
    cips = [r for r in by_field["cip_code"] if r["value_status"] == "found"]
    if cips:
        flag = "（待核实）" if stem.text.endswith("（待核实）") else ""
        stem.text = stem.text.removesuffix(flag) + f"，CIP {cips[0]['value']}" + flag
    length = _length(out, by_field)
    tuition = _tuition(out, by_field)
    cells = [
        Cell(AREA.get(display_group(program), display_group(program))), Cell(school(program)),
        Cell(program["institution_name"]), Cell(program["program_name"]), Cell(degree(program)),
        stem, length,
        cell("托福（旧制）", "toefl_min_legacy", lambda r: _number(r["value"])),
        cell("托福（新制）", "toefl_min_new_scale", lambda r: _score(r["value"], "toefl_min_new_scale")),
        cell("雅思", "ielts_min_overall", lambda r: _score(r["value"], "ielts_min_overall")),
        cell("GRE", "gre_policy", lambda r: POLICY.get(r["value"], r["value"])),
        cell("GMAT", "gmat_policy", lambda r: POLICY.get(r["value"], r["value"])),
        cell("申请费", "app_fee_usd", lambda r: "免申请费" if float(r["value"]) == 0 else _money(r["value"])),
        tuition, _estimate(tuition, by_field),
        Cell("、".join(SEASON[s] for s in ("fall", "spring", "summer") if s in seasons(program["intake_terms"]))),
        Cell(home_url, home_url), Cell(last_checked),
    ]
    cells.append(Cell("；".join(dict.fromkeys(out.notes))))
    return cells


LENGTH_IGNORED = ("conflict:", "multiple_values")


def _length(out, by_field):
    """Tracks of different lengths make one range (10 §3.1); their differences are not a reason to check."""
    low_rows, high_rows = by_field["length_months_min"], by_field["length_months_max"]
    (low_status, lows), (high_status, highs) = choose(low_rows), choose(high_rows)
    if low_status != "found" or high_status != "found":
        return out.cell("时长", low_rows, lambda r: _number(r["value"]), field="length_months_min")
    low = min(float(r["value"]) for r in lows)
    high = max(float(r["value"]) for r in highs)
    reasons = [x for r in lows + highs for x in adjusted_reasons(r, out.intake_terms)
               if not x.startswith(LENGTH_IGNORED)]
    pid = out.program["program_id"]
    if (out.gold_check(pid, "length_months_min", "found", [r for r in lows if float(r["value"]) == low])
            or out.gold_check(pid, "length_months_max", "found", [r for r in highs if float(r["value"]) == high])):
        reasons.append("gold_mismatch")
    a, b = _number(low), _number(high)
    return out._mark("时长", Cell(f"{a} 个月" if a == b else f"{a}–{b} 个月", lows[0]["evidence_url"]), reasons)


def _tuition(out, by_field):
    groups = defaultdict(dict)
    for field in ("tuition_basis", "tuition_amount_usd", "tuition_year"):
        for row in by_field[field]:
            if row["value_status"] == "found" and row.get("group_id"):
                groups[row["group_id"]][field] = row

    def render(amount):
        group = groups.get(amount.get("group_id"), {})
        return _tuition_text(amount, group.get("tuition_basis"), group.get("tuition_year"))

    return out.cell("学费", by_field["tuition_amount_usd"], render, multi_check=False, sep="；",
                    field="tuition_amount_usd")


PER_CREDIT = re.compile(r"per_credit x (\d+) credits")


def _estimate(tuition, by_field):
    """学费估算总额 (10 §3.1): tuition_program_total_usd_est of the chosen amounts; blank when none can be worked out."""
    status, chosen = choose(by_field["tuition_amount_usd"])
    if status != "found":
        return Cell("")
    by_total = {}
    for row in chosen:
        derived = row.get("derived") or {}
        total = derived.get("tuition_program_total_usd_est")
        if total is None:
            continue
        m = PER_CREDIT.match(derived.get("method") or "")
        text = _money(total) + (f"（{_money(row['value'])} × {m.group(1)} 学分）" if m else "")
        if float(total) not in by_total or not m:      # one entry per amount; a stated total wins over the product
            by_total[float(total)] = text
    texts = list(by_total.values())
    if not texts:
        return Cell("")
    return Cell("；".join(texts) + ("（待核实）" if tuition.mark == REVIEW else ""), tuition.link, tuition.mark)


def deadline_rows(program, rows, on_date, gold_check=no_check):
    """Rows of the deadline table for one program (10 §4), as (sort key, cells)."""
    found = [r for r in rows if r["field"] == "deadline" and r["value_status"] == "found"
             and CONTAMINATED not in r["conflict_type"]]
    kept = {}
    for row in sorted(found, key=lambda r: (_level(r), r["valid_for_term"] in ("", "term_unknown"))):
        v = row["value"]
        kept.setdefault((v.get("deadline_date") or "rolling", v.get("deadline_type"), v.get("applicant_scope")), row)
    out = []
    for (date, kind, scope), row in kept.items():
        term = row["valid_for_term"]
        reasons = adjusted_reasons(row, program["intake_terms"])
        if gold_check(program["program_id"], "deadline", "found", [row]):
            reasons.append("gold_mismatch")
        reasons = list(dict.fromkeys(reasons))
        expired = date != "rolling" and date < on_date
        status = "已过期" if expired else "待核实" if reasons else ""
        mark = STALE if expired else REVIEW if reasons else ""
        cells = [Cell(school(program)), Cell(program["institution_name"]), Cell(program["program_name"]),
                 Cell("未确定" if term == "term_unknown" else term), Cell(row["value"].get("round_name") or ""),
                 Cell(DEADLINE_TYPE.get(kind, kind or "")), Cell(SCOPE.get(scope, scope or "")),
                 Cell("滚动录取" if date == "rolling" else date), Cell(status),
                 Cell("、".join(reason_text(r) for r in reasons)), Cell(row["evidence_url"], row["evidence_url"])]
        for c in cells:
            c.mark = mark
        out.append(((expired, school_key(program), term_key(term), date, program["program_name"]), cells))
    return out


def change_rows(changes, programs, page_urls):
    """The recent-change table (10 §6), newest first."""
    out = []
    for change in sorted(changes, key=lambda c: c["date"], reverse=True):
        program = programs.get(change["program_id"])
        if change["application_info"] != "yes" or program is None:
            continue
        url = page_urls.get(change["page_id"], "")
        out.append([Cell(change["date"]), Cell(school(program)), Cell(program["institution_name"]), Cell(program["program_name"]),
                    Cell(change["description"]), Cell(url, url)])
    return out
