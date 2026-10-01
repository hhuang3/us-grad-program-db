"""docs/spec/01_reference_data.md §7: polite downloader and manual registration (offline)."""

import hashlib

import httpx
import pytest

import gradprog
from gradprog.util.download import DownloadError, Downloader, register_manual, user_agent
from gradprog.util.manifest import read_manifest

PDF = b"%PDF-1.6\nfake pdf body"
ZIP = b"PK\x03\x04fake zip body"
HTML = b"<html><body>Access Denied</body></html>"
EMAIL = "someone@example.com"
NOW = "2026-10-01T12:00:00Z"


class FakeTime:
    def __init__(self):
        self.t = 1000.0
        self.slept = []

    def clock(self):
        return self.t

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.t += seconds


def make(tmp_path, handler, monkeypatch, email=EMAIL, fake=None):
    if email is None:
        monkeypatch.delenv("GRADPROG_CONTACT_EMAIL", raising=False)
    else:
        monkeypatch.setenv("GRADPROG_CONTACT_EMAIL", email)
    fake = fake or FakeTime()
    client = httpx.Client(transport=httpx.MockTransport(handler))
    d = Downloader(tmp_path / "raw", tmp_path / "manifest.csv", client=client,
                   clock=fake.clock, sleep=fake.sleep, now=lambda: NOW)
    return d, fake


def ok(body):
    return lambda request: httpx.Response(200, content=body)


def test_user_agent_format():
    assert user_agent(EMAIL) == f"gradprog-refdata/{gradprog.__version__} (+mailto:{EMAIL})"


def test_missing_contact_email_refuses_to_run(tmp_path, monkeypatch):
    with pytest.raises(DownloadError, match="GRADPROG_CONTACT_EMAIL"):
        make(tmp_path, ok(PDF), monkeypatch, email=None)


def test_request_sends_user_agent(tmp_path, monkeypatch):
    seen = {}

    def handler(request):
        seen["ua"] = request.headers["user-agent"]
        return httpx.Response(200, content=ZIP)

    d, _ = make(tmp_path, handler, monkeypatch)
    d.fetch("ipeds_hd", "https://nces.ed.gov/ipeds/complete-data-files/HD2024.zip")
    assert seen["ua"] == user_agent(EMAIL)


def test_fetch_saves_file_and_manifest_row(tmp_path, monkeypatch):
    d, _ = make(tmp_path, ok(ZIP), monkeypatch)
    path = d.fetch("ipeds_hd", "https://nces.ed.gov/ipeds/complete-data-files/HD2024.zip")
    assert path == tmp_path / "raw" / "ipeds_hd" / "2026-10-01" / "HD2024.zip"
    assert path.read_bytes() == ZIP
    m = read_manifest(tmp_path / "manifest.csv")
    assert len(m) == 1
    r = m.iloc[0]
    assert (r["source"], r["method"], r["retrieved_at"]) == ("ipeds_hd", "http", NOW)
    assert r["sha256"] == hashlib.sha256(ZIP).hexdigest()
    assert int(r["bytes"]) == len(ZIP)


@pytest.mark.parametrize(
    "url",
    ["https://www.ice.gov/doclib/sevis/pdf/stemList2024.pdf",
     "https://nces.ed.gov/ipeds/complete-data-files/C2024_A.zip"],
)
def test_wrong_file_type_is_rejected_without_trace(tmp_path, monkeypatch, url):
    d, _ = make(tmp_path, ok(HTML), monkeypatch)
    with pytest.raises(DownloadError):
        d.fetch("dhs_stem", url)
    raw = tmp_path / "raw"
    assert not raw.exists() or not any(p.is_file() for p in raw.rglob("*"))
    assert not (tmp_path / "manifest.csv").exists()


def test_http_error_is_rejected(tmp_path, monkeypatch):
    d, _ = make(tmp_path, lambda r: httpx.Response(403, content=HTML), monkeypatch)
    with pytest.raises(DownloadError, match="403"):
        d.fetch("dhs_stem", "https://www.ice.gov/doclib/sevis/pdf/stemList2024.pdf")
    assert not (tmp_path / "manifest.csv").exists()


def test_requests_are_spaced_at_least_three_seconds(tmp_path, monkeypatch):
    d, fake = make(tmp_path, ok(ZIP), monkeypatch)
    d.fetch("ipeds_hd", "https://nces.ed.gov/ipeds/complete-data-files/HD2024.zip")
    fake.t += 1.0
    d.fetch("ipeds_completions", "https://nces.ed.gov/ipeds/complete-data-files/C2024_A.zip")
    assert sum(fake.slept) >= 2.0 - 1e-9  # 3 s minimum minus the 1 s already elapsed


# --- register_manual (§7.2) ---------------------------------------------------

STEM_URL = "https://www.ice.gov/doclib/sevis/pdf/stemList2024.pdf"


def test_register_manual_copies_and_records(tmp_path):
    src = tmp_path / "Downloads" / "stemList2024.pdf"
    src.parent.mkdir()
    src.write_bytes(PDF)
    path = register_manual("dhs_stem", STEM_URL, src, "2026-10-01T15:04:00Z",
                           "automated request returned HTTP 403", tmp_path / "raw", tmp_path / "manifest.csv")
    assert path == tmp_path / "raw" / "dhs_stem" / "2026-10-01" / "stemList2024.pdf"
    assert path.read_bytes() == PDF and src.exists()  # copied, not moved
    r = read_manifest(tmp_path / "manifest.csv").iloc[0]
    assert (r["method"], r["url"], r["retrieved_at"]) == ("manual", STEM_URL, "2026-10-01T15:04:00Z")
    assert r["sha256"] == hashlib.sha256(PDF).hexdigest()
    assert r["notes"] == "automated request returned HTTP 403"


def test_register_manual_date_only_marks_time_unknown(tmp_path):
    src = tmp_path / "stemList2024.pdf"
    src.write_bytes(PDF)
    register_manual("dhs_stem", STEM_URL, src, "2026-10-01", "automated request returned HTTP 403",
                    tmp_path / "raw", tmp_path / "manifest.csv")
    r = read_manifest(tmp_path / "manifest.csv").iloc[0]
    assert r["retrieved_at"] == "2026-10-01T00:00:00Z"
    assert r["notes"].endswith("time_unknown")


def test_register_manual_rejects_wrong_file_type(tmp_path):
    src = tmp_path / "stemList2024.pdf"
    src.write_bytes(HTML)
    with pytest.raises(DownloadError):
        register_manual("dhs_stem", STEM_URL, src, "2026-10-01T15:04:00Z", "403",
                        tmp_path / "raw", tmp_path / "manifest.csv")
    assert not (tmp_path / "manifest.csv").exists()


def test_register_manual_never_overwrites_different_content(tmp_path):
    src = tmp_path / "stemList2024.pdf"
    src.write_bytes(PDF)
    target = tmp_path / "raw" / "dhs_stem" / "2026-10-01" / "stemList2024.pdf"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"%PDF-1.6 different")
    with pytest.raises(DownloadError):
        register_manual("dhs_stem", STEM_URL, src, "2026-10-01T15:04:00Z", "403",
                        tmp_path / "raw", tmp_path / "manifest.csv")
    assert target.read_bytes() == b"%PDF-1.6 different"


@pytest.mark.parametrize("bad", ["2026/10/01", "yesterday", "2026-10-01T15:04:00+02:00"])
def test_register_manual_rejects_bad_timestamp(tmp_path, bad):
    src = tmp_path / "stemList2024.pdf"
    src.write_bytes(PDF)
    with pytest.raises((DownloadError, ValueError)):
        register_manual("dhs_stem", STEM_URL, src, bad, "403", tmp_path / "raw", tmp_path / "manifest.csv")
