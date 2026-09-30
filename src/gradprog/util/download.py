"""Polite single-threaded downloader and manual registration (docs/spec/01_reference_data.md §7)."""

import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import httpx

from gradprog import __version__
from gradprog.util.manifest import (
    ManifestError,
    append_manifest,
    raw_path_for,
    sha256_file,
    validate_timestamp,
)

CONTACT_ENV = "GRADPROG_CONTACT_EMAIL"
TIMEOUT_SECONDS = 120
MAX_RETRIES = 2
MAGIC = {".pdf": b"%PDF-", ".zip": b"PK\x03\x04", ".xlsx": b"PK\x03\x04"}
DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class DownloadError(RuntimeError):
    """Download or registration failed; nothing was written to the manifest."""


def user_agent(contact_email):
    return f"gradprog-refdata/{__version__} (+mailto:{contact_email})"


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_file_type(url, head):
    """Reject content whose leading bytes do not match the file type implied by the URL."""
    suffix = PurePosixPath(urlparse(url).path).suffix.lower()
    magic = MAGIC.get(suffix)
    if magic is not None:
        if not head.startswith(magic):
            raise DownloadError(f"{url}: expected {suffix} content starting with {magic!r}, got {head[:16]!r}")
    elif head.lstrip()[:15].lower().startswith((b"<!doctype html", b"<html")):
        raise DownloadError(f"{url}: got an HTML page instead of a {suffix or 'data'} file")


def _store(content_path, target):
    """Place content at target; identical existing file is reused, a different one is never overwritten."""
    if target.exists():
        if sha256_file(target) != sha256_file(content_path):
            raise DownloadError(f"{target} already exists with different content; refusing to overwrite")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(content_path, target)


class Downloader:
    def __init__(self, raw_root, manifest_path, contact_email=None, client=None,
                 min_interval=3.0, clock=None, sleep=None, now=None):
        email = contact_email or os.environ.get(CONTACT_ENV, "").strip()
        if not email:
            raise DownloadError(f"set {CONTACT_ENV} to a contact email before downloading")
        self.raw_root = Path(raw_root)
        self.manifest_path = Path(manifest_path)
        self.headers = {"User-Agent": user_agent(email)}
        self.client = client or httpx.Client(follow_redirects=True, timeout=TIMEOUT_SECONDS)
        self.min_interval = min_interval
        self.clock = clock or time.monotonic
        self.sleep = sleep or time.sleep
        self.now = now or utc_now
        self._last = None

    def _wait(self):
        if self._last is not None:
            elapsed = self.clock() - self._last
            if elapsed < self.min_interval:
                self.sleep(self.min_interval - elapsed)

    def _get(self, url):
        for attempt in range(MAX_RETRIES + 1):
            self._wait()
            try:
                resp = self.client.get(url, headers=self.headers, follow_redirects=True)
            except httpx.TransportError as e:
                self._last = self.clock()
                if attempt == MAX_RETRIES:
                    raise DownloadError(f"{url}: {e}") from e
                continue
            self._last = self.clock()
            if resp.status_code >= 500 and attempt < MAX_RETRIES:
                continue
            if not 200 <= resp.status_code < 300:
                raise DownloadError(f"{url}: HTTP {resp.status_code}")
            return resp.content
        raise AssertionError("unreachable")

    def fetch(self, source, url, notes=""):
        content = self._get(url)
        check_file_type(url, content[:64])
        retrieved_at = self.now()
        target = raw_path_for(self.raw_root, source, url, retrieved_at)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".part")
        tmp.write_bytes(content)
        try:
            _store(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)
        append_manifest(self.manifest_path, {
            "source": source, "url": url, "method": "http", "retrieved_at": retrieved_at,
            "sha256": sha256_file(target), "bytes": target.stat().st_size, "notes": notes,
        })
        return target


def register_manual(source, url, file, retrieved_at, notes, raw_root, manifest_path):
    file = Path(file).expanduser()
    if not file.is_file():
        raise DownloadError(f"{file} does not exist")
    notes = (notes or "").strip()
    if isinstance(retrieved_at, str) and DATE_ONLY.match(retrieved_at):
        retrieved_at = retrieved_at + "T00:00:00Z"
        notes = f"{notes}; time_unknown" if notes else "time_unknown"
    try:
        validate_timestamp(retrieved_at)
    except ManifestError as e:
        raise DownloadError(str(e)) from e
    with open(file, "rb") as f:
        check_file_type(url, f.read(64))
    target = raw_path_for(raw_root, source, url, retrieved_at)
    _store(file, target)
    append_manifest(manifest_path, {
        "source": source, "url": url, "method": "manual", "retrieved_at": retrieved_at,
        "sha256": sha256_file(target), "bytes": target.stat().st_size, "notes": notes,
    })
    return target
