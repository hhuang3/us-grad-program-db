"""Classification, previous-version selection and diffs (07 §7)."""

import difflib
from dataclasses import dataclass
from pathlib import Path

import yaml

from gradprog.snapshot.store import SUCCESS

THRESHOLDS_FILE = Path(__file__).resolve().parents[3] / "config" / "snapshot_thresholds.yaml"


@dataclass
class ContentResult:
    classification: str
    added: int | None = None
    removed: int | None = None
    diff: str | None = None


def load_thresholds(path=THRESHOLDS_FILE):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if set(data) != {"char_drop", "min_similarity"}:
        raise ValueError(f"thresholds must define exactly char_drop and min_similarity, got {sorted(data)}")
    return {"char_drop": float(data["char_drop"]), "min_similarity": float(data["min_similarity"])}


def similarity(prev_text, new_text):
    return difflib.SequenceMatcher(None, prev_text.splitlines(), new_text.splitlines(), autojunk=False).ratio()


def make_diff(prev_text, new_text, prev_id, new_id):
    return "".join(difflib.unified_diff(prev_text.splitlines(keepends=True), new_text.splitlines(keepends=True),
                                        fromfile=prev_id, tofile=new_id, n=3))


def _counts(diff):
    added = removed = 0
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    return added, removed


def classify_content(prev_text, new_text, thresholds, prev_id="prev", new_id="new"):
    if prev_text is None:
        return ContentResult("first_capture")
    if prev_text == new_text:
        return ContentResult("unchanged")
    diff = make_diff(prev_text, new_text, prev_id, new_id)
    added, removed = _counts(diff)
    drop = (len(prev_text) - len(new_text)) / len(prev_text) if prev_text else 0.0
    redesign = drop > thresholds["char_drop"] or similarity(prev_text, new_text) < thresholds["min_similarity"]
    return ContentResult("suspected_redesign" if redesign else "changed", added, removed, diff)


def select_prev(index, page_id, retrieved_at, snapshot_id, version):
    if index is None or len(index) == 0:
        return None
    ix = index[(index["page_id"] == page_id) & (index["normalizer_version"] == str(version))
               & index["classification"].isin(SUCCESS)]
    earlier = ix[[(r, s) < (retrieved_at, snapshot_id) for r, s in zip(ix["retrieved_at"], ix["snapshot_id"])]]
    if earlier.empty:
        return None
    return earlier.sort_values(["retrieved_at", "snapshot_id"]).iloc[-1].to_dict()
