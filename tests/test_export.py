"""docs/spec/10_export.md: the advisor export."""

import json

import pandas as pd
from openpyxl import load_workbook

from gradprog.export.links import anchors, resolve
from gradprog.export.tables import (
    PROGRAM_COLUMNS, REVIEW, STALE, adjusted_reasons, change_rows, choose, deadline_rows, degree, program_row, school,
)
from gradprog.export.workbook import DISCLAIMER, GoldCheck, build, write

PROGRAM = {"program_id": "p1", "institution_name": "Alpha University", "institution_short": "Alpha",
           "institution_name_zh": "阿尔法大学", "program_name": "MS in Data Science", "degree_type": "ms",
           "degree_label": "", "intake_terms": "fall", "status": "selected", "cip_group": "ds"}


def row(field, value="", status="found", page="pg-1", level="program", reasons=(), conflicts=(), term="",
        oid=None, suggested="", group="", extras=None, ref=""):
    return {"observation_id": oid or f"{field}-{page}-{value}", "program_id": "p1", "page_id": page,
            "snapshot_id": f"snap-1-{page}",
            "owner_level": level, "field": field, "value": value, "value_status": status, "reference_target": ref,
            "valid_for_term": term, "conflict_type": list(conflicts), "review_reasons": list(reasons),
            "suggested_observation_id": suggested, "group_id": group, "extras": extras or {},
            "evidence_url": f"https://a.edu/{page}", "stale": False}


def deadline(date, kind="application", term="Fall 2027", page="pg-1", level="program", reasons=(), scope="all",
             conflicts=(), rolling=False):
    return row("deadline", {"deadline_date": date, "deadline_type": kind, "applicant_scope": scope,
                            "round_name": "Round 1", "is_rolling": rolling},
               page=page, level=level, reasons=reasons, term=term, conflicts=conflicts, oid=f"d-{date}-{page}-{kind}")


def cells(rows, program=PROGRAM, **kw):
    return dict(zip(PROGRAM_COLUMNS, program_row(program, rows, "https://a.edu", "2026-11-15", **kw)))


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
    assert c["GRE"].text == "见其他页面：Graduate School page" and c["GMAT"].text == "页面未写明"
    assert c["申请费"].text == "提到但未给值"
    assert c["托福（旧制）"].text == "待核实（抽取失败）" and c["托福（旧制）"].mark == REVIEW
    assert c["雅思"].text == "页面未写明"


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
    assert [c[7].text for c in out] == ["2027-01-07", "2027-10-01", "2026-10-13"]
    assert out[0][10].text == "https://a.edu/pg-1"
    assert (out[1][8].text, out[1][1].mark, out[1][9].text) == ("待核实", REVIEW, "该学期不在项目入学季内")
    assert (out[2][8].text, out[2][0].mark) == ("已过期", STALE)


def test_a_date_on_two_pages_keeps_the_one_with_a_term():
    rows = [deadline("2027-06-30", term="term_unknown", page="pg-2"), deadline("2027-06-30", page="pg-3")]
    out = deadline_rows(PROGRAM, rows, "2026-11-20")
    assert len(out) == 1 and out[0][1][3].text == "Fall 2027"


def test_rolling_and_unknown_terms_are_written_out():
    out = deadline_rows(PROGRAM, [deadline(None, term="term_unknown", rolling=True)], "2026-11-20")
    cells_ = out[0][1]
    assert cells_[7].text == "滚动录取" and cells_[3].text == "未确定"


def test_contaminated_deadlines_are_left_out():
    assert deadline_rows(PROGRAM, [deadline("2027-01-07", conflicts=["cross_program_contamination"])], "2026-11-20") == []


# 10 §6
def test_changes_keep_application_info_newest_first():
    changes = [{"date": "2026-11-08", "page_id": "pg-1", "program_id": "p1", "application_info": "yes", "description": "a"},
               {"date": "2026-11-15", "page_id": "pg-1", "program_id": "p1", "application_info": "yes", "description": "b"},
               {"date": "2026-11-15", "page_id": "pg-1", "program_id": "p1", "application_info": "no", "description": "c"},
               {"date": "2026-11-15", "page_id": "pg-1", "program_id": "p9", "application_info": "yes", "description": "d"}]
    out = change_rows(changes, {"p1": PROGRAM}, {"pg-1": "https://a.edu/pg-1"})
    assert [r[4].text for r in out] == ["b", "a"] and out[0][5].link == "https://a.edu/pg-1"


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


def test_workbook_has_four_sheets_with_filters_and_carries_no_page_text(tmp_path):
    index = pd.DataFrame([{"page_id": "pg-1", "retrieved_at": "2026-11-15T11:00:00Z", "classification": "unchanged"},
                          {"page_id": "pg-2", "retrieved_at": "2026-11-15T11:00:00Z", "classification": "unchanged"}])
    view = [csv_row(row("gre_policy", "optional")), csv_row(deadline("2027-01-07")),
            csv_row({**row("gre_policy", "required", page="pg-2"), "program_id": "p2"})]
    for r in view:
        r["evidence_text"] = "secret page text"
    sheets, counts = build(view, Registry(), index, [], "2026-11-20")
    assert list(sheets) == ["说明", "项目总表", "截止日期", "最近变化"]
    assert counts["programs"] == 2 and counts["deadlines"] == 1
    path = tmp_path / "out.xlsx"
    write(sheets, path)
    book = load_workbook(path)
    text = " ".join(str(c.value) for s in book for r in s.iter_rows() for c in r)
    assert DISCLAIMER in text and "secret" not in text and "Holdout MS" in text and "页面未写明" in text
    assert book["项目总表"]["B2"].value == "Alpha / 阿尔法大学"
    assert all(sheet.auto_filter.ref for sheet in book)


# 10 §3 (2026-11-20 revision)
def test_area_school_and_degree_columns():
    c = cells([])
    assert (c["方向"].text, c["学校简称"].text, c["学位"].text) == ("数据科学", "Alpha / 阿尔法大学", "MS")
    assert degree({**PROGRAM, "degree_type": "other", "degree_label": "MQE"}) == "MQE"
    assert degree({**PROGRAM, "degree_type": "other", "program_name": "MQM: Business Analytics"}) == "MQM"
    assert degree({**PROGRAM, "degree_type": "other", "program_name": "Master of Things"}) == "其他"
    assert school({**PROGRAM, "institution_short": ""}) == "Alpha University"
    assert school({**PROGRAM, "institution_name_zh": ""}) == "Alpha"


def test_deadlines_sort_by_school_then_term_then_date():
    beta = {**PROGRAM, "program_id": "p2", "institution_short": "Beta", "institution_name_zh": "贝塔大学"}
    rows = (deadline_rows(beta, [deadline("2027-01-01")], "2026-11-20")
            + deadline_rows(PROGRAM, [deadline("2027-02-01"), deadline("2026-12-01", term="Spring 2027"),
                                      deadline("2027-01-15")], "2026-11-20"))
    ordered = [(c[0].text, c[7].text) for _, c in sorted(rows, key=lambda x: x[0])]
    assert ordered == [("Alpha / 阿尔法大学", "2026-12-01"), ("Alpha / 阿尔法大学", "2027-01-15"),
                       ("Alpha / 阿尔法大学", "2027-02-01"), ("Beta / 贝塔大学", "2027-01-01")]


def test_reference_cells_link_to_the_named_page():
    c = cells([row("gre_policy", status="referenced_elsewhere", ref="Graduate School page")],
              link_of=lambda r: "https://grad.a.edu/req")
    assert c["GRE"].link == "https://grad.a.edu/req"
    c = cells([row("gre_policy", status="referenced_elsewhere", ref="Graduate School page")])
    assert c["GRE"].link == "https://a.edu/pg-1"


PAGE = b"""<html><body><p>See the <a href="/grad/req">Graduate School requirements page</a>.</p>
<a href="/a">here</a> <a href="/b">here</a> <a href="https://x.edu/fees">Tuition and Fees</a></body></html>"""


def test_resolve_finds_a_unique_link_by_its_text():
    links = anchors(PAGE, "html", "https://a.edu/p")
    assert resolve("Graduate School requirements page", links) == "https://a.edu/grad/req"
    assert resolve("Graduate School Tuition and Fees page", links) == "https://x.edu/fees"
    assert resolve("here", links) is None
    assert resolve("https://y.edu/z", links) == "https://y.edu/z"
    assert resolve("nothing like it", links) is None


GOLD = [{"program_id": "p1", "field": "stem_claim_on_page", "value": "yes", "value_status": "found",
         "evidence_page_id": "pg-1", "deadline_type": "", "snapshot_ids": "snap-0-pg-1;snap-0-pg-2"},
        {"program_id": "p1", "field": "toefl_min_legacy", "value": "", "value_status": "not_mentioned",
         "evidence_page_id": "", "deadline_type": "", "snapshot_ids": "snap-0-pg-1;snap-0-pg-2"},
        {"program_id": "p1", "field": "deadline", "value": "2027-01-07", "value_status": "found",
         "evidence_page_id": "pg-1", "deadline_type": "application", "snapshot_ids": "snap-0-pg-1;snap-0-pg-2"}]
SHA = {"snap-0-pg-1": "a", "snap-1-pg-1": "a", "snap-0-pg-2": "b", "snap-1-pg-2": "changed"}


def test_values_that_disagree_with_the_gold_set_are_marked():
    view = [row("stem_claim_on_page", status="not_mentioned"), row("toefl_min_legacy", "90"), deadline("2027-02-01")]
    check = GoldCheck(GOLD, view, SHA)
    c = cells(view, gold_check=check)
    assert c["STEM"].mark == REVIEW and "抽取结果与人工标注不一致" in c["待核实说明"].text
    assert c["托福（旧制）"].mark == REVIEW
    out = deadline_rows(PROGRAM, [deadline("2027-02-01"), deadline("2027-01-07")], "2026-11-20", check)
    assert [(c[7].text, c[8].text) for _, c in out] == [("2027-02-01", "待核实"), ("2027-01-07", "")]


def test_pages_changed_since_the_gold_snapshot_are_not_compared():
    view = [row("toefl_min_legacy", "90", page="pg-2"), deadline("2027-02-01", page="pg-2")]
    check = GoldCheck(GOLD, view, SHA)
    assert cells(view, gold_check=check)["托福（旧制）"].mark == ""
    assert deadline_rows(PROGRAM, [deadline("2027-02-01", page="pg-2")], "2026-11-20", check)[0][1][8].text == ""


def test_agreeing_values_stay_unmarked():
    view = [row("stem_claim_on_page", "yes"), row("toefl_min_legacy", status="not_mentioned")]
    c = cells(view, gold_check=GoldCheck(GOLD, view, SHA))
    assert c["STEM"].mark == "" and c["托福（旧制）"].mark == ""


def test_snapshot_hashes_use_the_newest_normalizer():
    from gradprog.export.workbook import _norm_sha

    index = pd.DataFrame([{"snapshot_id": "s1", "normalizer_version": "2", "norm_sha256": "new"},
                          {"snapshot_id": "s1", "normalizer_version": "1", "norm_sha256": "old"}])
    assert _norm_sha(index) == {"s1": "new"}


# 10 §3.1 (2026-11-22)
def test_track_lengths_merge_into_one_range_without_a_check_mark():
    rows = [row("length_months_min", "9", reasons=["conflict:level_mismatch"]),
            row("length_months_min", "12", page="pg-2", reasons=["conflict:level_mismatch"]),
            row("length_months_max", "16"), row("length_months_max", "12", page="pg-2")]
    c = cells(rows)
    assert c["时长"].text == "9–16 个月" and c["时长"].mark == ""


def test_other_reasons_still_mark_the_length():
    c = cells([row("length_months_min", "21", reasons=["term_unknown"]), row("length_months_max", "21")])
    assert c["时长"].text == "21 个月（待核实）" and "无法确定适用学期" in c["待核实说明"].text


def test_estimated_total_and_year_format():
    c = cells([row("tuition_amount_usd", "1528", group="g1", extras={"includes_fees": False},
                   ).__or__({"derived": {"tuition_program_total_usd_est": 55008, "method": "per_credit x 36 credits"}}),
               row("tuition_basis", "per_credit", group="g1"), row("tuition_year", "2026-27", group="g1")])
    assert c["学费"].text == "$1,528 / 学分（2026-2027）"
    assert c["学费估算总额"].text == "$55,008（$1,528 × 36 学分）"
    c = cells([row("tuition_amount_usd", "1288", group="g1", extras={"includes_fees": False})
               | {"derived": {"tuition_program_total_usd_est": None, "method": ""}}])
    assert c["学费估算总额"].text == ""


def test_an_estimate_equal_to_the_stated_total_is_written_once():
    c = cells([row("tuition_amount_usd", "1250", group="g1", extras={"includes_fees": False})
               | {"derived": {"tuition_program_total_usd_est": 46250, "method": "per_credit x 37 credits"}},
               row("tuition_amount_usd", "46250", group="g2", extras={"includes_fees": False})
               | {"derived": {"tuition_program_total_usd_est": 46250, "method": "program_total"}}])
    assert c["学费估算总额"].text == "$46,250"


def test_area_uses_the_display_group():
    # 06 §2.8 (2026-11-23): a nominated program registered under another CIP shows its display group.
    c = cells([], program={**PROGRAM, "cip_group": "ieor", "display_group": "fin_eng"})
    assert c["方向"].text == "金融工程"


# 10 §3.1 (2026-11-23): programs with pages never captured show "待取得" instead of "页面未写明"
def test_pending_program_shows_pending_for_missing_values():
    c = cells([row("gre_policy", "optional"), row("ielts_min_overall", status="not_mentioned"),
               row("toefl_min_legacy", status="extraction_failed")], pending=True)
    assert c["GRE"].text == "可选"
    assert c["雅思"].text == "待取得" and c["雅思"].mark != REVIEW
    assert c["GMAT"].text == "待取得"                        # no rows at all
    assert c["托福（旧制）"].text.startswith("待核实")        # other statuses are unchanged
    assert "雅思" not in c["待核实说明"].text


def test_program_with_an_uncaptured_page_is_pending():
    index = pd.DataFrame([{"page_id": "pg-1", "retrieved_at": "2026-11-15T11:00:00Z", "classification": "unchanged"}])
    sheets, counts = build([csv_row(row("gre_policy", "optional"))], Registry(), index, [], "2026-11-20")
    by_program = {r[3].text: r for r in sheets["项目总表"][1]}
    gmat = PROGRAM_COLUMNS.index("GMAT")
    assert by_program["MS in Data Science"][gmat].text == "页面未写明"
    assert by_program["Holdout MS"][gmat].text == "待取得"      # pg-2 was never captured
    assert counts["pending_programs"] == 1


# 10 §3.2 (2026-11-23): term-by-term tuition keeps only the fall terms
def tuition_group(amount, year, gid):
    return [{**row("tuition_amount_usd", amount, oid=f"a-{gid}"), "group_id": gid},
            {**row("tuition_basis", "per_term", oid=f"b-{gid}"), "group_id": gid},
            {**row("tuition_year", year, oid=f"y-{gid}"), "group_id": gid}]


def test_term_by_term_tuition_keeps_the_fall_term():
    rows = tuition_group("16073", "Summer 2027", "t0") + tuition_group("16073", "Spring 2027", "t1") \
        + tuition_group("16073", "Fall 2026", "t2")
    assert cells(rows)["学费"].text == "$16,073 / 学期（fall 2026）"


def test_academic_year_tuition_is_kept_with_a_fall_term():
    rows = tuition_group("30000", "2026-2027", "t0") + tuition_group("16000", "Fall 2026", "t1") \
        + tuition_group("9000", "Summer 2027", "t2")
    text = cells(rows)["学费"].text
    assert "2026-2027" in text and "fall 2026" in text and "summer" not in text


def test_tuition_without_a_fall_term_is_unchanged():
    rows = tuition_group("9000", "Summer 2027", "t0") + tuition_group("16000", "Spring 2027", "t1")
    text = cells(rows)["学费"].text
    assert "summer 2027" in text and "spring 2027" in text
