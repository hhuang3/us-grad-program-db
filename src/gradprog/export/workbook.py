"""Assemble and write the advisor workbook (10 §1–§6)."""

import csv
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from gradprog.export.tables import (
    AREA, CHANGE_COLUMNS, DEADLINE_COLUMNS, PROGRAM_COLUMNS, REVIEW, STALE, Cell, change_rows, deadline_rows,
    parse_view_row, program_row, school_key,
)
from gradprog.export.student import student_sheets
from gradprog.registry.tables import display_group
from gradprog.extract.evaluate import normalize_value
from gradprog.snapshot.store import SUCCESS

DISCLAIMER = "数据整理自各校官网，申请前请以官网最新信息为准。"
FILLS = {REVIEW: PatternFill("solid", fgColor="FFF2CC"), STALE: PatternFill("solid", fgColor="E7E6E6")}
GREY = Font(color="808080")
LINK = Font(color="0563C1", underline="single")
WIDTHS = {"学校简称": 14, "学费估算总额": 26, "学校": 28, "项目": 34, "学费": 34, "官网链接": 40, "来源链接": 40, "页面链接": 40, "待核实说明": 48, "变化": 60}


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _programs(registry):
    pages = registry.pages.set_index("page_id")
    links = defaultdict(list)
    for link in registry.program_pages.itertuples():
        if link.page_id in pages.index and pages.loc[link.page_id, "url_status"] == "confirmed":
            links[link.program_id].append(link.page_id)
    out = []
    for program in registry.programs.to_dict("records"):
        if program["status"] != "selected" or not links[program["program_id"]]:
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


def _norm_sha(index):
    """snapshot_id -> norm_sha256 under the newest normalizer version (07 §6): older versions stay in the index."""
    if "norm_sha256" not in index:
        return {}
    latest = index.sort_values("normalizer_version", kind="stable").drop_duplicates("snapshot_id", keep="last")
    return dict(zip(latest["snapshot_id"], latest["norm_sha256"]))


class GoldCheck:
    """Whether an exported value disagrees with the gold set (10 §5). Pages whose text changed since the gold
    snapshot are not compared: the page may simply have been updated."""

    def __init__(self, gold_rows, view, norm_sha):
        self.answers = defaultdict(list)
        gold_snapshot = {}
        for row in gold_rows:
            self.answers[row["program_id"], row["field"]].append(row)
            for s in row["snapshot_ids"].split(";"):
                gold_snapshot[s[s.index("-pg-") + 1:]] = s
        used = {r["page_id"]: r.get("snapshot_id") for r in view}
        self.unchanged = {p: used.get(p) is not None and norm_sha.get(used[p]) == norm_sha.get(s)
                          for p, s in gold_snapshot.items()}
        self.marked = 0

    def __call__(self, program_id, field, status, chosen):
        answers = self.answers.get((program_id, field))
        if not answers:
            return False
        result = self._deadline(answers, chosen[0]) if field == "deadline" else self._field(field, answers, status, chosen)
        self.marked += result
        return result

    def _same_text(self, pages):
        return all(self.unchanged.get(p, False) for p in pages)

    def _field(self, field, answers, status, chosen):
        found = [a for a in answers if a["value_status"] == "found"]
        pages = {p for a in answers for p in a["evidence_page_id"].split(";") if p}
        if status == "found" or not pages:
            pages |= {r["page_id"] for r in chosen}
        if not self._same_text(pages):
            return False
        if not found:
            return status != answers[0]["value_status"]
        if status != "found":
            return True
        return {normalize_value(field, r["value"]) for r in chosen} != {normalize_value(field, a["value"]) for a in found}

    def _deadline(self, answers, row):
        if not self._same_text({row["page_id"]}):
            return False
        date = row["value"].get("deadline_date")
        if not date:
            return False
        return (date, row["value"].get("deadline_type")) not in {(a["value"], a["deadline_type"]) for a in answers}


def collect(view_rows, registry, index, on_date, gold_rows=(), link_of=None):
    """Both versions' data (10 §3–§5): per program its row of the program table and its deadline rows."""
    view = [parse_view_row(r) for r in view_rows]
    gold = GoldCheck(gold_rows, view, _norm_sha(index))
    chosen, pages = _programs(registry)
    by_program = defaultdict(list)
    for row in view:
        by_program[row["program_id"]].append(row)
    area_order = list(AREA)
    chosen.sort(key=lambda x: (area_order.index(display_group(x[0])) if display_group(x[0]) in area_order
                               else len(area_order),
                               school_key(x[0]), x[0]["program_name"]))
    out = []
    for program, page_ids in chosen:
        rows = [r for r in by_program[program["program_id"]] if r["page_id"] in page_ids]
        homes = [p for p in page_ids if pages.loc[p, "page_type"] == "program_home"] or page_ids
        home = pages.loc[homes[0], "url"]
        last = _last_checked(page_ids, index)
        pending = last == "从未"   # 10 §3.1 (2026-11-23): some page was never captured
        out.append({"program": program, "home": home, "last_checked": last, "pending": pending,
                    "cells": program_row(program, rows, home, last, gold, link_of or (lambda row: None), pending),
                    "deadlines": deadline_rows(program, rows, on_date, gold)})
    page_urls = dict(zip(registry.pages["page_id"], registry.pages["url"]))
    return out, page_urls, gold


def build(view_rows, registry, index, changes, on_date, gold_rows=(), link_of=None, audience="advisor"):
    """{sheet: (columns, rows)} and counts; rows are lists of Cell."""
    collected, page_urls, gold = collect(view_rows, registry, index, on_date, gold_rows, link_of)
    if audience == "student":
        return student_sheets(collected, changes, on_date, page_urls)
    program_table = [c["cells"] for c in collected]
    deadline_table = [cells for _, cells in sorted((d for c in collected for d in c["deadlines"]), key=lambda x: x[0])]
    programs = {c["program"]["program_id"]: c["program"] for c in collected}
    change_table = change_rows(changes, programs, page_urls)
    checked = [c["last_checked"] for c in collected]
    counts = {
        "programs": len(program_table),
        "pending_programs": sum(c["pending"] for c in collected),
        "program_cells_in_review": sum(c.mark == REVIEW for row in program_table for c in row),
        "programs_with_review": sum(any(c.mark == REVIEW for c in row) for row in program_table),
        "deadlines": len(deadline_table),
        "deadlines_in_review": sum(row[8].text == "待核实" for row in deadline_table),
        "deadlines_expired": sum(row[8].text == "已过期" for row in deadline_table),
        "changes": len(change_table),
        "gold_mismatches": gold.marked,
    }
    dated = [d for d in checked if d != "从未"]
    info = [["导出日期", on_date],
            ["页面检查日期", f"{min(dated)} 至 {max(dated)}" if dated else "无"],
            ["说明", DISCLAIMER],
            ["待核实", "这个值进了审核队列，或页面上有多个不同的值，还没有人工核对。单元格标黄，原因写在“待核实说明”列。"],
            ["已过期", "截止日期早于导出日期。标灰，排在截止日期表最后。"],
            ["学期", "只招秋季的项目，学期按日期推算。"],
            ["页面未写明", "我们收录的官网页面没有写这一项。不代表没有这项要求，也不代表答案是“否”，请到官网确认。"],
            ["待取得", "这个项目还有收录的页面没有取得（多是等待人工保存的页面），没有值的项暂时不能判断，取得后补上。"],
            ["见其他页面", "官网让读者去另一个页面看这一项；单元格链接到那个页面。"],
            ["时长", "有多个方向（轨道）时合并为一个区间，例如 9–16 个月。"],
            ["学费估算总额", "按页面写的学费和学分估算的整个项目学费，不含杂费和生活费；页面只给项目总额时就是该数额；算不出时留空。"],
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
        sheet.auto_filter.ref = sheet.dimensions
    path.parent.mkdir(parents=True, exist_ok=True)
    book.save(path)
