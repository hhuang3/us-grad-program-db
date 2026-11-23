"""docs/spec/10_export.md §8: the student version."""

from openpyxl import load_workbook

from gradprog.export.student import NOT_ON_SITE, UNSURE, _next_deadline, _plain, _stem, _toefl, _tuition
from gradprog.export.tables import REVIEW, Cell
from gradprog.export.workbook import build, write
from test_export import PROGRAM, Registry, csv_row, deadline, row

HOME = "https://a.edu/home"
INDEX_ROWS = [{"page_id": "pg-1", "retrieved_at": "2026-11-15T11:00:00Z", "classification": "unchanged",
               "snapshot_id": "snap-1-pg-1", "normalizer_version": "2", "norm_sha256": "a"},
              {"page_id": "pg-2", "retrieved_at": "2026-11-15T11:00:00Z", "classification": "unchanged",
               "snapshot_id": "snap-1-pg-2", "normalizer_version": "2", "norm_sha256": "b"}]


def test_unsure_values_keep_the_value():
    assert _plain(Cell("90 / 95（待核实）", "https://a.edu/p", REVIEW), HOME).text == "90 / 95" + UNSURE


def test_missing_values_send_the_reader_to_the_site():
    cell = _plain(Cell("页面未写明"), HOME)
    assert (cell.text, cell.link) == (NOT_ON_SITE, HOME)
    cell = _plain(Cell("见其他页面：Graduate page", "https://grad.a.edu"), HOME)
    assert (cell.text, cell.link) == (NOT_ON_SITE, "https://grad.a.edu")
    assert _plain(Cell("待核实（抽取失败）", "x", REVIEW), HOME).text == NOT_ON_SITE


def test_stem_is_yes_or_no():
    assert _stem(Cell("是（页面声称），CIP 30.7001"), HOME).text == "是"


def test_toefl_columns_merge():
    assert _toefl(Cell("100"), Cell("5.0"), HOME).text == "100（新制 5.0）"
    assert _toefl(Cell("100"), Cell("页面未写明"), HOME).text == "100"
    assert _toefl(Cell("页面未写明"), Cell("4.5"), HOME).text == "新制 4.5"
    assert _toefl(Cell("90 / 95（待核实）", mark=REVIEW), Cell("4.5"), HOME).text == "90 / 95（新制 4.5）" + UNSURE
    assert _toefl(Cell("页面未写明"), Cell("页面未写明"), HOME).text == NOT_ON_SITE


def test_tuition_uses_the_estimate_or_points_to_the_site():
    assert _tuition(Cell("$1,528 / 学分"), Cell("$55,008（$1,528 × 36 学分）"), HOME).text == "$55,008"
    assert _tuition(Cell("$1,288 / 学分（2026-2027）"), Cell(""), HOME).text == "$1,288 / 学分（2026-2027），总额请查看官网"
    assert _tuition(Cell("页面未写明"), Cell(""), HOME).text == NOT_ON_SITE


def deadline_cells(date, kind="申请截止", scope="全部", status="", round_name="Round 1"):
    cells = [Cell("A"), Cell("A"), Cell("P"), Cell("Fall 2027"), Cell(round_name), Cell(kind), Cell(scope), Cell(date),
             Cell(status), Cell(""), Cell("https://a.edu/d", "https://a.edu/d")]
    return cells, "奖学金优先截止" if scope == "奖助评选" else "申请截止"


def test_next_deadline_is_the_earliest_usable_application_date():
    rows = [deadline_cells("2027-02-01"), deadline_cells("2027-01-07", round_name="Round 3"),
            deadline_cells("2026-12-01", scope="奖助评选")]
    assert _next_deadline(rows, HOME).text == "2027-01-07（Round 3）"
    assert _next_deadline([deadline_cells("滚动录取")], HOME).text == "滚动录取"
    assert _next_deadline([deadline_cells("2027-01-07", status="待核实", round_name="")], HOME).text == "2027-01-07" + UNSURE
    assert _next_deadline([], HOME).text == NOT_ON_SITE


def test_student_workbook_keeps_only_usable_deadlines_and_no_internal_marks(tmp_path):
    import pandas as pd

    view = [csv_row(r) for r in [
        row("toefl_min_legacy", "90", reasons=["conflict:in_page_contradiction"]),
        row("toefl_min_legacy", "95", reasons=["conflict:in_page_contradiction"]),
        deadline("2027-01-07"), deadline("2026-12-01", scope="domestic"),
        deadline("2026-12-15", scope="funding_consideration"), deadline("2027-03-01", kind="deposit"),
        deadline("2026-10-01")]]
    for r in view:
        r["evidence_text"] = "secret page text"
    changes = [{"date": "2026-11-15", "page_id": "pg-1", "program_id": "p1", "application_info": "yes",
                "fields": "deadline", "description": "kept"},
               {"date": "2026-11-15", "page_id": "pg-1", "program_id": "p1", "application_info": "yes",
                "fields": "", "description": "dropped"}]
    sheets, counts = build(view, Registry(), pd.DataFrame(INDEX_ROWS), changes, "2026-11-20", audience="student")
    assert list(sheets) == ["名词解释", "项目总表", "截止日期", "最近变化"]
    deadlines = [[c.text for c in r] for r in sheets["截止日期"][1]]
    assert [(r[4], r[5]) for r in deadlines] == [("奖学金优先截止", "2026-12-15"), ("申请截止", "2027-01-07")]
    assert [r[3].text for r in sheets["最近变化"][1]] == ["kept"]
    rows = [dict(zip(sheets["项目总表"][0], (c.text for c in r))) for r in sheets["项目总表"][1]]
    first = next(r for r in rows if r["项目"] == PROGRAM["program_name"])
    assert first["托福"] == "90 / 95" + UNSURE and first["下一个申请截止日期"] == "2027-01-07（Round 1）"
    path = tmp_path / "s.xlsx"
    write(sheets, path)
    book = load_workbook(path)
    text = " ".join(str(c.value) for s in book for r in s.iter_rows() for c in r)
    for word in ("待核实", "secret", "snap-", "同一页面", "抽取", "审核原因"):
        assert word not in text
    assert not any(c.fill.fgColor.rgb not in ("00000000", None) for s in book for r in s.iter_rows() for c in r
                   if c.fill and c.fill.fill_type)
    assert all(s.auto_filter.ref for s in book)


# 10 §8.1 (2026-11-23)
def test_pending_cells_stay_pending_and_link_home():
    cell = _plain(Cell("待取得"), HOME)
    assert (cell.text, cell.link) == ("待取得", HOME)
    assert _toefl(Cell("待取得"), Cell("待取得"), HOME).text == "待取得"
    assert _tuition(Cell("待取得"), Cell(""), HOME).text == "待取得"
    assert _stem(Cell("待取得"), HOME).text == "待取得"
    assert _next_deadline([], HOME, pending=True).text == "待取得"
