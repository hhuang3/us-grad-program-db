"""Run report data/snapshots/reports/run-<run_id>.md (07 §9). Never contains page text."""

from gradprog.snapshot.store import CLASSES


def render(result, registry):
    out = [f"# Snapshot run {result.run_id}", "", "## 分类统计", "", "| classification | 数量 |", "|---|---|"]
    out += [f"| {c} | {result.counts.get(c, 0)} |" for c in CLASSES]

    out += ["", "## 异常清单", ""]
    if result.anomalies:
        out += ["| page_id | 项目 | 分类 | 原因 | 建议动作 | 需要处理 |", "|---|---|---|---|---|---|"]
        out += [f"| {a['page_id']} | {a['program_ids']} | {a['classification']} | {a['reason']} | {a['action']} | "
                f"{'是' if a['needs_action'] else '否'} |" for a in result.anomalies]
    else:
        out.append("无")

    changed = [r for r in result.rows if r["classification"] in ("changed", "suspected_redesign")]
    out += ["", "## 有变化的页面", ""]
    if changed:
        out += ["| page_id | 分类 | 增加行数 | 删除行数 |", "|---|---|---|---|"]
        out += [f"| {r['page_id']} | {r['classification']} | {r['added_lines']} | {r['removed_lines']} |"
                for r in changed]
    else:
        out.append("无")

    out += ["", "## 链接发现的候选（只提示，不自动登记）", ""]
    if result.link_candidates:
        out += ["| 项目 | 来源页 | 链接文字 | URL |", "|---|---|---|---|"]
        out += [f"| {c['program_id']} | {c['page_id']} | {c['text']} | [{c['url']}]({c['url']}) |"
                for c in result.link_candidates]
    else:
        out.append("无")

    redirected = [r for r in result.rows if "redirected" in r["note"].split("; ")]
    out += ["", "## 普通跳转（建议确认后在登记表中改用最终网址）", ""]
    out += [f"- {r['page_id']}: {r['requested_url']} → {r['final_url']}" for r in redirected] or ["无"]

    out += ["", "## 未纳入取得的页面（07 §3）", ""]
    out += [f"- {p['page_id']}（{p['program_ids']}）：{p['reason']}" for p in result.not_included] or ["无"]

    out += ["", f"## 人工取得待办：{result.manual_due} 个页面", ""]
    return "\n".join(out) + "\n"


def write(store, result, registry):
    path = store.report_path(result.run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(result, registry), encoding="utf-8")
    return path
