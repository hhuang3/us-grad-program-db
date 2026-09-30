"""Polite single-threaded downloader and manual registration (docs/spec/01_reference_data.md §7)."""


class DownloadError(RuntimeError):
    """Download or registration failed; nothing was written to the manifest."""


def user_agent(contact_email):
    raise NotImplementedError


class Downloader:
    def __init__(self, raw_root, manifest_path, contact_email=None, client=None,
                 min_interval=3.0, clock=None, sleep=None, now=None):
        raise NotImplementedError

    def fetch(self, source, url, notes=""):
        raise NotImplementedError


def register_manual(source, url, file, retrieved_at, notes, raw_root, manifest_path):
    raise NotImplementedError
