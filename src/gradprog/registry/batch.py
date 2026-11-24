"""Batch registration from a proposals file, the review checklist and apply-review (06 §8)."""

import copy
import re
from dataclasses import dataclass, field

import pandas as pd

from gradprog.ref.targets import GROUP_ORDER
from gradprog.registry import tables as t
from gradprog.registry.robots import crawl_allowed_for
from gradprog.registry.urls import UrlError, domain_of, normalize_url
from gradprog.registry.worksheet import build_worksheet

PROPOSAL_COLUMNS = [
    "program_id", "unitid", "cip_code", "institution_name", "institution_short", "program_name", "degree_type",
    "degree_label", "department", "delivery_mode", "intake_terms", "nominated", "url", "page_type", "owner_level",
    "content_format", "scope_note", "tos_url", "tos_hint", "note", "display_group", "cip_source",
]
LEGACY_PROPOSAL_COLUMNS = PROPOSAL_COLUMNS[:-2]   # files written before 2026-11-23 (06 §8.1)
PROGRAM_FIELDS = ["unitid", "cip_code", "institution_name", "institution_short", "program_name", "degree_type",
                  "degree_label", "department", "delivery_mode", "intake_terms", "nominated", "display_group",
                  "cip_source"]
TOS_DECISIONS = ("no_restriction", "prohibits_automated_access", "unclear")
PROGRAM_DECISIONS = ("select", "exclude", "backup")
PAGE_DECISIONS = ("confirm", "reject")


def read_proposals(path):
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(df.columns) == LEGACY_PROPOSAL_COLUMNS:
        df = df.assign(display_group="", cip_source="")
    if list(df.columns) != PROPOSAL_COLUMNS:
        raise t.RegistryError(f"{path}: columns must be {PROPOSAL_COLUMNS}, got {list(df.columns)}")
    return df


@dataclass
class AddResult:
    new_programs: list = field(default_factory=list)
    new_pages: list = field(default_factory=list)
    new_domains: list = field(default_factory=list)
    reused: list = field(default_factory=list)           # (program_id, page_id) of already registered pages
    page_additions: list = field(default_factory=list)   # (program_id, page_id) for registered programs
    robots_domains: list = field(default_factory=list)   # domains of new pages: check-robots runs on these


def _row_problems(i, r):
    where = f"row {i + 2} ({r['program_id'] or 'no program_id'})"
    out = []
    for name, allowed in (("page_type", t.PAGE_TYPES), ("owner_level", t.OWNER_LEVELS),
                          ("content_format", t.CONTENT_FORMATS)):
        if r[name] not in allowed:
            out.append(f"{where}: {name}={r[name]!r} must be one of {list(allowed)}")
    try:
        normalize_url(r["url"])
    except UrlError as e:
        out.append(f"{where}: {e}")
    if r["nominated"] not in ("", "yes"):
        out.append(f"{where}: nominated must be 'yes' or empty")
    return out


def add_programs(registry, proposals, candidates, added_at, label="expansion"):
    """Register every program and page of a proposals file, or nothing (06 §8.1)."""
    from gradprog.registry.validate import validate

    work = copy.deepcopy(registry)
    problems, result = [], AddResult()
    known = set(work.programs["program_id"])
    cand = candidates.set_index(["unitid", "cip_code"])
    for i, r in proposals.iterrows():
        problems += _row_problems(i, r)

    for pid, rows in proposals.groupby("program_id", sort=False):
        if pid in known:
            reg = work.programs.set_index("program_id").loc[pid]
            for col in PROGRAM_FIELDS:
                values = {v for v in rows[col] if v}
                if col != "nominated" and values and values != {reg[col]}:
                    problems.append(f"{pid}: {col}={sorted(values)} differs from the registered program "
                                    f"({reg[col]!r})")
            continue
        for col in PROGRAM_FIELDS:
            if rows[col].nunique() > 1:
                problems.append(f"{pid}: {col} differs between its rows: {sorted(set(rows[col]))}")
        first = rows.iloc[0]
        key = (first["unitid"], first["cip_code"])
        if key not in cand.index:
            problems.append(f"{pid}: (unitid, cip_code)={key} is not a row of candidates.csv")
            continue
        note = f"Proposed {added_at} ({label})." + (f" {first['note']}" if first["note"] else "")
        work.programs = pd.concat([work.programs, pd.DataFrame([{
            "program_id": pid, "unitid": first["unitid"], "cip_code": first["cip_code"],
            "cip_group": cand.loc[key, "cip_group"], "institution_name": first["institution_name"],
            "institution_short": first["institution_short"], "institution_name_zh": "",
            "program_name": first["program_name"], "degree_type": first["degree_type"],
            "degree_label": first["degree_label"], "department": first["department"],
            "delivery_mode": first["delivery_mode"], "status": "backlog", "exclusion_reason": "",
            "selection_note": note, "batch": "expansion", "fetch_method": "", "intake_terms": first["intake_terms"],
            "added_at": added_at, "display_group": first["display_group"],
            "cip_source": first["cip_source"]}])], ignore_index=True)
        result.new_programs.append(pid)
        known.add(pid)
    if problems:
        raise t.RegistryError("proposals rejected, nothing registered:\n- " + "\n- ".join(problems))

    before_domains = set(work.domains["domain"])
    by_url = dict(zip(work.pages["url"], work.pages["page_id"]))
    linked = set(map(tuple, work.program_pages[["program_id", "page_id"]].values.tolist()))
    new_programs = set(result.new_programs)
    for _, r in proposals.iterrows():
        url = normalize_url(r["url"])
        pid = r["program_id"]
        if url in by_url:
            page = by_url[url]
            if (pid, page) not in linked:
                work.program_pages = pd.concat([work.program_pages, pd.DataFrame([{
                    "program_id": pid, "page_id": page, "scope_note": r["scope_note"]}])], ignore_index=True)
                linked.add((pid, page))
                if page not in result.new_pages:
                    (result.reused if pid in new_programs else result.page_additions).append((pid, page))
            continue
        page = t.add_page(work, url, r["page_type"], r["owner_level"], r["content_format"], [pid], added_at)
        if r["scope_note"]:
            work.program_pages.loc[(work.program_pages["program_id"] == pid)
                                   & (work.program_pages["page_id"] == page), "scope_note"] = r["scope_note"]
        by_url[url] = page
        linked.add((pid, page))
        result.new_pages.append(page)
        if pid not in new_programs:
            result.page_additions.append((pid, page))

    result.new_domains = sorted(set(work.domains["domain"]) - before_domains)
    result.robots_domains = sorted(set(work.pages.loc[work.pages["page_id"].isin(result.new_pages), "domain"]))
    hints = {}
    for _, r in proposals.iterrows():
        d = domain_of(normalize_url(r["url"]))
        if d in result.new_domains and (r["tos_url"] or r["tos_hint"]) and d not in hints:
            hints[d] = (r["tos_url"], r["tos_hint"])
    for d, (url, hint) in hints.items():
        mask = work.domains["domain"] == d
        work.domains.loc[mask, "tos_url"] = url
        work.domains.loc[mask, "tos_note"] = f"Claude: {hint}" if hint else ""

    before = set(validate(registry, candidates).errors)
    errors = [e for e in validate(work, candidates).errors if e not in before]
    if errors:
        raise t.RegistryError("proposals rejected, nothing registered:\n- " + "\n- ".join(errors))
    for name in t.TABLES:
        setattr(registry, name, work.table(name))
    return result


# --- review checklist (§8.2) -----------------------------------------------------

def _checks(url_check):
    if url_check is None or not len(url_check):
        return {}
    return {r.page_id: r for r in url_check.itertuples(index=False)}


def _blocked(url_check):
    """HTTP 403 or a JavaScript challenge in the latest check (06 §5.2)."""
    from gradprog.registry.validate import site_blocked_pages
    return site_blocked_pages(url_check)


def _page_line(page, tos, checks, reused=False):
    c = checks.get(page["page_id"])
    check = f"{c.result}{' ' + c.http_status if c.http_status else ''}" if c is not None else "未检查"
    if c is not None and c.final_url:
        check += f" → {c.final_url}"
    state = "（已登记，沿用）" if reused else ""
    return (f"  - {page['page_id']}{state} {page['page_type']}（{page['owner_level']}）{page['url']} — "
            f"robots {page['robots_allowed']}，条款 {tos.get(page['domain'], '')}，网址检查 {check}")


def _expected_fetch(page_ids, pages, blocked):
    return "自动抓取" if all(pages.loc[p, "crawl_allowed"] == "true" and p not in blocked for p in page_ids) \
        else "人工保存"


def write_review(registry, candidates, proposals, url_check, on_date, title=""):
    """Markdown checklist for the owner (06 §8.2)."""
    pages = registry.pages.set_index("page_id")
    programs = registry.programs.set_index("program_id")
    pp = registry.program_pages
    tos = dict(zip(registry.domains["domain"], registry.domains["tos_status"]))
    checks, blocked = _checks(url_check), _blocked(url_check)
    ws = build_worksheet(candidates).set_index(["unitid", "cip_code"])
    by_url = dict(zip(registry.pages["url"], registry.pages["page_id"]))
    prop_pages = {}
    for _, r in proposals.iterrows():
        prop_pages.setdefault(r["program_id"], []).append(by_url.get(normalize_url(r["url"])))
    nominated = {pid for pid, v in zip(proposals["program_id"], proposals["nominated"]) if v == "yes"}

    review_programs = [pid for pid in dict.fromkeys(proposals["program_id"])
                       if programs.loc[pid, "status"] == "backlog" and programs.loc[pid, "batch"] == "expansion"]
    additions = [(pid, p) for pid, ps in prop_pages.items() if pid not in review_programs for p in ps
                 if pages.loc[p, "url_status"] == "proposed"]
    page_domains = {pages.loc[p, "domain"] for ps in prop_pages.values() for p in ps}
    new_domains = registry.domains[registry.domains["domain"].isin(page_domains)
                                   & (registry.domains["tos_status"] == "not_checked")]

    out = [f"# 扩展批次审核清单 {on_date}" + (f"（{title}）" if title else ""), "",
           "填写方法：",
           "- 每个新域名的“条款：”填 `no_restriction`、`prohibits_automated_access` 或 `unclear`，后面可加说明。",
           "- 每个项目的“决定：”填 `select`、`exclude <原因> <说明>`（原因用 exclusion_reason 的取值，如 "
           "`online_only`、`certificate`、`mba`、`out_of_scope`、`duplicate`、`not_admitting`、`other`）或 `backup`。",
           "- “用时（分钟）：”填审核这个项目实际花的时间，可空。",
           "- 补登页面的“决定：”填 `confirm` 或 `reject`。",
           "- “我要加的学校：”写本组要补充点名的学校，Claude 再为它们准备提议。",
           "- 没有填写的项不会改动。填完后运行 `gradprog registry apply-review <本文件>`。", ""]

    out += ["## 新域名条款", ""]
    if not len(new_domains):
        out += ["（没有新域名）", ""]
    for d in new_domains.itertuples(index=False):
        hint = d.tos_note[len("Claude: "):] if d.tos_note.startswith("Claude: ") else d.tos_note
        out += [f"#### 域名 {d.domain}", f"- 条款页：{d.tos_url or '未找到'}", f"- Claude 初步判断：{hint or '无'}",
                f"- robots.txt：{d.robots_status or '未检查'}（{d.robots_allows_registered_paths or '-'}）", "条款：", ""]

    from gradprog.registry.validate import QUOTAS

    for g in GROUP_ORDER:
        mine = [pid for pid in review_programs if t.display_group(programs.loc[pid]) == g]
        if not mine:
            continue
        selected = sum(1 for _, p in registry.programs.iterrows()
                       if p["status"] == "selected" and t.display_group(p) == g)
        nom = [p for p in mine if p in nominated]
        ranked = [p for p in mine if p not in nominated]
        out += [f"## 组 {g}", "",
                f"名额 {QUOTAS[g]}，已选 {selected}；本清单提议 {len(mine)} 个项目"
                f"（点名 {len(nom)}，按排序 {len(ranked)}）。", "", "我要加的学校：", ""]
        for heading, ids in (("### 点名", nom), ("### 按排序", ranked)):
            if not ids:
                continue
            out += [heading, ""]
            for pid in ids:
                out += _program_block(pid, programs.loc[pid], pp, pages, tos, ws, checks, blocked, prop_pages)

    out += ["## 补登页面", ""]
    if not additions:
        out += ["（没有补登页面）", ""]
    notes = {(r["program_id"], by_url.get(normalize_url(r["url"]))): r["note"] for _, r in proposals.iterrows()}
    for pid, p in additions:
        prog = programs.loc[pid]
        out += [f"#### 页面 {p} — {pid}（{prog['institution_short']} {prog['program_name']}）",
                _page_line(pages.loc[p].to_dict() | {"page_id": p}, tos, checks)]
        if notes.get((pid, p)):
            out.append(f"- 提示：{notes[(pid, p)]}")
        out += ["决定：", ""]

    def pages_of(ids):
        return {p for pid in ids for p in pp.loc[pp["program_id"] == pid, "page_id"]}

    def share(n, total):
        return f"{n} 个（{(n / total * 100 if total else 0):.0f}%）"

    all_pages = pages_of(review_programs)
    out += ["## 汇总", "",
            f"- 本清单项目 {len(review_programs)} 个，页面 {len(all_pages)} 个（含沿用的已登记页面）。"
            "条款未判断的域名按不能抓取算。"]
    for label, ids in (("按排序", [p for p in review_programs if p not in nominated]),
                       ("点名", [p for p in review_programs if p in nominated])):
        mine = pages_of(ids)
        manual = [p for p in mine if not (pages.loc[p, "crawl_allowed"] == "true" and p not in blocked)]
        likely = [p for p in mine if not (pages.loc[p, "robots_allowed"] == "yes" and p not in blocked
                                          and tos.get(pages.loc[p, "domain"]) in ("no_restriction", "not_checked"))]
        rule = "06 §2.8 上限 30%" if label == "按排序" else "按需求选入，不受比例限制"
        out.append(f"- {label}：项目 {len(ids)} 个，页面 {len(mine)} 个，不能自动抓取 {share(len(manual), len(mine))}；"
                   f"若条款都判为 no_restriction：{share(len(likely), len(mine))}。{rule}。")
    return "\n".join(out) + "\n\n"


def _program_block(pid, prog, pp, pages, tos, ws, checks, blocked, prop_pages):
    key = (prog["unitid"], prog["cip_code"])
    w = ws.loc[key] if key in ws.index else None
    stem = {"true": "是", "false": "否"}.get(w["on_stem_list"], "?") if w is not None else "?"
    linked = list(pp.loc[pp["program_id"] == pid, "page_id"])
    new = {p for p in prop_pages.get(pid, []) if pages.loc[p, "added_at"] == prog["added_at"]
           and pages.loc[p, "url_status"] == "proposed"}
    note = prog["selection_note"].split(").", 1)[-1].strip() if prog["selection_note"].startswith("Proposed") \
        else prog["selection_note"]
    lines = [f"#### 项目 {pid} — {prog['institution_name']} — {prog['program_name']}",
             f"- IPEDS：CIP {prog['cip_code']}"
             + (f"（{w['cip_title']}），硕士授予 {w['completions_masters']}，国际学生 "
                f"{w['completions_masters_nonresident']}，STEM：{stem}，工作表排名 {w['worksheet_rank']}"
                if w is not None else "（不在候选清单）"),
             f"- 学位 / 授课 / 入学季：{prog['degree_type']}{' ' + prog['degree_label'] if prog['degree_label'] else ''}"
             f" / {prog['delivery_mode']} / {prog['intake_terms'] or '未填'}；院系：{prog['department'] or '-'}",
             "- 页面："]
    if prog.get("display_group", ""):
        source = {"school_stated": "学校声明", "inferred": "推测"}.get(prog["cip_source"], prog["cip_source"])
        lines.insert(2, f"- 显示方向：{prog['display_group']}（按实际 CIP 登记，06 §2.8；CIP 来源：{source}）")
    for p in linked:
        lines.append(_page_line(pages.loc[p].to_dict() | {"page_id": p}, tos, checks, reused=p not in new))
    lines.append(f"- 建议：{_expected_fetch(linked, pages, blocked)}（按目前检查结果）")
    if note:
        lines.append(f"- 提示：{note}")
    lines += ["决定：", "用时（分钟）：", ""]
    return lines


# --- parse and apply (§8.3) ------------------------------------------------------

@dataclass
class Review:
    programs: dict = field(default_factory=dict)   # program_id -> (decision, rest, minutes or None)
    pages: dict = field(default_factory=dict)      # page_id -> confirm / reject
    tos: dict = field(default_factory=dict)        # domain -> (tos_status, note)
    nominated: dict = field(default_factory=dict)  # group -> text
    sections: dict = field(default_factory=dict)   # program_id -> 点名 / 按排序


HEAD = re.compile(r"^#### (项目|页面|域名) (\S+)")
GROUP = re.compile(r"^## 组 (\S+)")


def parse_review(text):
    review, current, group, section = Review(), None, None, None
    minutes = {}
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            current, section = None, None
            m = GROUP.match(line)
            group = m.group(1) if m else None
            continue
        if line in ("### 点名", "### 按排序"):
            section = line[4:]
            continue
        m = HEAD.match(line)
        if m:
            current = (m.group(1), m.group(2))
            if m.group(1) == "项目" and section:
                review.sections[m.group(2)] = section
            continue
        if line.startswith("我要加的学校：") and group:
            review.nominated[group] = line[len("我要加的学校："):].strip()
            continue
        if current is None:
            continue
        kind, key = current
        for label in ("决定：", "条款：", "用时（分钟）："):
            if line.startswith(label):
                value = line[len(label):].strip()
                break
        else:
            continue
        if not value:
            continue
        if label == "用时（分钟）：":
            try:
                minutes[key] = float(value)
            except ValueError:
                raise t.RegistryError(f"{key}: 用时 must be a number of minutes, got {value!r}")
            continue
        word, _, rest = value.partition(" ")
        if kind == "域名" and label == "条款：":
            if word not in TOS_DECISIONS:
                raise t.RegistryError(f"{key}: 条款 must be one of {list(TOS_DECISIONS)}, got {value!r}")
            review.tos[key] = (word, rest.strip())
        elif kind == "项目" and label == "决定：":
            if word not in PROGRAM_DECISIONS:
                raise t.RegistryError(f"{key}: 决定 must be one of {list(PROGRAM_DECISIONS)}, got {value!r}")
            if word == "exclude" and rest.split(" ")[0] not in t.EXCLUSION_REASONS:
                raise t.RegistryError(f"{key}: exclude needs a reason from {list(t.EXCLUSION_REASONS)}, got {value!r}")
            review.programs[key] = (word, rest.strip(), None)
        elif kind == "页面" and label == "决定：":
            if word not in PAGE_DECISIONS:
                raise t.RegistryError(f"{key}: 决定 must be one of {list(PAGE_DECISIONS)}, got {value!r}")
            review.pages[key] = word
    for key, value in minutes.items():
        if key in review.programs:
            d, rest, _ = review.programs[key]
            review.programs[key] = (d, rest, value)
        else:
            review.programs[key] = ("", "", value)
    review.programs = {k: v for k, v in review.programs.items() if v[0]}
    review.minutes = minutes
    return review


def apply_review(registry, review, url_check, on, source="review"):
    """Apply the owner's decisions (06 §8.3); returns a summary for the report."""
    d = registry.domains
    for domain, (status, note) in review.tos.items():
        mask = d["domain"] == domain
        if not mask.any():
            raise t.RegistryError(f"unknown domain in review: {domain}")
        hint = d.loc[mask, "tos_note"].iloc[0]
        hint = hint[len("Claude: "):] if hint.startswith("Claude: ") else hint
        d.loc[mask, "tos_status"] = status
        d.loc[mask, "tos_note"] = f"负责人: {note or status}" + (f"；Claude: {hint}" if hint else "")
    registry.pages["crawl_allowed"] = list(crawl_allowed_for(registry.pages, registry.domains))

    # Page decisions first, so a rejected page never counts towards a selected program (06 §8.3).
    for page, decision in review.pages.items():
        if page not in set(registry.pages["page_id"]):
            raise t.RegistryError(f"unknown page in review: {page}")
        if decision == "confirm":
            registry.pages.loc[registry.pages["page_id"] == page, "url_status"] = "confirmed"
        else:
            if registry.pages.loc[registry.pages["page_id"] == page, "url_status"].iloc[0] != "proposed":
                raise t.RegistryError(f"{page}: only proposed pages can be rejected")
            registry.pages = registry.pages[registry.pages["page_id"] != page].reset_index(drop=True)
            registry.program_pages = registry.program_pages[registry.program_pages["page_id"] != page] \
                .reset_index(drop=True)

    blocked = _blocked(url_check)
    pages = registry.pages.set_index("page_id")
    progs = registry.programs
    pp = registry.program_pages
    selected = []
    for pid, (decision, rest, _) in review.programs.items():
        mask = progs["program_id"] == pid
        if not mask.any():
            raise t.RegistryError(f"unknown program in review: {pid}")
        if decision == "select":
            linked = list(pp.loc[pp["program_id"] == pid, "page_id"])
            auto = all(pages.loc[p, "crawl_allowed"] == "true" and p not in blocked for p in linked)
            progs.loc[mask, "status"] = "selected"
            progs.loc[mask, "fetch_method"] = "auto" if auto else "manual"
            progs.loc[mask, "selection_note"] = progs.loc[mask, "selection_note"] + \
                f" Selected by owner {on} ({source})." + (f" {rest}" if rest else "")
            registry.pages.loc[registry.pages["page_id"].isin(linked), "url_status"] = "confirmed"
            selected.append(pid)
        elif decision == "exclude":
            reason, _, why = rest.partition(" ")
            progs.loc[mask, "status"] = "excluded"
            progs.loc[mask, "exclusion_reason"] = reason
            progs.loc[mask, "selection_note"] = progs.loc[mask, "selection_note"] + \
                f" Excluded by owner {on} ({source})" + (f": {why.strip()}" if why.strip() else ".")
    pages = registry.pages.set_index("page_id")
    links = registry.program_pages

    def manual_share(section):
        ids = [p for p in selected if review.sections.get(p, "按排序") == section]
        mine = set(links.loc[links["program_id"].isin(ids), "page_id"])
        manual = sum(not (pages.loc[p, "crawl_allowed"] == "true" and p not in blocked) for p in mine)
        return {"manual": manual, "total": len(mine)}
    timed = [v for v in review.minutes.values()]
    decided = set(review.programs) | set(review.pages)
    pending_programs = [pid for pid in progs.loc[(progs["batch"] == "expansion") & (progs["status"] == "backlog"),
                                                 "program_id"] if pid not in decided]
    pending_pages = [p for p in registry.pages.loc[registry.pages["url_status"] == "proposed", "page_id"]
                     if p not in decided and p not in set(registry.program_pages.loc[
                         registry.program_pages["program_id"].isin(set(progs.loc[progs["status"] != "selected",
                                                                                  "program_id"])), "page_id"])]
    return {
        "selected": selected,
        "excluded": [k for k, v in review.programs.items() if v[0] == "exclude"],
        "backup": [k for k, v in review.programs.items() if v[0] == "backup"],
        "pages": dict(review.pages),
        "tos": {k: v[0] for k, v in review.tos.items()},
        "minutes": {"programs": len(timed), "total": sum(timed),
                    "mean": (sum(timed) / len(timed)) if timed else 0.0},
        "manual_pages": {"nominated": manual_share("点名"), "ranked": manual_share("按排序")},
        "nominated": {g: v for g, v in review.nominated.items()},
        "undecided": pending_programs + pending_pages,
    }
