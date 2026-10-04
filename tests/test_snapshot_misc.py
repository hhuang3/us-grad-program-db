"""docs/spec/07_snapshots.md §6.4 (renormalize), §8 (links), §10 (launchd, backup)."""

import hashlib
import re

import pytest

from gradprog.snapshot.backup import BackupError, backup
from gradprog.snapshot.links import discover_links, load_keywords, registrable_domain
from gradprog.snapshot.manual import register_manual
from gradprog.snapshot.renormalize import renormalize
from gradprog.snapshot.store import SnapshotStore
from helpers import REPO, make_mhtml

T = {"char_drop": 0.5, "min_similarity": 0.3}
URL3 = "https://business.alpha.edu/msba"
BODY = "<html><body><main><h1>MSBA</h1>" + "".join(f"<p>Item {i}.</p>" for i in range(10)) + \
       "<p>Updated weekly.</p></main></body></html>"


# --- renormalize (§6.4) -------------------------------------------------------

@pytest.fixture
def populated(registry, tmp_path):
    p = registry.programs
    p.loc[p.program_id == "alpha-ms-businessanalytics", "fetch_method"] = "manual"
    store = SnapshotStore(tmp_path / "snapshots")
    for i, when in enumerate(["2026-10-06T10:00:00Z", "2026-10-20T10:00:00Z"]):
        body = BODY.replace("Updated weekly.", f"Updated weekly. Build {i}.")
        src = tmp_path / f"cap{i}.mhtml"
        src.write_bytes(make_mhtml(URL3, body))
        register_manual(registry, store, "pg-0003", src, retrieved_at=when, now=lambda: when, thresholds=T, rules={})
    failed = store.read_index().iloc[0].to_dict()
    failed.update(snapshot_id="snap-20261013T000000Z-pg-0003", retrieved_at="2026-10-13T00:00:00Z",
                  method="auto", content_type="", raw_sha256="", raw_bytes="", normalizer_version="",
                  norm_sha256="", norm_chars="", classification="fetch_error", prev_snapshot_id="", note="")
    store.append_index(failed)
    return registry, store


def test_v1_sees_build_line_as_change(populated):
    _, store = populated
    assert list(store.read_index()["classification"]) == ["first_capture", "changed", "fetch_error"]


def test_renormalize_appends_rows_and_keeps_raw(populated):
    registry, store = populated
    index_before = (store.root / "index.csv").read_bytes()
    raws = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (store.root / "raw").rglob("*") if p.is_file()}
    rules = {"business.alpha.edu": [{"remove_line_regex": r"^Updated weekly\."}]}
    rows = renormalize(registry, store, version=2, rules=rules, thresholds=T, now=lambda: "2026-10-21T00:00:00Z")
    assert (store.root / "index.csv").read_bytes().startswith(index_before)        # old rows untouched
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in raws} == raws   # raw files untouched
    new = store.read_index()[store.read_index()["normalizer_version"] == "2"]
    assert len(rows) == 2 and len(new) == 2                                         # failed capture not redone
    assert list(new["classification"]) == ["first_capture", "unchanged"]           # noise removed by v2 rule
    assert all("renormalized" in n for n in new["note"])
    assert new["run_id"].iloc[0].endswith("-renormalize")
    for r in new.itertuples(index=False):
        assert store.norm_path(r.page_id, r.snapshot_id, 2).is_file()
        assert store.norm_path(r.page_id, r.snapshot_id, 1).is_file()                # v1 output kept


def test_renormalize_is_idempotent(populated):
    registry, store = populated
    renormalize(registry, store, version=2, rules={}, thresholds=T, now=lambda: "2026-10-21T00:00:00Z")
    assert renormalize(registry, store, version=2, rules={}, thresholds=T, now=lambda: "2026-10-22T00:00:00Z") == []


# --- link discovery (§8) ------------------------------------------------------

@pytest.mark.parametrize("host, expected", [("cds.nyu.edu", "nyu.edu"), ("www.engineering.columbia.edu", "columbia.edu"),
                                            ("utdallas.edu", "utdallas.edu"), ("Grad.UCLA.edu", "ucla.edu"),
                                            ("www.example.com", "www.example.com")])
def test_registrable_domain(host, expected):
    assert registrable_domain(host) == expected


def test_keywords_from_config():
    assert load_keywords(REPO / "config" / "link_keywords.yaml") == [
        "admission", "apply", "deadline", "requirement", "tuition", "cost", "fee", "faq", "international", "i-20",
        "visa"]


def test_discover_links():
    html = ('<a href="/ms/apply">Apply</a> <a href="https://gsas.alpha.edu/x">Deadlines and fees</a> '
            '<a href="https://datascience.alpha.edu/ms/apply">Apply again</a> '
            '<a href="https://grad.alpha.edu/admissions/international">Registered</a> '
            '<a href="https://other.edu/admissions">Other school</a> <a href="/people">People</a> '
            '<a href="http://datascience.alpha.edu/faq">Insecure FAQ</a> <a href="mailto:a@alpha.edu">FAQ email</a> '
            '<a href="/i-20/info#top">Form</a>')
    got = discover_links(html, "https://datascience.alpha.edu/ms", {"https://grad.alpha.edu/admissions/international"},
                         ["apply", "deadline", "i-20", "faq", "admission"])
    assert [c["url"] for c in got] == ["https://datascience.alpha.edu/ms/apply", "https://gsas.alpha.edu/x",
                                       "https://datascience.alpha.edu/i-20/info"]
    assert got[0]["text"] == "Apply"


# --- launchd templates (§10.1) ------------------------------------------------

def test_launchd_templates():
    d = REPO / "ops" / "launchd"
    plist = (d / "com.gradprog.snapshot.plist.template").read_text(encoding="utf-8")
    script = (d / "run-snapshot.sh").read_text(encoding="utf-8")
    readme = (d / "README.md").read_text(encoding="utf-8")
    assert "<key>Weekday</key>" in plist and "<integer>1</integer>" in plist
    assert "<key>Hour</key>" in plist and "<integer>7</integer>" in plist
    assert "__REPO_DIR__" in plist and "/Users/" not in plist
    assert ".config/gradprog/env" in script and "GRADPROG_CONTACT_EMAIL" in script
    assert "snapshot run" in script
    for text in (plist, script, readme):   # no real address in the repository, only placeholders
        assert all(m.endswith("@example.com") for m in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text))
    assert "launchctl" in readme and "时区" in readme


# --- backup (§10.2) -----------------------------------------------------------

@pytest.fixture
def src(tmp_path):
    s = tmp_path / "snapshots"
    (s / "raw" / "pg-0001").mkdir(parents=True)
    (s / "raw" / "pg-0001" / "snap-a.html").write_bytes(b"raw a")
    (s / "reports").mkdir()
    (s / "reports" / "run-1.md").write_text("report v1", encoding="utf-8")
    (s / "index.csv").write_text("h\nrow1\n", encoding="utf-8")
    (s / "runs.csv").write_text("h\nrun1\n", encoding="utf-8")
    return s


def test_backup_copies_then_skips(src, tmp_path):
    dest = tmp_path / "backup"
    first = backup(src, dest)
    assert (dest / "raw" / "pg-0001" / "snap-a.html").read_bytes() == b"raw a"
    assert first["copied"] == 4
    second = backup(src, dest)
    assert (second["copied"], second["skipped"], second["overwritten"]) == (0, 4, 0)


def test_backup_appended_csv_overwrites_prefix(src, tmp_path):
    dest = tmp_path / "backup"
    backup(src, dest)
    (src / "index.csv").write_text("h\nrow1\nrow2\n", encoding="utf-8")
    assert backup(src, dest)["overwritten"] == 1
    assert (dest / "index.csv").read_text(encoding="utf-8") == "h\nrow1\nrow2\n"


def test_backup_refuses_non_prefix_csv(src, tmp_path):
    dest = tmp_path / "backup"
    backup(src, dest)
    (dest / "runs.csv").write_text("h\nsomething else\n", encoding="utf-8")
    with pytest.raises(BackupError, match="runs.csv"):
        backup(src, dest)


def test_backup_refuses_changed_immutable_file(src, tmp_path):
    dest = tmp_path / "backup"
    backup(src, dest)
    (dest / "raw" / "pg-0001" / "snap-a.html").write_bytes(b"tampered")
    with pytest.raises(BackupError, match="snap-a.html"):
        backup(src, dest)


def test_backup_overwrites_reports_and_never_deletes(src, tmp_path):
    dest = tmp_path / "backup"
    backup(src, dest)
    (dest / "extra.txt").write_text("keep", encoding="utf-8")
    (src / "reports" / "run-1.md").write_text("report v2", encoding="utf-8")
    assert backup(src, dest)["overwritten"] == 1
    assert (dest / "reports" / "run-1.md").read_text(encoding="utf-8") == "report v2"
    assert (dest / "extra.txt").exists()


def test_backup_requires_destination(src):
    with pytest.raises((BackupError, TypeError, ValueError)):
        backup(src, None)
