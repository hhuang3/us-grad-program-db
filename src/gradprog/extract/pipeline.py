"""Runs an extraction: selection, the call, checks, storage, the derived view (08)."""

import csv
import json
from collections import Counter
from datetime import date, datetime, timezone
from uuid import uuid4

from gradprog.extract.conflicts import cross_page_conflicts, suggestions
from gradprog.extract.derive import tuition_total
from gradprog.extract.fields import schema_errors
from gradprog.extract.llm import LLMCallFailed, cost_usd
from gradprog.extract.observations import build_rows, failure_rows
from gradprog.extract.prompt import (
    EXTRACT_RULES_VERSION, PROMPT_VERSION, SCHEMA_VERSION, build_prompt, load_schema, prompt_files, schema_file,
)
from gradprog.extract.review import review_reasons
from gradprog.extract.selection import EXTRACTED, FAILED_CALLS, MAX_CALL_FAILURES, plan_calls
from gradprog.extract.store import RUN_COLUMNS

CHARS_PER_TOKEN = 3
VIEW_COLUMNS = ["observation_id", "program_id", "page_id", "owner_level", "snapshot_id", "field", "value",
                "value_status", "reference_target", "valid_for_term", "term_as_written", "term_basis", "stale",
                "conflict_type", "suggested_observation_id", "review_reasons", "group_id", "evidence_text",
                "evidence_url", "retrieved_at", "confidence", "extras", "derived", "model_name", "prompt_version",
                "schema_version", "extract_rules_version", "extracted_at", "call_id"]
EMPTY_TOTALS = {"input": 0, "cache_write": 0, "cache_read": 0, "output": 0, "usd": 0.0}


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _compact(ts):
    return ts.replace("-", "").replace(":", "")


def _call_id(kind, stamp, c):
    return f"{kind}-{_compact(stamp)}-{c.page_id}-{c.program_id}-{uuid4().hex[:8]}"   # two calls can share a second


def key_expiry_warning(settings, today):
    """A warning once the API key is close to its expiry date, or None."""
    expires = settings["api_key_expires"]
    expires = expires if isinstance(expires, date) else date.fromisoformat(expires)
    left = (expires - today).days
    if left < 0:
        return f"ANTHROPIC_API_KEY expired on {expires}; replace it in ~/.config/gradprog/env"
    if left <= settings["api_key_warn_days"]:
        return f"ANTHROPIC_API_KEY expires on {expires} ({left} days left); replace it in ~/.config/gradprog/env"
    return None


def versions_for(settings):
    return {"prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION, "model_name": settings["model"]}


def make_plan(registry, snapshots, store, settings, pages=None, retry_failed=False):
    return plan_calls(registry, snapshots.read_index(), store.read_records(), versions_for(settings), pages,
                      retry_failed)


def estimate_usd(calls, settings, output_tokens=6000):
    """An upper-range estimate for `extract plan`: the prompt uncached, 3 characters a token, 6K output per call."""
    fixed = sum(len(p.read_text(encoding="utf-8")) for p in prompt_files()) + len(schema_file().read_text("utf-8"))
    n = [c for c in calls if c.action == "call"]
    usage = {"input": (sum(c.norm_chars for c in n) + fixed * len(n)) // CHARS_PER_TOKEN,
             "output": output_tokens * len(n)}
    return cost_usd(usage, settings["prices"][settings["model"]])


def _meta(call_id, model, extracted_at):
    return {"call_id": call_id, "model_name": model, "prompt_version": PROMPT_VERSION,
            "schema_version": SCHEMA_VERSION, "extracted_at": extracted_at}


def _record(call, call_id, status, usage, usd, model, extracted_at, terms=(), failure="", request_id=""):
    return {"call_id": call_id, "snapshot_id": call["snapshot_id"], "page_id": call["page_id"],
            "program_id": call["program_id"], "norm_sha256": call["norm_sha256"], "status": status,
            "failure_reason": failure, "terms_mentioned": list(terms), "model_name": model,
            "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION, "extracted_at": extracted_at,
            "request_id": request_id, "usage": usage, "usd": usd}


def _extract_one(c, snapshots, store, client, settings, schema, stem_ref, now):
    """One call: returns (status, observation rows, usage, usd). Everything goes to disk before it returns."""
    call = c.to_dict()
    call_id = _call_id("call", now(), c)
    path = snapshots.norm_path(c.page_id, c.snapshot_id, c.normalizer_version)
    page_text = path.read_text(encoding="utf-8")
    system, user = build_prompt(call, page_text)
    prices = settings["prices"][settings["model"]]
    stamp = now()
    try:
        result = client.extract(system, user, schema, settings)
    except LLMCallFailed as e:
        return _failed_call(c, call, call_id, "api_error", e.reason, e.usage, prices, settings["model"], stamp, store)
    usage, model = result.usage, result.model or settings["model"]
    if result.stop_reason in ("refusal", "max_tokens"):
        return _failed_call(c, call, call_id, result.stop_reason, result.stop_reason, usage, prices, model, stamp, store,
                            result)
    usd = cost_usd(usage, prices)
    payload = {"call": call, "output_text": result.text, "stop_reason": result.stop_reason, "model": model,
               "request_id": result.request_id, "usage": usage}
    store.write_call(call_id, payload)
    meta = _meta(call_id, model, stamp)
    output, problem = _parse(result.text, schema)
    if problem:     # 08 §1: off the schema is recorded and not repaired or retried
        rows = failure_rows(call, meta, "extraction_failed", ["output_off_schema"])
        store.append_record(_record(call, call_id, "invalid_output", usage, usd, model, stamp, failure=problem,
                                    request_id=result.request_id))
        store.append_observations(rows)
        return "invalid_output", rows, usage, usd
    rows = build_rows(call, output, page_text, meta, stem_ref)
    store.append_record(_record(call, call_id, "ok", usage, usd, model, stamp, output["terms_mentioned"],
                                request_id=result.request_id))
    store.append_observations(rows)
    return "ok", rows, usage, usd


def _failed_call(c, call, call_id, status, reason, usage, prices, model, stamp, store, result=None):
    usd = cost_usd(usage, prices)
    store.write_call(call_id, {"call": call, "output_text": result.text if result else None, "stop_reason": status,
                               "model": model, "request_id": result.request_id if result else "", "usage": usage,
                               "failure_reason": reason})
    review = [f"call_failed:{status}"]
    if c.prior_failures + 1 >= MAX_CALL_FAILURES:
        review.append("repeated_call_failure")           # 08 §10 row 13
    rows = failure_rows(call, _meta(call_id, model, stamp), "extraction_failed", review)
    store.append_record(_record(call, call_id, status, usage, usd, model, stamp, failure=reason,
                                request_id=result.request_id if result else ""))
    store.append_observations(rows)
    return status, rows, usage, usd


def _parse(text, schema):
    try:
        output = json.loads(text)
    except (TypeError, ValueError):
        return None, "output_not_json"
    errors = schema_errors(output, schema)
    return (None, f"off schema at {errors[0].split(':')[0]}") if errors else (output, "")


def _unavailable(c, store, now):
    call = c.to_dict() | {"final_url": ""}
    stamp = now()
    call_id = _call_id("unavailable", stamp, c)
    rows = failure_rows(call, _meta(call_id, "", stamp), "page_unavailable")
    store.append_record(_record(call, call_id, "page_unavailable", {}, 0.0, "", stamp))
    store.append_observations(rows)
    return rows


def run_extract(registry, snapshots, store, client, settings, pages=None, retry_failed=False, limit=None, max_usd=None,
                stem_ref=None, now=_now):
    """Calls the planned pages in order until the budget is reached (the cap covers every run on record)."""
    started = now()
    cap = min(max_usd, settings["max_usd"]) if max_usd is not None else settings["max_usd"]
    plan = make_plan(registry, snapshots, store, settings, pages, retry_failed)
    schema = load_schema()
    counts, totals, all_rows = Counter(), dict(EMPTY_TOTALS), []
    spent = store.spent_usd()
    made = 0
    try:
        for c in plan:
            if c.action == "unavailable":
                all_rows.extend(_unavailable(c, store, now))
                counts["unavailable"] += 1
            elif c.action == "needs_review":
                counts["needs_review"] += 1
            elif c.action == "call":
                if spent >= cap:
                    counts["stopped_by_budget"] += 1
                    continue
                if limit is not None and made >= limit:
                    continue
                status, rows, usage, usd = _extract_one(c, snapshots, store, client, settings, schema, stem_ref, now)
                made += 1
                counts[status] += 1
                all_rows.extend(rows)
                spent += usd
                totals["usd"] += usd
                for k in ("input", "cache_write", "cache_read", "output"):
                    totals[k] += usage.get(k, 0)
    finally:     # calls already paid for stay on record even when the run stops early
        view = rebuild_view(registry, store, settings)
        run_row = _run_row(started, now(), settings, made, counts, all_rows, view, totals)
        store.append_run(run_row)
    return {"plan": plan, "counts": counts, "run": run_row, "spent_usd": spent, "cap_usd": cap}


def _run_row(started, finished, settings, made, counts, rows, view, totals):
    ids = {r["observation_id"] for r in rows}
    row = {k: counts.get(k, 0) for k in RUN_COLUMNS if k in (
        "ok", "invalid_output", "api_error", "refusal", "max_tokens", "unavailable", "needs_review",
        "stopped_by_budget")}
    row.update(run_id=f"xrun-{_compact(started)}", started_at=started, finished_at=finished,
               model_name=settings["model"], prompt_version=PROMPT_VERSION, schema_version=SCHEMA_VERSION,
               extract_rules_version=EXTRACT_RULES_VERSION, calls=made, observations=len(rows),
               found=sum(r["value_status"] == "found" for r in rows),
               in_review=sum(1 for r in view if r["observation_id"] in ids and r["review_reasons"]),
               input_tokens=totals["input"], cache_write_tokens=totals["cache_write"],
               cache_read_tokens=totals["cache_read"], output_tokens=totals["output"], usd=round(totals["usd"], 4))
    return row


def current_rows(records, observations):
    """Rows of each page × program's latest extraction under the newest rules, plus a later failure if there is one."""
    latest, failure = {}, {}
    for record in records:
        key = record["page_id"], record["program_id"]
        if record["status"] in EXTRACTED:
            latest[key] = record["call_id"]
            failure.pop(key, None)
        elif record["status"] in (*FAILED_CALLS, "page_unavailable"):
            failure[key] = record["call_id"]
    wanted = set(latest.values()) | set(failure.values())
    newest = {}
    for row in observations:
        if row["call_id"] in wanted:
            newest[row["call_id"]] = max(newest.get(row["call_id"], 0), row["extract_rules_version"])
    return [r for r in observations if r["call_id"] in wanted and r["extract_rules_version"] == newest[r["call_id"]]]


def _program_urls(registry):
    """Registered URLs per selected program, without scheme or trailing slash (08 §10 row 12)."""
    urls = registry.pages.drop_duplicates("page_id").set_index("page_id")["url"]
    out = {}
    for link in registry.program_pages.itertuples():
        if link.page_id in urls.index:
            plain = urls[link.page_id].removeprefix("https://").removeprefix("http://").rstrip("/")
            out.setdefault(link.program_id, set()).add(plain)
    return out


def _add_tuition_totals(rows):
    """08 §3.1: only when the program has one credit count on record; terms and years wait for a reviewer."""
    credits = {}
    for row in rows:
        if row["field"] == "credits_required" and row["value_status"] == "found":
            credits.setdefault(row["program_id"], set()).add(row["value"])
    bases = {r["group_id"]: r["value"] for r in rows if r["field"] == "tuition_basis" and r["value_status"] == "found"}
    for row in rows:
        if row["field"] == "tuition_amount_usd" and row["value_status"] == "found":
            known = credits.get(row["program_id"], set())
            amount, method = tuition_total(bases.get(row["group_id"]), row["value"],
                                           credits=next(iter(known)) if len(known) == 1 else None)
            row["derived"] = {**row["derived"], "tuition_program_total_usd_est": amount, "method": method}


def rebuild_view(registry, store, settings):
    """derived/current.csv: the current rows with cross-page conflicts and review reasons, rebuilt every time (08 §8)."""
    rows = current_rows(store.read_records(), store.read_observations())
    cross, suggested = {}, {}
    for program in {r["program_id"] for r in rows}:
        mine = [r for r in rows if r["program_id"] == program]
        cross.update(cross_page_conflicts(mine))
        suggested.update(suggestions(mine))
    for row in rows:
        row["conflict_type"] = sorted(set(row["conflict_type"]) | set(cross.get(row["observation_id"], [])))
    _add_tuition_totals(rows)
    reasons = review_reasons(rows, settings["confidence_threshold"], _program_urls(registry))
    view = []
    for row in rows:
        out = {c: row.get(c) for c in VIEW_COLUMNS}
        out["suggested_observation_id"] = suggested.get(row["observation_id"]) or ""
        out["review_reasons"] = reasons[row["observation_id"]]
        view.append(out)
    _write_view(store.view_path, view)
    return view


def _cell(value):
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value


def _write_view(path, view):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(VIEW_COLUMNS)
        for row in view:
            w.writerow([_cell(row[c]) for c in VIEW_COLUMNS])


def replay(registry, snapshots, store, settings, stem_ref=None):
    """08 §11: rerun the rule code on stored outputs under a new extract_rules_version, with no LLM call."""
    done = {(r["call_id"], r["extract_rules_version"]) for r in store.read_observations()}
    made = 0
    for record in store.read_records():
        if record["status"] != "ok" or (record["call_id"], EXTRACT_RULES_VERSION) in done:
            continue
        payload = store.read_call(record["call_id"])
        call = payload["call"]
        output = json.loads(payload["output_text"])
        page_text = snapshots.norm_path(call["page_id"], call["snapshot_id"], call["normalizer_version"]).read_text("utf-8")
        meta = {"call_id": record["call_id"], "model_name": record["model_name"],
                "prompt_version": record["prompt_version"], "schema_version": record["schema_version"],
                "extracted_at": record["extracted_at"]}
        store.append_observations(build_rows(call, output, page_text, meta, stem_ref))
        made += 1
    rebuild_view(registry, store, settings)
    return made


def summarize(view):
    """Counts only, safe to print and to commit: no values, no page text."""
    return {"rows": len(view), "by_status": Counter(r["value_status"] for r in view),
            "by_field_found": Counter(r["field"] for r in view if r["value_status"] == "found"),
            "review_reasons": Counter(x for r in view for x in r["review_reasons"]),
            "conflicts": Counter(x for r in view for x in r["conflict_type"]),
            "by_basis": Counter(r["term_basis"] for r in view if r["value_status"] == "found")}


def page_statuses(view, pages=None):
    """{(page_id, program_id): {field: {status: count}}}: statuses only, no values and no page text."""
    out = {}
    for row in view:
        if not pages or row["page_id"] in pages:
            fields = out.setdefault((row["page_id"], row["program_id"]), {})
            fields.setdefault(row["field"], Counter())[row["value_status"]] += 1
    return out


def render_summary(view, pages=None):
    rows = [r for r in view if not pages or r["page_id"] in pages]
    lines = []
    for (page, program), fields in sorted(page_statuses(rows).items()):
        lines.append(f"{page} {program}")
        for field, statuses in fields.items():
            lines.append(f"  {field}: " + ", ".join(f"{s} {n}" for s, n in sorted(statuses.items())))
    s = summarize(rows)
    failed = Counter(x.split(":", 1)[1] for r in rows for x in r["review_reasons"] if x.startswith("evidence_failed:"))
    lines += [f"status: {dict(s['by_status'])}", f"evidence failures: {sum(failed.values())} {dict(failed)}",
              f"review reasons: {dict(s['review_reasons'])}", f"conflicts: {dict(s['conflicts'])}",
              f"term basis of found rows: {dict(s['by_basis'])}"]
    return "\n".join(lines)
