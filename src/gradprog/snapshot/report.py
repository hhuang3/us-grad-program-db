"""Run report data/snapshots/reports/run-<run_id>.md (07 §9). Never contains page text."""

from pathlib import Path

import yaml

from gradprog.snapshot.store import CLASSES

BASELINE_FILE = Path(__file__).resolve().parents[3] / "config" / "rule_loss_baseline.yaml"
BASELINE_MARGIN = 2   # 07 §6.5: a baseline page is listed again only above its value + 2


def load_baseline(path=BASELINE_FILE):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return {"normalizer_version": int(data["normalizer_version"]), "pages": dict(data.get("pages") or {})}


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

    out += rule_loss_section(result.rows)
    out += ["", f"## 人工取得待办：{result.manual_due} 个页面", ""]
    return "\n".join(out) + "\n"


def _split(rows, baseline):
    """(new reminders, known ones) among rows with rule losses; baseline only counts for its normalizer version."""
    new, known = [], []
    for r in rows:
        n = r.get("rule_losses") or 0
        if not n:
            continue
        base = baseline["pages"].get(r["page_id"]) if str(r.get("normalizer_version")) == \
            str(baseline["normalizer_version"]) else None
        (known if base is not None and n <= base + BASELINE_MARGIN else new).append((r, base))
    return new, known


def new_rule_losses(rows, baseline=None):
    """Rows whose rule-loss reminder is outside the known baseline (07 §6.5)."""
    return [r for r, _ in _split(rows, load_baseline() if baseline is None else baseline)[0]]


def rule_loss_section(rows, baseline=None):
    """07 §6.5: pages where the domain rules removed data-like lines (counts only, never the lines).

    Reminders inside the known baseline are only summed up, so that new ones stand out."""
    baseline = load_baseline() if baseline is None else baseline
    new, known = _split(rows, baseline)
    out = ["", "## 按域名规则删除的疑似数据行（提醒，不影响分类）", ""]
    if new:
        out += ["基线以外的新提醒：", "", "| page_id | 行数 | 基线 |", "|---|---|---|"]
        out += [f"| {r['page_id']} | {r['rule_losses']} | {'–' if base is None else base} |" for r, base in new]
    if known:
        out += ([""] if new else []) + [f"基线内：{len(known)} 个快照、{sum(r['rule_losses'] for r, _ in known)} 行"
                    "（已知，见 config/rule_loss_baseline.yaml）"]
    if not new and not known:
        out.append("无")
    return out


def write_rule_losses(store, run_id, rows, baseline=None):
    """Manual and renormalize runs have no full report; write one only when there is a new reminder."""
    baseline = load_baseline() if baseline is None else baseline
    if not _split(rows, baseline)[0]:
        return None
    path = store.report_path(run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([f"# Snapshot run {run_id}", *rule_loss_section(rows, baseline)]) + "\n",
                    encoding="utf-8")
    return path


def write(store, result, registry):
    path = store.report_path(result.run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(result, registry), encoding="utf-8")
    return path
