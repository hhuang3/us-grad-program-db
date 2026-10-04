"""docs/spec/07_snapshots.md §7: classification, thresholds, previous version, diffs."""

import pandas as pd
import pytest

from gradprog.snapshot.classify import classify_content, load_thresholds, make_diff, select_prev, similarity
from helpers import REPO

T = {"char_drop": 0.5, "min_similarity": 0.3}
BASE = "".join(f"line {i}\n" for i in range(10))   # 10 lines, 70 chars


def test_thresholds_from_config():
    assert load_thresholds(REPO / "config" / "snapshot_thresholds.yaml") == T


def test_first_capture_without_prev():
    r = classify_content(None, BASE, T)
    assert (r.classification, r.added, r.removed, r.diff) == ("first_capture", None, None, None)


def test_unchanged():
    r = classify_content(BASE, BASE, T)
    assert (r.classification, r.diff) == ("unchanged", None)


def test_changed_with_counts_and_diff():
    new = BASE.replace("line 3\n", "line 3 updated\n") + "line 10\n"
    r = classify_content(BASE, new, T)
    assert r.classification == "changed"
    assert (r.added, r.removed) == (2, 1)
    assert r.diff is not None


def test_redesign_by_char_drop():
    new = "line 0\nline 1\nline 2\nline 3\n"   # 28 of 70 chars: drop 60%
    assert classify_content(BASE, new, T).classification == "suspected_redesign"


def test_redesign_by_low_similarity():
    new = "".join(f"other {i}\n" for i in range(10))
    assert similarity(BASE, new) < 0.3
    assert classify_content(BASE, new, T).classification == "suspected_redesign"


def test_char_drop_boundary_is_strict():
    prev = "a" * 10 + "\n" + "b" * 9 + "\n"     # 21 chars
    exactly_half = "a" * 10 + "\n"            # 11 chars: drop 47.6%, not > 50%
    assert classify_content(prev, exactly_half, {"char_drop": 0.5, "min_similarity": 0.0}).classification == "changed"
    prev2 = "x" * 9 + "\n" + "y" * 9 + "\n"   # 20 chars
    half = "x" * 9 + "\n"                     # 10 chars: exactly 50%
    assert classify_content(prev2, half, {"char_drop": 0.5, "min_similarity": 0.0}).classification == "changed"


def test_similarity_boundary_is_strict():
    prev = "a\nb\nc\nd\ne\n"
    new = "a\nx\ny\nz\nw\n"
    ratio = similarity(prev, new)                                   # 2*1/10 = 0.2
    assert ratio == pytest.approx(0.2)
    assert classify_content(prev, new, {"char_drop": 1.0, "min_similarity": ratio}).classification == "changed"
    assert classify_content(prev, new, {"char_drop": 1.0, "min_similarity": ratio + 0.01}).classification \
        == "suspected_redesign"


def test_diff_format():
    d = make_diff(BASE, BASE.replace("line 5", "line five"), "snap-A", "snap-B")
    lines = d.splitlines()
    assert lines[0] == "--- snap-A" and lines[1] == "+++ snap-B"
    assert "-line 5" in lines and "+line five" in lines


# --- previous version (§7.2) --------------------------------------------------

def idx(*rows):
    cols = ["snapshot_id", "page_id", "retrieved_at", "normalizer_version", "classification"]
    return pd.DataFrame([dict(zip(cols, r)) for r in rows], columns=cols)


INDEX = idx(
    ("snap-20261001T000000Z-pg-0001", "pg-0001", "2026-10-01T00:00:00Z", "1", "first_capture"),
    ("snap-20261008T000000Z-pg-0001", "pg-0001", "2026-10-08T00:00:00Z", "1", "unchanged"),
    ("snap-20261015T000000Z-pg-0001", "pg-0001", "2026-10-15T00:00:00Z", "1", "fetch_error"),
    ("snap-20261022T000000Z-pg-0001", "pg-0001", "2026-10-22T00:00:00Z", "1", "blocked"),
    ("snap-20261008T000000Z-pg-0002", "pg-0002", "2026-10-08T00:00:00Z", "1", "changed"),
    ("snap-20261008T000000Z-pg-0001", "pg-0001", "2026-10-08T00:00:00Z", "2", "first_capture"),
)


def test_prev_skips_failures():
    p = select_prev(INDEX, "pg-0001", "2026-10-29T00:00:00Z", "snap-20261029T000000Z-pg-0001", "1")
    assert p["snapshot_id"] == "snap-20261008T000000Z-pg-0001"


def test_prev_none_for_first():
    assert select_prev(INDEX, "pg-0003", "2026-10-29T00:00:00Z", "snap-x", "1") is None


def test_prev_same_version_only():
    p = select_prev(INDEX, "pg-0001", "2026-10-29T00:00:00Z", "snap-20261029T000000Z-pg-0001", "2")
    assert (p["snapshot_id"], p["normalizer_version"]) == ("snap-20261008T000000Z-pg-0001", "2")


def test_backfilled_manual_only_compares_with_earlier():
    # A manual file saved on 10-05 but registered later compares with 10-01, not with 10-08.
    p = select_prev(INDEX, "pg-0001", "2026-10-05T00:00:00Z", "snap-20261005T000000Z-pg-0001", "1")
    assert p["snapshot_id"] == "snap-20261001T000000Z-pg-0001"


def test_same_time_tie_broken_by_snapshot_id():
    ix = idx(("snap-20261001T000000Z-pg-0001", "pg-0001", "2026-10-01T00:00:00Z", "1", "first_capture"))
    assert select_prev(ix, "pg-0001", "2026-10-01T00:00:00Z", "snap-20261001T000000Z-pg-0001", "1") is None
    assert select_prev(ix, "pg-0001", "2026-10-01T00:00:00Z", "snap-20261001T000000Z-pg-0002x", "1") is not None


def test_prev_on_empty_index():
    assert select_prev(idx(), "pg-0001", "2026-10-01T00:00:00Z", "snap-x", "1") is None
