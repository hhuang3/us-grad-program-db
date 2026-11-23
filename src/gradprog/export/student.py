"""The student version of the export (10 §8): the same data, plainer wording, no internal marks."""

from gradprog.export.tables import PENDING, PROGRAM_COLUMNS, REVIEW, Cell, school

DISCLAIMER = "数据整理自各校官网，申请前请以官网最新信息为准。"
UNSURE = "（请以官网为准）"
NOT_ON_SITE = "官网未写明，请查看官网"
FLAG = "（待核实）"
NO_VALUE_PREFIXES = ("页面未写明", "见其他页面", "提到但未给值", "待核实（")
STUDENT_PROGRAM_COLUMNS = ["方向", "学校", "项目", "STEM", "时长", "托福", "雅思", "GRE", "学费估算总额", "下一个申请截止日期"]
STUDENT_DEADLINE_COLUMNS = ["学校", "项目", "学期", "轮次", "类型", "日期", "来源链接"]
STUDENT_CHANGE_COLUMNS = ["日期", "学校", "项目", "变化", "页面链接"]
CHANGE_FIELDS = {"deadline", "scores", "gre", "intake", "tuition"}
GLOSSARY = [
    ["STEM 与 OPT", "STEM 认定的项目，毕业后的 OPT 可以在 12 个月之外再延长 24 个月，最长 3 年。是否认定以学校国际学生办公室的说明为准。"],
    ["托福新旧分制", "2026 年 1 月 21 日起托福采用 1–6 分的新分制，此前为 0–120 分。“100（新制 5.0）”表示旧制要求 100、新制要求 5.0。"],
    ["轮次", "很多项目分几轮截止（Round 1、Round 2……），越早的轮次录取和奖学金机会通常越多。"],
    ["滚动录取", "收到申请就开始审核、陆续发录取，名额满了可能提前结束，越早申请越好。"],
    ["学费估算总额", "按官网写的学费和学分估算的整个项目学费，不含杂费和生活费；官网只给总额时就是该数额。"],
    ["请以官网为准", "这个值在官网上有不一致或还没有人工核对，申请前请到官网确认。"],
    ["官网未写明，请查看官网", "我们收录的官网页面没有写这一项，不代表没有这项要求；点击链接查看官网。"],
    ["待取得", "这个项目的部分官网页面还没有收录，暂时不能判断；点击链接查看官网，收录后会补上。"],
    ["说明", DISCLAIMER],
]


def _value(cell):
    return cell.text.removesuffix(FLAG)


def _no_value(cell):
    return cell.text.startswith(NO_VALUE_PREFIXES)


def _plain(cell, home):
    """An advisor cell in student wording (10 §8.1)."""
    if cell.text == PENDING:
        return Cell(PENDING, home)
    if _no_value(cell):
        link = cell.link if cell.text.startswith("见其他页面") and cell.link else home
        return Cell(NOT_ON_SITE, link)
    return Cell(_value(cell) + (UNSURE if cell.mark == REVIEW else ""), cell.link)


def _stem(cell, home):
    if cell.text == PENDING:
        return Cell(PENDING, home)
    if _no_value(cell):
        return Cell(NOT_ON_SITE, home)
    text = "是" if cell.text.startswith("是") else "否" if cell.text.startswith("否") else _value(cell)
    return Cell(text + (UNSURE if cell.mark == REVIEW else ""), cell.link)


def _toefl(legacy, new, home):
    have_old, have_new = not _no_value(legacy) and legacy.text != PENDING, not _no_value(new) and new.text != PENDING
    if not (have_old or have_new):
        return Cell(PENDING, home) if PENDING in (legacy.text, new.text) else _plain(legacy, home)
    if have_old and have_new:
        text = f"{_value(legacy)}（新制 {_value(new)}）"
    else:
        text = _value(legacy) if have_old else f"新制 {_value(new)}"
    unsure = (have_old and legacy.mark == REVIEW) or (have_new and new.mark == REVIEW)
    return Cell(text + (UNSURE if unsure else ""), (legacy if have_old else new).link)


def _tuition(tuition, estimate, home):
    if estimate.text:
        amounts = "；".join(part.split("（")[0] for part in _value(estimate).split("；"))
        return Cell(amounts + (UNSURE if estimate.mark == REVIEW else ""), estimate.link)
    if _no_value(tuition) or tuition.text == PENDING:
        return _plain(tuition, home)
    text = f"{_value(tuition)}，总额请查看官网"
    return Cell(text + (UNSURE if tuition.mark == REVIEW else ""), tuition.link)


def _application_rows(deadlines):
    """(cells, kind) of unexpired application deadlines a student can use (10 §8.2)."""
    out = []
    for _, cells in deadlines:
        kind, scope, status = cells[5].text, cells[6].text, cells[8].text
        if kind != "申请截止" or status == "已过期" or scope == "美国本土":
            continue
        out.append((cells, "奖学金优先截止" if scope == "奖助评选" else "申请截止"))
    return out


def _next_deadline(rows, home, pending=False):
    usable = [(cells, kind) for cells, kind in rows if kind == "申请截止"]
    dated = sorted((c for c, _ in usable if c[7].text != "滚动录取"), key=lambda c: c[7].text)
    if dated:
        c = dated[0]
        text = c[7].text + (f"（{c[4].text}）" if c[4].text else "")
        return Cell(text + (UNSURE if c[8].text == "待核实" else ""), c[10].link)
    if any(c[7].text == "滚动录取" for c, _ in usable):
        rolling = next(c for c, _ in usable if c[7].text == "滚动录取")
        return Cell("滚动录取" + (UNSURE if rolling[8].text == "待核实" else ""), rolling[10].link)
    return Cell(PENDING if pending else NOT_ON_SITE, home)


def student_sheets(collected, changes, on_date, page_urls):
    col = {name: i for i, name in enumerate(PROGRAM_COLUMNS)}
    programs, deadlines = [], []
    for item in collected:
        program, home, cells = item["program"], item["home"], item["cells"]
        rows = _application_rows(item["deadlines"])
        get = lambda name: cells[col[name]]   # noqa: E731
        programs.append([
            get("方向"), Cell(school(program)), Cell(program["program_name"], home), _stem(get("STEM"), home),
            _plain(get("时长"), home), _toefl(get("托福（旧制）"), get("托福（新制）"), home),
            _plain(get("雅思"), home), _plain(get("GRE"), home), _tuition(get("学费"), get("学费估算总额"), home),
            _next_deadline(rows, home, item.get("pending", False)),
        ])
        for cells_, kind in rows:
            date = cells_[7].text
            deadlines.append(((date == "滚动录取", date, school(program)), [
                Cell(school(program)), Cell(program["program_name"]), Cell(cells_[3].text), Cell(cells_[4].text),
                Cell(kind), Cell(date + (UNSURE if cells_[8].text == "待核实" else "")),
                Cell(cells_[10].text, cells_[10].link)]))
    by_id = {item["program"]["program_id"]: item["program"] for item in collected}
    change_table = []
    for change in sorted(changes, key=lambda c: c["date"], reverse=True):
        program = by_id.get(change["program_id"])
        if program is None or not set(filter(None, change.get("fields", "").split(";"))) & CHANGE_FIELDS:
            continue
        url = page_urls.get(change["page_id"], "")
        change_table.append([Cell(change["date"]), Cell(school(program)), Cell(program["program_name"]),
                             Cell(change["description"]), Cell(url, url)])
    sheets = {
        "名词解释": (["名词", "解释"], [[Cell(a), Cell(b)] for a, b in [["导出日期", on_date], *GLOSSARY]]),
        "项目总表": (STUDENT_PROGRAM_COLUMNS, programs),
        "截止日期": (STUDENT_DEADLINE_COLUMNS, [c for _, c in sorted(deadlines, key=lambda x: x[0])]),
        "最近变化": (STUDENT_CHANGE_COLUMNS, change_table),
    }
    counts = {"programs": len(programs), "deadlines": len(deadlines), "changes": len(change_table),
              "unsure_cells": sum(UNSURE in c.text for row in programs for c in row),
              "not_on_site_cells": sum(c.text == NOT_ON_SITE for row in programs for c in row)}
    return sheets, counts
