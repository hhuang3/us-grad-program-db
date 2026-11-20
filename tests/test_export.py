"""docs/spec/10_export.md: the advisor export."""

import json

import pandas as pd
from openpyxl import load_workbook

from gradprog.export.tables import REVIEW, STALE, adjusted_reasons, change_rows, choose, deadline_rows, program_row
from gradprog.export.workbook import DISCLAIMER, build, write

PROGRAM = {"program_id": "p1", "institution_name": "Alpha University", "program_name": "MS in Data Science",
           "degree_type": "ms", "intake_terms": "fall", "status": "selected"}


def row(field, value="", status="found", page="pg-1", level="program", reasons=(), conflicts=(), term="",
        oid=None, suggested="", group="", extras=None, ref=""):
    return {"observation_id": oid or f"{field}-{page}-{value}", "program_id": "p1", "page_id": page,
            "owner_level": level, "field": field, "value": value, "value_status": status, "reference_target": ref,
            "valid_for_term": term, "conflict_type": list(conflicts), "review_reasons": list(reasons),
            "suggested_observation_id": suggested, "group_id": group, "extras": extras or {},
            "evidence_url": f"https://a.edu/{page}", "stale": False}


def deadline(date, kind="application", term="Fall 2027", page="pg-1", level="program", reasons=(), scope="all",
             conflicts=(), rolling=False):
    return row("deadline", {"deadline_date": date, "deadline_type": kind, "applicant_scope": scope,
                            "round_name": "Round 1", "is_rolling": rolling},
               page=page, level=level, reasons=reasons, term=term, conflicts=conflicts, oid=f"d-{date}-{page}-{kind}")


def cells(rows, program=PROGRAM):
    out = program_row(program, rows, "https://a.edu", "2026-11-15")
    return dict(zip(["学校", "项目", "学位", "STEM", "时长", "托福（旧制）", "托福（新制）", "雅思", "GRE", "GMAT", "申请费",
                     "学费", "入学季", "官网链接", "最后检查日期", "待核实说明"], out))


# 10 §3.2
def test_most_specific_level_wins():
    status, chosen = choose([row("toefl_min_legacy", "100", level="graduate_school"), row("toefl_min_legacy", "90")])
    assert status == "found" and [r["value"] for r in chosen] == ["90"]


def test_a_suggestion_overrides_the_level():
    rows = [row("toefl_min_legacy", "100", level="graduate_school", oid="g"),
            row("toefl_min_legacy", "90", oid="p", suggested="g")]
    assert [r["value"] for r in choose(rows)[1]] == ["100"]


def test_contaminated_values_are_dropped():
    rows = [row("gre_policy", "required", conflicts=["cross_program_contamination"]), row("gre_policy", "optional", page="pg-2")]
    assert [r["value"] for r in choose(rows)[1]] == ["optional"]


def test_no_value_takes_the_most_informative_status():
    rows = [row("app_fee_usd", status="not_mentioned"), row("app_fee_usd", status="referenced_elsewhere", page="pg-2")]
    assert choose(rows)[0] == "referenced_elsewhere"


# 10 §3.1, §3.3
def test_values_are_written_in_chinese():
    c = cells([row("gre_policy", "optional"), row("gmat_policy", "conditional_waiver"), row("app_fee_usd", "0"),
               row("toefl_min_new_scale", "4.5"), row("ielts_min_overall", "7"), row("stem_claim_on_page", "yes"),
               row("cip_code", "30.7001"), row("length_months_min", "9"), row("length_months_max", "18")])
    assert c["GRE"].text == "可选" and c["GMAT"].text == "可申请豁免" and c["申请费"].text == "免申请费"
    assert c["托福（新制）"].text == "4.5" and c["雅思"].text == "7.0"
    assert c["STEM"].text == "是（页面声称），CIP 30.7001" and c["时长"].text == "9–18 个月"
    assert c["学位"].text == "MS" and c["入学季"].text == "秋季" and c["GRE"].link == "https://a.edu/pg-1"


def test_tuition_shows_amount_basis_year_and_fees():
    c = cells([row("tuition_amount_usd", "1288", group="g1", extras={"includes_fees": False}),
               row("tuition_basis", "per_credit", group="g1"), row("tuition_year", "2026-2027", group="g1"),
               row("tuition_amount_usd", "61824", group="g2", extras={"includes_fees": True}),
               row("tuition_basis", "per_year", group="g2")])
    assert c["学费"].text == "$1,288 / 学分（2026-2027）；$61,824 / 年，含杂费"
    assert c["学费"].mark == ""


def test_missing_values_are_named_not_left_blank():
    c = cells([row("gre_policy", status="referenced_elsewhere", ref="Graduate School page"),
               row("gmat_policy", status="not_mentioned"), row("app_fee_usd", status="mentioned_without_value"),
               row("toefl_min_legacy", status="extraction_failed")])
    assert c["GRE"].text == "见其他页面：Graduate School page" and c["GMAT"].text == "未提及"
    assert c["申请费"].text == "提到但未给值"
    assert c["托福（旧制）"].text == "待核实（抽取失败）" and c["托福（旧制）"].mark == REVIEW
    assert c["雅思"].text == "未提及"


def test_review_reasons_mark_the_cell_and_explain_it():
    c = cells([row("toefl_min_legacy", "90", reasons=["conflict:in_page_contradiction"]),
               row("toefl_min_legacy", "95", reasons=["conflict:in_page_contradiction"])])
    assert c["托福（旧制）"].text == "90 / 95（待核实）" and c["托福（旧制）"].mark == REVIEW
    assert c["待核实说明"].text == "托福（旧制）：同一页面的数值互相矛盾、页面上有多个不同的值"


def test_two_values_without_a_reason_are_still_marked():
    c = cells([row("gre_policy", "optional"), row("gre_policy", "not_required", page="pg-2")])
    assert c["GRE"].mark == REVIEW and "页面上有多个不同的值" in c["待核实说明"].text


# 10 §5
def test_inferred_term_is_not_a_review_reason_for_fall_only_programs():
    d = deadline("2027-01-07", reasons=["term_inferred"])
    assert adjusted_reasons(d, "fall") == []
    assert adjusted_reasons(d, "fall;spring") == ["term_inferred"]


def test_a_term_outside_the_intake_is_marked():
    assert adjusted_reasons(deadline("2027-10-01", term="Spring 2028"), "fall") == ["term_outside_intake"]
    assert adjusted_reasons(deadline("2027-10-01", term="term_unknown"), "fall") == []


# 10 §4
def test_deadlines_dedupe_by_most_specific_page_and_expire_on_the_export_date():
    rows = [deadline("2027-01-07", page="pg-2", level="graduate_school"), deadline("2027-01-07"),
            deadline("2026-10-13"), deadline("2027-10-01", term="Spring 2028")]
    out = [c for _, c in sorted(deadline_rows(PROGRAM, rows, "2026-11-20"), key=lambda x: x[0])]
    assert [c[6].text for c in out] == ["2027-01-07", "2027-10-01", "2026-10-13"]
    assert out[0][9].text == "https://a.edu/pg-1"
    assert (out[1][7].text, out[1][1].mark, out[1][8].text) == ("待核实", REVIEW, "该学期不在项目入学季内")
    assert (out[2][7].text, out[2][0].mark) == ("已过期", STALE)


def test_a_date_on_two_pages_keeps_the_one_with_a_term():
    rows = [deadline("2027-06-30", term="term_unknown", page="pg-2"), deadline("2027-06-30", page="pg-3")]
    out = deadline_rows(PROGRAM, rows, "2026-11-20")
    assert len(out) == 1 and out[0][1][2].text == "Fall 2027"


def test_rolling_and_unknown_terms_are_written_out():
    out = deadline_rows(PROGRAM, [deadline(None, term="term_unknown", rolling=True)], "2026-11-20")
    cells_ = out[0][1]
    assert cells_[6].text == "滚动录取" and cells_[2].text == "未确定"


def test_contaminated_deadlines_are_left_out():
    assert deadline_rows(PROGRAM, [deadline("2027-01-07", conflicts=["cross_program_contamination"])], "2026-11-20") == []


# 10 §6
def test_changes_keep_application_info_newest_first():
    changes = [{"date": "2026-11-08", "page_id": "pg-1", "program_id": "p1", "application_info": "yes", "description": "a"},
               {"date": "2026-11-15", "page_id": "pg-1", "program_id": "p1", "application_info": "yes", "description": "b"},
               {"date": "2026-11-15", "page_id": "pg-1", "program_id": "p1", "application_info": "no", "description": "c"},
               {"date": "2026-11-15", "page_id": "pg-1", "program_id": "p9", "application_info": "yes", "description": "d"}]
    out = change_rows(changes, {"p1": PROGRAM}, {"pg-1": "https://a.edu/pg-1"})
    assert [r[3].text for r in out] == ["b", "a"] and out[0][4].link == "https://a.edu/pg-1"


# 10 §1, §2
class Registry:
    def __init__(self):
        self.programs = pd.DataFrame([PROGRAM, {**PROGRAM, "program_id": "p2", "program_name": "Holdout MS"}])
        self.pages = pd.DataFrame([
            {"page_id": "pg-1", "url": "https://a.edu/pg-1", "page_type": "program_home", "url_status": "confirmed"},
            {"page_id": "pg-2", "url": "https://a.edu/pg-2", "page_type": "admissions", "url_status": "confirmed"}])
        self.program_pages = pd.DataFrame([{"program_id": "p1", "page_id": "pg-1", "scope_note": ""},
                                           {"program_id": "p2", "page_id": "pg-2", "scope_note": ""}])


def csv_row(r):
    out = {k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v)) for k, v in r.items()}
    out["stale"] = "False"
    out["value"] = json.dumps(r["value"]) if isinstance(r["value"], dict) else r["value"]
    return out


def test_workbook_has_four_sheets_skips_holdout_and_carries_no_page_text(tmp_path):
    index = pd.DataFrame([{"page_id": "pg-1", "retrieved_at": "2026-11-15T11:00:00Z", "classification": "unchanged"},
                          {"page_id": "pg-2", "retrieved_at": "2026-11-15T11:00:00Z", "classification": "unchanged"}])
    view = [csv_row(row("gre_policy", "optional")), csv_row(deadline("2027-01-07")),
            csv_row({**row("gre_policy", "required", page="pg-2"), "program_id": "p2"})]
    for r in view:
        r["evidence_text"] = "secret page text"
    sheets, counts = build(view, Registry(), index, [], "2026-11-20", holdout={"p2"})
    assert list(sheets) == ["说明", "项目总表", "截止日期", "最近变化"]
    assert counts["programs"] == 1 and counts["deadlines"] == 1
    path = tmp_path / "out.xlsx"
    write(sheets, path)
    book = load_workbook(path)
    text = " ".join(str(c.value) for s in book for r in s.iter_rows() for c in r)
    assert DISCLAIMER in text and "secret" not in text and "Holdout MS" not in text
    assert book["项目总表"]["A2"].value == "Alpha University"
    sheets, counts = build(view, Registry(), index, [], "2026-11-20", holdout={"p2"}, include_holdout=True)
    assert counts["programs"] == 2
