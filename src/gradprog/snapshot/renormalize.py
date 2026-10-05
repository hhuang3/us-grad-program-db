"""Re-normalize stored raw snapshots under a new normalizer version (07 §6.4)."""

from gradprog.snapshot.classify import load_thresholds
from gradprog.snapshot.ingest import analyse, join_note, note_charset, page_domain
from gradprog.snapshot.normalize import NORMALIZER_VERSION, load_rules
from gradprog.snapshot.store import CLASSES, SUCCESS, make_run_id
from gradprog.util.download import utc_now

ACQUISITION = ["snapshot_id", "page_id", "method", "retrieved_at", "requested_url", "final_url", "http_status",
               "content_type", "raw_sha256", "raw_bytes"]


def renormalize(registry, store, version=None, rules=None, thresholds=None, now=None):
    version = NORMALIZER_VERSION if version is None else int(version)
    rules = load_rules() if rules is None else rules
    thresholds = thresholds or load_thresholds()
    now = now or utc_now
    ix = store.read_index()
    done = set(ix.loc[ix["normalizer_version"] == str(version), "snapshot_id"])
    # one source row per stored raw file (the earliest row of that snapshot carries the acquisition data)
    todo = ix[(ix["raw_sha256"] != "") & ~ix["snapshot_id"].isin(done)].drop_duplicates("snapshot_id")
    if todo.empty:
        return []
    started = now()
    run_id = make_run_id(started, "renormalize")
    rows = []
    for src in todo.sort_values(["page_id", "retrieved_at", "snapshot_id"]).to_dict("records"):
        raw = store.raw_path(src["page_id"], src["snapshot_id"], src["content_type"]).read_bytes()
        fields = analyse(store, src["page_id"], src["snapshot_id"], src["retrieved_at"], raw, src["content_type"],
                         note_charset(src["note"]), page_domain(registry, src["page_id"]), rules, thresholds, version)
        row = {c: "" for c in ix.columns}
        row.update({c: src[c] for c in ACQUISITION})
        extra = fields.pop("note", "")
        row.update({k: ("" if v is None else str(v)) for k, v in fields.items()})
        row.update(run_id=run_id, note=join_note(src["note"], extra, "renormalized"))
        store.append_index(row)
        rows.append(row)
    counts = {c: sum(r["classification"] == c for r in rows) for c in CLASSES}
    anomalies = sorted({r["page_id"] for r in rows if r["classification"] not in SUCCESS
                        or r["classification"] == "suspected_redesign"})
    store.append_run({"run_id": run_id, "method": "renormalize", "started_at": started, "finished_at": now(),
                      **counts, "anomaly_page_ids": ";".join(anomalies)})
    return rows
