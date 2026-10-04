"""docs/spec/07_snapshots.md §4: storage layout, index.csv and runs.csv."""

from pathlib import Path

import pytest

from gradprog.snapshot.store import SnapshotError, SnapshotStore, make_run_id, make_snapshot_id

INDEX_COLUMNS = [
    "snapshot_id", "page_id", "run_id", "method", "retrieved_at", "requested_url", "final_url", "http_status",
    "content_type", "raw_sha256", "raw_bytes", "normalizer_version", "norm_sha256", "norm_chars",
    "classification", "prev_snapshot_id", "added_lines", "removed_lines", "note",
]
CLASSES = ["first_capture", "unchanged", "changed", "suspected_redesign", "unavailable", "blocked", "fetch_error"]
RUNS_COLUMNS = ["run_id", "method", "started_at", "finished_at", *CLASSES, "anomaly_page_ids"]


def row(**over):
    base = {c: "" for c in INDEX_COLUMNS}
    base.update(snapshot_id="snap-20261005T070003Z-pg-0001", page_id="pg-0001", run_id="run-20261005T070000Z-auto",
                method="auto", retrieved_at="2026-10-05T07:00:03Z", requested_url="https://a.edu/x",
                final_url="https://a.edu/x", http_status="200", content_type="html", raw_sha256="a" * 64,
                raw_bytes="10", normalizer_version="1", norm_sha256="b" * 64, norm_chars="5",
                classification="first_capture")
    base.update(over)
    return base


def test_snapshot_id():
    assert make_snapshot_id("2026-10-05T07:00:03Z", "pg-0001") == "snap-20261005T070003Z-pg-0001"


@pytest.mark.parametrize("bad", ["2026-10-05 07:00:03", "2026-10-05", ""])
def test_snapshot_id_rejects_bad_time(bad):
    with pytest.raises(ValueError):
        make_snapshot_id(bad, "pg-0001")


def test_run_id():
    assert make_run_id("2026-10-05T07:00:00Z", "auto") == "run-20261005T070000Z-auto"
    with pytest.raises(ValueError):
        make_run_id("2026-10-05T07:00:00Z", "weekly")


def test_paths_include_version(tmp_path):
    s = SnapshotStore(tmp_path)
    sid = "snap-20261005T070003Z-pg-0001"
    assert s.raw_path("pg-0001", sid, "html") == tmp_path / "raw" / "pg-0001" / f"{sid}.html"
    assert s.norm_path("pg-0001", sid, 1) == tmp_path / "normalized" / "pg-0001" / f"{sid}.v1.txt"
    assert s.diff_path("pg-0001", sid, 2) == tmp_path / "diffs" / "pg-0001" / f"{sid}.v2.diff"


def test_index_header_and_append_only(tmp_path):
    s = SnapshotStore(tmp_path)
    s.append_index(row())
    first = (tmp_path / "index.csv").read_bytes()
    assert first.splitlines()[0] == ",".join(INDEX_COLUMNS).encode()
    s.append_index(row(snapshot_id="snap-20261012T070003Z-pg-0001", retrieved_at="2026-10-12T07:00:03Z",
                       classification="unchanged", prev_snapshot_id="snap-20261005T070003Z-pg-0001"))
    second = (tmp_path / "index.csv").read_bytes()
    assert second.startswith(first)                      # existing bytes untouched
    assert list(s.read_index()["classification"]) == ["first_capture", "unchanged"]
    assert s.read_index()["norm_chars"].iloc[0] == "5"   # read as strings


def test_index_key_is_snapshot_and_version(tmp_path):
    s = SnapshotStore(tmp_path)
    s.append_index(row())
    s.append_index(row(normalizer_version="2", note="renormalized"))   # same snapshot, new version: ok
    with pytest.raises(SnapshotError):
        s.append_index(row())                                          # exact duplicate key


def test_index_rejects_wrong_header(tmp_path):
    (tmp_path / "index.csv").write_text("snapshot_id,page_id\n", encoding="utf-8")
    with pytest.raises(SnapshotError):
        SnapshotStore(tmp_path).append_index(row())


@pytest.mark.parametrize("bad", [{"classification": "moved"}, {"method": "browser"}, {"extra": "x"}])
def test_index_rejects_invalid_rows(tmp_path, bad):
    r = row()
    r.update(bad)
    with pytest.raises(SnapshotError):
        SnapshotStore(tmp_path).append_index(r)


def test_note_must_be_single_line(tmp_path):
    with pytest.raises(SnapshotError):
        SnapshotStore(tmp_path).append_index(row(note="a\nb"))


def test_runs_append(tmp_path):
    s = SnapshotStore(tmp_path)
    r = {c: "0" for c in CLASSES}
    r.update(run_id="run-20261005T070000Z-auto", method="auto", started_at="2026-10-05T07:00:00Z",
             finished_at="2026-10-05T07:03:00Z", first_capture="2", anomaly_page_ids="pg-0003;pg-0007")
    s.append_run(r)
    text = (tmp_path / "runs.csv").read_text(encoding="utf-8").splitlines()
    assert text[0] == ",".join(RUNS_COLUMNS)
    assert s.read_runs()["anomaly_page_ids"].iloc[0] == "pg-0003;pg-0007"


def test_gitignore_keeps_bodies_out_of_git():
    gi = (Path(__file__).parent.parent / ".gitignore").read_text(encoding="utf-8")
    for p in ["data/snapshots/raw/", "data/snapshots/normalized/", "data/snapshots/diffs/",
              "data/snapshots/reports/", "data/snapshots/manual_due.md", "data/snapshots/logs/"]:
        assert p in gi, p
