"""docs/spec/07_snapshots.md §6.4 (renormalize), §8 (links), §10 (launchd, backup)."""

import hashlib
import plistlib
import re

import pytest

from gradprog.snapshot.backup import BackupError, backup
from gradprog.snapshot.links import discover_links, load_keywords, registrable_domain
from gradprog.snapshot.manual import register_manual
from gradprog.snapshot.normalize import NORMALIZER_VERSION
from gradprog.snapshot.renormalize import renormalize
from gradprog.snapshot.store import SnapshotStore
from helpers import REPO, make_mhtml

T = {"char_drop": 0.5, "min_similarity": 0.3}
NEXT = NORMALIZER_VERSION + 1   # renormalize tests target the version after the current one
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


def test_current_version_sees_build_line_as_change(populated):
    _, store = populated
    assert list(store.read_index()["classification"]) == ["first_capture", "changed", "fetch_error"]


def test_renormalize_appends_rows_and_keeps_raw(populated):
    registry, store = populated
    index_before = (store.root / "index.csv").read_bytes()
    raws = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (store.root / "raw").rglob("*") if p.is_file()}
    rules = {"business.alpha.edu": [{"remove_line_regex": r"^Updated weekly\."}]}
    rows = renormalize(registry, store, version=NEXT, rules=rules, thresholds=T, now=lambda: "2026-10-21T00:00:00Z")
    assert (store.root / "index.csv").read_bytes().startswith(index_before)        # old rows untouched
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in raws} == raws   # raw files untouched
    new = store.read_index()[store.read_index()["normalizer_version"] == str(NEXT)]
    assert len(rows) == 2 and len(new) == 2                                         # failed capture not redone
    assert list(new["classification"]) == ["first_capture", "unchanged"]           # noise removed by v2 rule
    assert all("renormalized" in n for n in new["note"])
    assert new["run_id"].iloc[0].endswith("-renormalize")
    for r in new.itertuples(index=False):
        assert store.norm_path(r.page_id, r.snapshot_id, NEXT).is_file()
        assert store.norm_path(r.page_id, r.snapshot_id, NORMALIZER_VERSION).is_file()   # current output kept


def test_renormalize_reports_rule_losses(populated, tmp_path):
    registry, store = populated
    src = tmp_path / "fees.mhtml"
    src.write_bytes(make_mhtml(URL3, BODY.replace("Updated weekly.", "Tuition $1,800 per credit.")))
    register_manual(registry, store, "pg-0003", src, retrieved_at="2026-10-21T09:00:00Z",
                    now=lambda: "2026-10-21T09:00:00Z", thresholds=T, rules={})
    rules = {"business.alpha.edu": [{"remove_line_regex": r"^Tuition"}]}
    renormalize(registry, store, version=NEXT, rules=rules, thresholds=T, now=lambda: "2026-10-22T00:00:00Z")
    run_id = store.read_runs().iloc[-1]["run_id"]
    report = store.report_path(run_id).read_text(encoding="utf-8")
    assert "按域名规则删除的疑似数据行" in report and "pg-0003" in report


def test_renormalize_is_idempotent(populated):
    registry, store = populated
    renormalize(registry, store, version=NEXT, rules={}, thresholds=T, now=lambda: "2026-10-21T00:00:00Z")
    assert renormalize(registry, store, version=NEXT, rules={}, thresholds=T, now=lambda: "2026-10-22T00:00:00Z") == []


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


def test_discover_links_ignores_navigation_regions_and_email_paths():
    html = ('<header><a href="/apply">Header apply</a></header>'
            '<nav><a href="/admissions/undergraduate">Undergraduate Admission</a></nav>'
            '<div role="navigation"><a href="/phd/admission">PhD Admission</a></div>'
            '<div id="cookie-banner"><a href="/privacy-faq">Cookie FAQ</a></div>'
            '<main><a href="/ms/apply">Apply to the MS</a> <a href="visp-msds@stat.alpha.edu">Email admissions</a>'
            '<a href="/ms/tuition">Tuition</a></main>'
            '<footer><a href="/deadlines">Footer deadlines</a></footer>'
            '<div class="site-menu"><a href="/fees">Menu fees</a></div>')
    got = discover_links(html, "https://datascience.alpha.edu/ms/", set(), ["apply", "admission", "faq", "deadline",
                                                                           "tuition", "fee"])
    assert [c["url"] for c in got] == ["https://datascience.alpha.edu/ms/apply",
                                       "https://datascience.alpha.edu/ms/tuition",
                                       "https://datascience.alpha.edu/fees"]


def test_discover_links_applies_domain_remove_selector():
    html = '<main><a href="/ms/apply">Apply</a></main><div class="site-menu"><a href="/fees">Menu fees</a></div>'
    rules = {"datascience.alpha.edu": [{"remove_selector": ".site-menu"}]}
    got = discover_links(html, "https://datascience.alpha.edu/ms/", set(), ["apply", "fee"],
                         domain="datascience.alpha.edu", rules=rules)
    assert [c["url"] for c in got] == ["https://datascience.alpha.edu/ms/apply"]


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
    # every Sunday 20:00 in the Mac's time zone (Weekday 0 = Sunday)
    assert plistlib.loads(plist.encode("utf-8"))["StartCalendarInterval"] == {"Weekday": 0, "Hour": 20, "Minute": 0}
    assert "Sunday 20:00" in readme and "20:00" in plist
    assert "__REPO_DIR__" in plist and "/Users/" not in plist
    assert ".config/gradprog/env" in script and "GRADPROG_CONTACT_EMAIL" in script
    assert "snapshot run" in script
    for text in (plist, script, readme):   # no real address in the repository, only placeholders
        assert all(m.endswith("@example.com") for m in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text))
    assert "launchctl" in readme and "时区" in readme
    assert "caffeinate -i" in script and "合盖" in readme      # lid-close sleep is not prevented (§10.1)


STUBS = {
    # fake uv: remember the call and the time, so the fake sleep log can fall inside the run window
    "uv": 'echo "uv $*"; [[ -n "${UV_SAY:-}" ]] && echo "$UV_SAY"; date "+%Y-%m-%d %H:%M:%S %z" > "$HOME/during"; '
          'exit "${UV_EXIT:-0}"',
    "osascript": 'shift; printf "osascript %s\\n" "$*" >> "$HOME/calls"',   # drop the "-" (script on stdin), keep argv
    "caffeinate": 'echo "caffeinate $1" >> "$HOME/calls"; shift; exec "$@"',
    "pmset": """case "$2" in
  batt) printf "${BATT:-Now drawing from 'Battery Power'\n -InternalBattery-0 (id=1)\t11%%; discharging; 2:10 remaining present: true\n}";;
  log) [[ -n "${SLEEPS:-}" ]] && printf "%s Sleep               \tEntering Sleep state due to 'Maintenance Sleep'\n" "$(cat "$HOME/during")"; true;;
esac""",
}


def run_wrapper(tmp_path, **env):
    import shutil
    import subprocess

    if not shutil.which("zsh"):
        pytest.skip("zsh not available")
    home = tmp_path / "home"
    (home / ".config" / "gradprog").mkdir(parents=True)
    (home / ".config" / "gradprog" / "env").write_text("GRADPROG_CONTACT_EMAIL=someone@example.com\n")
    bin_dir = home / ".local" / "bin"
    bin_dir.mkdir(parents=True)
    for name, body in STUBS.items():
        (bin_dir / name).write_text("#!/bin/zsh\n" + body + "\n")
        (bin_dir / name).chmod(0o755)
    script = REPO / "ops" / "launchd" / "run-snapshot.sh"
    result = subprocess.run(["zsh", str(script)], env={"HOME": str(home), **env}, capture_output=True, text=True)
    calls = (home / "calls").read_text() if (home / "calls").exists() else ""
    return result, calls


def test_wrapper_keeps_the_mac_awake_and_logs_power(tmp_path):
    result, calls = run_wrapper(tmp_path)
    assert result.returncode == 0, result.stderr
    assert calls == "caffeinate -i\n"                                   # the run is wrapped in caffeinate -i
    out = result.stdout
    assert "uv run gradprog snapshot run" in out
    assert out.count("power: Battery Power; 11%; discharging; 2:10 remaining") == 2   # start and end
    assert re.search(r"elapsed \d+ s; sleeps during run: 0", out)
    assert "WARNING" not in out and "someone@example.com" not in out


def test_wrapper_warns_about_sleep_and_keeps_exit_code(tmp_path):
    result, _ = run_wrapper(tmp_path, SLEEPS="1", UV_EXIT="3")
    assert result.returncode == 3
    assert "sleeps during run: 1" in result.stdout
    assert re.search(r"^WARNING: .*sleep", result.stdout, re.MULTILINE)
    assert result.stdout.count("power:") == 2                          # end is logged even when the run fails


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


def test_wrapper_power_summary_while_charging(tmp_path):
    batt = "Now drawing from 'AC Power'\\n -InternalBattery-0 (id=1)\\t22%%; charging; (no estimate) present: true\\n"
    result, _ = run_wrapper(tmp_path, BATT=batt)
    assert result.stdout.count("power: AC Power; 22%; charging; (no estimate)") == 2


def test_cli_skips_the_run_when_the_network_is_down(monkeypatch, capsys, registry):
    from gradprog import cli
    from gradprog.registry import tables
    from gradprog.snapshot import fetch

    def down(*a, **kw):
        raise fetch.NetworkUnavailable("network unavailable: no TCP connection to a.edu, b.edu")

    monkeypatch.setattr(tables, "load_registry", lambda path: registry)
    monkeypatch.setattr(fetch, "run_auto", down)
    assert cli.main(["snapshot", "run"]) == 75
    out = capsys.readouterr().out
    assert "run skipped" in out and "network unavailable" in out


def test_wrapper_notifies_when_the_run_is_skipped(tmp_path):
    reason = "run skipped: network unavailable: no TCP connection to a.edu (port 443)"
    result, calls = run_wrapper(tmp_path, UV_EXIT="75", UV_SAY=reason)
    assert result.returncode == 75
    assert reason in result.stdout                                       # still logged
    note = [c for c in calls.splitlines() if c.startswith("osascript ")]
    assert len(note) == 1 and "network unavailable: no TCP connection to a.edu" in note[0]
    assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", note[0])        # local time of the skip


@pytest.mark.parametrize("exit_code", ["0", "1"])
def test_wrapper_does_not_notify_otherwise(tmp_path, exit_code):
    result, calls = run_wrapper(tmp_path, UV_EXIT=exit_code, SLEEPS="1")
    assert "osascript" not in calls
