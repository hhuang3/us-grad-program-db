"""Assemble and write the advisor workbook (10 §1–§6)."""

import csv
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from gradprog.export.tables import (
    CHANGE_COLUMNS, DEADLINE_COLUMNS, PROGRAM_COLUMNS, REVIEW, STALE, Cell, change_rows, deadline_rows, parse_view_row,
    program_row,
)
from gradprog.snapshot.store import SUCCESS

DISCLAIMER = "数据整理自各校官网，申请前请以官网最新信息为准。"
FILLS = {REVIEW: PatternFill("solid", fgColor="FFF2CC"), STALE: PatternFill("solid", fgColor="E7E6E6")}
GREY = Font(color="808080")
LINK = Font(color="0563C1", underline="single")
WIDTHS = {"学校": 28, "项目": 34, "学费": 34, "官网链接": 40, "来源链接": 40, "页面链接": 40, "待核实说明": 48, "变化": 60}


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _programs(registry, holdout, include_holdout):
    pages = registry.pages.set_index("page_id")
    links = defaultdict(list)
    for link in registry.program_pages.itertuples():
        if link.page_id in pages.index and pages.loc[link.page_id, "url_status"] == "confirmed":
            links[link.program_id].append(link.page_id)
    out = []
    for program in registry.programs.to_dict("records"):
        if program["status"] != "selected" or not links[program["program_id"]]:
            continue
        if program["program_id"] in holdout and not include_holdout:
            continue
        out.append((program, links[program["program_id"]]))
    return out, pages


def _last_checked(page_ids, index):
    ok = index[index["classification"].isin(SUCCESS)]
    dates = []
    for page_id in page_ids:
        mine = ok[ok["page_id"] == page_id]["retrieved_at"]
        dates.append(mine.max()[:10] if len(mine) else "从未")
    return "从未" if "从未" in dates else min(dates)


def build(view_rows, registry, index, changes, on_date, holdout=(), include_holdout=False):
    """{sheet: (columns, rows)} and counts; rows are lists of Cell."""
    view = [parse_view_row(r) for r in view_rows]
    chosen, pages = _programs(registry, set(holdout), include_holdout)
    by_program = defaultdict(list)
    for row in view:
        by_program[row["program_id"]].append(row)
    program_table, deadline_table, checked = [], [], []
    for program, page_ids in chosen:
        rows = [r for r in by_program[program["program_id"]] if r["page_id"] in page_ids]
        homes = [p for p in page_ids if pages.loc[p, "page_type"] == "program_home"] or page_ids
        last = _last_checked(page_ids, index)
        checked.append(last)
        program_table.append(program_row(program, rows, pages.loc[homes[0], "url"], last))
        deadline_table.extend(deadline_rows(program, rows, on_date))
    deadline_table = [cells for _, cells in sorted(deadline_table, key=lambda x: x[0])]
    programs = {p["program_id"]: p for p, _ in chosen}
    change_table = change_rows(changes, programs, dict(zip(registry.pages["page_id"], registry.pages["url"])))
    counts = {
        "programs": len(program_table),
        "program_cells_in_review": sum(c.mark == REVIEW for row in program_table for c in row),
        "programs_with_review": sum(any(c.mark == REVIEW for c in row) for row in program_table),
        "deadlines": len(deadline_table),
        "deadlines_in_review": sum(row[7].text == "待核实" for row in deadline_table),
        "deadlines_expired": sum(row[7].text == "已过期" for row in deadline_table),
        "changes": len(change_table),
    }
    dated = [d for d in checked if d != "从未"]
    info = [["导出日期", on_date],
            ["页面检查日期", f"{min(dated)} 至 {max(dated)}" if dated else "无"],
            ["说明", DISCLAIMER],
            ["待核实", "这个值进了审核队列，或页面上有多个不同的值，还没有人工核对。单元格标黄，原因写在“待核实说明”列。"],
            ["已过期", "截止日期早于导出日期。标灰，排在截止日期表最后。"],
            ["学期", "只招秋季的项目，学期按日期推算。"],
            ["项目数", str(counts["programs"])]]
    sheets = {
        "说明": (["项目", "内容"], [[Cell(a), Cell(b)] for a, b in info]),
        "项目总表": (PROGRAM_COLUMNS, program_table),
        "截止日期": (DEADLINE_COLUMNS, deadline_table),
        "最近变化": (CHANGE_COLUMNS, change_table),
    }
    return sheets, counts


def write(sheets, path):
    book = Workbook()
    book.remove(book.active)
    for name, (columns, rows) in sheets.items():
        sheet = book.create_sheet(name)
        sheet.append(columns)
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for row in rows:
            sheet.append([c.text for c in row])
            for target, c in zip(sheet[sheet.max_row], row):
                if c.link:
                    target.hyperlink = c.link
                    target.font = LINK
                if c.mark:
                    target.fill = FILLS[c.mark]
                    if c.mark == STALE and not c.link:
                        target.font = GREY
        for i, column in enumerate(columns, 1):
            sheet.column_dimensions[get_column_letter(i)].width = WIDTHS.get(column, 14 if name != "说明" else 60)
        sheet.freeze_panes = "A2"
    path.parent.mkdir(parents=True, exist_ok=True)
    book.save(path)
