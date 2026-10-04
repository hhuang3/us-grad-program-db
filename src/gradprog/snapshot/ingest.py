"""Shared pipeline: store raw -> normalize -> compare -> write index (07 §4, §6, §7)."""

import hashlib
import re

from gradprog.snapshot.classify import classify_content, select_prev
from gradprog.snapshot.normalize import NORMALIZER_VERSION, normalize
from gradprog.snapshot.store import INDEX_COLUMNS, SnapshotError, make_snapshot_id

JS_NOTE = "可能需要 JavaScript 渲染"
CHARSET_NOTE = re.compile(r"(?:^|; )charset=([A-Za-z0-9_\-:.]+)")


def join_note(*parts):
    return "; ".join(p for p in parts if p)


def note_charset(note):
    m = CHARSET_NOTE.search(note or "")
    return m.group(1) if m else None


def page_domain(registry, page_id):
    pages = registry.pages
    return pages.loc[pages["page_id"] == page_id, "domain"].iloc[0]


def empty_row(**fields):
    row = {c: "" for c in INDEX_COLUMNS}
    row.update({k: ("" if v is None else str(v)) for k, v in fields.items()})
    return row


def analyse(store, page_id, snapshot_id, retrieved_at, raw, content_type, charset, domain, rules, thresholds,
            version=NORMALIZER_VERSION):
    """Normalize and classify one stored raw snapshot; write normalized text and diff. Returns index fields."""
    try:
        text = normalize(raw, content_type, domain=domain, rules=rules, charset=charset)
    except Exception as e:  # unparseable file: keep the raw file, record the failure
        return {"normalizer_version": version, "classification": "fetch_error",
                "note": f"normalize failed: {type(e).__name__}"}
    if not text:
        return {"normalizer_version": version, "classification": "fetch_error", "note": JS_NOTE}
    norm = store.norm_path(page_id, snapshot_id, version)
    norm.parent.mkdir(parents=True, exist_ok=True)
    norm.write_text(text, encoding="utf-8", newline="")
    fields = {"normalizer_version": version, "norm_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
              "norm_chars": len(text), "note": ""}
    prev = select_prev(store.read_index(), page_id, retrieved_at, snapshot_id, version)
    prev_text = None
    if prev is not None:
        prev_text = store.norm_path(page_id, prev["snapshot_id"], version).read_text(encoding="utf-8")
        fields["prev_snapshot_id"] = prev["snapshot_id"]
    res = classify_content(prev_text, text, thresholds, prev and prev["snapshot_id"], snapshot_id)
    fields["classification"] = res.classification
    if res.diff is not None:
        diff = store.diff_path(page_id, snapshot_id, version)
        diff.parent.mkdir(parents=True, exist_ok=True)
        diff.write_text(res.diff, encoding="utf-8", newline="")
        fields["added_lines"], fields["removed_lines"] = res.added, res.removed
    return fields


def ingest(store, registry, *, page_id, run_id, method, retrieved_at, requested_url, final_url, http_status,
           raw, content_type, charset=None, note="", rules=None, thresholds=None):
    """Store a successfully retrieved file and append its index row."""
    snapshot_id = make_snapshot_id(retrieved_at, page_id)
    path = store.raw_path(page_id, snapshot_id, content_type)
    if path.exists() and path.read_bytes() != raw:
        raise SnapshotError(f"{path} already exists with different content")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    fields = analyse(store, page_id, snapshot_id, retrieved_at, raw, content_type, charset,
                     page_domain(registry, page_id), rules or {}, thresholds)
    row = empty_row(snapshot_id=snapshot_id, page_id=page_id, run_id=run_id, method=method,
                    retrieved_at=retrieved_at, requested_url=requested_url, final_url=final_url,
                    http_status=http_status, content_type=content_type,
                    raw_sha256=hashlib.sha256(raw).hexdigest(), raw_bytes=len(raw))
    extra = fields.pop("note", "")
    row.update({k: ("" if v is None else str(v)) for k, v in fields.items()})
    row["note"] = join_note(note, extra)
    store.append_index(row)
    return row


def failure(store, *, page_id, run_id, method, retrieved_at, requested_url, final_url, http_status,
            classification, note=""):
    """Append the index row of a retrieval that produced no stored file."""
    row = empty_row(snapshot_id=make_snapshot_id(retrieved_at, page_id), page_id=page_id, run_id=run_id,
                    method=method, retrieved_at=retrieved_at, requested_url=requested_url, final_url=final_url,
                    http_status=http_status, classification=classification, note=note)
    store.append_index(row)
    return row
