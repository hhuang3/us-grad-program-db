"""docs/spec/07_snapshots.md §5.2: manual-due and register-manual (offline)."""

import hashlib
import os
from datetime import datetime, timezone

import pytest

from gradprog.snapshot.manual import manual_due, register_from_dir, register_manual, render_manual_due
from gradprog.snapshot.store import SnapshotError, SnapshotStore
from helpers import make_mhtml, make_pdf

T = {"char_drop": 0.5, "min_similarity": 0.3}
URL3 = "https://business.alpha.edu/msba"
URL4 = "https://business.alpha.edu/msba/admissions?term=fall"
BODY = "<html><body><main><h1>MS Business Analytics</h1>" + "".join(
    f"<p>Requirement {i}: details.</p>" for i in range(10)) + "</main></body></html>"


@pytest.fixture
def reg(registry):
    """alpha-ms-businessanalytics is manual: pg-0003 and pg-0004 are manual pages."""
    p = registry.programs
    p.loc[p.program_id == "alpha-ms-businessanalytics", "fetch_method"] = "manual"
    return registry


@pytest.fixture
def store(tmp_path):
    return SnapshotStore(tmp_path / "snapshots")


def write(tmp_path, name, data):
    path = tmp_path / "downloads" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def reg_one(reg, store, path, page="pg-0003", when="2026-10-06T10:00:00Z"):
    return register_manual(reg, store, page, path, retrieved_at=when, now=lambda: "2026-10-06T12:00:00Z",
                           thresholds=T, rules={})


# --- register-manual ----------------------------------------------------------

def test_register_mhtml(reg, store, tmp_path):
    src = write(tmp_path, "msba.mhtml", make_mhtml(URL3, BODY))
    row = reg_one(reg, store, src)
    assert (row["method"], row["content_type"], row["final_url"], row["classification"]) == (
        "manual", "mhtml", URL3, "first_capture")
    assert (row["requested_url"], row["http_status"], row["retrieved_at"]) == (URL3, "", "2026-10-06T10:00:00Z")
    raw = store.raw_path("pg-0003", row["snapshot_id"], "mhtml")
    assert raw.read_bytes() == src.read_bytes() and src.exists()          # copied, not moved
    assert row["raw_sha256"] == hashlib.sha256(src.read_bytes()).hexdigest()
    assert store.read_runs().iloc[-1]["method"] == "manual"


def test_second_capture_unchanged(reg, store, tmp_path):
    reg_one(reg, store, write(tmp_path, "a.mhtml", make_mhtml(URL3, BODY)))
    row = reg_one(reg, store, write(tmp_path, "b.mhtml", make_mhtml(URL3, BODY)), when="2026-10-20T10:00:00Z")
    assert row["classification"] == "unchanged"


def test_location_mismatch_is_rejected(reg, store, tmp_path):
    src = write(tmp_path, "wrong.mhtml", make_mhtml("https://business.alpha.edu/mba", BODY))
    with pytest.raises(SnapshotError, match="business.alpha.edu/mba"):
        reg_one(reg, store, src)
    assert not (store.root / "index.csv").exists()


def test_location_matches_known_redirect_target(reg, store, tmp_path):
    reg_one(reg, store, write(tmp_path, "a.mhtml", make_mhtml(URL3, BODY)))
    ix = store.read_index().iloc[0].to_dict()
    ix.update(snapshot_id="snap-20261007T000000Z-pg-0003", retrieved_at="2026-10-07T00:00:00Z",
              final_url="https://business.alpha.edu/programs/msba", method="auto", classification="unchanged")
    store.append_index(ix)
    row = reg_one(reg, store, write(tmp_path, "moved.mhtml", make_mhtml("https://business.alpha.edu/programs/msba", BODY)),
                  when="2026-10-21T00:00:00Z")
    assert row["final_url"] == "https://business.alpha.edu/programs/msba"


def test_location_is_normalized_before_comparison(reg, store, tmp_path):
    src = write(tmp_path, "q.mhtml", make_mhtml("https://Business.alpha.edu/msba/admissions?term=fall&utm_source=x#top", BODY))
    assert reg_one(reg, store, src, page="pg-0004")["classification"] == "first_capture"


def test_missing_location_is_rejected(reg, store, tmp_path):
    src = write(tmp_path, "noloc.mhtml", make_mhtml(URL3, BODY, snapshot_header=False, part_location=False))
    with pytest.raises(SnapshotError):
        reg_one(reg, store, src)


def test_register_pdf(reg, store, tmp_path):
    src = write(tmp_path, "msba.pdf", make_pdf(["MSBA requirements", "Deadline January 15"]))
    row = reg_one(reg, store, src)
    assert (row["content_type"], row["final_url"], row["classification"]) == ("pdf", URL3, "first_capture")


@pytest.mark.parametrize("name, data", [("page.html", b"<p>x</p>"), ("fake.pdf", b"<html>not a pdf</html>")])
def test_wrong_file_type_is_rejected(reg, store, tmp_path, name, data):
    with pytest.raises(SnapshotError):
        reg_one(reg, store, write(tmp_path, name, data))


def test_only_manual_pages(reg, store, tmp_path):
    src = write(tmp_path, "ds.mhtml", make_mhtml("https://datascience.alpha.edu/ms", BODY))
    with pytest.raises(SnapshotError, match="pg-0001"):
        reg_one(reg, store, src, page="pg-0001")


def test_date_only_retrieved_at(reg, store, tmp_path):
    row = reg_one(reg, store, write(tmp_path, "a.mhtml", make_mhtml(URL3, BODY)), when="2026-10-06")
    assert row["retrieved_at"] == "2026-10-06T00:00:00Z" and "time_unknown" in row["note"]


def test_retrieved_at_from_file_mtime(reg, store, tmp_path):
    src = write(tmp_path, "a.mhtml", make_mhtml(URL3, BODY))
    ts = datetime(2026, 10, 6, 13, 31, 0, tzinfo=timezone.utc).timestamp()
    os.utime(src, (ts, ts))
    row = register_manual(reg, store, "pg-0003", src, retrieved_at=None, now=lambda: "2026-10-07T00:00:00Z",
                          thresholds=T, rules={})
    assert row["retrieved_at"] == "2026-10-06T13:31:00Z" and "retrieved_at_from_mtime" in row["note"]


def test_empty_saved_page_is_fetch_error(reg, store, tmp_path):
    src = write(tmp_path, "empty.mhtml", make_mhtml(URL3, "<html><body><script>x()</script></body></html>"))
    row = reg_one(reg, store, src)
    assert row["classification"] == "fetch_error" and "可能需要 JavaScript 渲染" in row["note"]


# --- --from-dir ---------------------------------------------------------------

def test_from_dir(reg, store, tmp_path):
    write(tmp_path, "one.mhtml", make_mhtml(URL3, BODY))
    write(tmp_path, "two.mhtml", make_mhtml(URL4, BODY))
    write(tmp_path, "unknown.mhtml", make_mhtml("https://business.alpha.edu/elsewhere", BODY))
    write(tmp_path, "auto.mhtml", make_mhtml("https://datascience.alpha.edu/ms", BODY))
    write(tmp_path, "doc.pdf", make_pdf(["x"]))
    write(tmp_path, "notes.txt", b"ignore me")
    registered, unmatched = register_from_dir(reg, store, tmp_path / "downloads", retrieved_at="2026-10-06",
                                              now=lambda: "2026-10-06T12:00:00Z", thresholds=T, rules={})
    assert sorted(r["page_id"] for r in registered) == ["pg-0003", "pg-0004"]
    assert sorted(u["file"] for u in unmatched) == ["auto.mhtml", "doc.pdf", "unknown.mhtml"]
    assert len(store.read_runs()) == 1
    assert store.read_index()["run_id"].nunique() == 1


# --- manual-due ---------------------------------------------------------------

def test_never_captured_pages_are_due(reg, store):
    due = manual_due(reg, store, today="2026-10-06")
    assert list(due["page_id"]) == ["pg-0003", "pg-0004"]
    assert set(due["last_retrieved"]) == {""}


@pytest.mark.parametrize("today, due_pages", [("2026-10-19", ["pg-0004"]), ("2026-10-20", ["pg-0003", "pg-0004"])])
def test_fourteen_day_rule(reg, store, tmp_path, today, due_pages):
    reg_one(reg, store, write(tmp_path, "a.mhtml", make_mhtml(URL3, BODY)), when="2026-10-06T23:00:00Z")
    assert list(manual_due(reg, store, today=today)["page_id"]) == due_pages


def test_failed_capture_does_not_reset_the_clock(reg, store, tmp_path):
    src = write(tmp_path, "empty.mhtml", make_mhtml(URL3, "<html><body></body></html>"))
    reg_one(reg, store, src, when="2026-10-06T10:00:00Z")
    assert "pg-0003" in list(manual_due(reg, store, today="2026-10-07")["page_id"])


def test_render_manual_due(reg, store):
    md = render_manual_due(manual_due(reg, store, today="2026-10-06"))
    assert "alpha-ms-businessanalytics" in md
    assert f"[{URL4}]({URL4})" in md
    assert "从未" in md and "2" in md.splitlines()[-1]
