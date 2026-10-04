"""Automatic snapshot runs (07 §5.1, §7, §9)."""

MAX_BYTES = 10 * 1024 * 1024


def run_auto(registry, store, contact_email=None, client=None, clock=None, sleep=None, now=None,
             page_ids=None, dry_run=False, thresholds=None, rules=None, url_check=None,
             max_bytes=MAX_BYTES, keywords=None):
    raise NotImplementedError
